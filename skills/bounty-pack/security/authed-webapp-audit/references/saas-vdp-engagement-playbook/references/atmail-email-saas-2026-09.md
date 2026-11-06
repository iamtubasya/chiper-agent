# Atmail Bug Bounty — Session Reference (2026-09)

Concrete numbers, evidence, and debunks from a full-scope engagement against an email-SaaS
vendor (self-hosted program, email submission to `bugbounty@`). Useful as a calibration
reference for "hardened target, few findings, lots of coverage proof".

## Target shape

- Scope: `*.atmail.com`, `*.atmailcloud.com`, `*.junara.com` (self-hosted program, USD payouts
  Critical $5K / High $2K / Medium $500 / Low $50).
- Required traffic identifier header on ALL requests (self-hosted programs often require this —
  read the policy first). Rate limit ≤5 rps/host.
- Recon yield: 570 subdomains → 155 live hosts. Mostly identical SEP webmail clones + admin panel
  + API gateway + a separate account/billing portal.
- Stack: Atmail WebAdmin v11.3.1 (Zend PHP) behind nginx → AWS ELB; webmail SPA + api-gwy JSON API;
  login SPA (React Router v3.4.1); Junara account portal BFF (Node) with Chargebee; ops-api (FastAPI).
- **Policy quirk worth checking on every email-SaaS program:** §9.1 pre-declares whole classes as
  Informative ("most rate-limiting issues", "software version disclosure", "email/DNS posture",
  "SSL/TLS best practice"). Findings in those classes are effectively unpaid regardless of quality.
  Read the ineligible list BEFORE hunting, and weight effort toward classes they actually pay.

## Confirmed findings (2, both Medium)

### F1 — Missing login rate limiting / lockout disabled (CWE-307)
- `POST https://admin.atmailcloud.com/index.php/admin/index/login`
- **60 consecutive wrong-password attempts → HTTP 200 "Invalid username or password" every time.**
  No lockout, no CAPTCHA, no backoff; per-attempt 1.2–2.8 s (bcrypt cost only).
- **Cross-tool confirmed:** Python `urllib` (60 attempts) + `curl` (10 attempts) → identical.
- **Ground truth from the product's own config:** `GET /api/settings` (unauthenticated) returns
  `"blockDuration": 0` on every host tested → the lockout feature is off deployment-wide.
- Same absence on the customer webmail flow (`POST /webmail.junara.com/auth`, 40 rapid two-stage
  flows → 0×429/423).
- **Strength came from 4c (cross-component comparison)** — see below.

### F2 — Unauthenticated tenant configuration disclosure incl. third-party keys (CWE-200)
- `GET https://<any webmail/api host>/api/settings` → 200 with no credentials, on ~60 production
  AND staging hosts.
- Leaked: Google API keys + OAuth client IDs (`googleDrivePickerConfig.devKey/appId`), Dropbox
  app IDs (`dropboxPickerConfig.appId`), SSO auth URLs, password-reset/OTP copy, extension & licence
  posture, `blockDuration`, themes.
- **Honest impact cap:** probed the Google keys once against a Maps endpoint → `REQUEST_DENIED`
  (restricted to the Drive-picker API family) → no provable monetizable abuse. Reported as
  unauthorized disclosure of in-scope secrets, explicitly *not* ATO. Do not upgrade this claim.

## The cross-component comparison (the strongest evidence produced)

| Component | Control | Behaviour |
|---|---|---|
| Admin Zend login + api-gwy `/auth` | throttle / lockout | **none** — 60 attempts, 0×429, `blockDuration: 0` |
| Junara signup/billing BFF | throttle / preconditions / idempotency | `429 {"retryAfter":900}` after 5 OTP resends; `429 retryAfter:650` after 16 session creates; `409 PRECONDITION` on stage-skip; `Idempotency-Key` required on payment |

Same vendor, same control class, opposite behaviour → internal inconsistency. This is what turns a
"missing rate limiting" (pre-declared Informative) into an arguable defect. Quote their own
`retryAfter` field in the remediation.

## False positives killed (Response-Identity Rule, 4b)

| Candidate | Reality |
|---|---|
| `/ui/auth/signin.data`, `?_data=routes/...` → 200 | React Router **SPA shell** (text/html), not a data leak |
| `/vendor/composer/*.php` → 200 | PHP **executing** — 0 bytes returned, no source disclosure |
| `/index.php~` → 301 | nginx **rewrite to `/`**, not a backup file |
| `/activate`, `/api/signup` → 202 | **SiteGround CAPTCHA** interstitial (`/.well-known/sgcaptcha/`) |
| "locked"/"blocked" keyword in admin HTML | Boilerplate JS string about popup blocking |
| `X-Forwarded-Host: marker` echoed in `/auth/spa/config` JSON | Lookup echo; JSON-escaped, `no-cache`, no Location/cookie → **no impact** |
| `redirect_uri=evil` echoed in signin `Location` | Signin bounce echoing the param; validation at token exchange |
| 9 "dangling" CNAMEs (target NXDOMAIN) | Targets inside victim's own apex → **not registrable** → DNS hygiene, not takeover |

## Also negative (coverage proof)

sqlmap -r (raw request w/ fresh session cookie + valid single-use CSRF) → not injectable, 403×1490;
HTTP smuggling (CL.TE / TE.CL / obfuscated) → blocked by `awselb/2.0`; CORS reflects Origin but **no
`Access-Control-Allow-Credentials`** → not exploitable; OIDC `redirect_uri` requires PKCE; GObuster
0 hits (403 wildcard); nuclei (takeover/exposure/misconfig/cve) 0 findings; interactsh OOB **2
separate listeners → 0 callbacks**; cross-tenant CSRF matrix (5×5) → same-host only; user enumeration
n=12 interleaved → identical responses; WordPress 100% Cloudflare-blocked.

## Tool-invocation notes that cost time

- **sqlmap against a Zend login form:** `--csrf-url` is **incompatible with `--threads`**; and
  `--csrf-token` regex fails when the token is a **session-bound single-use** value (not per-page).
  Working method: fetch the login page (fresh cookie jar + token), write a **raw HTTP request file**,
  then `sqlmap -r req.txt -p <param> --level=3 --risk=2 --batch`.
- **dirsearch:** `--format` flag did not exist in this build → drop it; use `-o file --format plain`
  only if supported, else default output.
- **gobuster** on a host that 403s unknown paths returns 0 hits (len-118 wildcard) — use
  `--exclude-length` or fall back to dirsearch before concluding "nothing there".
- **Layer-ordering trap (see also triage-validation):** a `400 {"detail":"Access denied"}` on every
  FastAPI path is a **middleware block**, not absence of the route.
- **OTP polling:** list ALL recent senders, never a sender-filtered match — a filtered match grabbed
  an unrelated vendor's "Your code is…" email and produced a wrong-OTP submission.

## Reporting discipline applied

- Draft first, **never email before explicit user approval**; single send path only.
- Reported only what survived the false-positive diff; every negative documented in an
  `ENGAGEMENT_LOG.md` (5 deep-dive rounds) so coverage is provable to the user/triager.
- Declined to overclaim: F2 not called ATO; "write path for stored XSS" not claimed because every
  config-write candidate returned 401.
