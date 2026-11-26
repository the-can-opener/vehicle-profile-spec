"""Valid-signals-only converter from compressed telemetry to Racelogic .vbo format."""

from __future__ import annotations

import bisect
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .telemetry import (
    Acquisition,
    Dictionary,
    Observation,
    Quality,
    SignalSpec,
    TelemetryError,
    ValueKind,
    read_telemetry,
)

STANDARD_GRAVITY = 9.80665

_LAT_PATH = "Vehicle.CurrentLocation.Latitude"
_LON_PATH = "Vehicle.CurrentLocation.Longitude"
_FIX_PATH = "Vehicle.CurrentLocation.GNSSReceiver.FixType"

_NO_FIX_VALUES = frozenset({"", "0", "NONE", "NO_FIX", "NOFIX", "INVALID", "NO FIX"})


@dataclass(frozen=True)
class _ChannelMapping:
    header: str
    column: str
    standard: bool
    unit: str
    convert: Callable[[float], float]
    fmt: Callable[[float], str]


def _fmt_lat_lon(val: float) -> str:
    return f"{val:+012.5f}"


def _fmt_speed(val: float) -> str:
    return f"{val:07.3f}"


def _fmt_heading(val: float) -> str:
    return f"{val:06.2f}"


def _fmt_height(val: float) -> str:
    return f"{val:+09.2f}"


def _fmt_accel(val: float) -> str:
    return f"{val:+07.4f}"


def _fmt_rate(val: float) -> str:
    return f"{val:+08.3f}"


def _fmt_generic(val: float) -> str:
    return f"{val:+.4f}"


# Ordered standard VBO mappings (after `time`, `latitude`, `longitude`).
_STANDARD_MAPPINGS: tuple[tuple[str, _ChannelMapping], ...] = (
    (
        "Vehicle.Speed",
        _ChannelMapping("velocity kmh", "velocity", True, "", lambda v: v, _fmt_speed),
    ),
    (
        "Vehicle.CurrentLocation.Heading",
        _ChannelMapping("heading", "heading", True, "", lambda v: v, _fmt_heading),
    ),
    (
        "Vehicle.CurrentLocation.Altitude",
        _ChannelMapping("height", "height", True, "", lambda v: v, _fmt_height),
    ),
    (
        "Vehicle.Acceleration.Longitudinal",
        _ChannelMapping(
            "long accel g",
            "longacc",
            True,
            "",
            lambda v: v / STANDARD_GRAVITY,
            _fmt_accel,
        ),
    ),
    (
        "Vehicle.Acceleration.Lateral",
        _ChannelMapping(
            "lat accel g",
            "latacc",
            True,
            "",
            lambda v: v / STANDARD_GRAVITY,
            _fmt_accel,
        ),
    ),
    (
        "Vehicle.AngularVelocity.Yaw",
        _ChannelMapping("yaw rate deg/s", "yaw_rate", True, "", lambda v: -v, _fmt_rate),
    ),
)

_NONSTANDARD_IMU_MAPPINGS: dict[str, _ChannelMapping] = {
    "Vehicle.Acceleration.Vertical": _ChannelMapping(
        "Z-Acceleration",
        "z_accel",
        False,
        "g",
        lambda v: v / STANDARD_GRAVITY,
        _fmt_accel,
    ),
    "Vehicle.AngularVelocity.Pitch": _ChannelMapping(
        "PitchRate",
        "pitch_rate",
        False,
        "deg/s",
        lambda v: v,
        _fmt_rate,
    ),
    "Vehicle.AngularVelocity.Roll": _ChannelMapping(
        "RollRate",
        "roll_rate",
        False,
        "deg/s",
        lambda v: -v,
        _fmt_rate,
    ),
}


@dataclass(frozen=True)
class SkippedSignal:
    name: str
    source: str
    reason: str
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        data = {"name": self.name, "source": self.source, "reason": self.reason}
        if self.note:
            data["note"] = self.note
        return data


@dataclass(frozen=True)
class VboReport:
    row_count: int
    standard_channels: tuple[str, ...]
    nonstandard_channels: tuple[str, ...]
    dropped_observations: int
    dropped_no_fix_rows: int
    skipped_signals: tuple[SkippedSignal, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "standard_channels": list(self.standard_channels),
            "nonstandard_channels": list(self.nonstandard_channels),
            "dropped_observations": self.dropped_observations,
            "dropped_no_fix_rows": self.dropped_no_fix_rows,
            "skipped_signals": [s.to_dict() for s in self.skipped_signals],
        }


def _effective_ts_ms(obs: Observation) -> int:
    return obs.observed_at_ms if obs.observed_at_ms is not None else obs.received_at_ms


def _sanitize_column_name(raw: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_") or "signal"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _format_vbo_time(epoch_ms: int) -> str:
    sec, ms = divmod(epoch_ms, 1000)
    dt = datetime.fromtimestamp(sec, tz=timezone.utc)
    return f"{dt.hour:02d}{dt.minute:02d}{dt.second:02d}.{ms:03d}"


def _format_created_line(epoch_ms: int) -> str:
    sec, _ = divmod(epoch_ms, 1000)
    dt = datetime.fromtimestamp(sec, tz=timezone.utc)
    return f"File created on {dt.strftime('%d/%m/%Y')} at {dt.strftime('%H:%M:%S')}"


def _pair_gps_anchors(
    lats: Sequence[tuple[int, float]],
    lons: Sequence[tuple[int, float]],
    tolerance_ms: int,
) -> list[tuple[int, float, float]]:
    anchors: list[tuple[int, float, float]] = []
    lon_idx = 0
    n_lons = len(lons)
    for t_lat, lat in lats:
        while lon_idx < n_lons and lons[lon_idx][0] < t_lat - tolerance_ms:
            lon_idx += 1
        best_idx: int | None = None
        best_diff = tolerance_ms + 1
        probe = lon_idx
        while probe < n_lons and lons[probe][0] <= t_lat + tolerance_ms:
            diff = abs(lons[probe][0] - t_lat)
            if diff < best_diff:
                best_diff = diff
                best_idx = probe
            probe += 1
        if best_idx is not None:
            t_lon, lon = lons[best_idx]
            row_ts = t_lat if t_lat == t_lon else round((t_lat + t_lon) / 2)
            anchors.append((row_ts, lat, lon))
            lon_idx = best_idx + 1
    return anchors


def _is_valid_fix(
    row_ts: int,
    fix_ts: Sequence[int],
    fix_vals: Sequence[str],
) -> bool:
    if not fix_ts:
        return True
    idx = bisect.bisect_right(fix_ts, row_ts) - 1
    if idx < 0:
        return True
    return fix_vals[idx].strip().upper() not in _NO_FIX_VALUES


def _zoh_lookup(
    row_ts: int,
    times: Sequence[int],
    values: Sequence[float],
    max_age_ms: int | None,
) -> float:
    idx = bisect.bisect_right(times, row_ts) - 1
    if idx < 0:
        return 0.0
    if max_age_ms is not None and max_age_ms > 0 and (row_ts - times[idx]) > max_age_ms:
        return 0.0
    return values[idx]


def _source_priority(spec: SignalSpec) -> tuple[int, int]:
    # Prefer vehicle bus signals over external host sources when deduplicating standard VBO columns.
    rank = 0 if spec.acquisition in (Acquisition.SIGNAL, Acquisition.QUERY) else 1
    return (rank, spec.id)


def convert_to_vbo(
    dictionary: Dictionary,
    observations: Sequence[Observation],
    *,
    gps_pair_tolerance_ms: int = 5,
    max_age_ms: int | None = None,
) -> tuple[str, VboReport]:
    """Convert valid numeric telemetry observations to CRLF-terminated Racelogic .vbo text."""
    dropped_observations = 0
    valid_by_key: dict[tuple[str, str], list[tuple[int, float]]] = {}
    fix_samples: list[tuple[int, str]] = []

    spec_by_key = {(s.name, s.source): s for s in dictionary.signals}
    numeric_kinds = {ValueKind.INT, ValueKind.UINT, ValueKind.FLOAT}

    for obs in observations:
        if obs.quality != Quality.VALID or obs.value is None:
            dropped_observations += 1
            continue

        if obs.name == _FIX_PATH:
            if isinstance(obs.value, str):
                fix_samples.append((_effective_ts_ms(obs), obs.value))
            else:
                fix_samples.append((_effective_ts_ms(obs), str(obs.value)))
            continue

        spec = spec_by_key.get((obs.name, obs.source))
        if spec is None:
            try:
                spec = dictionary.resolve_signal(obs.name, obs.source)
            except TelemetryError:
                dropped_observations += 1
                continue

        if spec.value_kind not in numeric_kinds:
            continue
        if type(obs.value) is bool or not isinstance(obs.value, (int, float)):
            dropped_observations += 1
            continue
        fval = float(obs.value)
        if not math.isfinite(fval):
            dropped_observations += 1
            continue
        valid_by_key.setdefault((spec.name, spec.source), []).append((_effective_ts_ms(obs), fval))

    for samples in valid_by_key.values():
        samples.sort(key=lambda item: item[0])

    fix_samples.sort(key=lambda item: item[0])
    fix_ts = [t for t, _ in fix_samples]
    fix_vals = [v for _, v in fix_samples]

    skipped: list[SkippedSignal] = []
    for spec in dictionary.signals:
        if spec.name == _FIX_PATH:
            skipped.append(
                SkippedSignal(
                    spec.name,
                    spec.source,
                    "non_numeric",
                    "used for GNSS fix filtering",
                )
            )
            continue
        if spec.value_kind not in numeric_kinds:
            skipped.append(SkippedSignal(spec.name, spec.source, "non_numeric"))
            continue
        if (spec.name, spec.source) not in valid_by_key:
            skipped.append(SkippedSignal(spec.name, spec.source, "no_valid_samples"))

    # Select Latitude and Longitude series.
    lat_specs = sorted(
        (
            s
            for s in dictionary.signals
            if s.name == _LAT_PATH and (s.name, s.source) in valid_by_key
        ),
        key=_source_priority,
    )
    lon_specs = sorted(
        (
            s
            for s in dictionary.signals
            if s.name == _LON_PATH and (s.name, s.source) in valid_by_key
        ),
        key=_source_priority,
    )
    if not lat_specs or not lon_specs:
        raise TelemetryError(
            "VBO export requires valid Vehicle.CurrentLocation.Latitude and Longitude samples"
        )

    lat_key = (lat_specs[0].name, lat_specs[0].source)
    lon_key = (lon_specs[0].name, lon_specs[0].source)
    raw_anchors = _pair_gps_anchors(
        valid_by_key[lat_key], valid_by_key[lon_key], gps_pair_tolerance_ms
    )

    anchors: list[tuple[int, float, float]] = []
    dropped_no_fix = 0
    for anchor in raw_anchors:
        if _is_valid_fix(anchor[0], fix_ts, fix_vals):
            anchors.append(anchor)
        else:
            dropped_no_fix += 1

    if not anchors:
        raise TelemetryError("no valid GPS anchor rows available after fix filtering")

    # Build ordered channel plan: standard channels first, then non-standard channels.
    used_cols: set[str] = {"time", "lat", "long"}
    selected_standard: list[tuple[SignalSpec, _ChannelMapping]] = []
    selected_nonstandard: list[tuple[SignalSpec, _ChannelMapping]] = []
    claimed_keys: set[tuple[str, str]] = {lat_key, lon_key}

    for path, mapping in _STANDARD_MAPPINGS:
        candidates = sorted(
            (
                s
                for s in dictionary.signals
                if s.name == path and (s.name, s.source) in valid_by_key
            ),
            key=_source_priority,
        )
        if candidates:
            chosen = candidates[0]
            claimed_keys.add((chosen.name, chosen.source))
            used_cols.add(mapping.column)
            selected_standard.append((chosen, mapping))

    for spec in dictionary.signals:
        key = (spec.name, spec.source)
        if key in claimed_keys or key not in valid_by_key:
            continue
        if spec.value_kind not in numeric_kinds:
            continue
        imu_map = _NONSTANDARD_IMU_MAPPINGS.get(spec.name)
        if imu_map is not None and imu_map.column not in used_cols:
            used_cols.add(imu_map.column)
            selected_nonstandard.append((spec, imu_map))
        else:
            raw_col = spec.name if spec.name not in used_cols else f"{spec.name}_{spec.source}"
            col = _sanitize_column_name(raw_col, used_cols)
            header = (
                spec.name
                if not any(
                    s.name == spec.name for s, _ in (*selected_standard, *selected_nonstandard)
                )
                else f"{spec.name} ({spec.source})"
            )
            selected_nonstandard.append(
                (
                    spec,
                    _ChannelMapping(
                        header=header,
                        column=col,
                        standard=False,
                        unit=spec.unit,
                        convert=lambda v: v,
                        fmt=_fmt_generic,
                    ),
                )
            )

    # Pre-split timestamps and values for fast ZOH lookup.
    series_index: dict[tuple[str, str], tuple[list[int], list[float], int | None]] = {}
    for spec, _ in (*selected_standard, *selected_nonstandard):
        key = (spec.name, spec.source)
        pairs = valid_by_key[key]
        eff_max_age = max_age_ms if max_age_ms is not None else (spec.max_age_ms or None)
        series_index[key] = ([t for t, _ in pairs], [v for _, v in pairs], eff_max_age)

    standard_headers = ["time", "latitude", "longitude", *(m.header for _, m in selected_standard)]
    nonstandard_headers = [m.header for _, m in selected_nonstandard]
    all_headers = [*standard_headers, *nonstandard_headers]
    all_columns = [
        "time",
        "lat",
        "long",
        *(m.column for _, m in selected_standard),
        *(m.column for _, m in selected_nonstandard),
    ]
    unit_lines = [m.unit for _, m in selected_nonstandard]

    lines: list[str] = [
        _format_created_line(anchors[0][0]),
        "",
        "[header]",
        *all_headers,
        "",
        "[channel units]",
        *unit_lines,
        "",
        "[comments]",
        "Generated by vehicle-profile-tools VBO exporter (valid numeric signals only)",
        f"Vehicle ID: {dictionary.vehicle_id}",
        f"Dictionary Fingerprint: {dictionary.fingerprint.hex()}",
        f"Skipped signals: {len(skipped)}",
        "",
        "[column names]",
        " ".join(all_columns),
        "",
        "[data]",
    ]

    for row_ts, lat_deg, lon_deg in anchors:
        lat_min = lat_deg * 60.0
        lon_min = -(lon_deg * 60.0)  # Racelogic VBO: positive West, negative East.
        row_cells = [
            _format_vbo_time(row_ts),
            _fmt_lat_lon(lat_min),
            _fmt_lat_lon(lon_min),
        ]
        for spec, mapping in (*selected_standard, *selected_nonstandard):
            times, vals, eff_max_age = series_index[(spec.name, spec.source)]
            raw_val = _zoh_lookup(row_ts, times, vals, eff_max_age)
            row_cells.append(mapping.fmt(mapping.convert(raw_val)))
        lines.append(" ".join(row_cells))

    vbo_text = "\r\n".join(lines) + "\r\n"
    report = VboReport(
        row_count=len(anchors),
        standard_channels=tuple(standard_headers),
        nonstandard_channels=tuple(nonstandard_headers),
        dropped_observations=dropped_observations,
        dropped_no_fix_rows=dropped_no_fix,
        skipped_signals=tuple(skipped),
    )
    return vbo_text, report


def export_telemetry_to_vbo(
    input_path: str | Path,
    output_path: str | Path,
    *,
    gps_pair_tolerance_ms: int = 5,
    max_age_ms: int | None = None,
) -> VboReport:
    """Read a .vts or .zip telemetry file and write a Racelogic .vbo file."""
    dictionary, observations = read_telemetry(input_path)
    vbo_text, report = convert_to_vbo(
        dictionary,
        observations,
        gps_pair_tolerance_ms=gps_pair_tolerance_ms,
        max_age_ms=max_age_ms,
    )
    Path(output_path).write_bytes(vbo_text.encode("utf-8"))
    return report
