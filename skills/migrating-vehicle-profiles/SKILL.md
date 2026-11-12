---
name: migrating-vehicle-profiles
description: Migrates legacy version 1 and 1.1 profile.yaml folders to format 2 vehicle.yaml packages and reviews DOC_LEGACY_FORMAT, framing and unmapped capability reports.
---

# Migrate format 1

Use `vprofile` when installed, otherwise `uvx --from "git+https://github.com/the-can-opener/vehicle-profile-spec#subdirectory=tools" vprofile`.

Run `vprofile migrate OLD -o NEW` into an empty destination. When the source framing is established, supply `--framing raw|isotp|isotp-single-frame`; add `--responder ENDPOINT=HEX` or `--steering-side left|right` when supported by the source information. Preserve the original input. Read every unmapped record: it includes the original object and the reason it was not activated. Consult [mapping.md](mapping.md) before completing a mapping manually.

Check exact VSS identity, unit, enum and command effect. Map an all-door lock or unlock to Vehicle.Cabin.IsCentralLockEngaged. Do not bind that command to one door's IsLocked path. Map SEATBELT_WARNING to Vehicle.Cabin.IsSeatBeltWarningActive. Do not bind that indicator to a seat's IsBelted sensor. Map ACCELERATOR_PEDAL, BRAKE_PEDAL, and CLUTCH_PEDAL to Vehicle.Chassis.Accelerator.PedalPosition, Vehicle.Chassis.Brake.PedalPosition, and Vehicle.Chassis.Clutch.PedalPosition. Do not bind pedal travel to TPS or Vehicle.Powertrain.Transmission.ClutchEngagement. In a version 1.1 profile, a command with no established VSS target stays unmapped; never guess one, for example for WIPERS.low or CLIMATE.on. Never fabricate a missing horn-off case. Legacy padded request frames and application response prefixes cannot be copied together onto a raw-CAN endpoint without framing review.

Split the result into listed documents if helpful, retaining deterministic order and narrow overlay applicability. Add positive/negative fixtures and run `vprofile export json --strict --package NEW`. Report unmapped work and the lack of physical verification explicitly.
