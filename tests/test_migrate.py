from conftest import ROOT
from vehicle_profile_tools.migrate import migrate
from vehicle_profile_tools.resolve import resolve


def test_migrate(tmp_path):
    old = ROOT / "examples/legacy/nissan-versa-1-6"
    new = tmp_path / "converted"
    report = migrate(old, new)
    result = resolve([new])
    assert "Vehicle.Speed" in result["properties"]
    assert result["actions"]["ECU_WAKE"]["steps"][0]["request"] == "00 00 00 00 00 00 00 00"
    wipers = result["properties"]["Vehicle.Body.Windshield.Front.Wiping.Mode"]
    assert wipers["aliases"] == ["WIPERS"]
    assert wipers["write"]["cases"]["MEDIUM"]["request"] == "C1 03 40 00 00 00 00 00"
    assert "WIPERS" not in result["actions"]
    assert (new / "signals.dbc").read_bytes() == (old / "signals.dbc").read_bytes()
    lock = next(x for x in report if x["capability"] == "LOCK")
    assert "original" in lock and "--framing" in lock["reason"]
    assert "Vehicle.Cabin.Door.Row1.DriverSide.IsLocked" not in result["properties"]


def test_versa_request_response_migration(tmp_path):
    from vehicle_profile_tools.codec import matches, prepare_write

    old = ROOT / "examples/legacy/nissan-versa-1-6"
    new = tmp_path / "converted"
    report = migrate(old, new, framing="isotp-single-frame", steering_side="left")
    result = resolve([new])
    assert result["endpoints"]["body"]["protocol"] == "isotp"
    horn = prepare_write(result, "Vehicle.Body.Horn.IsActive", True)
    assert [s["request"] for s in horn["steps"]] == ["10 81", "10 C0", "30 30 00 01"]
    lock = prepare_write(result, "Vehicle.Cabin.Door.Central.IsLocked", True)
    assert [step["request"] for step in lock["steps"]] == ["10 81", "10 C0", "30 38 00 01"]
    assert matches(lock["steps"][-1]["expect"], "70 38 FF")
    unlock = prepare_write(result, "Vehicle.Cabin.Door.Central.IsLocked", False)
    assert unlock["steps"][-1]["request"] == "30 38 00 02"
    assert result["properties"]["Vehicle.Cabin.Door.Central.IsLocked"]["aliases"] == ["LOCK", "UNLOCK"]
    assert "Vehicle.Cabin.Door.Row1.DriverSide.IsLocked" not in result["properties"]
    assert "LOCK" not in result["actions"] and "UNLOCK" not in result["actions"]
    assert "HORN" not in result["actions"]
    assert "WIPERS" not in result["actions"]
    wipers = result["properties"]["Vehicle.Body.Windshield.Front.Wiping.Mode"]
    assert wipers["aliases"] == ["WIPERS"]
    assert wipers["write"]["cases"]["MEDIUM"]["request"] == "C1 03 40 00 00 00 00 00"
    assert result["properties"]["Vehicle.Body.Lights.Beam.Low.IsOn"]["read"]
    assert result["properties"]["Vehicle.Body.Lights.Beam.Low.IsOn"]["write"]
    assert "Vehicle.Cabin.Door.Row1.DriverSide.IsOpen" in result["properties"]
    assert not {"HORN", "LOCK", "UNLOCK", "RPM", "BRAKE_LIGHTS"} & {r["capability"] for r in report}
    assert (new / "signals.dbc").read_bytes() == (old / "signals.dbc").read_bytes()


def test_raw_request_and_exact_wildcard_preserved(tmp_path):
    import yaml

    old = tmp_path / "old"
    old.mkdir()
    data = {
        "version": 1,
        "endpoints": {"ecu": {"request_id": 0x700, "response_id": 0x708}},
        "actions": {
            "LOCK": {
                "endpoint": "ecu",
                "send": [1, 2],
                "expect": {"pattern": [3, "*"], "exact": True},
            }
        },
    }
    (old / "profile.yaml").write_text(yaml.safe_dump(data))
    new = tmp_path / "new"
    assert migrate(old, new, framing="raw") == []
    doc = resolve([new])
    assert doc["endpoints"]["ecu"]["protocol"] == "can"
    lock = doc["properties"]["Vehicle.Cabin.Door.Central.IsLocked"]["write"]["cases"]["true"]
    assert lock["request"] == "01 02"
    assert lock["expect"] == {"prefix": "03 *", "exact": True}
    assert "LOCK" not in doc.get("actions", {})


def test_queries_share_property_and_translate_dbc_offsets(tmp_path):
    import yaml
    from vehicle_profile_tools.codec import decode

    old = tmp_path / "old"
    old.mkdir()
    (old / "signals.dbc").write_text("""BO_ 100 Broadcast: 1 ECU
 SG_ Speed : 0|8@1+ (1,0) [0|255] "km/h" ECU
BO_ 1800 Response: 8 ECU
 SG_ Speed : 24|8@1+ (1,0) [0|255] "km/h" ECU
 SG_ RPM : 31|16@0+ (0.25,0) [0|16383.75] "rpm" ECU
""")
    data = {
        "version": 1,
        "dbc": {"files": [{"path": "signals.dbc"}]},
        "endpoints": {"ecu": {"request_id": 0x700, "response_ids": [{"range": [0x708, 0x70F]}]}},
        "signals": {"SPEED": {"monitor": {"message": "Broadcast", "signal": "Speed"}}},
        "queries": {
            "SPEED": {
                "endpoint": "ecu",
                "send": [2, 1, 13, 0, 0, 0, 0, 0],
                "expect": [0x41, 13],
                "dbc_mapping": {"message": "Response", "signal": "Speed"},
            },
            "RPM": {
                "endpoint": "ecu",
                "send": [2, 1, 12, 0, 0, 0, 0, 0],
                "expect": [0x41, 12],
                "dbc_mapping": {"message": "Response", "signal": "RPM"},
            },
            "VIN": {
                "endpoint": "ecu",
                "send": [2, 9, 2, 0, 0, 0, 0, 0],
                "expect": [0x49, 2, 1],
                "decoder": "ascii",
                "length": 17,
            },
            "SUPPORTED_PIDS_01_20": {
                "endpoint": "ecu",
                "send": [2, 1, 0, 0, 0, 0, 0, 0],
                "expect": [0x41, 0],
                "decoder": {"type": "bytes", "length": 4},
            },
        },
    }
    (old / "profile.yaml").write_text(yaml.safe_dump(data))
    new = tmp_path / "new"
    assert migrate(old, new, framing="isotp-single-frame", responders={"ecu": "708"}) == []
    result = resolve([new])
    prop = result["properties"]["Vehicle.Speed"]
    assert prop["aliases"] == ["SPEED"]
    assert set(prop["read"]) == {"signal", "query"}
    assert prop["read"]["query"]["request"] == "01 0D"
    assert decode("32", prop["read"]["query"]["decode"]) == 50
    rpm = result["properties"]["Vehicle.Powertrain.CombustionEngine.Speed"]["read"]["query"]
    assert decode("1F 40", rpm["decode"]) == 2000
    assert result["queries"]["SUPPORTED_PIDS_01_20"]["decode"]["type"] == "hex"
    assert (
        result["properties"]["Vehicle.VehicleIdentification.VIN"]["read"]["query"]["decode"][
            "bytes"
        ]
        == 17
    )
    assert result["endpoints"]["ecu"]["responder"] == "708"


def test_endpoint_switch_and_cycle_are_reported(tmp_path):
    import yaml

    old = tmp_path / "old"
    old.mkdir()
    data = {
        "version": 1,
        "endpoints": {"ecu": {"request_id": 0x700}, "other": {"request_id": 0x701}},
        "sequences": {
            "cycle": {"steps": [{"ref": "sequences.cycle"}]},
            "switch": {"endpoint": "other", "steps": [{"send": [1]}]},
        },
        "actions": {
            "CYCLE": {"endpoint": "ecu", "steps": [{"ref": "sequences.cycle"}]},
            "SWITCH": {"endpoint": "ecu", "steps": [{"ref": "sequences.switch"}]},
        },
    }
    (old / "profile.yaml").write_text(yaml.safe_dump(data))
    report = migrate(old, tmp_path / "new", framing="raw")
    reasons = {r["capability"]: r["reason"] for r in report}
    assert "cycle" in reasons["CYCLE"]
    assert "changes endpoint" in reasons["SWITCH"]
    assert not resolve([tmp_path / "new"]).get("actions")


def test_checked_in_versa_is_reproducible():
    import subprocess
    import sys

    subprocess.run([sys.executable, str(ROOT / "scripts/migrate-versa.py"), "--check"], check=True)
