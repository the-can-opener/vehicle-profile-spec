import json
from decimal import Decimal
from pathlib import Path

from .codec import check_constraints
from .errors import fail


def resource(name):
    packaged = Path(__file__).parent / "data" / name
    if packaged.exists():
        return packaged
    root = Path(__file__).resolve().parents[3]
    return root / ("docs" if name.endswith(".yaml") else "catalog") / name


def load_catalog(release="6.1"):
    if release != "6.1":
        fail("VSS_UNSUPPORTED_RELEASE", release, "only 6.1 is bundled")
    raw = json.loads(resource(f"vss-{release}.json").read_text())
    result = {}

    def walk(nodes, prefix=""):
        for key, node in nodes.items():
            path = f"{prefix}.{key}" if prefix else key
            if node.get("type") == "branch":
                walk(node.get("children", {}), path)
            else:
                result[path] = node

    walk(raw)
    return result


def check_value(value, entry, path):
    dtype = entry.get("datatype", "")
    if dtype.endswith("[]"):
        if not isinstance(value, list):
            fail("VSS_ENUM_VALUE", path, "expected array")
        for item in value:
            check_value(item, {**entry, "datatype": dtype[:-2]}, path)
        return
    valid = True
    if dtype == "boolean":
        valid = type(value) is bool
    elif dtype == "string":
        valid = isinstance(value, str)
    elif dtype.startswith(("uint", "int")):
        valid = type(value) is int
        if valid:
            bits = int(dtype.removeprefix("u").removeprefix("int"))
            low = 0 if dtype.startswith("u") else -(2 ** (bits - 1))
            high = 2**bits - 1 if dtype.startswith("u") else 2 ** (bits - 1) - 1
            valid = low <= value <= high
    elif dtype in ("float", "double"):
        valid = type(value) in (float, int)
    if not valid:
        fail("VSS_ENUM_VALUE", path, f"value does not have datatype {dtype}")
    if "allowed" in entry and value not in entry["allowed"]:
        fail("VSS_ENUM_VALUE", path, "outside allowed values")
    if type(value) in (float, int):
        try:
            check_constraints(value, {k: entry[k] for k in ("min", "max") if k in entry})
        except ValueError as exc:
            fail("VSS_ENUM_VALUE", path, str(exc))


def canonical_target(value):
    if isinstance(value, str):
        return value
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) in (int, float):
        decimal = Decimal(str(value))
        if not decimal.is_finite():
            raise ValueError("nonfinite target")
        text = format(decimal, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return "0" if decimal == 0 else text
    raise ValueError("cases require scalar targets")


def case_value(key, entry, path):
    dtype = entry["datatype"]
    if dtype == "string":
        value = key
    else:
        try:
            value = json.loads(key)
        except ValueError:
            fail("VSS_ENUM_VALUE", path, "case key must be a canonical value string")
        try:
            canonical = canonical_target(value)
        except ValueError as exc:
            fail("VSS_ENUM_VALUE", path, str(exc))
        if canonical != key:
            fail("VSS_ENUM_VALUE", path, "noncanonical case key")
    check_value(value, entry, path)
    return value


def validate_properties(document, catalog):
    names = (
        set(document.get("properties", {}))
        | set(document.get("queries", {}))
        | set(document.get("actions", {}))
    )
    for path, prop in document.get("properties", {}).items():
        if path not in catalog:
            fail("VSS_UNKNOWN_PATH", path, "not in pinned catalog")
        entry = catalog[path]
        if "write" in prop and entry["type"] != "actuator":
            fail("VSS_ROLE_MISMATCH", path, "only actuators can be written")
        if "value" in prop:
            if entry["type"] != "attribute":
                fail("VSS_ROLE_MISMATCH", path, "only attributes have static values")
            check_value(prop["value"], entry, path)
        for alias in prop.get("aliases", []):
            if alias in names:
                fail("ALIAS_COLLISION", path, alias)
            names.add(alias)
        write = prop.get("write", {})
        constraints = write.get("constraints", {})
        dtype = entry["datatype"]
        if constraints and (dtype.endswith("[]") or dtype in ("boolean", "string")):
            fail("VSS_CONSTRAINT_WIDENED", path, "numeric constraints require a numeric scalar")
        limits = {k: entry[k] for k in ("min", "max") if k in entry}
        if dtype.startswith(("int", "uint")) and not dtype.endswith("[]"):
            bits = int(dtype.removeprefix("u").removeprefix("int"))
            limits.setdefault("min", 0 if dtype.startswith("u") else -(2 ** (bits - 1)))
            limits.setdefault("max", 2**bits - 1 if dtype.startswith("u") else 2 ** (bits - 1) - 1)
        for bound in ("min", "max"):
            if bound in constraints and bound in limits:
                widened = (
                    constraints[bound] < limits[bound]
                    if bound == "min"
                    else constraints[bound] > limits[bound]
                )
                if widened:
                    fail("VSS_CONSTRAINT_WIDENED", path, bound)
        for key in write.get("cases", {}):
            value = case_value(key, entry, path)
            if constraints and type(value) in (int, float):
                try:
                    check_constraints(value, constraints)
                except ValueError as exc:
                    fail("VSS_ENUM_VALUE", path, str(exc))
