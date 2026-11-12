# Things that went wrong the first time

Written down after doing this once on a 520 post collection, so the next person
does not have to find them out.

## Instagram's post ids do not survive JavaScript

The `pk` field is a 64 bit integer. A JavaScript number cannot hold it exactly,
so reading it rounds the last digits and every comment request built from it
comes back `{"status":"ok"}` with no comments and no error. Use `strong_id__`,
or the string `id` with the part after the underscore removed.

This cost an hour because the failure looks like "this post has no comments"
rather than like a bug.

## The saved grid is not made of links

Scraping the collection page for post URLs returns nothing. The tiles are not
`<a>` elements. Use `/api/v1/feed/collection/{id}/posts/` with the
`X-IG-App-ID` header, which is what the page itself does.

## Fabricated shortcodes are the real danger

Writing up a batch from transcripts, it is easy to put an Instagram link in a
file from memory rather than from the data. Eleven characters of base64 look
exactly as plausible wrong as right, and nothing downstream complains. Fourteen
links were wrong the first time through this.

`audit.py` exists only because of this. Run it after every batch. It compares
every file's source line against the export and rewrites any that do not match.

## Reading frames is where the money goes

Transcribing locally is free. Reading ten video frames per reel is not, and it
is most of what a job like this costs. Read the transcript first and only open
frames when the transcript is thin or silent. Doing it that way turned an
estimated 45 to 60 percent of a weekly allowance into about three.

A guess made before measuring was off by roughly ten times, in the expensive
direction. Measure a batch of twenty before promising anyone a number.

## Captions come in four shapes

An ingredients header and a method header. Only a method header. No headers but
a line starting "1.". No headers at all, method starting at the first verb. All
four are common, and a splitter that only handles the first one gets about a
quarter of a collection.

## A line that looks like a title usually isn't

"Full Recipe", "Say YUM if you would eat this", "Hype or Hoax, Episode 260",
"INGREDIENTS", "8oz mozzarella cheese". Blacklisting phrases goes a certain
distance. Structural tests go further: a caption section word, an @ handle, a
sentence longer than seven words, a single generic word. What the rules cannot
trust should be flagged rather than guessed at.

## Matching categories anywhere in the caption fails

Half the savoury recipes in a collection have lime in them, so matching
"juice" anywhere files chicken bowls under Drinks. 24 of 239 were wrong this
way. Match the dish name, which is the title and the first line, and keep
anywhere matching for properties like macros that are not dish names.

## Two creators, one dish, one filename

Two posts titled "Protein Cheesecake" overwrite each other and the count
quietly comes up short. Append the creator's handle to the second one.

## A recipe with no quantities is a finding, not a failure

Plenty of creators genuinely never say how much. Writing an amount in to make
the page look finished is the worst thing this tool can do, because it reads as
the creator's own number. Say the amounts are missing. Mark any suggestion as
an estimate.

## Judgment calls worth flagging rather than smoothing

Real examples from one collection:

- Two tablespoons of baking soda in a loaf of bread. Will taste of soap, almost
  certainly meant teaspoons.
- "Turn your smoker to 25." Means 250.
- A protein pudding that sets in the fridge from raw egg. Not food safe.
- Watermelon gummies sweetened with honey. Not safe under one year old.
- Raw salmon from a warehouse store. The creator's own caveat was worth
  repeating, not dropping.

Write what the creator said, then say what you think and why. Do not silently
correct someone's recipe, and do not silently pass on something that will make
a reader ill.

## Account for every post

Six posts had been deleted or made private between saving and reading. Two were
not recipes at all: a workout plan and a comedy clip, saved into the folder by
mistake. All eight got entries saying what they were. If the index count and
the collection count agree, the reader can trust the book.

## TikTok is a different shape of problem, not a harder one

Three things found while adding it.

yt-dlp understands TikTok collection URLs directly and returns the caption, the
duration and the post date in one metadata call, so TikTok needs no browser
console script. In that respect it is easier than Instagram, where the
equivalent extractor is marked broken and the collection has to be read through
the site's own private endpoint.

TikTok captions arrive as one unbroken line. Every rule in the splitter works on
the shape of a line, so a caption with no breaks in it cannot be split at all,
and a perfectly good recipe comes out as one paragraph. `reflow()` puts breaks
back at the markers that are unambiguous: a section header with a colon, a
numbered step, a bullet. It only fires on captions with almost no breaks
already, so it is a no-op on all 520 Instagram captions, which was the test that
mattered. `split_run_on()` then breaks an ingredient line carrying three or more
quantities, which is what a list looks like after it has lost its newlines.
Neither touches a step like "simmer for 3 minutes", because minutes is not a
unit of measure.

TikTok gives no comment text. yt-dlp returns comment counts only, so the
recipe-in-the-first-comment case that works on Instagram is simply missing. Say
so rather than letting someone wonder why a recipe came out empty.

And the thing worth setting expectations on: TikTok is far more video heavy.
Instagram creators write the recipe in the caption because their audience
expects it. TikTok creators write the dish name and nine hashtags and say the
recipe out loud. On a public cooking account, all eight posts tested went to the
video tier, and the one transcribed came back with every quantity in it. So the
free half of this job is small on TikTok and the cost per recipe is higher.

## The post URL has to live in the data

Links were built as `instagram.com/reel/<code>` in four places. The moment a
second platform exists that is wrong everywhere at once, and it is the kind of
wrong that produces a plausible dead link rather than an error. Exporters now
write a `url` field per post and everything downstream reads it, falling back to
the Instagram template only for collections exported before the field existed.

## Facebook's limit is the comments, and no amount of code fixes it

Instagram was solved by reading comments. TikTok loses comment text but keeps
usable captions and narration. Facebook loses the comments and, on the pages
that matter most, has nothing in the caption or the video either.

What was actually checked, rather than assumed. yt-dlp returns no `comments`
and no `comment_count` for a Facebook post, with or without `--write-comments`.
The post's own HTML, fetched from inside a logged-in session, carries no comment
text at all: 890KB of page shell with zero hits for "ingredient", "feedback" or
anything comment shaped, because Facebook loads them later over GraphQL.
mbasic.facebook.com, the old plain-HTML version that would have made this
trivial, cannot be reached.

Then the part that makes it bite. Ten reels were pulled off one large Facebook
recipe page. Every one ran six to nine seconds, every one transcribed to
"[MUSIC PLAYING]" or "[BLANK_AUDIO]", and every frame was a beauty shot of the
finished dish with no text on it. The captions were all some version of "Full
recipe in the first comment". That is not an accident, it is the page's whole
engagement model, and it means those posts cannot be turned into recipes by
anyone, not just by this.

So the exporter counts them and says so before anything is downloaded. It folds
lookalike letters first, because the same pages write "Recipe in Firsτ Coʍmеոτ"
to get past Facebook's spam filters, and an unfolded match misses it.

## Two of the three platforms needed a letter-folding pass

"Recipe in Firsτ Coʍmеոτ" uses Greek tau, an IPA turned m, a Cyrillic e and an
Armenian vo. Left alone it defeats every pattern in `autobuild.py`, and a line
like that can end up as a recipe title.

`fold_lookalikes()` in `recipe_text.py` puts the letters back, with one rule
that keeps it safe: only words that already contain an ASCII letter get folded.
A caption genuinely written in Greek, Russian or Armenian has no ASCII in its
words and is never touched. Turkish dotless i is deliberately left out of the
table, because Kazandıbı is spelled that way on purpose. Checked against all 521
files of a finished Instagram book: folding changes none of them.

## The venv has to beat PATH, not the other way round

`setup.md` tells macOS users to build a venv because Homebrew's yt-dlp often
fails with "No module named expat". Every script then looked at PATH first,
found the broken Homebrew binary, and used it anyway, so the advice could be
followed to the letter and nothing would change. `work/venv/bin/yt-dlp` now
wins wherever it exists, in both exporters and in `watch.sh`.
