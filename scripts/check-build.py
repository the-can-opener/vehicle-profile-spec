"""Build and inspect a wheel in temporary storage, using installed dev dependencies."""

import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="vprofile-wheel-") as output:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            output,
            str(root / "tools"),
        ],
        check=True,
        capture_output=True,
    )
    wheels = list(Path(output).glob("*.whl"))
    assert len(wheels) == 1
    subprocess.run(
        [sys.executable, str(root / "scripts/check-wheel.py"), str(wheels[0])], check=True
    )
