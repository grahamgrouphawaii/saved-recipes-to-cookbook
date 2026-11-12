#!/usr/bin/env python3
"""
Sort every saved post into the cheapest lane that can actually produce a recipe.

This is the step that decides what the job costs. Scoring is pure regex, so
triaging a thousand posts is free, and it means the model is only ever asked
about the posts where there is genuinely nothing written down.

    text   the caption, or the creator's own comment, or a top comment
           already contains a usable recipe -> build it with no model at all
    video  the text is a title, a hype line or nothing -> the recipe only
           exists in the audio and on screen, so this one has to be watched
    none   the post is gone (deleted, private, or the fetch failed)

Usage:
    python3 triage.py recipes.json [--out data] [--threshold 6]
Writes data/text_tier.json, data/video_tier.json, data/triage_report.json
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recipe_text as rt


def score(txt):
    """How much like a followable recipe does this block of text look?"""
    if not txt or len(txt) < 40:
        return 0
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    s = 0
    if any(rt.ING_H.match(l) for l in lines):
        s += 3
    if any(rt.STEP_H.match(l) for l in lines):
        s += 3
    s += min(5, sum(1 for l in lines if rt.MEAS_RE.search(l)))
    s += min(4, sum(1 for l in lines if rt.VERB.match(l) and len(l.split()) >= 4))
    if sum(1 for l in lines if re.match(r"^\d+[\.\)]\s+\S", l)) >= 2:
        s += 2
    if len(txt) > 400:
        s += 1
    return s


def best_source(rec, threshold):
    """Return (source_key, text, score) for the best text we have, if any."""
    cands = [("caption", rt.clean(rec.get("cap", "")))]
    own = rec.get("own") or []
    if own:
        cands.append(("own", rt.clean("\n".join(own))))
    top = rec.get("top") or []
    if top:
        cands.append(("top", rt.clean("\n".join(c.get("t", "") for c in top))))
    scored = [(k, t, score(t)) for k, t in cands]
    scored.sort(key=lambda x: -x[2])
    k, t, sc = scored[0]
    return (k, t, sc) if sc >= threshold else (None, None, sc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recipes")
    ap.add_argument("--out", default="data")
    ap.add_argument("--threshold", type=int, default=6,
                    help="score needed to count the text as a usable recipe")
    a = ap.parse_args()

    data = json.load(open(a.recipes))
    # renumber defensively: everything downstream keys off n
    for i, rec in enumerate(data):
        rec["n"] = i

    os.makedirs(a.out, exist_ok=True)
    text, video, gone = [], [], []
    for rec in data:
        if not rec.get("code"):
            gone.append({"n": rec["n"], "user": rec.get("user", ""),
                         "why": rec.get("err", "no shortcode in the export")})
            continue
        k, _t, sc = best_source(rec, a.threshold)
        if k:
            text.append({"n": rec["n"], "src": k, "score": sc})
        else:
            video.append({"n": rec["n"], "code": rec["code"],
                          "user": rec.get("user", ""), "dur": rec.get("dur", 0),
                          "score": sc})

    json.dump(text, open(f"{a.out}/text_tier.json", "w"), indent=0)
    json.dump(video, open(f"{a.out}/video_tier.json", "w"), indent=0)
    json.dump(gone, open(f"{a.out}/missing.json", "w"), indent=1)

    mins = sum(max(20, r["dur"]) for r in video) / 60
    report = {
        "total": len(data),
        "text_tier": len(text),
        "video_tier": len(video),
        "missing": len(gone),
        "by_source": {k: sum(1 for r in text if r["src"] == k)
                      for k in ("caption", "own", "top")},
        "video_minutes": round(mins, 1),
    }
    json.dump(report, open(f"{a.out}/triage_report.json", "w"), indent=1)

    print(f"{report['total']} posts")
    print(f"  {report['text_tier']:>4} have a recipe in the text "
          f"(caption {report['by_source']['caption']}, "
          f"creator's comment {report['by_source']['own']}, "
          f"comments {report['by_source']['top']})  -> free to build")
    print(f"  {report['video_tier']:>4} need watching "
          f"({report['video_minutes']:.0f} min of video)")
    if gone:
        print(f"  {len(gone):>4} unreadable (deleted or private)")


if __name__ == "__main__":
    main()
