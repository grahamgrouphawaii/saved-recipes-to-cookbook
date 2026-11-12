#!/usr/bin/env bash
# Copy the skill into ~/.claude/skills so Claude Code can find it.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$dest"
if [ -e "$dest/saved-recipes" ]; then
  read -r -p "$dest/saved-recipes already exists. Replace it? [y/N] " a
  case "$a" in [yY]*) rm -rf "$dest/saved-recipes";; *) echo "left alone"; exit 0;; esac
fi
cp -R "$here/skills/saved-recipes" "$dest/"
cp "$here/run.sh" "$dest/saved-recipes/run.sh"
chmod +x "$dest/saved-recipes/scripts/watch.sh" "$dest/saved-recipes/run.sh"
echo "installed to $dest/saved-recipes"
echo
echo "Now open Claude Code and ask it to build a recipe book from your saved recipes."
echo "Missing ffmpeg, yt-dlp or whisper? See skills/saved-recipes/reference/setup.md"
