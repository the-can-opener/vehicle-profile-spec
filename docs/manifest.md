# Manifest and applicability

[Overview](../README.md) · [Documentation index](README.md)

## Manifest and documents

| Manifest field | Meaning |
|---|---|
| `manifest` | Container version; `1` |
| `format` | Document grammar; `2` is this format. Format 1 documents are rejected with a pointer to migration |
| `id` | Reverse-DNS identifier, stable across package versions |
| `version` | Semver of this package |
| `name` | Human-readable name |
| `vss` | Pinned VSS release, for example `"6.1"` |
| `applies_to` | Package-wide applicability |
| `dbc` | Map from a DBC id to `{path, channel, sha256?}` |
| `documents` | Ordered list; each entry has `path` and may set `applies_to` and `override` |
| `fixtures` | [Fixture files](fixtures.md) |
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
  - path: actions.yaml

fixtures:
  - fixtures/body.yaml

unmapped:
  - {capability: IDEAL_RANGE, reason: "VSS has no ideal or rated range separate from remaining range"}
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

## Related pages

[Package safety](package.md) · [Document sections](document.md) · [Applicability and overlays](composition.md) · [Fixtures](fixtures.md)
