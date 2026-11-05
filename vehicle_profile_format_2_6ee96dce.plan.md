---
name: Vehicle profile format 2
overview: Rewrite vehicle-profile-spec around a package container whose documents use flat VSS paths with read/write bindings (format 2), where a write carries its own steps and a matched expect is the acknowledgement. Format 1 is retired and handled only by a migration command. Ship docs, JSON schemas, a pinned VSS catalog, example packages, a Python validator (vprofile) with vss-tools-style tests and CI, and agent skills for authoring, validating, and migrating profiles that install by copying the folders, running scripts/install-skills.sh, or running vprofile skills install. The maintained standard is in docs/README.md.
todos:
  - id: docs-core
    content: Write docs/package.md, manifest.md, document.md (read/write/steps/expect/sequences/actions/endpoints), decoding.md, composition.md
    status: completed
  - id: docs-vss
    content: Write docs/vss.md, docs/vocabulary.yaml (keyword -> VSS path/target/action), extensions.md, fixtures.md, validation.md
    status: completed
  - id: docs-move
    content: Move DBC sections to docs/dbc.md; write authoring-guide.md, migration.md; rewrite README.md as overview and index
    status: completed
  - id: catalog
    content: Generate catalog/vss-6.1.json from vehicle_signal_specification via vspec export json; add make catalog and catalog/README.md
    status: completed
  - id: tools-models
    content: "tools/: pyproject, cli.py, cli_options.py, container.py, manifest.py, model.py (DocumentRaw + typed write shapes), strict.py, dbc.py, codec.py"
    status: completed
  - id: tools-pipeline
    content: "tools/: merge.py, resolve.py, catalog.py, exporters (json/tree/csv/jsonschema), compose.py, diff.py"
    status: completed
  - id: tools-migrate
    content: "tools/: migrate.py converting format 1 folders to format 2 packages using vocabulary.yaml, with unmapped report"
    status: completed
  - id: schemas
    content: Generate schemas/manifest, document, fixture .schema.json from models; CI drift check
    status: completed
  - id: examples
    content: Create examples/nissan-versa (migrated + split + overlay + fixtures), universal-obd, hvac-synthetic, legacy/nissan-versa-1-6
    status: completed
  - id: tests
    content: tests/packages positive and negative cases, unit tests for dbc/codec/merge/catalog, test_migrate over the legacy Versa folder
    status: completed
  - id: skills-content
    content: "Write skills/authoring-vehicle-profiles, skills/validating-vehicle-profiles, skills/migrating-vehicle-profiles (SKILL.md + reference files); generate error-codes.md from the error enum"
    status: completed
  - id: skills-install
    content: "skills/README.md with manual copy instructions; scripts/install-skills.sh and tools/ skills.py + vprofile skills list/install (same flags: --agent cursor|claude|codex|all, --project, --dir); bundle skills/ into the wheel via hatch force-include"
    status: completed
  - id: vss-lookup
    content: "tools/: vprofile vss search/show over the pinned catalog, used by the authoring skill"
    status: completed
  - id: skills-tests
    content: tests/test_skills.py (frontmatter limits, fragment validation, error-codes drift) and tests/test_install_skills.py (script and vprofile output both match skills/ for each target; wheel contains skills)
    status: completed
  - id: ci
    content: Makefile mandatory_targets (includes skills checks), .github/workflows/buildcheck.yml, .pre-commit-config.yaml, noxfile.py, CHANGELOG.md 2.0.0
    status: completed
  - id: remaining-dbc-channels
    content: Resolve loaded manifest DBC channel references against the composed channels; add missing/deleted-channel and cross-package regression tests.
    status: pending
  - id: remaining-decoder-vss
    content: Validate decoder result types and representable domains against VSS across inline, DBC and shared-source reads; distinguish static failures from runtime value checks.
    status: pending
  - id: remaining-raw-schema
    content: Generate distinct raw-document and resolved-document schema contracts so replaceable partial entries are authorable without weakening final typed validation.
    status: pending
  - id: remaining-migration-zip-goldens
    content: Add deterministic CLI golden exports for migrated packages and ZIP round trips, including vehicle selection, unmapped reports and error locations.
    status: pending
  - id: remaining-fixture-coverage
    content: Inventory active example bindings; add positive and negative fixtures for each and a coverage check that prevents omissions.
    status: pending
  - id: remaining-python311-ci
    content: Run the full acceptance target on Python 3.11 and 3.13, fix compatibility failures, and record successful remote CI evidence when available.
    status: pending
  - id: remaining-final-review
    content: Reconcile documentation and task statuses with verified behavior, run final acceptance and reproducibility checks, then remove disposable artifacts.
    status: pending
isProject: false
---

# Vehicle profile format 2

Before implementation, the repo held a single README (now preserved as [format-1.md](docs/format-1.md)) describing format 1: keyword names (`SPEED`, `LOCK`), sections for `signals`, `queries`, and `actions`, and byte arrays. This plan replaces that format with format 2:

- **Container:** a package with one manifest, from the earlier package plan.
- **Documents:** [format 2 standard](docs/README.md), including named queries/actions, inline writes, and acknowledgement semantics. The maintained topic pages define the current format.

Format 1 is no longer loaded. `vprofile migrate` converts it to format 2.

## Implementation record — 4 November 2026

Implemented the package reader, typed grammar, merge/reference/catalog checks, pure codecs and target preparation, CLI exports/compose/resolve/diff, explicit-framing migration, generated schemas, full pinned VSS 6.1 catalog, examples, CI and installable agent skills.

The last full `make mandatory_targets` run passed **111 tests**, lint/format, mypy, generated-file checks, strict example validation and an isolated wheel/resource check on Python 3.13. The configured Python 3.11 CI job and remote CI have not been run here. Work was stopped at the user's request; this record does not claim full plan completion.

Implemented reference alignment:

- Named `queries` and `actions` replace the earlier operations design. LOCK/UNLOCK remain multi-door actions; HORN is an actuator write with only a true case.
- Fixture descriptions use `label`; `name` identifies a named capability. Duplicate keys are rejected.
- Request-only endpoints omit response settings. Multi-responder endpoints require an explicit `responder`.
- Catalog source: v6.1 tag, commit `2817646d1808fc7c470c0432fc7f4ed685e5c9e3`, exported with vss-tools 1.9.9.
- Migration supports raw/application/single-frame ISO-TP declarations, DBC query offsets, fixed VIN/hex queries, shared sequences, patterns, cases and passive-plus-query merging. It validates output before writing the destination. Uncertain or unsupported inputs retain their original objects in `unmapped`.
- The Versa example is reproducibly generated from the retained legacy input using an explicit single-frame framing declaration and left-hand-drive mapping. Request-only frames remain byte-exact; request/response bindings use ISO-TP application bytes rather than invented raw receive PCI. Its 2011 timing overlay is synthetic and changes the shared sequence by inserting a 10 ms wait.
- `export`/`resolve` support exact unknown-field exceptions, logged with reasons. Core-field and semantic errors cannot be excepted.
- The mandatory target now builds and checks a wheel in temporary storage. `make clean` removes disposable caches/build output and retains the development environment.

### Remaining work at wrap-up

The completed frontmatter items record the implemented baseline, not full conformance. The `remaining-*` tasks are the outstanding work. The historical 111-test result is the starting point; do not treat it as verification of future changes.

Work in the following order. DBC/reference checks and decoder semantics come first, followed by schema alignment and acceptance coverage. Finish with the version matrix and cleanup. This update is a plan only; none of these pending tasks has been implemented or verified by this update.

#### 1. Resolve DBC channels (`remaining-dbc-channels`)

Relevant files: `tools/src/vehicle_profile_tools/resolve.py`, `manifest.py`, and reference/composition tests.

- Retain each loaded DBC asset's declared channel alongside its package-qualified ID.
- Resolve that channel against the final composed channel map, after applicability filtering and replacements/deletions. Use the same channel namespace as endpoints and inline signals.
- Report a missing channel with a stable error code and an actionable location identifying the package, DBC ID and channel field. Reuse `DOC_INVALID` unless a dedicated reference code is justified; regenerate error documentation if codes change.
- Cover a valid local channel, an unknown channel, a channel deleted by an overlay, and a channel provided by an earlier dependency. Exercise directory and ZIP loading.

Acceptance: valid composed references load; invalid DBC channel references fail strict CLI validation with the expected code and location. Existing packages still pass.

#### 2. Complete decoder/VSS compatibility checks (`remaining-decoder-vss`)

Relevant files: `catalog.py`, `resolve.py`, `dbc.py`, `codec.py`, and their unit/integration tests.

- Apply one compatibility policy to inline signals, inline queries, DBC bindings and shared-source outputs. Check every consumer of a shared output independently.
- Account for extraction type and width, signedness, scaling/offset, boolean conversion, raw enums and invalid encodings before comparing the result with the canonical datatype, allowed values and range.
- Reject provably incompatible result types, such as strings for numeric properties or fractional transformations that cannot preserve an integer datatype. Check enum result values and explicitly declared output datatypes consistently.
- Distinguish static compatibility from runtime observation validation. A wire field's full representable range is not necessarily its valid observation domain; document which out-of-domain values produce invalid observations instead of rejecting otherwise valid bindings.
- Keep exact numeric encoding and constraint-grid checks. Do not introduce implicit rounding, clamping, unit conversion, or fabricated enum defaults.

Acceptance: positive and negative tests cover numeric widths/signs, fractional scaling, booleans, enum values, string/numeric mismatches, range handling and shared consumers. Failures identify the canonical property and binding. Documentation states which checks remain the runtime's responsibility.

#### 3. Align raw and resolved schemas (`remaining-raw-schema`)

Relevant files: `model.py`, `exporters/jsonschema.py`, `schema_rules.py`, `scripts/generate.py`, `schemas/`, and schema/merge tests.

- Separate the raw authoring contract from the fully composed typed contract. Raw documents may contain partial keyed entries that a later document replaces, plus null deletions.
- Keep strict final validation after composition. Whole-entry replacement must remain whole-entry replacement; partial entries must not introduce deep merging.
- Choose and document clear schema names/references for authoring versus resolved data. Update single-file manifest embedding, examples, skill references and generated-file checks accordingly.
- Preserve top-level field restrictions, JSON-compatible keys and safety rules. Do not make the resolved schema permissive merely to accept partial authoring inputs.

Acceptance: an incomplete entry replaced by a complete later entry passes raw-schema and package validation; the same incomplete entry surviving composition fails final validation. Test null deletion, unknown fields, exclusive forms and single-file packages. Generated schemas remain drift-free.

#### 4. Finish migration and ZIP golden tests (`remaining-migration-zip-goldens`)

Relevant files: `tests/packages/`, `tests/test_golden_cli.py`, `test_migrate.py`, `test_packages.py`, and `scripts/migrate-versa.py`.

- Add checked-in expected CLI JSON output for migration, including combined signal/query properties, actuator cases, named queries/actions and retained unmapped records.
- Exercise declared raw and ISO-TP single-frame migration. Check exact preservation of raw bytes or the declared application-payload conversion, wildcard/exact matching, responder selection and prefix-relative DBC offsets.
- Add expected resolved exports for composed ZIPs and compare them with directory exports. Verify deterministic archive bytes and both year selections for the overlay example.
- Exclude temporary absolute paths and timestamps from snapshots. Retain focused assertions for behavior so snapshots are not the only checks.
- Ensure the remaining negative CLI cases assert nonzero exit, stable code and offending location. Inexact target preparation remains a pure-codec check; structural fixture validation must not be described as fixture execution.

Acceptance: migration and ZIP scenarios join the existing snapshot matrix and pass through the actual CLI. Repeated runs are deterministic; `scripts/migrate-versa.py --check` confirms the example is reproducible.

#### 5. Complete example fixture coverage (`remaining-fixture-coverage`)

Relevant files: the three non-legacy example packages, their fixture files, and fixture tests.

- Inventory each active signal, property query, named query, actuator write and action after composition. Include both acquisition kinds on dual-read properties and applicable overlay variants.
- Add a meaningful positive and negative fixture for every active binding. Cover supported write targets, unsupported case targets, invalid/short inputs, acknowledgement failures, wrong responders, timeouts and unknown outcomes as applicable.
- Preserve shared-source and no-implicit-polling examples. Keep unsupported-extension rejection in negative package tests, rather than making a positive example require an unavailable provider.
- Add a coverage test that relates fixtures to the active binding inventory and reports omissions. Do not invent unverified vehicle observations; label synthetic expectations and retain source provenance.

Acceptance: every active example binding has documented positive and negative fixture coverage, all fixture references validate, and the coverage check runs in the mandatory target. Fixtures remain runtime inputs; the Python validator does not execute vehicle behavior.

#### 6. Verify supported Python versions and CI (`remaining-python311-ci`)

Relevant files: `tools/pyproject.toml`, `tools/uv.lock`, `Makefile`, `noxfile.py`, and `.github/workflows/buildcheck.yml`.

- Use the locked dependencies to run the full acceptance target on Python 3.11 and Python 3.13 in separate environments.
- Include lint/format, types, tests, generated-file checks, strict example validation, skill checks and isolated wheel/resource verification. Resolve compatibility or packaging failures without dropping a supported version.
- Confirm the remote workflow runs equivalent checks and record the successful run URL/commit when a remote run is available. Keep remote verification pending until there is actual evidence.

Acceptance: both local version runs pass and remote CI is green for the reviewed revision. Record exact versions, commands and results rather than only the test count.

#### 7. Final review and cleanup (`remaining-final-review`)

- Reconcile README, validation/migration docs, schemas, examples and skills with the final behavior. Remove stale limitations only when a test demonstrates they are resolved.
- Run `make mandatory_targets` and `scripts/migrate-versa.py --check` after substantive edits; record the final results in this plan.
- Run `make clean`, remove task-owned temporary files, and retain source files, expected snapshots, pinned catalogs, generated schemas, the lockfile and development environment.
- Mark each remaining task complete only after its acceptance criteria pass. Keep any outstanding gaps explicit in the final report.

Acceptance: the repository contains intended source/reference artifacts, disposable build/test output is removed, and task statuses agree with verification evidence.

### Migration review and scope boundaries

Unknown TPS identity, fractional steering data incompatible with the VSS integer datatype, and unsupported multiplexed/variable-length/custom codecs remain explicit in `unmapped`. Resolving these mappings requires evidence or a separately specified codec; it is not a reason to guess values or silently activate capabilities. Expanding codec support is not required by the remaining tasks above.

Physical vehicle testing and consuming-runtime behavior remain outside this repository. The synthetic 2011 timing overlay is a composition demonstration, not an OEM compatibility claim. BLE interfaces and firmware behavior remain out of scope.

## Format 2 decisions

### Package

- A package is a directory, or a zip whose root is that directory.
- Exactly one manifest, `vehicle.yaml` or `vehicle.json`, sits at the root.
- A file is loaded only if the manifest lists it. The loader never scans directories.
- Zip, path, YAML, and size safety rules are the same as in the earlier package plan.

### Manifest

The manifest holds package metadata and the file list:

- `manifest: 1` and `format: 2`
- `id` (reverse DNS), `version` (semver), `name`
- `vss: "6.1"`, the pinned VSS release
- `applies_to`: package-wide applicability
- `dbc`: a map from an id to `{path, channel, sha256?}`
- `documents`: an ordered list; each entry may set `applies_to` and `override`
- `fixtures`, `depends`, `unmapped`

A multi-document manifest has no binding sections. If `documents` is omitted, the manifest file itself is the only document, so the v0.4 single-file shape still loads.

### Documents

A document may contain these top-level sections: `applies_to`, `channels`, `endpoints`, `sources`, `properties`, `sequences`, `queries`, `actions`, `requires`, `extensions`.

- **Property keys** are flat, canonical VSS paths. An optional `aliases` list keeps former keyword names.
- **Reads:** `read.signal` is one of three forms: a DBC reference, an inline frame, or a source/output pair. `read.query` is either an inline request or a source/output pair. `read.policy` has `preferred`, `max_age_ms`, and `active_fallback`.
- **Attributes:** `value` is for static attributes and cannot be combined with `read`.
- **Writes are allowed on VSS actuators only.** A write takes one of three shapes:
  - Shorthand: `endpoint`, `request`, and optional `expect`.
  - Steps: `endpoint`, `deadline_ms`, and `steps`.
  - Cases: `cases` maps each target value to one of the two shapes above.
  - An optional `constraints: {min, max, step}` may only narrow the VSS range.
- **Write result.** A write succeeds when every `expect` in its steps matches; that match is the vehicle's acknowledgement. A write with no `expect` reports `sent`. There are no `verify` or `completion` fields. The runtime keeps the requested target separate from the observed `read` value, and an acknowledgement never updates the observed state.
- **Steps** are `request` with an optional `expect`, `call: <sequence>`, and `wait_ms`. A `request` may be a hex string or `parts`, which mixes literal hex with encoded `input: value` fields (type, bytes, endian, scale, offset). Encoding must produce an exact integer; nothing is rounded.
- **Expect** is a hex prefix match by default. A `*` token is a wildcard byte, and `exact: true` turns off prefix matching. These are the format 1 matching rules written as strings: `expect: { prefix: "70 38 *" }`.
- **Sequences** hold only steps that are shared, such as `body-session`. `call` is resolved after the merge, so an overlay can replace a sequence. Calls stay on the same endpoint, cycles are rejected, and `deadline_ms` covers the steps inside calls.
- **Named queries** return data without changing vehicle state and declare their own datatype/unit or typed outputs. **Actions** change vehicle state outside a single VSS actuator write, with `description`, optional `retry` and `input_schema`, and the same shorthand/steps body a write uses. There is no `effect`, `output_schema`, or third procedure kind.
- **Endpoints:**
  - Raw CAN endpoints use `protocol: can`. Their payloads are the exact CAN data field.
  - ISO-TP endpoints use `protocol: isotp`. Their payloads are application data, and the transport owns protocol control information (PCI) and padding.
  - Each endpoint sets `channel`, `protocol`, `tx`, and `id_format`. Response endpoints require `rx` and `timeout_ms`; request-only endpoints omit both. The implementation uses `responder` for explicit multi-responder selection.
  - CAN IDs and payloads are uppercase hex strings, such as `"7E0"` and `"01 0D"`.

### Composition

Keyed sections merge by key: `endpoints`, `sources`, `properties`, `sequences`, `queries`, `actions`.

- A later document replaces the whole entry for a key.
- `KEY: null` deletes an entry defined earlier.
- A document's `applies_to` is intersected with the manifest's and must never widen it.
- Packages load in order, with each `depends` entry satisfied first. If two packages define the same key, that is a `MERGE_CONFLICT` unless the later document sets `override: true`.

Example write, cases shape:

```yaml
Vehicle.Cabin.Door.Row1.DriverSide.IsLocked:
  read:
    signal:
      {
        dbc: main,
        message: DOOR_STATUS,
        signal: DRIVER_DOOR_LOCKED,
        decode_as: boolean,
      }
  write:
    cases:
      "true":
        endpoint: body
        deadline_ms: 1000
        steps:
          - call: body-session
          - request: "30 38 00 01"
            expect: { prefix: "70 38 *" }
```

```mermaid
flowchart LR
  openPkg[Open dir or zip] --> safety[Path and size checks]
  safety --> manifest[Parse manifest]
  manifest --> docs[Parse documents in order]
  docs --> merge[Merge by key and null delete]
  merge --> refs[Resolve endpoints sources sequences DBC]
  refs --> vss[Check paths roles units against VSS catalog]
  vss --> applic[Filter by vehicle]
  applic --> capset[Resolved capability set]
```

### Error codes

Layer 4, Semantics, is new compared with the earlier package plan. It checks bindings against the pinned VSS catalog.

1. **Container:** `PKG_NO_MANIFEST`, `PKG_MULTIPLE_MANIFESTS`, `PKG_UNSAFE_PATH`, `PKG_UNLISTED_FILE`, `PKG_MISSING_FILE`, `PKG_HASH_MISMATCH`, `PKG_TOO_LARGE`
2. **Syntax:** `DOC_INVALID`, `DOC_UNKNOWN_FIELD` (strict mode), `DOC_LEGACY_FORMAT` (a format 1 file was found; the message points to `vprofile migrate`), `DOC_EXCLUSIVE_FORMS` (two exclusive forms were both used, such as `value` with `read`)
3. **References:**
   - Unknown targets: `REF_UNKNOWN_ENDPOINT`, `REF_UNKNOWN_SEQUENCE`, `REF_UNKNOWN_SOURCE`
   - Bad structure: `REF_SOURCE_KIND` (a source of the wrong kind), `REF_CYCLE`
   - DBC: `DBC_UNKNOWN_MESSAGE`, `DBC_UNKNOWN_SIGNAL`, `DBC_AMBIGUOUS_MESSAGE`
   - Dependencies: `DEP_UNSATISFIED`
4. **Semantics:**
   - Catalog: `VSS_UNSUPPORTED_RELEASE`, `VSS_UNKNOWN_PATH`, `VSS_ROLE_MISMATCH` (a write on a sensor, or a value on a sensor)
   - Domain: `VSS_CONSTRAINT_WIDENED`, `VSS_UNIT_MISMATCH`, `VSS_ENUM_VALUE`
   - Aliases: `ALIAS_COLLISION`
5. **Composition:** `MERGE_CONFLICT`, `APPLICABILITY_WIDENED`
6. **Extensions:** `EXT_NOT_REQUIRED` (an extension payload missing from `requires`), `EXT_UNSUPPORTED` (the package cannot be fully activated)
7. **Evidence:**
   - The fixture schema validates.
   - Each case names an existing path or action.
   - Each `kind` matches the binding it tests.

### Fixtures

- `kind` is one of `signal`, `query`, `write`, or `action`.
- Use `label` for the test description, `path` for a property, and `name` for a named query/action. Inputs are `frame` (a passive frame), `responses`, `target`, and `input`.
- `expect` may contain `value`, `quality`, `sent`, `result`, and `error`.
- The spec defines this format. Running the fixtures against vehicle behavior is the job of `can-opener-js`; the validator only checks that the fixtures are well-formed and point at real capabilities.

## Repo layout

### Documentation

- [README.md](README.md) is rewritten as an overview, a short quick-start package, and a link index.
- `docs/` holds one file per topic:
  - `package.md`, `manifest.md`, `document.md` (properties, read, write, steps, expect, sequences, actions, endpoints)
  - `decoding.md` (byte and bit decoders, enums, scaling, `parts` encoding), `composition.md`
  - `vss.md` (catalog pinning, roles, aliases, `unmapped`), `extensions.md`, `fixtures.md`, `validation.md`
  - `dbc.md`, moved from the README.
  - `authoring-guide.md`, `migration.md`
- `docs/vocabulary.yaml` maps each former keyword to a VSS path, plus a write target value or an action name. The generated vocabulary listing linked from `vss.md` and the `migrate` command both read it. Keywords with no one-to-one actuator, such as `ECU_WAKE`, `SIGNAL_OFF`, and multi-door `LOCK`/`UNLOCK` where needed, become actions.

### Schemas and catalog

- `schemas/manifest.schema.json`, `schemas/document.schema.json`, and `schemas/fixture.schema.json` are generated from the pydantic models and checked in. CI fails if they drift from the models.
- `catalog/vss-6.1.json` is generated with `vspec export json` from `/Users/henryhuang/Documents/code/repos/vehicle_signal_specification` (its `make json` target). A `make catalog` recipe and the source commit are recorded in `catalog/README.md`.

### Examples

- `examples/nissan-versa/` is built by migrating `can-opener-js/examples/slcan-web/nissan-versa-vehicle-profile-1-6`:
  - It is then split into `base`, `body`, `powertrain`, and `actions` documents, plus one year overlay.
  - Request-only endpoints remain raw CAN. Request/response commands use the explicitly declared ISO-TP single-frame conversion; the complete original bytes remain in the legacy input.
  - Fixtures cover lights, doors, lock, the horn, and the wildcard expect.
- `examples/universal-obd/` is a single-document package with the PIDs and VIN as `read.query`.
- `examples/hvac-synthetic/` is clearly marked synthetic. It shows a numeric write using `parts`, `constraints`, and a shared query source.
- `examples/legacy/nissan-versa-1-6/` is a format 1 input used only by the migration test.

### Tooling, skills, tests, and CI

- `tools/` holds the validator package, described below.
- `skills/` holds the agent skills, and `scripts/install-skills.sh` installs them without Python. Both are described under "Agent skills" below.
- `tests/` follows the vss-tools layout, described below.
- Repo scaffolding:
  - `Makefile` with a `mandatory_targets` target
  - `.github/workflows/buildcheck.yml`
  - `.pre-commit-config.yaml`
  - `noxfile.py`
  - `CHANGELOG.md`, with a 2.0.0 entry for the format break

## Tooling: `vehicle_profile_tools` (console script `vprofile`)

The tool targets Python 3.11 or later and uses pydantic v2, click with rich-click, pyyaml, and jsonschema. `uv` manages the lockfile, and pytest, ruff, and mypy are dev dependencies.

```text
tools/src/vehicle_profile_tools/
  cli.py, cli_options.py          # export, compose, resolve, diff, migrate; --strict, -l overlay, --vehicle, --log-file
  container.py                    # dir/zip open, safety, manifest discovery, hashes
  manifest.py                     # Manifest, DocumentRef, DbcRef, Applicability
  model.py                        # DocumentRaw (accepts partial entries) -> typed Property/Read/Write/Step/Sequence/NamedQuery/Action/Endpoint/Source
  merge.py                        # ordered merge, null delete, applicability intersection, cross-package override
  resolve.py                      # endpoint/source/sequence/DBC resolution, call cycles, endpoint consistency
  catalog.py                      # load catalog/vss-<ver>.json; path, role, datatype, unit, allowed, min/max checks
  codec.py                        # hex parsing, expect matching with *, parts encoding exactness, decoder validation
  dbc.py                          # minimal BO_/SG_/VAL_ parser
  strict.py                       # StrictOption + exceptions file
  migrate.py                      # format 1 folder -> format 2 package using docs/vocabulary.yaml
  errors.py                       # ErrorCode enum with a one-line fix hint per code; source for skills error-codes.md
  skills.py                       # list and install bundled skills; same targets and copy rules as install-skills.sh
  exporters/{json,tree,csv,jsonschema}.py
  compose.py, diff.py
```

### Typed model checks

- `DocumentRaw` is validated into the typed model after the merge. Errors are reported as `'properties.<path>' has N model error(s)`.
- Each write uses exactly one of three shapes: shorthand, steps, or cases.
- `cases` keys are canonical JSON-compatible strings for the property datatype, for example `"true"`/`"false"` for a boolean.
- `expect` is valid only on steps that wait for a response.

### Migration (`migrate.py`)

| Format 1                             | Format 2                                                                                               |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `signals.X.monitor`                  | `read.signal`                                                                                          |
| `queries.X`                          | `read.query` on the same path; one property gets both bindings when a keyword appears in both sections |
| `actions.X`                          | a `write` case or an `action`, according to `vocabulary.yaml`                                       |
| byte arrays                          | hex strings                                                                                            |
| `"*"`                                | the `*` token                                                                                          |
| `ref: sequences.x`                   | `call: x`                                                                                              |
| `request_id` / `response_id(s)`      | `tx` / `rx` on a `protocol: can` endpoint                                                              |
| inline `send: {request_id, request}` | a generated raw CAN endpoint                                                                           |

Anything that cannot be mapped goes to `unmapped`, and the command prints a report.

### CLI

- `vprofile export {json,tree,csv,jsonschema} --package <dir|zip> [--vehicle make=..,model=..,year=..] [-l overlay] [--strict] -o out`
- `vprofile compose --package <dir> -o <zip>` and `vprofile compose --verify <zip>`
- `vprofile resolve --packages ... --vehicle ...`
- `vprofile diff <old> <new>`
- `vprofile migrate <legacy-dir> -o <package-dir> [--framing raw|isotp|isotp-single-frame] [--responder ENDPOINT=HEX] [--steering-side left|right]`
- `vprofile vss search <text> [--role sensor|actuator|attribute]` and `vprofile vss show <path>` print path, role, datatype, unit, allowed values, and range from the pinned catalog
- `vprofile skills list` and `vprofile skills install [--agent cursor|claude|codex|all] [--project] [--dir PATH]`, described under "Installing skills"
## Agent skills

Skills live in `skills/` at the repo root. They are written for agents that edit vehicle packages, and they lean on `vprofile` for anything that must be exact. Each skill omits `disable-model-invocation`, so it triggers when an agent works on `vehicle.yaml`, DBC bindings, or format 1 profiles.

```text
skills/
  authoring-vehicle-profiles/
    SKILL.md            # workflow checklist + validate loop
    reference.md        # format 2 cheat sheet: manifest, read forms, write shapes, steps, expect, sequences, actions
    examples.md         # signal-only, signal+query, shared source, write cases, numeric write with parts, overlay, fixture
  validating-vehicle-profiles/
    SKILL.md            # run, read the log, fix, rerun
    error-codes.md      # generated from errors.py: code, layer, meaning, usual fix
  migrating-vehicle-profiles/
    SKILL.md            # migrate, review unmapped report, split documents, check lock-all vs per-door
    mapping.md          # format 1 -> format 2 table, mirrors the migrate.py table
```

### What each skill does

- **`authoring-vehicle-profiles`** applies when the user adds or edits a vehicle package, a property binding, or a DBC mapping. The agent:
  1. Sets the applicability.
  2. Finds the VSS path with `vprofile vss search`, then checks its role and unit with `vprofile vss show`.
  3. Picks a binding form: a signal, a query, or both, plus a policy.
  4. Writes the `write` inline. It uses `cases` for discrete targets and `parts` for numeric targets.
  5. Moves steps into a named sequence only when they are shared.
  6. Adds at least one positive and one negative fixture.
  7. Runs `vprofile export json --strict --package .` until it passes.
  8. Records anything unidentified under `unmapped` instead of guessing.
- **`validating-vehicle-profiles`** applies when `vprofile` fails, or when the user asks whether a package is valid. The agent runs the export with `--log-file`, looks up each code in `error-codes.md`, fixes the offending key, and reruns the export until it passes. It never weakens strict mode with an exceptions file unless the user asks.
- **`migrating-vehicle-profiles`** applies when the agent finds a `profile.yaml` with `version: 1`, or hits `DOC_LEGACY_FORMAT`. The agent:
  1. Runs `vprofile migrate`.
  2. Goes through the `unmapped` report.
  3. Confirms that each converted action affects exactly the paths it is now mapped to; a multi-door lock is an action, not a per-door write.
  4. Splits the result into documents.
  5. Validates the package.
- Every skill tells the agent to use `vprofile` when it is installed. Otherwise the agent uses `uvx --from "git+https://github.com/the-can-opener/vehicle-profile-spec#subdirectory=tools" vprofile ...`.

### Keeping skills in sync with the format

- `error-codes.md` is generated from `errors.py`, so a renamed code cannot go stale. `make skills` regenerates it, and CI fails on drift, as it does for schemas.
- YAML blocks in skill files that are fenced as `yaml vprofile-fragment` are wrapped into a synthetic package and validated under `--strict` by `tests/test_skills.py`. A format change that breaks an example breaks the build.
- `tests/test_skills.py` also enforces skill frontmatter:
  - `name` is lowercase with hyphens, at most 64 characters, and matches the directory name.
  - `description` is non-empty, at most 1024 characters, third person, and includes trigger terms.
  - The `SKILL.md` body is under 500 lines.
  - Links from `SKILL.md` go one level deep at most.

### Installing skills

Installing a skill means copying its folder from `skills/` into the agent's skills directory. `skills/README.md` documents both ways to do it.

**By hand**, from a clone:

```bash
cp -R skills/authoring-vehicle-profiles skills/validating-vehicle-profiles skills/migrating-vehicle-profiles ~/.cursor/skills/
```

**With `vprofile`**. The wheel bundles `skills/`: hatch `force-include` puts `../skills` into `vehicle_profile_tools/bundled_skills/`. Anyone who has the tool installed can run the install without a clone:

```bash
vprofile skills install                             # Cursor, user scope
vprofile skills install --agent claude
vprofile skills install --agent all --project
vprofile skills install --dir ./some/skills
vprofile skills list                                # bundled skill names

# no local install
uvx --from "git+https://github.com/the-can-opener/vehicle-profile-spec#subdirectory=tools" vprofile skills install
```

`vprofile skills install` takes the same flags as the script, uses the same target table, and copies the same way.

**With the script**, `scripts/install-skills.sh` (POSIX `sh`, no Python):

```bash
./scripts/install-skills.sh                         # Cursor, user scope: ~/.cursor/skills/
./scripts/install-skills.sh --agent claude
./scripts/install-skills.sh --agent all --project   # into ./.cursor/skills, ./.claude/skills, ./.agents/skills
./scripts/install-skills.sh --dir ./some/skills     # any directory
```

| Agent | User scope | Project scope (`--project`) |
| --- | --- | --- |
| `cursor` | `~/.cursor/skills/` | `.cursor/skills/` |
| `claude` | `~/.claude/skills/` | `.claude/skills/` |
| `codex` | `~/.agents/skills/` | `.agents/skills/` |

The script:

- Copies each folder under `skills/` into the target and replaces any existing folder with the same name.
- Creates the target directory if it is missing.
- Prints each path it wrote.
- Runs from any working directory, because it resolves `skills/` relative to its own location.
- Refuses `~/.cursor/skills-cursor/`, which belongs to Cursor.

With `--project`, it installs relative to the current directory. A repository of vehicle definitions can then commit the skills for everyone who works in it.

## Tests

This section records the intended acceptance matrix. Existing functional tests and snapshots cover most scenarios; the remaining migration/ZIP snapshots and fixture inventory are tracked above.

The suite follows the vss-tools `test_<feature>` layout.

### Positive cases

Target coverage: each applicable CLI scenario compares its resolved JSON output byte-for-byte with a checked-in expected file. Migration and ZIP still need the additional golden coverage listed above; multi-package scenarios use `resolve --strict`.

- `test_single_document`, `test_multi_document_merge`, `test_overlay_applicability` (`expected_2008.json`, `expected_2011.json`)
- `test_signal_and_query` (one path with both bindings)
- `test_shared_source`
- `test_write_shorthand`, `test_write_steps`, `test_write_cases`
- `test_write_parts_encoding`
- `test_sequence_call_override` (an overlay replaces a called sequence)
- `test_actions`, `test_zip_roundtrip`, `test_cross_package`, `test_aliases`
- `test_migrate` (the legacy Versa folder migrates, then validates under strict)

### Negative cases

Each asserts a nonzero exit code, the error code, and the offending key.

- `test_write_on_sensor` -> `VSS_ROLE_MISMATCH`
- `test_constraint_widened`
- `test_unknown_vss_path`
- `test_value_and_read` -> `DOC_EXCLUSIVE_FORMS`
- `test_source_kind_mismatch`
- `test_sequence_cycle`
- `test_dbc_ambiguous`
- `test_applicability_widened`
- `test_legacy_format_rejected` -> `DOC_LEGACY_FORMAT`
- `test_zip_unsafe`
- `test_extension_not_required`, `test_extension_unsupported`
- `test_encoding_inexact`: value 22.25 with step 0.5 is rejected

### Unit tests and CI

- Unit tests: `test_dbc_parser.py`, `test_codec.py` (hex, `*`, `parts`), `test_merge.py`, `test_catalog.py`
- `test_skills.py`: frontmatter limits, validation of `vprofile-fragment` blocks, and `error-codes.md` drift.
- `test_install_skills.py` runs both `scripts/install-skills.sh` and `vprofile skills install` with `HOME` set to a temporary directory. For each `--agent` and `--project` combination, and for `--dir`, both installs must produce a tree identical to `skills/`. Another check confirms the built wheel contains `vehicle_profile_tools/bundled_skills/`.
- `make mandatory_targets` runs these checks, and CI runs that target:
  - export every `examples/*` package under `--strict`;
  - check the generated schemas and `error-codes.md` against the checked-in files;
  - validate the skill fragments.

## Assumptions and out of scope

- Runtime changes in `can-opener-js` are out of scope; that repo must adopt format 2 separately.
- Raw CAN bindings use exact frame data; ISO-TP bindings use application payloads. Runtime adapters are separate implementations.
- Diagnostics and configuration stay reserved extension examples only. The tool parses them, then reports them as `EXT_UNSUPPORTED`.
- OBDb compatibility is not a goal.
