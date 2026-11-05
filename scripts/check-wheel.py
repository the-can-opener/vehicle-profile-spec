"""Check wheel resources and exercise imports without the source tree."""

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with zipfile.ZipFile(sys.argv[1]) as wheel:
    names = wheel.namelist()
    for skill in ("authoring", "validating", "migrating"):
        directory = f"{skill}-vehicle-profiles"
        for source in (root / "skills" / directory).rglob("*"):
            if source.is_file():
                packaged = f"vehicle_profile_tools/bundled_skills/{directory}/{source.relative_to(root / 'skills' / directory)}"
                assert wheel.read(packaged) == source.read_bytes(), packaged
    for source, packaged in [
        ("catalog/vss-6.1.json", "vss-6.1.json"),
        ("docs/vocabulary.yaml", "vocabulary.yaml"),
        ("catalog/LICENSE", "VSS-LICENSE"),
    ]:
        assert wheel.read(f"vehicle_profile_tools/data/{packaged}") == (root / source).read_bytes()
    with tempfile.TemporaryDirectory() as temp:
        wheel.extractall(temp)
        code = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import vehicle_profile_tools
from vehicle_profile_tools.catalog import load_catalog
from vehicle_profile_tools.skills import list_skills, install
assert Path(vehicle_profile_tools.__file__).is_relative_to(sys.argv[1])
assert len(load_catalog()) > 1300
assert len(list_skills()) == 3
assert len(install(directory=Path(sys.argv[1]) / 'installed')) == 3
"""
        subprocess.run([sys.executable, "-c", code, temp], cwd=temp, check=True)
print("Wheel resources and isolated imports verified")
