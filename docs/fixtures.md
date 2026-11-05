# Fixtures

[Overview](../README.md) · [Documentation index](README.md)

A fixture records inputs and expected outcomes for a binding. The validator checks its structure and references; a consuming runtime executes it. See [validation layers](validation.md#validation-layers) for the distinction between structural checks, behavior, and physical evidence.

## Case format

A fixture file lists cases. Each case has a `kind` of `signal`, `query`, `write`, or `action`; a `path` for signals, writes, and property queries, or a `name` for named queries and actions; inputs from `frame`, `responses`, `target`, and `input`; and an `expect` holding any of `value`, `quality`, `sent`, `result`, and `error`.

```yaml
fixture: 1
cases:
  - label: lock acknowledged
    kind: write
    path: Vehicle.Cabin.IsCentralLockEngaged
    target: true
    responses: ["50 81", "50 C0", "70 38 01"]
    expect:
      sent: ["10 81", "10 C0", "30 38 00 01"]
      result: acknowledged

  - label: lock sent with no reply
    kind: write
    path: Vehicle.Cabin.IsCentralLockEngaged
    target: true
    responses: ["50 81", "50 C0"]
    expect: {result: unknown, error: OUTCOME_UNKNOWN}
```

The spec defines the fixture format; a validator checks that fixtures are well formed and name existing capabilities, and runtimes execute them. Every active binding should have positive and negative fixtures. Required cases include passive-plus-query acquisition for one property, no implicit polling, numeric targets with exact encoding, an unsupported case target, a failed acknowledgement, wrong responder, timeouts, unknown write or action outcomes, and unsupported required extensions.

OBDb compatibility is not an acceptance criterion. Cross-language claims require shared behavioral fixtures; vehicle-portability claims require demonstrated matching semantics on multiple vehicles.

## Case identifiers

Use `label` for the test description and `name` for a named query/action. Duplicate YAML keys are invalid and are rejected. Fixtures describe expected runtime outcomes; the CLI validates their structure and references but does not execute them.

## Related pages

[Validation layers](validation.md#validation-layers) · [Write acknowledgements](document.md#writes) · [Example packages](README.md#examples-and-resources)
