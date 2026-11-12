"""
Shared text handling for the saved-recipe pipeline.

Captions are written for a feed, not for a cookbook. They carry calls to
action, hashtag walls, emoji dividers and promo lines, and the ingredients and
the method are often run together with no headers. Everything here is about
getting from that to something you can cook from, without inventing anything
that the creator did not write.

Nothing in this file calls a model. It is all regex and line shape, which is
why running it over a few hundred posts costs nothing.
"""

import json
import os
import re

# --------------------------------------------------------------------------
# cleaning
# --------------------------------------------------------------------------

PROMO = re.compile(r"""(
 comment\s*["“”']?\w+["“”']?\s*(below|and|for|to\b)
|link\s+in\s+(my\s+)?bio
|follow\s+(me\s+|us\s+)?for\s+more
|save\s+th(is|ese)\b
|my\s+(digital\s+)?cookbook
|newsletter
|^\s*announcements?\s*:?\s*$
|grab\s+yours
|app\s+store
|google\s+play
|discount\s+code
|use\s+code\s+\w+
|\bDM\s+me\b
|share\s+this\s+with
|tag\s+someone
|double\s+tap
|hit\s+the\s+follow
|secure\s+your\s+spot
|waitlist
|free\s+(guide|ebook|plan)\b
|join\s+my\b
|coaching\b
|sign\s+up\b
)""", re.I | re.X)

MEAS_RE = re.compile(
    r"\b\d+([\.,/]\d+)?\s*(g|kg|oz|ml|l|lb|lbs|cup|cups|tbsp|tbs|tsp|teaspoons?"
    r"|tablespoons?|cloves?|slices?|cans?|sticks?|pcs?|pieces?)\b"
    r"|^[\d¼-¾⅐-⅞]", re.I)

BULLET_CHARS = "-•*▢✅\U0001f525\U0001f449\U0001f963\U0001f6d2▸·"

EMO = r"[^\w\n]{0,6}"
ING_H = re.compile(r"^\s*" + EMO + r"(ingredients?|what you(\'ll)? need|you(\'ll)? need"
                   r"|shopping list|recipe)\b.{0,40}$", re.I)
STEP_H = re.compile(r"^\s*" + EMO + r"(method|instructions?|directions?|steps?|how to\b"
                    r"|process|preparation)\b.{0,40}$", re.I)
MACRO_H = re.compile(r"^\s*" + EMO + r"(macros?\b|calories?\b|nutrition\b|verdict\b"
                     r"|notes?\b|tips?\b).{0,60}$", re.I)

# "Full Recipe", "Ingredients", "You'll need" and friends, allowing a little
# leading decoration and a trailing "(makes 2)". Looser than ING_H on purpose:
# ING_H has to anchor the word at the start, this one only needs it in a short line.
LOOSE_ING_H = re.compile(
    r"^.{0,8}?\b(full\s+recipe|recipe|ingredients?|what you(\'ll)? need"
    r"|you(\'ll)? need|shopping list)\b.{0,30}$", re.I)

VERB = re.compile(
    r"^\s*(?:\d+[\.\)]\s*)?(preheat|heat|mix|combine|add|place|bake|cook|stir|whisk|blend"
    r"|pour|melt|season|cut|chop|slice|dice|divide|roll|fold|spread|layer|transfer|remove"
    r"|serve|boil|simmer|fry|grill|arrange|coat|brush|top|drain|rinse|marinate|refrigerate"
    r"|freeze|let\s|bring|set\s|wrap|press|shape|knead|scoop|dip|sprinkle|garnish|assemble"
    r"|repeat|cover|grease|line\s|prepare|toss|crack|beat|pulse|air\s?fry|in\s+a\b|on\s+a\b"
    r"|once\b|when\b|while\b|then\b|next\b|finally\b|start|begin)\b", re.I)


REFLOW_H = re.compile(
    r"\s*\b((?:full\s+)?ingredients?|method|instructions?|directions?|steps?"
    r"|you\'?ll need|what you need|macros?|notes?|tips?)\s*:", re.I)


def reflow(txt):
    """
    Put line breaks back into a caption that arrived as one long line.

    Instagram keeps the creator's line breaks. TikTok often does not, and a
    recipe as one unbroken paragraph defeats every rule downstream, because all
    of them work on the shape of a line. So when a caption has almost no breaks
    in it, split at the markers that are unambiguous: a section header followed
    by a colon, a numbered step, a bullet. Anything less certain than that is
    left alone, since a wrong break reads as a wrong ingredient.
    """
    if txt.count("\n") >= 3 or len(txt) < 120:
        return txt
    s = REFLOW_H.sub(lambda m: "\n" + m.group(1) + ":\n", txt)
    s = re.sub(r"\s+(?=\d{1,2}[\.\)]\s+[A-Za-z])", "\n", s)
    # a bullet glyph, or a hyphen that is followed by a word rather than a number
    s = re.sub(r"\s+(?=[•▢✅·‣▸]\s*\w)", "\n", s)
    s = re.sub(r"\s+(?=-\s+[A-Za-z])", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


# Creators dodge spam filters by swapping single letters for lookalikes from
# another alphabet, so a caption reads "Recipe in Firsτ Coʍmеոτ". It is common on
# Facebook and it happens on Instagram too. Left alone, a line like that slips
# past every pattern below and can end up as a recipe title.
#
# Only mixed-script words are folded. A word with no ASCII letter in it is
# left exactly as it is, so a caption genuinely written in Greek, Russian or
# Armenian is never touched.
LOOKALIKE = {
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0441": "c", "\u0440": "p",
    "\u0445": "x", "\u0456": "i", "\u0455": "s", "\u0443": "y", "\u043c": "m",
    "\u043a": "k", "\u0432": "b", "\u0433": "r", "\u0442": "t", "\u043d": "h",
    "\u0501": "d", "\u0475": "v", "\u0458": "j", "\u051b": "q", "\u0501": "d",
    "\u03bf": "o", "\u03bd": "v", "\u03c4": "t", "\u03c1": "p", "\u03b1": "a",
    "\u03b5": "e", "\u03b9": "i", "\u03ba": "k", "\u03f2": "c", "\u03c5": "u",
    # IPA letters only here. A real alphabet letter such as Turkish \u0131 is left
    # out on purpose: Kazand\u0131b\u0131 is spelled that way and should stay that way.
    "\u028d": "m", "\u0251": "a", "\u0261": "g", "\u026a": "i",
    "\u057d": "u", "\u0578": "n", "\u0561": "w", "\u0574": "d",
    "\u0399": "I", "\u0391": "A", "\u0395": "E", "\u039f": "O", "\u03a1": "P",
    "\u03a4": "T", "\u03a7": "X", "\u039d": "N", "\u039c": "M", "\u039a": "K",
    "\u0392": "B", "\u041d": "H", "\u0410": "A", "\u0415": "E", "\u041e": "O",
    "\u0421": "C", "\u0422": "T", "\u0412": "B", "\u041c": "M", "\u041a": "K",
}
HAS_ASCII = re.compile(r"[A-Za-z]")


def fold_lookalikes(txt):
    """Put the swapped-out letters back, word by word, Latin words only."""
    if txt.isascii():
        return txt
    parts = re.split(r"(\s+)", txt)
    for i, w in enumerate(parts):
        if w and not w.isascii() and HAS_ASCII.search(w):
            parts[i] = "".join(LOOKALIKE.get(c, c) for c in w)
    return "".join(parts)


def clean(cap):
    """Strip hashtag walls, promo lines and emoji dividers from a caption."""
    cap = reflow(fold_lookalikes(cap))
    out = []
    for ln in cap.split("\n"):
        s = ln.strip()
        if s and all(w.startswith("#") for w in s.split()):
            continue
        if s in {".", "·", "•", "—", "-", "*", "_"}:
            continue
        if PROMO.search(s):
            continue
        s = re.sub(r"(\s+#[\w一-鿿]+)+\s*$", "", s)
        out.append(s)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def _ing_like(ln):
    s = ln.strip()
    if not s:
        return True
    if len(s) > 95:
        return False
    if s[0] in BULLET_CHARS:
        return True
    if MEAS_RE.search(s):
        return True
    if VERB.match(s) and len(s.split()) >= 3:
        return False
    return len(s.split()) <= 9


def trim_ingredient_head(block):
    """
    Drop preamble from the top of an ingredient block.

    When a caption has no ingredients header we have to guess where the list
    starts, and a title line or a paragraph of "my kids loved this" usually
    sits above it. An ingredient list in practice always opens on a quantity,
    a bullet, or a short sub-header like "For the sauce".
    """
    il = block.split("\n")
    while il:
        s = il[0].strip()
        if not s:
            il.pop(0)
            continue
        if MEAS_RE.search(s) or s[0] in BULLET_CHARS:
            break
        if len(s.split()) <= 6 and len(s) <= 45 and not s.endswith((".", "!", "?")):
            break                      # short label, probably a sub-header
        il.pop(0)
    return "\n".join(il)


def _last_ing_header(head):
    """Index of the last ingredients-ish header line in `head`, or None."""
    found = None
    for i, ln in enumerate(head):
        s = ln.strip()
        if s and len(s) <= 50 and LOOSE_ING_H.match(s):
            found = i
    return found


def split_sections(txt):
    """
    Split cleaned caption text into (intro, ingredients, steps, notes).
    Returns None when the text has no recognisable split, in which case the
    caller should print the caption as-is rather than guess at a structure.

    Captions come in four shapes and all four turn up constantly:
      1. both an ingredients header and a method header
      2. only a method header, ingredients listed above it bare
      3. no headers, but the method starts at a line beginning "1."
      4. no headers at all, method starts at the first verb-led line
    """
    lines = txt.split("\n")
    idx_i = idx_s = None
    for i, ln in enumerate(lines):
        if idx_i is None and ING_H.match(ln):
            idx_i = i
        if idx_s is None and STEP_H.match(ln):
            idx_s = i

    if idx_i is not None and idx_s is not None and idx_s > idx_i:
        intro = "\n".join(lines[:idx_i])
        ing = "\n".join(lines[idx_i + 1:idx_s])
        rest = "\n".join(lines[idx_s + 1:])
    elif idx_s is not None:
        head = lines[:idx_s]
        hdr = _last_ing_header(head)
        if hdr is not None:
            start = hdr + 1
        else:
            # no header, so walk down until the lines start looking like a list
            start = 0
            for i, ln in enumerate(head):
                if not _ing_like(ln) or not ln.strip():
                    start = i + 1
                else:
                    break
        intro = "\n".join(head[:start])
        ing = "\n".join(head[start:])
        rest = "\n".join(lines[idx_s + 1:])
    else:
        cut = None
        for i, ln in enumerate(lines):
            if re.match(r"^\s*1[\.\)]\s+\S", ln):
                cut = i
                break
        if cut is None:
            for i in range(idx_i + 1 if idx_i is not None else 0, len(lines)):
                if lines[i].strip() and not _ing_like(lines[i]) and VERB.match(lines[i]):
                    cut = i
                    break
        if cut is None:
            return None
        head = lines[:cut]
        hdr = _last_ing_header(head)
        start = hdr + 1 if hdr is not None else 0
        if start == 0:
            for i, ln in enumerate(head):
                if ln.strip() and _ing_like(ln):
                    start = i
                    break
        intro = "\n".join(head[:start])
        ing = "\n".join(head[start:])
        rest = "\n".join(lines[cut:])

    ing = trim_ingredient_head(ing)

    if not ing.strip() or not rest.strip():
        return None

    rl = rest.split("\n")
    mcut = next((i for i, ln in enumerate(rl) if MACRO_H.match(ln)), None)
    if mcut is not None:
        steps, notes = "\n".join(rl[:mcut]).strip(), "\n".join(rl[mcut:]).strip()
    else:
        steps, notes = rest.strip(), ""
    return intro.strip(), ing.strip(), steps, notes


def drop_title_line(block, title):
    """Remove a leading line that is only the recipe title over again."""
    def norm(s):
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    tn = norm(title)
    lines = block.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and tn and norm(lines[0]) in (tn, tn.rstrip("s")):
        lines.pop(0)
    return "\n".join(lines).lstrip("\n")


UNIT = (r"g|kg|oz|ml|l|lb|lbs|cup|cups|tbsp|tbs|tsp|teaspoons?|tablespoons?"
        r"|cloves?|slices?|cans?|sticks?|pcs?|pieces?|scoops?")
# a quantity that starts a new item, i.e. one that follows a word rather than
# another number, so "2 1/2 cups flour" is left whole
RUN_ON = re.compile(r"(?<=[a-z\)’])\s+(?=\d+(?:[\./]\d+)?\s*(?:" + UNIT + r")\b)", re.I)


def split_run_on(block):
    """
    Break an ingredient line that is really several ingredients run together.

    Only applied to the ingredients block, and only to a line carrying three or
    more quantities, because that is the shape of a list that lost its newlines
    rather than of a sentence. A step like "simmer for 3 minutes" never matches,
    since minutes is not a unit of measure.
    """
    out = []
    for ln in block.split("\n"):
        if len(ln) > 60 and len(re.findall(MEAS_RE, ln)) >= 3:
            out.extend(x.strip() for x in RUN_ON.split(ln) if x and x.strip())
        else:
            out.append(ln)
    return "\n".join(out)


def bulletize(block):
    """
    Render an ingredient block as a markdown list. A short line with no
    quantity that is followed by a quantity line is a sub-header ("For the
    sauce"), not an ingredient, so it is bolded instead of bulleted.
    """
    lines, out = block.split("\n"), []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            out.append("")
            continue
        bulleted = s[0] in BULLET_CHARS
        s2 = re.sub(r"^[" + re.escape(BULLET_CHARS) + r"]\s*", "", s)
        if (not MEAS_RE.search(s2) and not bulleted and len(s2.split()) <= 5
                and not s2.endswith((".", "!", "?"))):
            nxt = next((x.strip() for x in lines[i + 1:] if x.strip()), "")
            nxt = re.sub(r"^[" + re.escape(BULLET_CHARS) + r"]\s*", "", nxt)
            if MEAS_RE.search(nxt):
                pad = "" if not out or out[-1] == "" else "\n"
                out.append(pad + "**" + s2.rstrip(":") + "**")
                continue
        out.append("- " + s2)
    return "\n".join(out)


def numberize(block):
    """Renumber a method block as 1..n, dropping whatever numbering it had."""
    out, n = [], 1
    for ln in block.split("\n"):
        s = re.sub(r"^\s*(\d+[\.\)]|[" + re.escape(BULLET_CHARS) + r"])\s*", "", ln.strip())
        if not s:
            continue
        out.append(f"{n}. {s}")
        n += 1
    return "\n".join(out)


def post_url(rec):
    """
    Where this post lives. Exporters write a `url` field; the Instagram
    exporter did not always, so fall back to building a reel link from the
    shortcode for the sake of collections exported before that was added.
    """
    return rec.get("url") or f"https://www.instagram.com/reel/{rec['code']}/"


def slug(t):
    s = re.sub(r"[^\w\s-]", "", t.lower())
    return re.sub(r"[\s_]+", "-", s).strip("-")[:60] or "untitled"


# --------------------------------------------------------------------------
# categories
# --------------------------------------------------------------------------

def load_categories(path=None):
    here = os.path.dirname(os.path.abspath(__file__))
    path = path or os.path.join(here, "categories.json")
    return json.load(open(path))


# --------------------------------------------------------------------------
# rendering one recipe file
# --------------------------------------------------------------------------

PROVENANCE = {
    "caption": "the caption",
    "own": "the creator's own comment",
    "top": "the comments",
    "video": "watching the video (narration and on-screen text)",
    "video+caption": "the caption plus watching the video",
    "none": "nothing recoverable",
}


def render(rec, meta, cats):
    """
    Build the markdown for one recipe.

    `rec` is the raw post from recipes.json. `meta` is what we worked out about
    it: title, cat, src, and then either pre-split caption sections or explicit
    ingredients/steps lists. Every file states where its steps came from, so a
    reader always knows whether they are looking at the creator's own words or
    at something transcribed from audio.
    """
    url = post_url(rec)
    cat = cats["names"][meta["cat"]]
    L = [f"# {meta['title']}", ""]
    L.append(f"- **Category:** {cat}")
    L.append(f"- **Source:** [@{rec['user']}]({url})")
    if meta.get("yield"):
        L.append(f"- **Makes:** {meta['yield']}")
    L.append("- **Steps from:** " + PROVENANCE.get(meta.get("src", "caption"), meta["src"]))
    L.append("")

    if meta.get("ingredients") or meta.get("steps"):
        if meta.get("ingredients"):
            L += ["## Ingredients", ""]
            # a "**For the sauce**" style sub-header passes through unbulleted,
            # with a blank line so markdown does not fold it into the list above
            for ln in meta["ingredients"]:
                if ln.startswith("**"):
                    if L and L[-1] != "":
                        L.append("")
                    L.append(ln)
                    L.append("")
                else:
                    L.append(ln if ln.startswith("-") else f"- {ln}")
            L.append("")
        if meta.get("steps"):
            L += ["## Steps", ""]
            L += [f"{i+1}. {s}" for i, s in enumerate(meta["steps"])]
            L.append("")
    else:
        body = meta.get("body", "")
        parts = split_sections(body)
        if parts:
            _intro, ing, steps, notes = parts
            # the title line can hide a paragraph of preamble behind it, so
            # trim again once the title itself is out of the way
            ing = split_run_on(
                trim_ingredient_head(drop_title_line(ing, meta["title"])))
            L += ["## Ingredients", "", bulletize(ing), "",
                  "## Steps", "", numberize(steps), ""]
            if notes.strip():
                L += ["## Notes", "", notes.strip(), ""]
        else:
            L += ["## Recipe (as the creator wrote it)", "", body, ""]

    if meta.get("note"):
        L += ["## Notes", "", meta["note"], ""]

    L += ["---", "", f"▶️ **Watch it:** {url}", f"(@{rec['user']} on Instagram)"]
    return "\n".join(L).rstrip() + "\n"


def write(rec, meta, outdir, cats):
    fn = f"{meta['n']:03d}-{slug(meta['title'])}.md"
    with open(os.path.join(outdir, fn), "w") as f:
        f.write(render(rec, meta, cats))
    return fn
