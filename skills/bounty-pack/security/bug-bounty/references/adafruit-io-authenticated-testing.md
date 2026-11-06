# Adafruit IO — authenticated API/MQTT testing techniques (2026-10-21)

Target: adafruit.com (maker platform + Adafruit IO IoT service). Rewards $25-$50 /
$100-$150 by CVSS band, published. Scope *.adafruit.com + *.adafruitdaily.com
(makecode.adafruit.com OOS — Microsoft). Registration is OPEN internationally (unlike
Fastmail/mail.com) — self-provisioned 2 test accounts.

Result of the session: no bounty-worthy findings. Target is hardened. The techniques below
are the reusable part.

## IO API auth model

- Browser session != API auth. The IO SPA authenticates API calls with
  `Authorization: Bearer <JWT>` obtained from an OAuth-ish exchange
  (`/api/v2/sign_in` -> accounts SSO -> `/api/v2/access_token?code=...`).
- **Capturing the Bearer from Playwright:** register a `page.on("request")` handler, filter
  `"/api/v2/" in url`, and stash `r.headers["authorization"][7:]` when it starts with
  `Bearer `. Then call the API from inside the page with
  `fetch(path, {headers: {"Authorization": "Bearer <tok>"}})` — the token is short-lived, so
  capture and use in the same session.
- **AIO key**: shown in the `aio-key-modal` after clicking the "View Adafruit IO Key" link;
  the value sits in `input[name="aio_key"]`. Format `aio_` + 28 chars (high entropy, not
  enumerable). API accepts it as the `X-AIO-Key` header.

## Full IO API map (extracted empirically — navigate the SPA, capture requests)

`/api/v2/user`, `/api/v2/{u}/groups`, `/api/v2/{u}/dashboards`,
`/api/v2/{u}/dashboards/{key}`, `/api/v2/{u}/dashboards/blocks`,
`/api/v2/{u}/dashboards/settings`, `/api/v2/{u}/feeds`, `/api/v2/{u}/feeds/{key}`,
`/api/v2/{u}/feeds/{key}/data`, `/api/v2/{u}/feeds/{key}/data/chart`,
`/api/v2/{u}/dynamic_actions`, `/api/v2/{u}/triggers`, `/api/v2/{u}/activities`,
`/api/v2/account/public_profile`, `/api/v2/sign_in`, `/api/v2/access_token`,
`/api/v2/sessions`. The app JS is an abstracted client — literal path greps return nothing;
navigate-and-capture is the way.

## IDOR matrix pattern (with a second account)

- **Gmail `+alias` does NOT give a second account** — Adafruit canonicalizes the address
  (strips the +tag; "The canonical form of your email is already taken"). Use a temp mailbox
  (mail.tm API: POST /accounts, then /token) for account 2.
- Account 2 must sign into IO once (its IO profile is created on first login) and create the
  private victim resources (feed + dashboard) before the matrix.
- Run with account 1's Bearer: list / read / write / update / delete of account 2's
  feeds-dashboards-groups. Result here: list returns `[]` (private not listed), read 404
  "not permitted", write/update/delete 404/401 — clean.
- Direct-ID paths (`/api/v2/feeds/{id}`) 404 — everything is username-scoped.

## MQTT topic ACL test (paho-mqtt, io.adafruit.com:8883, TLS)

- username = IO username, password = AIO key.
- Subscribe own topic -> granted QoS 0; subscribe another user's private feed ->
  **SUBACK refusal (granted QoS 128)**.
- Publish to another user's topic returns client-side success at QoS 0 (fire-and-forget) —
  **that is NOT proof**. Verify from the victim's account that the feed is still empty; the
  broker silently dropped the write. Always close the loop from the receiving side.

## Bytecode automation (dynamic_actions, v1.0.0-beta.1) — injection probe

Dynamic actions carry a `bytecode` object `{version, settings, expressions[], triggers[]}`
executed server-side. Probe by creating actions with candidate expression types and reading
`validation_status` / `bytecode_validation_errors` back:

- `http_request` / `http` / `fetch` / `webhook` / `set_feed` / `email` / `log` — ALL came back
  `invalidated` (async server-side validation; creation returns 200 first). Only empty
  bytecode validates. No SSRF/RCE via expression injection.
- `/api/v2/{u}/dynamic_actions/{id}/run` exists but is version-gated ("This app is out of
  date").
- Generalizable move: when an API validates a payload asynchronously, create-then-poll the
  resource and use the validation-status differential as the oracle.

## Trigger schema (cracked from the app bundle, not the docs)

Operators are the words `lt` / `gt` (symbols `<` `>` are rejected with "Operator is not
included in the list"). Actions are `to_feed_id` / `action_value` / email templates —
there is **no webhook action**, so the classic trigger->webhook SSRF does not exist.

## Stored-XSS check on feed data

POST an XSS payload as a feed `value` (the JSON API stores it raw — by design for a data
API), then load the dashboard and grep the DOM for the unescaped payload. Here the dashboard
did not render it unescaped — negative.

## Other Adafruit surface notes

- volcano.adafruit.com = Zen Cart admin (`/volcano/login.php`, admin_name/admin_pass +
  securityToken; stylesheet says Zen Cart). Hardened: unknown `Host` -> 403 (unlike mail.com),
  known Zen Cart paths (password_forgotten/sqlpatch) 404, zenAdminID cookie set on failed
  login but URL-jsessionid fixation not possible.
- blog.adafruit.com = WordPress: /wp-json, /xmlrpc.php, /wp-login.php all 403/404.
- Shop: legacy Zen Cart endpoints deprecated (301 to /product/...); several products are
  DigiKey-fulfilled (no direct add-to-cart); /api/products is an open 7.8MB public catalog
  (by design).
- Cleanup after testing: DELETE the created dynamic_actions/feeds/groups (verified 200) —
  log state changes per the engagement-hygiene rule.
