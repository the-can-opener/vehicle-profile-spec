# Authoring a package

1. Set `manifest: 1`, `format: 2`, a reverse-DNS ID, semver, `vss: "6.1"`, and honest applicability.
2. Run `vprofile vss search temperature` and `vprofile vss show Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature`. Match quantity, role, unit and datatype.
3. List every document, DBC and fixture. Use one passive binding, active binding or both on a canonical property. Keep unknown mappings in `unmapped`.
4. Select raw CAN versus ISO-TP explicitly. For multiple responders use the tooling's `responder` selection field on the endpoint; this narrows the draft's otherwise unspecified selection mechanism.
5. Write one actuator with an inline body or quoted `cases` keys. Use uppercase named actions for multi-actuator commands. Reuse only genuinely shared steps as sequences.
6. Add positive and negative fixtures, then run `vprofile export json --strict --package . --log-file validation.log`.
7. Exercise fixtures in a compatible runtime on the declared vehicle before claiming behavior. Validation does not provide physical evidence.

Examples: [OBD](../examples/universal-obd/vehicle.yaml), [synthetic HVAC](../examples/hvac-synthetic/vehicle.yaml), [Versa](../examples/nissan-versa/README.md).
