# Saved recipes to a real cookbook

I had 520 recipes saved on Instagram and no way to cook from any of them. You
know the problem. You save a reel, it goes into a folder, and six months later
you are scrolling a wall of thumbnails trying to remember which one was the
chicken thing.

This is a Claude Code skill that turns a saved collection into a folder of
markdown recipes, sorted into categories, each one linking back to the post it
came from. Instagram saved collections and TikTok collections both work.

It does the whole collection, including the posts where nobody wrote anything
down. Those get watched and transcribed.

## What you end up with

```
book/
├── README.md                       the index, by category
└── recipes/
    ├── 000-oh-my-days-cheesy-egg-bites.md
    ├── 030-tennessee-onions.md
    └── ...
```

One file per recipe. Ingredients, numbered steps, notes, a line at the top
saying where the recipe came from, and a watch link at the bottom.

```markdown
# Tennessee Onions

- **Category:** Dips, sides & snacks
- **Source:** [@thatguywywy](https://www.instagram.com/reel/DblPyFzgAX1/)
- **Steps from:** watching the video (narration and on-screen text)

## Ingredients

- 3 lb sweet onions, sliced thin

**Spice blend**
- 2 tsp salt
- 1 tsp smoked paprika
...
```

That one had a two word caption. The entire recipe came out of the audio.

## Why it doesn't cost much to run

This is the part I actually care about. Watching 300 videos with an AI should be
expensive, and a lot of tools like this are.

Three things keep it cheap.

Most of the work isn't AI work. Scoring captions, splitting ingredients from
method, titling, categorising, building files, checking links: all of that is
regex and Python, running locally, costing nothing. On my collection that
finished 239 of 520 recipes before Claude was asked a single question.

Transcription is local too. Videos get downloaded with yt-dlp and transcribed
with whisper.cpp on your own machine. No API, no per minute charge.

Claude only reads the transcripts, and only looks at video frames when a
transcript comes back thin or silent. A transcript is a few hundred tokens. Ten
frames is a lot more than that.

My 520 post collection cost about three percent of a weekly Claude Max
allowance, start to finish. I had guessed 45 to 60 percent before I measured it,
so take the number as what happened to me and not as a promise.

## Installing it

You need Python 3 and ffmpeg. For the videos you also need yt-dlp and
whisper.cpp, both free. `skills/saved-recipes/reference/setup.md` has the
commands for macOS and Linux.

```bash
git clone https://github.com/grahamgrouphawaii/saved-recipes-to-cookbook
cd saved-recipes-to-cookbook
./install.sh
```

That copies the skill into `~/.claude/skills/`. Then open Claude Code and say:

> build a recipe book from my saved Instagram recipes

On claude.ai you can zip the `skills/saved-recipes` folder and upload it as
a skill instead.

## Using it without Claude, or with a different agent

Half the job needs no AI, and you can run that half yourself:

```bash
./run.sh recipes.json --out book --title "My Recipe Book"
```

That triages the export, builds every recipe whose creator wrote it down,
indexes the lot and checks every link. It then tells you how many reels are
left to watch. On my collection that one command finished 239 of 520 recipes.

For the watched half, any agent will do. There's an `AGENTS.md` in the root, so
Codex and anything else that reads that convention picks up the same
instructions. The scripts are plain Python 3 and bash with no Claude dependency
anywhere, so they run on Linux or a VPS just as well as on a Mac.

One caveat if you're using something other than Claude Code. Most reels get
solved from the transcript alone, but the silent ones put the recipe on screen
as text, and reading those needs a model that can look at images. `AGENTS.md`
says what to do when it can't: those get a titled entry, a watch link and a note
saying the recipe hasn't been read, instead of a guess. Test on five before
pointing anything at three hundred.

## TikTok

TikTok is one command, with no console script at all:

```bash
python3 -I skills/saved-recipes/scripts/export-tiktok.py \
  "https://www.tiktok.com/@you/collection/Recipes-7312345678901234567"
```

Get that URL from your profile, the saved tab, Collections, then the collection
you want. Add `--append` and it merges into an existing `recipes.json`, so your
Instagram and TikTok saves can end up in one book.

Two honest caveats. TikTok's loose Favorites list, the ungrouped bookmarks,
can't be read this way, so move those into a Collection on TikTok first. And
TikTok doesn't hand over comment text, only comment counts, so a recipe a
creator left in their first comment gets picked up on Instagram and missed on
TikTok.

Expect TikTok to lean much harder on the video half. Instagram creators write
the recipe in the caption because their audience expects it. TikTok creators
mostly write the dish name and nine hashtags and say the recipe out loud. I
tested one public cooking account and all eight posts went to the video tier:
the caption was "Lobster Bisque" plus hashtags, and the transcript had the
quantities, the butter, the pan temperature, all of it. So TikTok works, it just
costs more per recipe than Instagram.

## How your login is handled

Your password never goes anywhere near this, and neither do your cookies.

On Instagram, reading the collection happens in your browser, not in the tool. You open your
saved collection, open the developer console, and paste in one script. It uses
the session you are already signed in with, calls only instagram.com, and hands
you a `recipes.json` file through your browser's normal download prompt. You can
read the whole script first. It's about a hundred lines and it is commented.

On TikTok there is no script to paste. Reading your own collection and
downloading the videos both use `yt-dlp --cookies-from-browser`, which reads
your session straight out of the running browser and keeps it in memory. No
cookie file gets written, so there is nothing sitting on disk to leak. Public
collections need no sign-in at all.

It only reads your own saves. There is nothing in here that touches anyone
else's account, and nothing that posts, likes, follows or sends.

## What it gets wrong

I would rather tell you than have you find out.

Titles. Creators put all sorts of things on the first line. "Say YUM if you
would eat this." "Hype or Hoax, Episode 260." The rules catch most of it, and
everything they can't trust goes into `data/needs_review.json` so a short pass
can fix just those. On my collection that was 50 out of 239.

Quantities. Plenty of creators never say how much. Those recipes say so. If an
amount is a guess, the file says it's a guess.

Deleted posts. Six of mine had been taken down or made private since I saved
them. Those get a file saying that, rather than an invented recipe.

Comments. On Instagram a recipe in the first comment gets picked up, though one
buried in a reply to a comment does not. On TikTok no comment text is available
at all.

Categories. The default six are food ones: sweets, light and high protein, mains,
dips and sides, baking, drinks. Edit `scripts/categories.json` to re-cut it, or
rewrite them entirely if your collection isn't food.

## It's their data, not mine and not yours

The recipes belong to the people who posted them. This builds you a private,
searchable copy of things you already saved, with a link back to every creator
so you can go and watch, follow or credit them. Don't republish someone's recipe
as your own, and don't point this at saves that aren't yours.

Instagram's private endpoints change without warning, and TikTok's are read
through yt-dlp, which has to keep up with them. If an export stops working,
that's why. Updating yt-dlp is the first thing to try.

## Licence

MIT. See LICENSE.
