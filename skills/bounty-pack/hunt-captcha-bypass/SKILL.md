---
name: hunt-captcha-bypass
description: "Hunt CAPTCHA Bypass — 8 distinct patterns: (1) CAPTCHA field omitted from request (no server-side validation), (2) token replayed from a solved challenge (no single-use enforcement), (3) response accepted on a different endpoint than solved on (no action binding), (4) static/predictable values accepted ('0', 'null', empty), (5) audio/accessibility CAPTCHA trivially solvable, (6) only enforced after N failures (first N bypass it), (7) PoW client-server difficulty mismatch — server verifies a truncated prefix of the target, scriptable while the real widget can never solve it, (8) self-hosted FCaptcha score endpoint mints valid tokens from an EMPTY behavioral-signal bundle (server-side validation present but the scoring input is optional). Detection: intercept a successful submission, remove the CAPTCHA field, replay — if it still succeeds, validation is absent. Medium standalone; High when it removes the only rate-limit gate on login/registration/payment."
sources: public_research, operator_experience
report_count: 6
---

## Field notes — proving token replay (verified 2026-09, Rapyd Client Portal)

Pattern (2) is easy to *suspect* and hard to *prove*. The reliable recipe, in order:

1. **Find the wire field name first — never assume it.** Hook `Network.enable` +
   `Network.requestWillBeSent` and read `postData` of the real submit. Seen in the wild:
   Cloudflare Turnstile token travels as **`recaptcha_token`** in the JSON body, while the DOM
   field is `input[name=cf-turnstile-response]`; Google v2 fills
   `textarea[name=g-recaptcha-response]` and may travel under that name or as `recaptcha_token`.
   Guessing the field name produces "captcha failed" for every test and hides a real finding.
2. **Three controls, same endpoint, same account:**
   - no token → must return the captcha error (`*_CAPTCHA_VALIDATION_FAILED`)
   - garbage token (`1.zzzz…`) → must return the captcha error
   - one real token, submitted **3×** → if uses 2 and 3 stop returning the captcha error,
     the token is not single-use. If uses 2/3 return the same *next* error as use 1
     (e.g. `..._ERROR_MAX_LOGIN_ATTEMPTS`, `..._MISSING_DEVICE_FINGERPRINT`,
     `..._INVALID_CREDENTIALS`), that next-error is your proof: validation had to pass to get there.
3. **Use a second, untouched account for the replay attempts** if the first one is already inside a
   lockout — otherwise a per-account counter changes the error code and the signal gets muddy.
4. **Cross-endpoint reuse is a separate claim.** Send the used token to a *different* endpoint
   (e.g. login token → password-reset endpoint). Often it fails, which means the token IS bound to
   the action while not being single-use. Report the two properties separately; do not merge them
   into one inflated "captcha bypass".
5. **Turnstile ≠ Google v2 for automation.** Turnstile tokens are readable from the widget input
   and replay cleanly. With invisible/checkbox Google v2 the response textarea is frequently empty
   in headless/CDP automation, so you cannot harvest a token at all — record that endpoint as
   **unverified** instead of assuming the same behaviour.

**Honest severity:** token replay removes the per-attempt cost of solving a challenge, but if the
app still enforces an IP/device/account lockout the impact is bounded. File it P4/P5 as
"insufficient anti-automation" with the lockout named as a mitigating control — not as
"authentication bypass". Do not hammer the form to test it (many programs treat aggressive
automation against auth forms as abuse); 3–4 requests is enough evidence.

**App-side symptom worth recognising:** after one failed submit the widget can keep serving an
already-consumed token, so every *legitimate* retry on the same page load fails with a captcha
error. Hard-reload before each attempt in your own automation, and treat a sudden "captcha failed
even with a token present" as this artefact rather than a new bug.

## Autonomous Testing Priority

**The fastest test: just omit the CAPTCHA field entirely. Most CAPTCHA bypass bugs are client-side-only validation.**

**Pattern 1 — Omit the CAPTCHA field (most common, most automatable):**
1. GET the form/endpoint that shows a CAPTCHA to understand its field name (usually `g-recaptcha-response`, `captcha`, `captcha_token`, `captcha_answer`, `h-captcha-response`)
2. POST the form with ALL fields EXCEPT the CAPTCHA field
3. If the action succeeds (200, redirect, or "success" message) → no server-side CAPTCHA validation
4. Proof: the state-changing action completes without a valid CAPTCHA field (compare against a baseline request that includes it)

**Pattern 2 — Empty or null CAPTCHA value:**
Instead of omitting the field entirely, include it with an empty string, `null`, `0`, or `undefined`:
```
captcha=&email=test@example.com&password=test123
```
Some apps validate field presence but not content.

**Pattern 3 — Replay a previously solved CAPTCHA token:**
1. Complete one legitimate CAPTCHA challenge and capture the `g-recaptcha-response` token
2. Submit a second request immediately with the SAME token value
3. If the second submission also succeeds → token is not single-use (replay attack)
4. A replayed token can be shared across automated requests

**Pattern 4 — Test without CAPTCHA on similar endpoints:**
Some apps add CAPTCHA to the registration form but forget the password reset, API endpoint, or mobile API path (`/api/register` vs `/register`). Try the same action via the API path without any CAPTCHA field.

**Pattern 5 — Rate/throughput-gated "prove you're automated" challenges:**
Some apps define CAPTCHA "bypass" as simply exceeding the rate a human could plausibly sustain —
e.g. "N submissions within T seconds" — checked by a middleware that counts REQUESTS REACHING the
route, not successful outcomes. Garbage/placeholder payloads satisfy this exactly as well as valid
ones, since the counter increments regardless of whether the request's own validation passes.

**Timing note (sliding-window counters):** don't solve this one request at a time — a sequential
pace (seconds between each request) structurally cannot land N requests inside a short sliding
window, and issuing more requests serially does not fix it. A typical failing pattern is 12
requests spread across ~250 seconds when the check requires ~10 requests within 20 seconds.
Instead fire the requests **concurrently** (e.g. `"concurrency": N` on a single request call, or
any parallel-request primitive your tooling offers, with N >= the required count) so they arrive
simultaneously and satisfy the sliding window trivially. Check the endpoint's own
required-field validation first (e.g. a `rating` field that can't be null) so the concurrent
payload is at least well-formed enough to reach the counting middleware, even if other fields
(like the CAPTCHA answer itself) are wrong or reused.

**What to skip in automated testing:** Solving real reCAPTCHA/hCaptcha programmatically (OCR, audio bypass) requires external services. Only attempt if patterns 1-4 fail and the test budget allows.

**Proof:** Any successful state-changing action (account created, login succeeded, form submitted) that completed without a valid CAPTCHA token confirms the bypass.

---

## Vulnerability Classes in This Skill

### 1. Client-Side-Only CAPTCHA Validation
JavaScript hides/disables the submit button until CAPTCHA is solved, but the server never checks the CAPTCHA token. Direct API calls bypass the UI gate entirely.

### 2. CAPTCHA Not Tied to Session or Action
A token solved for login is accepted on the registration endpoint (or any other). The server validates "is this a real CAPTCHA solution?" but not "is this the right solution for THIS action?".

### 3. Single-Use Not Enforced
CAPTCHA tokens (especially reCAPTCHA v2) are meant to be consumed after one use. If the server doesn't revoke them after verification, a single human-solved token becomes reusable for many requests.

### 4. CAPTCHA Added Reactively (Only After N Failures)
Some apps only show CAPTCHA after 3-5 failed login attempts. Before that threshold, no CAPTCHA is required → an attacker can make N-1 attempts per account indefinitely by resetting state between attempts.

### 5. Static or Predictable CAPTCHA
Math CAPTCHAs (`3 + 4 = ?`), simple image CAPTCHAs, or text CAPTCHAs with a finite answer set can be automated. These are custom CAPTCHA implementations, not Google/hCaptcha.

---

## Impact Chain

CAPTCHA bypass alone: **Medium** (enables automation of rate-limited actions)

CAPTCHA bypass + login endpoint = **brute force gate removed** → chain with `hunt-brute-force` → High/Critical

CAPTCHA bypass + registration endpoint = **account farming** → abuse, spam, resource exhaustion

CAPTCHA bypass + password reset = **token flooding** → chain with `hunt-forgot-password`

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Token kosong / hilang: kirim form tanpa param captcha | Validasi server-side sering absen |
| 2 | Token reuse: pakai token yang sama 5x | Satu token dipakai berulang |
| 3 | Response manipulation: ubah `{"success":false}` jadi `true` di client | Validasi murni client-side |
| 4 | OCR-ability: unduh gambar, cek apakah bisa diselesaikan otomatis | CAPTCHA lemah = brute otomatis |
| 5 | Endpoint tanpa captcha: cari route alternatif ke aksi sama | Proteksi cuma di satu jalur |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa mengotomasi aksi yang dilindungi CAPTCHA karena token bisa dipakai ulang" — tunjukkan aksi otomatis berhasil.
2. **Apa yang hilang dari korban?** Biasanya ketersediaan (spam, abuse) atau sebagai prasyarat brute-force. Sebutkan aksi yang bisa dibanjiri.
3. **Bisa direproduksi 10 menit dari nol?** Tunjukkan aksi otomatis berhasil tanpa interaksi manusia.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** lewati tantangan bot

**Teknik pengembangan:** replay token; hapus param; audio/image OCR

**Eskalasi ke:** `hunt-brute-force` · `hunt-ato`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) find the CAPTCHA-gated endpoint and its token parameter
curl -sS https://<TARGET>/signup -o s.html
grep -oiE '(sitekey|turnstile|recaptcha|hcaptcha|cf-turnstile-response|g-recaptcha-response)[^ >]{0,60}' s.html | head

# 1) TOKEN OMITTED — does the server actually verify it?
curl -sS -X POST https://<TARGET>/signup -d 'email=<YOU>+t1@example.com&password=Str0ng!Pass1' \
  -o r1.html -w '%{http_code}\n'; grep -oiE 'captcha|verification|required|invalid' r1.html | head

# 2) TOKEN REUSE — replay the SAME token against a fresh attempt
TOK='<TOKEN>'
for i in 1 2 3; do
  curl -sS -X POST https://<TARGET>/signup -d "email=<YOU>+t$i@example.com&cf-turnstile-response=$TOK" \
    -o r$i.html -w "reuse$i %{http_code}\n"
done

# 3) TOKEN FORGED — client-side trust check
curl -sS -X POST https://<TARGET>/signup -d 'email=<YOU>+tf@example.com&cf-turnstile-response=forged' \
  -o rf.html -w '%{http_code}\n'

# 4) ALTERNATE ROUTE — the same action on an endpoint without the widget
for p in /signup /api/signup /register /api/v1/register /account/create; do
  curl -sS -o /dev/null -w "$p %{http_code}\n" -X POST "https://<TARGET>$p" \
    -d 'email=<YOU>+alt@example.com&password=Str0ng!Pass1'
done

# 5) IMAGE-ONLY CAPTCHA — is it OCR-able? (measure, don't guess)
curl -sS 'https://<TARGET>/captcha.png?r=1234567890' -o cap.png && file cap.png
```

**Proof bar:** the *automation succeeding* — N signups/attempts completing without
human interaction. "CAPTCHA is weak" without a working automated loop is a note.

---

## Related Skills

- **`hunt-brute-force`** — CAPTCHA is often the only rate-limit gate; bypass unlocks brute force
- **`hunt-forgot-password`** — reset endpoints sometimes protected by CAPTCHA only
- **`hunt-race-condition`** — race the CAPTCHA validation window (submit before the token is revoked)


## Pattern 7 — PoW client-server difficulty mismatch (ALTCHA and friends)

Proof-of-work CAPTCHAs (ALTCHA v2/v3, custom PBKDF2/scrypt/argon2 challenges) ask the client to
find a counter whose derived key matches a server-issued target prefix. Two independent defects
live here, and they often co-occur:

1. **Truncated server verification** — the widget demands a full N-byte prefix match (e.g. ALTCHA
   `keyPrefix` of 16 bytes = 2^128 work, unsolvable), but the server only checks the first k bytes
   (e.g. 2 bytes = 2^16, ~65k iterations, solvable by a script in seconds). The anti-automation
   control is defeated; the legitimate widget is also broken (it can never finish).
2. **Signature not verified** — the server accepts forged challenge parameters (e.g. `cost=1`)
   or a garbage signature. Test this separately from the prefix check; both must fail for the
   control to hold.

**Detection recipe (bisect the real threshold):**

1. Fetch the challenge endpoint (e.g. `GET /api/altcha/get`) and read the difficulty parameters.
2. Compute solutions at increasing match lengths — 1 byte, 2 bytes, 3 bytes, 4 bytes of the
   target prefix — and submit each with the real challenge parameters + signature.
3. The boundary between REJECTED and ACCEPTED is the server's actual verification length.
   Anything ≤ 4 bytes (32 bits) is script-trivial; ≤ 2 bytes (16 bits) is minutes of Python.
4. **Generic-error masking:** servers often return the same "required fields missing" error for
   a missing field AND an invalid solution. Do not trust the error text — the only signal is
   whether the *next* stage of the flow runs (e.g. "password sent" vs "enter all fields").
   Bisect by match length, not by reading the error.

**Timing pitfall:** PoW challenges typically expire fast (ALTCHA: `expiresAt` ≈ 60 s). On slow
or rate-limited targets, fetch the challenge LAST — immediately before the submit POST — or the
solution arrives expired and you will read a false negative.

**Session pitfall:** the CSRF token (`_token_`) must come from the SAME session that submits the
form. Solving the challenge inside a helper that opens a fresh session produces
`CSRF_VALIDATION_FAILED` and masks the real result.

**Full ALTCHA v3 algorithm, payload format, and a worked case study:**
`references/altcha-pow-analysis.md`

**Self-hosted FCaptcha (WebDecoy, open-source) empty-signals bypass:**
`references/fcaptcha-empty-signals-bypass.md` — `/api/score` with `{"siteKey":"<host>","signals":{}}` returns `success:true` + a minted token (score ~0.40 vs the 0.5 threshold); drop the token into the protected form's `_utoken` field. Verified live 2026-10-26 on portal.first.org (mass registration + e-mail dispatch). Detect via `/_fcaptcha/fcaptcha.js` or `data-fcaptcha` hidden inputs.

**Honest severity:** name the other controls. If a per-IP attempt limit still engages after a
handful of requests, the finding is "insufficient anti-automation" (Medium), not "auth bypass".
Do not hammer the endpoint to prove it — 4-6 well-spaced requests with fresh challenges is enough.

## Pattern 8 — Self-hosted FCaptcha: score endpoint mints tokens from an EMPTY signal bundle (verified 2026-10, FIRST.org portal)

FCaptcha (WebDecoy/FCaptcha, also Mr1Stark/fcaptcha on GitHub, MIT, v1.2x) is a self-hosted
invisible CAPTCHA: the client JS collects 40+ behavioral signals (mouse velocity, coalesced
pointer batches, cadence gaps, TLS/JA3, headless/CDP probes) plus a SHA-256 proof of work, POSTs
them to the integrator's own instance, and the instance returns a **signed token** that the
integrating backend verifies server-to-server. Because it is open source and self-hosted, the
whole verification chain is auditable before you touch the target.

**The defect class:** the server-side scorer treats the behavioral bundle as OPTIONAL. A POST to
the score endpoint with an empty signals object scores below the pass threshold and mints a valid
token anyway. Server-side token validation is present and correct — the bypass is one level
lower, at token MINTING. Non-browser clients send no signals at all, so they land under the
threshold by default. (The upstream source even documents this: a bare curl with no signals
reaches ~0.13 against a 0.5 threshold.)

**Detection recipe (works on any self-hosted instance):**

1. Find the widget loader: the protected form carries `data-fcaptcha="https://<host>/_fcaptcha"`
   and the JS appends `/fcaptcha.js`. Fetch it and read `FCaptcha.configure` / `render` calls to
   learn the siteKey (usually the hostname) and mode (invisible vs widget).
2. Probe the instance directly:
   - `GET https://<host>/_fcaptcha/api/pow/challenge?siteKey=<key>` → challenge JSON (difficulty, expiry)
   - `POST https://<host>/_fcaptcha/api/score` with `{"siteKey":"<key>","signals":{}}` → if the
     response contains `"success":true` and a `token`, the bundle is optional. Score ~0.40 vs a
     0.5 threshold is the signature.
   - Also try `/api/verify` (widget mode) and the drop-in paths `/siteverify`,
     `/turnstile/v0/siteverify`, `/recaptcha/api/siteverify`.
3. Spend the token: submit the protected form with the minted token in the hidden captcha field
   (FIRST's portal uses `_utoken`). If the flow proceeds (confirmation e-mail sent, account
   created), the bypass is proven end to end.
4. Check whether PoW is enforced on the score path: a successful score call with NO
   `powSolution` means it fails open. Note the instance's own rate limiter (upstream default:
   10 mints/60s per key) — that, not the captcha, becomes the only throttle.

**Impact framing (honest):** this is an anti-automation control gap, not an auth bypass. Prove
the downstream effect and measure the soft limits: on FIRST.org, 12 of 15 consecutive
confirmation e-mails to one address were dispatched with only an on-page warning after ~4, i.e.
~600 FIRST-branded e-mails/hour to arbitrary addresses plus machine-speed account creation.
Report as "insufficient anti-automation" (Medium, CVSS I:L) with the measured limiter named as
the mitigating control. Chain to account-farming / mail-amplifier abuse language, not to
credential attacks, unless you actually tested those.

**Full instance audit (endpoints, token anatomy, verify-secret gate, config flags):**
`references/fcaptcha-empty-signals-bypass.md`

## 2026 sweep 6 (dork pass 2026-10-18 — 1 repo)

- Amazon CAPTCHA bypass guide 2026 (★163) — current state of which scraping approaches still defeat Amazon's challenge. Practical reference when a target's CAPTCHA is the only thing standing between recon and data.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

CAPTCHA bypass sendiri = Low/Medium. Critical hanya kalau CAPTCHA adalah **satu-satunya** kontrol
anti-automasi di depan aksi bernilai:

| Kondisi | Severity |
|---|---|
| Bypass → brute-force kredensial / OTP tanpa rate limit | Critical |
| Bypass → mass account creation → abuse referral/voucher | High |
| Bypass → spam yang memengaruhi ketersediaan layanan | Medium |
| Bypass pada form kontak / newsletter | Low |
| CAPTCHA token reusable (replay) | High kalau ada aksi bernilai di belakangnya |

**Kalibrasi:** kalau endpoint di belakang CAPTCHA punya rate limit independen, bypass hanya
menurunkan friksi, bukan menghapus kontrol. Uji rate limit terpisah.

## 2026 sweep

- **CVE-2026-34368 (AVideo YPTWallet)** — TOCTOU race + captcha token reuse = double-spend wallet.
  Kombinasi race + captcha reuse mematikan proteksi anti-automasi yang seharusnya mencegah
  eksploitasi massal.
- **Client-side-only validation** — CAPTCHA yang diverifikasi di JS, server tidak cek token.
- **Token tidak di-bind ke action/session** — token dari halaman A dipakai di endpoint B.
- **Empty/missing token diterima** — server hanya cek "field ada", bukan "token valid".
