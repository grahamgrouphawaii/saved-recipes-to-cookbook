#!/usr/bin/env python3
"""
Turn model-written recipe records into recipe files.

This is the handoff for the video tier. After reading a transcript the model
writes plain JSON, one object per recipe, and this renders it in exactly the
same format the automatic text-tier files use. Writing JSON instead of markdown
keeps the model off the boilerplate, which is most of the token cost per file.

One record:

    {
      "n": 30,
      "title": "Tennessee Onions",
      "cat": "side",
      "src": "video",
      "yield": "a 9x13 dish",
      "ingredients": ["3 lb sweet onions, sliced thin", "**Spice blend**",
                      "2 tsp salt", "1 tsp smoked paprika"],
      "steps": ["Slice the onions thin on a mandolin, about 1/4 inch.",
                "Bake at 350F for 45 minutes covered, then 30 uncovered."],
      "note": "He never says how much cheese; a pound of each looked right."
    }

"cat" is a key from categories.json. "src" says where the steps came from:
caption, own, top, video, video+caption, or none. An ingredient line starting
with ** is treated as a sub-header, not an ingredient.

Usage:
    python3 write_recipes.py records.json recipes.json --out book [--data data]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recipe_text as rt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("records", help="JSON array of recipe records")
    ap.add_argument("recipes", help="recipes.json from the export")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default="data")
    ap.add_argument("--categories", default=None)
    a = ap.parse_args()

    data = json.load(open(a.recipes))
    for i, rec in enumerate(data):
        rec["n"] = i
    recs = json.load(open(a.records))
    cats = rt.load_categories(a.categories)
    outdir = os.path.join(a.out, "recipes")
    os.makedirs(outdir, exist_ok=True)

    bad = [r for r in recs if r.get("cat") not in cats["names"]]
    if bad:
        print("unknown category on n=" + ", ".join(str(r.get("n")) for r in bad), file=sys.stderr)
        print("valid: " + ", ".join(cats["names"]), file=sys.stderr)
        return 1

    written = []
    for r in recs:
        if not (0 <= r["n"] < len(data)):
            print(f"n={r['n']} is not in recipes.json, skipped", file=sys.stderr)
            continue
        r.setdefault("src", "video")
        written.append(rt.write(data[r["n"]], r, outdir, cats))

    store = f"{a.data}/built.json"
    have = json.load(open(store)) if os.path.exists(store) else []
    ns = {r["n"] for r in recs}
    have = [x for x in have if x["n"] not in ns]
    have += [{"n": r["n"], "title": r["title"], "cat": r["cat"], "src": r["src"]} for r in recs]
    os.makedirs(a.data, exist_ok=True)
    json.dump(sorted(have, key=lambda x: x["n"]), open(store, "w"), indent=0)

    print(f"wrote {len(written)} recipes ({len(have)} in the book so far)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
