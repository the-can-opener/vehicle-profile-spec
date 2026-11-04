import json
import subprocess
import sys

import pytest
from conftest import base, signal
from vehicle_profile_tools.errors import ProfileError
from vehicle_profile_tools.resolve import resolve
from vehicle_profile_tools.strict import StrictOption, parse


def test_exact_unknown_field_exception(package, tmp_path):
    data = {**base(), "properties": {"Vehicle.Speed": {**signal(), "vendor_note": "draft"}}}
    path = package(data)
    exception_file = tmp_path / "exceptions.json"
    pointer = "/properties/Vehicle.Speed/vendor_note"
    exception_file.write_text(json.dumps([{"path": pointer, "reason": "vendor annotation"}]))
    policy = StrictOption.from_file(True, exception_file)
    result = resolve([path], strict=policy)
    assert "vendor_note" not in result["properties"]["Vehicle.Speed"]
    assert policy.ignored == {pointer}
    log = tmp_path / "log.txt"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "vehicle_profile_tools.cli",
            "export",
            "json",
            "--package",
            str(path),
            "--strict",
            "--strict-exceptions",
            str(exception_file),
            "--log-file",
            str(log),
        ],
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert pointer in log.read_text() and b"excepted" in proc.stderr


def test_exception_cannot_remove_core_binding(package):
    data = {
        **base(),
        "properties": {"Vehicle.Speed": {"write": {"endpoint": "ecu", "request": "01"}}},
    }
    policy = StrictOption(True, {"/properties/Vehicle.Speed/write": "cannot silence role errors"})
    with pytest.raises(ProfileError, match="VSS_ROLE_MISMATCH"):
        resolve([package(data)], strict=policy)
    assert not policy.ignored


def test_exception_cannot_remove_other_union_form(package):
    data = {
        **base(),
        "properties": {
            "Vehicle.Body.Horn.IsActive": {
                "write": {
                    "endpoint": "ecu",
                    "request": "01",
                    "cases": {"true": {"endpoint": "ecu", "request": "02"}},
                }
            }
        },
    }
    policy = StrictOption(
        True, {"/properties/Vehicle.Body.Horn.IsActive/write/cases": "not an unknown field"}
    )
    with pytest.raises(ProfileError):
        resolve([package(data)], strict=policy)


def test_unknown_vehicle_selector_rejected(package):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "vehicle_profile_tools.cli",
            "resolve",
            "--packages",
            str(package()),
            "--vehicle",
            "yaer=2011",
        ],
        capture_output=True,
    )
    assert proc.returncode != 0


@pytest.mark.parametrize("text", ['{"x":1e999}', '{"x":-1e999}'])
def test_json_overflow_rejected(text):
    with pytest.raises(ProfileError, match="DOC_INVALID"):
        parse(text, "x.json")
