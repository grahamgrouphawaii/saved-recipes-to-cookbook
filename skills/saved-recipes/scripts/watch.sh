#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Download the video-tier reels and turn each one into a transcript and a
# handful of frames.
#
# Everything here runs on your own machine and costs nothing but time and disk.
# The mp4 is deleted as soon as its transcript and frames are out, so a few
# hundred reels never takes more than a couple of hundred megabytes at once.
#
#   ./watch.sh --data data --work work [--start 0] [--count 50]
#              [--browser chrome] [--model path/to/ggml-base.en.bin] [--no-frames]
#
# Re-running it skips anything already transcribed, so it is safe to stop it
# half way and pick up later.
# ---------------------------------------------------------------------------
set -uo pipefail
shopt -s nullglob

DATA=data; WORK=work; START=0; COUNT=0; BROWSER=chrome; MODEL=""; FRAMES=1
while [ $# -gt 0 ]; do
  case "$1" in
    --data) DATA="$2"; shift 2;;
    --work) WORK="$2"; shift 2;;
    --start) START="$2"; shift 2;;
    --count) COUNT="$2"; shift 2;;
    --browser) BROWSER="$2"; shift 2;;
    --model) MODEL="$2"; shift 2;;
    --no-frames) FRAMES=0; shift;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

command -v ffmpeg >/dev/null || { echo "ffmpeg not found. See reference/setup.md" >&2; exit 1; }

YTDLP=$(command -v yt-dlp || true)
[ -z "$YTDLP" ] && [ -x "$WORK/venv/bin/yt-dlp" ] && YTDLP="$WORK/venv/bin/yt-dlp"
[ -z "$YTDLP" ] && { echo "yt-dlp not found. See reference/setup.md" >&2; exit 1; }

# whisper.cpp is preferred: it is fast on an Apple silicon CPU and needs no API key
WHISPER=""
if command -v whisper-cli >/dev/null; then WHISPER=cpp
elif command -v whisper >/dev/null;    then WHISPER=py
else echo "note: no whisper found, so frames only and no transcripts (see reference/setup.md)"; fi

if [ "$WHISPER" = cpp ] && [ -z "$MODEL" ]; then
  for c in "$WORK/models/ggml-base.en.bin" "$HOME/.cache/whisper/ggml-base.en.bin" \
           /opt/homebrew/share/whisper.cpp/ggml-base.en.bin; do
    [ -f "$c" ] && MODEL="$c" && break
  done
  [ -z "$MODEL" ] && { echo "whisper-cli is installed but no ggml model found. See reference/setup.md" >&2; WHISPER=""; }
fi

mkdir -p "$WORK/frames" "$WORK/txt" "$WORK/mp4"

mapfile_urls=$(python3 -I -c "
import json,sys
v=json.load(open('$DATA/video_tier.json'))
s=$START; c=$COUNT
v=v[s:s+c] if c else v[s:]
import os
todo=[x for x in v if not os.path.exists('$WORK/txt/%s.txt'%x['code'])
                   and not os.path.isdir('$WORK/frames/%s'%x['code'])]
print(' '.join(x.get('url') or 'https://www.instagram.com/reel/%s/'%x['code'] for x in todo))
print(len(todo), file=sys.stderr)
")
N=$(printf '%s' "$mapfile_urls" | wc -w | tr -d ' ')
if [ "$N" -eq 0 ]; then echo "nothing left to do in that range"; exit 0; fi

echo "downloading $N reels (cookies from $BROWSER)..."
# --cookies-from-browser reads the session straight out of the running browser.
# Nothing is written to disk, which is the point: no cookie file to leak.
# shellcheck disable=SC2086
"$YTDLP" --cookies-from-browser "$BROWSER" -f 'mp4/best[ext=mp4]/best' \
  --no-warnings --ignore-errors --sleep-interval 1 --max-sleep-interval 3 \
  -o "$WORK/mp4/%(id)s.%(ext)s" $mapfile_urls 2>&1 \
  | grep -Ei "error|^\[download\] Destination" | tail -40

echo "=== transcribing and grabbing frames ==="
done_n=0
for f in "$WORK"/mp4/*.mp4; do
  id=$(basename "$f" .mp4)
  [ -f "$WORK/txt/$id.txt" ] && { rm -f "$f"; continue; }

  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null | cut -d. -f1)
  [ -z "$dur" ] && dur=30

  if [ "$FRAMES" -eq 1 ]; then
    mkdir -p "$WORK/frames/$id"
    # a frame roughly every nine seconds, three minimum, ten maximum. Enough to
    # read on-screen text without handing the model a flipbook.
    n=$(( dur / 9 + 3 )); [ "$n" -gt 10 ] && n=10
    rate=$(python3 -I -c "print(max(0.08, $n/float($dur)))")
    ffmpeg -loglevel error -y -i "$f" -vf "fps=$rate,scale=400:-2" \
           -frames:v "$n" -q:v 7 "$WORK/frames/$id/f_%02d.jpg" 2>/dev/null
  fi

  if [ -n "$WHISPER" ]; then
    ffmpeg -loglevel error -y -i "$f" -ar 16000 -ac 1 -c:a pcm_s16le "$WORK/a.wav" 2>/dev/null
    if [ -f "$WORK/a.wav" ]; then
      if [ "$WHISPER" = cpp ]; then
        whisper-cli -m "$MODEL" -f "$WORK/a.wav" -nt -np 2>/dev/null \
          | tr '\n' ' ' | sed 's/  */ /g' > "$WORK/txt/$id.txt"
      else
        whisper "$WORK/a.wav" --model base.en --output_format txt \
          --output_dir "$WORK/txt" --fp16 False >/dev/null 2>&1
        [ -f "$WORK/txt/a.txt" ] && mv "$WORK/txt/a.txt" "$WORK/txt/$id.txt"
      fi
      rm -f "$WORK/a.wav"
    fi
  fi
  rm -f "$f"
  done_n=$((done_n+1))
done

echo "=== $done_n processed. $(ls "$WORK/txt" 2>/dev/null | wc -l | tr -d ' ') transcripts, $(ls "$WORK/frames" 2>/dev/null | wc -l | tr -d ' ') frame sets ==="
