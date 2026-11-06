# Byte Federal engagement — 2026-10-20/21 (11 rounds, no payable finding)

State snapshot for re-engagement. Program:
https://www.bytefederal.com/security-bug-bounty/ (Critical $10–20k / High $5–10k /
Medium $1–5k / Low $50–1k; safe harbor stated; scope = bytefederal.com + official
subdomains, ByteWallet mobile+backend, ByteVault, ByteConnect, ATM software excluding
physical). Artifacts: `D:/data hermes/bug-bounty/bytefederal_2026-10/` (PHASE_LOG.md,
TOOL_LEDGER.json, gau_all.txt, APK + jadx output).

## Why nothing paid (and what would change that)

Every money path is gated **by design**, not by an oversight:

| Surface | Gate | Status |
|---|---|---|
| Wallet web (`wallet.bytefederal.com`, Laravel+Livewire) | registration is **mobile-app-only** (signup modal: "Create your account in the app"); both `/register` and `/web/register` POST → 500 (deprecated, fail-closed); magic-link only fires for existing users | no web account creatable |
| KYC (`register/verify.bytefederal.com` → `api-register.bytefederal.com`) | SMS OTP → Turnstile → FaceTec-encrypted biometric payload | chain mapped, unforgeable without app+camera |
| Money API (`mobileapi.bytefederal.com`, DRF) | SMS-OTP session (`/v2/users/*` 401) | `/v2/locations` open (public ATM data, by design) |
| ByteAuth QR (`auth.bytefederal.com/api/fastbyte`) | mobile-app ECDSA signature | verified: fresh sid → "Session not found" in all payload variants |
| Host portal (`portal.bytefederal.com`, Next.js) | Turnstile on register; login solid (generic errors, 2FA, lockout) | — |
| Scam reports (`reportscams.bytefederal.com`, SvelteKit) | `/auth/login|recover|register` = SvelteKit actions + Turnstile; public report DB is by design | — |

**Single blocker that unlocks two surfaces:** one SMS-receivable test number (KYC document
journey + mobileapi `/v2/users/*`). Everything else was verified-negative.

## Verified negatives (do not re-test without new info)

- subdomain takeover: subzy flagged influx/ldbapi/ldbapiglobal as "Cargo Collective" —
  **false positives** (all resolve to CF proxy IPs; generic CF 404 matched the fingerprint).
  Bare-IP hosts (onyx/tagcase/skynyxvanta) are live SSH servers, not dangling.
- Origin hunt: DNS categorized all 90 subs (35 CF / 8 Tailscale / 22 bare / 25 NXDOMAIN).
  KYC cluster origin 104.248.125.225 serves only a default Apache vhost for foreign Host
  headers — no CDN bypass for CF-fronted apps. No exposed DB ports anywhere (naabu).
- Request smuggling (CL.TE/TE.CL): CF 400s the malformed framing.
- CORS: no origin reflection on mobileapi/api-register.
- WP (`news.bytefederal.com`): wp-json/xmlrpc 403 (byp4xx: no bypass works); plugins
  current (jetpack-boost 4.8.1 > patched 3.4.6); username enum via `/author/<slug>/`
  (admin, arusso, carlp) = informational only.
- MCP server (`mcp.bytefederal.com/sse`): live "bytefederal-bitcoin-atm" v1.0.0, 4 tools,
  all public location data; no IDOR/injection; session not validated but stateless.
- Telemetry NoSQL injection: strict typed validation (400 on `$ne/$gt/$where/$regex`).
- Certified endpoint (`wallet.../web/certified/<hash>`): prefix lookup, min 20 hex chars,
  hex-validated; SQL wildcards rejected.
- Gmail token for magic-link testing: revoked (Google 7-day testing-mode expiry) — re-auth
  before any email-reading task.

## Reusable techniques surfaced here (see owner skills for the general form)

- Livewire 3 magic-link/webhook auth flow + rate-limit oracle → `modern-webapp-auth-hunting`
- Scanner-FP verification + origin hunting + Tailscale-IP-in-public-DNS finding class →
  `hunt-session-gateway`
- CF/Turnstile tool-behavior + auth-chain differential mapping → `bot-protected-target-testing`
  (`references/turnstile-and-scanner-stall-patterns.md`)
- RN/Hermes APK triage (jadx on the nested base APK of a split bundle; secret-pattern mining;
  thin-Java/fat-Hermes expectation) → `mobile-pentest`
