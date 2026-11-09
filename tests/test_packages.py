import json
import zipfile

import pytest
from click.testing import CliRunner
from conftest import ROOT, base, signal
from vehicle_profile_tools.cli import cli
from vehicle_profile_tools.compose import compose
from vehicle_profile_tools.errors import ProfileError
from vehicle_profile_tools.resolve import resolve


@pytest.mark.parametrize(
    "name",
    ["nissan-versa", "universal-obd", "hvac-synthetic", "canfd-dual-bus", "bmw-addressing"],
)
def test_examples(name):
    result = resolve([ROOT / "examples" / name])
    assert result["format"] == 2
    assert result["properties"]


def test_single_and_query(package):
    data = base()
    data["properties"] = {"Vehicle.Speed": signal()}
    data["properties"]["Vehicle.Speed"]["read"]["query"] = {
        "endpoint": "ecu",
        "request": "01 0D",
        "response": {"prefix": "41 0D"},
        "decode": {"byte": 0, "bytes": 1, "type": "uint"},
    }
    result = resolve([package(data)])
    assert set(result["properties"]["Vehicle.Speed"]["read"]) == {"signal", "query"}


@pytest.mark.parametrize(
    "write",
    [
        {"endpoint": "ecu", "request": "01"},
        {
            "endpoint": "ecu",
            "deadline_ms": 1000,
            "steps": [{"request": "01", "expect": {"prefix": "02"}}],
        },
        {"cases": {"true": {"endpoint": "ecu", "request": "01"}}},
    ],
)
def test_write_shapes(package, write):
    data = base()
    data["properties"] = {"Vehicle.Body.Horn.IsActive": {"write": write}}
    assert "write" in resolve([package(data)])["properties"]["Vehicle.Body.Horn.IsActive"]


def _can_package():
    data = base()
    data["endpoints"]["lamps"] = {
        "channel": "bus",
        "protocol": "can",
        "tx": "35D",
        "id_format": "standard",
    }
    data["actions"] = {
        "SIGNAL_OFF": {
            "description": "Turn off both direction indicators.",
            "endpoint": "ecu",
            "request": "30 2F 00 00",
            "expect": {"prefix": "70 2F"},
        }
    }
    return data


def test_duration_release_and_masked_repeat(package):
    from vehicle_profile_tools.codec import prepare_write

    data = _can_package()
    data["properties"] = {
        "Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling": {
            "write": {
                "cases": {
                    "true": {
                        "endpoint": "ecu",
                        "deadline_ms": 1000,
                        "steps": [{"request": "30 2F 00 02", "expect": {"prefix": "70 2F"}}],
                        "duration": 5000,
                        "release": {"action": "SIGNAL_OFF"},
                    }
                }
            }
        },
        "Vehicle.Body.Lights.Hazard.IsSignaling": {
            "write": {
                "endpoint": "lamps",
                "repeat": {
                    "interval_ms": 100,
                    "release": "silence",
                    "frame": {
                        "base": "last-rx",
                        "mask": "00 00 0F 00 00 00 00 00",
                        "patch": "00 00 01 00 00 00 00 00",
                    },
                },
            }
        },
        "Vehicle.Body.Windshield.Front.Wiping.Mode": {
            "write": {
                "cases": {
                    "MEDIUM": {
                        "endpoint": "lamps",
                        "repeat": {
                            "interval_ms": 100,
                            "release": "silence",
                            "frame": {
                                "base": "last-rx",
                                "mask": "00 00 F0 00 00 00 00 00",
                                "patch": "00 00 40 00 00 00 00 00",
                            },
                        },
                    }
                }
            }
        },
    }
    result = resolve([package(data)])
    prepared = prepare_write(result, "Vehicle.Body.Windshield.Front.Wiping.Mode", "MEDIUM")
    assert prepared["steps"] == []
    assert prepared["repeat"]["interval_ms"] == 100
    assert prepared["repeat"]["release"] == "silence"


@pytest.mark.parametrize(
    "mutate,code",
    [
        (
            lambda data: data["properties"][
                "Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling"
            ]["write"]["cases"]["true"].__setitem__("release", {"action": "MISSING"}),
            "REF_UNKNOWN_ACTION",
        ),
        (
            lambda data: data["properties"].__setitem__(
                "Vehicle.Body.Horn.IsActive",
                {
                    "write": {
                        "endpoint": "ecu",
                        "repeat": {
                            "interval_ms": 100,
                            "release": "silence",
                            "frame": {
                                "base": "last-rx",
                                "mask": "FF",
                                "patch": "01",
                            },
                        },
                    }
                },
            ),
            "DOC_INVALID",
        ),
        (
            lambda data: data["properties"].__setitem__(
                "Vehicle.Body.Lights.Hazard.IsSignaling",
                {
                    "write": {
                        "endpoint": "lamps",
                        "repeat": {
                            "interval_ms": 100,
                            "release": "silence",
                            "frame": {
                                "base": "last-rx",
                                "mask": "00 00 F0 00 00 00 00 00",
                                "patch": "00 00 10 00 00 00 00 00",
                            },
                        },
                    }
                },
            ),
            "DOC_INVALID",
        ),
    ],
)
def test_repeat_and_release_rejection(package, mutate, code):
    data = _can_package()
    data["properties"] = {
        "Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling": {
            "write": {
                "cases": {
                    "true": {
                        "endpoint": "ecu",
                        "request": "30 2F 00 02",
                        "expect": {"prefix": "70 2F"},
                        "duration": 5000,
                        "release": {"action": "SIGNAL_OFF"},
                    }
                }
            }
        },
        "Vehicle.Body.Windshield.Front.Wiping.Mode": {
            "write": {
                "cases": {
                    "MEDIUM": {
                        "endpoint": "lamps",
                        "repeat": {
                            "interval_ms": 100,
                            "release": "silence",
                            "frame": {
                                "base": "last-rx",
                                "mask": "00 00 F0 00 00 00 00 00",
                                "patch": "00 00 40 00 00 00 00 00",
                            },
                        },
                    }
                }
            }
        },
    }
    mutate(data)
    with pytest.raises(ProfileError, match=code):
        resolve([package(data, folder=code)])


def test_duration_excludes_repeat(package):
    data = _can_package()
    data["properties"] = {
        "Vehicle.Body.Horn.IsActive": {
            "write": {
                "endpoint": "lamps",
                "steps": [{"request": "01"}],
                "duration": 5000,
                "repeat": {
                    "interval_ms": 100,
                    "release": "silence",
                    "frame": {"base": "last-rx", "mask": "FF", "patch": "01"},
                },
            }
        }
    }
    with pytest.raises(ProfileError, match="DOC_EXCLUSIVE_FORMS"):
        resolve([package(data)])


def test_latched_duration(package):
    data = base()
    data["properties"] = {
        "Vehicle.Cabin.IsCentralLockEngaged": {
            "write": {
                "cases": {"true": {"endpoint": "ecu", "request": "01", "duration": "latched"}}
            }
        }
    }
    result = resolve([package(data)])
    case = result["properties"]["Vehicle.Cabin.IsCentralLockEngaged"]["write"]["cases"]["true"]
    assert case["duration"] == "latched"
    data["properties"]["Vehicle.Cabin.IsCentralLockEngaged"]["write"]["cases"]["true"][
        "duration"
    ] = 0
    with pytest.raises(ProfileError):
        resolve([package(data, folder="zero-duration")])


@pytest.mark.parametrize(
    "change,code,key",
    [
        (
            {"properties": {"Vehicle.Speed": {"write": {"endpoint": "ecu", "request": "01"}}}},
            "VSS_ROLE_MISMATCH",
            "Vehicle.Speed",
        ),
        ({"properties": {"Vehicle.BadPath": signal()}}, "VSS_UNKNOWN_PATH", "Vehicle.BadPath"),
        (
            {"properties": {"Vehicle.Speed": {"value": 1, **signal()}}},
            "DOC_EXCLUSIVE_FORMS",
            "Vehicle.Speed",
        ),
        (
            {
                "properties": {
                    "Vehicle.Speed": {"read": {"query": {"source": "missing", "output": "v"}}}
                }
            },
            "REF_UNKNOWN_SOURCE",
            "Vehicle.Speed",
        ),
        ({"sequences": {"a": {"steps": [{"call": "a"}]}}}, "REF_CYCLE", "sequences.a"),
        ({"extensions": {"org.test.x": {}}}, "EXT_NOT_REQUIRED", "org.test.x"),
        ({"requires": {"org.test.x": "1.0.0"}}, "EXT_UNSUPPORTED", "org.test.x"),
        (
            {
                "properties": {
                    "Vehicle.Body.Horn.IsActive": {
                        "write": {"cases": {"TRUE": {"endpoint": "ecu", "request": "01"}}}
                    }
                }
            },
            "VSS_ENUM_VALUE",
            "Vehicle.Body.Horn.IsActive",
        ),
        (
            {
                "properties": {
                    "Vehicle.Speed": {
                        "read": {
                            "query": {
                                "endpoint": "nope",
                                "request": "01",
                                "response": {"prefix": "02"},
                                "decode": {"byte": 0, "bytes": 1, "type": "uint"},
                            }
                        }
                    }
                }
            },
            "REF_UNKNOWN_ENDPOINT",
            "Vehicle.Speed",
        ),
    ],
)
def test_negative(package, change, code, key):
    data = {**base(), **change}
    path = package(data)
    with pytest.raises(ProfileError) as exc:
        resolve([path])
    assert exc.value.code == code
    assert key in str(exc.value)
    result = CliRunner().invoke(cli, ["export", "json", "--strict", "--package", str(path)])
    assert result.exit_code != 0


def test_source_kind(package):
    data = base()
    data["sources"] = {
        "a": {
            "kind": "signal",
            "channel": "bus",
            "id": "123",
            "id_format": "standard",
            "length": 1,
            "outputs": {"v": {"byte": 0, "bytes": 1, "type": "uint"}},
        }
    }
    data["properties"] = {"Vehicle.Speed": {"read": {"query": {"source": "a", "output": "v"}}}}
    with pytest.raises(ProfileError, match="REF_SOURCE_KIND"):
        resolve([package(data)])


def test_zip_roundtrip(package, tmp_path):
    root = package({**base(), "properties": {"Vehicle.Speed": signal()}})
    output = tmp_path / "out.zip"
    expected = resolve([root])
    assert compose(root, output) == expected
    first = output.read_bytes()
    compose(root, output)
    assert output.read_bytes() == first


@pytest.mark.parametrize("name", ["../evil", "/evil", "a/../evil", "a\\evil"])
def test_zip_unsafe(tmp_path, name):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(name, "{}")
    with pytest.raises(ProfileError, match="PKG_UNSAFE_PATH"):
        resolve([path])


def test_zip_duplicate(tmp_path):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("vehicle.json", json.dumps(base()))
        z.writestr("VEHICLE.JSON", "{}")
    with pytest.raises(ProfileError, match="PKG_UNSAFE_PATH"):
        resolve([path])


def test_legacy():
    with pytest.raises(ProfileError, match="DOC_LEGACY_FORMAT"):
        resolve([ROOT / "examples/legacy/nissan-versa"])


def test_unknown_field(package):
    data = {**base(), "properties": {"Vehicle.Speed": {**signal(), "typo": True}}}
    path = package(data)
    with pytest.raises(ProfileError, match="DOC_UNKNOWN_FIELD"):
        resolve([path])
    assert resolve([path], strict=False)


def test_alias_collision(package):
    data = base()
    data["properties"] = {"Vehicle.Speed": {**signal(), "aliases": ["Vehicle.Speed"]}}
    with pytest.raises(ProfileError, match="ALIAS_COLLISION"):
        resolve([package(data)])


def test_fixture_unknown(package):
    data = {**base(), "fixtures": ["fixture.json"]}
    root = package(
        data,
        files={
            "fixture.json": {
                "fixture": 1,
                "cases": [{"kind": "action", "name": "NOPE", "expect": {"result": "sent"}}],
            }
        },
    )
    with pytest.raises(ProfileError, match="FIXTURE_INVALID"):
        resolve([root])


def test_single_actuator_cannot_be_action(package):
    data = {
        **base(),
        "actions": {"HORN": {"description": "Horn", "endpoint": "ecu", "request": "01"}},
    }
    with pytest.raises(ProfileError, match="VSS_ROLE_MISMATCH"):
        resolve([package(data)])


def test_encoded_input_declared(package):
    data = {
        **base(),
        "actions": {
            "TEST": {
                "description": "Test",
                "endpoint": "ecu",
                "request": {"parts": [{"input": "missing", "type": "uint", "bytes": 1}]},
            }
        },
    }
    with pytest.raises(ProfileError, match="undeclared encoded input"):
        resolve([package(data)])


def test_decoder_frame_bounds(package):
    prop = signal()
    prop["read"]["signal"]["decode"]["bytes"] = 2
    with pytest.raises(ProfileError, match="decoder exceeds"):
        resolve([package({**base(), "properties": {"Vehicle.Speed": prop}})])


def test_diff_and_compose_cli(package, tmp_path):
    import subprocess
    import sys

    a = package(base(), "a")
    b = package({**base(), "properties": {"Vehicle.Speed": signal()}}, "b")
    prefix = [sys.executable, "-m", "vehicle_profile_tools.cli"]
    result = subprocess.run([*prefix, "diff", str(a), str(b)], capture_output=True, check=True)
    assert json.loads(result.stdout)["properties"]["added"] == ["Vehicle.Speed"]
    archive = tmp_path / "package.zip"
    subprocess.run(
        [*prefix, "compose", "--package", str(b), "-o", str(archive)],
        check=True,
        capture_output=True,
    )
    subprocess.run([*prefix, "compose", "--verify", str(archive)], check=True, capture_output=True)
    assert resolve([archive]) == resolve([b])
