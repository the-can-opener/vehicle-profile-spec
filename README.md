# Vehicle Profile Standard — format 2

[Overview](#overview) · [Documentation](#documentation) · [Quick start](#quick-start) · [Examples](#examples) · [Development](#development)

## Overview

This standard describes how a vehicle exposes data and accepts commands through a portable YAML or JSON package. It binds canonical COVESA VSS paths, such as `Vehicle.Speed`, to vehicle-specific signals, requests and actuator writes.

A package contains a manifest and explicitly listed documents, DBC assets and fixtures. The main concepts are:

- **Properties:** canonical VSS paths with passive signals, active queries, static attributes or actuator writes.
- **Endpoints and sources:** reusable addressing and acquisition definitions.
- **Steps and sequences:** requests, expected responses, waits and shared command steps.
- **Named queries and actions:** capabilities that do not map to a single VSS property.
- **Composition:** ordered documents and overlays with explicit replacement and applicability rules.

A matched response acknowledges a write; it does not update the observed property value. Only a read does. Polling is explicit, and package metadata does not grant runtime permissions.

This repository includes the standard, JSON schemas, a pinned VSS 6.1 catalog, the `vprofile` Python tooling, examples and agent skills. Format 1 is retired; the [migration guide](docs/migration.md) explains conversion and unmapped records.

## Documentation

Use the **[documentation index](docs/README.md)** to browse the complete standard. Each topic links back to the index and to related pages.

- **Get started:** [authoring guide](docs/authoring-guide.md), [validation and CLI](docs/validation.md), [migration](docs/migration.md).
- **Package structure:** [file format and safety](docs/package.md), [manifest and applicability](docs/manifest.md), [composition and overlays](docs/composition.md).
- **Bindings:** [properties, reads and writes](docs/document.md), [VSS semantics](docs/vss.md), [decoding and encoding](docs/decoding.md), [DBC assets](docs/dbc.md).
- **Conformance:** [fixtures](docs/fixtures.md), [extensions](docs/extensions.md), [schemas](docs/README.md#examples-and-resources), [error codes](skills/validating-vehicle-profiles/error-codes.md).
- **Resources:** [catalog provenance](catalog/README.md), [keyword vocabulary](docs/vocabulary.md), [agent skills](skills/README.md).

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

To write your own profile, follow the [authoring guide](docs/authoring-guide.md). The [manifest reference](docs/manifest.md) and [binding reference](docs/document.md) include YAML and JSON examples.

## Examples

- [Universal OBD package](examples/universal-obd/vehicle.yaml) — property queries, VIN and a named PID query; [fixtures](examples/universal-obd/fixtures.yaml).
- [Synthetic HVAC](examples/hvac-synthetic/README.md) — shared reads, passive acquisition and a numeric write; [package](examples/hvac-synthetic/vehicle.yaml).
- [Nissan Versa migration](examples/nissan-versa/README.md) — split documents, horn cases, all-door actions and a synthetic year overlay.

Examples and fixtures illustrate the format. Validation performs no vehicle I/O and does not prove physical compatibility.

## Development

```sh
make mandatory_targets
make clean
```

The acceptance target checks tests, lint, types, generated files, example packages and wheel resources. Cleanup retains the development environment and maintained artifacts.

See the [changelog](CHANGELOG.md), [validation limits](docs/validation.md#remaining-validation-work) and [remaining implementation plan](vehicle_profile_format_2_6ee96dce.plan.md#remaining-work-at-wrap-up). Runtime implementations and BLE interfaces are outside this repository's standard/tooling scope.
