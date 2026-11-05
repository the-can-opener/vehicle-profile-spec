# Vehicle Profile Standard — format 2

[Overview](#overview) · [Vehicle Signal Specification](#vehicle-signal-specification) · [Specification reference](#specification-reference) · [Documentation](#documentation) · [Quick start](#quick-start) · [Example](#example) · [Development](#development)

## Overview

This standard describes how a vehicle exposes data and accepts commands through a portable YAML or JSON package. It binds canonical VSS paths, such as `Vehicle.Speed`, to vehicle-specific signals, requests and actuator writes.

A package contains a manifest and explicitly listed documents, DBC assets and fixtures. The main concepts are:

- **Properties:** canonical VSS paths with passive signals, active queries, static attributes or actuator writes.
- **Endpoints and sources:** reusable addressing and acquisition definitions.
- **Steps and sequences:** requests, expected responses, waits and shared command steps.
- **Named queries and actions:** capabilities that do not map to a single VSS property.
- **Composition:** ordered documents and overlays with explicit replacement and applicability rules.

A matched response acknowledges a write; it does not update the observed property value. Only a read does. Polling is explicit, and package metadata does not grant runtime permissions.

This repository includes the standard, JSON schemas, a pinned VSS 6.1 catalog, the `vprofile` Python tooling, examples and agent skills. Format 1 is retired; the [migration guide](docs/migration.md) explains conversion and unmapped records.

## Vehicle Signal Specification

Property identity comes from the [COVESA Vehicle Signal Specification (VSS)](https://github.com/COVESA/vehicle_signal_specification). This repository pins VSS 6.1. [Path semantics](docs/vss.md) describe how a binding uses that catalog, and [catalog provenance](catalog/README.md) records the export and the local departures from upstream.

## Specification reference

The [documentation index](docs/README.md) is the maintained standard. These pages define the format:

- [Package and file format](docs/package.md) — directory and ZIP layout, safe paths, and asset limits.
- [Manifest and applicability](docs/manifest.md) — package identity, versions, document order, DBC assets, and vehicle selectors.
- [Properties and bindings](docs/document.md) — reads, shared sources, writes, endpoints, steps, queries, and actions.
- [VSS paths and semantics](docs/vss.md) — canonical identities, roles, aliases, and catalog resolution.
- [Decoding and encoding](docs/decoding.md) — byte and bit extraction, scaling, enums, and request encoding.
- [DBC assets](docs/dbc.md) — signal layout and the boundary between DBC data and binding behavior.
- [Composition and overlays](docs/composition.md) — ordered replacement, deletion, applicability, and conflicts.
- [Extensions and configuration](docs/extensions.md) — versioned requirements and non-VSS configuration.
- [Fixtures](docs/fixtures.md) — positive and negative inputs and expected outcomes.

Machine-readable contracts: [manifest schema](schemas/manifest.schema.json), [document schema](schemas/document.schema.json), and [fixture schema](schemas/fixture.schema.json).

## Documentation

- **Get started:** [authoring guide](docs/authoring-guide.md), [validation and CLI](docs/validation.md), [migration](docs/migration.md).
- **Resources:** [catalog provenance](catalog/README.md), [keyword vocabulary](docs/vocabulary.md), [error codes](skills/validating-vehicle-profiles/error-codes.md), [agent skills](skills/README.md).

## Quick start

Install the tooling and validate an example:

```sh
uv sync --project tools
uv run --project tools vprofile export json --strict --package examples/universal-obd
uv run --project tools vprofile vss search temperature --role actuator
```

Package a validated profile and verify the archive:

```sh
uv run --project tools vprofile compose --package examples/universal-obd -o /tmp/obd.zip
uv run --project tools vprofile compose --verify /tmp/obd.zip
```

To write your own profile, follow the [authoring guide](docs/authoring-guide.md).

## Example

This single-file package is illustrative. The frame and request bytes are not a vehicle mapping. `documents` is omitted, so the file is both the manifest and the only binding document.

`Vehicle.Cabin.Door.Row1.DriverSide.IsOpen` is a read-only state. Bit 0 of CAN `60D` is the observed door: `0` is closed and `1` is open. `Vehicle.Cabin.IsCentralLockEngaged` has both a read and a write. Bit 1 is the observed lock state (`LOCKED`). The `"true"` case is `LOCK` and the `"false"` case is `UNLOCK`. A matching `70 38` response acknowledges the command. It does not change the observed value; only the read does. `DriverSide` assumes left-hand drive.

```yaml
manifest: 1
format: 2
id: org.example.locks
version: 2.0.0
name: Illustrative lock state, read, and write
vss: "6.1"
channels:
  vehicle:
    protocol: can
    configuration: runtime
endpoints:
  body:
    channel: vehicle
    protocol: isotp
    tx: "745"
    rx:
      - "765"
    id_format: standard
    timeout_ms: 500
properties:
  Vehicle.Cabin.Door.Row1.DriverSide.IsOpen:
    aliases:
      - FRONT_LEFT_DOOR_OPEN
    read:
      signal:
        channel: vehicle
        id: "60D"
        id_format: standard
        length: 1
        decode:
          start_bit: 0
          bits: 1
          bit_order: lsb0
          type: uint
          enum:
            "0": false
            "1": true
  Vehicle.Cabin.IsCentralLockEngaged:
    aliases:
      - LOCKED
      - LOCK
      - UNLOCK
    read:
      signal:
        channel: vehicle
        id: "60D"
        id_format: standard
        length: 1
        decode:
          start_bit: 1
          bits: 1
          bit_order: lsb0
          type: uint
          enum:
            "0": false
            "1": true
    write:
      cases:
        "true":
          endpoint: body
          request: "30 38 00 01"
          expect:
            prefix: "70 38"
        "false":
          endpoint: body
          request: "30 38 00 02"
          expect:
            prefix: "70 38"
```

Checked-in packages:

- [Universal OBD](examples/universal-obd/vehicle.yaml) — property queries, VIN, and a named PID query; [fixtures](examples/universal-obd/fixtures.yaml).
- [Synthetic HVAC](examples/hvac-synthetic/README.md) — shared reads, passive acquisition, and a numeric write; [package](examples/hvac-synthetic/vehicle.yaml).
- [Nissan Versa migration](examples/nissan-versa/README.md) — split documents, horn cases, and an all-door lock write.

Examples and fixtures illustrate the format. Validation performs no vehicle I/O and does not prove physical compatibility.

## Development

```sh
make mandatory_targets
make clean
```

The acceptance target checks tests, lint, types, generated files, example packages and wheel resources. Cleanup retains the development environment and maintained artifacts.

See the [changelog](CHANGELOG.md), [validation limits](docs/validation.md#remaining-validation-work) and [remaining implementation plan](vehicle_profile_format_2_6ee96dce.plan.md#remaining-work-at-wrap-up). Runtime implementations and BLE interfaces are outside this repository's standard/tooling scope.
