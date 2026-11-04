# Vehicle Binding Specification

**Version 0.4.0 — design draft**

CAN Opener · 4 November 2026

## 1. Purpose

Describe how a vehicle exposes properties, accepts control requests, and runs vehicle-specific commands through a portable package of YAML or JSON files. COVESA VSS provides property identities and semantics. Vehicle bindings provide acquisition, encoding, addressing, and execution details.

The primary authoring model is **flat property keys**, each using its canonical VSS path. A property's `read` binding may include a passive `signal`, an active `query`, or both. Writable properties have a separate `write` binding. Requests and commands that have no VSS path are named `queries` and `actions`.

Vehicle configuration is a versioned extension area; adding it must not require redesigning the property model. Diagnostics and BLE firmware interfaces are not covered by this draft. OBDb is a design reference only; compatibility or import support is not a requirement.

This is an independent draft, not an adopted COVESA standard. It supersedes the earlier nested-tree design and the format 1 profile described in `README.md`. The schemas and tools in the previous v0.2/v0.3 kits do not implement this syntax.

MUST, MUST NOT, SHOULD, and MAY describe requirements for implementations of this draft.

## 2. Core concepts

| Concept | Responsibility |
|---|---|
| Manifest | Package identity, applicability, DBC files, and the ordered list of documents |
| `properties` | Flat map of canonical VSS properties and their vehicle bindings |
| `read.signal` | Passive acquisition from a CAN frame or DBC field |
| `read.query` | Active request/response acquisition |
| `write` | Steps that change one VSS actuator to a target value |
| `value` | Static value of a VSS attribute |
| `sources` | Optional shared frames or multi-output requests |
| `channels` | Bus protocol and bitrate |
| `endpoints` | The ECU a request targets: addressing, framing, and timing |
| `sequences` | Shared steps called from writes, queries, and actions |
| `queries` | Named request/response reads that have no VSS path |
| `actions` | Named vehicle commands that are not a write to one VSS actuator |
| `requires` | Versioned features an implementation must understand |
| `extensions` | Payloads governed by optional versioned extension specifications |
| `unmapped` | Documentation of work that is not an active capability |

The VSS role is inherited rather than repeated:

| VSS type | Permitted core bindings |
|---|---|
| Sensor | `read` |
| Actuator | `read`, `write`, or both |
| Attribute | `value` or `read` |

A `value` and `read` are mutually exclusive. A sensor cannot be written. An attribute is not automatically a configurable vehicle parameter. Query and action names are the only public capability names outside VSS. DBC `signal` names remain protocol-level field names, not a second public property catalog.

## 3. Package and file format

A vehicle definition is a **package**: a directory, or a zip whose root is that directory. Exactly one manifest, `vehicle.yaml` or `vehicle.json`, sits at the package root. The manifest lists every document, DBC, and fixture file. The loader MUST NOT scan directories, and a file the manifest does not list is never loaded. Free-form `docs/`, `README*`, `LICENSE*`, and `CHANGELOG*` files may be present and are never loaded.

```text
nissan-versa/
  vehicle.yaml          # manifest
  base.yaml             # channels, engine endpoint, powertrain properties
  body.yaml             # body endpoints, sequences, body properties and actions
  overlays/2011.yaml    # narrower applicability, merged last
  dbc/signals.dbc
  fixtures/body.yaml
  README.md             # not loaded
```

YAML and JSON represent the same JSON-compatible object model. Object keys MUST be strings. Reject duplicate keys, YAML tags/anchors/aliases, non-finite numbers, implicit timestamps, and objects that cannot round-trip to JSON. Hexadecimal values are uppercase strings. CAN IDs use strings such as `"7E0"`; payloads use byte strings such as `"01 0D"`. Model-year ranges are inclusive.

Property keys are flat, case-sensitive canonical paths, for example `Vehicle.Speed`. The loader MUST NOT accept both flat and nested representations in one document or silently rewrite nonstandard names. Binding objects remain structured; flat property addressing does not mean flattening every protocol field.

Resolve asset paths relative to the package root. Reject absolute paths, `..` traversal, symlinks, duplicate or case-insensitively colliding entries, encrypted zip entries, non-UTF-8 names, and sizes above the implementation's declared limits. Recommended defaults are 16 MiB per package, 4 MiB per file, 1000 entries, and a 1:100 compression ratio. A listed file may carry `sha256`; a loader running with an integrity-required policy rejects listed files that omit it.

## 4. Manifest and documents

| Manifest field | Meaning |
|---|---|
| `manifest` | Container version; `1` |
| `format` | Document grammar; `2` is this draft. Format 1 documents are rejected with a pointer to migration |
| `id` | Reverse-DNS identifier, stable across package versions |
| `version` | Semver of this package |
| `name` | Human-readable name |
| `vss` | Pinned VSS release, for example `"6.1"` |
| `applies_to` | Package-wide applicability |
| `dbc` | Map from a DBC id to `{path, channel, sha256?}` |
| `documents` | Ordered list; each entry has `path` and may set `applies_to` and `override` |
| `fixtures` | Fixture files (§16) |
| `depends` | Packages that must load first: `{id, version}` with a semver range |
| `unmapped` | Documented gaps, never capabilities |

If `documents` is omitted, the manifest file itself is the only document, so a single-file package is valid.

`applies_to` accepts `manufacturers`, `models`, `years`, `trims`, `engines`, and `markets`. A missing key is a wildcard. `years` lists model years or inclusive `{range: [from, to]}` entries.

```yaml
manifest: 1
format: 2
id: com.canopener.nissan.versa
version: 0.1.0
name: Nissan Versa (2007-2012)
vss: "6.1"

applies_to:
  manufacturers: [Nissan]
  models: [Versa]
  years: [{range: [2007, 2012]}]

dbc:
  main: {path: dbc/signals.dbc, channel: vehicle}

documents:
  - path: base.yaml
  - path: body.yaml
  - path: overlays/2011.yaml
    applies_to: {years: [2011]}

fixtures:
  - fixtures/body.yaml

unmapped:
  - {capability: SEATBELT_WARNING, reason: "exact VSS identity and frame not established"}
```

A document may contain `applies_to`, `channels`, `endpoints`, `sources`, `properties`, `sequences`, `queries`, `actions`, `requires`, and `extensions`. This `base.yaml` binds one property to both a broadcast signal and an engine query:

```yaml
channels:
  vehicle:
    protocol: can
    configuration: runtime

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
      signal:
        dbc: main
        message: SPEED_BRAKE
        signal: SPEED_KMPH
      query:
        endpoint: engine
        request: "01 0D"
        response:
          prefix: "41 0D"
          min_data_bytes: 1
        decode:
          byte: 0
          bytes: 1
          type: uint
        interval_ms: 500
      policy:
        preferred: signal
        max_age_ms: 500
        active_fallback: false
```

A signal-only or query-only property simply omits the other binding. Do not duplicate `Vehicle.Speed` under separate signal and query sections.

Equivalent flat property syntax in JSON:

```json
{
  "properties": {
    "Vehicle.Speed": {
      "read": {
        "signal": {
          "dbc": "main",
          "message": "SPEED_BRAKE",
          "signal": "SPEED_KMPH"
        }
      }
    }
  }
}
```

The JSON above is a property fragment, not a complete document.

## 5. Property semantics and catalog resolution

The pinned VSS release supplies datatype, unit, meaning, range, and allowed values. A binding MUST NOT redefine a standard property's semantics. Namespaced catalog additions require an explicit overlay validated with VSS tooling. Always check for a matching standard concept before adding an extension.

A binding must match the underlying quantity, not merely have a similar label. A warning indicator is not interchangeable with buckle state. The current seatbelt warning remains `unmapped` until its exact catalog identity and vehicle encoding are established; this standard invents no replacement seatbelt namespace.

Aliases MAY be supplied as an array on a property for legacy SDK names, such as `SPEED` for `Vehicle.Speed`. They resolve to the same canonical cache entry and MUST NOT collide with another alias, property key, query name, or action name.

VSS does not define a vehicle's ECUs. `Vehicle.ControlUnit` is a branch whose instance names (`Central`, `FrontLeft`, `FrontRight`, `RearLeft1`, `RearLeft2`, `Trunk`) are examples that the catalog expects deployments to replace. Each instance carries only an `ID` attribute and `Health` signals: network status, power, temperature, CPU and memory use, and software supervision. A package MUST NOT treat those instance names as ECU addresses. To bind health properties of a real controller, supply a VSS overlay that sets the instance list, validate it with VSS tooling, and bind the resulting paths like any other property. The ECU that answers a request is identified by its endpoint (§10).

## 6. Passive signals and active queries

`read.signal` contains either:

- A DBC reference: `dbc`, `message`, `signal`, with optional `decode_as` or raw `enum` mapping.
- An inline CAN frame binding: `channel`, `id`, `id_format`, `length`, `decode`.
- A reference to a passive shared source: `source`, `output`.

`read.query` contains either:

- An inline request: `endpoint`, `request`, `response`, `decode`, optional `interval_ms`.
- A reference to an active shared source: `source`, `output`.

Each binding MUST choose one of these forms. A query source cannot be referenced as a passive signal. A passive source cannot be referenced as a query.

Policy fields:

| Field | Meaning |
|---|---|
| `preferred` | `signal` or `query`; must reference an available binding |
| `max_age_ms` | Maximum age of an observation considered fresh |
| `active_fallback` | Whether automatic fallback may consider an active query; default false |

With both bindings, default preference is signal. With one binding, that binding is preferred. Missing `max_age_ms` means the profile supplies no freshness guarantee; a caller requesting fresh data must supply its own age bound. No age bound means cached validity only, not a claim of real-time freshness.

`get` never transmits. A default subscription uses passive signals where available. Polling must be explicitly requested. A read explicitly requesting `query` may transmit subject to runtime permissions and scheduling. Automatic fallback may transmit only when BOTH profile policy and caller/runtime policy permit it. Profile policy cannot grant permissions.

A response updates the same canonical property as a broadcast observation. Record acquisition kind, source, receipt time, optional measured time, and monotonic sequence. Late responses cannot overwrite a newer accepted observation. Use runtime acquisition ordering where ECU clocks cannot be compared. A transport timestamp must not be fabricated as measurement time.

Polling jobs are shared by endpoint, request, responder selection, and decoding contract. `interval_ms` is the minimum interval between request starts. Deduplicate identical reads, bound bus load, and release a job when its last consumer stops. Monitoring and polling have separate subscription accounting.

## 7. Shared sources

A named source declares `kind: signal` or `kind: query` and contains the corresponding binding without a `source` reference. Sources cannot reference other sources, preventing chains and cycles.

A DBC signal source identifies `dbc` and `message`; outputs are existing DBC signal names. Inline signal/query sources declare an `outputs` map of decoder definitions. A shared query specifies endpoint/request/response/interval once and may produce many property values.

```yaml
sources:
  lights:
    kind: signal
    dbc: main
    message: LIGHTS_STATUS_60D

properties:
  Vehicle.Body.Lights.Beam.Low.IsOn:
    read:
      signal:
        source: lights
        output: LOW_BEAMS
        decode_as: boolean

  Vehicle.Body.Lights.Beam.High.IsOn:
    read:
      signal:
        source: lights
        output: HIGH_BEAMS
        decode_as: boolean
```

One monitor supplies both properties. Unsubscribing one must not stop the other. Raw decode/layout belongs in the source or DBC; property semantics belong in VSS.

## 8. Decoding and encoding

Byte decoders use `byte`, `bytes`, `type`, and optional `endian`. Core types: uint, int, ascii, hex. Byte offsets are zero-based; integer endian defaults to big. ASCII is strict; hex results use uppercase without spaces.

Bit decoders use `start_bit`, `bits`, `bit_order` (msb0 or lsb0), and integer type. msb0 counts from the high bit and assembles the first bit as most significant; lsb0 counts from the low bit and assembles the first bit as least significant. These conventions are distinct from DBC Motorola sawtooth notation. DBC adapters use native DBC rules.

For query responses, decode offsets begin AFTER the validated response prefix. Passive frame decoders operate on the entire CAN data field. Validate frame length, responder, response prefix, and minimum payload before decoding.

Order: extraction; invalid_raw handling; enum OR numeric scaling; canonical validation; publication. Scaling is raw × scale + offset, defaulting to 1 and 0. Enum keys are canonical raw-value strings. Unknown enum values and invalid raw encodings produce invalid observations, never zero/false defaults. Enum mapping and scaling cannot coexist.

DBC physical decoding applies factor/offset without automatically substituting `VAL_` labels. `decode_as: boolean` maps raw 0/1 to false/true; other encodings are invalid. Explicit enum mapping is an alternative to physical decoding.

Units and ranges must match VSS. Inline decoder `unit`, if specified, describes the physical result. If absent, the result is in the target property unit. Core 0.4 does not silently convert incompatible units. Shared outputs require compatible semantics and units for all consumers.

A `request` is either a hex string or `parts`, a list that mixes literal hex strings with encoded fields. An encoded field declares `input`, `type`, `bytes`, `endian`, `scale`, and `offset`. Encode raw = (input − offset) / scale, requiring an integral result within the wire width. Do not round, clamp, or overflow silently. More complex codecs require a declared versioned extension.

## 9. Writes

`write` is allowed only on VSS actuators. The steps that perform the write live inside it; a write does not point at a named procedure. A write uses exactly one of three shapes:

| Shape | Fields | Use |
|---|---|---|
| Shorthand | `endpoint`, `request`, optional `expect` | One request |
| Steps | `endpoint`, `deadline_ms`, `steps` | Session setup or several requests |
| Cases | `cases`, mapping each target value to a shorthand or steps body | Discrete targets that use different commands |

In the shorthand and steps shapes, an encoded `parts` field with `input: value` carries the requested target. A `cases` key is the canonical string form of a target in the property datatype: `"true"` or `"false"`, an allowed value, or a decimal number. A target with no case is UNSUPPORTED, and nothing is transmitted.

Optional `constraints` has min, max, and step in canonical units. It MUST narrow, never expand, the catalog domain. The step grid is min + n × step, using zero if min is absent. Validate datatype, catalog constraints, binding constraints, grid, and exact encoding before transmission. Decimal grids use decimal/rational semantics.

A write succeeds when every `expect` in its steps matches. That match is the vehicle's acknowledgement, and the result is `acknowledged`. A write with no `expect` reports `sent` once the transport has submitted its last request. There is no separate verification or completion field. A response that fails its pattern fails the write. A timeout after transmission is OUTCOME_UNKNOWN, not proof that nothing happened.

The runtime stores the requested target and the observed actual value separately. Sending or acknowledging a request never changes the observed value; only a `read` observation does. A caller that needs readback reads or subscribes to the property after the write. A command that affects several actuators cannot be advertised as independent control of one of them; define it as an action (§11).

### Horn example

This uses the Versa body command. The format 1 profile defines no horn-off command, so `"false"` has no case and writing false is unsupported.

```yaml
properties:
  Vehicle.Body.Horn.IsActive:
    aliases: [HORN]
    write:
      cases:
        "true":
          endpoint: body
          deadline_ms: 1000
          steps:
            - call: body-session
            - request: "30 30 00 01"
              expect: {prefix: "70 30 01"}
```

### Cabin temperature example

Measured air temperature and the selected HVAC setting are separate properties. This is a **synthetic binding fragment**, not a Nissan command mapping. DBC names, endpoint, bytes, scaling, and limits are illustrative. Validate path/datatype/unit against the pinned catalog before deployment; fractional targets are valid only when that datatype permits them.

```yaml
properties:
  Vehicle.Cabin.HVAC.AmbientAirTemperature:
    read:
      signal:
        dbc: main
        message: CLIMATE_STATUS
        signal: CABIN_TEMPERATURE

  Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature:
    read:
      signal:
        dbc: main
        message: CLIMATE_STATUS
        signal: DRIVER_TEMPERATURE_SETTING
    write:
      endpoint: climate
      request:
        parts:
          - "AA BB"
          - input: value
            type: uint
            bytes: 1
            endian: big
            scale: 0.5
            offset: 16
      expect: {prefix: "CC DD"}
      constraints: {min: 16, max: 30, step: 0.5}
```

Selecting 22 encodes (22 − 16) / 0.5 = 12, or `0C`, and sends `AA BB 0C`. A `CC DD` response means the climate ECU accepted the setting. The setting readback arrives through the `read` binding. If ambient air is 28, the setting may read 22 while ambient remains 28; the acknowledgement confirms the selected setting, not that the cabin has reached it.

## 10. Endpoints, ECU targets, and steps

Channels declare protocol and explicit bitrate(s) or runtime configuration. Runtime configuration must resolve before activation.

An endpoint is the ECU a request targets. VSS supplies no addresses; the endpoint does. Property queries, writes, named queries, and actions name an endpoint instead of repeating CAN IDs, so two controllers on one bus are two endpoints, and a request reaches only the controller whose endpoint it names.

| Endpoint field | Meaning |
|---|---|
| `channel` | Channel the endpoint is on |
| `protocol` | `can` for raw frames or `isotp` for ISO-TP transport |
| `tx` | Transmit CAN ID |
| `rx` | List of accepted response CAN IDs; omitted on a request-only endpoint |
| `id_format` | `standard` or `extended` |
| `timeout_ms` | Response wait per request |

```yaml
endpoints:
  body:
    channel: vehicle
    protocol: isotp
    tx: "745"
    rx: ["765"]
    id_format: standard
    timeout_ms: 300

  body-wake:
    channel: vehicle
    protocol: can
    tx: "60D"
    id_format: standard
```

`body` is the Versa body control module. `body-wake` is request-only, so it has no `rx` and no `timeout_ms`.

Distinguish extended CAN IDs from ISO-TP extended addressing. Missing protocol adapters make affected capabilities unavailable. For raw CAN endpoints, payloads and response patterns refer to the exact CAN data field. For ISO-TP endpoints, they refer to reassembled application payloads; adapters own PCI, padding, and flow control. Do not infer framing from the first byte. The format 1 Versa profile sends raw frames that include the PCI byte and padding; a migration that must stay byte-exact keeps those endpoints as `protocol: can`. Functional or multi-responder requests, such as `tx: "7DF"` with responses from `7E8` through `7EF`, require explicit responder selection or separate per-responder results.

### Response patterns

`response` on a query and `expect` on a step use the same matching. `prefix` is a hex byte string matched against the start of the response. A `*` token matches any one byte. `exact: true` requires the response to be exactly the pattern length. `min_data_bytes` requires at least that many bytes after the prefix.

### Steps

| Step | Behavior |
|---|---|
| `request` with `expect` | Send, wait for a response on the endpoint's `rx`, and match it |
| `request` without `expect` | Send only; no response wait |
| `call: <sequence>` | Run a shared sequence's steps in place |
| `wait_ms` | Pause |

Transport adapters are outside this standard. Bindings specify acquisition and request/response semantics without prescribing a firmware interface.

### Sequences

`sequences` hold steps shared by more than one write, query, or action, such as session setup. Steps used in one place stay inline. A sequence has only `steps` and runs on the caller's endpoint. Calls resolve after composition, so an overlay can replace a sequence for a narrower set of vehicles. Cycles and unbounded loops are forbidden. The caller's `deadline_ms` bounds nested calls and waits.

```yaml
sequences:
  body-session:
    steps:
      - request: "10 81"
        expect: {prefix: "50 81"}
      - request: "10 C0"
        expect: {prefix: "50 C0"}
```

Preconditions use fresh valid property values. Session-affecting work acquires an endpoint lease; conflicting work waits or reports conflict. Disconnect invalidates session state. Cancellation stops future steps but cannot reverse transmitted vehicle effects. Long-lived keepalive and security access are not core steps and require an explicit adapter contract.

## 11. Queries and actions

A capability with a VSS path is a property: it is read through `read.signal` or `read.query` and controlled through `write`. Everything else is a named query or a named action. A query returns data and does not change vehicle state. An action changes vehicle state. There is no third procedure kind.

Names are uppercase with underscores. When the standard keyword vocabulary lists the capability, for example `ECU_WAKE`, `WAKE_UP`, `LOCK`, or `SIGNAL_OFF`, the package MUST use that name; other names are vehicle-specific. A keyword that maps to exactly one VSS actuator is a write on that path, with the keyword as an alias, and MUST NOT also be an action. `HORN` is therefore a write on `Vehicle.Body.Horn.IsActive`. A name MUST NOT be both a query and an action.

Queries and actions may declare `input_schema` (JSON Schema) when a request uses encoded `parts`; each encoded field's `input` names a property of the input object. An action cannot call another action or query. A caller that needs the body network awake invokes `ECU_WAKE` first.

### Queries

A query has `description`, `endpoint`, `request`, and `response`, and either `decode` with `datatype` and optional `unit`, or an `outputs` map whose decoders each declare `datatype` and optional `unit`. No VSS entry supplies the datatype and unit, so the query declares them. Optional `interval_ms` allows polling. A query never changes state, so it may be retried. A query whose result has a VSS path is a property `read.query` instead.

```yaml
queries:
  SUPPORTED_PIDS_01_20:
    description: Bitmap of mode 01 PIDs 01 to 20 supported by the engine controller.
    endpoint: engine
    request: "01 00"
    response: {prefix: "41 00", min_data_bytes: 4}
    decode: {byte: 0, bytes: 4, type: hex}
    datatype: string
```

### Actions

An action has `description`, optional `input_schema`, optional `retry` (`never` or `idempotent`, default `never`), and the body of a shorthand or steps write: `endpoint` and `request` with optional `expect`, or `endpoint`, `deadline_ms`, and `steps`. Actions have no `cases`; inputs come through `input_schema`. The result follows write rules: `acknowledged` when every `expect` matches, `sent` when no step expects a response.

```yaml
actions:
  ECU_WAKE:
    description: Wake the body network with five empty frames before a body command.
    endpoint: body-wake
    steps:
      - request: "00 00 00 00 00 00 00 00"
      - request: "00 00 00 00 00 00 00 00"
      - request: "00 00 00 00 00 00 00 00"
      - request: "00 00 00 00 00 00 00 00"
      - request: "00 00 00 00 00 00 00 00"

  LOCK:
    description: Lock all doors.
    retry: idempotent
    endpoint: body
    deadline_ms: 1000
    steps:
      - call: body-session
      - request: "30 38 00 01"
        expect: {prefix: "70 38 *"}

  SIGNAL_OFF:
    description: Turn off both direction indicators.
    endpoint: body
    deadline_ms: 1000
    steps:
      - call: body-session
      - request: "30 2F 00 00"
        expect: {prefix: "70 2F *"}
```

`ECU_WAKE` has no VSS actuator, and its steps have no `expect`, so its result is `sent`. `LOCK` is an action because the vehicle locks every door with one command; VSS has an `IsLocked` actuator per door, and advertising per-door control would be false. `SIGNAL_OFF` turns off both indicators at once for the same reason.

Writes and actions default to no retries. A timeout after transmission can mean outcome unknown, not failure to execute. `idempotent` is an explicit semantic assertion and does not guarantee exactly-once ECU execution.

## 12. Composition

Documents load in manifest order. Keyed sections merge by key: `endpoints`, `sources`, `properties`, `sequences`, `queries`, and `actions`.

- A later document replaces the whole entry for a key; entries are not deep-merged.
- `KEY: null` deletes an entry defined earlier.
- A document's `applies_to` is intersected with the manifest's and MUST NOT widen it.
- References (endpoints, sources, sequence calls, DBC names) resolve after the merge.

Packages load in host order; universal, then make, model, and year is recommended. Each `depends` entry must be satisfied earlier in the order. The same key defined by two packages is a conflict unless the later document sets `override: true`.

## 13. Extension mechanism

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

## 14. Configuration model

Separate three categories:

| Category | Location | Example |
|---|---|---|
| Connection/runtime configuration | channels/endpoints/runtime | bitrate, timeout |
| Vehicle property already represented by VSS | properties + write | HVAC setting |
| Persistent vehicle parameter without a matching VSS property | configuration extension | OEM auto-relock delay |

Do not duplicate a VSS actuator in a custom configuration registry. VSS attributes describe characteristics and are not a generic vehicle-coding interface. For a persistent non-VSS parameter, the extension must define datatype, unit, range, permitted values, readback, scope, persistence, defaults if known, required ignition/session state, and whether activation requires restart.

Batch changes must declare atomicity. If not atomic, return per-parameter outcomes and partial success. Do not promise rollback unless verified undo behavior exists. Readback verifies stored/applied state as appropriate; saving an intended setting locally does not prove ECU persistence. Configuration extension contracts must distinguish pending, stored, and active values when they differ.

## 15. Runtime results and discovery

Recommended SDK verbs: describe, get, read, subscribe, unsubscribe, set, invoke, cancel. `read` takes a property path or a query name, `set` takes an actuator path and target, and `invoke` takes an action name and input. This standard defines behavior, not a required language-specific method name or wire protocol.

An observation includes path or query name, value when valid, unit when applicable, source, acquisition kind, receivedAt, optional observedAt, clockDomain, sequence, and quality: valid/stale/invalid/unavailable. UTC timestamps use RFC3339; deadlines and ordering use monotonic clocks. Properties have isolated state per connected vehicle.

Executions report accepted/running/succeeded/failed/cancelled/unknown and evidence `sent` or `acknowledged`. Errors use stable codes: INVALID_PACKAGE, UNKNOWN_PATH, UNSUPPORTED, UNAVAILABLE, VEHICLE_MISMATCH, PERMISSION_DENIED, PRECONDITION_FAILED, TIMEOUT, NEGATIVE_RESPONSE, DECODE_ERROR, CONFLICT, CANCELLED, OUTCOME_UNKNOWN.

Discovery distinguishes defined capability, implementation support, applicability, current availability, and permission. Unmapped properties are explicitly unavailable. Unknown/mismatched applicability cannot automatically authorize writes or actions. Make/model/year declarations are not physical test evidence.

## 16. Validation, fixtures, and acceptance

Validation layers:

1. Container: one manifest, safe paths, listed files present, hashes, size limits.
2. Syntax: JSON-compatible parsing, manifest and format versions, allowed fields, mutually exclusive forms (`value` with `read`, two write shapes, a query and an action with one name).
3. References: assets, source kind, outputs, endpoints, sequence calls and cycles, DBC messages and signals, `depends`.
4. Semantics: exact VSS catalog paths, roles (no write on a sensor), datatypes, units, ranges, allowed values, target constraints, alias and name collisions.
5. Composition: merge conflicts and widened applicability.
6. Extensions: every extension payload in `requires`, and whether the package can be fully activated.
7. Behavior: decode/encode, shared acquisition, freshness, source selection, response correlation, acknowledgement, failures.
8. Evidence: physical tests on declared vehicle/ECU variants.

A syntax check cannot establish later layers. Missing dependencies and unchecked mappings must be reported.

A fixture file lists cases. An optional `label` describes the test without duplicating its capability `name`. Each case has a `kind` of `signal`, `query`, `write`, or `action`; a `path` for signals, writes, and property queries, or a `name` for named queries and actions; inputs from `frame`, `responses`, `target`, and `input`; and an `expect` holding any of `value`, `quality`, `sent`, `result`, and `error`.

```yaml
fixture: 1
cases:
  - label: lock acknowledged
    kind: action
    name: LOCK
    responses: ["50 81", "50 C0", "70 38 01"]
    expect:
      sent: ["10 81", "10 C0", "30 38 00 01"]
      result: acknowledged

  - label: lock sent with no reply
    kind: action
    name: LOCK
    responses: ["50 81", "50 C0"]
    expect: {result: unknown, error: OUTCOME_UNKNOWN}
```

The spec defines the fixture format; a validator checks that fixtures are well formed and name existing capabilities, and runtimes execute them. Every active binding should have positive and negative fixtures. Required cases include passive-plus-query acquisition for one property, no implicit polling, numeric targets with exact encoding, an unsupported case target, a failed acknowledgement, wrong responder, timeouts, unknown write or action outcomes, and unsupported required extensions.

OBDb compatibility is not an acceptance criterion. Cross-language claims require shared behavioral fixtures; vehicle-portability claims require demonstrated matching semantics on multiple vehicles.

## 17. Versioning and migration

This draft changes the authoring format. Previous schemas and tools need updates before they can validate it.

Migration from format 1 (`README.md` profiles):

| Format 1 | This draft |
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

Changes from the earlier 0.4.0 draft:

- One root manifest became a package manifest with an ordered document list, composition rules, and `depends`.
- `operations` were replaced by named `queries` and `actions`.
- Write steps live inside the write. `write.sequence`, `completion`, and `verify` were removed; a matched `expect` is the acknowledgement.
- Sequences hold only shared steps and run on the caller's endpoint.
- Endpoints are the ECU target, and VSS `ControlUnit` instance names are not addresses.
- The future diagnostics contract was removed from this draft.

Migration from v0.3:

- Flatten the nested properties tree into exact VSS-path keys.
- Put passive bindings under `read.signal` and active bindings under `read.query`.
- A property may contain both; replace positional alternatives with the explicit acquisition policy.
- Rename passive source kinds to `signal` and keep active source kind `query`.
- Preserve DBC signal names, numeric write constraints, and canonical property semantics.
- Remove any OBDb compatibility/import/parity release requirements.

During 0.x, minor versions may break compatibility and require migration notes. A published 1.x standard uses major versions for breaking interpretation changes. Pin VSS and feature versions independently. Publish schemas, examples, and conformance fixtures with each implemented release. Do not present an unsupported feature as working merely because the standard has an extension point for it.
