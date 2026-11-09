from conftest import ROOT
from vehicle_profile_tools.migrate import migrate
from vehicle_profile_tools.resolve import resolve


def test_migrate(tmp_path):
    old = ROOT / "examples/legacy/nissan-versa"
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

    old = ROOT / "examples/legacy/nissan-versa"
    new = tmp_path / "converted"
    report = migrate(old, new, framing="isotp-single-frame", steering_side="left")
    result = resolve([new])
    assert result["endpoints"]["body"]["protocol"] == "isotp"
    horn = prepare_write(result, "Vehicle.Body.Horn.IsActive", True)
    assert [s["request"] for s in horn["steps"]] == ["10 81", "10 C0", "30 30 00 01"]
    lock = prepare_write(result, "Vehicle.Cabin.IsCentralLockEngaged", True)
    assert [step["request"] for step in lock["steps"]] == ["10 81", "10 C0", "30 38 00 01"]
    assert matches(lock["steps"][-1]["expect"], "70 38 FF")
    unlock = prepare_write(result, "Vehicle.Cabin.IsCentralLockEngaged", False)
    assert unlock["steps"][-1]["request"] == "30 38 00 02"
    assert result["properties"]["Vehicle.Cabin.IsCentralLockEngaged"]["aliases"] == [
        "LOCK",
        "UNLOCK",
    ]
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
    lock = doc["properties"]["Vehicle.Cabin.IsCentralLockEngaged"]["write"]["cases"]["true"]
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


def _legacy(tmp_path, data, dbc=None):
    import yaml

    old = tmp_path / "old"
    old.mkdir()
    (old / "profile.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    if dbc:
        (old / "signals.dbc").write_text(dbc)
    return old


def test_bmw_extended_addressing_migrates(tmp_path):
    # Mirrors can-opener-js tests/fixtures/vehicles/bmw/extended-addressing/profile.yaml.
    data = {
        "version": 1,
        "endpoints": {
            "dme": {
                "request_id": 0x6F1,
                "response_id": 0x612,
                "timeout_ms": 500,
                "addressing": {"mode": "extended", "target_address": 0x12, "source_address": 0xF1},
            }
        },
        "queries": {
            "VIN": {
                "endpoint": "dme",
                "send": [0x03, 0x22, 0xF1, 0x90, 0, 0, 0, 0],
                "expect": [0x62, 0xF1, 0x90],
                "decoder": "ascii",
                "length": 17,
            }
        },
        "actions": {
            "TESTER_PRESENT": {
                "endpoint": "dme",
                "send": [0x02, 0x3E, 0x00],
                "expect": [0x7E, 0x00],
            }
        },
    }
    report = migrate(_legacy(tmp_path, data), tmp_path / "new", framing="isotp-single-frame")
    assert report == []
    doc = resolve([tmp_path / "new"])
    dme = doc["endpoints"]["dme"]
    assert dme["channel"] == "can0"
    assert dme["addressing"] == {"mode": "extended", "target_address": "12", "source_address": "F1"}
    assert doc["channels"] == {"can0": {"protocol": "can", "configuration": "runtime"}}
    vin = doc["properties"]["Vehicle.VehicleIdentification.VIN"]["read"]["query"]
    assert vin["request"] == "22 F1 90"
    assert doc["actions"]["TESTER_PRESENT"]["request"] == "3E 00"


def test_addressing_on_raw_framing_stays_unmapped(tmp_path):
    data = {
        "version": 1,
        "endpoints": {
            "body": {
                "request_id": 0x7A0,
                "response_id": 0x7A8,
                "addressing": {"mode": "mixed", "address_extension": 0xA5},
            }
        },
        "actions": {"TESTER_PRESENT": {"endpoint": "body", "send": [0x02, 0x3E, 0x00]}},
    }
    report = migrate(_legacy(tmp_path, data), tmp_path / "new", framing="raw")
    assert "isotp" in report[0]["reason"]


def test_dual_bus_canfd_migrates(tmp_path):
    dbc = """BO_ 256 BODY: 8 ECU
 SG_ DRIVER_DOOR : 0|1@1+ (1,0) [0|1] "" ECU
BO_ 2024 OBD: 8 ECU
 SG_ SPEED : 24|8@1+ (1,0) [0|255] "km/h" ECU
"""
    data = {
        "version": 1,
        "dbc": {"files": [{"path": "signals.dbc"}]},
        "can": {
            "buses": {
                0: {"bitrate": 500000, "data_bitrate": 2000000, "fd": {"isotp": {"tx_dl": 64}}},
                1: {"bitrate": "auto"},
            }
        },
        "endpoints": {
            "obd": {"bus": 0, "request_id": 0x7DF, "response_ids": [{"range": [0x7E8, 0x7EF]}]},
            "bcm": {"bus": 0, "request_id": 0x7A0, "response_id": 0x7A8, "fd": {"tx_dl": 8}},
            "legacy": {"bus": 0, "request_id": 0x7B0, "response_id": 0x7B8, "fd": False},
            "body": {"bus": 1, "request_id": 0x745, "response_id": 0x765, "extended": False},
        },
        "signals": {
            "FRONT_LEFT_DOOR_OPEN": {
                "monitor": {"bus": 1, "message": "BODY", "signal": "DRIVER_DOOR"},
            }
        },
        "queries": {
            "SPEED": {
                "endpoint": "obd",
                "send": [2, 1, 13, 0, 0, 0, 0, 0],
                "expect": [0x41, 0x0D],
                "dbc_mapping": {"message": "OBD", "signal": "SPEED"},
            }
        },
        "actions": {
            "LEFT_SIGNAL": {"send": {"bus": 1, "request_id": 0x123, "request": [1, 0, 0, 0]}},
            "CHIME": {"send": {"bus": 0, "request_id": 0x3F1, "fd": False, "request": [1]}},
            "WAKE_UP": {
                "endpoint": "body",
                "batch": False,
                "steps": [{"send": [2, 0x3E, 0], "delay_ms": 50}, {"send": [2, 0x3E, 0]}],
            },
        },
    }
    report = migrate(
        _legacy(tmp_path, data, dbc),
        tmp_path / "new",
        framing="isotp-single-frame",
        responders={"obd": "7E8"},
        steering_side="left",
    )
    assert report == []
    doc = resolve([tmp_path / "new"])
    assert doc["channels"] == {
        "can0": {
            "protocol": "canfd",
            "bitrate": 500000,
            "data_bitrate": 2000000,
            "fd": {"tx_dl": 64},
        },
        "can1": {"protocol": "can", "bitrate": "auto"},
    }
    assert doc["endpoints"]["obd"]["rx"] == [{"range": ["7E8", "7EF"]}]
    assert doc["endpoints"]["obd"]["responder"] == "7E8"
    assert doc["endpoints"]["bcm"]["fd"] == {"tx_dl": 8}
    assert doc["endpoints"]["legacy"]["fd"] is False
    assert doc["endpoints"]["body"]["channel"] == "can1"
    assert doc["endpoints"]["generated-left_signal"]["channel"] == "can1"
    assert doc["endpoints"]["generated-chime"] == {
        "channel": "can0",
        "protocol": "can",
        "tx": "3F1",
        "id_format": "standard",
        "fd": False,
    }
    # The DBC's only monitored message is on bus 1, so the DBC binds there and stays DBC-backed.
    door = doc["properties"]["Vehicle.Cabin.Door.Row1.DriverSide.IsOpen"]["read"]["signal"]
    assert door["dbc"].endswith(":main") and "bus" not in door
    manifest = resolve([tmp_path / "new"])["packages"][0]
    assert manifest["id"].startswith("org.canopener.migrated.")
    assert doc["actions"]["WAKE_UP"]["steps"] == [
        {"request": "3E 00"},
        {"wait_ms": 50},
        {"request": "3E 00"},
    ]
    readme = (tmp_path / "new" / "README.md").read_text()
    assert "batch" in readme


def test_dbc_shared_across_buses_uses_inline_binding(tmp_path):
    dbc = """BO_ 256 BODY: 8 ECU
 SG_ DRIVER_DOOR : 0|1@1+ (1,0) [0|1] "" ECU
BO_ 257 BRAKE: 8 ECU
 SG_ BRAKE_ON : 0|1@1+ (1,0) [0|1] "" ECU
VAL_ 257 BRAKE_ON 0 "off" 1 "on";
"""
    data = {
        "version": 1,
        "dbc": {"files": ["signals.dbc"]},
        "signals": {
            "FRONT_LEFT_DOOR_OPEN": {
                "monitor": {"bus": 1, "message": "BODY", "signal": "DRIVER_DOOR"}
            },
            "BRAKE_LIGHTS": {"monitor": {"message": "BRAKE", "signal": "BRAKE_ON"}},
        },
    }
    assert migrate(_legacy(tmp_path, data, dbc), tmp_path / "new", steering_side="left") == []
    doc = resolve([tmp_path / "new"])
    door = doc["properties"]["Vehicle.Cabin.Door.Row1.DriverSide.IsOpen"]["read"]["signal"]
    assert door["channel"] == "can1" and door["id"] == "100"
    brake = doc["properties"]["Vehicle.Body.Lights.Brake.IsActive"]["read"]["signal"]
    assert "dbc" in brake
    assert set(doc["channels"]) == {"can0", "can1"}


def test_invalid_bus_and_step_timeout_are_reported(tmp_path):
    data = {
        "version": 1,
        "can": {"buses": {0: {"bitrate": 500000, "fd": {}}}},
        "endpoints": {"ecu": {"request_id": 0x700, "response_id": 0x708}},
        "actions": {
            "WAKE_UP": {"endpoint": "ecu", "steps": [{"send": [1], "timeout_ms": 50}]},
        },
    }
    report = migrate(_legacy(tmp_path, data), tmp_path / "new", framing="raw")
    reasons = {r["capability"]: r["reason"] for r in report}
    assert "timeout_ms" in reasons["WAKE_UP"]
    assert "can.buses.0" not in reasons
    doc = resolve([tmp_path / "new"])
    assert doc["channels"]["can0"] == {"protocol": "canfd", "bitrate": 500000, "fd": True}


def test_checked_in_versa_is_reproducible():
    import subprocess
    import sys

    subprocess.run([sys.executable, str(ROOT / "scripts/migrate-versa.py"), "--check"], check=True)
