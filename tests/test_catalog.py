import pytest
from conftest import base, signal
from vehicle_profile_tools.catalog import check_value, load_catalog
from vehicle_profile_tools.errors import ProfileError
from vehicle_profile_tools.resolve import resolve


def test_pinned_full_catalog():
    cat = load_catalog()
    assert len(cat) > 1300
    assert cat["Vehicle.Speed"]["unit"] == "km/h"
    assert cat["Vehicle.Body.Horn.IsActive"]["type"] == "actuator"
    door_lock = cat["Vehicle.Cabin.Door.IsLocked"]
    assert door_lock["type"] == "actuator" and door_lock["datatype"] == "boolean"
    assert cat["Vehicle.Cabin.Door.Row1.DriverSide.IsLocked"]["type"] == "actuator"
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
