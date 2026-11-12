#!/usr/bin/env python3
"""
Write every text-tier recipe, with no model involved at all.

Titles come out of the caption. Creators nearly always put the dish name on its
own line near the top, often in capitals, and the lines that look like a title
but are really a hook or a call to action follow a small number of shapes.

Categories are decided on the title first and the caption second. That ordering
matters more than it sounds: half the savoury recipes in a collection contain
the word "juice" because they have lime in them, and matching anywhere in the
caption files them all under Drinks.

What cannot be decided mechanically is not guessed at. A caption whose title
comes out as "Say YUM if you would eat this" still gets a complete recipe file,
and its number goes into data/needs_review.json so a short model pass can
retitle just those, which is a line of text each rather than a whole recipe.

Usage:
    python3 autobuild.py recipes.json --out book [--data data]
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recipe_text as rt

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿️←-⇿⬀-⯿]+")

# looks like a title, is actually a hook, a CTA or a series marker
BAD_TITLE = re.compile(
    r"(full recipe|recipe below|save th|cookbook|comment\b|follow\b|worth the hype"
    r"|new post|part \d|episode|day \d+|link in bio|you need|i tried|pov\b|tag a\b"
    r"|rate th|try th|would eat th|f\*?[\w*]ck or|hype or|say\s*[\"“]|drop a\b"
    r"|written recipe|recipe in (the )?comment|did you know|whipped up|here.?s how"
    r"|watch (this|till)|wait for it|who else|am i the only)", re.I)

# a caption section header or a bare generic word is not a dish name
SECTION_START = re.compile(
    r"^\s*(ingredients?|macros?|method|instructions?|directions?|steps?|notes?|tips?"
    r"|for the\b|you(\'ll)? need|first\b|updated?|recipe|serves?\b|makes\b|calories?)\b",
    re.I)
GENERIC = {"recipe", "recipes", "new", "today", "yum", "food", "love food", "updated",
           "breakfast", "lunch", "dinner", "snack", "dessert", "easy", "quick", "good",
           "delicious", "so good", "this", "healthy"}


def deco(s):
    s = EMOJI.sub("", s)
    s = re.sub(r"^[\W_]+|[\W_]+$", "", s).strip()
    return re.sub(r"\s{2,}", " ", s)


def _unusable(t):
    """Is this title too poor to put at the top of a page?"""
    low = t.lower().strip(" .!?")
    if low in GENERIC or len(low) < 5:
        return True
    if SECTION_START.match(t) or BAD_TITLE.search(t):
        return True
    if "@" in t:
        return True
    if len(t.split()) > 7 and (t.endswith((".", "!", "?")) or rt.VERB.match(t)):
        return True
    return False


def title_for(rec):
    """Return (title, ok). ok is False when the title needs a human or a model."""
    lines = [x for x in (deco(l) for l in rt.clean(rec.get("cap", "")).split("\n")) if x]
    cands = []
    for l in lines[:8]:
        if BAD_TITLE.search(l) or SECTION_START.match(l) or not (4 <= len(l) <= 70):
            continue
        if rt.MEAS_RE.search(l):
            continue
        if l.endswith((".", "?")) and len(l.split()) > 9:
            continue
        cands.append(l)

    if cands:
        # an all-caps line among the candidates is nearly always the dish name
        caps = [c for c in cands if c.upper() == c and len(c.split()) > 1]
        t = caps[0] if caps else cands[0]
        if len(t) > 45:
            # only a spaced dash starts a subtitle; "high-protein" is one word
            t = re.sub(r"\s+[-–—|]\s+.*$", "", t)
        if t.upper() == t:
            t = t.title()
        t = t.strip()[:70]
        if not _unusable(t):
            return t, True
    else:
        t = next((l for l in lines[:12] if 4 < len(l) <= 90), "")
        t = t[:70] if t else ""

    return (t or "Untitled (@%s)" % rec.get("user", "unknown")), False


def cat_for(rec, title, cats):
    """
    Two passes. First the dish name, then the whole caption, each in the order
    the config gives. A title match always beats an anywhere match.
    """
    cap = rt.clean(rec.get("cap", ""))
    first = next((l for l in cap.split("\n") if l.strip()), "")
    head = f"{title}\n{first}"
    for key in cats["order"]:
        pat = cats.get("title_match", {}).get(key)
        if pat and re.search(pat, head, re.I):
            return key
    for key in cats["order"]:
        pat = cats.get("any_match", {}).get(key)
        if pat and re.search(pat, cap, re.I):
            return key
    return cats["fallback"]


def source_text(rec, src):
    if src == "own":
        return rt.clean("\n".join(rec.get("own") or []))
    if src == "top":
        return rt.clean("\n".join(c.get("t", "") for c in (rec.get("top") or [])))
    return rt.clean(rec.get("cap", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recipes")
    ap.add_argument("--out", required=True, help="book directory; recipes go in <out>/recipes")
    ap.add_argument("--data", default="data")
    ap.add_argument("--categories", default=None)
    a = ap.parse_args()

    data = json.load(open(a.recipes))
    for i, rec in enumerate(data):
        rec["n"] = i
    tier = json.load(open(f"{a.data}/text_tier.json"))
    cats = rt.load_categories(a.categories)

    outdir = os.path.join(a.out, "recipes")
    os.makedirs(outdir, exist_ok=True)

    metas, review, seen = [], [], {}
    for row in tier:
        rec = data[row["n"]]
        title, ok = title_for(rec)
        key = rt.slug(title)
        if key in seen:                       # two creators, same dish, one filename
            title = f"{title} (@{rec['user']})"
        seen[key] = True
        meta = {"n": row["n"], "title": title,
                "cat": cat_for(rec, title, cats), "src": row["src"],
                "body": source_text(rec, row["src"])}
        metas.append(meta)

        # Two things are worth a second look. A title the rules could not
        # trust, and an ingredient list with no quantities anywhere in it,
        # which means either the split went wrong or the creator never gave
        # any. Both are a line or two of work each, not a whole recipe.
        parts = rt.split_sections(meta["body"])
        no_amounts = bool(parts) and not rt.MEAS_RE.search(parts[1])
        if not ok or no_amounts:
            review.append({"n": row["n"], "guessed_title": title, "cat": meta["cat"],
                           "user": rec["user"],
                           "why": ("title" if not ok else "") +
                                  ("+" if (not ok and no_amounts) else "") +
                                  ("no quantities in the ingredients" if no_amounts else ""),
                           "caption_head": meta["body"][:220]})

    for meta in metas:
        rt.write(data[meta["n"]], meta, outdir, cats)

    store = f"{a.data}/built.json"
    have = json.load(open(store)) if os.path.exists(store) else []
    have = [x for x in have if x["n"] not in {m["n"] for m in metas}]
    have += [{k: v for k, v in m.items() if k != "body"} for m in metas]
    json.dump(sorted(have, key=lambda x: x["n"]), open(store, "w"), indent=0)
    json.dump(review, open(f"{a.data}/needs_review.json", "w"), indent=1)

    print(f"wrote {len(metas)} recipes with no model involved")
    print(Counter(cats["names"][m["cat"]] for m in metas).most_common())
    unsplit = sum(1 for m in metas if not rt.split_sections(m["body"]))
    if unsplit:
        print(f"{unsplit} had no clear ingredients/steps split, so the caption is "
              "printed as the creator wrote it")
    if review:
        print(f"{len(review)} got a title worth a second look -> "
              f"{a.data}/needs_review.json")


if __name__ == "__main__":
    main()
