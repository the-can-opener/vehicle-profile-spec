"""Ordered package pipeline: merge, typed validation, references, semantics, fixtures."""

import json
import re
from copy import deepcopy
from typing import Any

import jsonschema
from semantic_version import NpmSpec, Version

from .catalog import check_value, load_catalog, resource, validate_properties
from .container import Package, validate_model
from .dbc import Dbc
from .errors import fail
from .merge import applicable, intersect, merge_document
from .model import Document, Fixture


def validate_references(doc, dbcs, catalog):
    endpoints, sources = doc.get("endpoints", {}), doc.get("sources", {})
    sequences = doc.get("sequences", {})
    for name, ep_value in endpoints.items():
        if ep_value["channel"] not in doc.get("channels", {}):
            fail("DOC_INVALID", f"endpoints.{name}.channel", "unknown channel")
    for name in doc.get("queries", {}):
        if name in doc.get("actions", {}):
            fail("DOC_EXCLUSIVE_FORMS", name, "name is both query and action")
    vocabulary = json.loads(resource("vocabulary.yaml").read_text())
    for section in ("queries", "actions"):
        for name, value in doc.get(section, {}).items():
            mapping = vocabulary.get(name, {})
            if "path" in mapping and (section == "queries" or "target" in mapping):
                fail(
                    "VSS_ROLE_MISMATCH",
                    f"{section}.{name}",
                    "use the canonical VSS property and alias",
                )
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                fail("DOC_INVALID", f"{section}.{name}", "expected uppercase keyword")
            if "input_schema" in value:
                try:
                    jsonschema.Draft202012Validator.check_schema(value["input_schema"])
                except jsonschema.SchemaError as exc:
                    fail("DOC_INVALID", name, str(exc))

    def endpoint(name, loc, needs_rx=False):
        if name not in endpoints:
            fail("REF_UNKNOWN_ENDPOINT", loc, name)
        if needs_rx and not endpoints[name].get("rx"):
            fail("DOC_INVALID", loc, "response binding needs endpoint rx and timeout")
        return endpoints[name]

    traversed = 0

    def steps(items, ep, loc, stack=()):
        nonlocal traversed
        if len(stack) > 64:
            fail("DOC_INVALID", loc, "sequence nesting exceeds 64 calls")
        for step in items:
            traversed += 1
            if traversed > 10000:
                fail("DOC_INVALID", loc, "sequence validation exceeds 10000 expanded steps")
            if "call" in step:
                name = step["call"]
                if name not in sequences:
                    fail("REF_UNKNOWN_SEQUENCE", loc, name)
                if name in stack:
                    fail("REF_CYCLE", loc, " -> ".join((*stack, name)))
                steps(sequences[name]["steps"], ep, loc, (*stack, name))
            elif "request" in step and ep is not None:
                endpoint(ep, loc, "expect" in step)
                request = step["request"]
                if isinstance(request, str) and endpoints[ep]["protocol"] == "can":
                    if len(request.split()) > 8:
                        fail("DOC_INVALID", loc, "classic CAN payload exceeds 8 bytes")

    for name, sequence in sequences.items():
        steps(sequence["steps"], None, f"sequences.{name}", (name,))

    def check_inputs(request, loc, allowed):
        if isinstance(request, dict):
            for part in request["parts"]:
                if isinstance(part, dict) and part["input"] not in allowed:
                    fail("DOC_INVALID", loc, f"undeclared encoded input {part['input']}")

    repeats: list[tuple[str, str, str, str, str]] = []

    def action_ref(name, loc):
        if name not in doc.get("actions", {}):
            fail("REF_UNKNOWN_ACTION", loc, name)

    def note_repeat(value, loc):
        repeat = value.get("repeat")
        if repeat is None:
            return
        ep = endpoints[value["endpoint"]]
        if ep["protocol"] != "can":
            fail("DOC_INVALID", loc, "repeat frame requires a raw CAN endpoint")
        limit = 64 if doc["channels"][ep["channel"]]["protocol"] == "canfd" else 8
        mask = repeat["frame"]["mask"]
        if len(mask.split()) > limit:
            fail("DOC_INVALID", loc, "repeat frame exceeds the channel payload length")
        release = repeat["release"]
        if isinstance(release, dict):
            action_ref(release["action"], f"{loc}.repeat.release")
        repeats.append((loc, ep["channel"], ep["tx"], ep["id_format"], mask))

    def body(value, loc, allowed=None):
        allowed = {"value"} if allowed is None else allowed
        if "cases" in value:
            for key, case in value["cases"].items():
                body(case, f"{loc}.cases.{key}", allowed)
        else:
            endpoint(value["endpoint"], loc)

            def inputs(items, visited=()):
                for item in items:
                    if "request" in item:
                        check_inputs(item["request"], loc, allowed)
                    elif (
                        "call" in item and item["call"] not in visited and item["call"] in sequences
                    ):
                        inputs(sequences[item["call"]]["steps"], (*visited, item["call"]))

            if "steps" in value:
                inputs(value["steps"])
                steps(value["steps"], value["endpoint"], loc)
            elif "request" in value:
                inputs([value])
                steps(
                    [{k: value[k] for k in ("request", "expect") if k in value}],
                    value["endpoint"],
                    loc,
                )
            if "release" in value:
                action_ref(value["release"]["action"], f"{loc}.release")
            note_repeat(value, loc)

    def binding(value, kind, loc, output=None):
        if "source" in value:
            name = value["source"]
            if name not in sources:
                fail("REF_UNKNOWN_SOURCE", loc, name)
            source = sources[name]
            if source["kind"] != kind:
                fail("REF_SOURCE_KIND", loc, name)
            resolved = binding(source, kind, loc, value["output"])
            return {**resolved, **{k: value[k] for k in ("enum", "decode_as") if k in value}}
        if "dbc" in value:
            if value["dbc"] not in dbcs:
                fail("DBC_UNKNOWN_MESSAGE", loc, f"unknown DBC {value['dbc']}")
            dbc = dbcs[value["dbc"]]
            dbc.message(value["message"])
            sig = value.get("signal", output)
            if sig is None:
                return {}
            signal = dbc.signal(value["message"], sig)
            return {
                "unit": signal.unit,
                **{k: value[k] for k in ("enum", "decode_as") if k in value},
            }
        if kind == "query":
            endpoint(value["endpoint"], loc, True)
        else:
            if value["channel"] not in doc.get("channels", {}):
                fail("DOC_INVALID", loc, "unknown signal channel")
            limit = 0x7FF if value["id_format"] == "standard" else 0x1FFFFFFF
            if int(value["id"], 16) > limit:
                fail("DOC_INVALID", loc, "CAN ID outside selected format")
        if output is not None:
            if output not in value.get("outputs", {}):
                fail("REF_UNKNOWN_SOURCE", loc, f"unknown output {output}")
            return value["outputs"][output]
        return value.get("decode", {})

    for name, source in sources.items():
        binding(source, source["kind"], f"sources.{name}")
    for name, query in doc.get("queries", {}).items():
        binding(query, "query", f"queries.{name}")
        check_inputs(
            query["request"],
            f"queries.{name}",
            set(query.get("input_schema", {}).get("properties", {})),
        )
    for name, action in doc.get("actions", {}).items():
        body(action, f"actions.{name}", set(action.get("input_schema", {}).get("properties", {})))
    for path, prop in doc.get("properties", {}).items():
        if "write" in prop:
            body(prop["write"], f"properties.{path}.write")
        for kind in ("signal", "query"):
            if kind not in prop.get("read", {}):
                continue
            decoder = binding(prop["read"][kind], kind, path)
            read_binding = prop["read"][kind]
            if "source" in read_binding:
                read_binding = sources[read_binding["source"]]
            if "request" in read_binding:
                check_inputs(read_binding["request"], path, set())
            if kind == "signal" and "length" in read_binding:
                end = (
                    (decoder.get("byte", 0) + decoder.get("bytes", 0)) * 8
                    if "byte" in decoder
                    else decoder.get("start_bit", 0) + decoder.get("bits", 0)
                )
                if end > read_binding["length"] * 8:
                    fail("DOC_INVALID", path, "decoder exceeds frame length")
            entry = catalog[path]
            if decoder.get("datatype") and decoder["datatype"] != entry["datatype"]:
                fail("VSS_ENUM_VALUE", path, "decoder datatype differs from VSS")
            unit = decoder.get("unit")
            if unit and unit != entry.get("unit"):
                fail("VSS_UNIT_MISMATCH", path, f"{unit!r} != {entry.get('unit')!r}")
            if decoder.get("decode_as") == "boolean" and entry["datatype"] != "boolean":
                fail("VSS_ENUM_VALUE", path, "boolean decoder on nonboolean property")
            for value in decoder.get("enum", {}).values():
                check_value(value, entry, path)

    owned: dict[tuple[str, str, str], list[int]] = {}
    for loc, channel, tx, id_format, mask in repeats:
        key = (channel, tx, id_format)
        bits = owned.setdefault(key, [])
        for index, byte in enumerate(bytes.fromhex(mask)):
            if index == len(bits):
                bits.append(0)
            if bits[index] & byte:
                fail("DOC_INVALID", loc, "repeat mask overlaps another command on the same CAN id")
            bits[index] |= byte


def validate_fixtures(fixture, doc):
    for case in fixture.cases:
        loc = case.label or case.path or case.name
        if case.path:
            prop = doc.get("properties", {}).get(case.path)
            if prop is None:
                fail("FIXTURE_INVALID", loc, "unknown property")
            present = "write" in prop if case.kind == "write" else case.kind in prop.get("read", {})
            if not present:
                fail("FIXTURE_INVALID", loc, "fixture kind has no matching binding")
        else:
            section = "actions" if case.kind == "action" else "queries"
            if case.name not in doc.get(section, {}):
                fail("FIXTURE_INVALID", loc, "unknown named capability")


def resolve(
    packages,
    vehicle=None,
    strict=True,
    overlays=(),
    integrity_required=False,
    supported_extensions=None,
):
    vehicle = vehicle or {}
    supported_extensions = supported_extensions or {}
    result: dict[str, Any] = {}
    owners: dict[tuple[str, str], str] = {}
    dbcs: dict[str, Dbc] = {}
    loaded: dict[str, str] = {}
    fixtures, metadata = [], []
    for source in [*packages, *overlays]:
        pkg = Package(source, strict, integrity_required)
        m = pkg.manifest
        if m.id in loaded:
            fail("MERGE_CONFLICT", m.id, "duplicate package ID in composition")
        for dep in m.depends:
            try:
                valid = dep.id in loaded and NpmSpec(dep.version).match(Version(loaded[dep.id]))
            except ValueError:
                valid = False
            if not valid:
                fail("DEP_UNSATISFIED", dep.id, dep.version)
        app = m.applies_to.model_dump(exclude_none=True)
        if not applicable(app, vehicle):
            continue
        # Namespace DBC assets internally; references in exported bindings use these stable IDs.
        for key, ref in m.dbc.items():
            dbcs[f"{m.id}:{key}"] = Dbc(pkg.read(ref.path).decode("utf-8"))
        for raw, ref_app, override in pkg.documents():
            if not isinstance(raw, dict):
                fail("DOC_INVALID", str(source), "document must be object")
            if raw.get("version") == 1:
                fail("DOC_LEGACY_FORMAT", str(source), "run vprofile migrate")
            effective = intersect(intersect(app, ref_app), raw.get("applies_to", {}))
            if not applicable(effective, vehicle):
                continue
            raw = deepcopy(raw)

            for binding in raw.get("sources", {}).values():
                if isinstance(binding, dict) and isinstance(binding.get("dbc"), str):
                    binding["dbc"] = f"{m.id}:{binding['dbc']}"
            for prop in raw.get("properties", {}).values():
                if isinstance(prop, dict) and isinstance(prop.get("read"), dict):
                    binding = prop["read"].get("signal")
                    if isinstance(binding, dict) and isinstance(binding.get("dbc"), str):
                        binding["dbc"] = f"{m.id}:{binding['dbc']}"

            merge_document(result, raw, m.id, owners, override, strict)
        for ref in m.fixtures:
            path = ref if isinstance(ref, str) else ref.path
            fixtures.append(validate_model(Fixture, pkg.parse(path), path, strict))
        loaded[m.id] = m.version
        metadata.append(
            {"id": m.id, "version": m.version, "applies_to": app, "unmapped": m.unmapped}
        )
    typed = validate_model(Document, result, strict=strict)
    result = typed.model_dump(exclude_unset=True, exclude_none=True)
    catalog = load_catalog()
    validate_properties(result, catalog)
    validate_references(result, dbcs, catalog)
    for fixture in fixtures:
        validate_fixtures(fixture, result)
    for name in result.get("extensions", {}):
        if name not in result.get("requires", {}):
            fail("EXT_NOT_REQUIRED", name, "declare extension in requires")
    for name, version in result.get("requires", {}).items():
        if not re.fullmatch(r"[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+", name):
            fail("DOC_INVALID", name, "extension feature IDs must be publisher-qualified")
        try:
            Version(version)
        except ValueError:
            fail("DOC_INVALID", name, "requires must pin an exact semantic version")
        if supported_extensions.get(name) != version:
            fail("EXT_UNSUPPORTED", name, f"required {version}; package cannot fully activate")
    return {"format": 2, "vss": "6.1", "packages": metadata, "vehicle": vehicle, **result}
