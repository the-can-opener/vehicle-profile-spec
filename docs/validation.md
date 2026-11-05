# Validation and CLI

[Overview](../README.md) · [Documentation index](README.md)

On this page: [Validation layers](#validation-layers) · [Tool commands and limits](#tool-commands-and-limits) · [Strict exceptions and acceptance checks](#strict-exceptions-and-acceptance-checks) · [Remaining validation work](#remaining-validation-work)

## Validation layers

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

The [fixture reference](fixtures.md) defines cases, expected outcomes and behavioral coverage. Fixtures do not establish physical vehicle compatibility by themselves.

## Tool commands and limits

`vprofile export json --package PATH --strict` performs container, grammar, reference, catalog, composition, extension and fixture-reference checks. Omit `--strict` to ignore unknown fields; value and reference checks still run. Unsupported required extensions fail explicitly. No runtime provider is bundled.

`--vehicle make=Nissan,model=Versa,year=2011` selects applicable documents. Without a selector all variants are inspected in manifest order; this is a tooling view, not authorization to activate unknown vehicle applicability. `-l PATH` loads another package as a later overlay. `resolve --packages BASE --packages OVERLAY` loads ordered packages and checks dependency ranges. `--integrity-required` requires SHA-256 on every listed asset. Manifest self-hashing is not required.

Readers enforce 4 MiB per file, 16 MiB per package, 1000 listed/archive entries, and 100:1 maximum ZIP compression ratio. Directory readers inspect only listed assets; ZIP readers additionally reject unlisted executable assets. JSON-compatible YAML rejects non-string or duplicate keys, tags, anchors, aliases and nonfinite values. Date-like strings stay strings.

`compose --package PATH -o package.zip` creates a deterministic archive of listed files; `compose --verify package.zip` reruns validation. `diff OLD NEW` compares resolved entries. Exports support json, tree, csv and property-value jsonschema. Checked-in authoring schemas are generated separately with `make schemas`; Pydantic and semantic checks enforce rules that JSON Schema alone cannot express.

See [generated error codes](../skills/validating-vehicle-profiles/error-codes.md). A schema-only success is not complete validation.

## Strict exceptions and acceptance checks

`export` and `resolve` accept `--strict-exceptions FILE` together with `--strict`. The file is a YAML/JSON list of objects with `path` (an exact JSON Pointer relative to a document root) and a nonempty `reason`. Example: `[{path: /properties/Vehicle.Speed/vendor_note, reason: vendor annotation}]`.

Only unknown fields can be excepted. Known fields, conflicting binding forms, references, applicability and VSS errors cannot be suppressed this way. Used exceptions are reported on stderr and in `--log-file`. Exceptions are never enabled implicitly by an authoring skill.

`make mandatory_targets` runs tests, lint/format, type checks, generated-file checks, every non-legacy example, and an isolated wheel build/resource check. Wheel output is temporary. `make clean` removes disposable build/test caches but retains `tools/.venv` and all checked-in artifacts. Sequence validation is bounded to 64 nested calls and 10000 visited expanded steps.

## Remaining validation work

The implementation does not yet prove full decoder-output compatibility with every VSS datatype and range, and manifest DBC channel references need a dedicated resolution check. The document authoring schema permits null deletions but still describes complete typed entries; earlier partial entries that are replaced before validation are accepted by the merge pipeline, not by that standalone schema. These gaps are tracked in the [implementation plan](../vehicle_profile_format_2_6ee96dce.plan.md#remaining-work-at-wrap-up).

## Related pages

[Package safety](package.md) · [Fixture format](fixtures.md) · [Error codes](../skills/validating-vehicle-profiles/error-codes.md) · [Migration](migration.md)
