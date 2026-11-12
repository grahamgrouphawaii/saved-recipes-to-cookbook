#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# The half of the job that needs no AI at all.
#
# Triage the export, build every recipe whose creator already wrote it down,
# index it, and check every link. Nothing here calls a model or the network, so
# it costs nothing and you can run it as many times as you like.
#
#   ./run.sh recipes.json [--out book] [--title "My Recipe Book"] [--threshold 6]
#
# Afterwards it tells you what is left, which is the reels that have to be
# watched. Those need scripts/watch.sh and a model, or your own eyes.
# ---------------------------------------------------------------------------
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
S="$here/skills/instagram-recipes/scripts"
[ -d "$S" ] || S="$here/scripts"          # also works from inside an installed skill

IN=""; OUT=book; TITLE="Recipe Book"; DATA=data; THRESH=6
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2;;
    --title) TITLE="$2"; shift 2;;
    --data) DATA="$2"; shift 2;;
    --threshold) THRESH="$2"; shift 2;;
    -h|--help) sed -n '3,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
    -*) echo "unknown option: $1" >&2; exit 2;;
    *) IN="$1"; shift;;
  esac
done

if [ -z "$IN" ]; then
  echo "usage: ./run.sh recipes.json [--out book] [--title \"My Recipe Book\"]" >&2
  echo >&2
  echo "No recipes.json yet? Open your saved collection on instagram.com, open the" >&2
  echo "browser console, and paste in scripts/export-collection.js. The instructions" >&2
  echo "are at the top of that file." >&2
  exit 2
fi
[ -f "$IN" ] || { echo "$IN not found" >&2; exit 1; }

echo "== triage =="
python3 -I "$S/triage.py" "$IN" --out "$DATA" --threshold "$THRESH"

echo
echo "== building everything already written down =="
python3 -I "$S/autobuild.py" "$IN" --out "$OUT" --data "$DATA"

echo
echo "== index and link check =="
python3 -I "$S/index.py" --out "$OUT" --title "$TITLE"
python3 -I "$S/audit.py" "$IN" --out "$OUT" --fix

left=$(python3 -I -c "import json;print(len(json.load(open('$DATA/video_tier.json'))))")
echo
echo "Done, and nothing was spent on it. Your book is in $OUT/"
echo
if [ -d "$OUT/recipes" ]; then
  first=$(ls "$OUT/recipes" | head -1)
  [ -n "$first" ] && echo "Have a look at $OUT/recipes/$first to check the format suits you."
fi
echo "$left reels have no written recipe and have to be watched. For those:"
echo "  $S/watch.sh --data $DATA --work work --start 0 --count 50"
echo "then hand the transcripts in work/txt/ to Claude Code or another agent."
echo "The instructions for that half are in $(cd "$S/.." && pwd)/SKILL.md"
