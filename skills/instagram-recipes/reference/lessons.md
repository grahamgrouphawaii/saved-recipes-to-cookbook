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
