# Validated fragments

A signal and query share one canonical property. This synthetic mapping is not vehicle evidence.

```yaml vprofile-fragment
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
    read:
      signal:
        channel: vehicle
        id: "100"
        id_format: standard
        length: 1
        decode: {byte: 0, bytes: 1, type: uint}
      query:
        endpoint: engine
        request: "01 0D"
        response: {prefix: "41 0D", min_data_bytes: 1}
        decode: {byte: 0, bytes: 1, type: uint}
      policy: {preferred: signal, max_age_ms: 500, active_fallback: false}
```

A synthetic discrete write uses a shared sequence and one supported case.

```yaml vprofile-fragment
channels:
  vehicle: {protocol: can, configuration: runtime}
endpoints:
  body: {channel: vehicle, protocol: can, tx: "745", id_format: standard}
sequences:
  pause: {steps: [{wait_ms: 5}]}
properties:
  Vehicle.Body.Horn.IsActive:
    write:
      cases:
        "true":
          endpoint: body
          deadline_ms: 100
          steps: [{call: pause}, {request: "01"}]
```

For a numeric setting use `request: {parts: ["AA BB", {input: value, type: uint, bytes: 1, scale: 0.5, offset: 16}]}` and `constraints: {min: 16, max: 30, step: 0.5}`. A target of 22 becomes `0C`; 22.25 is rejected. Shared query sources declare outputs once, then properties reference source/output. An overlay replaces whole entries, so repeat every field that remains needed. Fixture descriptions use label; action/query identifiers use name.

A shared query source supplies two properties. No interval is declared, so this does not request polling.

```yaml vprofile-fragment
channels:
  vehicle: {protocol: can, configuration: runtime}
endpoints:
  climate: {channel: vehicle, protocol: isotp, tx: "700", rx: ["708"], id_format: standard, timeout_ms: 300}
sources:
  temperatures:
    kind: query
    endpoint: climate
    request: "AA 01"
    response: {prefix: "BB 01", min_data_bytes: 2}
    outputs:
      ambient: {byte: 0, bytes: 1, type: uint, offset: -40, unit: Celsius}
      selected: {byte: 1, bytes: 1, type: uint, scale: 0.5, offset: 16, unit: Celsius}
properties:
  Vehicle.Cabin.HVAC.AmbientAirTemperature:
    read: {query: {source: temperatures, output: ambient}}
  Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature:
    read: {query: {source: temperatures, output: selected}}
    write:
      endpoint: climate
      request:
        parts: ["AA BB", {input: value, type: uint, bytes: 1, scale: 0.5, offset: 16}]
      expect: {prefix: "CC DD"}
      constraints: {min: 16, max: 30, step: 0.5}
```

A fixture for that synthetic binding:

```yaml vprofile-fixture
fixture: 1
cases:
  - label: Numeric setting acknowledged
    kind: write
    path: Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature
    target: 22
    responses: ["CC DD"]
    expect: {sent: ["AA BB 0C"], result: acknowledged}
  - label: Setting outcome unknown
    kind: write
    path: Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature
    target: 22
    responses: []
    expect: {result: unknown, error: OUTCOME_UNKNOWN}
```

This narrower document replaces a shared sequence when listed after its base document. It does not deep-merge steps.

```yaml vprofile-fragment
applies_to: {years: [2011]}
sequences:
  pause: {steps: [{wait_ms: 10}]}
```

A passive-only property requires no endpoint:

```yaml vprofile-fragment
channels:
  vehicle: {protocol: can, configuration: runtime}
properties:
  Vehicle.Speed:
    read:
      signal:
        channel: vehicle
        id: "100"
        id_format: standard
        length: 1
        decode: {byte: 0, bytes: 1, type: uint}
```
