# Migrating profiles

[Overview](../README.md) · [Documentation index](README.md)

## Versioning and migration

Format 2 replaces the keyword-based format 1 profile with packages and canonical VSS property bindings. Use the migration command below and review its unmapped report.

Migration from the [format 1 profile](format-1.md), `version: 1` or `version: 1.1`:

| Format 1                              | Format 2                                                              |
| ------------------------------------- | --------------------------------------------------------------------- |
| `profile.yaml` with sibling DBC files | A package manifest listing documents and DBC files                    |
| `signals.X.monitor`                   | `read.signal` on the VSS path for X                                   |
| `queries.X`                           | `read.query` on the VSS path, or a named query when X has no VSS path |
| `actions.X`                           | A `write` case when X maps to one VSS actuator, otherwise an action   |
| `actions.X.values.command` (1.1)      | The `write` case for that command's state on the VSS path for X       |
| `actions."X.command"` (1.1)           | The same as `actions.X.values.command`                                |
| `actions.X.encode` (1.1)              | A `write` whose request has an encoded part, with `constraints`       |
| Byte arrays                           | Hex strings                                                           |
| `"*"`                                 | The `*` token                                                         |
| `ref: sequences.x`                    | `call: x`                                                             |
| `request_id` / `response_id(s)`       | `tx` / `rx` on an endpoint; `{range: [lo, hi]}` entries stay ranges   |
| Inline `send: {request_id, request}`  | A request-only endpoint                                               |
| `can.buses.N` and `bus: N`            | Channel `canN` and `channel: canN`                                    |

Keyword names stay usable as aliases on properties and as query and action names. Anything that cannot be mapped goes to `unmapped`.

### Transport compatibility

Format 2 replaces the can-opener-js profile specification. Every transport declaration of that specification is either a format 2 field or classified here as runtime policy, so nothing is dropped silently.

| Format 1 (can-opener-js)                                    | Format 2                                                 | Notes                                                                                                                          |
| ----------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `can.buses.N.bitrate: <int>`                                | `channels.canN.bitrate: <int>`                           | Nominal rate. Omitted in format 2 means 500000                                                                                 |
| `can.buses.N.bitrate: auto`                                 | `channels.canN.bitrate: auto`                            | Nominal detection only; a failed detection leaves the channel unavailable                                                      |
| `can.buses.N.data_bitrate`                                  | `channels.canN.data_bitrate`                             | The channel becomes `protocol: canfd`                                                                                          |
| `can.buses.N.fd: true` / `{}`                               | `channels.canN.fd: true`                                 | FD requests with 8-byte ISO-TP frames                                                                                          |
| `can.buses.N.fd.isotp.tx_dl`                                | `channels.canN.fd.tx_dl`                                 | `8` or `64`                                                                                                                    |
| `can.buses.N.fd: false`                                     | omitted `fd`                                             | Classic requests                                                                                                               |
| Bus used but not declared                                   | `channels.canN: {protocol: can, configuration: runtime}` | The legacy adapter kept its default timing; the runtime still supplies it                                                      |
| `endpoints.X.bus`                                           | `endpoints.X.channel: canN`                              | Omitted legacy bus 0 becomes `can0`                                                                                            |
| `endpoints.X.extended`                                      | `endpoints.X.id_format: extended`                        | 29-bit CAN IDs                                                                                                                 |
| `endpoints.X.fd`                                            | `endpoints.X.fd`                                         | Same `true`, `false`, or `{tx_dl}` shape                                                                                       |
| `endpoints.X.addressing`                                    | `endpoints.X.addressing`                                 | Addresses become hex bytes, for example `0x12` → `"12"`; requires an ISO-TP framing                                            |
| `endpoints.X.response_ids: [{range}]`                       | `rx: [{range: [lo, hi]}]` plus `responder`               | `--responder X=HEX` selects the responder                                                                                      |
| `signals.X.monitor.bus`                                     | `channel` of the binding                                 | A DBC binds to the single bus its monitored messages use, else `can0`; a signal on another bus becomes an inline frame binding |
| `send: {bus, fd, request_id, request}`                      | Generated request-only endpoint with `channel` and `fd`  |                                                                                                                                |
| Step `delay_ms`                                             | A following `wait_ms` step                               | Only when declared; the legacy 20 ms default is runtime pacing                                                                 |
| Step or query `timeout_ms`                                  | none                                                     | Stays unmapped; format 2 has one `timeout_ms` per endpoint                                                                     |
| `actions.X.batch`                                           | none                                                     | Transport batching is runtime policy; noted in the migrated README                                                             |
| `ECU_WAKE` retries, bus-sleep detection, polling scheduling | none                                                     | Runtime policy. `ECU_WAKE` itself stays an action                                                                              |
| `VehicleTransport` adapter API, BLE protocol                | none                                                     | Outside this standard; see [extensions](extensions.md#configuration-model)                                                     |

Logical channel names identify the OBD connector: `can0` is pins 6 (CAN-H) and 14 (CAN-L), and `can1` is pins 3 (CAN-H) and 11 (CAN-L). A runtime binds each name to the controller wired to those pins, SocketCAN `can0` for pins 6 and 14 by default, and may override that host binding in deployment configuration.

Format 2 structure:

- One root manifest became a package manifest with an ordered document list, composition rules, and `depends`.
- `operations` were replaced by named `queries` and `actions`.
- Write steps live inside the write. `write.sequence`, `completion`, and `verify` were removed; a matched `expect` is the acknowledgement.
- Sequences hold only shared steps and run on the caller's endpoint.
- Endpoints are the ECU target, and VSS `ControlUnit` instance names are not addresses.
- Diagnostics providers are outside the core binding format.

Migration from v0.3:

- Flatten the nested properties tree into exact VSS-path keys.
- Put passive bindings under `read.signal` and active bindings under `read.query`.
- A property may contain both; replace positional alternatives with the explicit acquisition policy.
- Rename passive source kinds to `signal` and keep active source kind `query`.
- Preserve DBC signal names, numeric write constraints, and canonical property semantics.
- Remove any OBDb compatibility/import/parity release requirements.

Pin package, VSS and extension versions independently. Publish schemas, examples and conformance fixtures with each implemented release. Do not present an unsupported feature as working merely because the standard has an extension point for it.

## Implemented migration

`vprofile migrate OLD -o NEW` reads format 1, `version: 1` or `version: 1.1`, and writes a strictly validated package into an empty destination. It preserves DBC files, converts every declared bus and endpoint, combines passive and queried bindings on one property, translates shared sequences and wildcards, and maps single-actuator commands to write cases. `LOCK` and `UNLOCK` become `"true"` and `"false"` cases on `Vehicle.Cabin.IsCentralLockEngaged`. Other multi-actuator commands remain actions. Unconverted objects retain their original data and reason in `unmapped`.

Request/response conversion requires an explicit `--framing` declaration:

- `raw`: preserve request bytes and raw response patterns on CAN endpoints.
- `isotp`: requests and response patterns already contain application data.
- `isotp-single-frame`: validate and remove single-frame PCI/padding from requests; response patterns already contain application data. DBC query offsets additionally account for the one-byte raw response header.

A version 1.1 profile names entities and gives each command its own request. The migrator handles it as follows:

- Each command of `values`, or a flat `ENTITY.command` key, becomes one write case on the entity's VSS actuator. `lock`, `unlock`, `close`, `fold` and `unfold` select the vocabulary target for `locked`, `unlocked`, `closed`, `folded` and `unfolded`. `on`, `off`, `open` and `close` select `true` or `false` on a boolean actuator. Any other command must be an allowed value of the actuator, for example `WIPERS.off`.
- A command with no established target stays unmapped with its request, for example `WIPERS.low`, `CLIMATE.on` and a command on a sensor path such as `ENGINE.on`.
- An entity the vocabulary does not know is vehicle-specific. Each command becomes the named action `ENTITY_COMMAND`, recorded in the migration notes.
- `encode` becomes an encoded request part: `{input: value, type, bytes, endian, scale, offset}`. `min`, `max` and `step` become write `constraints`, which may narrow the VSS domain and never widen it. A vehicle-specific numeric entity becomes an action with an `input_schema` for `value`.
- Format 2 encodes whole bytes. An `encode` field that starts or ends inside a byte stays unmapped. Format 2 also refuses a target that does not encode to a whole number, where the 1.1 runtime rounded it.

No framing is inferred from the first byte. Without the flag, request-only commands and known signals can migrate, while response bindings remain unmapped. A multi-responder endpoint requires `--responder ENDPOINT=HEX`. Physical left/right door names require `--steering-side left|right`.

```sh
vprofile migrate examples/legacy/nissan-versa -o /tmp/versa-format2 \
  --framing isotp-single-frame --steering-side left
```

DBC query fields become prefix-relative byte/bit decoders, preserving native Motorola/little-endian layout and scaling. Known spelling aliases such as `R/min` to `rpm` are normalized without numerical conversion; passive bindings with a renamed unit use an inline decoder. Explicit raw enum mappings preserve supported label normalization. Fixed-length VIN and byte/hex queries are supported; byte-array results become uppercase hex strings, recorded in the migration notes.

Unsupported or uncertain inputs stay unmapped: multiplexed DBC declarations, unknown canonical identities, fractional values targeting integer VSS properties, variable-length codecs, generic ASCII trailing-NUL trimming, sequence cycles, steps that switch endpoints, per-step or per-query timeouts, ISO-TP addressing under `--framing raw`, commands without an established VSS target, bit-level `encode` fields, and invalid bus or endpoint declarations. An unmapped report is work to review, not an active capability.

The [Versa example](../examples/nissan-versa/README.md) is reproduced by `scripts/migrate-versa.py`; `--check` verifies it without editing files. Request/response commands use the declared single-frame conversion, while request-only commands remain raw CAN. No physical vehicle compatibility is claimed.

## Related pages

[Legacy reference](format-1.md) · [Keyword vocabulary](vocabulary.md) · [Authoring guide](authoring-guide.md) · [Validation](validation.md)
