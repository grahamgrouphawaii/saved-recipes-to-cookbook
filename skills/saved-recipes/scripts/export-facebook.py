#!/usr/bin/env python3
"""
Export saved Facebook posts into the same recipes.json the rest of the pipeline
reads.

Facebook is the awkward one of the three. There is no endpoint that lists what
you have saved, so this script does not go and find your saves by itself. You
give it Facebook post links and it turns them into records: the caption, the
author, the length and the date, one yt-dlp metadata call per post.

Three ways to hand it links.

    # whatever you have in front of you
    python3 export-facebook.py "https://www.facebook.com/reel/1008803898959659"

    # a file of links, one per line, which is what export-facebook.js writes
    python3 export-facebook.py --urls saved-urls.txt

    # a Download Your Information export, unzipped (or still zipped)
    python3 export-facebook.py --dyi ~/Downloads/facebook-yourname

For the saved list itself, either run scripts/export-facebook.js in your
browser console on facebook.com/saved, or ask Facebook for your data:
Settings -> Your information -> Download your information, pick JSON, and
include "Saved items and collections". The export takes anywhere from minutes
to hours to turn up.

WHAT FACEBOOK WILL NOT GIVE YOU

Comments. yt-dlp returns no comment text for Facebook and no comment count
either, and the comments are not in the page source for a script to read.
That matters more here than on the other two platforms, because the big
Facebook recipe pages deliberately put the recipe in the first comment and
leave the caption as a hook ("Full recipe in the comments"). Their reels run
six to nine seconds, so the recipe is not in the audio either. For those posts
there is nothing to extract and this will tell you so instead of inventing
something. Creators who write the recipe into the caption, or who narrate it,
come through fine.

The data in a DYI export is not used for anything except the links. Captions,
authors and dates all come from the live post, so Meta's double-encoded
mojibake in that file never reaches your recipes.

    --out recipes.json
    --append             add to an existing recipes.json instead of replacing it
    --browser chrome|safari|firefox|brave|edge|chromium|vivaldi
    --no-cookies         public posts only, no session read
    --limit N            stop after N links, for a quick test
    --batch N            links per yt-dlp call (default 20)
    --dry-run            list the links it found and stop
    --work work          where to look for work/venv/bin/yt-dlp
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from recipe_text import fold_lookalikes
except ImportError:          # the exporter still works on its own
    def fold_lookalikes(t):
        return t

# A Facebook link worth asking yt-dlp about. Saved items also include articles,
# marketplace listings, groups and events, and there is no point spending a
# request on those.
#
# Every branch demands an id. Facebook's own navigation is full of links like
# facebook.com/reel/ and facebook.com/watch/?ref=tab, which look like posts and
# are not, and a sloppier pattern collects a few of those off every page.
VIDEOISH = re.compile(
    r"https?://(?:www\.|web\.|m\.|mbasic\.)?facebook\.com/"
    r"(?:[^\s\"'<>/]+/)?"                          # optional page name
    r"(?:reel/\d+"
    r"|videos?/[\w%.-]+"
    r"|(?:video\.php|watch/?)\?[^\s\"'<>]*\bv=\d+"
    r"|(?:permalink|story)\.php\?[^\s\"'<>]*\bstory_fbid=[\w.-]+"
    r"|posts/[\w.-]+"
    r"|share/[rvp]/[\w-]+)"
    r"[^\s\"'<>\\]*"
    r"|https?://fb\.watch/[\w-]+/?", re.I)


def find_ytdlp(work="work"):
    # The venv wins over PATH on purpose. On macOS, Homebrew's yt-dlp is often
    # broken ("No module named expat"), and reference/setup.md tells people to
    # make a venv to get round it. Looking at PATH first would hand them the
    # broken one anyway and the venv would never get used.
    for p in (os.path.join(work, "venv/bin/yt-dlp"), "venv/bin/yt-dlp"):
        if os.path.isfile(p):
            return p
    return shutil.which("yt-dlp")


def clean_url(u):
    u = u.replace("\\/", "/").rstrip('\\",\'')
    u = re.sub(r"[&?](?:fbclid|mibextid|rdid|__cft__|__tn__|_rdr)[^&]*", "", u)
    return u.rstrip("&?")


def from_text(txt):
    # Meta's exports come out of PHP, which escapes every forward slash, so a
    # link in there reads https:\/\/www.facebook.com\/reel\/123. Undo that first
    # or the pattern below matches nothing at all.
    txt = txt.replace("\\/", "/")
    return [clean_url(m.group(0)) for m in VIDEOISH.finditer(txt)]


def harvest(path):
    """
    Pull Facebook links out of a Download Your Information export.

    Deliberately schema-blind. Meta has renamed and reshaped these files
    several times, so instead of reaching for a key like saves_v2 this reads
    every json, html and txt file in the export and keeps anything that looks
    like a link to a Facebook post. A layout change cannot break it, and the
    worst a stray match costs is one metadata request that comes back empty.
    """
    tmp = None
    if os.path.isfile(path) and path.lower().endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="fbdyi-")
        print(f"unzipping {os.path.basename(path)} ...")
        with zipfile.ZipFile(path) as z:
            z.extractall(tmp)
        path = tmp

    found, files = [], 0
    if os.path.isfile(path):
        walk = [(os.path.dirname(path), [], [os.path.basename(path)])]
    else:
        walk = os.walk(path)
    for root, _dirs, names in walk:
        for name in names:
            if not name.lower().endswith((".json", ".html", ".htm", ".txt")):
                continue
            files += 1
            try:
                with open(os.path.join(root, name), errors="replace") as fh:
                    found += from_text(fh.read())
            except OSError:
                continue
    print(f"read {files} files in the export")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return found


def fetch(urls, ytdlp, browser, use_cookies):
    """One yt-dlp call for a batch. Returns {original_url: info}."""
    cmd = [ytdlp, "-J", "--skip-download", "--no-warnings", "--ignore-errors",
           "--socket-timeout", "30"]
    if use_cookies:
        cmd += ["--cookies-from-browser", browser]
    cmd += urls
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = {}
    for line in p.stdout.split("\n"):
        line = line.strip()
        if not line or line == "null":      # a post it could not read
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and d.get("id"):
            out[d.get("original_url") or d.get("webpage_url") or ""] = d
    if not out and p.stderr:
        for l in [x for x in p.stderr.split("\n") if x.strip()][-3:]:
            sys.stderr.write("  " + l + "\n")
    return out, p.stderr or ""


def to_record(d, asked, n):
    # `code` has to match what yt-dlp will name the mp4, because watch.sh pairs
    # transcripts to posts by that name. For Facebook that is the numeric id.
    vid = str(d.get("id") or "")
    # Never fall back to `title`. Facebook builds it as
    # "110K views - 743 reactions | <caption> | <author>", which would put view
    # counts into recipe titles.
    cap = d.get("description") or ""
    url = asked or f"https://www.facebook.com/watch/?v={vid}"
    return {
        "n": n,
        "id": vid,
        "code": vid,
        "user": d.get("uploader") or d.get("channel") or "",
        "dur": int(d.get("duration") or 0),
        "taken": int(d.get("timestamp") or 0),
        "cap": cap,
        "own": [],      # Facebook comment text is not available, see above
        "top": [],
        "url": url,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Export saved Facebook posts to recipes.json",
        epilog="Run with no arguments for the full notes at the top of this file.")
    ap.add_argument("urls", nargs="*", help="Facebook post or reel URLs")
    ap.add_argument("--urls", dest="urlfile", help="file of URLs, one per line")
    ap.add_argument("--dyi", help="a Download Your Information export, folder or zip")
    ap.add_argument("--out", default="recipes.json")
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--browser", default="chrome")
    ap.add_argument("--no-cookies", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--work", default="work")
    a = ap.parse_args()

    links = list(a.urls)
    if a.urlfile:
        links += from_text(open(a.urlfile, errors="replace").read())
    if a.dyi:
        links += harvest(a.dyi)
    if not links:
        sys.stderr.write(
            "no Facebook links given. Pass some on the command line, or --urls "
            "a file,\nor --dyi your Download Your Information export.\n")
        return 1

    seen_link, uniq = set(), []
    for u in links:
        key = re.sub(r"[?#].*$", "", u).rstrip("/")
        if key not in seen_link:
            seen_link.add(key)
            uniq.append(u)
    print(f"{len(uniq)} Facebook links to look at")
    if a.limit:
        uniq = uniq[:a.limit]
    if a.dry_run:
        for u in uniq:
            print("  " + u)
        return 0

    ytdlp = find_ytdlp(a.work)
    if not ytdlp:
        sys.stderr.write("yt-dlp not found. See reference/setup.md\n")
        return 1

    out = []
    if a.append and os.path.exists(a.out):
        out = json.load(open(a.out))
        print(f"appending to {len(out)} posts already in {a.out}")
    seen_id = {str(r.get("code")) for r in out}

    gone, why = [], ""
    for i in range(0, len(uniq), max(1, a.batch)):
        chunk = uniq[i:i + max(1, a.batch)]
        got, err = fetch(chunk, ytdlp, a.browser, not a.no_cookies)
        why += err
        for asked in chunk:
            d = got.get(asked)
            if not d:
                gone.append(asked)
                continue
            if str(d["id"]) in seen_id:
                continue
            out.append(to_record(d, asked, len(out)))
            seen_id.add(str(d["id"]))
        print(f"  {min(i + len(chunk), len(uniq))}/{len(uniq)} read, "
              f"{len(out)} posts, {len(gone)} could not be read")

    if len(gone) == len(uniq):
        sys.stderr.write("\nEvery link failed, so %s was left alone.\n" % a.out)
        if "expat" in why:
            sys.stderr.write(
                "yt-dlp itself is broken, not your links. Homebrew's copy is "
                "missing a\nPython module. Build a venv next to your work "
                "folder and it will be used\nin preference to the one on your "
                "PATH:\n\n"
                "    python3 -m venv work/venv\n"
                "    work/venv/bin/pip install -q yt-dlp\n")
        elif "cookie" in why.lower():
            sys.stderr.write(
                "That looks like a cookie problem. Close the browser and try "
                "again, or\npass --browser for whichever one you are signed in "
                "to.\n")
        elif not a.no_cookies:
            sys.stderr.write(
                "If the errors above mention cookies, close the browser and try "
                "again,\nor pass --browser for the one you are signed in to.\n")
        return 1
    if not out:
        sys.stderr.write("\nnothing new to add, so %s was left alone\n" % a.out)
        return 1

    for i, r in enumerate(out):      # keep n and position in step
        r["n"] = i
    json.dump(out, open(a.out, "w"), indent=1)

    with_text = sum(1 for r in out if len(r["cap"]) > 80)
    # Count the ones that say the recipe is in the comments, in either word
    # order, after folding the lookalike letters creators use to dodge spam
    # filters ("Recipe in Firs\u03c4 Co\u028dm\u0435\u0578\u03c4").
    def hook(cap):
        t = fold_lookalikes(cap)
        return bool(re.search(r"recipe|ingredient", t, re.I)
                    and re.search(r"comment", t, re.I))
    # Only the Facebook ones. An Instagram caption that says "recipe in the
    # comments" is fine, because that comment can be read.
    hooks = sum(1 for r in out
                if "facebook.com" in (r.get("url") or "") and hook(r["cap"]))
    print(f"\nwrote {len(out)} posts to {a.out}")
    if gone:
        print(f"{len(gone)} links could not be read. Deleted, private, or not a "
              "video post.")
    print(f"{with_text} have a caption long enough to hold a recipe. "
          "Run ./run.sh next and it will tell you the real split.")
    if hooks:
        print(f"\nHeads up: {hooks} of these say the recipe is in the comments. "
              "Facebook\ncomment text cannot be read, so those will come out "
              "empty whatever you do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
