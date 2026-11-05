"""Pure reference codecs; no transport or execution engine."""

import re
from decimal import Decimal
from fractions import Fraction
from typing import Any

from .model import sends_fd


def frame_limit(channel, endpoint):
    """Largest raw CAN data field an endpoint sends; ISO-TP adapters segment payloads."""
    if endpoint["protocol"] != "can":
        return None
    return 64 if sends_fd(channel, endpoint) else 8


def hex_bytes(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-F]{2}( [0-9A-F]{2})*", value):
        raise ValueError("expected uppercase spaced hex bytes")
    return bytes.fromhex(value)


def _frame_bytes(value):
    if isinstance(value, str):
        return hex_bytes(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    raise ValueError("expected uppercase spaced hex bytes")


def check_repeat_frame(mask, patch):
    """A repeat frame owns the bits set in mask and writes patch into those bits."""
    mask_b, patch_b = _frame_bytes(mask), _frame_bytes(patch)
    if len(mask_b) != len(patch_b):
        raise ValueError("mask and patch differ in length")
    if not any(mask_b):
        raise ValueError("mask owns no bits")
    if any(bit & ~owned for bit, owned in zip(patch_b, mask_b, strict=True)):
        raise ValueError("patch sets bits outside the mask")
    return mask_b, patch_b


def merge_repeat_frame(base, mask, patch):
    """Copy unowned bits from the latest frame and write the owned bits from patch."""
    mask_b, patch_b = check_repeat_frame(mask, patch)
    base_b = _frame_bytes(base)
    if len(base_b) != len(mask_b):
        raise ValueError("base frame length differs from mask")
    merged = (
        (current & ~owned) | bit
        for current, owned, bit in zip(base_b, mask_b, patch_b, strict=True)
    )
    return bytes(merged)


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
    authorization, response matching or deadlines. duration is information:
    a positive number of milliseconds, or latched when the effect stays.
    Absent duration and repeat mean the hold time is unknown.
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
                channel = document.get("channels", {}).get(endpoint.get("channel"), {})
                limit = frame_limit(channel, endpoint)
                if limit is not None and len(payload) > limit:
                    raise ValueError(f"raw CAN request exceeds {limit} bytes")
                result.append({**step, "request": payload.hex(" ").upper()})
            else:
                result.append(dict(step))

    if "steps" in body:
        expand(body["steps"])
    elif "request" in body:
        expand([{k: body[k] for k in ("request", "expect") if k in body}])
    prepared: dict[str, Any] = {"endpoint": body["endpoint"], "steps": result}
    for key in ("duration", "release", "repeat"):
        if key in body:
            prepared[key] = body[key]
    return prepared
