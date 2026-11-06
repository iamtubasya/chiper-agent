# Cloudflare Bot Management + Turnstile: diagnosing walls, extracting contracts

Worked case: Byte Federal estate (2026-10-20). Companion to the ALTCHA reference in this skill.

## 1. The uniform-403 wall (CF Bot Management vs the application)

CF Bot Management answers blocked tool UAs with a 403 that is **byte-identical on every path**
(observed: 5863 bytes / 668 words on every ffuf hit across wallet + mobileapi hosts).

Diagnostic ladder:
1. Content-discovery run returns same status AND same size for every path → that's the bot
   manager, not the app. NOT "all paths 403" (fake negative), NOT a finding.
2. Re-run the identical wordlist with a real browser UA
   (`-H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"`).
   ffuf/nuclei default UAs (`ffuf/2.x`, `Nuclei - ...`) are fingerprinted instantly.
3. Plain curl with a browser UA still passes on many CF estates — only escalate to a real
   browser when the body is an actual challenge page ("Just a moment...", cf-ray + challenge JS).
4. nuclei on CF-challenged hosts stalls in retry storms — kill after ~10 min, switch to targeted
   probes. Don't run nuclei full-tag sweeps at CF-challenged hosts.

## 2. Turnstile-gated APIs: the contract is recoverable even when the widget isn't solvable

CF Turnstile (invisible/managed) has beaten headless AND headed Chromium in practice — the
widget iframe renders
(`challenges.cloudflare.com/cdn-cgi/challenge-platform/.../turnstile/f/av0`) but no token is
ever issued to automation. Stealth Firefox (camoufox) may also wedge at tab creation. Don't
burn the session solving; extract the API contract from the front-end bundle instead:

1. Grep the bundle for the site key (`0x4AAAA...`) and the token field name
   (`turnstileToken`, `cf-turnstile-response`), then reconstruct the call ORDER. Worked example
   (Byte Federal KYC, api-register.bytefederal.com):
   - `POST /phone/otp-challenge` body `{turnstileToken, visitId, journeyId}` → `{challengeToken}`
   - `POST /phone/request-verification` body `{phoneNumber, ...}` (uses the challengeToken)
2. Probe directly WITHOUT a token and with a DUMMY token — the differential proves whether
   validation is server-side:
   - no token → 403 `otp_challenge_required` / dummy → 403 = **enforced** (verified control)
   - dummy accepted = **the finding** (bot-check bypass on an OTP/PII endpoint)
   - empty-string token → 400 validation error tells you the field is schema-checked first
3. Record the wall as an honest coverage limit. The authed surface behind it (IDOR/logic classes)
   is what one test account / SMS number unlocks — ask the operator for exactly that.

Full engagement context: `security/bug-bounty/references/bytefederal-2026-10-engagement.md`.
