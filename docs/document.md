# Properties and bindings

[Overview](../README.md) · [Documentation index](README.md)

On this page: [Core concepts](#core-concepts) · [Passive signals and active queries](#passive-signals-and-active-queries) · [Shared sources](#shared-sources) · [Writes](#writes) · [Endpoints, ECU targets, and steps](#endpoints-ecu-targets-and-steps) · [Queries and actions](#queries-and-actions) · [Runtime results and discovery](#runtime-results-and-discovery)

## Core concepts

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

## Passive signals and active queries

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

## Shared sources

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

## Writes

`write` is allowed only on VSS actuators. The steps that perform the write live inside it; a write does not point at a named procedure. A write uses exactly one of three shapes:

| Shape | Fields | Use |
|---|---|---|
| Shorthand | `endpoint`, `request`, optional `expect` | One request |
| Steps | `endpoint`, `deadline_ms`, `steps` | Session setup or several requests |
| Cases | `cases`, mapping each target value to a shorthand or steps body | Discrete targets that use different commands |

In the shorthand and steps shapes, an encoded `parts` field with `input: value` carries the requested target. A `cases` key is the canonical string form of a target in the property datatype: `"true"` or `"false"`, an allowed value, or a decimal number. A target with no case is UNSUPPORTED, and nothing is transmitted.

Optional `constraints` has min, max, and step in canonical units. It MUST narrow, never expand, the catalog domain. The step grid is min + n × step, using zero if min is absent. Validate datatype, catalog constraints, binding constraints, grid, and exact encoding before transmission. Decimal grids use decimal/rational semantics.

A write succeeds when every `expect` in its steps matches. That match is the vehicle's acknowledgement, and the result is `acknowledged`. A write with no `expect` reports `sent` once the transport has submitted its last request. There is no separate verification or completion field. A response that fails its pattern fails the write. A timeout after transmission is OUTCOME_UNKNOWN, not proof that nothing happened.

The runtime stores the requested target and the observed actual value separately. Sending or acknowledging a request never changes the observed value; only a `read` observation does. A caller that needs readback reads or subscribes to the property after the write. A command that affects several actuators cannot be advertised as independent control of one of them. Bind it to the catalog actuator that means the whole set, or define it as an [action](document.md#actions) when no such actuator exists.

`Vehicle.Cabin.Door.Central.IsLocked` is that actuator. `Central` sits beside `Row1` and `Row2` and is not a door position. `"true"` locks every door and `"false"` unlocks every door. The per-door paths, such as `Vehicle.Cabin.Door.Row1.DriverSide.IsLocked`, remain the lock state of one door.

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

## Endpoints, ECU targets, and steps

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

## Queries and actions

A capability with a VSS path is a property: it is read through `read.signal` or `read.query` and controlled through `write`. Everything else is a named query or a named action. A query returns data and does not change vehicle state. An action changes vehicle state. There is no third procedure kind.

Names are uppercase with underscores. When the standard keyword vocabulary lists the capability, for example `ECU_WAKE`, `WAKE_UP`, or `SIGNAL_OFF`, the package MUST use that name; other names are vehicle-specific. A keyword that maps to exactly one VSS actuator is a write on that path, with the keyword as an alias, and MUST NOT also be an action. `HORN` is therefore a write on `Vehicle.Body.Horn.IsActive`. `LOCK` and `UNLOCK` are aliases on `Vehicle.Cabin.Door.Central.IsLocked`, for targets `"true"` and `"false"`. `WIPERS` is a write on `Vehicle.Body.Windshield.Front.Wiping.Mode` for target `"MEDIUM"` when the command does not select a speed. `OPEN_FRONT_LEFT_WINDOW`, `OPEN_FRONT_RIGHT_WINDOW`, `OPEN_REAR_LEFT_WINDOW`, and `OPEN_REAR_RIGHT_WINDOW` write `100` on that door's `Window.Position`, and the matching `CLOSE_*_WINDOW` names write `0`. Left and right assume left-hand drive. `WINDOW_CHILD_LOCK` and `WINDOW_CHILD_UNLOCK` are the true and false cases of `Vehicle.Cabin.IsWindowChildLockEngaged`. A name MUST NOT be both a query and an action.

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

  SIGNAL_OFF:
    description: Turn off both direction indicators.
    endpoint: body
    deadline_ms: 1000
    steps:
      - call: body-session
      - request: "30 2F 00 00"
        expect: {prefix: "70 2F *"}
```

`ECU_WAKE` has no VSS actuator, and its steps have no `expect`, so its result is `sent`. `SIGNAL_OFF` turns off both indicators at once, and the catalog has no actuator for that pair, so it stays an action. An all-door lock is not an action: it is a write on `Vehicle.Cabin.Door.Central.IsLocked`.

Writes and actions default to no retries. A timeout after transmission can mean outcome unknown, not failure to execute. `idempotent` is an explicit semantic assertion and does not guarantee exactly-once ECU execution.

## Runtime results and discovery

Recommended SDK verbs: describe, get, read, subscribe, unsubscribe, set, invoke, cancel. `read` takes a property path or a query name, `set` takes an actuator path and target, and `invoke` takes an action name and input. This standard defines behavior, not a required language-specific method name or wire protocol.

An observation includes path or query name, value when valid, unit when applicable, source, acquisition kind, receivedAt, optional observedAt, clockDomain, sequence, and quality: valid/stale/invalid/unavailable. UTC timestamps use RFC3339; deadlines and ordering use monotonic clocks. Properties have isolated state per connected vehicle.

Executions report accepted/running/succeeded/failed/cancelled/unknown and evidence `sent` or `acknowledged`. Errors use stable codes: INVALID_PACKAGE, UNKNOWN_PATH, UNSUPPORTED, UNAVAILABLE, VEHICLE_MISMATCH, PERMISSION_DENIED, PRECONDITION_FAILED, TIMEOUT, NEGATIVE_RESPONSE, DECODE_ERROR, CONFLICT, CANCELLED, OUTCOME_UNKNOWN.

Discovery distinguishes defined capability, implementation support, applicability, current availability, and permission. Unmapped properties are explicitly unavailable. Unknown/mismatched applicability cannot automatically authorize writes or actions. Make/model/year declarations are not physical test evidence.

## Related pages

[VSS identity](vss.md) · [Decoders and request encoding](decoding.md) · [DBC references](dbc.md) · [Composition](composition.md) · [Fixtures](fixtures.md)
