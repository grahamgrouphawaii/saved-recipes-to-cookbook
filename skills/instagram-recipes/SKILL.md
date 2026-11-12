---
name: instagram-recipes
description: Turn a saved Instagram collection into a real recipe book. Pulls every post in one of the user's own saved collections, takes the recipe from the caption, from the creator's own comment, or by watching the video and transcribing it, then writes one markdown file per recipe, sorted into categories, each one linking back to the reel. Use when someone wants to get recipes out of their Instagram saves, build a cookbook from saved reels, or asks what is in their saved recipes folder. Also covers saved collections that are not food, since only the category list is food specific.
---

# Instagram saved collection to recipe book

Most of a saved recipe collection is already written down. The caption has the
ingredients, or the creator put them in the first comment. The rest only exist
in the video, where someone says "about two cups" over a shot of their hands.

So the job splits in two, and the whole point of this skill is to keep those two
apart. The written ones get built by scripts, at no token cost at all. Only the
ones that have to be watched reach you. On a 520 post collection that was 239
free and 281 watched, and the watched half cost about three percent of a weekly
Max allowance.

Work in batches, audit after every batch, and never invent a reel code.

## Before you start

Check the tools are there:

```bash
python3 --version && ffmpeg -version | head -1 && yt-dlp --version && whisper-cli --help 2>&1 | head -1
```

Anything missing, send the user to `reference/setup.md`. Python 3 and ffmpeg are
the only hard requirements. Without yt-dlp and whisper you can still build the
written half and list the rest as links to watch, which is worth saying out loud
rather than stopping.

Tell the user the plan and the rough cost before you begin, then start. If they
set a usage ceiling, check `mcp__ccd_session_mgmt__get_usage` between batches.

## 1. Export the collection

The export runs in the user's own browser on their own session. Do not try to
drive this with a browser tool, and do not export their cookies to a file. Give
them `scripts/export-collection.js` and the instructions at the top of it: open
the collection, open the console, paste, save `recipes.json`.

Ask them to put `recipes.json` in the working directory, then check it:

```bash
python3 -I -c "import json; d=json.load(open('recipes.json')); print(len(d),'posts'); print(d[0]['code'], d[0]['user'])"
```

If the user has Claude in Chrome connected and would rather you did it, you can
run the same fetches through `javascript_tool`. Two things bite if you do:
`Runtime.evaluate` gives up after about 45 seconds, so page in chunks and keep
state on `window`; and tool output truncates every string field at 1000
characters, so long captions have to come back split across several fields.

## 2. Triage

```bash
python3 -I <skill>/scripts/triage.py recipes.json
```

This scores the caption, the creator's own comments and the top comments for how
much they look like a followable recipe, and writes `data/text_tier.json`,
`data/video_tier.json` and `data/missing.json`. Report the split to the user. It
tells them what the job will cost before any of it is spent.

If the text tier looks too small, try `--threshold 5`. Too generous, `--threshold 8`.

## 3. Build the written half, free

```bash
python3 -I <skill>/scripts/autobuild.py recipes.json --out book
python3 -I <skill>/scripts/index.py --out book --title "<their name>'s Recipe Book"
python3 -I <skill>/scripts/audit.py recipes.json --out book --fix
```

That is a complete, readable book for every post whose creator wrote the recipe
down, and you have not spent a token on it. Show the user one finished recipe at
this point so they can see the format before the slow half starts.

`autobuild.py` also writes `data/needs_review.json`: the recipes where the title
rules came up with something like "Say YUM if you would eat this", or where the
ingredient list has no quantities anywhere in it. Fix those in one pass, reading
`caption_head` from that file. It is a line of text each, so fifty of them cost
less than one video.

## 4. Watch the rest

In batches of 40 to 60:

```bash
<skill>/scripts/watch.sh --data data --work work --start 0 --count 50
```

Downloads each reel, writes a transcript to `work/txt/<code>.txt` and up to ten
frames to `work/frames/<code>/`, then deletes the mp4. It skips anything already
done, so it is safe to stop and restart. All local, no tokens.

## 5. Write up the watched batch

Read the transcripts first, all of them at once:

```bash
for f in work/txt/*.txt; do echo "=== $(basename $f .txt)"; cat "$f"; done
```

Only open frames for a reel whose transcript is thin or silent. This single
habit is most of the cost difference: a transcript is a few hundred tokens, ten
frames are an order of magnitude more. Plenty of reels have no narration and put
everything on screen, and those genuinely need the frames, so look when you need
to and not otherwise.

Then write one JSON array, one object per recipe, and render it:

```bash
python3 -I <skill>/scripts/write_recipes.py batch1.json recipes.json --out book
python3 -I <skill>/scripts/audit.py recipes.json --out book --fix
```

Record shape, and the valid `cat` keys, are documented at the top of
`scripts/write_recipes.py`. Writing JSON instead of markdown keeps you off the
boilerplate, which is most of the per file cost.

Rebuild the index when the last batch lands.

## If you cannot look at the frames

Most reels come out of the transcript alone. Some creators narrate nothing and
put the whole recipe on screen as text, and those need the frames read. If
whatever is running this has no vision, pass `--no-frames` to `watch.sh` and
handle the silent ones honestly: write the file with `"src": "none"` and a note
saying the recipe is on screen in the video and has not been read, so the user
gets a titled entry and a watch link rather than a gap. Then tell them how many
ended that way. A partial result that says so is fine. An invented recipe is not.

## Hard rules

Never write a reel code you did not read out of `recipes.json`. A fabricated
shortcode is eleven characters that look exactly like the real eleven, and the
link is dead. This is the one mistake in this job that a reader cannot spot. Run
`audit.py --fix` after every batch and it cannot survive.

Say where every recipe came from. The `src` field puts a line at the top of each
file: the caption, the creator's own comment, the comments, or watching the
video. A reader always needs to know whether they are looking at the creator's
own words or at something transcribed from audio.

Never invent a quantity. A lot of creators say "some cheese" and nothing more.
Write what they said, add a note that the amounts are missing, and if you suggest
one, mark it as your estimate and not theirs.

Flag what looks wrong instead of smoothing it. Two tablespoons of baking soda in
a loaf of bread will taste of soap. A smoker set to "25" means 250. A pudding
set in the fridge from raw egg is not safe to eat, and honey is not safe under
one year old. Write the creator's number, then say plainly what you think and
why.

Account for everything. Deleted and private posts get a file saying so, not a
guess. A workout plan saved into a recipe folder gets an entry saying it is a
workout plan. If the index says 520 and the collection says 520, the user can
trust the whole thing.

Do not pad the method. If a creator gave four steps, the recipe has four steps.

## If something breaks

Collection fetch comes back empty: the post ids are the problem. Instagram's
numeric `pk` is larger than a JavaScript number holds exactly, so it rounds and
every later request 404s. Use `strong_id__` or the string `id`.

`yt-dlp` fails with "No module named expat": Homebrew's bundled Python is
missing it. Make a venv with the system Python and pip install yt-dlp there
rather than touching their Homebrew install.

A download is refused: that reel is private or gone. Record it in the book as
unavailable and move on.
