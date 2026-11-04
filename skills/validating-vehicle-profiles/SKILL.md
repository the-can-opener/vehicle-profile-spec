---
name: validating-vehicle-profiles
description: Validates vehicle.yaml packages and diagnoses vprofile errors in VSS bindings, composition, DBC mappings and format 2 fixtures.
---

# Validate a package

Use `vprofile` when installed, otherwise `uvx --from "git+https://github.com/the-can-opener/vehicle-profile-spec#subdirectory=tools" vprofile`.

Run `vprofile export json --strict --package PATH --log-file validation.log`. Read the exact code and location, consult [error-codes.md](error-codes.md), fix the affected entry and rerun. Check catalog semantics with `vprofile vss show PATH`. Do not silence errors by removing strictness or weakening applicability. Use `--strict-exceptions FILE` only if the user explicitly asks to permit an unknown annotation; exceptions cannot suppress known fields or semantic failures.

For composed packages, pass the actual ordered inputs to `vprofile resolve --packages BASE --packages OVERLAY --strict --vehicle make=...,model=...,year=...`. Missing selectors give an inspection view of all documents, not authorization to write to an unidentified vehicle. Verify archives with `vprofile compose --verify PACKAGE.zip`.

Report separately what structural checks passed and what remains untested. Fixtures are checked for shape and existing bindings, not executed against a vehicle. Unsupported extensions and uncertain migration mappings must remain explicit. Never transmit commands as part of this validation workflow.
