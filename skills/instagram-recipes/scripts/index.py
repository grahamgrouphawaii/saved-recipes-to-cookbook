#!/usr/bin/env python3
"""
Build the book's README: a categorised index of every recipe file, each one
linking to the recipe and to the creator it came from.

Reads the files themselves rather than any metadata, so the index can never
disagree with what is actually in the book.

Usage:
    python3 index.py --out book [--title "My Recipe Book"]
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recipe_text as rt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Recipe Book")
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--categories", default=None)
    a = ap.parse_args()

    cats = rt.load_categories(a.categories)
    rd = os.path.join(a.out, "recipes")
    by_name = {v: k for k, v in cats["names"].items()}

    rows = []
    for fn in sorted(os.listdir(rd)):
        if not fn.endswith(".md"):
            continue
        t = open(os.path.join(rd, fn)).read()
        title = re.search(r"^# (.+)$", t, re.M)
        cat = re.search(r"^- \*\*Category:\*\* (.+?)\s*$", t, re.M)
        src = re.search(r"^- \*\*Source:\*\* \[@([^\]]+)\]\(([^)]+)\)", t, re.M)
        if not (title and cat):
            continue
        rows.append({"file": fn, "title": title.group(1).strip(),
                     "cat": cat.group(1).strip(),
                     "user": src.group(1) if src else "",
                     "url": src.group(2) if src else ""})

    by = {}
    for r in rows:
        by.setdefault(r["cat"], []).append(r)

    sub = a.subtitle or (
        f"{len(rows)} recipes saved on Instagram, written out from the captions, "
        "the creators' own comments, and the videos themselves.")
    L = [f"# {a.title}", "", sub, "",
         "Every recipe links back to the reel it came from, so you can watch it cook.",
         "", "## Contents", ""]

    ordered = [cats["names"][k] for k in cats["order"] if cats["names"][k] in by]
    ordered += [c for c in by if c not in ordered]
    for c in ordered:
        anchor = re.sub(r"[^a-z0-9 -]", "", c.lower()).replace(" ", "-")
        L.append(f"- [{c}](#{anchor}) — {len(by[c])} recipes")
    L.append("")

    for c in ordered:
        L += [f"## {c}", ""]
        key = by_name.get(c)
        if key and cats.get("blurbs", {}).get(key):
            L += [f"*{cats['blurbs'][key]}*", ""]
        for r in sorted(by[c], key=lambda x: x["title"].lower()):
            tail = f" — [@{r['user']}]({r['url']})" if r["user"] else ""
            L.append(f"- [{r['title']}](recipes/{r['file']}){tail}")
        L.append("")

    open(os.path.join(a.out, "README.md"), "w").write("\n".join(L).rstrip() + "\n")
    print(Counter(r["cat"] for r in rows).most_common())
    print("indexed", len(rows), "recipes")


if __name__ == "__main__":
    main()
