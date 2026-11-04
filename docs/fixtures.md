# Fixtures

Based on [Vehicle Binding Specification 0.4.0](../Vehicle_BInding_Standardv0.4.0.md). Format 2 tooling implements structural validation; vehicle execution is outside this repository.

## Validation, fixtures, and acceptance

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

A fixture file lists cases. Each case has a `kind` of `signal`, `query`, `write`, or `action`; a `path` for signals, writes, and property queries, or a `name` for named queries and actions; inputs from `frame`, `responses`, `target`, and `input`; and an `expect` holding any of `value`, `quality`, `sent`, `result`, and `error`.

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

## Fixture label clarification

Use `label` for the test description and `name` for a named query/action. The original source draft repeated `name` in its sample (now corrected); duplicate YAML keys are invalid and are rejected here. Fixtures describe expected runtime outcomes; the CLI validates their structure and references but does not execute them.
