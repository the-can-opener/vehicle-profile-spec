"""Generate or check schema/error documentation from source models."""

import argparse
import json
from pathlib import Path

from vehicle_profile_tools.errors import error_reference
from vehicle_profile_tools.exporters.jsonschema import schemas

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
files = {
    root / "schemas" / f"{name}.schema.json": json.dumps(schema, indent=2, sort_keys=True) + "\n"
    for name, schema in schemas().items()
}
files[root / "skills/validating-vehicle-profiles/error-codes.md"] = error_reference()
vocabulary = json.loads((root / "docs/vocabulary.yaml").read_text())
lines = [
    "# Keyword vocabulary",
    "",
    "[Overview](../README.md) · [Documentation index](README.md)",
    "",
    "Generated from [vocabulary.yaml](vocabulary.yaml); do not edit this listing by hand.",
    "",
]
for name, mapping in vocabulary.items():
    if "path" in mapping:
        description = mapping["path"]
        if "target" in mapping:
            description += " (write target " + json.dumps(mapping["target"]) + ")"
        if "unit" in mapping:
            description += "; unit " + mapping["unit"]
        if "note" in mapping:
            description += "; " + mapping["note"]
    elif "query" in mapping:
        description = "query " + mapping["query"]
    elif "action" in mapping:
        description = "action " + mapping["action"]
    else:
        description = "unmapped: " + mapping["reason"]
    lines.append(f"- `{name}`: {description}")
lines.extend(
    [
        "",
        "## Related pages",
        "",
        "[VSS paths and semantics](vss.md) · [Migration](migration.md) · [Historical format 1 reference](format-1.md)",
    ]
)
files[root / "docs/vocabulary.md"] = "\n".join(lines) + "\n"
for path, text in files.items():
    if args.check:
        if not path.exists() or path.read_text() != text:
            raise SystemExit(f"Generated file drift: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
