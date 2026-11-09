import pytest
from conftest import ROOT
from vehicle_profile_tools.dbc import Dbc
from vehicle_profile_tools.errors import ProfileError


def test_native_bits_and_labels():
    dbc = Dbc((ROOT / "examples/legacy/nissan-versa/signals.dbc").read_text())
    speed = dbc.signal("SPEED_BRAKE", "SPEED_KMPH")
    assert speed.raw(bytes.fromhex("01 02 00 00 00 00 00 00")) == 258
    light = dbc.signal("LIGHTS_STATUS_60D", "LOW_BEAMS")
    assert light.decode(bytes.fromhex("04 00 00 00 00 00 00 00"), "boolean") is True
    assert light.labels == {"0": "off", "1": "on"}
    assert light.decode(bytes.fromhex("04 00 00 00 00 00 00 00")) == 1


def test_ambiguous():
    dbc = Dbc("BO_ 1 SAME: 8 ECU\nBO_ 2 SAME: 8 ECU\n")
    with pytest.raises(ProfileError, match="DBC_AMBIGUOUS_MESSAGE"):
        dbc.message("SAME")


def test_multiplexed_rejected():
    with pytest.raises(ProfileError, match="unsupported signal"):
        Dbc('BO_ 1 M: 8 ECU\n SG_ X m0 : 0|8@1+ (1,0) [0|255] "" ECU')
