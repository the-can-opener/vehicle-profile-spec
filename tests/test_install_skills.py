import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ROOT
from vehicle_profile_tools.skills import install, list_skills


def tree(path):
    return {str(f.relative_to(path)): f.read_bytes() for f in path.rglob("*") if f.is_file()}


@pytest.mark.parametrize("agent", ["cursor", "claude", "codex", "all"])
@pytest.mark.parametrize("project", [False, True])
def test_installers_match(tmp_path, monkeypatch, agent, project):
    # Change only the child process environment; never mutate the actual user's HOME.
    home = tmp_path / "home"
    home.mkdir()
    work = tmp_path / "project"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setenv("HOME", str(home))
    command = [
        sys.executable,
        "-m",
        "vehicle_profile_tools.cli",
        "skills",
        "install",
        "--agent",
        agent,
    ]
    if project:
        command.append("--project")
    installed = subprocess.run(command, check=True, capture_output=True, text=True)
    paths = installed.stdout.splitlines()
    expected = {p: tree(Path(p)) for p in paths}
    # Ensure replacement removes stale content, rather than merely overlaying it.
    for p in paths:
        (Path(p) / "stale.txt").write_text("old")
    args = [str(ROOT / "scripts/install-skills.sh"), "--agent", agent]
    if project:
        args.append("--project")
    subprocess.run(args, check=True, capture_output=True)
    assert {p: tree(Path(p)) for p in paths} == expected
    for p in paths:
        assert tree(Path(p)) == tree(ROOT / "skills" / Path(p).name)


def test_explicit_directory(tmp_path):
    a, b = tmp_path / "python", tmp_path / "shell"
    install(directory=a)
    subprocess.run(
        [str(ROOT / "scripts/install-skills.sh"), "--dir", str(b)], check=True, capture_output=True
    )
    assert tree(a) == tree(b)
    assert len(list_skills()) == 3


def test_protected_destination(tmp_path):
    dest = tmp_path / ".cursor/skills-cursor"
    with pytest.raises(ValueError):
        install(directory=dest)
    result = subprocess.run(
        [str(ROOT / "scripts/install-skills.sh"), "--dir", str(dest)], capture_output=True
    )
    assert result.returncode != 0


def test_cli_default_destination(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-m", "vehicle_profile_tools.cli", "skills", "install"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(result.stdout.splitlines()) == 3
    assert all(str(tmp_path / ".cursor/skills") in line for line in result.stdout.splitlines())
