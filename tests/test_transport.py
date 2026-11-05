"""Channel defaults, CAN FD, ISO-TP addressing and receive-ID ranges."""

import pytest
from conftest import base, signal
from vehicle_profile_tools.codec import prepare_write
from vehicle_profile_tools.errors import ProfileError
from vehicle_profile_tools.resolve import resolve


def _fd_package():
    data = base()
    data["channels"] = {
        "can0": {"protocol": "can", "bitrate": 500000},
        "can1": {
            "protocol": "canfd",
            "bitrate": "auto",
            "data_bitrate": 2000000,
            "fd": {"tx_dl": 64},
        },
    }
    data["endpoints"] = {
        "obd": {
            "channel": "can1",
            "protocol": "isotp",
            "tx": "7DF",
            "rx": [{"range": ["7E8", "7EF"]}],
            "responder": "7E8",
            "id_format": "standard",
            "timeout_ms": 500,
        },
        "bcm": {
            "channel": "can1",
            "protocol": "isotp",
            "tx": "7A0",
            "rx": ["7A8"],
            "id_format": "standard",
            "timeout_ms": 500,
            "fd": {"tx_dl": 8},
        },
        "legacy": {
            "channel": "can1",
            "protocol": "can",
            "tx": "7B0",
            "id_format": "standard",
            "fd": False,
        },
        "lamps": {"channel": "can1", "protocol": "can", "tx": "3F1", "id_format": "standard"},
        "dme": {
            "protocol": "isotp",
            "tx": "6F1",
            "rx": ["612"],
            "id_format": "standard",
            "timeout_ms": 500,
            "addressing": {"mode": "extended", "target_address": "12", "source_address": "F1"},
        },
    }
    return data


def test_defaults_materialize(package):
    data = base()
    del data["channels"]
    del data["endpoints"]["ecu"]["channel"]
    prop = signal()
    del prop["read"]["signal"]["channel"]
    data["properties"] = {"Vehicle.Speed": prop}
    result = resolve([package(data)])
    assert result["channels"] == {"can0": {"protocol": "can", "bitrate": 500000}}
    assert result["endpoints"]["ecu"]["channel"] == "can0"
    assert result["properties"]["Vehicle.Speed"]["read"]["signal"]["channel"] == "can0"


def test_declared_channel_keeps_default_bitrate(package):
    data = base()
    data["channels"] = {"bus": {"protocol": "can"}}
    assert resolve([package(data)])["channels"]["bus"]["bitrate"] == 500000


def test_runtime_configuration_is_not_defaulted(package):
    result = resolve([package(base())])
    assert result["channels"]["bus"] == {"protocol": "can", "configuration": "runtime"}


def test_fd_and_addressing_round_trip(package):
    data = _fd_package()
    data["properties"] = {
        "Vehicle.VehicleIdentification.VIN": {
            "read": {
                "query": {
                    "endpoint": "dme",
                    "request": "22 F1 90",
                    "response": {"prefix": "62 F1 90", "min_data_bytes": 17},
                    "decode": {"byte": 0, "bytes": 17, "type": "ascii"},
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
                        "mask": " ".join(["FF"] * 64),
                        "patch": " ".join(["00"] * 64),
                    },
                },
            }
        },
    }
    result = resolve([package(data)])
    assert result["channels"]["can1"]["bitrate"] == "auto"
    assert result["channels"]["can0"]["bitrate"] == 500000
    assert result["endpoints"]["obd"]["rx"] == [{"range": ["7E8", "7EF"]}]
    assert result["endpoints"]["dme"]["channel"] == "can0"
    assert result["endpoints"]["dme"]["addressing"]["target_address"] == "12"
    assert result["endpoints"]["bcm"]["fd"] == {"tx_dl": 8}
    assert result["endpoints"]["legacy"]["fd"] is False


def test_raw_frame_limit_follows_resolved_fd(package):
    data = _fd_package()
    data["properties"] = {
        "Vehicle.Body.Horn.IsActive": {
            "write": {"endpoint": "lamps", "request": " ".join(["01"] * 12)}
        }
    }
    result = resolve([package(data)])
    prepared = prepare_write(result, "Vehicle.Body.Horn.IsActive", True)
    assert len(prepared["steps"][0]["request"].split()) == 12
    data["properties"]["Vehicle.Body.Horn.IsActive"]["write"]["endpoint"] = "legacy"
    with pytest.raises(ProfileError, match="raw CAN request exceeds 8"):
        resolve([package(data, folder="classic")])


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda d: d["channels"]["can0"].update(data_bitrate=2000000), "require protocol canfd"),
        (lambda d: d["channels"]["can0"].update(fd=True), "require protocol canfd"),
        (
            lambda d: d["channels"]["can0"].update(configuration="runtime"),
            "DOC_EXCLUSIVE_FORMS",
        ),
        (lambda d: d["channels"]["can1"].update(fd={"tx_dl": 12}), "channels.can1.fd"),
        (lambda d: d["endpoints"]["dme"].update(fd=True), "classic channel"),
        (lambda d: d["endpoints"]["lamps"].update(fd={"tx_dl": 64}), "raw CAN takes fd"),
        (
            lambda d: d["endpoints"]["lamps"].update(
                addressing={"mode": "mixed", "address_extension": "A5"}
            ),
            "requires protocol isotp",
        ),
        (
            lambda d: d["endpoints"]["dme"]["addressing"].update(address_extension="A5"),
            "DOC_UNKNOWN_FIELD",
        ),
        (lambda d: d["endpoints"]["dme"]["addressing"].update(target_address="123"), "pattern"),
        (lambda d: d["endpoints"]["obd"]["rx"].append("7EA"), "overlap"),
        (
            lambda d: d["endpoints"]["obd"]["rx"].append({"range": ["7F0", "7E0"]}),
            "endpoints.obd.rx",
        ),
        (lambda d: d["endpoints"]["obd"].update(responder="7F0"), "responder"),
        (
            lambda d: d["endpoints"]["obd"].update(rx=[{"range": ["100", "4FF"]}]),
            "endpoints.obd.rx",
        ),
        (lambda d: d["endpoints"]["bcm"].update(channel="can9"), "unknown channel"),
    ],
)
def test_transport_rejections(package, mutate, match):
    data = _fd_package()
    mutate(data)
    with pytest.raises(ProfileError, match=match):
        resolve([package(data)])


def test_dbc_channel_must_exist(package, tmp_path):
    data = base()
    data["dbc"] = {"main": {"path": "signals.dbc", "channel": "missing"}}
    dbc = 'BO_ 100 M: 1 ECU\n SG_ S : 0|8@1+ (1,0) [0|255] "km/h" ECU\n'
    with pytest.raises(ProfileError, match="dbc.main.channel"):
        resolve([package(data, files={"signals.dbc": dbc})])
    data["dbc"]["main"] = {"path": "signals.dbc"}
    result = resolve([package(data, folder="default", files={"signals.dbc": dbc})])
    assert result["channels"]["can0"] == {"protocol": "can", "bitrate": 500000}
