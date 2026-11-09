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


def vocabulary_cell(value):
    return value.replace("|", "\\|").replace("\n", " ")


def vocabulary_rows(entries):
    rows = [
        "| Keyword | Mapping | Unit | Write target | Notes |",
        "|---|---|---|---|---|",
    ]
    for name, mapping in entries:
        if "path" in mapping:
            mapped = f"`{mapping['path']}`"
            note = mapping.get("note", "")
        elif "query" in mapping:
            mapped = f"query `{mapping['query']}`"
            note = ""
        elif "action" in mapping:
            mapped = f"action `{mapping['action']}`"
            note = ""
        else:
            mapped = "unmapped"
            note = mapping["reason"]
        target = json.dumps(mapping["target"]) if "target" in mapping else ""
        cells = [
            f"`{name}`",
            mapped,
            mapping.get("unit", ""),
            f"`{target}`" if target else "",
            note,
        ]
        rows.append("| " + " | ".join(vocabulary_cell(cell) for cell in cells) + " |")
    return rows


vocabulary = json.loads((root / "docs/vocabulary.yaml").read_text())
standard = [(name, mapping) for name, mapping in vocabulary.items() if not mapping.get("legacy")]
legacy = [(name, mapping) for name, mapping in vocabulary.items() if mapping.get("legacy")]
lines = [
    "# Keyword vocabulary",
    "",
    "[Overview](../README.md) · [Documentation index](README.md)",
    "",
    "Generated from [vocabulary.yaml](vocabulary.yaml); do not edit this listing by hand.",
    "",
    *vocabulary_rows(standard),
    "",
    "## Legacy keywords",
    "",
    "Format 1 predicate, past-tense, and verb-specific keyword variants retained for migration compatibility.",
    "",
    *vocabulary_rows(legacy),
]
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
