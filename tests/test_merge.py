import pytest
from conftest import base, signal
from vehicle_profile_tools.errors import ProfileError
from vehicle_profile_tools.resolve import resolve


def test_overlay_and_null(package):
    data = base()
    channels = data.pop("channels")
    endpoints = data.pop("endpoints")
    data["applies_to"] = {"years": [{"range": [2007, 2012]}]}
    data["documents"] = [
        {"path": "base.json"},
        {"path": "2011.json", "applies_to": {"years": [2011]}},
    ]
    root = package(
        data,
        files={
            "base.json": {
                "channels": channels,
                "endpoints": endpoints,
                "properties": {"Vehicle.Speed": signal()},
            },
            "2011.json": {"properties": {"Vehicle.Speed": None}},
        },
    )
    assert "Vehicle.Speed" in resolve([root], {"year": 2008})["properties"]
    assert not resolve([root], {"year": 2011})["properties"]


def test_widened(package):
    data = base()
    data.pop("channels")
    data.pop("endpoints")
    data["applies_to"] = {"years": [2011]}
    data["documents"] = [{"path": "a.json", "applies_to": {"years": [2012]}}]
    with pytest.raises(ProfileError, match="APPLICABILITY_WIDENED"):
        resolve([package(data, files={"a.json": {}})])


def test_cross_package_override_and_dependencies(package):
    a = package({**base(), "properties": {"Vehicle.Speed": signal()}}, "a")
    b = base()
    b.pop("channels")
    b.pop("endpoints")
    b.update(
        id="org.test.overlay",
        depends=[{"id": "org.test.base", "version": "^1.0.0"}],
        documents=[{"path": "overlay.json"}],
    )
    overlay = {"properties": {"Vehicle.Speed": signal()}}
    path = package(b, "b", {"overlay.json": overlay})
    with pytest.raises(ProfileError, match="DEP_UNSATISFIED"):
        resolve([path])
    with pytest.raises(ProfileError, match="MERGE_CONFLICT"):
        resolve([a, path])
    b["documents"][0]["override"] = True
    path = package(b, "b", {"overlay.json": overlay})
    assert resolve([a, path])["properties"]["Vehicle.Speed"]


def test_sequence_override_after_merge(package):
    data = base()
    channels, endpoints = data.pop("channels"), data.pop("endpoints")
    data["documents"] = [{"path": "a.json"}, {"path": "b.json"}]
    a = {
        "channels": channels,
        "endpoints": endpoints,
        "sequences": {"setup": {"steps": [{"call": "missing"}]}},
        "actions": {
            "TEST": {"description": "test", "endpoint": "ecu", "steps": [{"call": "setup"}]}
        },
    }
    b = {"sequences": {"setup": {"steps": [{"request": "01"}]}}}
    assert resolve([package(data, files={"a.json": a, "b.json": b})])["sequences"] == b["sequences"]
