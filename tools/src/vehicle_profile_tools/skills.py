import shutil
from pathlib import Path

TARGETS = {"cursor": ".cursor", "claude": ".claude", "codex": ".agents"}


def skill_root():
    root = Path(__file__).parent / "bundled_skills"
    return root if root.is_dir() else Path(__file__).resolve().parents[3] / "skills"


def list_skills():
    return sorted(p.name for p in skill_root().iterdir() if (p / "SKILL.md").is_file())


def install(agent="cursor", project=False, directory=None):
    base = Path.cwd() if project else Path.home()
    destinations = (
        [Path(directory).expanduser()]
        if directory
        else [base / TARGETS[name] / "skills" for name in (TARGETS if agent == "all" else [agent])]
    )
    written = []
    for destination in destinations:
        destination = destination.resolve()
        if "skills-cursor" in destination.parts:
            raise ValueError("refusing Cursor-owned skills-cursor directory")
        for name in list_skills():
            target = destination / name
            source = skill_root() / name
            if target.is_symlink() or target.resolve().is_relative_to(source.resolve()):
                raise ValueError("refusing symlink or source skill destination")
        destination.mkdir(parents=True, exist_ok=True)
        for name in list_skills():
            target = destination / name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(skill_root() / name, target)
            written.append(str(target))
    return written
