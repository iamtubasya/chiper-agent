# Forexfactory / Fair Economy bounty — platform map + posture (2026-09-30)

Worked example for RULE 35 (scanner triage) and for driving an authenticated PHP+Vue app whose session
cookie is HttpOnly. Target set: `*.forexfactory.com`, `*.cryptocraft.com`, `*.energyexch.com`,
`*.metalsmine.com` — one shared codebase on four verticals (same `_sites` config in `window.FF`).

## Program exclusions (read from /bug-bounty, Sep 2026 — check before every round)

Out of scope / not rewarded: DoS, TLS config, SPF/DMARC, **host header injection**, **CORS config**,
**cookie flags (Secure/HttpOnly)**, weak password policy, **session mgmt policy**, unique email,
**email enumeration / IDOR / brute force**, insignificant requests lacking CSRF tokens, phishing,
cached info in client/CDN, public config + version disclosure.
Reportable therefore = real server-side attacks (SQLi/RCE/SSRF/deserialization/template), XSS that
survives WAF + sanitiser, and significant business logic. Rewards $100 → $10k.
Submission: `/contact?subject=other&other_subject=Bug+Bounty`.

## Infra

Everything is Cloudflare (`104.18.x`); **no origin IP found** — passive subdomains (`web1-4`, `mail`,
`secure`, `blog`, `cdn`) are NXDOMAIN, `o1/o2.ptr*` are SendGrid. WAF bypass must be payload/behavioural,
not direct-to-origin. UA layer behaves per `waf-stateful-bypass` (stale Chrome UA → CF JS challenge).

## URL scheme (matters for scanner triage)

`/<username>` → **public member profile** (so `/admin`, `/manager`, `/debug`, `/swagger`, `/api/` all
return 200 as profiles — classic FP, see RULE 35.2). Real routes: `/thread/<id>-<slug>`,
`/thread/post/<id>`, `/forum/<id>-<slug>`, `/calendar`, `/market/<pair>`, `/news`, `/trades`,
`/tradeexplorer`, `/traders`, `/brokers`, `/search`, `/create-account`, `/profile`, `/account`,
`/subscriptions`. Legacy vBulletin files (`members.php`, `news.php`, `search.php`, `login.php`,
`sentiment.php`, `member.php`) 301/400 to modern routes — dead surface.

## Auth flow (for future rounds)

- Login: `POST /login`, fields `_csrf`, `do=login`, `gotoprofile=1`, `vb_login_username`,
  `vb_login_password` (hidden; the page JS copies the visible inputs in). CSRF = `meta[name=csrf-token]`.
- **CSRF header is `X-CSRF-TOKEN`** — injected globally via axios defaults + `$.ajaxSetup`. Without it,
  endpoints return 400/"Unauthorized"/"No permission"; with it they work. Re-fire before recording any
  negative on this target.
- Registration: 3-step JSON-backed wizard (`/create-account` → email → 6-digit code → username/password/
  trading-from/agreement). reCAPTCHA **Enterprise** widget is present and the step-1 POST was accepted
  with an empty `g-recaptcha-response` (anti-automation weakness, Low/Info — not worth reporting given
  the program's exclusions). Disposable mailbox (mail.tm API) worked end-to-end.
- Fresh accounts are heavily gated: posts are **hand-moderated** (`threadpost-content--moderated`) and
  shouts/PMs return `{"error":"Unauthorized"}` ("Private Messages Restricted Per Account Status").
  A new account cannot reach the stored-XSS surfaces — plan to age the account or test with one in good standing.

## Endpoint map (from JS bundle mining — 65 + 10 bundles)

App AJAX engine: **`POST /flex.php`** — every "flex box" (forums, trades, news, profile activity) posts a
FormData with `flex[<Model>][field]` + a server-encrypted `modelData` blob and gets back
`<flex><![CDATA[…]]></flex>`; the client does `responseXML.body.innerHTML = …`. Invalid settings fall back
to defaults and are not echoed unescaped. Other app endpoints: `/market/component-setting` (chart
settings, form-encoded `type=CgsChart&id=&settings={}`; JSON content-type ⇒ 500), `/trades/validate-pair`,
`/news/hot-stories/save`, `/misc/{save-settings,hide-notice,info-editor/save,move-layout-component}`,
`/calendar/{more,details,history,graph,mini,apply-settings,initials}` (numeric segments are int-cast;
non-numeric ⇒ 302), `/thread/{edit-post,update-post,delete-post}/`, `/market-admin` and `/calendar/initials`
exist but 403.

Trade Explorer subsystem (round 2, `recon/js2/`): `GET /explorerapi.php?content=<c>&id=<acct>` —
`content=` `shell|overview|graph|tradeslist|positions|tradegraphdata` work **unauthenticated** for public
explorers (by design; ids are linked from `/trades`), `content=account&action=reset|sync|blacklist` is
**authorised** (400 unauth), `content=chartedtrade` and `?admin=<x>` ⇒ 500 with an empty body. Also
`GET /tradeexplorer/public-by-username?username=` (parameterised, public data) and
`POST /shout/<userid>` + `POST /shout/delete/<vmid>`.

API hosts: `mds-api` (Laravel, strict integer/enum validation — "must be an integer", "not greater than
9999"; market data needs exact instrument names like `EUR/USD`), `bds-api` (404 on everything guessed),
`explorer-api` (routed PHP, "Invalid account id"), `npd-api` (403 on every path, XFF/Origin/Referer spoofs
ignored), `wss://mds-wss.forexfactory.com:2096` (public market data; needs browser UA **and**
`Origin: https://www.forexfactory.com` or it 403s; injection channel names silently ignored).
`window.FF` (public config) discloses all endpoint hosts, site ids, GTM ids and the reCAPTCHA
site key — recon, not a finding; bearer fields are empty even when authenticated.

## Confirmed negatives (don't re-derive — cite instead)

Reflected XSS in `/search` (all 4 reflection points: `og:url` full-query echo, `input value`,
"No results for '<strong>…", and `decodeURIComponent("<double-url-encoded>")` inside `<script>` — the
double encoding means only `[A-Za-z0-9%]` reaches the JS string); stored XSS in forum posts (HTML
entities + new-user moderation); `flex.php` settings/`modelData` tampering; SSRF via Trade Explorer
`mt4[server]` (injected an interactsh host into the select and submitted the real form → no OOB);
SQLi on app params (`month`,`day`,`week`,`range`,`filter`,`countries`,`impacts`,`searchuser`,`searchid`,
`provider`,`item`,`type`,`idSuffix`) and on mds-api params; `provider` class/route injection
(whitelist behaviour); sensitive files ⇒ 403; open redirect (`redirect_uri`, search redirect);
`explorerapi` parameter reflection; websocket authz/injection; legacy PHP surface.

## Open leads (round 3+)

1. **Explorer title → HTML (unescaped output PROVEN, input escaping unproven).** `content=shell` emits
   `<strong class="explorer__titlesegment explorer__titlesegment--title">…TITLE…</strong>` raw, and the
   member profile emits it inside `<span class="internal">`. Of 64 harvested titles, 5 contain *stored*
   HTML entities (`1400&#8364; Empf&#228;nger 1`) and one raw UTF-8 (`Empfänger 5`) — so the stored value
   is emitted verbatim. Blocked only by explorer creation requiring a successful **MT4/MT5 handshake**
   (`/tradeexplorer?do=validate`; fake credentials + real AAAFx demo server id 54738 created nothing).
   → get one demo MT4/MT5 login, name the explorer with `" < > &`, re-read shell + profile.
2. Shouts / verbose messaging after raising account standing (`emojiParser.toShort()` is the render path).
3. `content=account&action=…` CSRF-via-GET on our **own** explorer once one exists (never on other users'.
   State-changing actions via GET are only reportable when the action is genuinely meaningful — the
   "insignificant requests lacking CSRF tokens" exclusion bites otherwise).
4. Standalone re-run of `execute-references.py` (C6 stage died on a 2400 s timeout — environment, not a
   target result).

## Process notes for the next round

- Keep one camofox `userId` per identity for the whole engagement and **don't delete the session** until
  the work is done (deleting it logs the account out — see the camoufox skill).
- `window.FF` etc. are invisible to camofox `/evaluate` (isolated world) — fetch the HTML in-page and
  regex the config instead of debugging the main-world handshake.
- Drive authenticated endpoints with in-page `fetch` + `X-CSRF-TOKEN`; that single trick unlocked the
  whole explorerapi/public-by-username/shout surface.
- Triple-check reflection claims with a *raw* marker test (`z"y<x>z`) and count raw occurrences in the
  body — the `og:url` full-query echo produces scanner FPs on **every** parameter, including ones the app
  never consumes.
