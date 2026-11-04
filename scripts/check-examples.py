"""Discover example package roots explicitly; skip the legacy migration inputs."""

from pathlib import Path

from vehicle_profile_tools.resolve import resolve

root = Path(__file__).resolve().parents[1]
for package in sorted((root / "examples").iterdir()):
    if package.is_dir() and package.name != "legacy":
        resolve([package])
        print(f"OK: {package.relative_to(root)}")
