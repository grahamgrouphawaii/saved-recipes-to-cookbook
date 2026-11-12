#!/usr/bin/env python3
"""
Check the book against the export, and fix what can be fixed mechanically.

Run this after every batch, not once at the end. The failure it exists to catch
is the worst one available here: a plausible-looking Instagram link that was
never in the data. A wrong shortcode is eleven characters that look exactly like
the right eleven characters, and it fails silently until someone clicks it.

Checks:
  * every file's Source line matches the creator and shortcode in recipes.json
  * every file ends in a watch link, pointing at the same reel
  * every file in the book has a numeric prefix that exists in the export
  * no two files claim the same post
  * every recipe link in README.md resolves to a file that exists

--fix repairs the first two, which are purely mechanical. The rest are reported.

Usage:
    python3 audit.py recipes.json --out book [--fix]
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recipe_text as rt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recipes")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fix", action="store_true")
    a = ap.parse_args()

    data = json.load(open(a.recipes))
    for i, rec in enumerate(data):
        rec["n"] = i
    rd = os.path.join(a.out, "recipes")
    files = sorted(f for f in os.listdir(rd) if f.endswith(".md"))

    src_fixed = watch_fixed = 0
    problems, claimed = [], {}

    for fn in files:
        m = re.match(r"^(\d+)-", fn)
        if not m:
            problems.append(f"{fn}: filename has no leading post number")
            continue
        n = int(m.group(1))
        if n >= len(data):
            problems.append(f"{fn}: post {n} is not in the export")
            continue
        if n in claimed:
            problems.append(f"{fn}: post {n} is already written up in {claimed[n]}")
        claimed[n] = fn

        rec = data[n]
        p = os.path.join(rd, fn)
        t = open(p).read()
        url = rt.post_url(rec)

        want = f"- **Source:** [@{rec['user']}]({url})"
        found = re.search(r"^- \*\*Source:\*\* \[@[^\]]+\]\(https?://[^)]+\)", t, re.M)
        if not found:
            problems.append(f"{fn}: no Source line")
        elif found.group(0) != want:
            if a.fix:
                t = t[:found.start()] + want + t[found.end():]
                open(p, "w").write(t)
                src_fixed += 1
            else:
                problems.append(f"{fn}: Source line does not match the export")

        line = (f"---\n\n▶️ **Watch it:** {url}\n"
                f"(@{rec['user']} on Instagram)")
        if not t.rstrip().endswith(line):
            if a.fix:
                body = re.sub(r"\n*---\n\n▶️ \*\*Watch it:\*\*.*$", "",
                              t.rstrip(), flags=re.S).rstrip()
                open(p, "w").write(body + "\n\n" + line + "\n")
                watch_fixed += 1
            else:
                problems.append(f"{fn}: watch link missing or wrong")

    readme = os.path.join(a.out, "README.md")
    if os.path.exists(readme):
        for link in re.findall(r"\]\((recipes/[^)]+\.md)\)", open(readme).read()):
            if not os.path.exists(os.path.join(a.out, link)):
                problems.append(f"README links to {link}, which does not exist")

    print(f"{len(files)} recipe files, covering {len(claimed)} of {len(data)} saved posts")
    if a.fix:
        print(f"corrected {src_fixed} source links, {watch_fixed} watch links")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems[:60]:
            print("  " + p)
        if len(problems) > 60:
            print(f"  ... and {len(problems)-60} more")
        return 1
    print("no problems found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
