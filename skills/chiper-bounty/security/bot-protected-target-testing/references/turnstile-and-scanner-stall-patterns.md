# Turnstile-walled targets + scanner stall patterns

Worked case: `bytefederal.com` estate (Bitcoin ATM operator, bug bounty, 2026-10-20/21).
Every meaningful flow (KYC register, host-portal registration, scam-report submission,
scam-report login) sat behind **Cloudflare Turnstile** with server-side validation, and the
rest of the estate sat behind plain Cloudflare with bot management. Eleven rounds of testing
from every angle produced no payable finding — but the *tool-behavior* lessons below are
durable and cost real time to learn.

## 1. Turnstile beats headless AND headed Chromium — plan around it, don't fight it

Symptom chain (register.bytefederal.com, a SvelteKit/Astro SPA):

- Headless Chromium: `cf frames = 0` until you click submit; then the
  `challenges.cloudflare.com/turnstile/f/av0` iframe appears, **detaches on click**, and the
  `cf-turnstile-response` input stays `''` forever. App telemetry showed
  `turnstile_outcome: interactive_shown` → `interactive_deferred`.
- Headed Chromium with `--disable-blink-features=AutomationControlled` +
  `navigator.webdriver` undefined patch: identical — token never populates.
- The app **prewarms** Turnstile and only renders the interactive widget at submit
  (`phase:"prewarm"` vs `"submit"`), so waiting for the widget before clicking is wasted time.

**Rule:** if a flow is Turnstile-gated, do NOT burn the session trying to solve it in
automation. Instead (a) map the API contract from the JS bundles (the endpoint names, body
shapes, and auth chain are all client-visible), (b) verify server-side enforcement with
forged tokens (see §3), and (c) treat the gated flow as a documented coverage limit.

## 2. nuclei STALLS on Cloudflare-challenged hosts — kill it, go manual

A full-library nuclei sweep (`-tags exposure,misconfiguration,cve,... -rl 5 -c 4`) over 51
hosts where most are CF-fronted ran **30+ minutes with frozen output** — every template
request receives the JS-challenge page, templates fail/timeout, and the scan crawls. Only the
DNS-level `dns-waf-detect` template (which needs no HTTP) ever completed.

**Rule:** on a CF-heavy estate, expect nuclei to stall. Give it ~10 minutes, check the output
file mtime, and if frozen: kill it, record "nuclei sweep stalled on CF-challenged hosts —
documented limitation" in the ledger, and cover the same ground with targeted curl probes +
single-template runs against the few hosts that answer cleanly. Do not wait an hour for a
scan that will not finish.

## 3. Verifying gates without passing them: the status-code differential

You can fully map an auth chain without a single valid credential by reading status codes:

| Probe | Response | Meaning |
|---|---|---|
| `POST /endpoint` no body | `400 invalid request` | route exists, body validated |
| `POST /endpoint` wrong body | `422 [body.x] expected string` | **pydantic-style schema leak** — field names revealed |
| `POST /endpoint` valid body, no session | `401 authentication_required` | session-gated; body shape correct |
| `POST /endpoint` dummy token | `403 bot verification required` | server-side token validation enforced |
| `POST /endpoint` dummy token, empty string | `400 invalid request` | presence-check quirk (empty ≠ missing) |
| `POST /endpoint` + header w/ any value | `400` (body gate) vs `401` (header gate) | **presence-only header check** — value never validated |

Worked example (KYC chain): `phone/otp-challenge` → challengeToken;
`phone/request-verification {phoneNumber, challengeToken}` → SMS;
`api/auth/phone-number/verify {phoneNumber, code}` → session; `kyc/site-token` → 401;
`kyc/facetec-init` → 400 (needs SDK payload); `kyc/process-request` → 401 missing header,
but **any** header value passes the presence check and dies at the encrypted body. The whole
chain was mapped without SMS.

## 4. camoufox REST recovery (tab-create wedge)

The camoufox browser server (port 9377) accepts `/tabs` creates for ~30s then times out
(`tab create timed out after 30000ms`), and `/stop` returns `403 Forbidden`. Recovery:
`POST /start` (200, restarts the engine) → retry tab creation. The Hermes browser client may
be incompatible with it (read timeouts) — drive camoufox's REST API directly
(`/openapi.json` documents the full endpoint map) or accept the limitation.

## 5. Uniform-403 fuzz results are the WAF, not the app

ffuf with its default User-Agent against a CF bot-management host returns **identical 403s
for every path** (same size/word count) — including paths that curl with a browser UA answers
with 200/401/404. Rule (restated because it bites every engagement): before recording ANY
403 from a scanner, re-probe 2–3 of those paths with a browser-UA curl. Identical size across
all paths = burst-block; treat as no-result, not as "everything is 403".
