# Vehicle profile agent skills

Copy the three skill directories into your agent's skills folder, or use either installer:

```sh
mkdir -p ~/.cursor/skills
cp -R skills/authoring-vehicle-profiles skills/validating-vehicle-profiles skills/migrating-vehicle-profiles ~/.cursor/skills/
./scripts/install-skills.sh --agent all --project
vprofile skills install --agent all --project
vprofile skills list
```

Both installers accept `--agent cursor|claude|codex|all`, `--project`, and `--dir PATH`. Default is Cursor user scope. User destinations are `~/.cursor/skills`, `~/.claude/skills`, and `~/.agents/skills`; project destinations use those same paths relative to the current directory. `--dir` overrides the destination. Existing skill folders with matching names are replaced; other skills are untouched. Symlink skill destinations and Cursor-owned `skills-cursor` paths are refused.

The shell script requires only POSIX sh and standard filesystem utilities, resolves source skills relative to itself, and works from any current directory. The Python wheel bundles the skills so installation does not need a clone. Without a local install:

```sh
uvx --from "git+https://github.com/the-can-opener/vehicle-profile-spec#subdirectory=tools" vprofile skills install --agent codex
```
