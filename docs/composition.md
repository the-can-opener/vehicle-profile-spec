# Composition and overlays

[Overview](../README.md) · [Documentation index](README.md)

## Composition

Documents load in manifest order. Keyed sections merge by key: `endpoints`, `sources`, `properties`, `sequences`, `queries`, and `actions`.

- A later document replaces the whole entry for a key; entries are not deep-merged.
- `KEY: null` deletes an entry defined earlier.
- A document's `applies_to` is intersected with the manifest's and MUST NOT widen it.
- References (endpoints, sources, sequence calls, DBC names) resolve after the merge.

Packages load in host order; universal, then make, model, and year is recommended. Each `depends` entry must be satisfied earlier in the order. The same key defined by two packages is a conflict unless the later document sets `override: true`.

## Related pages

[Manifest applicability](manifest.md) · [Shared sequences](document.md#sequences) · [Validation](validation.md)
