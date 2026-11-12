/* ---------------------------------------------------------------------------
   Instagram saved-collection exporter

   WHAT IT DOES
     Reads one of your own saved collections and downloads it as recipes.json.
     Runs entirely in your browser, on your own logged-in session. Nothing is
     sent anywhere: the only network calls are to instagram.com, the same ones
     the page makes itself, and the file is written by your browser's own
     download prompt.

   HOW TO RUN IT
     1. Open Instagram in Chrome and go to the collection you want:
        Profile -> Saved -> (the collection). The address bar should look like
        instagram.com/<you>/saved/<collection-name>/17912345678901234/
     2. Open the console: View -> Developer -> JavaScript Console (or Cmd-Opt-J).
        First time only, Chrome makes you type: allow pasting
     3. Paste this whole file, press Return, and leave the tab open and in front.
     4. It prints progress. When it finishes, Chrome asks you to save
        recipes.json. Save it, then move it into the folder you are working in.

   HOW LONG
     About one second per post, because it asks for each post's comments too.
     500 posts is roughly 10 minutes. Set WANT_COMMENTS=false below to skip the
     comments and finish in under a minute, at the cost of losing the recipes
     that creators put in the first comment instead of the caption.
--------------------------------------------------------------------------- */

(async () => {
  const WANT_COMMENTS = true;   // false = much faster, misses comment recipes
  const TOP_COMMENTS  = 3;      // non-author comments to keep per post
  const PAUSE_MS      = 900;    // politeness delay between comment requests
  const MAX_POSTS     = 0;      // 0 = all. Set e.g. 20 for a quick test run.

  const APP_ID = '936619743392459';
  const H = { 'X-IG-App-ID': APP_ID, 'Accept': 'application/json' };
  const get = async (u) => {
    const r = await fetch(u, { headers: H, credentials: 'include' });
    if (!r.ok) throw new Error(`HTTP ${r.status} on ${u}`);
    return r.json();
  };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const log = (...a) => console.log('%c[recipes]', 'color:#0a7', ...a);

  /* --- find the collection id ------------------------------------------- */
  const parts = location.pathname.split('/').filter(Boolean);
  const si = parts.indexOf('saved');
  const cid = si >= 0 ? parts.slice(si + 1).reverse().find((p) => /^\d{5,}$/.test(p)) : null;
  if (!cid) {
    console.error(
      '[recipes] Could not find a collection id in the address bar.\n' +
      'Open the collection itself (Profile -> Saved -> the collection) and run this again.\n' +
      'The URL needs to end in a long number, e.g. .../saved/recipes/17912345678901234/'
    );
    return;
  }
  log('collection', cid);

  /* --- page through the collection -------------------------------------- */
  const media = [];
  let next = null, page = 0;
  do {
    const u = `https://www.instagram.com/api/v1/feed/collection/${cid}/posts/?count=50` +
              (next ? `&max_id=${encodeURIComponent(next)}` : '');
    const j = await get(u);
    const items = j.items || [];
    for (const it of items) media.push(it.media || it);
    next = j.more_available ? (j.next_max_id || null) : null;
    log(`page ${++page}: ${items.length} posts (${media.length} total)`);
    if (MAX_POSTS && media.length >= MAX_POSTS) { next = null; media.length = MAX_POSTS; }
    if (next) await sleep(400);
  } while (next);

  if (!media.length) {
    console.error('[recipes] The collection came back empty. Are you signed in as the owner?');
    return;
  }

  /* --- flatten -----------------------------------------------------------
     NOTE: never read the numeric `pk` field for an id. It is bigger than a
     JavaScript number can hold exactly, so it silently rounds and every later
     comment request 404s. Always use the string form.                       */
  const posts = media.map((m, i) => ({
    n: i,
    id: m.strong_id__ || String(m.id || '').split('_')[0] || String(m.pk),
    code: m.code || '',
    user: m.user?.username || '',
    dur: Math.round(m.video_duration || 0),
    taken: m.taken_at || 0,
    cap: m.caption?.text || '',
    own: [],
    top: [],
  }));
  log(`${posts.length} posts found`);

  /* --- comments ---------------------------------------------------------- */
  if (WANT_COMMENTS) {
    log('fetching comments, about a second each. Leave this tab in front.');
    for (const p of posts) {
      try {
        const j = await get(
          `https://www.instagram.com/api/v1/media/${p.id}/comments/` +
          `?can_support_threading=true&permalink_enabled=false`
        );
        const cs = j.comments || [];
        p.own = cs.filter((c) => c.user?.username === p.user).map((c) => c.text);
        p.top = cs
          .filter((c) => c.user?.username !== p.user)
          .sort((a, b) => (b.comment_like_count || 0) - (a.comment_like_count || 0))
          .slice(0, TOP_COMMENTS)
          .map((c) => ({ u: c.user?.username || '', t: c.text || '' }));
      } catch (e) {
        p.err = String(e.message || e);   // deleted, private, or rate-limited
      }
      if (p.n % 25 === 0) log(`comments ${p.n}/${posts.length}`);
      await sleep(PAUSE_MS);
    }
  }

  /* --- save -------------------------------------------------------------- */
  const blob = new Blob([JSON.stringify(posts, null, 1)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'recipes.json';
  document.body.appendChild(a);
  a.click();
  a.remove();

  const withText = posts.filter((p) => p.cap.length > 80 || p.own.length).length;
  const failed = posts.filter((p) => p.err).length;
  log(`done. ${posts.length} posts, ${withText} already have text, ${failed} could not be read.`);
  log('Saved as recipes.json. Move it into the folder you are working in.');
  window.__recipes = posts;   // also left here in case the download was blocked
})();
