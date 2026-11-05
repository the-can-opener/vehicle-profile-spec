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
path.write_text(text.replace(old, new, 1))
PY
