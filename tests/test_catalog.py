import json

import pytest
from conftest import base, signal
from vehicle_profile_tools.catalog import check_value, load_catalog
from vehicle_profile_tools.errors import ProfileError
from vehicle_profile_tools.exporters.jsonschema import export
from vehicle_profile_tools.resolve import resolve


def test_pinned_full_catalog():
    cat = load_catalog()
    assert len(cat) > 1300
    assert cat["Vehicle.Speed"]["unit"] == "km/h"
    assert cat["Vehicle.Body.Horn.IsActive"]["type"] == "actuator"
    assert "Vehicle.Cabin.Door.IsLocked" not in cat
    assert "Vehicle.Cabin.Door.Central.IsLocked" not in cat
    assert "Vehicle.Cabin.DoorLock.IsLocked" not in cat
    assert "Vehicle.Cabin.SeatBelt.IsWarning" not in cat
    door_lock = cat["Vehicle.Cabin.IsCentralLockEngaged"]
    assert door_lock["type"] == "actuator" and door_lock["datatype"] == "boolean"
    assert cat["Vehicle.Cabin.Door.Row1.DriverSide.IsLocked"]["type"] == "actuator"
    belt_warning = cat["Vehicle.Cabin.IsSeatBeltWarningActive"]
    assert belt_warning["type"] == "sensor" and belt_warning["datatype"] == "boolean"
    assert cat["Vehicle.Cabin.Seat.Row1.DriverSide.IsBelted"]["type"] == "sensor"
    clutch = cat["Vehicle.Chassis.Clutch.PedalPosition"]
    assert clutch["type"] == "sensor" and clutch["datatype"] == "uint8"
    assert clutch["unit"] == "percent" and clutch["min"] == 0 and clutch["max"] == 100
    assert cat["Vehicle.Chassis.Accelerator.PedalPosition"]["type"] == "sensor"
    assert cat["Vehicle.Chassis.Brake.PedalPosition"]["type"] == "sensor"
    assert cat["Vehicle.Powertrain.Transmission.ClutchEngagement"]["type"] == "actuator"
    assert cat["Vehicle.OBD.EngineLoad"]["unit"] == "percent"
    assert cat["Vehicle.OBD.O2.Sensor8.Voltage"]["unit"] == "V"
    assert cat["Vehicle.OBD.O2WR.Sensor1.Lambda"]["datatype"] == "float"
    with pytest.raises(ProfileError, match="VSS_UNSUPPORTED_RELEASE"):
        load_catalog("6.0")


def test_domain():
    with pytest.raises(ProfileError, match="VSS_ENUM_VALUE"):
        check_value(256, {"datatype": "uint8"}, "test")
    with pytest.raises(ProfileError):
        check_value(True, {"datatype": "int8"}, "test")


def test_unit_mismatch(package):
    data = base()
    p = signal()
    p["read"]["signal"]["decode"]["unit"] = "m/s"
    data["properties"] = {"Vehicle.Speed": p}
    with pytest.raises(ProfileError, match="VSS_UNIT_MISMATCH"):
        resolve([package(data)])


def test_widened_constraint(package):
    data = base()
    data["properties"] = {
        "Vehicle.Cabin.Door.Row1.DriverSide.Position": {
            "write": {"endpoint": "ecu", "request": "01", "constraints": {"max": 500}}
        }
    }
    with pytest.raises(ProfileError, match="VSS_CONSTRAINT_WIDENED"):
        resolve([package(data)])


def inline_signal(decode, length=1):
    return {
        "channel": "bus",
        "id": "1F9",
        "id_format": "standard",
        "length": length,
        "decode": decode,
    }


def test_read_constraints_narrow_unbounded_float(package):
    data = base()
    data["properties"] = {
        "Vehicle.Powertrain.CombustionEngine.Speed": {
            "aliases": ["RPM"],
            "read": {
                "signal": inline_signal(
                    {"byte": 0, "bytes": 2, "type": "uint", "scale": 0.25, "unit": "rpm"},
                    length=2,
                ),
                "constraints": {"min": 0, "max": 8000},
            },
        },
        "Vehicle.Chassis.Accelerator.PedalPosition": {
            "read": {
                "signal": inline_signal({"byte": 0, "bytes": 1, "type": "uint", "unit": "percent"}),
                "constraints": {"max": 80},
            }
        },
    }
    resolved = resolve([package(data)])
    speed = resolved["properties"]["Vehicle.Powertrain.CombustionEngine.Speed"]
    assert speed["read"]["constraints"] == {"min": 0.0, "max": 8000.0}
    schema = json.loads(export(resolved))
    assert schema["properties"]["Vehicle.Powertrain.CombustionEngine.Speed"]["minimum"] == 0
    assert schema["properties"]["Vehicle.Powertrain.CombustionEngine.Speed"]["maximum"] == 8000
    pedal = schema["properties"]["Vehicle.Chassis.Accelerator.PedalPosition"]
    assert pedal["minimum"] == 0
    assert pedal["maximum"] == 80


def test_widened_read_constraint(package):
    data = base()
    data["properties"] = {
        "Vehicle.Chassis.Accelerator.PedalPosition": {
            "read": {
                "signal": inline_signal({"byte": 0, "bytes": 1, "type": "uint", "unit": "percent"}),
                "constraints": {"max": 120},
            }
        }
    }
    with pytest.raises(ProfileError, match="VSS_CONSTRAINT_WIDENED"):
        resolve([package(data)])


def test_read_constraint_respects_integer_width(package):
    data = base()
    data["properties"] = {
        "Vehicle.Diagnostics.DTCCount": {
            "read": {
                "signal": inline_signal({"byte": 0, "bytes": 1, "type": "uint"}),
                "constraints": {"max": 300},
            }
        }
    }
    with pytest.raises(ProfileError, match="VSS_CONSTRAINT_WIDENED"):
        resolve([package(data)])


def test_read_constraints_require_numeric_scalar(package):
    data = base()
    data["properties"] = {
        "Vehicle.Body.Horn.IsActive": {
            "read": {
                "signal": inline_signal({"byte": 0, "bytes": 1, "type": "uint"}),
                "constraints": {"max": 1},
            }
        }
    }
    with pytest.raises(ProfileError, match="numeric constraints require a numeric scalar"):
        resolve([package(data)])
