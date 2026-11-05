# VSS paths and semantics

[Overview](../README.md) · [Documentation index](README.md)

## Property semantics and catalog resolution

The pinned VSS release supplies datatype, unit, meaning, range, and allowed values. A binding MUST NOT redefine a standard property's semantics. The pinned catalog differs from upstream VSS 6.1 in the ways recorded on the node and in [catalog provenance](../catalog/README.md):

- `Vehicle.Chassis.SteeringWheel.Angle` is `float` here and `int16` upstream, so a fractional degree signal can be published without rounding.
- `Vehicle.Cabin.IsCentralLockEngaged` is a boolean actuator added beside `IsWindowChildLockEngaged`. True locks every cabin door and false unlocks every cabin door. Upstream has `IsLocked` only on each door. A package that has one command for every door MUST bind that command here, and MUST NOT copy it onto one door's `IsLocked` path.
- `Vehicle.Cabin.IsSeatBeltWarningActive` is a boolean sensor added beside `IsWindowChildLockEngaged`. True means the vehicle seatbelt warning indicator is active. Upstream has `IsBelted` only on each seat. A package that has one seatbelt warning indicator MUST bind it here, and MUST NOT copy it onto one seat's `IsBelted` path.
- `Vehicle.OBD` is the COVESA OBD overlay. Upstream removed that branch from the standard catalog. A keyword that exists only as an OBD PID maps there.

Namespaced catalog additions require an explicit overlay validated with VSS tooling. Always check for a matching standard concept before adding an extension.

A binding must match the underlying quantity, not merely have a similar label. A warning indicator is not interchangeable with buckle state. `SEATBELT_WARNING` maps to `Vehicle.Cabin.IsSeatBeltWarningActive`.

Aliases MAY be supplied as an array on a property for legacy SDK names, such as `SPEED` for `Vehicle.Speed`. They resolve to the same canonical cache entry and MUST NOT collide with another alias, property key, query name, or action name.

VSS does not define a vehicle's ECUs. `Vehicle.ControlUnit` is a branch whose instance names (`Central`, `FrontLeft`, `FrontRight`, `RearLeft1`, `RearLeft2`, `Trunk`) are examples that the catalog expects deployments to replace. Each instance carries only an `ID` attribute and `Health` signals: network status, power, temperature, CPU and memory use, and software supervision. A package MUST NOT treat those instance names as ECU addresses. To bind health properties of a real controller, supply a VSS overlay that sets the instance list, validate it with VSS tooling, and bind the resulting paths like any other property. The ECU that answers a request is identified by its [endpoint](document.md#endpoints-ecu-targets-and-steps).

## Legacy keyword mapping

See the [generated vocabulary](vocabulary.md). Both this listing and migration use [vocabulary.yaml](vocabulary.yaml); unknown mappings remain inactive.

## Related pages

[Pinned catalog](../catalog/README.md) · [Legacy vocabulary](vocabulary.md) · [Property bindings](document.md)
