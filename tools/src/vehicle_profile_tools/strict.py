"""JSON-compatible YAML/JSON parsing, including duplicate key rejection."""

import json
import math
import re
from dataclasses import dataclass, field

import yaml

from .errors import fail


class Loader(yaml.SafeLoader):
    integer_keys = False


Loader.yaml_implicit_resolvers = {
    key: [
        (tag, rx)
        for tag, rx in entries
        if tag not in ("tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp")
    ]
    for key, entries in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
Loader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(true|false)$"), list("tf"))


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if isinstance(key, int) and not isinstance(key, bool) and loader.integer_keys:
            key = str(key)
        if not isinstance(key, str) or key in result:
            fail("DOC_INVALID", str(key), "object keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


class LegacyLoader(Loader):
    """Format 1 keys `can.buses` by integer; those keys become strings."""

    integer_keys = True


def parse(text: str, location: str = "", loader=Loader):
    try:
        if location.endswith(".json"):

            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result:
                        raise ValueError(f"duplicate key {key}")
                    result[key] = value
                return result

            def invalid_constant(value):
                raise ValueError(f"nonfinite JSON number {value}")

            value = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
            json.dumps(
                value, allow_nan=False
            )  # Also reject finite syntax that overflows, e.g. 1e999.
            return value
        for token in yaml.scan(text):
            if isinstance(
                token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken, yaml.tokens.TagToken)
            ):
                fail("DOC_INVALID", location, "YAML tags, anchors and aliases are forbidden")
        value = yaml.load(text, Loader=loader)
        json.dumps(value, allow_nan=False)

        def check(v):
            if isinstance(v, float) and not math.isfinite(v):
                raise ValueError("nonfinite number")
            if isinstance(v, dict):
                for x in v.values():
                    check(x)
            elif isinstance(v, list):
                for x in v:
                    check(x)

        check(value)
        return value
    except (yaml.YAMLError, TypeError, ValueError) as exc:
        fail("DOC_INVALID", location, str(exc))


@dataclass
class StrictOption:
    enabled: bool = False
    exceptions: dict[str, str] = field(default_factory=dict)
    ignored: set[str] = field(default_factory=set)

    @classmethod
    def from_file(cls, enabled, path=None):
        from pathlib import Path

        if path and not enabled:
            fail("DOC_INVALID", str(path), "--strict-exceptions requires --strict")
        entries = parse(Path(path).read_text(), str(path)) if path else []
        if not isinstance(entries, list):
            fail("DOC_INVALID", str(path), "exceptions must be a list of {path, reason} objects")
        exceptions = {}
        for item in entries:
            if (
                not isinstance(item, dict)
                or set(item) != {"path", "reason"}
                or not isinstance(item["path"], str)
                or not item["path"].startswith("/")
                or not isinstance(item["reason"], str)
                or not item["reason"].strip()
                or item["path"] in exceptions
            ):
                fail("DOC_INVALID", str(path), "use unique JSON Pointer paths and nonempty reasons")
            exceptions[item["path"]] = item["reason"]
        return cls(enabled, exceptions)

    def clean(self, model, data):
        """Remove only explicitly excepted *unknown* fields, never known core fields.

        Union alternatives contribute all their known keys. Thus an exception
        cannot turn two exclusive binding forms into one by deleting a valid field.
        """
        schema = model.model_json_schema()
        definitions = schema.get("$defs", {})

        def alternatives(node):
            if "$ref" in node:
                return alternatives(definitions[node["$ref"].rsplit("/", 1)[-1]])
            branches = node.get("anyOf", node.get("oneOf"))
            if branches:
                return [child for branch in branches for child in alternatives(branch)]
            return [node]

        def walk(value, nodes, path=""):
            nodes = [branch for node in nodes for branch in alternatives(node)]
            if isinstance(value, dict):
                objects = [node for node in nodes if node.get("type") == "object"]
                if not objects or any(node == {} for node in nodes):
                    return value  # Raw or extension-owned objects are validated elsewhere.
                result = {}
                for key, child in value.items():
                    pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
                    shapes = [
                        node["properties"][key]
                        for node in objects
                        if key in node.get("properties", {})
                    ]
                    additional = [node.get("additionalProperties", True) for node in objects]
                    if not shapes and all(item is False for item in additional):
                        if pointer in self.exceptions:
                            self.ignored.add(pointer)
                            continue
                    if not shapes:
                        shapes = [item for item in additional if isinstance(item, dict)]
                    result[key] = walk(child, shapes, pointer) if shapes else child
                return result
            if isinstance(value, list):
                items = [node["items"] for node in nodes if "items" in node]
                return (
                    [
                        walk(child, items, path + "/" + str(index))
                        for index, child in enumerate(value)
                    ]
                    if items
                    else value
                )
            return value

        return walk(data, [schema])
