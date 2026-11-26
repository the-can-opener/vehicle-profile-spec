"""Tests for the valid-signals-only Racelogic .vbo exporter."""

import json

import pytest
from click.testing import CliRunner
from vehicle_profile_tools.cli import cli
from vehicle_profile_tools.telemetry import (
    Acquisition,
    Dictionary,
    Observation,
    Quality,
    Quantization,
    SignalSpec,
    TelemetryError,
    ValueKind,
    host_sensor_signals,
    write_telemetry,
)
from vehicle_profile_tools.vbo import STANDARD_GRAVITY, convert_to_vbo


def _make_mixed_session() -> tuple[Dictionary, list[Observation]]:
    host_specs = host_sensor_signals()
    next_id = len(host_specs) + 1
    extra = [
        SignalSpec(
            id=next_id,
            name="Vehicle.Speed",
            unit="km/h",
            value_kind=ValueKind.FLOAT,
            source="can0:100",
            acquisition=Acquisition.SIGNAL,
            quantization=Quantization(0.0, 0.1),
        ),
        SignalSpec(
            id=next_id + 1,
            name="Vehicle.Powertrain.CombustionEngine.Speed",
            unit="rpm",
            value_kind=ValueKind.FLOAT,
            source="can0:180",
            acquisition=Acquisition.SIGNAL,
            quantization=Quantization(0.0, 1.0),
        ),
        SignalSpec(
            id=next_id + 2,
            name="Vehicle.Cabin.IsCentralLockEngaged",
            value_kind=ValueKind.BOOL,
            source="can0:60D",
            acquisition=Acquisition.SIGNAL,
        ),
        SignalSpec(
            id=next_id + 3,
            name="Vehicle.VehicleIdentification.VIN",
            value_kind=ValueKind.STRING,
            source="query:engine",
            acquisition=Acquisition.QUERY,
        ),
        SignalSpec(
            id=next_id + 4,
            name="Vehicle.Chassis.Brake.PedalPosition",
            unit="percent",
            value_kind=ValueKind.UINT,
            source="can0:200",
            acquisition=Acquisition.SIGNAL,
        ),
    ]
    dictionary = Dictionary(vehicle_id="vbo-car", signals=(*host_specs, *extra))

    # 2026-11-26T10:00:00.000Z
    t0 = 1_795_687_200_000
    obs: list[Observation] = [
        # Fix status: NO_FIX at t0, 3D at t0 + 40 ms.
        Observation(
            name="Vehicle.CurrentLocation.GNSSReceiver.FixType",
            received_at_ms=t0 + 5,
            observed_at_ms=t0,
            value="NO_FIX",
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        Observation(
            name="Vehicle.CurrentLocation.GNSSReceiver.FixType",
            received_at_ms=t0 + 45,
            observed_at_ms=t0 + 40,
            value="3D",
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=2,
        ),
        # GPS point 0 at t0 (dropped because FixType == NO_FIX).
        Observation(
            name="Vehicle.CurrentLocation.Latitude",
            received_at_ms=t0 + 5,
            observed_at_ms=t0,
            value=37.0,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        Observation(
            name="Vehicle.CurrentLocation.Longitude",
            received_at_ms=t0 + 5,
            observed_at_ms=t0,
            value=-122.0,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        # GPS point 1 at t0 + 40 ms (San Francisco: +37.7749 N, -122.4194 W).
        Observation(
            name="Vehicle.CurrentLocation.Latitude",
            received_at_ms=t0 + 45,
            observed_at_ms=t0 + 40,
            value=37.7749,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=2,
        ),
        Observation(
            name="Vehicle.CurrentLocation.Longitude",
            received_at_ms=t0 + 45,
            observed_at_ms=t0 + 40,
            value=-122.4194,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=2,
        ),
        Observation(
            name="Vehicle.CurrentLocation.Altitude",
            received_at_ms=t0 + 45,
            observed_at_ms=t0 + 40,
            value=15.5,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=2,
        ),
        Observation(
            name="Vehicle.CurrentLocation.Heading",
            received_at_ms=t0 + 45,
            observed_at_ms=t0 + 40,
            value=90.25,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=2,
        ),
        # GPS point 2 at t0 + 80 ms (Tokyo: +35.6762 N, +139.6503 E -> negative VBO longitude).
        Observation(
            name="Vehicle.CurrentLocation.Latitude",
            received_at_ms=t0 + 85,
            observed_at_ms=t0 + 80,
            value=35.6762,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=3,
        ),
        Observation(
            name="Vehicle.CurrentLocation.Longitude",
            received_at_ms=t0 + 85,
            observed_at_ms=t0 + 80,
            value=139.6503,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=3,
        ),
        # Invalid GPS sample at t0 + 120 ms (must be dropped).
        Observation(
            name="Vehicle.CurrentLocation.Latitude",
            received_at_ms=t0 + 125,
            observed_at_ms=t0 + 120,
            value=None,
            quality=Quality.INVALID,
            source="host.gnss",
            acquisition=Acquisition.HOST,
            sequence=4,
        ),
        # Higher-rate IMU at t0 + 30 ms and t0 + 70 ms (ZOH picks latest <= row_ts).
        Observation(
            name="Vehicle.Acceleration.Longitudinal",
            received_at_ms=t0 + 30,
            observed_at_ms=t0 + 30,
            value=STANDARD_GRAVITY,  # +1.0 g
            source="host.imu",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        Observation(
            name="Vehicle.Acceleration.Lateral",
            received_at_ms=t0 + 30,
            observed_at_ms=t0 + 30,
            value=-0.5 * STANDARD_GRAVITY,  # -0.5 g
            source="host.imu",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        Observation(
            name="Vehicle.Acceleration.Vertical",
            received_at_ms=t0 + 30,
            observed_at_ms=t0 + 30,
            value=STANDARD_GRAVITY,  # +1.0 g
            source="host.imu",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        Observation(
            name="Vehicle.AngularVelocity.Yaw",
            received_at_ms=t0 + 30,
            observed_at_ms=t0 + 30,
            value=12.5,  # ISO 8855 CCW+ -> Racelogic CW+ = -12.5
            source="host.imu",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        Observation(
            name="Vehicle.AngularVelocity.Pitch",
            received_at_ms=t0 + 30,
            observed_at_ms=t0 + 30,
            value=3.0,
            source="host.imu",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        Observation(
            name="Vehicle.AngularVelocity.Roll",
            received_at_ms=t0 + 30,
            observed_at_ms=t0 + 30,
            value=4.0,  # Negated to -4.0
            source="host.imu",
            acquisition=Acquisition.HOST,
            sequence=1,
        ),
        # CAN signals: valid at t0 + 20 ms, STALE at t0 + 60 ms (STALE must NOT overwrite ZOH).
        Observation(
            name="Vehicle.Speed",
            received_at_ms=t0 + 20,
            value=72.5,
            source="can0:100",
            sequence=1,
        ),
        Observation(
            name="Vehicle.Speed",
            received_at_ms=t0 + 60,
            value=999.0,
            quality=Quality.STALE,
            source="can0:100",
            sequence=2,
        ),
        Observation(
            name="Vehicle.Powertrain.CombustionEngine.Speed",
            received_at_ms=t0 + 20,
            value=3200.0,
            source="can0:180",
            sequence=1,
        ),
        # Non-numeric signals (must be skipped in VBO, reported in skipped_signals).
        Observation(
            name="Vehicle.Cabin.IsCentralLockEngaged",
            received_at_ms=t0 + 20,
            value=True,
            source="can0:60D",
            sequence=1,
        ),
        Observation(
            name="Vehicle.VehicleIdentification.VIN",
            received_at_ms=t0 + 20,
            value="1N4AL3AP8JC123456",
            source="query:engine",
            acquisition=Acquisition.QUERY,
            sequence=1,
        ),
        # Numeric signal with only UNAVAILABLE samples (must be skipped with no_valid_samples).
        Observation(
            name="Vehicle.Chassis.Brake.PedalPosition",
            received_at_ms=t0 + 20,
            value=None,
            quality=Quality.UNAVAILABLE,
            source="can0:200",
            sequence=1,
        ),
    ]
    return dictionary, obs


def test_vbo_valid_only_conversions_and_structure():
    dictionary, obs = _make_mixed_session()
    vbo_text, report = convert_to_vbo(dictionary, obs)

    # CRLF line endings everywhere.
    assert "\r\n" in vbo_text
    assert "\n" not in vbo_text.replace("\r\n", "")

    assert report.row_count == 2
    assert report.dropped_no_fix_rows == 1
    assert report.dropped_observations == 3  # INVALID lat, STALE speed, UNAVAILABLE brake

    skipped_map = {s.name: s.reason for s in report.skipped_signals}
    assert skipped_map["Vehicle.Cabin.IsCentralLockEngaged"] == "non_numeric"
    assert skipped_map["Vehicle.VehicleIdentification.VIN"] == "non_numeric"
    assert skipped_map["Vehicle.CurrentLocation.GNSSReceiver.FixType"] == "non_numeric"
    assert skipped_map["Vehicle.Chassis.Brake.PedalPosition"] == "no_valid_samples"

    sections: dict[str, list[str]] = {}
    current = "_preamble"
    sections[current] = []
    for line in vbo_text.split("\r\n"):
        if line.startswith("[") and line.endswith("]"):
            current = line
            sections[current] = []
        elif line != "":
            sections[current].append(line)

    assert sections["_preamble"][0] == "File created on 26/11/2026 at 10:00:00"
    headers = sections["[header]"]
    units = sections["[channel units]"]
    cols = sections["[column names]"][0].split()
    rows = [line.split() for line in sections["[data]"]]

    assert len(cols) == len(headers)
    assert len(units) == len(report.nonstandard_channels)
    assert len(headers) == len(report.standard_channels) + len(report.nonstandard_channels)
    assert len(rows) == 2

    col_idx = {name: i for i, name in enumerate(cols)}
    row0, row1 = rows

    # Row 0: 10:00:00.040, San Francisco (+37.7749 N, -122.4194 W -> +7345.16400 W).
    assert row0[col_idx["time"]] == "100000.040"
    assert float(row0[col_idx["lat"]]) == pytest.approx(37.7749 * 60.0, abs=1e-4)
    assert float(row0[col_idx["long"]]) == pytest.approx(122.4194 * 60.0, abs=1e-4)
    assert float(row0[col_idx["velocity"]]) == pytest.approx(72.5, abs=1e-3)
    assert float(row0[col_idx["heading"]]) == pytest.approx(90.25, abs=1e-2)
    assert float(row0[col_idx["height"]]) == pytest.approx(15.5, abs=1e-2)
    assert float(row0[col_idx["longacc"]]) == pytest.approx(1.0, abs=1e-3)
    assert float(row0[col_idx["latacc"]]) == pytest.approx(-0.5, abs=1e-3)
    assert float(row0[col_idx["yaw_rate"]]) == pytest.approx(-12.5, abs=1e-2)
    assert float(row0[col_idx["z_accel"]]) == pytest.approx(1.0, abs=1e-3)
    assert float(row0[col_idx["pitch_rate"]]) == pytest.approx(3.0, abs=1e-2)
    assert float(row0[col_idx["roll_rate"]]) == pytest.approx(-4.0, abs=1e-2)
    rpm_col = col_idx["Vehicle_Powertrain_CombustionEngine_Speed"]
    assert float(row0[rpm_col]) == pytest.approx(3200.0, abs=1e-3)

    # Row 1: Tokyo (+139.6503 E -> negative VBO longitude); STALE speed 999.0 was dropped so 72.5 held.
    assert row1[col_idx["time"]] == "100000.080"
    assert float(row1[col_idx["long"]]) == pytest.approx(-139.6503 * 60.0, abs=1e-4)
    assert float(row1[col_idx["velocity"]]) == pytest.approx(72.5, abs=1e-3)


def test_vbo_max_age_cutoff_expires_stale_channel():
    dictionary, obs = _make_mixed_session()
    vbo_text, _ = convert_to_vbo(dictionary, obs, max_age_ms=30)
    lines = vbo_text.split("\r\n")
    cols = lines[lines.index("[column names]") + 1].split()
    data_start = lines.index("[data]") + 1
    row0 = lines[data_start].split()
    row1 = lines[data_start + 1].split()
    vel_idx = cols.index("velocity")
    # Speed sampled at t0+20: valid at t0+40 (age 20 <= 30), expired at t0+80 (age 60 > 30).
    assert float(row0[vel_idx]) == pytest.approx(72.5, abs=1e-3)
    assert float(row1[vel_idx]) == pytest.approx(0.0, abs=1e-3)


def test_vbo_fails_without_valid_gps():
    dictionary = Dictionary(
        vehicle_id="no-gps",
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
    obs = [Observation(name="Vehicle.Speed", received_at_ms=1000, value=50.0, source="can0:100")]
    with pytest.raises(TelemetryError, match="Latitude and Longitude"):
        convert_to_vbo(dictionary, obs)


def test_cli_to_vbo_from_zip(tmp_path):
    dictionary, obs = _make_mixed_session()
    zip_path = tmp_path / "session.zip"
    vbo_path = tmp_path / "session.vbo"
    write_telemetry(zip_path, dictionary, obs, compression="zip")

    runner = CliRunner()
    result = runner.invoke(cli, ["telemetry", "to-vbo", str(zip_path), "-o", str(vbo_path)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["row_count"] == 2
    assert payload["dropped_no_fix_rows"] == 1
    assert vbo_path.exists()
    assert b"[data]\r\n" in vbo_path.read_bytes()
