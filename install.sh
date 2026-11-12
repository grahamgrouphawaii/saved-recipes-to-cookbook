#!/usr/bin/env bash
# Copy the skill into ~/.claude/skills so Claude Code can find it.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$dest"
if [ -e "$dest/instagram-recipes" ]; then
  read -r -p "$dest/instagram-recipes already exists. Replace it? [y/N] " a
  case "$a" in [yY]*) rm -rf "$dest/instagram-recipes";; *) echo "left alone"; exit 0;; esac
fi
cp -R "$here/skills/instagram-recipes" "$dest/"
chmod +x "$dest/instagram-recipes/scripts/watch.sh"
echo "installed to $dest/instagram-recipes"
echo
echo "Now open Claude Code and ask it to build a recipe book from your saved Instagram recipes."
echo "Missing ffmpeg, yt-dlp or whisper? See skills/instagram-recipes/reference/setup.md"
