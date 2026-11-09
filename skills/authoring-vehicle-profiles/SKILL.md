---
name: authoring-vehicle-profiles
description: Authors format 2 vehicle.yaml packages, VSS property bindings, DBC references, queries, actions and fixtures, using the pinned catalog and strict validator.
---

# Author a vehicle package

Use `vprofile` when installed. Otherwise run `uvx --from "git+https://github.com/the-can-opener/vehicle-profile-spec#subdirectory=tools" vprofile` with the same arguments.

Set applicability before choosing mappings. Use `vprofile vss search TEXT` and `vprofile vss show PATH` to check canonical identity, role, datatype, unit and domain. Similar labels are not sufficient evidence. Keep unidentified mappings in `unmapped`.

Read [reference.md](reference.md) for grammar and [examples.md](examples.md) for tested fragments. Keep passive and query acquisition on one property. A write controls exactly one actuator. Bind an all-door lock or unlock to Vehicle.Cabin.IsCentralLockEngaged; do not copy that command onto one door. Bind a vehicle seatbelt warning indicator to Vehicle.Cabin.IsSeatBeltWarningActive; do not copy that indicator onto one seat's IsBelted sensor. Bind accelerator, brake, and clutch pedal travel to Vehicle.Chassis.Accelerator.PedalPosition, Vehicle.Chassis.Brake.PedalPosition, and Vehicle.Chassis.Clutch.PedalPosition, with aliases ACCELERATOR_PEDAL, BRAKE_PEDAL, and CLUTCH_PEDAL. Do not copy pedal travel onto TPS or Vehicle.Powertrain.Transmission.ClutchEngagement. Leave the hold time unknown when it is not known: the vehicle may keep the state or drop it after a few milliseconds. Declare `duration` as information: a positive number of milliseconds, or `latched` when the effect has been observed to stay. The runtime does not time or reverse the write from it. Declare `release.action` when a named action ends it early. Declare `repeat` when one masked CAN frame must be retransmitted to keep the state. Use quoted string case keys and exact numeric parts encoding. Move steps into sequences only when shared. Never infer ECU addresses from VSS ControlUnit names.

Add positive and negative fixtures. Use `label` for the test description and `name` only for named queries/actions. Run `vprofile export json --strict --package .` after edits and fix errors before reporting structural validity. This command performs no vehicle I/O. Physical applicability and response framing still need evidence; do not describe validation as a vehicle test.
