import json
import subprocess
import sys

import pytest
from conftest import ROOT


def scenarios():
    for directory in sorted((ROOT / "tests/packages").iterdir()):
        config = directory / "scenario.json"
        runs = (
            json.loads(config.read_text())
            if config.exists()
            else [{"packages": ["."], "vehicle": {}, "expected": "expected.json"}]
        )
        for run in runs:
            yield pytest.param(directory, run, id=directory.name + "-" + run["expected"])


@pytest.mark.parametrize("directory,run", list(scenarios()))
def test_golden_export(directory, run):
    paths = [directory / path for path in run["packages"]]
    command = [sys.executable, "-m", "vehicle_profile_tools.cli"]
    if len(paths) == 1:
        command += ["export", "json", "--package", str(paths[0])]
    else:
        command += ["resolve"]
        for path in paths:
            command += ["--packages", str(path)]
    command += ["--strict"]
    if run["vehicle"]:
        command += ["--vehicle", ",".join(f"{k}={v}" for k, v in run["vehicle"].items())]
    result = subprocess.run(command, capture_output=True, check=True)
    assert result.stdout == (directory / run["expected"]).read_bytes()


@pytest.mark.parametrize("format", ["tree", "csv", "jsonschema"])
def test_other_exports(format):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vehicle_profile_tools.cli",
            "export",
            format,
            "--strict",
            "--package",
            str(ROOT / "examples/universal-obd"),
        ],
        capture_output=True,
        check=True,
    )
    assert result.stdout
    if format == "jsonschema":
        schema = json.loads(result.stdout)
        assert schema["properties"]["Vehicle.Speed"]["type"] == "number"


def test_cli_error_log(tmp_path):
    log = tmp_path / "errors.log"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vehicle_profile_tools.cli",
            "export",
            "json",
            "--strict",
            "--package",
            str(ROOT / "examples/legacy/nissan-versa-1-6"),
            "--log-file",
            str(log),
        ],
        capture_output=True,
    )
    assert result.returncode == 1
    assert b"DOC_LEGACY_FORMAT" in result.stderr
    assert "DOC_LEGACY_FORMAT" in log.read_text()
    assert b"Traceback" not in result.stderr
