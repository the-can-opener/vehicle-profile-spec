import hashlib

import pytest
from conftest import base
from vehicle_profile_tools.errors import ProfileError
from vehicle_profile_tools.resolve import resolve
from vehicle_profile_tools.strict import parse


@pytest.mark.parametrize(
    "text", ["a: 1\na: 2", "a: &x 1\nb: *x", "a: !!str 1", "a: .nan", "true: 1", "1: x"]
)
def test_invalid_yaml(text):
    with pytest.raises(ProfileError, match="DOC_INVALID"):
        parse(text)


def test_yaml_json_compatible():
    assert parse("a: on\nb: 2026-11-04\nc: true") == {"a": "on", "b": "2026-11-04", "c": True}


def test_hash_policy(package):
    data = base()
    data.pop("channels")
    data.pop("endpoints")
    data["documents"] = [{"path": "a.json"}]
    root = package(data, files={"a.json": "{}"})
    with pytest.raises(ProfileError, match="PKG_HASH_MISMATCH"):
        resolve([root], integrity_required=True)
    data["documents"][0]["sha256"] = hashlib.sha256(b"{}").hexdigest()
    assert resolve([package(data, files={"a.json": "{}"})], integrity_required=True)
    with pytest.raises(ProfileError, match="PKG_HASH_MISMATCH"):
        resolve([package(data, files={"a.json": "{ }"})])


def test_symlink(package, tmp_path):
    data = base()
    data.pop("channels")
    data.pop("endpoints")
    data["documents"] = [{"path": "a.json"}]
    root = package(data)
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    (root / "a.json").symlink_to(outside)
    with pytest.raises(ProfileError, match="PKG_UNSAFE_PATH"):
        resolve([root])


@pytest.mark.parametrize("text", ['{"x":NaN}', '{"x":Infinity}', '{"x":1,"x":2}', "x: 1"])
def test_strict_json(text):
    with pytest.raises(ProfileError, match="DOC_INVALID"):
        parse(text, "test.json")


def test_unlisted_directory_file_is_never_parsed(package):
    root = package(files={"unlisted.yaml": "a: !!python/object:bad {}"})
    assert resolve([root])


def test_compression_bomb_rejected(tmp_path):
    import zipfile

    path = tmp_path / "large.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("vehicle.yaml", "x" * 100000)
    with pytest.raises(ProfileError, match="PKG_TOO_LARGE"):
        resolve([path])


def test_duplicate_manifests(package):
    with pytest.raises(ProfileError, match="PKG_MULTIPLE_MANIFESTS"):
        resolve([package(files={"vehicle.yaml": "{}"})])
