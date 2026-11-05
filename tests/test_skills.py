import re
import subprocess
from pathlib import Path

import yaml
from conftest import ROOT, base
from vehicle_profile_tools.errors import error_reference
from vehicle_profile_tools.resolve import resolve


def test_skill_metadata_and_fragments(package):
    count = 0
    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text()
        front, body = text.split("---", 2)[1:]
        meta = yaml.safe_load(front)
        assert meta["name"] == skill.parent.name
        assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
        assert 0 < len(meta["description"]) <= 1024
        assert meta["description"].split()[0].endswith("s")  # Third-person verb.
        assert "vehicle" in meta["description"].lower()
        assert "disable-model-invocation" not in meta
        assert len(body.splitlines()) < 500
        for link in re.findall(r"\]\(([^)]+)\)", body):
            assert len(Path(link).parts) == 1
            reference = skill.parent / link
            assert reference.is_file()
            assert not re.findall(r"\]\((?!https?://)[^)]+\)", reference.read_text())
        for reference in skill.parent.glob("*.md"):
            last_document = None
            for kind, fragment in re.findall(
                r"```yaml vprofile-(fragment|fixture)\n(.*?)```", reference.read_text(), re.S
            ):
                if kind == "fixture":
                    from vehicle_profile_tools.model import Fixture
                    from vehicle_profile_tools.resolve import validate_fixtures

                    assert last_document is not None
                    validate_fixtures(
                        Fixture.model_validate(yaml.safe_load(fragment)), last_document
                    )
                else:
                    doc = base()
                    doc.pop("channels")
                    doc.pop("endpoints")
                    doc.update(yaml.safe_load(fragment))
                    last_document = resolve([package(doc, folder=f"fragment-{count}")])
                    assert last_document
                count += 1
    assert count >= 6


def test_error_reference_drift():
    assert (
        ROOT / "skills/validating-vehicle-profiles/error-codes.md"
    ).read_text() == error_reference()


def test_schema_drift():
    import sys

    subprocess.run([sys.executable, str(ROOT / "scripts/generate.py"), "--check"], check=True)


def test_examples_against_generated_schemas():
    import jsonschema
    from vehicle_profile_tools.container import Package
    from vehicle_profile_tools.exporters.jsonschema import schemas

    definitions = schemas()
    for name in (
        "nissan-versa",
        "universal-obd",
        "hvac-synthetic",
        "canfd-dual-bus",
        "bmw-addressing",
    ):
        pkg = Package(ROOT / "examples" / name)
        jsonschema.validate(pkg.raw, definitions["manifest"])
        for doc, _, _ in pkg.documents():
            jsonschema.validate(doc, definitions["document"])
        for asset in pkg.manifest.fixtures:
            jsonschema.validate(pkg.parse(asset), definitions["fixture"])
    # The authoring schema must admit a null deletion in an overlay.
    jsonschema.validate({"properties": {"Vehicle.Speed": None}}, definitions["document"])


def test_schemas_reject_exclusive_shapes():
    import jsonschema
    import pytest
    from vehicle_profile_tools.exporters.jsonschema import schemas

    schema = schemas()["document"]
    invalid = [
        {"properties": {"Vehicle.Speed": {"value": 1, "read": {"query": {}}}}},
        {
            "actions": {
                "TEST": {
                    "description": "test",
                    "endpoint": "ecu",
                    "request": "01",
                    "steps": [{"wait_ms": 1}],
                }
            }
        },
        {"properties": {"Vehicle.Speed": {"read": {}}}},
        {"properties": {"Vehicle.Speed": {}}},
        {
            "queries": {
                "TEST": {
                    "description": "test",
                    "endpoint": "ecu",
                    "request": "01",
                    "response": {"prefix": "02"},
                    "decode": {"byte": 0, "bytes": 1, "type": "uint"},
                }
            }
        },
    ]
    for document in invalid:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(document, schema)
