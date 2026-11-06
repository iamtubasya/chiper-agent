---
name: js-spa-data-extraction
description: "Use when a 200 returns an empty shell (unrendered SPA)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Scraping, SPA, NextJS, Headless, JSON-API, DataExtraction]
    related_skills: [blocked-page-recovery, dogfood]
---

# JS-SPA Data Extraction

A **client-rendered single-page app** returns HTTP 200 with a few KB of
`<div id="root"></div>` and no data. `web_extract`, `curl`, and text scrapers
all come back with an empty shell — which reads *exactly* like a WAF block but
is not one. There is nothing to bypass and no stealth tooling will help: the
data is fetched by JS *after* load, or embedded in the HTML as a serialized
payload you haven't parsed yet.

**Rule zero: an empty 200 is an unrendered SPA until proven otherwise.** If
you reach for anti-bot evasion before ruling this out, you will spend the
session fighting a wall that isn't there.

## When to Use

Load this skill whenever a fetch **succeeds but returns no data**:

- `web_extract` / `curl` / a scraper returns HTTP 200 with an empty shell
- A directory, listing, dashboard, or marketplace page yields no records
- You are about to reach for anti-bot / stealth tooling because a page
  "looks blocked" — stop and rule out SPA first
- You need records out of a Next.js / Nuxt / Remix page without a browser daemon

Do **not** use this for genuine blocks (403/429/CAPTCHA/interstitial) — that is
`blocked-page-recovery`. Use this when the response is a valid page that simply
contains no records.

## Symptom triad — any one means "suspect SPA"

| Signal | Detail |
|---|---|
| 200 + tiny body | A few KB, a `<script src>` bundle, contains no list items/records |
| Renders fine by hand | Same URL in a normal desktop browser shows the full list |
| Template with no records | `curl` of the canonical URL returns the app shell, zero data |

Contrast with a real block: a block returns 403/429/challenge HTML, or a title
like "Just a moment" / "Attention Required". An SPA shell has a *normal* page
title and *valid* markup — just no data. Prove which one you have: if the raw
HTML has no records but the DOM does, it was an SPA.

## Route A — dump the rendered DOM (no browser daemon required)

The cheapest render path needs no Playwright, no CDP session, and no
`browser_exec` daemon — just the Chrome/Edge binary already on the box:

```bash
chrome --headless --disable-gpu --dump-dom --virtual-time-budget=8000 \
  "https://TARGET/directory" > page.html
```

- Raise `--virtual-time-budget` (ms) when the list lazy-loads or paginates.
- On Windows, Chrome/Edge usually live under
  `C:/Program Files/Google/Chrome/Application/chrome.exe` or
  `C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`; quote the
  path, and pass **native forward-slash paths** (`C:/...`, `D:/...`) — MSYS
  does not path-translate arguments to native binaries.
- This is a *different mechanism* from the browser tool, not a retry of it.
  When a browser daemon is unavailable, this route still works — an absent
  daemon is a setup state, never a dead end.

Then parse the dump **from disk with a script**, not by piping it through a
text extractor and not by pasting it into context (a rendered directory can be
hundreds of KB). Extract → write structured output to a file → report the
count. See `references/nextjs-flight-payload-parser.md`.

## Route B — parse the framework's embedded state

Modern SPAs inline their first payload into the HTML, so a single `--dump-dom`
is usually enough — no further network calls:

| Framework | Payload |
|---|---|
| Next.js **App Router** | `self.__next_f.push([1,"..."])` chunks (a "flight" payload) |
| Next.js **Pages Router** | `__NEXT_DATA__` (a single JSON `<script>`) |
| Nuxt | `window.__NUXT__=` |
| Remix / React Router | `__remixContext` |
| Redux | `__PRELOADED_STATE__` |
| Apollo | `__APOLLO_STATE__` |

Prefer **brace-matching / array-literal matching over regex** to lift these
out — the payload contains nested quotes and escaped JSON, so a greedy regex
silently truncates. Concatenate the `__next_f` chunks in order first, then
brace-match the resulting JSON.

Advantage over DOM scraping: you recover **complete structured objects**
(name, URL, scope, reward fields) rather than scraped text fragments, so
downstream filtering is exact instead of heuristic.

## Route C — find the JSON endpoint (best route when it exists)

If the directory renders client-side, a JSON API almost always feeds it, and
that endpoint needs no rendering and no JS at all. **Probe this before
writing any parser** — it is cheaper and more complete than DOM scraping.

- Common shapes: `/engagements.json`, `/api/programs`, `/api/v1/...`,
  `/graphql`, `.json` appended to the directory URL.
- Find the real one in the **JS bundle**: grep the dumped HTML for `fetch(`,
  `axios`, or relative string literals near the list component.
- Cheap probes first: if a plain `curl` of a guessed endpoint returns JSON,
  you are done in one call.

If Route C works, use it and skip Routes A/B entirely.

## Order of operations

1. Fetch. Got records? Done.
2. Empty shell → it's an SPA. Don't escalate anti-bot tooling.
3. Probe for a JSON endpoint (Route C) — one or two `curl` calls.
4. No endpoint → `--dump-dom` (Route A) and parse embedded state (Route B).
5. Validate: count matches the visible total, and spot-check one record
   against the rendered page (`js`/DOM read) before trusting the batch.

## Known SPA Catch-All Behaviors (Bug Bounty Context)

When probing for source disclosure (`.git`, `.env`, `config.js`, `swagger-ui.html`,
`actuator`, `backup.zip`, etc.), SPA frameworks return HTTP 200 for ALL paths.
This creates false positives in source disclosure scans.

**Detection pattern:** Compare response body size + content of suspected path vs root `/`.
If identical → SPA catch-all, NOT real file access.

**Example (PepperShop/SAP Spartacus):**
```
/                    → 200, 253KB, Angular SPA HTML
/.env                → 200, 0 bytes (empty body, SPA catch-all)
/.git/config         → 200, 0 bytes (SPA catch-all)
/application.properties → 200, 0 bytes (SPA catch-all)
/swagger-ui.html     → 200, 0 bytes (SPA catch-all)
/actuator/env        → 200, 0 bytes (SPA catch-all)
```

**Blocklist of SPA catch-all hosts to skip in source disclosure:**
- Any Angular/SAP Spartacus shop frontend (shop.post.ch, fundeint.post.ch)
- Any PepperShop deployment
- Any host where root `/` returns Angular SPA HTML

**False positive trap:** Status code alone is unreliable. Always check:
1. Response body size (0 bytes = likely catch-all)
2. Response body content (matches root page = SPA catch-all)
3. Content-Type header (text/html for all paths = SPA catch-all)

**Parameter pollution on SPAs:** Duplicate params (e.g., `?query=a&query=b`) may
trigger HTTP 500 from the SPA router, NOT a real server error. Verify by checking
if the response body is the SPA's error page HTML (not a Java/PHP/Python stack trace).

## Pitfalls

- **Don't misdiagnose an SPA as a WAF block.** It is the single most expensive
  error here. `blocked-page-recovery`'s ladder (Wayback, archive.today, Jina,
  Camofox) will not fix an unrendered app — archives of JS-only pages are
  shells too, and no fingerprint spoof makes the data appear.
- **Don't paste a rendered dump into a text extractor and call it extracted.**
  It's markup; parse it structurally or route around it.
- **Don't let a giant DOM flood context.** Persist to a scratch file, parse
  with a script, and read back only the counts and a couple of samples.
- **Don't regex the flight payload.** Nested/escaped JSON defeats greedy
  patterns; brace-match or parse normally after unwrapping.
- **Don't trust `--dump-dom` output on pages with client-side pagination.** A
  single dump sees one page at most; drive pagination or use the JSON API.
- **Re-render at the right URL** — some apps only load data on a specific
  route (e.g. a query-string or slug variant), so re-dumping the marketing URL
  keeps returning a shell.
- **Clean up scratch files.** HTML dumps and parse intermediates belong in a
  temp dir; keep only the small reusable script (see `scripts/`).

## Verification

Before reporting extraction results:

```bash
# 1. Records parsed > 0 and the count is not suspiciously round/partial
# 2. One record matches the live rendered page (spot-check by DOM read)
# 3. No record fields are null where the source page shows a value
```

If any check fails, you parsed the wrong node — do not report the partial set.

## Support files

- `references/nextjs-flight-payload-parser.md` — working unwrap + brace-match
  recipe for `__next_f`, plus how to spot the list node in a dumped DOM.
- `scripts/unwrap_next_flight.py` — re-runnable extractor: reads a dumped HTML
  file, joins the flight chunks, brace-matches records, writes JSON.
