---
name: authoring-vehicle-profiles
description: Authors format 2 vehicle.yaml packages, VSS property bindings, DBC references, queries, actions and fixtures, using the pinned catalog and strict validator.
---

# Author a vehicle package

Use `vprofile` when installed. Otherwise run `uvx --from "git+https://github.com/the-can-opener/vehicle-profile-spec#subdirectory=tools" vprofile` with the same arguments.

Set applicability before choosing mappings. Use `vprofile vss search TEXT` and `vprofile vss show PATH` to check canonical identity, role, datatype, unit and domain. Similar labels are not sufficient evidence. Keep unidentified mappings in `unmapped`.

Read [reference.md](reference.md) for grammar and [examples.md](examples.md) for tested fragments. Keep passive and query acquisition on one property. A write controls exactly one actuator. Bind an all-door lock or unlock to Vehicle.Cabin.Door.Central.IsLocked; do not copy that command onto one door. Use quoted string case keys and exact numeric parts encoding. Move steps into sequences only when shared. Never infer ECU addresses from VSS ControlUnit names.

Add positive and negative fixtures. Use `label` for the test description and `name` only for named queries/actions. Run `vprofile export json --strict --package .` after edits and fix errors before reporting structural validity. This command performs no vehicle I/O. Physical applicability and response framing still need evidence; do not describe validation as a vehicle test.
