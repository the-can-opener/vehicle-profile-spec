import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def base():
    return {
        "manifest": 1,
        "format": 2,
        "id": "org.test.base",
        "version": "1.0.0",
        "name": "Test",
        "vss": "6.1",
        "channels": {"bus": {"protocol": "can", "configuration": "runtime"}},
        "endpoints": {
            "ecu": {
                "channel": "bus",
                "protocol": "isotp",
                "tx": "700",
                "rx": ["708"],
                "id_format": "standard",
                "timeout_ms": 300,
            }
        },
    }


def signal():
    return {
        "read": {
            "signal": {
                "channel": "bus",
                "id": "123",
                "id_format": "standard",
                "length": 1,
                "decode": {"byte": 0, "bytes": 1, "type": "uint"},
            }
        }
    }


@pytest.fixture
def package(tmp_path):
    def write(data=None, folder="package", files=None):
        root = tmp_path / folder
        root.mkdir(exist_ok=True)
        (root / "vehicle.json").write_text(json.dumps(data if data is not None else base()))
        for path, value in (files or {}).items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value if isinstance(value, str) else json.dumps(value))
        return root

    return write
