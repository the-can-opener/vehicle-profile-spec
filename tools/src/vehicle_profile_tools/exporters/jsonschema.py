import json
from typing import Any

from ..catalog import load_catalog
from ..model import Document
from ..schema_rules import augment


def schemas():
    from ..manifest import Manifest
    from ..model import Fixture

    # A manifest without documents can also contain document sections.
    manifest = Manifest.model_json_schema()
    document = Document.model_json_schema()
    document.setdefault("$defs", {}).update(manifest["$defs"])
    document["properties"]["applies_to"] = manifest["properties"]["applies_to"]
    # Null deletes an earlier keyed entry during composition; it is not a typed binding.
    for section in (
        "channels",
        "endpoints",
        "sources",
        "properties",
        "sequences",
        "queries",
        "actions",
    ):
        entries = document["properties"][section]
        entries["additionalProperties"] = {
            "anyOf": [entries["additionalProperties"], {"type": "null"}]
        }
    manifest.setdefault("$defs", {}).update(document.get("$defs", {}))
    for key, value in document["properties"].items():
        if key != "applies_to":
            manifest["properties"][key] = value
    manifest["allOf"] = [
        {
            "if": {"required": ["documents"]},
            "then": {
                "not": {
                    "anyOf": [
                        {"required": [k]} for k in document["properties"] if k != "applies_to"
                    ]
                }
            },
        }
    ]
    for schema in (manifest, document):
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    fixture = Fixture.model_json_schema()
    fixture["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    augmented = set()
    for root in (manifest, document, fixture):
        for name, definition in root.get("$defs", {}).items():
            if id(definition) not in augmented:
                augment(name, definition)
                augmented.add(id(definition))
    return {"manifest": manifest, "document": document, "fixture": fixture}


def export(document):
    catalog = load_catalog()
    props = {}
    for path in document.get("properties", {}):
        entry = catalog[path]
        dtype = entry["datatype"].removesuffix("[]")
        typ = (
            "boolean"
            if dtype == "boolean"
            else "string"
            if dtype == "string"
            else "integer"
            if dtype.startswith(("int", "uint"))
            else "number"
        )
        schema: dict[str, Any] = {"type": typ}
        for src, dst in [("min", "minimum"), ("max", "maximum"), ("allowed", "enum")]:
            if src in entry:
                schema[dst] = entry[src]
        if entry["datatype"].endswith("[]"):
            schema = {"type": "array", "items": schema}
        props[path] = schema
    return (
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": props,
                "additionalProperties": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
