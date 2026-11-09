# Pinned VSS catalog

`vss-6.1.json` is the full expanded COVESA Vehicle Signal Specification v6.1 export, generated from tag `v6.1`, commit `2817646d1808fc7c470c0432fc7f4ed685e5c9e3` in `https://github.com/COVESA/vehicle_signal_specification`.

Run `make catalog VSS_SOURCE=/path/to/vehicle_signal_specification`. The script verifies the tag commit, exports that tree into temporary storage, and runs `vss-tools==1.9.9` / `vspec export json --strict` with the release units file. It never depends on the source checkout's working tree or branch. After export it applies the local departures below. The catalog is bundled into the Python wheel so lookups work outside this repository. Source license and notice are included alongside the data.

`Vehicle.Chassis.SteeringWheel.Angle` is `float` in this catalog. Upstream VSS 6.1 declares it as `int16`. The local type keeps fractional degree signals, such as a 0.1 deg CAN factor, exact. The same note is on the signal in the sibling `vehicle_signal_specification` tree (`spec/Chassis/Chassis.vspec`).

`Vehicle.Cabin.IsCentralLockEngaged` is a boolean actuator added beside `IsWindowChildLockEngaged`. True locks every cabin door and false unlocks every cabin door. Upstream VSS 6.1 has `IsLocked` only on each door. This actuator does not report or command a single door.

`Vehicle.Cabin.IsSeatBeltWarningActive` is a boolean sensor added beside `IsWindowChildLockEngaged`. True means the vehicle seatbelt warning indicator is active. Upstream VSS 6.1 has `IsBelted` only on each seat. This sensor does not report or stand in for one seat's buckle.

`Vehicle.Chassis.Clutch.PedalPosition` is a `uint8` sensor added between `Brake` and `ParkingBrake`. `0` is not depressed and `100` is fully depressed, matching `Accelerator.PedalPosition` and `Brake.PedalPosition`. Upstream VSS 6.1 has no clutch pedal position. This sensor does not report or stand in for `Vehicle.Powertrain.Transmission.ClutchEngagement`, where `0` is fully disengaged and `100` is fully engaged.

`Vehicle.OBD` is the COVESA OBD overlay from the same tag (`overlays/extensions/OBD.vspec`). Upstream VSS 6.1 removed that branch from the standard catalog. `scripts/catalog.sh` reapplies the steering-wheel type, the central-lock actuator, the seatbelt-warning sensor, the clutch pedal position, and this overlay after every export.
