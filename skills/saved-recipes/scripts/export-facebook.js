/* ---------------------------------------------------------------------------
   Facebook saved-items link grabber

   WHAT IT DOES
     Scrolls your Saved page and writes out the links to everything video
     shaped that it finds, as a plain text file, one link per line. That file
     goes to export-facebook.py, which fetches each post's caption and author.

     Links only. Facebook has no endpoint that hands over a saved list, so
     this reads the page the way you would: scroll, look at what loaded,
     scroll again. Nothing is sent anywhere. The only thing it touches is the
     page already open in front of you.

   HOW TO RUN IT
     1. Open facebook.com/saved and click into the collection you want, or
        stay on All.
     2. Open the console: View -> Developer -> JavaScript Console (Cmd-Opt-J).
        First time only, Chrome makes you type: allow pasting
     3. Paste this whole file, press Return, and leave the tab in front.
        Scrolling stops when nothing new turns up.
     4. Chrome asks you to save facebook-saved-urls.txt. Then run:
            python3 export-facebook.py --urls facebook-saved-urls.txt

   THE HONEST BIT
     This half is the one I could not test on real data. The Facebook account
     I had to hand has nothing saved in it, so what you are reading is written
     against Facebook's current markup and the link shapes it uses, and it has
     never run against a full saved list. The link patterns below are the same
     ones export-facebook.py matches, and those are tested.

     If it finds nothing, that is the likely culprit, and there is a plain
     fallback that always works: scroll your saved page yourself, copy the
     links you care about, and paste them into a text file by hand. Or ask
     Facebook for your data (Settings -> Your information -> Download your
     information, JSON, "Saved items and collections") and run
     export-facebook.py --dyi on the export.

   WHAT YOU WILL NOT GET, WHATEVER YOU DO
     Comments. The big Facebook recipe pages put the recipe in the first
     comment on purpose, and leave the caption as bait. That text is not in
     the page source and yt-dlp does not return it, so those posts have
     nothing to extract. Expect a thinner book than Instagram gives you.
--------------------------------------------------------------------------- */

(async () => {
  const MAX_SCROLLS   = 400;    // hard stop, roughly a few thousand items
  const PAUSE_MS      = 1200;   // how long to wait for each batch to render
  const QUIET_ROUNDS  = 4;      // stop after this many scrolls with nothing new

  /* Same shapes export-facebook.py accepts. Anything else saved (articles,
     marketplace, groups, events) is left out, because yt-dlp cannot read it. */
  const VIDEOISH = /^https?:\/\/(?:www\.|web\.|m\.)?facebook\.com\/(?:[^\/]+\/)?(?:reel\/\d+|videos?\/[\w%.-]+|(?:video\.php|watch\/?)\?[^\s]*\bv=\d+|(?:permalink|story)\.php\?[^\s]*\bstory_fbid=[\w.-]+|posts\/[\w.-]+|share\/[rvp]\/[\w-]+)/i;

  const log = (...a) => console.log('%c[recipes]', 'color:#0a7', ...a);

  const tidy = (href) => {
    try {
      const u = new URL(href, location.origin);
      if (u.hostname === 'l.facebook.com' && u.searchParams.get('u')) {
        return null;                       // an outbound link, not a post
      }
      const v = u.searchParams.get('v');
      const story = u.searchParams.get('story_fbid');
      const owner = u.searchParams.get('id');
      u.hash = '';
      // keep only the parameters that identify the post
      const keep = new URLSearchParams();
      if (v) keep.set('v', v);
      if (story) keep.set('story_fbid', story);
      if (story && owner) keep.set('id', owner);
      u.search = keep.toString();
      return u.toString();
    } catch (e) { return null; }
  };

  const found = new Map();                 // tidied url -> true, keeps order
  const sweep = () => {
    let added = 0;
    for (const a of document.querySelectorAll('a[href]')) {
      const u = tidy(a.href);
      if (!u || !VIDEOISH.test(u) || found.has(u)) continue;
      found.set(u, true);
      added++;
    }
    return added;
  };

  if (!/facebook\.com$/.test(location.hostname.replace(/^www\./, ''))) {
    console.error('[recipes] Run this on facebook.com, on your Saved page.');
    return;
  }
  if (!/\/saved/.test(location.pathname)) {
    log('note: you are not on /saved. Carrying on anyway, but you will only ' +
        'get what is linked from this page.');
  }

  sweep();
  let quiet = 0;
  for (let i = 0; i < MAX_SCROLLS && quiet < QUIET_ROUNDS; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise((r) => setTimeout(r, PAUSE_MS));
    const added = sweep();
    quiet = added ? 0 : quiet + 1;
    if (i % 5 === 0 || added) log(`scroll ${i + 1}: ${found.size} links so far`);
  }

  if (!found.size) {
    console.error(
      '[recipes] Found no video posts on this page.\n' +
      'Either the collection is empty, or Facebook has changed its markup ' +
      'since this was written.\nRead the notes at the top of this file for ' +
      'the two fallbacks.'
    );
    return;
  }

  const text = [...found.keys()].join('\n') + '\n';
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'facebook-saved-urls.txt';
  a.click();
  URL.revokeObjectURL(url);
  log(`done. ${found.size} links written to facebook-saved-urls.txt`);
  log('next: python3 export-facebook.py --urls facebook-saved-urls.txt');
})();
