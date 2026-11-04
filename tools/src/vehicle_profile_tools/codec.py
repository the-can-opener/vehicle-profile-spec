"""Pure reference codecs; no transport or execution engine."""

import re
from decimal import Decimal
from fractions import Fraction
from typing import Any


def hex_bytes(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-F]{2}( [0-9A-F]{2})*", value):
        raise ValueError("expected uppercase spaced hex bytes")
    return bytes.fromhex(value)


def matches(pattern, data):
    if isinstance(data, str):
        data = hex_bytes(data)
    tokens = pattern["prefix"].split(" ")
    if any(t != "*" and not re.fullmatch("[0-9A-F]{2}", t) for t in tokens):
        raise ValueError("invalid response pattern")
    if len(data) < len(tokens) + pattern.get("min_data_bytes", 0):
        return False
    if pattern.get("exact", False) and len(data) != len(tokens):
        return False
    return all(t == "*" or int(t, 16) == b for t, b in zip(tokens, data, strict=False))


def encode(request, inputs):
    if isinstance(request, str):
        return hex_bytes(request)
    result = bytearray()
    for part in request["parts"]:
        if isinstance(part, str):
            result.extend(hex_bytes(part))
            continue
        value = inputs[part["input"]]
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("encoded input must be numeric")
        scale = Fraction(Decimal(str(part.get("scale", 1))))
        if not scale:
            raise ValueError("scale cannot be zero")
        raw = (
            Fraction(Decimal(str(value))) - Fraction(Decimal(str(part.get("offset", 0))))
        ) / scale
        if raw.denominator != 1:
            raise ValueError("encoding must produce an exact integer")
        try:
            result.extend(
                int(raw).to_bytes(
                    part["bytes"], part.get("endian", "big"), signed=part["type"] == "int"
                )
            )
        except OverflowError as exc:
            raise ValueError("encoded integer exceeds wire width") from exc
    return bytes(result)


def check_constraints(value, constraints):
    v = Decimal(str(value))
    if "min" in constraints and v < Decimal(str(constraints["min"])):
        raise ValueError("target below min")
    if "max" in constraints and v > Decimal(str(constraints["max"])):
        raise ValueError("target above max")
    if "step" in constraints:
        step = Fraction(Decimal(str(constraints["step"])))
        if step <= 0:
            raise ValueError("step must be positive")
        n = (Fraction(v) - Fraction(Decimal(str(constraints.get("min", 0))))) / step
        if n.denominator != 1:
            raise ValueError("target is off step grid")


def decode(data, decoder):
    if isinstance(data, str):
        data = hex_bytes(data)
    if "byte" in decoder:
        start, length = decoder["byte"], decoder["bytes"]
        if start + length > len(data):
            raise ValueError("short frame")
        segment = data[start : start + length]
        if decoder["type"] == "ascii":
            return segment.decode("ascii")
        if decoder["type"] == "hex":
            return segment.hex().upper()
        raw = int.from_bytes(segment, decoder.get("endian", "big"), signed=decoder["type"] == "int")
    else:
        start, width = decoder["start_bit"], decoder["bits"]
        if start + width > len(data) * 8:
            raise ValueError("short bit field")
        raw = 0
        for i in range(width):
            pos = start + i
            if decoder["bit_order"] == "msb0":
                raw = (raw << 1) | ((data[pos // 8] >> (7 - pos % 8)) & 1)
            else:
                raw |= ((data[pos // 8] >> (pos % 8)) & 1) << i
        if decoder["type"] == "int" and raw & (1 << (width - 1)):
            raw -= 1 << width
    if raw in decoder.get("invalid_raw", []):
        raise ValueError("invalid raw value")
    if "enum" in decoder:
        if str(raw) not in decoder["enum"]:
            raise ValueError("unmapped enum value")
        return decoder["enum"][str(raw)]
    return raw * decoder.get("scale", 1) + decoder.get("offset", 0)


def prepare_write(document, path, target, catalog=None):
    """Validate a target and return expanded, encoded steps without transmitting.

    This pure helper checks the static command contract, not runtime availability,
    authorization, response matching or deadlines.
    """
    from .catalog import canonical_target, check_value, load_catalog
    from .errors import fail

    catalog = catalog or load_catalog()
    if path not in document.get("properties", {}) or path not in catalog:
        fail("VSS_UNKNOWN_PATH", path, "unknown property")
    prop = document["properties"][path]
    if "write" not in prop:
        raise ValueError("UNSUPPORTED: property is not writable")
    check_value(target, catalog[path], path)
    write = prop["write"]
    if write.get("constraints"):
        check_constraints(target, write["constraints"])
    if "cases" in write:
        key = canonical_target(target)
        if key not in write["cases"]:
            raise ValueError("UNSUPPORTED: target has no case")
        body = write["cases"][key]
    else:
        body = write
    result: list[dict[str, Any]] = []

    def expand(steps, stack=()):
        if len(stack) > 64:
            raise ValueError("sequence nesting exceeds 64 calls")
        for step in steps:
            if len(result) >= 10000:
                raise ValueError("request expands beyond 10000 steps")
            if "call" in step:
                name = step["call"]
                if name in stack:
                    fail("REF_CYCLE", path, name)
                if name not in document.get("sequences", {}):
                    fail("REF_UNKNOWN_SEQUENCE", path, name)
                expand(document["sequences"][name]["steps"], (*stack, name))
            elif "request" in step:
                payload = encode(step["request"], {"value": target})
                endpoint = document["endpoints"][body["endpoint"]]
                if endpoint["protocol"] == "can" and len(payload) > 8:
                    raise ValueError("raw CAN request exceeds 8 bytes")
                result.append({**step, "request": payload.hex(" ").upper()})
            else:
                result.append(dict(step))

    expand(body.get("steps", [{k: body[k] for k in ("request", "expect") if k in body}]))
    return {"endpoint": body["endpoint"], "steps": result}
