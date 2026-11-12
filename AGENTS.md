# Working on this repo, or running the job

Two different things, so check which one you are being asked for.

If someone wants their saved recipes turned into a book, you are running the
job. Read `skills/instagram-recipes/SKILL.md` and follow it. It is written in
Claude Code's skill format, so ignore the `---` block at the top and read the
rest; nothing in it is Claude specific.

If someone wants to change this tool, you are working on the repo, and the
section at the bottom applies.

## Running the job, in short

The point of the design is that most of the work is not model work. Do not read
captions yourself and write recipes out by hand. Run the scripts.

```bash
# 1. the user exports their collection themselves, in their own browser.
#    give them skills/instagram-recipes/scripts/export-collection.js and
#    the instructions at the top of it.
#    they end up with recipes.json.

# 2-3. triage, then build everything that is already written down. no model.
./run.sh recipes.json --out book --title "Recipe Book"

# 4. download and transcribe the rest, locally. no model. batches of ~50.
skills/instagram-recipes/scripts/watch.sh --data data --work work --start 0 --count 50

# 5. read work/txt/*.txt, write a JSON array of recipe records, render it
python3 -I skills/instagram-recipes/scripts/write_recipes.py batch1.json recipes.json --out book
python3 -I skills/instagram-recipes/scripts/audit.py recipes.json --out book --fix
```

Step 5 is the only part that needs you. The record shape and the valid category
keys are documented at the top of `skills/instagram-recipes/scripts/write_recipes.py`.

Two practical notes. The download step needs network access, so if your sandbox
blocks it, that step has to run with network enabled. And `run.sh` and
`watch.sh` are the cheap parts, so never substitute your own reading for them.

## If you cannot look at images

`watch.sh` writes a transcript and a few video frames per reel. Most reels are
solved from the transcript alone, but some creators narrate nothing and put the
whole recipe on screen as text. Those need the frames read.

If you have no vision, do this rather than guessing:

1. Pass `--no-frames` to `watch.sh`. It saves time and disk.
2. Write up every reel whose transcript carries a real recipe.
3. For the ones whose transcript is thin or silent, do not invent anything.
   Write the file with `"src": "none"` and a note saying the recipe is on screen
   in the video and has not been read yet, so the user gets a titled entry and a
   watch link instead of a gap.
4. Tell the user how many ended up that way, and that a vision capable model, or
   ten seconds of their own time per reel, would finish them.

That is an honest partial result. A made up recipe is not.

## Hard rules, whoever is running this

Never write an Instagram shortcode you did not read out of `recipes.json`. A
fabricated code is eleven characters that look exactly like the real eleven and
the link is dead, and it is the one error here a reader cannot catch. Run
`audit.py --fix` after every batch and it cannot survive.

Say where every recipe came from. The `src` field puts a line at the top of each
file. A reader needs to know whether they are reading the creator's own words or
something transcribed from audio.

Never invent a quantity. Plenty of creators say "some cheese" and nothing more.
Write what they said, note that the amounts are missing, and mark any suggestion
of your own as an estimate.

Flag what looks wrong instead of smoothing it. Two tablespoons of baking soda in
a loaf of bread will taste of soap. A smoker set to "25" means 250. A pudding
set in the fridge from raw egg is not safe to eat. Write the creator's number,
then say what you think and why.

Account for everything. Deleted posts get a file saying so. A workout plan saved
into a recipe folder gets an entry saying it is a workout plan. If the index
count matches the collection count, the book can be trusted.

## Working on the repo

`skills/instagram-recipes/reference/lessons.md` is the record of what went wrong the first time through.
Read it before changing the splitter, the titler or the categoriser, because
most of the obvious simplifications in those three are things that were already
tried and broke.

Keep the split that makes this cheap. Anything decidable by regex or by line
shape belongs in Python, not in a model's context. If you are adding a step that
sends text to a model, first check whether a rule would do it.

Adding a platform means writing one new exporter. Everything downstream reads
`recipes.json` and `work/txt/<id>.txt` and does not care where either came
from. The shape of a `recipes.json` record is in
`skills/instagram-recipes/scripts/export-collection.js`.

There are no tests yet. Verify a change by running the pipeline over a real
export and reading twenty output files, including some from
`data/needs_review.json`.
