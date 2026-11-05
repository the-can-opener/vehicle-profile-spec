# Authoring a package

[Overview](../README.md) · [Documentation index](README.md)

1. Set [manifest fields](manifest.md): `manifest: 1`, `format: 2`, a reverse-DNS ID, semver, `vss: "6.1"`, and honest applicability.
2. Run `vprofile vss search temperature` and `vprofile vss show Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature`. Match [quantity, role, unit and datatype](vss.md).
3. List every [document](document.md), [DBC](dbc.md) and [fixture](fixtures.md). Use one passive binding, active binding or both on a canonical property. Keep unknown mappings in `unmapped`.
4. Select [raw CAN versus ISO-TP](document.md#endpoints-ecu-targets-and-steps) explicitly. For multiple responders, set `responder` to one of the endpoint's listed response IDs.
5. Write one actuator with an inline body or quoted `cases` keys. Bind a command that locks or unlocks every cabin door to `Vehicle.Cabin.Door.Central.IsLocked`. Use uppercase named actions for commands that affect several actuators and have no single catalog path. Reuse only genuinely shared steps as sequences.
6. Add positive and negative [fixtures](fixtures.md), then [validate](validation.md) with `vprofile export json --strict --package . --log-file validation.log`.
7. Exercise fixtures in a compatible runtime on the declared vehicle before claiming behavior. Validation does not provide physical evidence.

Examples: [OBD](../examples/universal-obd/vehicle.yaml), [synthetic HVAC](../examples/hvac-synthetic/vehicle.yaml), [Versa](../examples/nissan-versa/README.md).

## Related pages

[Package layout](package.md) · [Property bindings](document.md) · [Validation](validation.md)
