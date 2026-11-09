# Vehicle Profile Standard 2.2

[Overview](#overview) · [Vehicle Signal Specification](#vehicle-signal-specification) · [Quick start](#quick-start) · [Example](#example) · [Specification reference](#specification-reference) · [Guides and resources](#guides-and-resources) · [Development](#development)

## Overview

The Vehicle Profile Standard (format 2) defines how a vehicle exposes data and accepts commands through a portable YAML or JSON package. It binds canonical VSS property paths, such as `Vehicle.Speed`, to vehicle-specific CAN frames, diagnostic queries, DBC signals, and actuator writes.

### Core concepts

| Concept                       | Role in a package                                                                                                                             |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Manifest**                  | Declares package identity, version, VSS release, channels, DBC assets, fixtures, and ordered documents.                                       |
| **Properties**                | Binds canonical VSS paths to passive signals (`read.signal`), active requests (`read.query`), static values (`value`), or commands (`write`). |
| **Endpoints and sources**     | Defines reusable ECU addressing/framing (`endpoints`) and shared signal or query acquisition (`sources`).                                     |
| **Steps and sequences**       | Expresses request bytes, expected response prefixes, waits, and reusable command sequences (`sequences`).                                     |
| **Named queries and actions** | Defines diagnostic reads (`queries`) and state-changing commands (`actions`) that do not map to a single VSS property.                        |
| **Composition**               | Merges ordered documents and overlays with explicit replacement, deletion, and vehicle applicability rules.                                   |

### Runtime model

- **Read vs. write state:** A matched response acknowledges a write (`acknowledged`); it never updates the observed property value. Only a `read` updates observed state.
- **Explicit polling:** Passive frame monitoring and active query polling are separate; polling is never implicit.
- **No implicit permissions:** Package metadata and vehicle selectors describe capability and applicability, not runtime authorization.

## Vehicle Signal Specification

Property identity, datatype, unit, and role (`sensor`, `actuator`, or `attribute`) come from the [COVESA Vehicle Signal Specification (VSS)](https://github.com/COVESA/vehicle_signal_specification). This repository pins **VSS 6.1** in [`catalog/vss-6.1.json`](catalog/vss-6.1.json).

- [VSS paths and semantics](docs/vss.md) — how bindings inherit property roles, units, allowed values, and aliases from the catalog.
- [Catalog provenance](catalog/README.md) — how the pinned VSS 6.1 export is built and where it departs from upstream.
- [Keyword vocabulary](docs/vocabulary.md) — how legacy format 1 capability keywords map to VSS 6.1 paths, units, and write targets.

## Quick start

Install the `vprofile` CLI and validate an example package:

```sh
uv sync --project tools
uv run --project tools vprofile export json --strict --package examples/universal-obd
```

Search the pinned VSS 6.1 catalog by keyword and role:

```sh
uv run --project tools vprofile vss search temperature --role actuator
uv run --project tools vprofile vss show Vehicle.Cabin.IsCentralLockEngaged
```

Build a deterministic `.zip` package and verify the archive:

```sh
uv run --project tools vprofile compose --package examples/universal-obd -o /tmp/obd.zip
uv run --project tools vprofile compose --verify /tmp/obd.zip
```

To build a new package from scratch, follow the [authoring guide](docs/authoring-guide.md).

## Example

This illustrative single-file package omits `documents`, so `vehicle.yaml` serves as both the manifest and the binding document (`DriverSide` assumes left-hand drive):

- `Vehicle.Cabin.Door.Row1.DriverSide.IsOpen` (`FRONT_LEFT_DOOR_OPEN`) — read-only sensor decoded from bit 0 of CAN frame `60D` (`0` = `false`, `1` = `true`).
- `Vehicle.Cabin.IsCentralLockEngaged` (`LOCKED`, `LOCK`, `UNLOCK`) — actuator with a passive state `read` on bit 1 of CAN frame `60D` and a `write` that sends lock (`"true"`) and unlock (`"false"`) commands to the `body` ISO-TP endpoint. A `70 38` response acknowledges the command without mutating the observed state.

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

### Checked-in example packages

| Package               | Highlights                                                                                     | Files                                                                                                                                                       |
| --------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Universal OBD**     | Mode `01`/`09` queries (`Vehicle.Speed`, `RPM`, `VIN`) and a named PID bitmap query            | [vehicle.yaml](examples/universal-obd/vehicle.yaml) · [fixtures.yaml](examples/universal-obd/fixtures.yaml)                                                 |
| **Synthetic HVAC**    | Shared signal sources, passive acquisition, and a scaled numeric actuator write                | [README](examples/hvac-synthetic/README.md) · [vehicle.yaml](examples/hvac-synthetic/vehicle.yaml) · [fixtures.yaml](examples/hvac-synthetic/fixtures.yaml) |
| **Nissan Versa**      | Split documents, DBC signals, shared diagnostic sequences, horn cases, and central lock writes | [README](examples/nissan-versa/README.md) · [vehicle.yaml](examples/nissan-versa/vehicle.yaml)                                                              |
| **Dual-bus CAN FD**   | Two channels, `auto` bitrate, CAN FD request defaults and overrides, and a responder range     | [README](examples/canfd-dual-bus/README.md) · [vehicle.yaml](examples/canfd-dual-bus/vehicle.yaml) · [fixtures.yaml](examples/canfd-dual-bus/fixtures.yaml) |
| **ISO-TP addressing** | BMW-style extended and mixed addressing on the default `can0` channel                          | [README](examples/bmw-addressing/README.md) · [vehicle.yaml](examples/bmw-addressing/vehicle.yaml) · [fixtures.yaml](examples/bmw-addressing/fixtures.yaml) |

Examples and fixtures illustrate the format. Validation performs no vehicle I/O and does not prove physical compatibility.

## Specification reference

The [documentation index](docs/README.md) is the maintained standard:

| Document                                           | Scope                                                                            |
| -------------------------------------------------- | -------------------------------------------------------------------------------- |
| [Package and file format](docs/package.md)         | Directory and ZIP layout, safe paths, JSON-compatible YAML, and asset limits     |
| [Manifest and applicability](docs/manifest.md)     | Package identity, versions, document order, DBC assets, and vehicle selectors    |
| [Properties and bindings](docs/document.md)        | Reads, shared sources, writes, endpoints, steps, sequences, queries, and actions |
| [VSS paths and semantics](docs/vss.md)             | Canonical identities, roles, units, aliases, and catalog resolution              |
| [Decoding and encoding](docs/decoding.md)          | Byte and bit extraction, scaling, enums, and request encoding                    |
| [DBC assets](docs/dbc.md)                          | Signal layout and the boundary between DBC data and binding behavior             |
| [Composition and overlays](docs/composition.md)    | Ordered replacement, deletion, applicability, and conflict rules                 |
| [Extensions and configuration](docs/extensions.md) | Versioned requirements and non-VSS configuration                                 |
| [Fixtures](docs/fixtures.md)                       | Positive and negative test cases and expected outcomes                           |

## Guides and resources

- **Authoring and validation:** [Authoring guide](docs/authoring-guide.md) · [Validation and CLI](docs/validation.md) · [Error codes](skills/validating-vehicle-profiles/error-codes.md)
- **Migration:** [Migration guide](docs/migration.md) · [Keyword vocabulary](docs/vocabulary.md) · [Format 1 reference (retired)](docs/format-1.md)
- **JSON schemas:** [Manifest schema](schemas/manifest.schema.json) · [Document schema](schemas/document.schema.json) · [Fixture schema](schemas/fixture.schema.json)
- **Catalog and skills:** [Pinned VSS catalog](catalog/README.md) · [Agent skills](skills/README.md) · [Changelog](CHANGELOG.md)

## Development

```sh
make mandatory_targets
make clean
```

`make mandatory_targets` runs the test suite, linter, type checker, generated-file drift checks, example package validations, and wheel resource checks. `make clean` removes build and test caches while retaining the development environment and checked-in artifacts.

Runtime implementations and BLE interfaces are outside this repository's scope.
