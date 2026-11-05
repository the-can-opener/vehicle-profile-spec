# Changelog

## Unreleased

## 2.1.0

- Absorb the can-opener-js transport contract into channels and endpoints: `bitrate: auto`, `data_bitrate`, CAN FD request defaults with `tx_dl` 8 or 64 and per-endpoint overrides, ISO-TP extended and mixed addressing, and inclusive receive-ID ranges with explicit responder selection.
- Define transport defaults: a missing channel reference is `can0`, an undeclared `can0` is classic CAN at 500000 bit/s, and a declared channel without `bitrate` or `configuration` runs at 500000 bit/s. Resolved output materializes these defaults. `can0` is OBD pins 6 (CAN-H) and 14 (CAN-L); `can1` is pins 3 (CAN-H) and 11 (CAN-L). Host interfaces stay runtime configuration.
- Validate manifest DBC channels, CAN FD only on `canfd` channels, raw frame lengths against the resolved frame format, and addressing only on ISO-TP endpoints.
- Migrate legacy `can.buses`, endpoint `bus`/`extended`/`fd`/`addressing`, inline `bus`/`fd`, monitor `bus`, step `delay_ms` and every declared bus and endpoint; classify batching, retries and per-step timeouts as runtime policy. Legacy bus N becomes channel `canN`.
- Add dual-bus CAN FD and ISO-TP addressing example packages.

## 2.0.0

- Replace keyword-based format 1 with manifest packages and flat VSS 6.1 properties.
- Implement the 0.4.0 reference's named queries/actions and inline writes with acknowledgement semantics.
- Add bounded directory/ZIP loading, typed models, references, catalog checks, composition, fixtures, exports and conservative migration.
- Publish schemas, examples, authoring/validation/migration skills, matching installers and CI checks.
- Retire direct format 1 loading. Uncertain migration mappings remain inactive in `unmapped`.
- Clarify duplicate fixture labels and explicit multi-responder selection. No runtime activation or physical compatibility is claimed.
