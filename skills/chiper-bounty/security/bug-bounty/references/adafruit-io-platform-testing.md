# Adafruit IO Platform Testing (2026-10-21, 0 findings — hardened target)

Engagement: adafruit.com bug bounty ($25-$150 CVSS-based, scope *.adafruit.com + *.adafruitdaily.com).
Result: no bounty-worthy findings. Full tool ledger + manual testing, all clean.

## Platform architecture

- **io.adafruit.com** — Rails IoT data platform (feeds/dashboards/groups/blocks/triggers/dynamic_actions).
  NOT behind Cloudflare (direct origin). SPA served from CloudFront (`d2794n4cyhr13z.cloudfront.net/vite/`).
- **accounts.adafruit.com** — Rails account/SSO (Devise). Login: `user[login]` + `user[password]` (login accepts email OR username).
- **www.adafruit.com** — Zen Cart storefront (legacy index.php?main_page= deprecated, 301s to /product/*).
  Products increasingly DigiKey-fulfilled (no direct add-to-cart form).
- **blog.adafruit.com** — WordPress (wp-json/xmlrpc/wp-login all blocked 403/404).
- **volcano.adafruit.com** — Zen Cart admin panel (/volcano/login.php). Auth-gated.
  Host header REJECTED (403 on unknown Host) — unlike mail.com.
- **forums.adafruit.com** — Discourse behind CF challenge.
- **learn.adafruit.com** — Rails learning system (403 on API paths).

## IO API auth flow (the key to all testing)

1. Browser → `io.adafruit.com/api/v2/sign_in` → 302 to accounts SSO
2. POST accounts.adafruit.com/users/sign_in (Devise)
3. Redirect back → `GET /api/v2/access_token?code=...&response_type=code&state=...`
4. App uses `Authorization: Bearer <JWT>` (claims: tid, exp) for all /api/v2/ calls
5. AIO key (`aio_` + 28 chars, high entropy) via `X-AIO-Key` header — shown in "aio-key-modal" after clicking "View Adafruit IO Key"

## IO API endpoint map (extracted empirically by driving the SPA)

- `/api/v2/user` — user profile + subscription + limits
- `/api/v2/{username}/feeds` — list/create feeds (visibility: private/public)
- `/api/v2/{username}/feeds/{key}` — feed CRUD
- `/api/v2/{username}/feeds/{key}/data` — feed data (POST accepts arbitrary values incl. huge negatives, unicode — by design)
- `/api/v2/{username}/feeds/{key}/data/chart` — chart data
- `/api/v2/{username}/dashboards` — dashboards
- `/api/v2/{username}/dashboards/{key}` — dashboard detail
- `/api/v2/{username}/dashboards/{key}/blocks` — dashboard blocks
- `/api/v2/{username}/groups` — groups
- `/api/v2/{username}/triggers` — triggers (operator: lt/gt words not symbols; actions: to_feed_id/action_value/email templates — NO webhook action)
- `/api/v2/{username}/dynamic_actions` — bytecode automation (BETA v1.0.0-beta.1)
- `/api/v2/{username}/activities` — audit log (own-scoped)
- `/api/v2/account/public_profile`
- `/api/v2/sessions`

## IDOR matrix result (CLEAN)

Token acct1 vs acct2 private resources: list→200 [] (private not listed), read→404 "not permitted", write/update/delete→404/401. Direct-ID paths (/api/v2/feeds/{id})→404. API is username-scoped.

## Dynamic actions bytecode (SSRF/RCE attempt — BLOCKED)

Bytecode: `{"version":"1.0.0-beta.1","settings":{},"expressions":[...],"triggers":[...]}`. Server-side async validation marks unknown expression types as `validation_status: "invalidated"`. Tested http_request/http/fetch/webhook/set_feed/email/log → ALL invalidated. Only empty bytecode validates. `/run` endpoint exists but version-gated. No SSRF/RCE vector.

## MQTT ACLs (CLEAN — both directions)

io.adafruit.com:8883 (TLS), auth = username + AIO key. Subscribe own topic → granted. Subscribe other user's private feed → SUBACK refused (qos 128). Publish to other user's topic → client-side QoS 0 success but broker DROPPED (verified: victim feed empty).

## Zen Cart admin identification

`volcano.adafruit.com/volcano/includes/stylesheet.css` contains `@copyright Copyright 2003-2006 Zen Cart Development Team` — the fastest way to ID a Zen Cart admin. Known CVE paths (sqlpatch.php, password_forgotten.php, etc.) all 404. Host header → 403.

## Pitfalls

- **Gmail +alias canonicalization**: Adafruit canonicalizes email (strips +tag) — cannot create multiple test accounts with +aliases. Use mail.tm for acct2.
- **Cross-origin fetch from accounts.adafruit.com to www.adafruit.com** → CORS blocked in Playwright. Navigate to the target origin FIRST, then fetch same-origin.
- **Livewire/none** — Adafruit is Rails/Devise, not Livewire.
- **Shop add-to-cart**: no server-rendered form on product pages (JS-driven or DigiKey-only). The legacy Zen Cart POST (index.php?action=add_product) 301s to /product/{id}.
