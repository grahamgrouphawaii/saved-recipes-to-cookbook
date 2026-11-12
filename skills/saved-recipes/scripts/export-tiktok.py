#!/usr/bin/env python3
"""
Export a TikTok collection into the same recipes.json the rest of the pipeline
reads.

TikTok is easier than Instagram here. yt-dlp understands collection URLs
directly and hands back the caption, the duration and the post date in one
metadata call, so there is no browser console script and nothing to paste.

    python3 export-tiktok.py "https://www.tiktok.com/@you/collection/Recipes-7312345678901234567"

Finding that URL: open tiktok.com in a browser, go to your profile, open the
saved tab, then Collections, then the collection you want. Copy what is in the
address bar. It ends in a long number.

TikTok's loose Favorites list, the ungrouped bookmarks, cannot be read this way.
If your recipes are sitting in there, make a Collection on TikTok and move them
into it first.

A public profile needs no sign-in. Your own collection does, so by default this
reads the session out of your running browser, the same way the downloader does.
Nothing is written to disk and no cookie file is created.

    --browser chrome|safari|firefox|brave|edge|chromium|vivaldi
    --no-cookies         public profiles and collections only
    --out recipes.json
    --append             add to an existing recipes.json instead of replacing it
    --limit N            stop after N posts, for a quick test

One thing TikTok will not give you. yt-dlp returns comment counts but not
comment text, so a recipe that a creator put in their own first comment is not
picked up the way it is on Instagram. On TikTok the recipe has to be in the
caption or in the video itself.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


def find_ytdlp(work="work"):
    # The venv wins over PATH on purpose. On macOS, Homebrew's yt-dlp is often
    # broken ("No module named expat"), and reference/setup.md tells people to
    # make a venv to get round it. Looking at PATH first would hand them the
    # broken one anyway and the venv would never get used.
    for p in (os.path.join(work, "venv/bin/yt-dlp"), "venv/bin/yt-dlp"):
        if os.path.isfile(p):
            return p
    return shutil.which("yt-dlp")


def fetch(url, ytdlp, browser, use_cookies, limit):
    cmd = [ytdlp, "--flat-playlist", "-J", "--no-warnings", "--ignore-errors",
           "--socket-timeout", "30"]
    if use_cookies:
        cmd += ["--cookies-from-browser", browser]
    if limit:
        cmd += ["--playlist-end", str(limit)]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True)
    if not p.stdout.strip():
        sys.stderr.write("\nyt-dlp returned nothing for %s\n" % url)
        tail = [l for l in p.stderr.strip().split("\n") if l.strip()][-6:]
        for l in tail:
            sys.stderr.write("  " + l + "\n")
        if use_cookies:
            sys.stderr.write(
                "\nIf that mentions cookies, close the browser and try again, or\n"
                "pass --browser with whichever browser you are signed in to.\n")
        else:
            sys.stderr.write(
                "\nA collection of your own needs your session. Drop --no-cookies.\n")
        return []
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        sys.stderr.write("could not read yt-dlp's output as JSON\n")
        return []
    entries = data.get("entries")
    return entries if entries is not None else [data]


def to_record(e, n):
    # `code` has to match what yt-dlp will name the downloaded file, because
    # watch.sh pairs transcripts to posts by that name. For TikTok that is the
    # numeric video id.
    vid = str(e.get("id") or "")
    user = e.get("uploader") or e.get("channel") or e.get("uploader_id") or ""
    url = e.get("url") or e.get("webpage_url") or (
        f"https://www.tiktok.com/@{user}/video/{vid}" if user and vid else "")
    # `title` is usually the description cut short, so prefer the description
    cap = e.get("description") or e.get("title") or ""
    return {
        "n": n,
        "id": vid,
        "code": vid,
        "user": user,
        "dur": int(e.get("duration") or 0),
        "taken": int(e.get("timestamp") or 0),
        "cap": cap,
        "own": [],      # TikTok comment text is not available through yt-dlp
        "top": [],
        "url": url,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Export a TikTok collection to recipes.json",
        epilog="Run with no arguments for the full notes at the top of this file.")
    ap.add_argument("urls", nargs="+", help="collection or profile URLs")
    ap.add_argument("--out", default="recipes.json")
    ap.add_argument("--browser", default="chrome")
    ap.add_argument("--no-cookies", action="store_true")
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--work", default="work")
    a = ap.parse_args()

    ytdlp = find_ytdlp(a.work)
    if not ytdlp:
        sys.stderr.write("yt-dlp not found. See reference/setup.md\n")
        return 1

    out = []
    if a.append and os.path.exists(a.out):
        out = json.load(open(a.out))
        print(f"appending to {len(out)} posts already in {a.out}")

    seen = {r.get("code") for r in out}
    for url in a.urls:
        print(f"reading {url}")
        entries = fetch(url, ytdlp, a.browser, not a.no_cookies, a.limit)
        added = 0
        for e in entries:
            if not e or not e.get("id") or str(e["id"]) in seen:
                continue
            out.append(to_record(e, len(out)))
            seen.add(str(e["id"]))
            added += 1
        print(f"  {added} posts")

    if not out:
        sys.stderr.write("nothing exported, so recipes.json was left alone\n")
        return 1

    for i, r in enumerate(out):      # keep n and position in step
        r["n"] = i
    json.dump(out, open(a.out, "w"), indent=1)

    with_text = sum(1 for r in out if len(r["cap"]) > 80)
    print(f"\nwrote {len(out)} posts to {a.out}")
    print(f"{with_text} have a caption long enough to hold a recipe. "
          "Run ./run.sh next and it will tell you the real split.")
    print("\nNote: TikTok comment text is not available, so a recipe left in "
          "the comments\nwill not be picked up. Caption or video only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
