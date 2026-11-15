# Round-3b negative matrix — forexfactory / cryptocraft / energyexch / metalsmine (2026-10-01)

Purpose: the next round must be able to skip everything on this page and start where the coverage
actually stopped. Every row was **executed** against the live target; the evidence trails are named.

## Settled negatives (fire only if you have a NEW idea)

| vector | what was fired | verdict / evidence |
|---|---|---|
| mass assignment on `POST /create-account` | crafted JSON with `subscription_id:1`, `content_id:1`, `child_content_id:0` + `is_admin, is_team, admin, role:"admin", usergroupid:6, userid:1, verified, email_verified, reputation, joindate, perms{…}, can_control_panel, can_manage_cbase, subscription:"premium", plan, tier, premium, mirs_rank, is_moderator, usergroup` | account created, **all privileged fields ignored** (`is_team:false`, 4/4 perms false, status "Trader") → whitelisted. Evidence: `recon/massassign_result.json`, account C `fzmassnvgr` |
| prototype pollution | `__proto__[x]`, `constructor[prototype][x]`, nested flex keys → `flex.php`, `/misc/save-settings` | no state change |
| deserialisation / param pollution | PHP-serialised `modelData`, 4 KB junk, NUL bytes, duplicated `do`/`setdefault` | no 500, no stack trace, no state change |
| XXE | `application/xml` + DOCTYPE entity → `flex.php` (XML-returning) | empty 200, no fetch, no OOB |
| HTTP desync | raw socket CL.TE / TE.CL / `TE:<tab>` / `TE: xchunked` | 400 / 400 / 501 / 501 at the Cloudflare edge |
| verb tampering | TRACE, OPTIONS, `X-HTTP-Method-Override`, GET-on-state-change | TRACE 405; override ignored; `/brokers/delete-log` POST-only; `explorerapi content=account&action=…` 400 unauth |
| SSRF (OOB, live interactsh) | OOB host into: `tradeexplorer?do=validate` `mt4[server]`/`mt5[server]`/`mt4[broker]`, `search`/`searchid`/`provider` (`data-type=searchBing`), `/news/hot-stories/save`, `/calendar/apply-settings`, `/market/component-setting`, `/trades/validate-pair`, `member.php` panels (`website`/`url`/`userfield[field4]`), `explorerapi` `url`, `/brokers/delete-log/<oob>`, mds-api JSON | **0 callbacks** in 30 s+ (listener domain printed from its own log) |
| IDOR `explorerapi.php` | `content=tradesnote|chartedtrade|account` × real public explorer ids × `ticket=0,1..5,1000000,-1` | `{"error":"invalid request"}` / empty 500 on the `chartedtrade` error path; no other member's data |
| GraphQL | `/graphql`, `/graphiql`, `/api/graphql`, `/playground` per host + GraphQLmap | 404 everywhere → none |
| SQLi | ghauri (level 2) on the new endpoints; sqlmap/dalfox/pipeline in earlier rounds | no injection |
| XSS | dalfox on the new endpoints | 1 `BUILTIN` grep hit = **FP** (response is 27-byte `{"error":"invalid request"}`; `page_id` never consumed; `<svg onload>` → 5503-byte CF block). The `AIza…` string it grepped is an **invalid sample key** absent from the target (verified with one Google API call + site-wide grep) |
| nuclei (local mirror, tags exposure/misconfig/tech/cve/default-login/takeover/redirect/ssrf/xxe) | 8 hosts | 16 findings, **all weak-cipher TLS1.0/1.1** → program excludes TLS → 0 reportable (`recon/scans/nuclei.txt`) |
| dir-bust | ffuf wordlist + path list on siblings and the 4 API hosts | API hosts: CF 403 + `npd` "NPD Access Forbidden" + `explorer-api` "Unable to match route"; siblings: every 200 is a `/<username>` profile page (`upload's Profile`, same ~56–59 KB band) |
| race | `race-checker.py` 8×25 on `/brokers/delete-log/<bogus>` and `explorerapi…action=sync&id=0` | uniform 403, no flip; tool has **no cookie flag** → unauthenticated run; authenticated concurrency needs a custom harness |
| websockets | `mds-wss:2096` **with a real session cookie**, channels `EUR/USD`, `private.<uid>`, `user.<uid>`, `trades.<uid>`, `admin`, `*`, `../config` → identical public deflate market feed; `calendar-feed:2087` with session, real event ids + range | channel names are not an authorisation boundary (public-by-design feed); calendar feed push-on-change ⇒ inconclusive, no leak evidence |
| SSTI | `{{7*7}}`, `${7*7}`, `{{7*'7'}}` on `search`/`calendar`/`market` + control request | not reflected, no evaluation signal |
| self-service writes | `/misc/save-settings`, `/flex.php do=saveoptions`, `/member.php do=apirequest&panel=aboutinfo&action=save` | `{"success":true}` with nothing persisted; `data-isdefault="1"` in the flex re-render ⇒ not applied |
| profile free-text fields | `aboutinfo` editor (24 controls, all `<select>`); `linkInfo` → 401 `<fail/>`; `profilePicture` → upload-only; `userfield[field4]` save returned a success panel but persisted/rendered nothing | **no free-text profile field exists for a member account** ⇒ signature/status/custom-field stored-XSS surface unreachable from outside |
| avatar upload `POST /member.php` (multipart `upload` + `do=apirequest&panel=profilePicture&u=<uid>&action=upload|delete`) | real 1×1 PNG, HTML content, `.php`/`.svg` names, traversal names | PNG baseline refused (`Invalid image uploaded.`), `.html`/traversal refused, `.php`/`.svg` → CF 403; delete → "No profile picture found." ⇒ no bypass, but no positive baseline either |

## Still open (needs credentials, not more tooling)

1. **Demo MT4/MT5 login** — explorer create form has `name` (user-controlled, ≤40, "can be edited at
   any time") but **no login field**: the MT account id comes from the handshake, and
   `POST /tradeexplorer?do=validate` with fake creds creates nothing and surfaces no error
   (`/tradeexplorer/public-by-username?username=<u>` → `explorers: []`). The title output is proven
   unescaped, so one real demo login is the only gate.
2. **Account with posting rights** — fresh accounts are throttled (`highload` page) and can be
   downgraded to status "Membership Denied", which also removes the settings UI. Needed for the
   cross-account `/thread/update-post/<id>` test, shout/PM content and the Text Signature render.

## Files worth reading before round 4

`recon/scans/nuclei.txt`, `recon/scans/dalfox3.txt`, `recon/massassign_result.json`,
`recon/r3_serverside.log`, `recon/r3_ssrf.log`, `recon/r3_explorerapi.log`, `recon/r3_profile_api.log`,
`recon/aboutinfo_editor.html`, `recon/soft_*.html` (soft-404 proof), `recon/oob/` (interactsh logs),
`recon/ck_*.txt` (per-host cookie jars), `recon/mailtm*.json` (three mail.tm boxes),
and `ENGAGEMENT_LOG.md` §"Round 3b".
