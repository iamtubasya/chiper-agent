# Tripadvisor (Bugcrowd) — engagement notes, 2026-10

Slug: `tripadvisor-bb-og`. Progress dir: `D:/data hermes/bug-bounty/_progress/tripadvisor_v1/`.

## SCOPE REALITY — read the brief before firing a single tool

The reward table looks huge (Tier 1 $5000 … mobile $3500) but the OOS clauses delete most of the
juicy surface. Two clauses cost the most if missed:

1. **TAMG-owned brands that "operate independently" are OUT OF SCOPE — do not spend a session here:**
   - CruiseCritic — cruisecritic.com
   - TheFork / LaFourchette — thefork.com
   - Jetsetter — jetsetter.com
   - SeatGuru — seatguru.com
   - Viator — viator.com  ← looks in-scope (booking flow!) but is OUT
   - HelloReco — helloreco.com
   - plus minority-investment domains (e.g. traxo.com). If unsure, file a scope question instead of testing.
2. **IDOR in property-owner features is TEMPORARILY OUT OF SCOPE.** The whole owner/management plane is
   off-limits right now.

Also OOS: paths `/Trips`, `/Mobile*`, `/engineering`, `/WidgetEmbed-*`, `*adexpress`, `*wifi`,
`taplus`/`tripadvisor-plus`; hosts `prod bokun.*`, `ir.tripadvisor.com`, `*.tripadviser.at`,
`*.tripadvisor.cn`, `spotlight*`, `careers.*`, `*.experiences.zone`, `travelermail.com`; classes:
missing headers, content fraud, mass signup/spam, DoS, social engineering / open redirect (unless extra
impact), AI-system attacks, physical access.

## The two rules that constrain every authed test

- **Interacting with legitimate LIVE properties or customers is forbidden** — even "mark this review
  helpful". Test properties only.
- All created accounts/content must contain **"bugcrowd"**; the **User-Agent** must contain `bugcrowd`;
  forms that need no account get "bugcrowd" in a field.
- Test-property city is **Atafu (location id 446951)**; bank country UK, account 12345678, sort code 70 99 99.
- **TRAP:** the brief ships the test-property list as *names only* ("Test Hotel 1", "Test Vacation
  Rental 1", "Test Restaurant 1", "Test Tour", "Test Attraction"). If you extract the brief to markdown,
  the links are lost — and then **place-scoped features cannot be tested at all** (`/PostPhotos` +
  `/search` demand "Where'd you take these?" before a file input even renders; reviews, check-ins same
  shape). Either re-pull the brief HTML and keep the anchors, or park those features and say so. Never
  fall back to a live property to unblock yourself.

## What was tried and is HARDENED (skip on the next pass)

| Asset | Result |
|---|---|
| `api.b.tripadvisor.com/metrics` | **200, unauthenticated Prometheus, 440 families / ~950 KB** ← the finding (P4). Note the host: `api.tripadvisor.com/metrics` is a *different* host and returns 403. |
| `POST /data/graphql/ids` (www) | persisted-query allowlist; arbitrary ops rejected (see below) |
| `service.platform.tripadvisor.com` | Jetty 9.4.26; requires client cert / LDAP token |
| `api.tripadvisor.com` | Apache front: unknown paths 301 → www; `/config` `/content` `/metrics` 403 on every case/encoding/traversal variant |
| `gwapi1/2.tripadvisor.com` | 301 → www |
| `api.production.cde.tamg.cloud` | 403 |
| `hacapitest.developer.tripadvisor.com` | "IB Certification Tool", Spring Boot `/verify/login`; no actuator, Whitelabel error page, no trace; static under `/hacapiverifier/` |
| Vacation Rentals | vacationhomerentals/holidaylettings/flipkey/niumba → 301 www (decommissioned); rentals.tripadvisor.com → 503; **only www.housetrip.com is live** |
| `www.housetrip.com` | Next.js + Cloudflare affiliate to stay22.com; `/go/booking/<hash>?k=` is a FIXED redirect (k ignored); `/search?dest=` escapes to `&lt;…&gt;` and `\u003c…\u003e` in the RSC JSON → no XSS; no `/api/*` |
| subdomain enum tripadvisor.com | 825 hosts, **0 new** vs the stored list |

Jetty CVE non-bypass detail (worth knowing before you burn an hour): on `service.platform`,
`/health/..` and `/health/%2e%2e` return 200 `<NotImplemented/>` — but that is just path normalisation
to the **unauthenticated root `/`**, which already returns that. The security constraint on `/health`
itself held for every variant (28164/28169/34429 ladder).

## GraphQL persisted queries (the one real technique this engagement produced)

- Endpoint: `POST https://www.tripadvisor.com/data/graphql/ids`, body is a **JSON array**:
  `[{"variables":{…},"extensions":{"preRegisteredQueryId":"<16 hex>"}}, …]`
- Arbitrary operations are BLOCKED — `{"query":"{__typename}"}` →
  `{"errors":[{"message":"Arbitrary operations not available to untrusted clients"}]}` (HTTP 200).
  **That is a working control, not a finding.**
- Harvest the ids with `Network.requestWillBeSent` (a JS fetch/XHR hook, and even
  `Page.addScriptToEvaluateOnNewDocument`, **missed** these — the client is urql+batchFetchExchange).
  Captured on a single `/Hotels-…html` load:
  - `25f9ddb1ce629144` → `{"request":{"id":"<geoId>","type":"location"}}` (public location data)
  - `afb52b3d56ec64e7` → `{"userId":"<32 hex>"}` → `{"tripCount":{"trips":[…]}}`
  - `7b2d1f78e3dc76a4` → `{experimentKeys:[…],page,userId}`
  - `e61c41aba1e70583`, `32f2e254f7f08a0d` → hotel list/config
  - `71a4406fb83d70a3` → telemetry events
- **BOLA honesty rule from this session:** replaying `afb52b3d56ec64e7` with your own `userId` and with
  a random valid-format id BOTH returned `{"trips":[]}` (your account simply has no trips). Two empty
  results cannot distinguish "server ignores the id" from "server honours any id". Invalid-format ids
  error out — which proves only format validation. **Do not report this.** It would need a populated
  victim id, and `Trips` is OOS anyway.

## Deliverable rule (owner)

1 finding = 1 PDF PoC. **Validate the finding ≥3× BEFORE writing the PDF** (owner: *"pastikan sudah
divalidasi minimal 3x"*), then stage the report text **and the PDF as an attachment on a Gmail DRAFT**
(`[Gmail]/Draf`, IMAP `APPEND … (\Draft)`) — the owner takes it from there rather than from chat.
Bugcrowd itself takes submissions through the **web form**
(`/engagements/<slug>/submissions/new`), never by email. Toolkit account for this program:
`RESEARCHER_BC_EMAIL` (alias forwards to the owner's Gmail).

Evidence hygiene that mattered: verify a screenshot is non-blank *and* shows the target content before
embedding it (`--headless=new --dump-dom` on the same URL is the cheap proof when the vision model is
unavailable); and never trust `grep -o … | head -3 && echo FOUND` — the exit status is `head`'s, so the
echo always fires. Count matches explicitly.
