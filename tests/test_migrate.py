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


BODY = {"body": {"request_id": 0x745, "response_id": 0x765, "timeout_ms": 300}}
SESSION = {"body_session": {"steps": [{"send": [2, 0x10, 0x81, 0, 0, 0, 0, 0], "expect": [0x50]}]}}


def test_version_1_1_values_become_write_cases(tmp_path):
    from vehicle_profile_tools.codec import prepare_write

    dbc = """BO_ 1549 BODY: 8 ECU
 SG_ LOCKED : 0|1@1+ (1,0) [0|1] "" ECU
 SG_ LEFT_DOOR : 1|1@1+ (1,0) [0|1] "" ECU
VAL_ 1549 LOCKED 0 "open_latch" 1 "latched";
VAL_ 1549 LEFT_DOOR 0 "closed" 1 "open";
"""
    data = {
        "version": 1.1,
        "dbc": {"files": [{"path": "signals.dbc"}]},
        "endpoints": BODY,
        "sequences": SESSION,
        "signals": {
            "DOORS": {
                "monitor": {"message": "BODY", "signal": "LOCKED"},
                "normalize": {"enum": {"latched": "locked", "open_latch": "unlocked"}},
            },
            "FRONT_LEFT_DOOR": {"monitor": {"message": "BODY", "signal": "LEFT_DOOR"}},
        },
        "actions": {
            "DOORS": {
                "endpoint": "body",
                "values": {
                    "lock": {
                        "steps": [
                            {"ref": "sequences.body_session"},
                            {"send": [4, 0x30, 0x38, 0, 1, 0, 0, 0], "expect": [0x70, 0x38, "*"]},
                        ]
                    },
                    "unlock": {"send": [4, 0x30, 0x38, 0, 2, 0, 0, 0], "expect": [0x70, 0x38]},
                },
            },
            # The flat key is the same action as TRUNK: {values: {open: ...}}.
            "TRUNK.open": {"endpoint": "body", "send": [4, 0x30, 0x40, 0, 1, 0, 0, 0]},
            "TRUNK.close": {"endpoint": "body", "send": [4, 0x30, 0x40, 0, 2, 0, 0, 0]},
            "SUNROOF": {
                "endpoint": "body",
                "values": {"open": {"send": [2, 0x31, 1]}, "close": {"send": [2, 0x31, 2]}},
            },
            "LOW_BEAMS": {
                "endpoint": "body",
                "values": {"on": {"send": [2, 0x3B, 1]}, "off": {"send": [2, 0x3B, 0]}},
            },
            "HORN": {"endpoint": "body", "send": [4, 0x30, 0x30, 0, 1, 0, 0, 0]},
        },
    }
    report = migrate(
        _legacy(tmp_path, data, dbc),
        tmp_path / "new",
        framing="isotp-single-frame",
        steering_side="left",
    )
    assert report == []
    doc = resolve([tmp_path / "new"])
    assert not doc.get("actions")
    lock = doc["properties"]["Vehicle.Cabin.IsCentralLockEngaged"]
    assert lock["aliases"] == ["DOORS"]
    assert lock["read"]["signal"]["enum"] == {"0": False, "1": True}
    assert set(lock["write"]["cases"]) == {"true", "false"}
    steps = prepare_write(doc, "Vehicle.Cabin.IsCentralLockEngaged", True)["steps"]
    assert [step["request"] for step in steps] == ["10 81", "30 38 00 01"]
    assert lock["write"]["cases"]["false"]["request"] == "30 38 00 02"
    trunk = doc["properties"]["Vehicle.Body.Trunk.Rear.IsOpen"]
    assert trunk["aliases"] == ["TRUNK"]
    assert trunk["write"]["cases"]["true"]["request"] == "30 40 00 01"
    assert trunk["write"]["cases"]["false"]["request"] == "30 40 00 02"
    sunroof = doc["properties"]["Vehicle.Cabin.Sunroof.Switch"]["write"]["cases"]
    assert {key: case["request"] for key, case in sunroof.items()} == {
        "OPEN": "31 01",
        "CLOSE": "31 02",
    }
    beams = doc["properties"]["Vehicle.Body.Lights.Beam.Low.IsOn"]["write"]["cases"]
    assert beams["true"]["request"] == "3B 01" and beams["false"]["request"] == "3B 00"
    assert doc["properties"]["Vehicle.Body.Horn.IsActive"]["write"]["cases"]["true"]
    assert "Vehicle.Cabin.Door.Row1.DriverSide.IsOpen" in doc["properties"]


def test_version_1_1_commands_without_a_target_are_reported(tmp_path):
    def command(byte):
        return {"send": [2, 0x30, byte]}

    data = {
        "version": 1.1,
        "endpoints": BODY,
        "actions": {
            "CLIMATE": {"endpoint": "body", "values": {"on": command(1)}},
            "WIPERS": {"endpoint": "body", "values": {"off": command(2), "low": command(3)}},
            "ENGINE": {"endpoint": "body", "values": {"on": command(4)}},
            "SPORT_MODE": {
                "endpoint": "body",
                "batch": False,
                "values": {"on": command(5), "off": command(6)},
            },
            "WINDOW_CHILD": {"endpoint": "body", "values": {"lock": command(7)}},
            "MIXED": {"endpoint": "body", "send": [1, 0], "values": {"on": command(8)}},
            "DOORS.lock.now": {"endpoint": "body", "send": [1, 0]},
        },
    }
    report = migrate(_legacy(tmp_path, data), tmp_path / "new", framing="isotp-single-frame")
    reasons = {record["capability"]: record["reason"] for record in report}
    assert set(reasons) == {
        "CLIMATE.on",
        "WIPERS.low",
        "ENGINE.on",
        "WINDOW_CHILD.lock",
        "MIXED",
        "DOORS.lock.now",
    }
    assert "No single climate power actuator" in reasons["CLIMATE.on"]
    assert "'low'" in reasons["WIPERS.low"]
    assert "not an actuator" in reasons["ENGINE.on"]
    assert "WINDOW_CHILD_LOCK is a standard keyword" in reasons["WINDOW_CHILD.lock"]
    assert "values" in reasons["MIXED"]
    climate = next(record for record in report if record["capability"] == "CLIMATE.on")
    assert climate["original"] == {"endpoint": "body", "send": [2, 0x30, 1]}
    doc = resolve([tmp_path / "new"])
    wipers = doc["properties"]["Vehicle.Body.Windshield.Front.Wiping.Mode"]["write"]["cases"]
    assert set(wipers) == {"OFF"}
    assert doc["actions"]["SPORT_MODE_ON"]["request"] == "30 05"
    assert doc["actions"]["SPORT_MODE_OFF"]["request"] == "30 06"
    readme = (tmp_path / "new" / "README.md").read_text()
    assert "SPORT_MODE.on: no VSS actuator" in readme and "SPORT_MODE.on: legacy batch" in readme


def test_version_1_1_encode_becomes_an_encoded_request(tmp_path):
    import pytest
    from vehicle_profile_tools.codec import encode, prepare_write

    data = {
        "version": 1.1,
        "endpoints": BODY,
        "sequences": SESSION,
        "actions": {
            "CHARGE_LIMIT": {
                "endpoint": "body",
                "encode": {"byte": 4, "min": 50, "max": 100, "step": 5},
                "send": [4, 0x2E, 0x12, 0x34, 0, 0, 0, 0],
                "expect": [0x6E, 0x12, 0x34],
            },
            "DRIVER_TEMP_SETTING": {
                "endpoint": "body",
                "encode": {"min": 16, "max": 32, "step": 0.5},
                "steps": [
                    {"ref": "sequences.body_session"},
                    {
                        "send": [5, 0x2E, 0x56, 0x78, 0, 0, 0xFF, 0],
                        "encode": {
                            "start_bit": 39,
                            "length": 16,
                            "byte_order": "big",
                            "scale": 0.5,
                            "offset": -40,
                        },
                    },
                ],
            },
            "FAN_SPEED": {
                "endpoint": "body",
                "encode": {"start_bit": 16, "min": 1, "max": 7},
                "send": [2, 0x31, 0],
            },
            "CABIN_TEMP_SETPOINT": {
                "endpoint": "body",
                "encode": {"byte": 2},
                "send": [2, 0x32, 0],
            },
            "NIBBLE": {
                "endpoint": "body",
                "encode": {"start_bit": 20, "length": 4},
                "send": [2, 0x33, 0],
            },
            "PASSENGER_TEMP_SETTING": {
                "endpoint": "body",
                "encode": {"byte": 0},
                "send": [2, 0x34, 0],
            },
            "FRONT_LEFT_WINDOW_POSITION": {
                "endpoint": "body",
                "encode": {"byte": 2, "max": 300},
                "send": [2, 0x35, 0],
            },
            "LOW_BEAMS": {"endpoint": "body", "encode": {"byte": 2}, "send": [2, 0x36, 0]},
        },
    }
    report = migrate(
        _legacy(tmp_path, data),
        tmp_path / "new",
        framing="isotp-single-frame",
        steering_side="left",
    )
    reasons = {record["capability"]: record["reason"] for record in report}
    assert set(reasons) == {
        "CABIN_TEMP_SETPOINT",
        "NIBBLE",
        "PASSENGER_TEMP_SETTING",
        "FRONT_LEFT_WINDOW_POSITION",
        "LOW_BEAMS",
    }
    assert "station is not fixed" in reasons["CABIN_TEMP_SETPOINT"]
    assert "whole-byte" in reasons["NIBBLE"]
    assert "outside the request payload" in reasons["PASSENGER_TEMP_SETTING"]
    assert "VSS_CONSTRAINT_WIDENED" in reasons["FRONT_LEFT_WINDOW_POSITION"]
    assert "not a numeric actuator" in reasons["LOW_BEAMS"]
    doc = resolve([tmp_path / "new"])
    path = "Vehicle.Powertrain.TractionBattery.Charging.ChargeLimit"
    limit = doc["properties"][path]
    assert limit["aliases"] == ["CHARGE_LIMIT"]
    assert limit["write"]["request"] == {
        "parts": ["2E 12 34", {"input": "value", "type": "uint", "bytes": 1}]
    }
    assert limit["write"]["expect"]["prefix"] == "6E 12 34"
    assert limit["write"]["constraints"] == {"min": 50, "max": 100, "step": 5}
    assert prepare_write(doc, path, 80)["steps"][0]["request"] == "2E 12 34 50"
    with pytest.raises(ValueError, match="grid"):
        prepare_write(doc, path, 82)
    path = "Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature"
    steps = prepare_write(doc, path, 22)["steps"]
    assert [step["request"] for step in steps] == ["10 81", "2E 56 78 00 7C"]
    assert doc["properties"][path]["write"]["constraints"] == {"min": 16, "max": 32, "step": 0.5}
    fan = doc["actions"]["FAN_SPEED"]
    assert encode(fan["request"], {"value": 3}).hex(" ").upper() == "31 03"
    assert fan["input_schema"]["properties"]["value"] == {
        "type": "number",
        "minimum": 1,
        "maximum": 7,
    }
    assert "rounded" in (tmp_path / "new" / "README.md").read_text()


def test_version_1_1_encode_on_an_inline_send(tmp_path):
    from vehicle_profile_tools.codec import encode

    data = {
        "version": 1.1,
        "actions": {
            "DASH_BRIGHTNESS": {
                "encode": {"byte": 1, "max": 100},
                "send": {"request_id": 0x35D, "request": [0xA0, 0, 0, 0, 0, 0, 0, 0]},
            }
        },
    }
    assert migrate(_legacy(tmp_path, data), tmp_path / "new") == []
    doc = resolve([tmp_path / "new"])
    action = doc["actions"]["DASH_BRIGHTNESS"]
    assert action["endpoint"] == "generated-dash_brightness"
    assert encode(action["request"], {"value": 64}).hex(" ").upper() == "A0 40 00 00 00 00 00 00"
    assert action["input_schema"]["properties"]["value"] == {"type": "number", "maximum": 100}


def test_only_version_1_and_1_1_are_read(tmp_path):
    import pytest

    for index, version in enumerate([1.2, 2, True, "1.1", None]):
        folder = tmp_path / str(index)
        folder.mkdir()
        with pytest.raises(ValueError, match="version 1 or 1.1"):
            migrate(_legacy(folder, {"version": version}), folder / "new")
    assert migrate(_legacy(tmp_path, {"version": 1.1}), tmp_path / "new") == []


def test_checked_in_versa_is_reproducible():
    import subprocess
    import sys

    subprocess.run([sys.executable, str(ROOT / "scripts/migrate-versa.py"), "--check"], check=True)
