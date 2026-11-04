# Vehicle Profile Specification — format 2

Vehicle packages bind flat COVESA VSS property paths to CAN signals, queries and actuator writes. Named queries and actions cover capabilities without a VSS path. This repository implements the [Vehicle Binding Specification 0.4.0 draft](Vehicle_BInding_Standardv0.4.0.md) with a Python validator, pinned VSS 6.1 catalog, schemas, examples and agent skills.

Format 1 is retired. Use `vprofile migrate` and review its `unmapped` report. The [original format 1 specification](docs/format-1.md) remains available for migration.

## Quick start

```sh
uv sync --project tools
uv run --project tools vprofile export json --strict --package examples/universal-obd
uv run --project tools vprofile vss search temperature --role actuator
uv run --project tools vprofile compose --package examples/universal-obd -o /tmp/obd.zip
uv run --project tools vprofile compose --verify /tmp/obd.zip
make mandatory_targets
make clean
```

A minimal single-file `vehicle.yaml`:

```yaml
manifest: 1
format: 2
id: org.example.obd
version: 1.0.0
name: Engine speed query
vss: "6.1"
channels:
  vehicle: {protocol: can, configuration: runtime}
endpoints:
  engine:
    channel: vehicle
    protocol: isotp
    tx: "7E0"
    rx: ["7E8"]
    id_format: standard
    timeout_ms: 500
properties:
  Vehicle.Speed:
    aliases: [SPEED]
    read:
      query:
        endpoint: engine
        request: "01 0D"
        response: {prefix: "41 0D", min_data_bytes: 1}
        decode: {byte: 0, bytes: 1, type: uint}
```

A write acknowledgement does not update the observed property value. Only reads do. Polling is explicit; a profile cannot grant runtime permissions. Validation performs no vehicle I/O and does not prove vehicle compatibility.

## Documentation

- [Package safety](docs/package.md), [manifest](docs/manifest.md), [document grammar and runtime contracts](docs/document.md)
- [Decoding and encoding](docs/decoding.md), [composition](docs/composition.md), [VSS identity and roles](docs/vss.md), [catalog provenance](catalog/README.md)
- [Extensions](docs/extensions.md), [fixtures](docs/fixtures.md), [validation and CLI](docs/validation.md)
- [DBC](docs/dbc.md), [authoring guide](docs/authoring-guide.md), [migration](docs/migration.md)
- [Agent skill installation](skills/README.md), [schemas](schemas), [examples](examples), [changelog](CHANGELOG.md)

The original implementation plan is tracked in [vehicle_profile_format_2_6ee96dce.plan.md](vehicle_profile_format_2_6ee96dce.plan.md). Local clarifications are documented: fixture descriptions use `label`, and multi-responder endpoints require an explicit `responder`. Diagnostics/configuration providers and can-opener-js runtime changes remain outside this implementation.

The implementation is not yet a complete conformance validator. Remaining semantic/schema checks and coverage are listed in the [implementation plan](vehicle_profile_format_2_6ee96dce.plan.md#remaining-work-at-wrap-up).
