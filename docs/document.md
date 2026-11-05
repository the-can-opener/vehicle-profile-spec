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
| `channels` | Logical buses: protocol, bitrate, and CAN FD defaults |
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
| Repeat | `endpoint`, `repeat`, optional `steps` | One raw CAN frame retransmitted to keep the state |
| Cases | `cases`, mapping each target value to one of the bodies above | Discrete targets that use different commands |

In the shorthand and steps shapes, an encoded `parts` field with `input: value` carries the requested target. A `cases` key is the canonical string form of a target in the property datatype: `"true"` or `"false"`, an allowed value, or a decimal number. A target with no case is UNSUPPORTED, and nothing is transmitted.

Optional `constraints` has min, max, and step in canonical units. It MUST narrow, never expand, the catalog domain. The step grid is min + n × step, using zero if min is absent. Validate datatype, catalog constraints, binding constraints, grid, and exact encoding before transmission. Decimal grids use decimal/rational semantics.

A write succeeds when every `expect` in its steps matches. That match is the vehicle's acknowledgement, and the result is `acknowledged`. A write with no `expect` reports `sent` once the transport has submitted its last request. There is no separate verification or completion field. A response that fails its pattern fails the write. A timeout after transmission is OUTCOME_UNKNOWN, not proof that nothing happened.

`deadline_ms` bounds that transmission. It is the time allowed for the steps, including nested calls and waits. It is not how long the vehicle keeps the commanded state. Each response still waits at most the endpoint `timeout_ms`.

How long the state lasts is a separate declaration on the shorthand, the steps body, or one case:

| Declaration | Meaning |
|---|---|
| `duration` and `repeat` both absent | Hold time is unknown. The vehicle may keep the state, or it may drop it after a few milliseconds |
| `duration: <milliseconds>` | Information. How long the commanded effect has been observed to last |
| `duration: latched` | Information. The effect has been observed to stay until another command changes it |
| `release.action` | Named action that ends the effect early. It may accompany `duration` |
| `repeat` | The state lasts while one raw CAN frame is retransmitted |

When `duration` and `repeat` are both absent, the profile states no hold time. The vehicle may keep the state, or it may drop it after a few milliseconds. `duration` is information for the caller. A positive number is an observed hold in milliseconds. `latched` means the effect has been observed to stay until another command changes it. The runtime transmits the write and leaves the hold, its ending, and any following state to the vehicle. It does not start a timer, wait out a finite `duration`, or send an off frame when that time elapses. A later `read` reports the observed value. A matched `expect` is still the acknowledgement. For `Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling` and `Vehicle.Body.Lights.Hazard.IsSignaling`, true means the signaling function is active and the vehicle flashes the lamp. A finite `duration` describes how long that function has been observed to stay active, not the flash period. A lamp that stays lit steadily is an `IsOn` actuator, such as `Vehicle.Body.Lights.Beam.High.IsOn`.

`repeat` is one frame on a raw CAN endpoint. It excludes `duration` and a body-level `release`. Optional `steps` run once before repetition starts; they are not repeated. A shorthand `request` is not combined with `repeat`, because the frame is the repeated command. `interval_ms` is the maximum gap between frame starts. `release: silence` means stopping that transmission is the off command. `release.action` names an action the runtime invokes when the repetition stops. `frame.base: last-rx` copies every unowned bit from the newest frame received on that CAN id. `frame.mask` marks the bits this command owns, and `frame.patch` supplies those bits. On each tick:

```text
outgoing = (last-rx AND NOT mask) OR patch
```

`mask` and `patch` are the same length, at least one mask bit is set, and patch bits outside the mask are zero. Several repeats may share one CAN id when their masks do not overlap; the runtime applies every active patch to the same received frame and transmits it once per interval. Until one frame has been received, a `last-rx` repeat is unavailable. A repeat with no `expect` reports `sent` when the first merged frame is submitted, then keeps sending until release.

The runtime stores the requested target and the observed actual value separately. Sending or acknowledging a request never changes the observed value; only a `read` observation does. A caller that needs readback reads or subscribes to the property after the write. A command that affects several actuators cannot be advertised as independent control of one of them. Bind it to the catalog actuator that means the whole set, or define it as an [action](document.md#actions) when no such actuator exists.

`Vehicle.Cabin.IsCentralLockEngaged` is that actuator. It sits beside `IsWindowChildLockEngaged`. `"true"` locks every door and `"false"` unlocks every door. The per-door paths, such as `Vehicle.Cabin.Door.Row1.DriverSide.IsLocked`, remain the lock state of one door.

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

### Timed signal and repeated frame

The signal is the Versa command: one diagnostic sequence, then the vehicle signals for 5 seconds or until `SIGNAL_OFF`. The wiper frame is a **synthetic binding fragment**. Its mask bits are illustrative. The checked-in Versa wiper command sends one fixed frame and does not declare `repeat`.

```yaml
endpoints:
  wipers:
    channel: vehicle
    protocol: can
    tx: "35D"
    id_format: standard

actions:
  SIGNAL_OFF:
    description: Turn off both direction indicators.
    endpoint: body
    deadline_ms: 1000
    steps:
      - call: body-session
      - request: "30 2F 00 00"
        expect: {prefix: "70 2F *"}

properties:
  Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling:
    write:
      cases:
        "true":
          endpoint: body
          deadline_ms: 1000
          steps:
            - call: body-session
            - request: "30 2F 00 02"
              expect: {prefix: "70 2F *"}
          duration: 5000
          release:
            action: SIGNAL_OFF

  Vehicle.Body.Windshield.Front.Wiping.Mode:
    write:
      cases:
        MEDIUM:
          endpoint: wipers
          repeat:
            interval_ms: 100
            release: silence
            frame:
              base: last-rx
              mask: "00 00 F0 00 00 00 00 00"
              patch: "00 00 40 00 00 00 00 00"
```

`deadline_ms: 1000` limits the session and the signal command. `duration: 5000` tells the caller that this command has been observed to keep the indicator signaling for 5 seconds. `duration: latched` is the other informational value, for an effect observed to stay until another command changes it. `SIGNAL_OFF` is a separate command that ends the indicator sooner. The runtime does not turn the indicator off when those 5 seconds elapse. The wiper state lasts while the `wipers` endpoint transmits that one frame every 100 ms. The high nibble of byte 2 becomes `4`; every other bit stays as it was in the latest received frame. Stopping the repetition turns the wiper command off.

## Endpoints, ECU targets, and steps

### Channels

A channel is a logical CAN bus. Endpoints, inline signals, and manifest DBC files name a channel; the runtime maps each channel name to one of its controllers at activation. Channel names are portable: `can0` in a package means "the vehicle's first bus", and a runtime binds it to SocketCAN `can0`, adapter controller 0, or a serial adapter as it sees fit. A package never names a host interface.

| Channel field | Meaning |
|---|---|
| `protocol` | `can` for a classic controller or `canfd` for a CAN FD controller |
| `bitrate` | Nominal (arbitration) bitrate in bit/s, or `auto` for runtime detection. Omitted: 500000 |
| `configuration: runtime` | The runtime supplies the bitrate; excludes `bitrate` |
| `data_bitrate` | CAN FD data-phase bitrate in bit/s for frames sent with bit-rate switching. `canfd` only |
| `fd` | Default format of frames sent on this channel: `true`, `false`, or `{tx_dl: 8 \| 64}`. `canfd` only; omitted means classic |

Defaults:

- A missing `channel` on an endpoint, inline signal, signal source, or manifest DBC reference names `can0`.
- A referenced `can0` with no declaration is `{protocol: can, bitrate: 500000}`. Any other undeclared channel is an error.
- A declared channel without `bitrate` or `configuration` runs at 500000 bit/s.
- Resolved output materializes these defaults, so an exported document always states its channels and bitrates.

```yaml
channels:
  can0:
    protocol: can                # 500000 bit/s by default
  can1:
    protocol: canfd
    bitrate: auto                # the runtime searches the nominal rate only
    data_bitrate: 2000000
    fd: {tx_dl: 64}              # requests default to CAN FD with 64-byte ISO-TP frames
```

`auto` detects the nominal bitrate at activation. The data bitrate is never detected; declare `data_bitrate` on every channel that carries bit-rate-switched FD frames, even when the package never sends FD, or the controller cannot decode them. A failed detection leaves the channel unavailable rather than guessing. `configuration: runtime` defers the whole timing to the runtime, for packages that bind to several adapters. A channel declared by one package may be used by another in the same composition.

A `canfd` channel receives classic and FD frames without further declaration; `fd` only governs what the runtime sends. `fd: true` sends CAN FD with 8-byte ISO-TP frames; `{tx_dl: 64}` uses the ISO 15765-2:2016 escape form padded to 64 bytes. Sending FD on a `can` channel is an error, because classic nodes flag FD frames with error frames.

### Endpoints

An endpoint is the ECU a request targets. VSS supplies no addresses; the endpoint does. Property queries, writes, named queries, and actions name an endpoint instead of repeating CAN IDs, so two controllers on one bus are two endpoints, and a request reaches only the controller whose endpoint it names.

| Endpoint field | Meaning |
|---|---|
| `channel` | Channel the endpoint is on. Omitted: `can0` |
| `protocol` | `can` for raw frames or `isotp` for ISO-TP transport |
| `tx` | Transmit CAN ID |
| `rx` | Accepted response CAN IDs or inclusive `{range: [low, high]}` entries; omitted on a request-only endpoint |
| `responder` | Required when `rx` covers more than one ID: the one ID whose responses this endpoint accepts |
| `id_format` | `standard` or `extended` |
| `timeout_ms` | Response wait per request |
| `fd` | Request frame format, overriding the channel: `true`, `false`, or `{tx_dl: 8 \| 64}` (`isotp` only) |
| `addressing` | ISO-TP extended or mixed addressing (`isotp` only). Omitted: normal addressing |

```yaml
endpoints:
  body:
    channel: can0
    protocol: isotp
    tx: "745"
    rx: ["765"]
    id_format: standard
    timeout_ms: 300

  body-wake:
    channel: can0
    protocol: can
    tx: "60D"
    id_format: standard

  obd:
    channel: can1
    protocol: isotp
    tx: "7DF"
    rx: [{range: ["7E8", "7EF"]}]
    responder: "7E8"
    id_format: standard
    timeout_ms: 500

  legacy-ecu:
    channel: can1
    protocol: isotp
    tx: "7B0"
    rx: ["7B8"]
    id_format: standard
    timeout_ms: 500
    fd: false                    # a classic-only node on the FD channel
```

`body` is the Versa body control module. `body-wake` is request-only, so it has no `rx` and no `timeout_ms`. `rx` entries may not overlap and together cover at most 1000 IDs. Functional or multi-responder requests, such as `obd` above, require explicit `responder` selection; responses from other IDs in the range belong to other exchanges and are ignored. Separate per-responder results need separate endpoints.

The runtime sends each request in the first format it finds: the endpoint `fd`, then the channel `fd`, then classic. `tx_dl` is the ISO-TP frame size for requests and for the flow control the runtime returns, `8` or `64`. Raw CAN endpoints take only `fd: true` or `fd: false`; a raw request on a classic endpoint holds at most 8 data bytes and on an FD endpoint at most 64. Replies describe themselves by frame length, so response patterns and decoders do not change with `tx_dl`.

#### ISO-TP addressing

With normal addressing, the CAN IDs alone identify the two ends and the PCI is the first data byte. With extended and mixed addressing, every frame of the exchange in both directions carries one address byte in front of the PCI:

| Mode | Fields | Byte sent to the ECU | Byte the ECU sends back |
|---|---|---|---|
| `extended` | `target_address`, `source_address` | `target_address` (N_TA) | `source_address` (N_SA) |
| `mixed` | `address_extension` | `address_extension` (N_AE) | `address_extension` (N_AE) |

Each address is one hex byte, for example `"12"` or `F1`. Each mode accepts only its own fields.

```yaml
endpoints:
  dme:                           # BMW engine ECU, address 12; every ECU listens on 6F1
    protocol: isotp
    tx: "6F1"
    rx: ["612"]
    id_format: standard
    timeout_ms: 500
    addressing: {mode: extended, target_address: "12", source_address: F1}
```

Requests and response patterns stay application bytes. The adapter inserts the transmit address before the PCI and strips the receive address and PCI from each reply frame; a reply frame whose first byte is not the receive address is ignored. Flow control goes to `tx` with the transmit address first. The address byte takes one data byte from every frame, so a classic single frame carries 6 application bytes instead of 7. Normal fixed addressing, the 29-bit `18DAttss` scheme of OBD-II and UDS, needs no `addressing`: declare a 29-bit `tx` with `id_format: extended`.

Distinguish extended CAN IDs (`id_format`) from ISO-TP extended addressing (`addressing`). Missing protocol adapters make affected capabilities unavailable. For raw CAN endpoints, payloads and response patterns refer to the exact CAN data field. For ISO-TP endpoints, they refer to reassembled application payloads; adapters own PCI, padding, segmentation, and flow control. Do not infer framing from the first byte. The format 1 Versa profile sends raw frames that include the PCI byte and padding; a migration that must stay byte-exact keeps those endpoints as `protocol: can`.

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

Names are uppercase with underscores. When the standard keyword vocabulary lists the capability, for example `ECU_WAKE`, `WAKE_UP`, or `SIGNAL_OFF`, the package MUST use that name; other names are vehicle-specific. A keyword that maps to exactly one VSS actuator is a write on that path, with the keyword as an alias, and MUST NOT also be an action. `HORN` is therefore a write on `Vehicle.Body.Horn.IsActive`. `LOCK` and `UNLOCK` are aliases on `Vehicle.Cabin.IsCentralLockEngaged`, for targets `"true"` and `"false"`. `WIPERS` is a write on `Vehicle.Body.Windshield.Front.Wiping.Mode` for target `"MEDIUM"` when the command does not select a speed. `OPEN_FRONT_LEFT_WINDOW`, `OPEN_FRONT_RIGHT_WINDOW`, `OPEN_REAR_LEFT_WINDOW`, and `OPEN_REAR_RIGHT_WINDOW` write `100` on that door's `Window.Position`, and the matching `CLOSE_*_WINDOW` names write `0`. Left and right assume left-hand drive. `WINDOW_CHILD_LOCK` and `WINDOW_CHILD_UNLOCK` are the true and false cases of `Vehicle.Cabin.IsWindowChildLockEngaged`. A name MUST NOT be both a query and an action.

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

`ECU_WAKE` has no VSS actuator, and its steps have no `expect`, so its result is `sent`. `SIGNAL_OFF` turns off both indicators at once, and the catalog has no actuator for that pair, so it stays an action. An all-door lock is not an action: it is a write on `Vehicle.Cabin.IsCentralLockEngaged`.

Writes and actions default to no retries. A timeout after transmission can mean outcome unknown, not failure to execute. `idempotent` is an explicit semantic assertion and does not guarantee exactly-once ECU execution.

## Runtime results and discovery

Recommended SDK verbs: describe, get, read, subscribe, unsubscribe, set, invoke, cancel. `read` takes a property path or a query name, `set` takes an actuator path and target, and `invoke` takes an action name and input. This standard defines behavior, not a required language-specific method name or wire protocol.

An observation includes path or query name, value when valid, unit when applicable, source, acquisition kind, receivedAt, optional observedAt, clockDomain, sequence, and quality: valid/stale/invalid/unavailable. UTC timestamps use RFC3339; deadlines and ordering use monotonic clocks. Properties have isolated state per connected vehicle.

Executions report accepted/running/succeeded/failed/cancelled/unknown and evidence `sent` or `acknowledged`. Errors use stable codes: INVALID_PACKAGE, UNKNOWN_PATH, UNSUPPORTED, UNAVAILABLE, VEHICLE_MISMATCH, PERMISSION_DENIED, PRECONDITION_FAILED, TIMEOUT, NEGATIVE_RESPONSE, DECODE_ERROR, CONFLICT, CANCELLED, OUTCOME_UNKNOWN.

Discovery distinguishes defined capability, implementation support, applicability, current availability, and permission. Unmapped properties are explicitly unavailable. Unknown/mismatched applicability cannot automatically authorize writes or actions. Make/model/year declarations are not physical test evidence.

## Related pages

[VSS identity](vss.md) · [Decoders and request encoding](decoding.md) · [DBC references](dbc.md) · [Composition](composition.md) · [Fixtures](fixtures.md)
