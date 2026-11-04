"""Reproduce the Versa example from the retained legacy input and declared framing.

The year overlay is deliberately a synthetic timing example, not an OEM claim.
Run with --check to compare generated files without changing the checkout.
"""

import argparse
import tempfile
from copy import deepcopy
from pathlib import Path

import yaml
from vehicle_profile_tools.migrate import migrate
from vehicle_profile_tools.resolve import resolve

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix="vprofile-versa-") as work:
    package = Path(work) / "package"
    migrate(
        root / "examples/legacy/nissan-versa-1-6",
        package,
        framing="isotp-single-frame",
        steering_side="left",
    )
    manifest = yaml.safe_load((package / "vehicle.yaml").read_text())
    bindings = yaml.safe_load((package / "bindings.yaml").read_text())
    manifest["id"] = "org.canopener.nissan.versa"
    manifest["name"] = "Nissan Versa format 1 migration — not physically verified"
    documents = {
        "base.yaml": {key: bindings[key] for key in ("channels", "endpoints")},
        "body.yaml": {"sequences": bindings["sequences"], "properties": {}},
        "powertrain.yaml": {"properties": {}},
        "actions.yaml": {"actions": bindings["actions"]},
    }
    for path, value in bindings["properties"].items():
        filename = (
            "body.yaml"
            if path.startswith(("Vehicle.Body.", "Vehicle.Cabin."))
            else "powertrain.yaml"
        )
        documents[filename]["properties"][path] = value
    overlay = deepcopy(bindings["sequences"]["body_session_prep"])
    overlay["steps"].insert(1, {"wait_ms": 10})
    documents["overlays/2011.yaml"] = {"sequences": {"body_session_prep": overlay}}
    manifest["documents"] = [{"path": name} for name in documents]
    manifest["documents"][-1]["applies_to"] = {"years": [2011]}
    manifest["fixtures"] = ["fixtures/body.yaml"]
    fixtures = {
        "fixture": 1,
        "cases": [
            {
                "label": "Low beam on",
                "kind": "signal",
                "path": "Vehicle.Body.Lights.Beam.Low.IsOn",
                "frame": {"id": "60D", "data": "04 00 00 00 00 00 00 00"},
                "expect": {"value": True},
            },
            {
                "label": "Short signal frame",
                "kind": "signal",
                "path": "Vehicle.Body.Lights.Beam.High.IsOn",
                "frame": {"id": "60D", "data": "00"},
                "expect": {"quality": "invalid", "error": "DECODE_ERROR"},
            },
            {
                "label": "Driver door",
                "kind": "signal",
                "path": "Vehicle.Cabin.Door.Row1.DriverSide.IsOpen",
                "frame": {"id": "60D", "data": "08 00 00 00 00 00 00 00"},
                "expect": {"value": True},
            },
            {
                "label": "Horn acknowledged",
                "kind": "write",
                "path": "Vehicle.Body.Horn.IsActive",
                "target": True,
                "responses": ["50 81", "50 C0", "70 30 01"],
                "expect": {"sent": ["10 81", "10 C0", "30 30 00 01"], "result": "acknowledged"},
            },
            {
                "label": "Unsupported horn off",
                "kind": "write",
                "path": "Vehicle.Body.Horn.IsActive",
                "target": False,
                "expect": {"error": "UNSUPPORTED", "sent": []},
            },
            {
                "label": "Lock wildcard acknowledged",
                "kind": "action",
                "name": "LOCK",
                "responses": ["50 81", "50 C0", "70 38 01"],
                "expect": {"sent": ["10 81", "10 C0", "30 38 00 01"], "result": "acknowledged"},
            },
            {
                "label": "Unknown lock outcome",
                "kind": "action",
                "name": "LOCK",
                "responses": ["50 81", "50 C0"],
                "expect": {"result": "unknown", "error": "OUTCOME_UNKNOWN"},
            },
            {
                "label": "Failed acknowledgement",
                "kind": "action",
                "name": "LOCK",
                "responses": ["7F 10"],
                "expect": {"error": "NEGATIVE_RESPONSE"},
            },
        ],
    }
    documents["vehicle.yaml"] = manifest
    documents["fixtures/body.yaml"] = fixtures
    (package / "bindings.yaml").unlink()
    for name, document in documents.items():
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(document, sort_keys=False))
    (package / "README.md").write_text("""# Nissan Versa migration example

Reproduce with `python scripts/migrate-versa.py` from the repository root.
The script declares `--framing isotp-single-frame --steering-side left` for the retained legacy input. It removes validated single-frame PCI and padding from request/response commands and retains the original application response patterns, including wildcards. The request-only ECU_WAKE and WIPERS commands remain byte-exact raw CAN. The original DBC and complete format 1 input remain under `../legacy/nissan-versa-1-6`.

These declarations describe the source framing and left-hand-drive mapping; they are not physical test evidence. DBC comments identify Sentra-derived observations. Do not infer model-year compatibility from the package metadata. TPS has no established canonical mapping and the fractional steering decoder does not preserve the VSS integer datatype; both remain in unmapped with the original data.

The 2011 overlay is **synthetic**: it inserts a 10 ms wait in the shared setup sequence to demonstrate late call resolution and narrower applicability. It claims no real 2011 ECU difference. Compare exports with `--vehicle make=Nissan,model=Versa,year=2008` and `year=2011`.

LOCK/UNLOCK control all doors and remain actions. HORN supports only the true case. Fixture expectations preserve the legacy application bytes; no raw receive PCI values are invented. Runtime execution and vehicle testing are outside this repository.
""")
    resolve([package], {"year": 2008})
    resolve([package], {"year": 2011})
    destination = root / "examples/nissan-versa"
    for file in sorted(package.rglob("*")):
        if not file.is_file():
            continue
        target = destination / file.relative_to(package)
        if args.check:
            if not target.exists() or target.read_bytes() != file.read_bytes():
                raise SystemExit(f"Example drift: {target.relative_to(root)}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(file.read_bytes())
print("Versa example verified" if args.check else "Versa example generated")
