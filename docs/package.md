# Package and file format

[Overview](../README.md) · [Documentation index](README.md)

## Package and file format

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

## Related pages

[Manifest fields](manifest.md) · [Composition](composition.md) · [Integrity checks](validation.md#tool-commands-and-limits)
