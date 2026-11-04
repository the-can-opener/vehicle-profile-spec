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
