# VBO export

[Overview](../README.md) · [Documentation index](README.md) · [Compressed telemetry](telemetry.md)

Racelogic `.vbo` is a widely supported lap-session text format used by VBOX Tools, RaceChrono, Dragy·Lap, and RaceBox. Because `.vbo` is a fixed-column numeric log, it cannot carry non-numeric signals, per-sample quality flags, or vehicle commands. `vprofile telemetry to-vbo` exports **valid numeric signals only** from a `.vts` or `.zip` telemetry session into a compliant CRLF-terminated `.vbo` file.

## Valid-only filtering

Before building rows, the converter applies strict filtering:

1. **Quality filter:** Only observations with `quality == VALID` are kept. `STALE`, `INVALID`, and `UNAVAILABLE` observations are dropped.
2. **Type filter:** Only numeric scalar signals (`INT`, `UINT`, `FLOAT`) are eligible for `.vbo` columns. Booleans, strings, enums, and non-numeric queries are excluded and reported in the conversion summary.
3. **GNSS fix filter:** If `Vehicle.CurrentLocation.GNSSReceiver.FixType` is present, GPS samples at timestamps where the latest fix status indicates no fix (`NONE`, `NO_FIX`, `INVALID`, or `0`) are excluded from row generation.

## Row alignment (GPS-anchored zero-order hold)

`.vbo` requires every channel to share one timestamp per row, while vehicle telemetry combines heterogeneous rates (e.g. 25 Hz GNSS, 100 Hz IMU, 10 Hz CAN).

- **Anchor timestamps:** Output rows are anchored on valid pairs of `Vehicle.CurrentLocation.Latitude` and `Vehicle.CurrentLocation.Longitude`. Each observation's effective timestamp is `observed_at` when present, otherwise `received_at`. Latitude and longitude observations within the pairing tolerance (default `5 ms`) form one GPS row.
- **Zero-order hold (ZOH):** For every other eligible numeric channel, the converter selects the most recent `VALID` sample at or before the row timestamp.
- **Staleness cutoff:** When a channel declares `max_age_ms` (or a CLI override is provided), a carried value older than that bound is not held past expiry.

## Channel mapping, units, and sign conventions

### Standard VBO channels

Standard channels use Racelogic's fixed header names and implicit units (they do not appear in `[channel units]`):

| VSS 6.1 path | VBO header | Column name | Conversion |
|---|---|---|---|
| *(row timestamp)* | `time` | `time` | UTC `HHMMSS.sss` (session date in file header) |
| `Vehicle.CurrentLocation.Latitude` | `latitude` | `lat` | `degrees * 60` (`MMMMM.MMMMM`, `+` North / `-` South) |
| `Vehicle.CurrentLocation.Longitude` | `longitude` | `long` | `-(degrees * 60)` (`MMMMM.MMMMM`, **`+` West / `-` East**) |
| `Vehicle.Speed` | `velocity kmh` | `velocity` | `km/h` (direct) |
| `Vehicle.CurrentLocation.Heading` | `heading` | `heading` | `degrees` (`0` = North, `90` = East) |
| `Vehicle.CurrentLocation.Altitude` | `height` | `height` | `m` (direct) |
| `Vehicle.Acceleration.Longitudinal` | `long accel g` | `longacc` | `m/s^2 / 9.80665` (`+` forward) |
| `Vehicle.Acceleration.Lateral` | `lat accel g` | `latacc` | `m/s^2 / 9.80665` (`+` left) |
| `Vehicle.AngularVelocity.Yaw` | `yaw rate deg/s` | `yaw_rate` | `-yaw` (`degrees/s`, negated: ISO 8855 CCW+ to Racelogic CW+) |

### Non-standard IMU and vehicle channels

Additional valid numeric channels are written after the standard channels with their unit in `[channel units]` and a space-free identifier in `[column names]`:

| VSS 6.1 path | VBO header | Unit | Conversion |
|---|---|---|---|
| `Vehicle.Acceleration.Vertical` | `Z-Acceleration` | `g` | `m/s^2 / 9.80665` (`+` upward) |
| `Vehicle.AngularVelocity.Pitch` | `PitchRate` | `deg/s` | `degrees/s` (`-` nose down) |
| `Vehicle.AngularVelocity.Roll` | `RollRate` | `deg/s` | `-roll` (`degrees/s`, Racelogic sign convention) |
| Any other valid numeric VSS property or query | Canonical name | Catalog/query unit | Direct numeric value (sanitized column name, e.g. `Vehicle_Powertrain_CombustionEngine_Speed`) |

## File layout

Generated `.vbo` files use UTF-8 encoding with CRLF (`\r\n`) line endings and blank lines between sections:

- `File created on DD/MM/YYYY at HH:MM:SS`
- `[header]` — one channel name per line
- `[channel units]` — one unit line per non-standard channel
- `[comments]` — generator note, `vehicle_id`, dictionary fingerprint, and skipped-channel summary
- `[column names]` — single space-separated line matching `[header]`
- `[data]` — one space-separated numeric row per valid GPS anchor timestamp

## CLI usage

```sh
uv run --project tools vprofile telemetry to-vbo session.zip -o session.vbo
```

The command prints a JSON conversion report listing the exported row count, included channels, and skipped signals (with reasons such as `non_numeric`, `no_valid_samples`, or `fix_invalid`).

## Related pages

[Compressed telemetry protobuf](telemetry.md) · [VSS paths and semantics](vss.md)
