"""Tests for the compressed protobuf telemetry codec, containers, and CLI."""

import io
import json
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner
from vehicle_profile_tools.cli import cli
from vehicle_profile_tools.resolve import resolve
from vehicle_profile_tools.telemetry import (
    Acquisition,
    Constraints,
    Dictionary,
    NameKind,
    Observation,
    Quality,
    Quantization,
    SignalSpec,
    TelemetryError,
    ValueKind,
    build_dictionary,
    decode_batch,
    encode_batch,
    host_sensor_signals,
    infer_dictionary,
    inspect_telemetry,
    read_telemetry,
    read_vts_bytes,
    read_zip_bytes,
    write_observations_jsonl,
    write_telemetry,
    write_vts_bytes,
    write_zip_bytes,
)

ROOT = Path(__file__).resolve().parents[1]


def test_build_dictionary_from_profile_and_host_sensors():
    doc = resolve([ROOT / "examples/universal-obd"])
    dictionary = build_dictionary("veh-1", document=doc, include_host_sensors=True)
    names = {s.name for s in dictionary.signals}
    assert "Vehicle.Speed" in names
    assert "Vehicle.Powertrain.CombustionEngine.Speed" in names
    assert "SUPPORTED_PIDS_01_20" in names
    assert "Vehicle.CurrentLocation.Latitude" in names
    assert "Vehicle.Acceleration.Longitudinal" in names
    assert "Vehicle.AngularVelocity.Yaw" in names
    assert len(dictionary.fingerprint) == 32


def test_roundtrip_quantized_profile_and_host_gps_imu():
    dictionary = Dictionary(
        vehicle_id="test-car",
        signals=(
            SignalSpec(
                id=1,
                name="Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature",
                unit="celsius",
                value_kind=ValueKind.FLOAT,
                source="dbc:main:CLIMATE_STATUS.DRIVER_TEMPERATURE_SETTING",
                acquisition=Acquisition.SIGNAL,
                quantization=Quantization(origin=16.0, scale=0.5),
                constraints=Constraints(min=16.0, max=30.0, step=0.5),
            ),
            SignalSpec(
                id=2,
                name="Vehicle.CurrentLocation.Latitude",
                unit="degrees",
                value_kind=ValueKind.FLOAT,
                source="host.gnss",
                acquisition=Acquisition.HOST,
                clock_domain="gnss-utc",
                quantization=Quantization(origin=0.0, scale=1e-7),
                constraints=Constraints(min=-90.0, max=90.0),
            ),
            SignalSpec(
                id=3,
                name="Vehicle.Cabin.IsCentralLockEngaged",
                value_kind=ValueKind.BOOL,
                source="can0:60D",
                acquisition=Acquisition.SIGNAL,
            ),
            SignalSpec(
                id=4,
                name="Vehicle.VehicleIdentification.VIN",
                value_kind=ValueKind.STRING,
                source="query:engine",
                acquisition=Acquisition.QUERY,
            ),
            SignalSpec(
                id=5,
                name="Vehicle.Speed",
                unit="km/h",
                value_kind=ValueKind.FLOAT,
                source="can0:100",
                acquisition=Acquisition.SIGNAL,
                # Unquantized raw double fallback.
            ),
        ),
    )

    t0 = 1_764_151_200_000
    observations = [
        # Step-grid float without observed_at (must remain None).
        Observation(
            name="Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature",
            received_at_ms=t0 + i * 100,
            value=20.0 + (i % 3) * 0.5,
            source="dbc:main:CLIMATE_STATUS.DRIVER_TEMPERATURE_SETTING",
            sequence=10 + i,
        )
        for i in range(6)
    ]
    # Jittered 25 Hz GNSS latitude with measurement timestamps.
    gnss_intervals = [0, 40, 80, 121, 160, 200]
    for idx, dt in enumerate(gnss_intervals):
        observations.append(
            Observation(
                name="Vehicle.CurrentLocation.Latitude",
                received_at_ms=t0 + dt,
                observed_at_ms=t0 + dt - 12,
                value=round(37.7749000 + idx * 0.0000123, 7),
                source="host.gnss",
                acquisition=Acquisition.HOST,
                clock_domain="gnss-utc",
                sequence=100 + idx,
            )
        )
    # Repeated booleans (RLE).
    for idx in range(10):
        observations.append(
            Observation(
                name="Vehicle.Cabin.IsCentralLockEngaged",
                received_at_ms=t0 + idx * 50,
                value=idx >= 7,
                source="can0:60D",
                sequence=idx,
            )
        )
    # Repeated string + mixed observed_at presence.
    observations.extend(
        [
            Observation(
                name="Vehicle.VehicleIdentification.VIN",
                received_at_ms=t0,
                observed_at_ms=None,
                value="1N4AL3AP8JC123456",
                source="query:engine",
                acquisition=Acquisition.QUERY,
                sequence=1,
            ),
            Observation(
                name="Vehicle.VehicleIdentification.VIN",
                received_at_ms=t0 + 1000,
                observed_at_ms=t0 + 995,
                value="1N4AL3AP8JC123456",
                source="query:engine",
                acquisition=Acquisition.QUERY,
                sequence=2,
            ),
        ]
    )
    # Unquantized raw doubles with repeats and mixed quality.
    observations.extend(
        [
            Observation(
                name="Vehicle.Speed",
                received_at_ms=t0,
                value=88.125,
                quality=Quality.VALID,
                source="can0:100",
                sequence=1,
            ),
            Observation(
                name="Vehicle.Speed",
                received_at_ms=t0 + 100,
                value=88.125,
                quality=Quality.STALE,
                source="can0:100",
                sequence=2,
            ),
            Observation(
                name="Vehicle.Speed",
                received_at_ms=t0 + 200,
                value=None,
                quality=Quality.UNAVAILABLE,
                source="can0:100",
                sequence=3,
            ),
        ]
    )

    batch = encode_batch(dictionary, observations)
    raw_vts = write_vts_bytes(dictionary, [batch], compress=False)
    decoded_dict, decoded = read_vts_bytes(raw_vts)
    assert decoded_dict == dictionary

    by_sig_orig = sorted(observations, key=lambda o: (o.name, o.source, o.sequence))
    by_sig_dec = sorted(decoded, key=lambda o: (o.name, o.source, o.sequence))
    assert len(by_sig_dec) == len(by_sig_orig)

    for orig, dec in zip(by_sig_orig, by_sig_dec, strict=True):
        assert dec.name == orig.name
        assert dec.received_at_ms == orig.received_at_ms
        assert dec.observed_at_ms == orig.observed_at_ms
        assert dec.quality == orig.quality
        assert dec.sequence == orig.sequence
        if isinstance(orig.value, float):
            assert dec.value == pytest.approx(orig.value, abs=1e-7)
        else:
            assert dec.value == orig.value


def test_off_grid_and_out_of_range_never_clamped():
    dictionary = Dictionary(
        vehicle_id="veh-grid",
        signals=(
            SignalSpec(
                id=1,
                name="Vehicle.Powertrain.CombustionEngine.Speed",
                unit="rpm",
                value_kind=ValueKind.FLOAT,
                source="can0:180",
                quantization=Quantization(origin=0.0, scale=0.5),
                constraints=Constraints(min=0.0, max=8000.0, step=0.5),
            ),
        ),
    )

    off_grid = Observation(
        name="Vehicle.Powertrain.CombustionEngine.Speed",
        received_at_ms=1000,
        value=1200.25,  # Off 0.5 step grid.
        source="can0:180",
        sequence=1,
    )
    out_of_range = Observation(
        name="Vehicle.Powertrain.CombustionEngine.Speed",
        received_at_ms=1100,
        value=9500.0,  # Above max 8000.
        source="can0:180",
        sequence=2,
    )

    # Reject as valid by default (never silently clamp).
    with pytest.raises(TelemetryError, match="off step grid"):
        encode_batch(dictionary, [off_grid])
    with pytest.raises(TelemetryError, match="above max"):
        encode_batch(dictionary, [out_of_range])

    # With downgrade_invalid=True, encode strictly as INVALID with value=None.
    valid = Observation(
        name="Vehicle.Powertrain.CombustionEngine.Speed",
        received_at_ms=1200,
        value=2500.5,
        source="can0:180",
        sequence=3,
    )
    batch = encode_batch(dictionary, [off_grid, out_of_range, valid], downgrade_invalid=True)
    decoded = decode_batch(dictionary, batch)
    assert [o.quality for o in decoded] == [Quality.INVALID, Quality.INVALID, Quality.VALID]
    assert [o.value for o in decoded] == [None, None, 2500.5]


def test_emit_on_change_with_max_age_heartbeat():
    dictionary = Dictionary(
        vehicle_id="veh-hb",
        signals=(
            SignalSpec(
                id=1,
                name="Vehicle.Speed",
                unit="km/h",
                value_kind=ValueKind.FLOAT,
                source="can0:100",
                quantization=Quantization(origin=0.0, scale=0.1),
                max_age_ms=500,
            ),
        ),
    )
    # 11 samples at 100 ms: constant 50.0 km/h from t=0..700, changes to 52.0 at t=800, constant to t=1000.
    obs = [
        Observation(
            name="Vehicle.Speed",
            received_at_ms=10_000 + i * 100,
            value=50.0 if i < 8 else 52.0,
            source="can0:100",
            sequence=100 + i,
        )
        for i in range(11)
    ]
    batch = encode_batch(dictionary, obs, emit_on_change=True)
    decoded = decode_batch(dictionary, batch)
    # Kept: i=0 (first), i=5 (heartbeat at +500 ms), i=8 (changed to 52.0).
    assert [o.sequence for o in decoded] == [100, 105, 108]
    assert [o.received_at_ms for o in decoded] == [10_000, 10_500, 10_800]
    assert [o.value for o in decoded] == [50.0, 50.0, 52.0]


def test_dictionary_fingerprint_mismatch_rejected():
    dict_a = Dictionary(
        vehicle_id="veh-a",
        signals=(
            SignalSpec(
                id=1,
                name="Vehicle.Speed",
                unit="km/h",
                value_kind=ValueKind.FLOAT,
                source="can0:100",
            ),
        ),
    )
    dict_b = Dictionary(
        vehicle_id="veh-b",
        signals=dict_a.signals,
    )
    batch = encode_batch(
        dict_a,
        [Observation(name="Vehicle.Speed", received_at_ms=1000, value=60.0, source="can0:100")],
    )
    with pytest.raises(TelemetryError, match="fingerprint mismatch"):
        decode_batch(dict_b, batch)

    # Also check tampered ZIP manifest fingerprint.
    zip_data = write_zip_bytes(dict_a, [batch])
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(zip_data), "r") as src, zipfile.ZipFile(buf, "w") as dst:
        dst.writestr("session.vts", src.read("session.vts"))
        manifest = json.loads(src.read("manifest.json").decode("utf-8"))
        manifest["dictionary_fingerprint"] = "00" * 32
        dst.writestr("manifest.json", json.dumps(manifest))
    with pytest.raises(TelemetryError, match="manifest fingerprint mismatch"):
        read_zip_bytes(buf.getvalue())


def test_compression_size_vts_zlib_and_zip_vs_jsonl(tmp_path):
    dictionary = Dictionary(
        vehicle_id="track-car",
        signals=tuple(host_sensor_signals(include_gnss_speed=True)),
    )
    t0 = 1_764_151_200_000
    observations: list[Observation] = []
    # 5 seconds at 25 Hz GPS + 100 Hz IMU (constant cruise with small deltas).
    for i in range(125):
        ts = t0 + i * 40
        observations.extend(
            [
                Observation(
                    name="Vehicle.CurrentLocation.Latitude",
                    received_at_ms=ts,
                    observed_at_ms=ts - 5,
                    value=round(37.7749000 + i * 0.0000040, 7),
                    source="host.gnss",
                    acquisition=Acquisition.HOST,
                    clock_domain="gnss-utc",
                    sequence=i,
                ),
                Observation(
                    name="Vehicle.CurrentLocation.Longitude",
                    received_at_ms=ts,
                    observed_at_ms=ts - 5,
                    value=round(-122.4194000 - i * 0.0000020, 7),
                    source="host.gnss",
                    acquisition=Acquisition.HOST,
                    clock_domain="gnss-utc",
                    sequence=i,
                ),
                Observation(
                    name="Vehicle.Speed",
                    received_at_ms=ts,
                    observed_at_ms=ts - 5,
                    value=100.0 + (i % 2) * 0.05,
                    source="host.gnss",
                    acquisition=Acquisition.HOST,
                    clock_domain="gnss-utc",
                    sequence=i,
                ),
            ]
        )
    for i in range(500):
        ts = t0 + i * 10
        observations.append(
            Observation(
                name="Vehicle.Acceleration.Longitudinal",
                received_at_ms=ts,
                observed_at_ms=ts - 2,
                value=0.0 if i < 250 else round(0.01 * (i - 250), 3),
                source="host.imu",
                acquisition=Acquisition.HOST,
                sequence=i,
            )
        )

    jsonl_path = tmp_path / "obs.jsonl"
    vts_zlib_path = tmp_path / "session.vts"
    zip_path = tmp_path / "session.zip"
    write_observations_jsonl(jsonl_path, observations)
    zlib_bytes = write_telemetry(vts_zlib_path, dictionary, observations, compression="zlib")
    zip_bytes = write_telemetry(zip_path, dictionary, observations, compression="zip")
    jsonl_bytes = jsonl_path.stat().st_size

    # Columnar delta + RLE + zlib/zip should beat JSONL by well over 10x.
    assert zlib_bytes < jsonl_bytes / 10
    assert zip_bytes < jsonl_bytes / 10

    dec_dict, dec_obs = read_telemetry(zip_path)
    assert dec_dict.fingerprint == dictionary.fingerprint
    assert len(dec_obs) == len(observations)


def test_cli_pack_unpack_inspect(tmp_path):
    t0 = 1_764_151_200_000
    obs = [
        Observation(
            name="Vehicle.Speed",
            name_kind=NameKind.PROPERTY,
            received_at_ms=t0 + i * 100,
            value=50.0 + i,
            source="query:engine",
            acquisition=Acquisition.QUERY,
            sequence=i,
        )
        for i in range(5)
    ]
    in_jsonl = tmp_path / "in.jsonl"
    out_zip = tmp_path / "out.zip"
    out_jsonl = tmp_path / "out.jsonl"
    write_observations_jsonl(in_jsonl, obs)

    runner = CliRunner()
    pack_res = runner.invoke(
        cli,
        [
            "telemetry",
            "pack",
            str(in_jsonl),
            "-o",
            str(out_zip),
            "--package",
            str(ROOT / "examples/universal-obd"),
            "--host-sensors",
            "--compression",
            "zip",
        ],
    )
    assert pack_res.exit_code == 0, pack_res.output
    pack_json = json.loads(pack_res.output)
    assert pack_json["compression"] == "zip"
    assert pack_json["observations"] == 5

    inspect_res = runner.invoke(cli, ["telemetry", "inspect", str(out_zip)])
    assert inspect_res.exit_code == 0, inspect_res.output
    summary = json.loads(inspect_res.output)
    assert summary["container"] == "zip"
    assert summary["observation_count"] == 5
    assert inspect_telemetry(out_zip)["dictionary_fingerprint"] == summary["dictionary_fingerprint"]

    unpack_res = runner.invoke(cli, ["telemetry", "unpack", str(out_zip), "-o", str(out_jsonl)])
    assert unpack_res.exit_code == 0, unpack_res.output
    lines = [json.loads(line) for line in out_jsonl.read_text().splitlines() if line.strip()]
    assert [row["value"] for row in lines] == [50.0, 51.0, 52.0, 53.0, 54.0]


def test_infer_dictionary_for_unmapped_query():
    obs = [
        Observation(
            name="SUPPORTED_PIDS_01_20",
            name_kind=NameKind.QUERY,
            received_at_ms=1000,
            value="BE1FA813",
            source="query:engine",
            acquisition=Acquisition.QUERY,
        )
    ]
    d = infer_dictionary("veh-q", obs)
    assert d.signals[0].value_kind == ValueKind.STRING
    decoded = decode_batch(d, encode_batch(d, obs))
    assert decoded[0].value == "BE1FA813"
