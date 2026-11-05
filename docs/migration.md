# Migrating profiles

[Overview](../README.md) · [Documentation index](README.md)

## Versioning and migration

Format 2 replaces the keyword-based format 1 profile with packages and canonical VSS property bindings. Use the migration command below and review its unmapped report.

Migration from the [format 1 profile](format-1.md):

| Format 1 | Format 2 |
|---|---|
| `profile.yaml` with sibling DBC files | A package manifest listing documents and DBC files |
| `signals.X.monitor` | `read.signal` on the VSS path for X |
| `queries.X` | `read.query` on the VSS path, or a named query when X has no VSS path |
| `actions.X` | A `write` case when X maps to one VSS actuator, otherwise an action |
| Byte arrays | Hex strings |
| `"*"` | The `*` token |
| `ref: sequences.x` | `call: x` |
| `request_id` / `response_id(s)` | `tx` / `rx` on an endpoint |
| Inline `send: {request_id, request}` | A request-only endpoint |

Keyword names stay usable as aliases on properties and as query and action names. Anything that cannot be mapped goes to `unmapped`.

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

`vprofile migrate OLD -o NEW` reads format 1 and writes a strictly validated package into an empty destination. It preserves DBC files, combines passive and queried bindings on one property, translates shared sequences and wildcards, and maps single-actuator commands to write cases. `LOCK` and `UNLOCK` become `"true"` and `"false"` cases on `Vehicle.Cabin.IsCentralLockEngaged`. Other multi-actuator commands remain actions. Unconverted objects retain their original data and reason in `unmapped`.

Request/response conversion requires an explicit `--framing` declaration:

- `raw`: preserve request bytes and raw response patterns on CAN endpoints.
- `isotp`: requests and response patterns already contain application data.
- `isotp-single-frame`: validate and remove single-frame PCI/padding from requests; response patterns already contain application data. DBC query offsets additionally account for the one-byte raw response header.

No framing is inferred from the first byte. Without the flag, request-only commands and known signals can migrate, while response bindings remain unmapped. A multi-responder endpoint requires `--responder ENDPOINT=HEX`. Physical left/right door names require `--steering-side left|right`.

```sh
vprofile migrate examples/legacy/nissan-versa-1-6 -o /tmp/versa-format2 \
  --framing isotp-single-frame --steering-side left
```

DBC query fields become prefix-relative byte/bit decoders, preserving native Motorola/little-endian layout and scaling. Known spelling aliases such as `R/min` to `rpm` are normalized without numerical conversion; passive bindings with a renamed unit use an inline decoder. Explicit raw enum mappings preserve supported label normalization. Fixed-length VIN and byte/hex queries are supported; byte-array results become uppercase hex strings, recorded in the migration notes.

Unsupported or uncertain inputs stay unmapped: multiplexed DBC declarations, unknown canonical identities, fractional values targeting integer VSS properties, variable-length codecs, generic ASCII trailing-NUL trimming, sequence cycles, and steps that switch endpoints. An unmapped report is work to review, not an active capability.

The [Versa example](../examples/nissan-versa/README.md) is reproduced by `scripts/migrate-versa.py`; `--check` verifies it without editing files. Request/response commands use the declared single-frame conversion, while request-only commands remain raw CAN. No physical vehicle compatibility is claimed.

## Related pages

[Legacy reference](format-1.md) · [Keyword vocabulary](vocabulary.md) · [Authoring guide](authoring-guide.md) · [Validation](validation.md)
