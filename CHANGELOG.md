# Changelog

## Unreleased

- `vprofile migrate` reads `version: 1.1` profiles as well as `version: 1`. Each command of an entity's `values`, or a flat `ENTITY.command` key, becomes a write case on the entity's VSS actuator; commands of a vehicle-specific entity become `ENTITY_COMMAND` actions. A whole-byte `encode` becomes an encoded request part with write `constraints`, or an action `input_schema`. Commands without an established target and bit-level `encode` fields stay unmapped.

## 2.2.0

- Harmonize `docs/vocabulary.yaml` and `docs/vocabulary.md` with the `can-opener-js` 1.1 entity/present-tense keyword registry, and separate legacy Format 1 predicate/past-tense/verb-specific variants into a `Legacy keywords` section.
- Add `ACCELERATOR_PEDAL`, `BRAKE_PEDAL`, and `CLUTCH_PEDAL` aliases for pedal travel. `Vehicle.Chassis.Clutch.PedalPosition` is a local catalog sensor; clutch engagement stays `Vehicle.Powertrain.Transmission.ClutchEngagement`.

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
