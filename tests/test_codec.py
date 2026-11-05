import pytest
from vehicle_profile_tools.codec import check_constraints, decode, encode, hex_bytes, matches


def test_exact_encoding():
    request = {
        "parts": [
            "AA BB",
            {"input": "value", "type": "uint", "bytes": 1, "scale": 0.5, "offset": 16},
        ]
    }
    assert encode(request, {"value": 22}) == bytes.fromhex("AA BB 0C")
    with pytest.raises(ValueError, match="exact integer"):
        encode(request, {"value": 22.25})
    with pytest.raises(ValueError, match="wire width"):
        encode(request, {"value": 999})
    with pytest.raises(ValueError, match="grid"):
        check_constraints(22.25, {"min": 16, "max": 30, "step": 0.5})
    check_constraints(0.3, {"min": 0.1, "step": 0.1})


def test_pattern():
    assert matches({"prefix": "70 38 *"}, "70 38 FF 00")
    assert not matches({"prefix": "70 38 *", "exact": True}, "70 38 FF 00")
    assert not matches({"prefix": "41 00", "min_data_bytes": 4}, "41 00 01")
    assert not matches({"prefix": "70 38 *"}, "70 39 FF")
    with pytest.raises(ValueError):
        hex_bytes("aa bb")


def test_decoders():
    assert decode("FF 00", {"byte": 0, "bytes": 1, "type": "int"}) == -1
    assert decode("80", {"start_bit": 0, "bits": 1, "bit_order": "msb0", "type": "uint"}) == 1
    assert decode("80", {"start_bit": 0, "bits": 1, "bit_order": "lsb0", "type": "uint"}) == 0
    assert decode("41 42", {"byte": 0, "bytes": 2, "type": "ascii"}) == "AB"
    assert decode("0F", {"byte": 0, "bytes": 1, "type": "hex"}) == "0F"
    with pytest.raises(ValueError, match="short"):
        decode("00", {"byte": 0, "bytes": 2, "type": "uint"})
    with pytest.raises(ValueError, match="unmapped"):
        decode("02", {"byte": 0, "bytes": 1, "type": "uint", "enum": {"0": False, "1": True}})


def test_merge_repeat_frame():
    from vehicle_profile_tools.codec import merge_repeat_frame

    merged = merge_repeat_frame(
        "11 22 33 44 55 66 77 88",
        "00 00 F0 00 00 00 00 00",
        "00 00 40 00 00 00 00 00",
    )
    assert merged == bytes.fromhex("11 22 43 44 55 66 77 88")
    with pytest.raises(ValueError, match="outside the mask"):
        merge_repeat_frame("00", "0F", "F0")
    with pytest.raises(ValueError, match="base frame length"):
        merge_repeat_frame("00 00", "FF", "01")


def test_prepare_numeric_write():
    from conftest import ROOT
    from vehicle_profile_tools.codec import prepare_write
    from vehicle_profile_tools.resolve import resolve

    doc = resolve([ROOT / "examples/hvac-synthetic"])
    path = "Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature"
    assert prepare_write(doc, path, 22)["steps"][0]["request"] == "AA BB 0C"
    with pytest.raises(ValueError, match="grid"):
        prepare_write(doc, path, 22.25)
    with pytest.raises(ValueError, match="max"):
        prepare_write(doc, path, 31)


def test_prepare_case_and_nested_sequence():
    from conftest import ROOT
    from vehicle_profile_tools.codec import prepare_write
    from vehicle_profile_tools.resolve import resolve

    doc = resolve([ROOT / "examples/nissan-versa"], {"year": 2008})
    assert len(prepare_write(doc, "Vehicle.Body.Horn.IsActive", True)["steps"]) == 3
    signal = prepare_write(doc, "Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling", True)
    assert signal["duration"] == 5000
    assert signal["release"] == {"action": "SIGNAL_OFF"}
    assert signal["steps"][-1]["request"] == "30 2F 00 02"
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        prepare_write(doc, "Vehicle.Body.Horn.IsActive", False)


def test_encoding_does_not_round_large_decimal():
    from decimal import Decimal

    value = Decimal("10000000000000000000000000000.1")
    request = {"parts": [{"input": "value", "type": "uint", "bytes": 32}]}
    with pytest.raises(ValueError, match="exact integer"):
        encode(request, {"value": value})


def test_numeric_case_canonicalization():
    from vehicle_profile_tools.codec import prepare_write

    doc = {
        "endpoints": {"e": {"protocol": "can"}},
        "properties": {"X": {"write": {"cases": {"22": {"endpoint": "e", "request": "01"}}}}},
    }
    assert (
        prepare_write(doc, "X", 22.0, {"X": {"datatype": "float"}})["steps"][0]["request"] == "01"
    )
