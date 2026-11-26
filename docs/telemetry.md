# Compressed telemetry protobuf

[Overview](../README.md) · [Documentation index](README.md) · [Runtime results](document.md#runtime-results-and-discovery) · [VBO export](vbo-export.md)

The Vehicle Profile Standard defines runtime observation behavior, not a required wire protocol. This page specifies an optional, compact protobuf encoding for recording and streaming those observations—both vehicle-bus reads and external host sensors such as GNSS receivers and IMUs.

The schema lives in [`proto/vehicle_telemetry.proto`](../proto/vehicle_telemetry.proto) (`package vehicle.telemetry.v1`).

## Scope and future control

This format carries **observations only**: canonical VSS properties and named queries, with value, unit, source, acquisition kind, receipt time, optional measurement time, clock domain, monotonic sequence, and quality (`VALID`, `STALE`, `INVALID`, `UNAVAILABLE`).

Actuator writes (`set`) and named commands (`invoke`) are intentionally separate. `Frame` reserves field numbers `10` through `19` for a future companion control schema (`Command` and `Execution`). Consistent with [runtime semantics](document.md#runtime-results-and-discovery), a write acknowledgement is never encoded as an observation.

## Wire structure

A telemetry stream is a sequence of `Frame` messages:

1. A **`Dictionary`** frame sent once per session. It maps dense `uint32` signal IDs to static metadata so strings never repeat per sample, and carries a SHA-256 `fingerprint` over its canonical contents.
2. One or more **`Batch`** frames. Every batch echoes `dictionary_fingerprint`; decoders MUST reject a batch whose fingerprint does not match the active dictionary.

### Dictionary and host signals

Each `SignalSpec` in `Dictionary.signals` declares:

| Field | Meaning |
|---|---|
| `id` | Dense `uint32` identifier unique within the dictionary |
| `name` | Canonical VSS path (e.g. `Vehicle.Speed`) or named query |
| `name_kind` | `PROPERTY` or `QUERY` |
| `unit` | Canonical VSS catalog or query unit; empty if unitless |
| `value_kind` | `BOOL`, `INT`, `UINT`, `FLOAT`, or `STRING` |
| `source` | Acquisition source label (e.g. `can0:60D`, `query:engine`, `host.gnss`, `host.imu`) |
| `acquisition` | `SIGNAL`, `QUERY`, `STATIC`, or `HOST` |
| `clock_domain` | Clock reference label (e.g. `host-utc`, `gnss-utc`, `ecu-monotonic`) |
| `quantization` | Optional fixed-point grid `origin` + `scale` (`value = origin + step * scale`) |
| `constraints` | Optional numeric `min`, `max`, `step` in canonical units |
| `max_age_ms` | Optional freshness bound from the profile (`0` = unspecified) |

When building a dictionary from a composed vehicle profile package:

- `unit` and `value_kind` come from the pinned VSS 6.1 catalog (or the query declaration).
- Numeric `read.constraints` populate `constraints`, and a declared `step` supplies `quantization` (`origin = min` or `0`, `scale = step`).

External host sensors (phone GPS, Dragy, RaceBox, or an external IMU) are not CAN bindings in the vehicle package. They are declared in the dictionary with `acquisition = HOST`, standard VSS 6.1 paths, and canonical catalog units:

| Host signal | VSS 6.1 path | Unit | Default grid scale |
|---|---|---|---|
| Latitude | `Vehicle.CurrentLocation.Latitude` | `degrees` | `1e-7` |
| Longitude | `Vehicle.CurrentLocation.Longitude` | `degrees` | `1e-7` |
| Altitude | `Vehicle.CurrentLocation.Altitude` | `m` | `1e-3` |
| Heading | `Vehicle.CurrentLocation.Heading` | `degrees` | `1e-2` |
| Horizontal / vertical accuracy | `Vehicle.CurrentLocation.{Horizontal,Vertical}Accuracy` | `m` | `1e-3` |
| GNSS fix type | `Vehicle.CurrentLocation.GNSSReceiver.FixType` | *(none)* | *(string)* |
| Longitudinal / lateral / vertical acceleration | `Vehicle.Acceleration.{Longitudinal,Lateral,Vertical}` | `m/s^2` | `1e-3` |
| Roll / pitch / yaw rate | `Vehicle.AngularVelocity.{Roll,Pitch,Yaw}` | `degrees/s` | `1e-2` |
| Roll / pitch / yaw attitude | `Vehicle.Orientation.{Roll,Pitch,Yaw}` | `degrees` | `1e-2` |

Host IMU readings MUST be rotated into the ISO 8855 vehicle frame (X forward, Y left, Z up) and converted to `m/s^2` and `degrees/s` before encoding.

### Columnar `Batch` and `Series` compression

Grouping samples by signal (`Series`) rather than interleaving heterogeneous records lets both protobuf varints and outer `zlib`/`zip` compression collapse repeated values and steady intervals:

- **Delta-of-delta receipt timestamps:** `Batch.base_received_ms` sets the batch origin in Unix milliseconds. Each `Series` stores `first_received_delta_ms`, `first_interval_ms`, and packed `sint64` second deltas (`received_dod_ms`). Steady 10–100 Hz sensors produce mostly `0` and `±1` single-byte entries.
- **Optional measurement timestamps (`observed_at`):** Stored as signed millisecond offsets from each sample's `received_at` (`observed_offset_ms`), with an optional bitset (`observed_present_bits`) when only some samples carry measurement time. When `has_observed_at` is `false`, `observed_at` decodes as absent; receipt time MUST NOT be fabricated as measurement time.
- **Quantized deltas + RLE (`QuantizedDeltas`):** Numbers on a quantization grid (or integer signals) are stored as `first_step` plus packed ZigZag `sint64` deltas (`step_deltas`). Repeated values (`0`) and small changes (`|Δ| <= 63`) encode as 1 byte. When runs of identical values occur, optional `run_lengths` RLE-encodes consecutive repeats.
- **Booleans (`BoolRuns`) and strings (`StringRuns`):** Booleans encode as `initial_value` plus alternating `run_lengths`. Strings encode as unique run values plus optional `run_lengths`. Unquantized floats use packed `double` (`RawDoubles`), also with optional `run_lengths`.
- **Quality (`uniform_quality` or `quality_runs`):** All-`VALID` series store a single enum; mixed series store RLE quality runs.
- **Invalid and off-grid samples:** Consistent with [decoding constraints](document.md#passive-signals-and-active-queries), out-of-range or off-grid observations MUST NOT be clamped or silently rounded. The encoder records them with `quality = INVALID` and no value.
- **Optional emit-on-change with heartbeat:** Encoders MAY suppress consecutive identical values (within the signal's quantization grid) while still emitting a sample whenever `max_age_ms` elapses. Non-contiguous sequence numbers are preserved via `sequence_deltas`.

## Container formats (`.vts` and `.zip`)

### Framed stream (`.vts`)

A `.vts` file is crash-safe and streamable:

```text
+--------+-------+----------+-----------------+-------+----------+-----------------+
| "VTS1" | flags | len (BE) | Frame payload   | flags | len (BE) | Frame payload   | ...
| 4 B    | 1 B   | 4 B      | len bytes       | 1 B   | 4 B      | len bytes       |
+--------+-------+----------+-----------------+-------+----------+-----------------+
```

- `flags = 0x00`: raw serialized `vehicle.telemetry.v1.Frame`.
- `flags = 0x01`: `zlib`-compressed `vehicle.telemetry.v1.Frame`.

Each flushed batch record is independently decodable.

### Whole-session archive (`.zip`)

For archival or upload after a drive, a session MAY be wrapped in a standard `ZIP_DEFLATED` `.zip` container containing:

- `session.vts` — raw-framed (`flags = 0x00`) `.vts` stream so the outer ZIP compressor sees the full session dictionary without double compression.
- `manifest.json` — session summary (`format`, `vehicle_id`, `dictionary_fingerprint`, `profile_id`, `profile_version`, `vss_release`, `batch_count`, `sample_count`, `start_received_ms`, `end_received_ms`, and `signals`).

## CLI reference

The `vprofile telemetry` commands work offline on JSONL observation files and `.vts`/`.zip` archives (no bus I/O):

```sh
# Pack observation JSONL using a vehicle profile plus host GNSS/IMU presets
uv run --project tools vprofile telemetry pack observations.jsonl -o session.vts --package examples/universal-obd --host-sensors

# Pack as a whole-session ZIP archive with emit-on-change suppression
uv run --project tools vprofile telemetry pack observations.jsonl -o session.zip --compression zip --emit-on-change

# Unpack back to JSONL observations
uv run --project tools vprofile telemetry unpack session.zip -o unpacked.jsonl

# Inspect dictionary, sample counts, and compression summary
uv run --project tools vprofile telemetry inspect session.zip

# Export valid numeric signals to Racelogic .vbo
uv run --project tools vprofile telemetry to-vbo session.zip -o session.vbo
```

## Related pages

[Runtime results and discovery](document.md#runtime-results-and-discovery) · [VBO export](vbo-export.md) · [VSS paths and semantics](vss.md)
