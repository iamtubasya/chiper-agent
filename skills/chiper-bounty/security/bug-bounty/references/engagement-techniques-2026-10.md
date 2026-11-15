# Engagement techniques — Byte Federal + Fastmail sessions (2026-10)

Condensed from two full engagements. Session-specific detail lives in each engagement dir;
this file is the reusable technique bank.

## Anti-bot wall escalation ladder (Cloudflare Turnstile)
Order that was actually tried (all failed on Turnstile-gated flows):
1. Playwright headless Chromium — CF fingerprinting fails interactive challenge
2. Playwright headed Chromium (real window) — still fails
3. Camoufox REST server (port 9377) — tab-create wedged; /stop Forbidden, /start works but sessions stall
Lesson: when Turnstile holds, STOP burning turns. Instead hunt for a SECOND auth door
(Byte Federal wallet had a Livewire `magic-link-login` component beside the QR login —
the magic link worked, just rate-limited per email: "Too many requests. Please try again in 57 minutes").
Check every login page for alternate flows (magic link, SMS, OAuth) before declaring a wall.

## Livewire 3 auth-flow testing
- POST /livewire/update needs: plain `_token` (from `<meta name="csrf-token">`) in the JSON body
  AND the EXACT current wire:snapshot. Stale snapshot → 404. X-CSRF-TOKEN with encrypted cookie → 419.
- Browser-driven call works; scripted replay with a stale snapshot 404s (checksum mismatch).
- Component names in snapshots reveal auth modules (magic-link-login, q-r-login) — enumerate
  all `wire:snapshot` blocks on the login page.

## Signup/JMAP API contract probing (Fastmail pattern)
- `api.fastmail.com/signup/api` trust gate = client-set header `x-trustedclient: Yes`
  (without it: 401 "Request not from trusted source").
- JMAP methodCalls need 3 elements: `[name, args, callId]` — 2 elements →
  "Not a valid JMAP request (method 1 array not 3 elements)".
- Signup/createAccount contract: `{serviceLevelName,name,username,password,dataRegion,verificationId,verificationCode}`.
  dataRegion is CLIENT-controlled (us/eu). Verification validated server-side
  (error types: notFound/expired/inUse/incorrectCode). Geo-gate leaks detected country
  (`needsVerification {countryCode:"ID"}` → mandatory SMS for high-abuse countries).
  Rate-limited (rl3) after a handful of attempts — probe slowly.
- App module map: `/static/jmapui/{version}/app/module/desktop/{Module}.mod.js`
  (find version in `data-version` attr; find module filenames in bootstrap.js module map).
  Module names map to paid bug classes: OAuthToken, sudo (reauth), Passkey, TOTP,
  defangHTML/rewriteInternalLink (external-link protection).

## OAuth DCR + redirect_uri testing
- `.well-known/oauth-authorization-server` on the API host = full metadata + DCR endpoint.
- Fastmail DCR accepts ONLY localhost/127.0.0.1 redirect URIs (all https rejected, even its own
  domain) and NORMALIZES: strips port, 127.0.0.1→localhost. Registration returns client_id immediately.
- `/oauth/authorize` passed ANY redirect_uri (incl. evil.example.com) through to the app's
  consent page — validation lives inside the authenticated flow, so unauth testing only proves
  the API layer doesn't pre-validate. Don't report "authorize accepts any redirect_uri" without
  completing an authenticated flow to code issuance.

## Tool behavior on Cloudflare-challenged hosts
- ffuf default burst → UNIFORM 403 from CF bot management (not real 403s). Distinguish:
  same status + same byte count for every path = CF block. Direct curl with browser UA works.
- nuclei full-template sweep STALLS on CF-challenged hosts (every request JS-challenged);
  30+ min for one info finding. Kill it, document the limitation, rely on manual + targeted checks.
- Direct origin IPs throttle after heavy probing (000 timeouts) — pace requests, expect soft bans.

## Verification pitfalls (scanner label ≠ finding)
- subzy flagged influx/ldbapi/ldbapiglobal as "Cargo Collective" takeovers = FALSE POSITIVES:
  all resolved to Cloudflare proxy IPs; the generic CF 404 matched the fingerprint.
  Always check DNS class (CF proxy vs dangling CNAME) before believing a takeover flag.
- byp4xx takes a bare URL (no -H header flag — it tries to read the value as a file).
- gmail/google_token.json refresh died with invalid_grant (Google 7-day testing-mode expiry) —
  re-auth needs browser consent; email-reading tasks (magic links) are blocked until then.

## Target-switch quarantine workflow (operator rule: hapus = _QUARANTINE + manifest)
1. `mv <engagement>/* _QUARANTINE/<target>_<ISO-timestamp>/`
2. Write MANIFEST.json (reason, engagement summary, key artifacts, recovery instructions)
3. If mv fails "Device or resource busy": a zombie child process holds the file
   (Hermes kills the bash wrapper, not the child) → `taskkill //F //PID <pid>` then retry
4. Empty leftover dir that won't rmdir = shell CWD handle — harmless, self-clears; don't fight it

## React Native APK RE (quick path)
- jadx decompile gives only the standard RN wrapper (MainActivity/MainApplication/BuildConfig);
  the real logic is the Hermes bundle (`assets/index.android.bundle`).
- Hermes string table concatenates strings (raw ASCII scan is noisy) but secret-pattern mining
  still works: Sentry DSN, `phc_` PostHog keys, `pk.eyJ` Mapbox tokens, `AIza` Firebase keys.
- Web-SDK keys found in JS (e.g. FaceTec production key passed to initializeWithSessionRequest)
  are public BY DESIGN for browser SDKs — verify against the vendor API before claiming exposure.
