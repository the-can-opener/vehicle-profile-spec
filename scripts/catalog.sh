#!/bin/sh
set -eu
source_repo=${VSS_SOURCE:-../vehicle_signal_specification}
expected=2817646d1808fc7c470c0432fc7f4ed685e5c9e3
actual=$(git -C "$source_repo" rev-parse 'v6.1^{commit}')
[ "$actual" = "$expected" ] || { echo "Unexpected VSS 6.1 tag commit" >&2; exit 1; }
task_tmp=$(mktemp -d)
trap 'rm -rf "$task_tmp"' EXIT HUP INT TERM
git -C "$source_repo" archive v6.1 -o "$task_tmp/vss.tar"
tar -xf "$task_tmp/vss.tar" -C "$task_tmp"
uv tool run --from vss-tools==1.9.9 vspec export json --strict -u "$task_tmp/spec/units.yaml" -s "$task_tmp/spec/VehicleSignalSpecification.vspec" -o catalog/vss-6.1.json
# Local departure from the v6.1 tag: SteeringWheel.Angle is float, not int16.
# See catalog/README.md. The tag export above would otherwise restore int16.
python3 - <<'PY'
from pathlib import Path

path = Path("catalog/vss-6.1.json")
text = path.read_text()
old = (
    '"Angle": {"datatype": "int16", "description": "Steering wheel angle. '
    'Positive = degrees to the left. Negative = degrees to the right.", '
    '"type": "sensor", "unit": "degrees"}'
)
new = (
    '"Angle": {"comment": "Upstream COVESA VSS 6.1 uses datatype int16. '
    "This catalog uses float so fractional degree signals, such as a 0.1 deg "
    'CAN factor, can be published without rounding.", "datatype": "float", '
    '"description": "Steering wheel angle. Positive = degrees to the left. '
    'Negative = degrees to the right.", "type": "sensor", "unit": "degrees"}'
)
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected one upstream SteeringWheel.Angle node, found {count}")
text = text.replace(old, new, 1)
# Local additions beside IsWindowChildLockEngaged. See catalog/README.md.
# Upstream VSS 6.1 has IsLocked only on each door and IsBelted only on each seat.
child_lock = '"IsWindowChildLockEngaged":'
leaves = (
    '"IsCentralLockEngaged": {"comment": "Not in upstream COVESA VSS 6.1. '
    "One command that locks or unlocks every cabin door binds here. Per-door lock "
    'state remains on each door\'s IsLocked actuator.", "datatype": "boolean", '
    '"description": "Is central lock engaged. True = Engaged. False = Disengaged.", '
    '"type": "actuator"}, "IsSeatBeltWarningActive": {"comment": "Not in upstream '
    "COVESA VSS 6.1. The vehicle seatbelt warning indicator binds here. Per-seat "
    'buckle state remains on each seat\'s IsBelted sensor.", "datatype": "boolean", '
    '"description": "Is the vehicle seatbelt warning indicator active. '
    'True = Active. False = Inactive.", "type": "sensor"}, '
    '"IsWindowChildLockEngaged":'
)
count = text.count(child_lock)
if count != 1:
    raise SystemExit(f"expected one Cabin child-lock signal, found {count}")
path.write_text(text.replace(child_lock, leaves, 1))
PY
# Vehicle.OBD comes from the v6.1 OBD overlay. The standard catalog export omits it.
python3 - "$task_tmp/overlays/extensions/OBD/OBD.vspec" catalog/vss-6.1.json <<'PY'
import copy
import json
import re
import sys
from pathlib import Path

def parse_scalar(text):
    text = text.strip()
    if text in ("true", "false"):
        return text == "true"
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        return parse_flow(text[1:-1])
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text

def parse_flow(text):
    items, buf, quote = [], "", None
    for char in text:
        if quote:
            buf += char
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            buf += char
        elif char == ",":
            if buf.strip():
                items.append(parse_scalar(buf))
            buf = ""
        else:
            buf += char
    if buf.strip():
        items.append(parse_scalar(buf))
    return items

def parse_vspec(text):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))

    def parse_block(index, indent):
        node = {}
        while index < len(lines) and lines[index][0] >= indent:
            cur, line = lines[index]
            if cur > indent:
                raise SystemExit(f"unexpected indent: {line}")
            key, _, value = line.partition(":")
            value = value.strip()
            index += 1
            if value:
                node[key] = parse_scalar(value)
                continue
            if index < len(lines) and lines[index][0] > cur and lines[index][1].startswith("- "):
                child_indent = lines[index][0]
                items = []
                while (
                    index < len(lines)
                    and lines[index][0] == child_indent
                    and lines[index][1].startswith("- ")
                ):
                    items.append(parse_scalar(lines[index][1][2:]))
                    index += 1
                node[key] = items
                continue
            child, index = parse_block(index, cur + 2)
            node[key] = child
        return node, index

    tree, index = parse_block(0, 0)
    if index != len(lines):
        raise SystemExit(f"unparsed overlay line: {lines[index][1]}")
    return tree

def build(flat):
    obd = {"type": "branch", "description": "OBD data.", "children": {}}

    def branch(parent, name):
        node = parent["children"].get(name)
        if node is None:
            node = {"type": "branch", "children": {}}
            parent["children"][name] = node
        elif node.get("type") != "branch":
            raise SystemExit(f"{name} is not a branch")
        node.setdefault("children", {})
        return node

    for key, spec in flat.items():
        node = obd
        parts = key.split(".")
        for part in parts[:-1]:
            node = branch(node, part)
        name = parts[-1]
        if spec.get("type") == "branch":
            existing = branch(node, name)
            existing.update(spec)
        elif name in node["children"]:
            raise SystemExit(f"duplicate OBD signal {key}")
        else:
            node["children"][name] = dict(spec)
    return obd

def expand(node):
    for child in list(node.get("children", {}).values()):
        if child.get("type") == "branch":
            expand(child)
    specs = node.get("instances")
    if not specs:
        return
    names = []
    for spec in specs:
        match = re.fullmatch(r"([A-Za-z]+)\[(\d+),(\d+)\]", spec)
        if not match:
            raise SystemExit(f"unsupported instance {spec}")
        prefix, start, end = match.group(1), int(match.group(2)), int(match.group(3))
        names.extend(f"{prefix}{i}" for i in range(start, end + 1))
    signals = node.pop("children")
    node.pop("instances")
    node["children"] = {
        name: {
            "children": copy.deepcopy(signals),
            "description": node["description"],
            "type": "branch",
        }
        for name in names
    }

def order(node):
    if node.get("type") == "branch":
        result = {"children": {key: order(value) for key, value in node["children"].items()}}
        if "comment" in node:
            result["comment"] = node["comment"]
        result["description"] = node["description"]
        result["type"] = "branch"
        return result
    result = {}
    if "allowed" in node:
        result["allowed"] = node["allowed"]
    result["datatype"] = node["datatype"]
    result["description"] = node["description"]
    if "max" in node:
        result["max"] = node["max"]
    if "min" in node:
        result["min"] = node["min"]
    result["type"] = node["type"]
    if "unit" in node:
        result["unit"] = node["unit"]
    return result

overlay_path, catalog_path = sys.argv[1:]
obd = build(parse_vspec(Path(overlay_path).read_text()))
expand(obd)
obd["comment"] = (
    "Included from the COVESA OBD overlay. Upstream VSS 6.1 does not contain Vehicle.OBD."
)
catalog = json.loads(Path(catalog_path).read_text())
children = catalog["Vehicle"]["children"]
if "OBD" in children:
    raise SystemExit("Vehicle.OBD already present in the standard export")
children["OBD"] = order(obd)
Path(catalog_path).write_text(json.dumps(catalog))
PY
