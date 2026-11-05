"""Remove disposable repository build/test artifacts; retain the virtual environment."""

import os
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
disposable = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", ".nox"}
for directory, children, _ in os.walk(root, topdown=True):
    children[:] = [name for name in children if name not in {".git", ".venv"}]
    for name in list(children):
        path = Path(directory) / name
        if name in disposable and not path.is_symlink():
            shutil.rmtree(path)
            children.remove(name)
            print(f"Removed {path.relative_to(root)}")
