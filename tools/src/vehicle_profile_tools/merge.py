from copy import deepcopy

from .container import validate_model
from .errors import fail
from .manifest import Applicability
from .model import DocumentRaw

SECTIONS = (
    "channels",
    "endpoints",
    "sources",
    "properties",
    "sequences",
    "queries",
    "actions",
    "requires",
    "extensions",
)


def domains(app):
    app = validate_model(Applicability, app, "applies_to").model_dump(exclude_none=True)
    result: dict[str, set] = {}
    for key, values in app.items():
        result[key] = set()
        for value in values:
            if isinstance(value, dict):
                result[key].update(range(value["range"][0], value["range"][1] + 1))
            else:
                result[key].add(value)
    return result


def intersect(parent, child):
    p, c = domains(parent), domains(child)
    for key in p.keys() & c.keys():
        if not c[key] <= p[key]:
            fail(
                "APPLICABILITY_WIDENED",
                f"applies_to.{key}",
                "document widens package applicability",
            )
    return {key: sorted(c.get(key, p.get(key, set()))) for key in p.keys() | c.keys()}


def applicable(app, vehicle):
    aliases = {
        "manufacturers": "make",
        "models": "model",
        "years": "year",
        "trims": "trim",
        "engines": "engine",
        "markets": "market",
    }
    for key, values in domains(app).items():
        val = vehicle.get(aliases[key], vehicle.get(key))
        if val is not None and val not in values:
            return False
    return True


def merge_document(result, raw, owner, owners, override=False, strict=True):
    validate_model(DocumentRaw, raw, owner, strict)
    for section in SECTIONS:
        for key, value in raw.get(section, {}).items():
            identity = (section, key)
            if identity in owners and owners[identity] != owner and not override:
                fail("MERGE_CONFLICT", f"{section}.{key}", "later package needs override: true")
            if value is None:
                result.setdefault(section, {}).pop(key, None)
                owners.pop(identity, None)
            else:
                result.setdefault(section, {})[key] = deepcopy(value)
                owners[identity] = owner
