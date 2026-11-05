# Historical format 1 reference

[Overview](../README.md) · [Documentation index](README.md)

On this page: [Core Architecture](#core-architecture) · [Standard Capability Keywords](#standard-capability-keywords) · [Standard PID Keywords](#standard-pid-keywords) · [File Structure](#file-structure) · [YAML Root Structure](#yaml-root-structure) · [Applicability Rules](#applicability-rules) · [DBC Rules](#dbc-rules) · [DBC File References](#dbc-file-references) · [Endpoint Rules](#endpoint-rules) · [Transaction Step Rules](#transaction-step-rules) · [Expect Matching Rules](#expect-matching-rules) · [Sequences](#sequences) · [Sequence References](#sequence-references) · [Signals](#signals) · [Queries](#queries) · [Actions](#actions) · [Runtime Profile Reloading](#runtime-profile-reloading) · [Historical scope](#historical-scope)

This document defines the stable vehicle capability vocabulary, the YAML profile
format and DBC responsibilities used by
`can-opener-js`.

## Core Architecture

`can-opener-js` separates these responsibilities:

- DBC files decode received CAN frames into named signals.
- YAML profiles define requests, command flows, monitor subscriptions,
  applicability, and references to DBC mappings.
- Transport implementation details are outside the current binding standard.

DBC never defines workflow. YAML never defines bit math.

DBC also owns physical decode metadata such as units, scaling, offsets, byte
order, signedness, ranges, and enum tables. YAML only points standardized
capability names at the DBC messages and signals that decode them.

## Standard Capability Keywords

These names are the stable app-facing vocabulary. Vehicle profiles map them to
vehicle-specific CAN IDs, request bytes, response IDs, and DBC mappings.

YAML profile keys must use the standardized names when a capability is listed in
this document. For capabilities not listed here, profiles may define additional
vehicle-specific names. DBC message and signal names should match the
standardized names when practical, but this is a recommendation rather than a
requirement because DBC files often reflect OEM, reverse-engineering, or tool
export naming.

### Actions

**Security and access**

- `UNLOCK`
- `LOCK`
- `OPEN_TRUNK`
- `CLOSE_TRUNK`
- `OPEN_FRUNK`
- `CLOSE_FRUNK`
- `ACTUATE_TRUNK_FRONT`
- `ACTUATE_TRUNK_REAR`

`OPEN_TRUNK` / `CLOSE_TRUNK` target the rear trunk explicitly. `OPEN_FRUNK` /
`CLOSE_FRUNK` target the front trunk (frunk). `ACTUATE_TRUNK_FRONT` /
`ACTUATE_TRUNK_REAR` are toggle-style commands for vehicles that do not
distinguish open from close in a single request.

**Windows**

- `OPEN_FRONT_LEFT_WINDOW`
- `CLOSE_FRONT_LEFT_WINDOW`
- `OPEN_FRONT_RIGHT_WINDOW`
- `CLOSE_FRONT_RIGHT_WINDOW`
- `OPEN_REAR_LEFT_WINDOW`
- `CLOSE_REAR_LEFT_WINDOW`
- `OPEN_REAR_RIGHT_WINDOW`
- `CLOSE_REAR_RIGHT_WINDOW`
- `WINDOW_CHILD_LOCK`
- `WINDOW_CHILD_UNLOCK`

Each `OPEN_*_WINDOW` command opens that window fully, and each `CLOSE_*_WINDOW`
command closes it fully. These commands take no opening percentage. Left and
right assume left-hand drive; review that mapping for a right-hand-drive
vehicle. `WINDOW_CHILD_LOCK` / `WINDOW_CHILD_UNLOCK` engage and release the
lock that disables the rear window switches.

**Vehicle control**

- `WAKE_UP`
- `ECU_WAKE`
- `REMOTE_START`

**Horn and lights**

- `HORN`
- `HIGH_BEAMS`
- `LOW_BEAMS`
- `RUNNING_LIGHTS`
- `LEFT_SIGNAL`
- `RIGHT_SIGNAL`
- `HAZARD_LIGHTS`

**Climate**

- `CLIMATE_ON`
- `CLIMATE_OFF`
- `SET_TEMPERATURE`
- `AUTO_CONDITIONING_START`
- `AUTO_CONDITIONING_STOP`
- `DEFROST_ON`
- `DEFROST_OFF`

**Charging**

- `CHARGE_START`
- `CHARGE_STOP`
- `CHARGE_PORT_OPEN`
- `CHARGE_PORT_CLOSE`
- `SET_CHARGE_LIMIT`
- `SET_CHARGING_AMPS`
- `ADD_CHARGE_SCHEDULE`
- `REMOVE_CHARGE_SCHEDULE`
- `ADD_PRECONDITION_SCHEDULE`
- `REMOVE_PRECONDITION_SCHEDULE`

**Software**

- `SCHEDULE_SOFTWARE_UPDATE`
- `CANCEL_SOFTWARE_UPDATE`

### Queries

Queries expose supported PIDs and structured diagnostic reads. The common query
namespace is the PID list below.

### Signals

**Drivetrain**

- `SPEED`
- `RPM`
- `TPS`
- `STEERING_ANGLE`
- `GEAR`
- `ODOMETER`

**Body and lights**

- `LEFT_SIGNAL`
- `RIGHT_SIGNAL`
- `BRAKE_LIGHTS`
- `RUNNING_LIGHTS`
- `LOW_BEAMS`
- `HIGH_BEAMS`
- `REVERSE_LIGHTS`

**Doors and security**

- `FRONT_LEFT_DOOR_OPEN`
- `FRONT_RIGHT_DOOR_OPEN`
- `REAR_LEFT_DOOR_OPEN`
- `REAR_RIGHT_DOOR_OPEN`
- `LOCKED`

**Fuel**

- `FUEL_LEVEL`

**Charging**

- `BATTERY_LEVEL`
- `BATTERY_RANGE`
- `ESTIMATED_RANGE`
- `IDEAL_RANGE`
- `CHARGING_STATE`
- `CHARGE_PORT_OPEN`
- `CHARGE_LIMIT_SOC`
- `CHARGER_VOLTAGE`
- `CHARGER_CURRENT`
- `CHARGER_POWER`
- `CHARGE_RATE`
- `TIME_TO_FULL_CHARGE`
- `CHARGE_ENERGY_ADDED`
- `PLUGGED_IN`

**Climate**

- `CLIMATE_ON`
- `CABIN_TEMP`
- `OUTSIDE_TEMP`
- `DRIVER_TEMP_SETTING`
- `PASSENGER_TEMP_SETTING`

`TPS` means throttle position.

Standard signal values should use these script-facing domains. Numeric units
come from the DBC. Enum labels come from DBC `VAL_` entries unless a profile
uses `normalize.enum` to translate car-specific labels:

- `SPEED`: number, typically `km/h`
- `RPM`: number, typically `rpm`
- `TPS`: number, typically `%`
- `STEERING_ANGLE`: number, typically `deg`
- `FUEL_LEVEL`: number, typically `%`
- `ODOMETER`: number, typically `km`
- `LEFT_SIGNAL`, `RIGHT_SIGNAL`, `BRAKE_LIGHTS`, `LOW_BEAMS`, `HIGH_BEAMS`,
  `PLUGGED_IN`, `CLIMATE_ON`: `"off"` or `"on"`
- `LOCKED`: `"off"` (unlocked) or `"on"` (locked)
- `FRONT_LEFT_DOOR_OPEN`, `FRONT_RIGHT_DOOR_OPEN`, `REAR_LEFT_DOOR_OPEN`,
  `REAR_RIGHT_DOOR_OPEN`, `CHARGE_PORT_OPEN`: `"closed"` or `"open"`
- `GEAR`: `"park"`, `"reverse"`, `"neutral"`, or `"drive"`
- `CHARGING_STATE`: `"disconnected"`, `"stopped"`, `"charging"`, or
  `"complete"`
- `BATTERY_LEVEL`, `CHARGE_LIMIT_SOC`: number, typically `%`
- `BATTERY_RANGE`, `ESTIMATED_RANGE`, `IDEAL_RANGE`: number, typically `km`
- `CHARGER_VOLTAGE`: number, typically `V`
- `CHARGER_CURRENT`: number, typically `A`
- `CHARGER_POWER`: number, typically `kW`
- `CHARGE_RATE`: number, typically `km/h`
- `TIME_TO_FULL_CHARGE`: number, typically `h`
- `CHARGE_ENERGY_ADDED`: number, typically `kWh`
- `CABIN_TEMP`, `OUTSIDE_TEMP`, `DRIVER_TEMP_SETTING`,
  `PASSENGER_TEMP_SETTING`: number, typically `°C`

If no `normalize` block is declared, the script-facing value is the DBC-decoded
value. Signals with a matching DBC `VAL_` entry return the enum label; other
numeric signals return the DBC-scaled physical number.

## Standard PID Keywords

Profiles may support any subset of these basic PIDs:

- `RPM`
- `SPEED`
- `ECT`
- `IAT`
- `MAP`
- `MAF`
- `TPS`
- `STFT_B1`
- `LTFT_B1`
- `STFT_B2`
- `LTFT_B2`
- `FUEL_PRESSURE`
- `TIMING_ADVANCE`
- `ENGINE_LOAD`
- `RUNTIME`
- `FUEL_LEVEL`
- `DIST_SINCE_CLEAR`
- `BARO`
- `LAMBDA`
- `O2_DATA`
- `MODULE_VOLTAGE`
- `OIL_TEMP`
- `DRIVER_TORQUE_DEMAND`
- `ACTUAL_TORQUE`
- `FUEL_RATE`
- `ODOMETER`
- `VIN`
- `MIL_STATUS`
- `READINESS_STATUS`

## File Structure

Vehicle definitions are grouped by folder. Each folder may contribute partial
definitions:

```text
vehicles/
  universal/
    profile.yaml
    signals.dbc

  nissan/sentra/
    profile.yaml
    signals.dbc
```

Profiles merge by applicability, with the most-specific match winning.

## YAML Root Structure

Only `version` is required.

```yaml
version: 1

applies_to: {}

dbc:
  files: []

endpoints: {}

sequences: {}

signals: {}

queries: {}

actions: {}
```

## Applicability Rules

`applies_to` describes which vehicles a YAML profile and its DBC files support.
If `applies_to` is omitted, the profile is universal and applies to all makes and
models. Standard OBD-II PID profiles are a typical universal profile.

Supported keys:

- `manufacturers`
- `models`
- `years`
- `trims`
- `engines`
- `markets`

Missing fields act as wildcards.

```yaml
applies_to:
  manufacturers: [Nissan]
  models: [Sentra, Versa]
  years:
    - 2010
    - 2011
    - range: [2012, 2015]
  trims: [S, SV]
  engines: [2.0L]
  markets: [NA]
```

Year ranges are inclusive:

```yaml
years:
  - range: [2010, 2015]
```

This matches model years 2010 through 2015.

## DBC Rules

DBC files decode received CAN payloads only.

Use DBC for:

- passive broadcast frames
- request/response diagnostic replies
- UDS positive responses
- ECU status messages
- sensor values

Do not use DBC for:

- command flows
- multi-step transactions
- security or session setup
- tester-present keepalive
- applicability logic

DBC message IDs must be real CAN response IDs, not invented logical IDs.

```dbc
VERSION ""

BU_: Tester ECU

BO_ 2024 OBD_Response: 8 ECU
 SG_ vehicle_speed : 24|8@1+ (1,0) [0|255] "km/h" Vector__XXX

BO_ 1893 Body_Response: 8 ECU
 SG_ response_service : 8|8@1+ (1,0) [0|255] "" Vector__XXX
 SG_ routine_high     : 16|8@1+ (1,0) [0|255] "" Vector__XXX
 SG_ routine_low      : 24|8@1+ (1,0) [0|255] "" Vector__XXX
 SG_ routine_status   : 32|8@1+ (1,0) [0|255] "" Vector__XXX
```

In this example, `0x7E8` is decimal `2024` and `0x765` is decimal `1893`.

## DBC File References

Profiles reference DBC files by relative path:

```yaml
dbc:
  files:
    - path: signals.dbc
```

## Endpoint Rules

An endpoint defines a reusable request/response transport target.

```yaml
endpoints:
  obd:
    request_id: 0x7DF
    response_ids:
      - range: [0x7E8, 0x7EF]
    timeout_ms: 500

  body:
    request_id: 0x745
    response_id: 0x765
    timeout_ms: 500
```

Rules:

- `request_id` is one transmit CAN ID.
- `response_id` is one accepted response CAN ID.
- `response_ids` is a list of accepted response IDs and ranges.
- Endpoints are reused by queries, actions, and sequences.

## Transaction Step Rules

A step is one request transaction.

```yaml
- send: [0x10, 0x81]
  expect: [0x50, 0x81]
```

This sends bytes, waits for a response, and validates the response prefix. If
`expect` is omitted, the step sends bytes only and does not wait for a response.
`send` and `expect` always belong to the same step.

## Expect Matching Rules

`expect` is a response pattern. By default, an `expect` array is a prefix match
and extra response bytes are ignored.

```yaml
expect: [0x41, 0x0D]
```

This matches `41 0D 00`, `41 0D 7F`, and any other response starting with
`41 0D`.

Use `"*"` as a wildcard byte:

```yaml
expect: [0x70, 0x30, "*"]
```

This matches `70 30 00`, `70 30 01`, and `70 30 FF`.

Use exact matching when extra response bytes should fail validation:

```yaml
expect:
  pattern: [0x70, 0x30, 0x01]
  exact: true
```

Omitted `expect` means no response wait.

## Sequences

Sequences are reusable step groups intended for shared setup logic.

```yaml
sequences:
  body_session_prep:
    steps:
      - send: [0x10, 0x81]
        expect: [0x50, 0x81]

      - send: [0x10, 0xC0]
        expect: [0x50, 0xC0]
```

Rules:

- Sequences are expanded inline.
- Sequences may be nested.
- Circular references are invalid.

## Sequence References

A step may reference another sequence:

```yaml
- ref: sequences.body_session_prep
```

Example:

```yaml
actions:
  HORN:
    endpoint: body
    steps:
      - ref: sequences.body_session_prep
      - send: [0x30, 0x30, 0x00, 0x01]
        expect: [0x70, 0x30, 0x01]
```

Rules:

- References expand in place.
- Circular references are invalid.
- A referenced sequence inherits the command endpoint unless it declares its own
  endpoint.

## Signals

Signals represent passively collected values. They are usually broadcast at a
regular cadence on the CAN bus and decoded with a DBC file.

```yaml
signals:
  STEERING_ANGLE:
    monitor:
      message: STEERING
      signal: STEERING_ANGLE
```

Default value behavior:

- If the DBC signal has a matching `VAL_` entry, state is updated with that enum
  label.
- Otherwise, state is updated with the DBC-scaled physical value.
- Profile `normalize.enum` is optional and runs after DBC decode.

Use `normalize.enum` only when the DBC labels need to be translated into the
portable profile vocabulary:

```yaml
signals:
  LOW_BEAMS:
    monitor:
      message: BODY_STATUS
      signal: HEADLAMP_STATE
    normalize:
      enum:
        inactive: off
        active: on
```

## Queries

Queries are request/response reads from the CAN bus, typically to an ECU that
responds with a CAN frame. They are used for PIDs, UDS reads, VIN, serial
numbers, ASCII strings, multi-frame identifiers, and status blobs.

DBC-backed queries use `dbc_mapping` to point a standard YAML query name to the
DBC message and signal that decode the response payload. The DBC owns units,
scaling, offsets, byte order, signedness, and enum tables.

```yaml
queries:
  SPEED:
    endpoint: obd
    send: [0x01, 0x0D]
    expect: [0x41, 0x0D]
    dbc_mapping:
      message: OBD_Response_7E8
      signal: SPEED
```

Queries follow the same value rules as monitored signals. DBC enum labels are
returned by default, numeric DBC signals return physical values by default, and
optional `normalize.enum` remaps labels after decode:

```yaml
queries:
  GEAR:
    endpoint: obd
    send: [0x22, 0x12, 0x34]
    expect: [0x62, 0x12, 0x34]
    dbc_mapping:
      message: Body_Response
      signal: TRANSMISSION_STATE
    normalize:
      enum:
        P: park
        R: reverse
        D: drive
```

Use `decoder` only for built-in non-DBC decoders:

```yaml
queries:
  VIN:
    endpoint: obd
    send: [0x09, 0x02]
    expect: [0x49, 0x02]
    decoder: ascii
    length: 17
```

Supported built-in decoder forms:

```yaml
decoder: ascii
length: 17
```

```yaml
decoder: bytes
```

```yaml
decoder:
  type: ascii
  length: 17
```

```yaml
decoder:
  type: bytes
  length: 8
```

Built-in decoders operate on the response payload after the `expect` prefix is
removed. `ascii` returns a string and trims trailing null bytes. `bytes` returns
raw bytes. `length` limits the number of bytes consumed by the decoder.

Queries use request/response acquisition.

## Actions

Actions change vehicle state. They may be request-only, verified
request/response, or multi-step flows.

### send forms

The `send` field accepts two forms:

- **Array form** `send: [0x30, 0x38, ...]`: requires `endpoint` to supply the
  transmit CAN ID and optional response bounds.
- **Object form** `send: {request_id: 0x123, request: [...]}`: embeds the
  transmit CAN ID inline. No `endpoint` is needed. This form is always
  request-only; response bounds and timeouts are not inherited from any
  endpoint.

Actions with no `send` and no `steps` are silently skipped during profile
loading.

Single request (inline `request_id`, no endpoint required):

```yaml
actions:
  LEFT_SIGNAL:
    send:
      request_id: 0x123
      request: [0x01, 0x00, 0x00, 0x00]
```

Verified request/response (array `send`, endpoint required):

```yaml
actions:
  LOCK:
    endpoint: body
    send: [0x30, 0x38, 0x00, 0x01]
    expect: [0x70, 0x38, 0x01]
```

Multi-step flow:

```yaml
actions:
  HORN:
    endpoint: body
    steps:
      - ref: sequences.body_session_prep
      - send: [0x30, 0x30, 0x00, 0x01]
        expect: [0x70, 0x30, 0x01]
```

Actions may return nothing. If `expect` validation is used, actions return
boolean success or failure.

## Runtime Profile Reloading

`VirtualVehicle.reloadProfiles(sources)` replaces the loaded capability set
at runtime without reconnecting. This is useful for staged loading: connect
with a minimal profile (for example, OBD-II PIDs only) to read the VIN, then
call `reloadProfiles` with the full vehicle-specific profile set after
discovery.

Profile reload rebuilds capabilities and DBC bindings from scratch. Active
monitors are not automatically restarted; the caller should re-subscribe after
reloading.

Batch `subscribe([...])` calls skip signals that cannot be resolved against the
currently loaded DBC. This makes it safe to call subscribe with a superset of
signal names before or after a reload.

## Historical scope

The original firmware interface material is excluded here.

## Related pages

[Migration command](migration.md#implemented-migration) · [Current binding format](document.md) · [Keyword mappings](vocabulary.md)
