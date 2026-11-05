# Extensions and configuration

[Overview](../README.md) · [Documentation index](README.md)

## Extension mechanism

`requires` is a flat map from publisher-qualified feature IDs to exact versions. The example ID below is a proposed extension contract, not an existing installed package. `extensions` maps those IDs to extension-owned payloads.

```yaml
requires:
  org.canopener.configuration: "0.1.0"

extensions:
  org.canopener.configuration:
    parameters:
      auto-relock-delay:
        datatype: uint16
        unit: s
        constraints: {min: 0, max: 120, step: 5}
        read: AUTO_RELOCK_DELAY
        write: SET_AUTO_RELOCK_DELAY
        persistence: ecu
```

This fragment illustrates the reserved extension design; it is not an executable configuration implementation. `read` names a query and `write` names an action; both must exist. Publishing extension version 0.1.0 requires its own schema, semantics, provider/codec contract, and tests. Do not declare it supported merely because its payload can be parsed.

Rules:

1. Unknown extension payloads may be preserved for tooling but MUST NOT execute or expose capabilities.
2. Every behavior-bearing extension MUST appear in `requires`.
3. If a required feature/version is unsupported, activation fails explicitly. A tool may still inspect core data, but must report the package as not fully activatable.
4. Extension schemas cannot redefine core semantics or override VSS property types.
5. Publishers must define deterministic versioning and migration, input/output errors, resource limits, and conformance tests.
6. The same versioned provider may serve property reads, queries, actions, or configuration read/write without duplicating protocol definitions.
7. Capability discovery reports provider support and runtime availability separately.

## Configuration model

Separate three categories:

| Category | Location | Example |
|---|---|---|
| Connection/runtime configuration | channels/endpoints/runtime | bitrate, CAN FD, addressing, timeout; the mapping from a channel name to a host interface, transport batching and wake retries are runtime |
| Vehicle property already represented by VSS | properties + write | HVAC setting |
| Persistent vehicle parameter without a matching VSS property | configuration extension | OEM auto-relock delay |

Do not duplicate a VSS actuator in a custom configuration registry. VSS attributes describe characteristics and are not a generic vehicle-coding interface. For a persistent non-VSS parameter, the extension must define datatype, unit, range, permitted values, readback, scope, persistence, defaults if known, required ignition/session state, and whether activation requires restart.

Batch changes must declare atomicity. If not atomic, return per-parameter outcomes and partial success. Do not promise rollback unless verified undo behavior exists. Readback verifies stored/applied state as appropriate; saving an intended setting locally does not prove ECU persistence. Configuration extension contracts must distinguish pending, stored, and active values when they differ.

## Related pages

[VSS properties](vss.md) · [Queries and actions](document.md#queries-and-actions) · [Validation](validation.md)
