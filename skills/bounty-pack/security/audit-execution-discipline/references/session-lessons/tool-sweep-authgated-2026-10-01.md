# Tool sweep on an auth-gated target — measured results (forexfactory round 3b, 2026-10-01)

Companion to RULE 36. Target: Cloudflare-fronted, reCAPTCHA-Enterprise-gated PHP/vBulletin-flex app with
a real test account. Everything below was **executed**; the point of keeping the table is that the next
round must not re-run settled negatives (RULE 33) and must be able to quote what "negative" was based on.

## 1. Per-vector matrix (all fired, all with a written verdict)

| # | vector | tool / method | verdict |
|---|---|---|---|
| 1 | mass assignment (`is_admin, is_team, role, usergroupid, userid, verified, reputation, joindate, perms{}, can_control_panel, subscription_id, content_id, plan, tier, premium, mirs_rank, usergroup`) | crafted JSON to `POST /create-account` through a captcha-verified browser session, then read `window.FF.perms` / `is_team` / profile status | **whitelisted** — account created, every privileged field ignored (`is_team:false`, all 4 perms false, status "Trader") |
| 2 | prototype pollution (`__proto__[x]`, `constructor[prototype][x]`, nested) | `flex.php` + `/misc/save-settings` | no observable state change |
| 3 | deserialisation / param pollution | PHP-serialised blob, 4 KB junk, NUL bytes, duplicated `do`/`setdefault` into `flex.php modelData` | no 500, no stack trace, no state change |
| 4 | XXE | `application/xml` + DOCTYPE entity → `flex.php` (returns XML) | empty 200, no fetch, no OOB |
| 5 | HTTP desync | raw socket CL.TE / TE.CL / `TE:`+tab / `TE: xchunked` | 400 / 400 / 501 / 501 at the CF edge → rejected |
| 6 | verb tampering | TRACE / OPTIONS / `X-HTTP-Method-Override` / GET-on-state-change | TRACE 405, override ignored, state changes POST-only or auth-gated |
| 7 | blind SSRF (OOB) | interactsh `*.oast.fun` injected into ~20 server-side fields (broker/server pickers, search backend `data-type=searchBing`, hot-stories save, calendar/market setting saves, profile panel `website`/`url`/`userfield[]`, API `url` param, delete-log path) | **0 callbacks** (listener live, domain printed from the log) |
| 8 | IDOR | `explorerapi.php?content=tradesnote&#124;chartedtrade&#124;account&id=<real public ids>&ticket=0,1..5,1000000,-1` | `{"error":"invalid request"}` / empty 500 error path |
| 9 | GraphQL | `/graphql`, `/graphiql`, `/api/graphql`, per host + GraphQLmap | 404 everywhere → no GraphQL |
| 10 | nuclei (local mirror, tags exposure/misconfig/tech/cve/default-login/takeover/redirect/ssrf/xxe) | 8 hosts | 16 findings, **all `weak-cipher-suites` TLS1.0/1.1** → program excludes TLS → 0 reportable |
| 11 | dir-bust | ffuf (wordlist + targeted path list) on siblings + 4 API hosts | API hosts: CF 403 + JSON route errors only; siblings: **every 200 is a `/<username>` profile page** (soft-404) |
| 12 | race | `race-checker.py` (8×25) on authz endpoints | uniform 403, no flip — and see tool note below |
| 13 | websockets (authenticated) | `mds-wss:2096` with real session cookie, channels `EUR/USD`, `private.<uid>`, `user.<uid>`, `trades.<uid>`, `admin`, `*`, `../config` | identical public market feed for every channel name → channel string is not an authz boundary; `calendar-feed:2087` push-on-change ⇒ inconclusive |
| 14 | SSTI | `{{7*7}}`, `${7*7}`, `{{7*'7'}}` on search/calendar/market + control request | not reflected, no evaluation signal |
| 15 | self-service write endpoints | `/misc/save-settings`, `/flex.php do=saveoptions`, `/member.php do=apirequest&panel=…&action=save` | **`success:true` with nothing persisted** — see §2 |

## 2. The `success:true` trap (biggest time-waster of the session)

`/misc/save-settings` returned `{"success":true}` for *every* payload, including privileged option keys
(`options[can_control_panel]`, `set_options[usergroupid]`, `options[is_team]`). A re-read of the profile
proved nothing was stored: signature/status fields came back empty and `FF.perms` stayed false.

Recipe that settled it:

```
POST /misc/save-settings   {signature[text][text]: "MARK", userstatus: "MARK"}   -> {"success":true}
GET  /<username>           -> grep 'name="signature\[text\]\[text\]"[^>]*value="([^"]*)"'  -> empty
```

Rules that fall out: (a) never report a write-endpoint finding off the write response; (b) an
unconditional-success endpoint is a whitelist, and quoting it as "mass assignment accepted" is an FP;
(c) `data-isdefault="1"` in a flex-style XML re-render means the save was *not* applied.

## 3. FP-triage recipes added this session

- **dalfox `BUILTIN` grep hit** (`{"type":"G","poc_type":"plain","evidence":"","message_str":"Found
  dalfox-google-api via built-in grepping"}`) — verify by fetching the POC URL yourself; here the
  response was a 27-byte `{"error":"invalid request"}`, the parameter (`page_id`) was never consumed,
  and the `<svg onload>` variant returned the 5503-byte Cloudflare block page ⇒ FP.
- **dalfox can grep a *fake* API key.** It printed `AIzaSy[REDACTED_FAKE_KEY]`, which
  appears nowhere in any fetched page/JS/API response, and one benign Google API call answered
  `The provided API key is invalid`. Before an "API key exposure" ever reaches a report: (1) grep the
  key across the pages/JS you already saved, (2) make one call to see whether it is even live,
  (3) `grep -c` the live pages. Only a key that exists on the *target* and is *usable* is a candidate.
- **Soft-404 by `<title>` on `/<username>` routers** — confirm a dir-bust "hit" by comparing the title
  of a random path with the candidate path: `/zzz-nonexistent` → `Notice | Page Not Found`,
  `/upload` → `upload's Profile`, `/health` → `health's Profile`; same size band (~56–59 KB) ⇒ all FP.
- **TLS findings are program-excluded here** — nuclei's whole output on this stack was weak-cipher
  TLS1.0/1.1; report them as out-of-scope, never as coverage, and never pad the report.

## 4. Tool-usage nuances (not "tool is broken" — the workaround is the lesson)

- `race-checker.py` takes only `-u/--threads/--attempts/--timeout`: **no cookie support**, so it can
  only test unauthenticated endpoints. Authenticated concurrency needs your own threaded harness
  (`http.client` + session cookie). Also: a race that could actually fire on a *third party's*
  resource is out of bounds — record "untestable in scope" instead of a clean negative.
- `arjun` returned `AttributeError: 'dict' object has no attribute 'status_code'` on one GET target and
  hung on another. Fallback that worked: a bounded manual parameter diff (or `ffuf` with a wordlist of
  parameter names) — record the fallback and the payload set, don't record a coverage claim.
- `nuclei -t <dir>` is correct (`-template-dir` is not a flag) — already in RULE 2b; reconfirmed here.

## 5. Account hygiene on a moderated platform (learned the hard way)

- A fresh account that posts/registers repeatedly can be silently downgraded: the profile status field
  flipped to **"Membership Denied"**, the reply POST returned a `highload` page, and the settings panel
  vanished from the DOM while still present in the curl-rendered HTML. Register **a spare account
  early** and check the status field before concluding "the feature is broken".
- Content from a new account may never clear moderation (the round-1 test post 404'd later) — do not
  build a cross-account test on a post you cannot prove is visible.
- The one-time password-reset flow *rewrites the password*; both test accounts had to be re-logged with
  the system-generated password read from the mailbox. Keep those values in the engagement log.
