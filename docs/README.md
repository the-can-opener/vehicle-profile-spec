# Vehicle Profile Standard

[Project overview](../README.md) · [Quick start](../README.md#quick-start) · [Author a package](authoring-guide.md) · [Validate a package](validation.md)

Format 2 describes vehicle capabilities in YAML or JSON packages. COVESA VSS supplies canonical property identities; bindings supply acquisition, encoding, addressing and command steps. These pages are the maintained standard.

## Start here

- **Create a profile:** follow the [authoring guide](authoring-guide.md), then [validate it](validation.md).
- **Understand the format:** read [packages](package.md), [manifests](manifest.md), then [properties and bindings](document.md).
- **Convert a legacy profile:** use the [migration guide](migration.md) and [keyword vocabulary](vocabulary.md).
- **Diagnose an error:** read [validation and CLI](validation.md) and the [error-code reference](../skills/validating-vehicle-profiles/error-codes.md).

## Format reference

- [Package and file format](package.md) — directory/ZIP layout, safe paths, JSON-compatible YAML and asset limits.
- [Manifest and applicability](manifest.md) — package identity, versions, document order, DBC assets, dependencies and vehicle selectors.
- [Properties and bindings](document.md) — [reads](document.md#passive-signals-and-active-queries), [shared sources](document.md#shared-sources), [writes](document.md#writes), [channels](document.md#channels), [endpoints and steps](document.md#endpoints), [queries and actions](document.md#queries-and-actions), and [runtime results](document.md#runtime-results-and-discovery).
- [VSS paths and semantics](vss.md) — canonical identities, roles, aliases and catalog resolution.
- [Decoding and encoding](decoding.md) — byte/bit extraction, scaling, enums and exact request encoding.
- [DBC assets](dbc.md) — native signal layout and the boundary between DBC data and binding behavior.
- [Composition and overlays](composition.md) — ordered whole-entry replacement, deletion, applicability and conflicts.
- [Extensions and configuration](extensions.md) — versioned requirements, provider support and non-VSS configuration.

## Authoring and validation

- [Authoring guide](authoring-guide.md) — build a package from applicability through fixtures.
- [Fixtures](fixtures.md) — describe positive and negative inputs and expected outcomes.
- [Validation and CLI](validation.md) — validation layers, commands, strict exceptions and implementation limits.
- [Migration](migration.md) — convert format 1 with explicit framing and an unmapped report.
- [Keyword vocabulary](vocabulary.md) — generated mappings used by migration.
- [Historical format 1 reference](format-1.md) — legacy input syntax, retained for migration only.

## Examples and resources

- [Universal OBD](../examples/universal-obd/vehicle.yaml) — a single-file package with property and named queries.
- [Synthetic HVAC](../examples/hvac-synthetic/README.md) — shared acquisition and an exactly encoded numeric write; [package](../examples/hvac-synthetic/vehicle.yaml) and [fixtures](../examples/hvac-synthetic/fixtures.yaml).
- [Nissan Versa migration](../examples/nissan-versa/README.md) — split documents, shared sequences, and an all-door lock write.
- [Synthetic dual-bus CAN FD](../examples/canfd-dual-bus/README.md) — two channels, `auto` bitrate, FD request defaults and overrides, and a responder range; [package](../examples/canfd-dual-bus/vehicle.yaml).
- [ISO-TP addressing](../examples/bmw-addressing/README.md) — BMW-style extended and mixed addressing on the default `can0` channel; [package](../examples/bmw-addressing/vehicle.yaml).
- [Manifest schema](../schemas/manifest.schema.json), [document schema](../schemas/document.schema.json) and [fixture schema](../schemas/fixture.schema.json).
- [Pinned VSS catalog and provenance](../catalog/README.md).
- [Agent skills and installation](../skills/README.md).
- [Changelog](../CHANGELOG.md) and [remaining implementation work](../vehicle_profile_format_2_6ee96dce.plan.md#remaining-work-at-wrap-up).

## Scope and conventions

MUST and MUST NOT express requirements; SHOULD expresses a recommendation; MAY permits an option. This is an independent binding standard that uses COVESA VSS identities, not an adopted COVESA specification.

The standard defines binding and runtime contracts. The Python tooling performs structural and semantic checks but does not execute vehicle commands or establish physical compatibility. See [remaining validation work](validation.md#remaining-validation-work) for current implementation gaps. BLE interfaces and firmware behavior are outside this standard.
