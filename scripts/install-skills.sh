#!/bin/sh
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source_dir="$script_dir/../skills"
agent=cursor
project=false
destination=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent|--dir)
      [ "$#" -ge 2 ] || { echo "Missing option value" >&2; exit 2; }
      if [ "$1" = --agent ]; then agent=$2; else destination=$2; fi
      shift 2 ;;
    --project) project=true; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$agent" in cursor|claude|codex|all) ;; *) echo "Invalid agent" >&2; exit 2 ;; esac
base="$HOME"
if [ "$project" = true ]; then base=$(pwd); fi
copy_to() {
  case "$1/" in *'/skills-cursor/'*) echo "Refusing Cursor-owned skills-cursor" >&2; exit 2 ;; esac
  mkdir -p "$1"
  target_dir=$(CDPATH= cd -- "$1" && pwd -P)
  case "$target_dir/" in *'/skills-cursor/'*) echo "Refusing Cursor-owned skills-cursor" >&2; exit 2 ;; esac
  for source in "$source_dir"/*; do
    [ -f "$source/SKILL.md" ] || continue
    name=$(basename "$source")
    target="$target_dir/$name"
    [ ! -L "$target" ] || { echo "Refusing symlink destination" >&2; exit 2; }
    source_path=$(CDPATH= cd -- "$source" && pwd -P)
    case "$target/" in "$source_path/"*) echo "Refusing source destination" >&2; exit 2 ;; esac
  done
  for source in "$source_dir"/*; do
    [ -f "$source/SKILL.md" ] || continue
    target="$target_dir/$(basename "$source")"
    if [ -d "$target" ]; then rm -r -- "$target"; fi
    cp -R "$source" "$target"
    echo "$target"
  done
}
if [ -n "$destination" ]; then
  copy_to "$destination"
else
  agents=$agent
  if [ "$agent" = all ]; then agents='cursor claude codex'; fi
  for selected in $agents; do
    case "$selected" in cursor) folder=.cursor ;; claude) folder=.claude ;; codex) folder=.agents ;; esac
    copy_to "$base/$folder/skills"
  done
fi
