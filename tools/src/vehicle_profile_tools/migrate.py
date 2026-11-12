"""Format 1 conversion with explicit framing and a lossless unmapped report."""

import json
import math
import re
import shutil
import tempfile
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from .catalog import check_value, load_catalog, resource, validate_properties
from .container import MAX_FILE, safe_path, validate_model
from .dbc import Dbc
from .errors import ProfileError
from .model import Action, Channel, Endpoint, NamedQuery, Property, expand_rx
from .strict import LegacyLoader, parse

FRAMINGS = (None, "raw", "isotp", "isotp-single-frame")
# Profile spec versions this migrator reads. 1 is spec 1.0. 1.1 names entities and adds
# `values`, flat `ENTITY.command` keys and numeric `encode` on actions.
LEGACY_VERSIONS = (1, 1.1)
# A 1.1 command is a present-tense verb where it differs from the reported condition.
COMMAND_STATES = {
    "lock": "locked",
    "unlock": "unlocked",
    "close": "closed",
    "fold": "folded",
    "unfold": "unfolded",
}
ENCODE_PLACEMENT = ("byte", "start_bit", "length", "byte_order", "signed", "scale", "offset")
ENCODE_BOUNDS = ("min", "max", "step")
# These are spelling aliases for identical units, not numerical conversions.
UNIT_NAMES = {
    "R/min": "rpm",
    "r/min": "rpm",
    "deg": "degrees",
    "C": "Celsius",
    "degC": "Celsius",
    "°C": "Celsius",
    "%": "percent",
    "L/h": "l/h",
}


def hex_string(values, wildcard=False):
    if (
        not isinstance(values, list)
        or not values
        or any(
            not (type(x) is int and 0 <= x <= 255) and not (wildcard and x == "*") for x in values
        )
    ):
        raise ValueError("expected a nonempty legacy byte array")
    return " ".join("*" if x == "*" else f"{x:02X}" for x in values)


def response_pattern(value):
    if isinstance(value, list):
        return {"prefix": hex_string(value, wildcard=True)}
    if not isinstance(value, dict) or set(value) - {"pattern", "exact"}:
        raise ValueError("expected expect array or {pattern, exact}")
    return {
        "prefix": hex_string(value["pattern"], wildcard=True),
        "exact": value.get("exact", False),
    }


def whole(value, low, high):
    return type(value) is int and low <= value <= high


def number(value):
    return type(value) in (int, float)


def encoded_field(encode):
    """A 1.1 `encode` as (first byte, byte count, format 2 encoded part).

    Format 2 encodes whole bytes, so a field that starts or ends inside a byte is refused.
    """
    if not isinstance(encode, dict) or set(encode) - {*ENCODE_PLACEMENT, *ENCODE_BOUNDS}:
        raise ValueError(
            "encode takes byte or start_bit, length, byte_order, signed, scale, offset"
        )
    order = encode.get("byte_order", "little")
    if "byte" in encode:
        if "start_bit" in encode or "length" in encode:
            raise ValueError("encode takes byte, or start_bit and length")
        if not whole(encode["byte"], 0, 7):
            raise ValueError("encode byte must be an integer from 0 to 7")
        start_bit, length = encode["byte"] * 8, 8
    elif "start_bit" in encode:
        start_bit, length = encode["start_bit"], encode.get("length", 8)
    else:
        raise ValueError("encode must declare byte or start_bit")
    scale, offset = encode.get("scale", 1), encode.get("offset", 0)
    if (
        not whole(start_bit, 0, 63)
        or not whole(length, 1, 52)
        or order not in ("little", "big")
        or type(encode.get("signed", False)) is not bool
        or not number(scale)
        or not scale
        or not number(offset)
    ):
        raise ValueError("invalid encode field")
    # A big-endian start bit is the most significant bit of the first byte.
    if start_bit % 8 != (0 if order == "little" else 7) or length % 8:
        raise ValueError("encode is not a whole-byte field; format 2 encodes whole bytes")
    part: dict[str, Any] = {
        "input": "value",
        "type": "int" if encode.get("signed", False) else "uint",
        "bytes": length // 8,
    }
    if length > 8:
        part["endian"] = order
    if scale != 1:
        part["scale"] = scale
    if offset:
        part["offset"] = offset
    return start_bit // 8, length // 8, part


def input_bounds(encode):
    bounds = {key: encode[key] for key in ENCODE_BOUNDS if key in encode}
    if any(not number(value) for value in bounds.values()) or bounds.get("step", 1) <= 0:
        raise ValueError("encode min, max and step must be numbers, with a positive step")
    return bounds


def dbc_decoder(signal, skip_bytes=0):
    """Translate native DBC sawtooth/little-endian bits to prefix-relative core bits."""
    start = signal.start if signal.little else signal.start // 8 * 8 + 7 - signal.start % 8
    start -= skip_bytes * 8
    if start < 0:
        raise ValueError("DBC field overlaps the response prefix or transport header")
    result = {
        "start_bit": start,
        "bits": signal.bits,
        "bit_order": "lsb0" if signal.little else "msb0",
        "type": "int" if signal.signed else "uint",
    }
    if signal.factor != 1:
        result["scale"] = signal.factor
    if signal.offset != 0:
        result["offset"] = signal.offset
    if signal.unit:
        result["unit"] = UNIT_NAMES.get(signal.unit, signal.unit)
    return result


class Migrator:
    def __init__(self, source, framing=None, responders=None, steering_side=None):
        if framing not in FRAMINGS or steering_side not in (None, "left", "right"):
            raise ValueError("invalid migration framing or steering side")
        self.source = Path(source)
        self.framing = framing
        self.responders = responders or {}
        self.steering_side = steering_side
        self.legacy = parse(
            self.read("profile.yaml").decode("utf-8"), "profile.yaml", loader=LegacyLoader
        )
        if (
            not isinstance(self.legacy, dict)
            or type(self.legacy.get("version")) not in (int, float)
            or self.legacy["version"] not in LEGACY_VERSIONS
        ):
            raise ValueError("expected format 1 profile.yaml declaring version 1 or 1.1")
        self.vocabulary = json.loads(resource("vocabulary.yaml").read_text())
        self.catalog = load_catalog()
        self.doc: dict[str, Any] = {
            "channels": {},
            "endpoints": {},
            "properties": {},
            "sequences": {},
            "actions": {},
            "queries": {},
        }
        self.manifest = {
            "manifest": 1,
            "format": 2,
            "id": "org.canopener.migrated." + re.sub(r"[^a-z0-9_-]", "-", self.source.name.lower()),
            "version": "2.0.0",
            "name": self.legacy.get("name", self.source.name),
            "vss": "6.1",
            "applies_to": self.legacy.get("applies_to", {}),
            "dbc": {},
            "documents": [{"path": "bindings.yaml"}],
            "unmapped": [],
        }
        self.assets: dict[str, bytes] = {}
        self.dbcs: dict[str, Dbc] = {}
        self.notes: list[str] = []
        # Input bounds of the action being converted; None until a request encodes a value.
        self.bounds: dict[str, Any] | None = None

    def read(self, name):
        safe_path(name)
        current = self.source
        if current.is_symlink():
            raise ValueError("symlink legacy package")
        for part in Path(name).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"symlink legacy asset: {name}")
        if current.stat().st_size > MAX_FILE:
            raise ValueError(f"legacy asset too large: {name}")
        return current.read_bytes()

    def unmapped(self, name, reason, original):
        self.manifest["unmapped"].append(
            {"capability": name, "reason": str(reason), "original": original}
        )

    def mapping(self, name):
        result = deepcopy(self.vocabulary.get(name, {}))
        if (
            result.get("note")
            and "left-hand-drive" in result["note"]
            and any(part in result.get("path", "") for part in ("DriverSide", "PassengerSide"))
        ):
            if self.steering_side is None:
                raise ValueError("left/right door identity needs --steering-side left|right")
            if self.steering_side == "right":
                path = result["path"]
                result["path"] = (
                    path.replace("DriverSide", "TEMP")
                    .replace("PassengerSide", "DriverSide")
                    .replace("TEMP", "PassengerSide")
                )
        return result

    def channel(self, bus):
        """Logical bus N becomes channel canN. An undeclared bus kept adapter timing."""
        if type(bus) is not int or not 0 <= bus <= 255:
            raise ValueError("legacy bus must be an integer from 0 to 255")
        name = f"can{bus}"
        if name in self.doc["channels"]:
            return name
        old = self.legacy.get("can", {}).get("buses", {}).get(str(bus))
        if old is None:
            channel: dict[str, Any] = {"protocol": "can", "configuration": "runtime"}
        else:
            fd = old.get("fd")
            sends_fd = fd is not None and fd is not False  # true, {} and {isotp: ...} all mean FD
            channel = {
                "protocol": "canfd" if sends_fd or "data_bitrate" in old else "can",
                "bitrate": old["bitrate"],
            }
            if "data_bitrate" in old:
                channel["data_bitrate"] = old["data_bitrate"]
            if isinstance(fd, dict) and "isotp" in fd:
                channel["fd"] = {"tx_dl": fd["isotp"]["tx_dl"]}
            elif sends_fd:
                channel["fd"] = True
        validate_model(Channel, channel, f"channels.{name}")
        self.doc["channels"][name] = channel
        return name

    @staticmethod
    def addressing(old):
        fields = {
            "extended": ("target_address", "source_address"),
            "mixed": ("address_extension",),
        }
        keys = fields.get(old["mode"])
        if keys is None:
            raise ValueError("addressing mode must be extended or mixed")
        if set(old) != {"mode", *keys}:
            raise ValueError(f"{old['mode']} addressing takes exactly {', '.join(keys)}")
        return {"mode": old["mode"], **{key: f"{old[key]:02X}" for key in keys}}

    def endpoint(self, name):
        if name not in self.legacy.get("endpoints", {}):
            raise ValueError(f"unknown legacy endpoint {name}")
        if name in self.doc["endpoints"]:
            return self.doc["endpoints"][name]
        old = self.legacy["endpoints"][name]
        rx: list[Any] = [f"{old['response_id']:X}"] if "response_id" in old else []
        for value in old.get("response_ids", []):
            if isinstance(value, dict):
                low, high = value["range"]
                rx.append({"range": [f"{low:X}", f"{high:X}"]})
            else:
                rx.append(f"{value:X}")
        ids = expand_rx(rx)
        ep: dict[str, Any] = {
            "channel": self.channel(old.get("bus", 0)),
            "protocol": "isotp"
            if rx and self.framing in ("isotp", "isotp-single-frame")
            else "can",
            "tx": f"{old['request_id']:X}",
            "id_format": "extended"
            if old.get("extended") or any(x > 0x7FF for x in [old["request_id"], *ids])
            else "standard",
        }
        if rx:
            ep.update(rx=rx, timeout_ms=old.get("timeout_ms", 500))
        if len(ids) > 1:
            selected = self.responders.get(name)
            if (
                selected is None
                or not re.fullmatch("[0-9A-F]{1,8}", selected)
                or int(selected, 16) not in ids
            ):
                raise ValueError(
                    f"multiple responders require --responder {name}=HEX selecting a listed ID"
                )
            ep["responder"] = selected
        if "fd" in old:
            ep["fd"] = old["fd"]
        if "addressing" in old:
            ep["addressing"] = self.addressing(old["addressing"])
        validate_model(Endpoint, ep, f"endpoints.{name}")
        self.doc["endpoints"][name] = ep
        return ep

    def request(self, values, endpoint, encode=None):
        hex_string(values)  # Reject wildcards, booleans and out-of-range bytes first.
        if encode is not None:
            start, count, part = encoded_field(encode)
            # Like the 1.1 runtime, a field past the declared bytes extends the request.
            values = values + [0] * (start + count - len(values))
        if endpoint["protocol"] == "isotp" and self.framing == "isotp-single-frame":
            if len(values) > 8 or not 1 <= values[0] <= 7 or values[0] > len(values) - 1:
                raise ValueError("declared ISO-TP single frame has an invalid PCI length")
            values = values[1 : 1 + values[0]]
            if encode is not None:
                start -= 1
        if encode is None:
            return hex_string(values)
        if start < 0 or start + count > len(values):
            raise ValueError("encoded field lies outside the request payload")
        fixed = [values[:start], values[start + count :]]
        head, tail = (hex_string(part_bytes) if part_bytes else None for part_bytes in fixed)
        return {"parts": [x for x in (head, part, tail) if x is not None]}

    def steps(self, items, ep_name, stack=(), encode=None):
        """`encode` is the action-level field, which applies to the action's direct sends."""
        ep = self.endpoint(ep_name)
        converted = []
        for item in items:
            if "ref" in item:
                if "encode" in item:
                    raise ValueError("encode cannot be declared on a ref step")
                name = item["ref"].removeprefix("sequences.")
                if name in stack:
                    raise ValueError("sequence cycle: " + " -> ".join((*stack, name)))
                old = self.legacy.get("sequences", {}).get(name)
                if old is None:
                    raise ValueError(f"unknown sequence {name}")
                if old.get("endpoint", ep_name) != ep_name:
                    raise ValueError(
                        f"sequence {name} changes endpoint; split into separately invoked actions"
                    )
                steps = self.steps(old["steps"], ep_name, (*stack, name))
                new_name = name
                if name in self.doc["sequences"] and self.doc["sequences"][name]["steps"] != steps:
                    new_name = name + "--" + ep["protocol"]
                self.doc["sequences"][new_name] = {"steps": steps}
                converted.append({"call": new_name})
            elif "wait_ms" in item:
                converted.append({"wait_ms": item["wait_ms"]})
            else:
                if isinstance(item.get("send"), dict):
                    raise ValueError(
                        "inline send inside steps changes endpoint; split into separate actions"
                    )
                if "timeout_ms" in item:
                    raise ValueError(
                        "per-step timeout_ms has no format 2 form; the endpoint timeout applies"
                    )
                field = item.get("encode", encode)
                step = {"request": self.request(item["send"], ep, field)}
                if field is not None:
                    self.bounds = self.bounds or {}
                    if not stack and "encode" in item:
                        self.bounds.update(input_bounds(item["encode"]))
                if "expect" in item:
                    if self.framing is None:
                        raise ValueError(
                            "response framing requires --framing raw|isotp|isotp-single-frame"
                        )
                    if not ep.get("rx"):
                        raise ValueError("expect requires response IDs")
                    step["expect"] = response_pattern(item["expect"])
                converted.append(step)
                if item.get("delay_ms"):
                    converted.append({"wait_ms": item["delay_ms"]})
        return converted

    def dbc_signal(self, mapping):
        candidates = [
            (key, dbc)
            for key, dbc in self.dbcs.items()
            if any(message.name == mapping["message"] for message in dbc.messages)
        ]
        if len(candidates) != 1:
            raise ValueError("DBC message is missing or ambiguous")
        key, dbc = candidates[0]
        return (
            key,
            dbc.message(mapping["message"]),
            dbc.signal(mapping["message"], mapping["signal"]),
        )

    def normalization(self, name, old, signal, entry):
        enum = old.get("normalize", {}).get("enum")
        canonical = self.vocabulary.get(name, {}).get("enum", {})
        if enum is not None or canonical or (entry and entry["datatype"] == "string"):
            if not signal.labels:
                raise ValueError("enum normalization requires DBC VAL_ labels")
            result = {}
            for raw, label in signal.labels.items():
                value = enum.get(label, label) if enum else label
                value = canonical.get(str(value), value)
                if entry and entry["datatype"] == "boolean":
                    if value not in ("on", "off", "open", "closed", True, False):
                        raise ValueError(f"unknown boolean label {value!r}")
                    value = value in ("on", "open", True)
                if entry:
                    check_value(value, entry, name)
                result[raw] = value
            return {"enum": result}
        if entry and entry["datatype"] == "boolean":
            return {"enum": {"0": False, "1": True}}
        return {}

    def property(self, path, alias):
        prop = self.doc["properties"].setdefault(path, {"aliases": []})
        if alias not in prop["aliases"]:
            prop["aliases"].append(alias)
        return prop

    def validate_decoder(self, decoder, entry, name):
        if entry and decoder.get("unit") and decoder["unit"] != entry.get("unit"):
            raise ValueError(f"unit {decoder['unit']!r} differs from VSS {entry.get('unit')!r}")
        if entry and entry["datatype"].startswith(("int", "uint")) and not decoder.get("enum"):
            if any(
                not float(decoder.get(k, default)).is_integer()
                for k, default in [("scale", 1), ("offset", 0)]
            ):
                raise ValueError("fractional decoder cannot preserve the integer VSS datatype")
        if entry:
            for value in decoder.get("enum", {}).values():
                check_value(value, entry, name)

    def signal(self, name, old):
        mapping = self.mapping(name)
        if "path" not in mapping:
            raise ValueError(mapping.get("reason", "no canonical property mapping"))
        path = mapping["path"]
        entry = self.catalog[path]
        key, message, signal = self.dbc_signal(old["monitor"])
        channel = self.channel(old["monitor"].get("bus", 0))
        decoder = dbc_decoder(signal)
        norm = self.normalization(name, old, signal, entry)
        if norm:
            decoder.pop("scale", None)
            decoder.pop("offset", None)
            decoder.update(norm)
        self.validate_decoder(decoder, entry, name)
        monitor = {k: v for k, v in old["monitor"].items() if k != "bus"}
        if (
            signal.unit == decoder.get("unit", "")
            and channel == self.manifest["dbc"][key]["channel"]
        ):
            binding = {"dbc": key, **monitor, **norm}
        else:
            # A renamed unit or a DBC bound to another channel needs an inline frame binding.
            binding = {
                "channel": channel,
                "id": f"{message.id & 0x1FFFFFFF:X}",
                "id_format": "extended" if message.id > 0x7FF else "standard",
                "length": message.length,
                "decode": decoder,
            }
        prop = self.property(path, name)
        prop.setdefault("read", {})["signal"] = binding
        validate_model(Property, prop, path)

    def query(self, name, old):
        if self.framing is None:
            raise ValueError("response framing requires --framing raw|isotp|isotp-single-frame")
        ep = self.endpoint(old["endpoint"])
        if not ep.get("rx"):
            raise ValueError("query requires response IDs")
        if "timeout_ms" in old:
            raise ValueError(
                "per-query timeout_ms has no format 2 form; the endpoint timeout applies"
            )
        mapping = self.mapping(name)
        path = mapping.get("path")
        if mapping.get("reason"):
            raise ValueError(mapping["reason"])
        entry = self.catalog[path] if path else None
        pattern = response_pattern(old["expect"])
        if "dbc_mapping" in old:
            _, message, signal = self.dbc_signal(old["dbc_mapping"])
            selected = ep.get("responder", ep["rx"][0])
            if message.id & 0x1FFFFFFF != int(selected, 16):
                raise ValueError("DBC response ID differs from selected endpoint responder")
            skip = len(pattern["prefix"].split()) + (
                1 if self.framing == "isotp-single-frame" else 0
            )
            decoder = dbc_decoder(signal, skip)
            norm = self.normalization(name, old, signal, entry)
            if norm:
                decoder.pop("scale", None)
                decoder.pop("offset", None)
                decoder.update(norm)
            self.validate_decoder(decoder, entry, name)
            datatype = entry["datatype"] if entry else "double"
            if norm and not entry:
                values = list(norm["enum"].values())
                datatype = "boolean" if all(type(v) is bool for v in values) else "string"
            needed = math.ceil((decoder["start_bit"] + decoder["bits"]) / 8)
        else:
            definition = old.get("decoder")
            if isinstance(definition, str):
                definition = {"type": definition, "length": old.get("length")}
            if not isinstance(definition, dict) or definition.get("type") not in ("ascii", "bytes"):
                raise ValueError("unsupported legacy decoder")
            length = definition.get("length", old.get("length"))
            if type(length) is not int or length <= 0:
                raise ValueError("variable-length decoder requires an explicit codec extension")
            # Core ascii intentionally has no legacy trailing-NUL trimming behavior.
            if definition["type"] == "ascii" and name != "VIN":
                raise ValueError(
                    "legacy ASCII trims trailing NULs; non-VIN strings need codec review"
                )
            decoder = {
                "byte": 0,
                "bytes": length,
                "type": "ascii" if definition["type"] == "ascii" else "hex",
            }
            datatype, needed = "string", length
            if definition["type"] == "bytes":
                self.notes.append(
                    f"{name}: legacy byte-array results are represented as uppercase hex strings."
                )
        pattern["min_data_bytes"] = needed
        query = {
            "endpoint": old["endpoint"],
            "request": self.request(old["send"], ep),
            "response": pattern,
            "decode": decoder,
        }
        if "interval_ms" in old:
            query["interval_ms"] = old["interval_ms"]
        if path:
            prop = self.property(path, name)
            prop.setdefault("read", {})["query"] = query
            validate_model(Property, prop, path)
        else:
            query.update(description=old.get("description", name), datatype=datatype)
            if decoder.get("unit"):
                query["unit"] = decoder["unit"]
            validate_model(NamedQuery, query, name)
            if name in self.doc["actions"]:
                raise ValueError("name is already an action")
            self.doc["queries"][mapping.get("query", name)] = query

    def commands(self):
        """Legacy actions, with a 1.1 `values` entity split into one `ENTITY.command` each."""
        for name, old in self.legacy.get("actions", {}).items():
            values = old.get("values") if isinstance(old, dict) else None
            if (
                not isinstance(values, dict)
                or not values
                or "." in name
                or {"send", "steps", "expect", "encode"} & old.keys()
                or any(
                    not command
                    or "." in command
                    or not isinstance(branch, dict)
                    or {"values", "encode"} & branch.keys()
                    for command, branch in values.items()
                )
            ):
                yield name, old  # A trigger, a flat name, or a malformed entity for action().
                continue
            defaults = {key: old[key] for key in ("endpoint", "batch") if key in old}
            for command, branch in values.items():
                yield f"{name}.{command}", {**defaults, **branch}

    def command_target(self, command, mapping):
        """VSS target of a 1.1 command: its condition in the vocabulary enum, or a boolean."""
        path = mapping["path"]
        entry = self.catalog[path]
        if entry["type"] != "actuator":
            raise ValueError(f"{path} is a {entry['type']}, not an actuator")
        state = COMMAND_STATES.get(command, command)
        enum = mapping.get("enum", {})
        if state in enum:
            target = enum[state]
        elif entry["datatype"] == "boolean" and state in ("on", "off", "open", "closed"):
            target = state in ("on", "open")
        elif state.upper() in entry.get("allowed", []):
            target = state.upper()
        else:
            raise ValueError(f"no VSS target is established for command {command!r}")
        check_value(target, entry, path)
        return target

    def write_case(self, path, alias, target, body):
        prop = self.property(path, alias)
        key = json.dumps(target) if not isinstance(target, str) else target
        cases = prop.setdefault("write", {"cases": {}}).get("cases")
        if cases is None or (key in cases and cases[key] != body):
            raise ValueError("conflicting commands for the same actuator target")
        cases[key] = body
        validate_model(Property, prop, path)

    def numeric_write(self, path, alias, body, bounds):
        """A 1.1 numeric entity becomes a write whose request encodes the target."""
        entry = self.catalog[path]
        if entry["type"] != "actuator" or not re.fullmatch(
            r"u?int\d+|float|double", entry["datatype"]
        ):
            raise ValueError(f"{path} is not a numeric actuator")
        prop = self.property(path, alias)
        if "write" in prop:
            raise ValueError("conflicting commands for the same actuator target")
        prop["write"] = {**body, **({"constraints": bounds} if bounds else {})}
        validate_model(Property, prop, path)
        # Bounds may narrow the catalog domain and never widen it.
        validate_properties({"properties": {path: prop}}, self.catalog)

    def action(self, name, old):
        if not isinstance(old, dict):
            raise ValueError("an action is an object with send or steps")
        if "values" in old:
            raise ValueError(
                "an entity with values takes one send or steps per command "
                "and no send, steps, expect or encode of its own"
            )
        entity, _, command = name.partition(".")
        if "." in name and (not entity or not command or "." in command):
            raise ValueError("an action name takes one ENTITY.command separator at most")
        self.bounds = None
        if "batch" in old:
            self.notes.append(
                f"{name}: legacy batch is runtime transport policy and has no format 2 field."
            )
        field = old.get("encode")
        if isinstance(old.get("send"), dict):
            send = old["send"]
            endpoint = "generated-" + name.lower().replace(".", "-")
            generated = {
                "channel": self.channel(send.get("bus", 0)),
                "protocol": "can",
                "tx": f"{send['request_id']:X}",
                "id_format": "extended" if send["request_id"] > 0x7FF else "standard",
            }
            if "fd" in send:
                generated["fd"] = send["fd"]
            validate_model(Endpoint, generated, f"endpoints.{endpoint}")
            self.doc["endpoints"][endpoint] = generated
            body = {
                "endpoint": endpoint,
                "request": self.request(send["request"], generated, field),
            }
            if field is not None:
                self.bounds = input_bounds(field)
        else:
            endpoint = old["endpoint"]
            if "steps" in old:
                # Bounds alone on the action leave the field to the steps that declare one.
                inherited = field if field and set(field) & set(ENCODE_PLACEMENT) else None
                body = {
                    "endpoint": endpoint,
                    "steps": self.steps(old["steps"], endpoint, encode=inherited),
                }
            else:
                body = {"endpoint": endpoint, **self.steps([old], endpoint)[0]}
            if field is not None:
                if self.bounds is None:
                    raise ValueError("encode needs a send that carries the value")
                self.bounds.update(input_bounds(field))
        if "deadline_ms" in old:
            body["deadline_ms"] = old["deadline_ms"]
        mapping = self.mapping(entity)
        path, bounds = mapping.get("path"), self.bounds
        if bounds is not None:
            if command:
                raise ValueError("a command cannot declare encode")
            self.notes.append(
                f"{name}: the request encodes the target. Format 2 refuses a target that does "
                "not encode to a whole number; the legacy runtime rounded it."
            )
            if path and not mapping.get("reason"):
                self.numeric_write(path, name, body, bounds)
                return
        elif command and path and not mapping.get("reason"):
            self.write_case(path, entity, self.command_target(command, mapping), body)
            return
        elif path and "target" in mapping:
            self.write_case(path, name, mapping["target"], body)
            return
        if mapping.get("reason") or path:
            raise ValueError(mapping.get("reason", "actuator target is not established"))
        new_name = mapping.get("action", entity)
        if command:
            # No VSS actuator: each command is a vehicle-specific action of its own.
            new_name += "_" + re.sub(r"[^A-Z0-9]+", "_", command.upper()).strip("_")
            if new_name in self.vocabulary:
                raise ValueError(f"{new_name} is a standard keyword; map the command by hand")
            self.notes.append(f"{name}: no VSS actuator, so the command is action {new_name}.")
        if new_name in self.doc["queries"]:
            raise ValueError("name is already a query")
        if new_name in self.doc["actions"]:
            raise ValueError("name is already an action")
        action = {"description": old.get("description", name), **body}
        for field_name in ("retry", "input_schema"):
            if field_name in old:
                action[field_name] = old[field_name]
        if bounds is not None:
            action["input_schema"] = self.input_schema(name, bounds)
        validate_model(Action, action, new_name)
        self.doc["actions"][new_name] = action

    def input_schema(self, name, bounds):
        value: dict[str, Any] = {"type": "number"}
        if "min" in bounds:
            value["minimum"] = bounds["min"]
        if "max" in bounds:
            value["maximum"] = bounds["max"]
        if "step" in bounds:
            step = Fraction(str(bounds["step"]))
            if (Fraction(str(bounds.get("min", 0))) / step).denominator == 1:
                value["multipleOf"] = bounds["step"]
            else:
                self.notes.append(
                    f"{name}: step {bounds['step']} counts from the minimum, which JSON Schema "
                    "multipleOf cannot state; the caller keeps the grid."
                )
        return {
            "type": "object",
            "properties": {"value": value},
            "required": ["value"],
            "additionalProperties": False,
        }

    def convert(self):
        for bus, original in self.legacy.get("can", {}).get("buses", {}).items():
            try:
                self.channel(int(bus))
            except (ValueError, KeyError, TypeError) as exc:
                self.unmapped(f"can.buses.{bus}", exc, original)
        for i, ref in enumerate(self.legacy.get("dbc", {}).get("files", [])):
            name = ref["path"] if isinstance(ref, dict) else ref
            if name in self.assets or name in ("vehicle.yaml", "bindings.yaml", "README.md"):
                raise ValueError("duplicate or reserved legacy asset path")
            data = self.read(name)
            key = "main" if i == 0 else f"dbc{i}"
            try:
                dbc = Dbc(data.decode("utf-8"))
            except ProfileError as exc:
                self.unmapped(f"dbc.{key}", exc, {"path": name})
                continue
            self.assets[name] = data
            self.manifest["dbc"][key] = {"path": name}
            self.dbcs[key] = dbc
        # A DBC binds to one channel: the single bus its monitored messages use, else bus 0.
        buses: dict[str, set[int]] = {key: set() for key in self.dbcs}
        for old in self.legacy.get("signals", {}).values():
            try:
                key, _, _ = self.dbc_signal(old["monitor"])
                buses[key].add(old["monitor"].get("bus", 0))
            except (ValueError, KeyError, TypeError):
                continue
        for key, used in buses.items():
            self.manifest["dbc"][key]["channel"] = self.channel(
                next(iter(used)) if len(used) == 1 else 0
            )
        for section, method in [
            ("signals", self.signal),
            ("queries", self.query),
            ("actions", self.action),
        ]:
            entries = self.legacy.get(section, {}).items()
            for name, original in self.commands() if section == "actions" else entries:
                before, notes = deepcopy(self.doc), list(self.notes)
                try:
                    method(name, original)
                except (ValueError, KeyError, TypeError) as exc:
                    self.doc, self.notes = before, notes
                    self.unmapped(name, exc, original)
        for name, original in self.legacy.get("endpoints", {}).items():
            try:
                self.endpoint(name)
            except (ValueError, KeyError, TypeError) as exc:
                self.unmapped(f"endpoints.{name}", exc, original)
        used = {name.split("--")[0] for name in self.doc["sequences"]}
        for name, original in self.legacy.get("sequences", {}).items():
            if name not in used:
                self.unmapped(
                    f"sequences.{name}",
                    "no successfully migrated caller; original retained",
                    original,
                )
        unknown_selections = self.responders.keys() - self.legacy.get("endpoints", {}).keys()
        if unknown_selections:
            raise ValueError(f"unknown responder endpoints: {sorted(unknown_selections)}")

    def write(self, destination):
        self.convert()
        for name, data in self.assets.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (destination / "vehicle.yaml").write_text(yaml.safe_dump(self.manifest, sort_keys=False))
        (destination / "bindings.yaml").write_text(yaml.safe_dump(self.doc, sort_keys=False))
        (destination / "README.md").write_text(
            "# Migrated package\n\n"
            f"Legacy framing: `{self.framing or 'unspecified'}`. Steering side: `{self.steering_side or 'unspecified'}`.\n\n"
            "Review unmapped records, which retain original input objects. No physical vehicle compatibility is claimed.\n\n"
            + "\n".join("- " + note for note in self.notes)
            + "\n"
        )
        from .resolve import resolve

        resolve([destination])
        return self.manifest["unmapped"]


def migrate(source, destination, *, framing=None, responders=None, steering_side=None):
    """Convert into an empty destination; validate before publishing any output."""
    destination = Path(destination)
    if destination.is_symlink() or (
        destination.exists() and (not destination.is_dir() or any(destination.iterdir()))
    ):
        raise ValueError("migration destination must be an empty, non-symlink directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    migrator = Migrator(source, framing, responders, steering_side)
    with tempfile.TemporaryDirectory(
        prefix=".vprofile-migrate-", dir=destination.parent
    ) as staging:
        report = migrator.write(Path(staging))
        destination.mkdir(exist_ok=True)
        for path in Path(staging).iterdir():
            shutil.move(str(path), destination / path.name)
    return report
