---
name: chiper-frontend-api-reverse
description: "Reverse-engineer a web app's internal / undocumented API from its frontend JavaScript bundles. Reconstruct request signing (AES/RSA/hash), obfuscated crypto, upload flows (presigned URLs, OSS/S3), and authorization/quota guards, then rebuild a working client. Use when an app gatekeeps a feature behind a UI (paywall, credits, login, rate limit) and you want to call the underlying endpoints directly — 'free no-login' features, 'bisa pakai API endpoint gak', JS bundle analysis, hidden endpoint discovery, request signing bypass."
origin: chiper
version: "1.0.0"
compatibility:
  - chiper
  - claude-code
  - cursor
  - windsurf
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - WebFetch
metadata:
  domain: web-attack
  mitre: "T1190-Exploit Public-Facing Application, T1592-Gather Victim Host Information, T1552.001-Credentials In Files"
  last_reviewed: "2026-11-16"
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-frontend-api-reverse/references/aifaceswap-case.md
---

# Skill: Frontend-to-API Reverse Engineering

## When to use

- App exposes a feature in the UI ("Free face swap, no login") but the official API is paywalled / VIP-only.
- User asks "bisa dipakai lewat API endpoint gak?" for a web-only tool.
- An SPA/minified bundle hides an internal API behind client-side crypto or signature headers.
- You need to call a hidden endpoint directly instead of driving the browser.

**Core principle:** the browser can always do it, so the endpoints + crypto are always recoverable. The UI is a client; you are rebuilding the client.

Distinct from `chiper-api-security` (attacks *documented* APIs with BOLA/JWT/rate-limit tests) and `chiper-web-auth-bypass` (bypasses auth flows). This skill is about **discovering and reconstructing** the protocol itself from client code.

---

## Methodology

### Phase 1 — Harvest the bundle surface
```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36"
curl -sL -A "$UA" "https://target/page" -o page.html
# 1. collect ALL script srcs (framework bundles, plugins, feature chunks)
grep -oE 'src="[^"]+\.js[^"]*"' page.html | sort -u
grep -oE 'https?://[a-z0-9.]*(target|cdn)[a-z0-9.]*/[a-zA-Z0-9._/-]+\.js' page.html | sort -u
# 2. look for doc/manage routes referenced in-page (they leak endpoint lists)
grep -oiE 'href="[^"]*(api-doc|api-manage|swagger|redoc)[^"]*"' page.html
```
Fetch every JS file. Note: feature code is often in a **separate chunk** (`.../js/custom/feature/<name>.<hash>.js`) — grab it too, not just the main bundle.

### Phase 2 — Extract endpoints
```bash
grep -oE '["'"'"'`]/?(api|v1|v2)/[a-zA-Z0-9._/{}$-]+' *.js | sort -u   # endpoint paths
grep -oE 'https?://[a-zA-Z0-9._-]+/[a-zA-Z0-9._/-]*' *.js | sort -u    # full URLs (OSS/CDN/backend)
```
Also open any `/api-doc/`, `/api-manage/`, `/docs` page — vendors often publish the *paid* API surface, which maps 1:1 to the internal one.

### Phase 3 — Reconstruct crypto / signing
1. Find the request wrapper (`verify_axios`, `request`, custom fetch). It reveals which headers are injected and when.
2. Locate crypto helpers. Grep for: `encrypt`, `sign`, `subtle`, `AES`, `RSA`, `CryptoJS`, `SHA`, `getFP`, `nonce`.
3. Read the helper bodies literally — the key material is usually a literal in the same file.
4. Capture every header the wrapper sets: `theme-version`, `x-code`, `x-sign`, `x-guide`, `fp`, `Authorization`, etc.
5. **Try the plaintext path first** (see pitfalls) — often no crypto is enforced server-side.

### Phase 4 — Rebuild a client & verify incrementally
Reproduce step by step against the live server, stopping at the first failure:
boot page (scrape any per-session key) → presign/upload → main action → poll.
Match the exact **body field names** the JS sends (e.g. `start`/`end` not `duration`).

### Phase 5 — Identify the guard
When the action is rejected, decode the response code. Vendors reuse one code for one guard:
`401` token expired · `6xx` permission check failed (signature/header wrong) · `637` quota exhausted.
Signature-wrong and quota-exhausted look identical to a beginner — read the message string.

---

## Key techniques

| Technique | How |
|---|---|
| Find hidden endpoints | feature-chunk JS + `/api-doc/` page + network tab on the real UI |
| Recover crypto key | grep literals near `SHA256`/`AES`/`RSA`/`encrypt` in the same chunk |
| Reproduce a signature | port the helper verbatim; JSEncrypt = RSA **PKCS#1 v1.5**, AES via CryptoJS = **CBC + Pkcs7** |
| Per-session key | scrape `data-kt-theme-version`-style attributes from the HTML and re-fetch each run |
| Upload flow | `POST /upload_file` → presigned S3/OSS PUT → `cdnUrl = url.split('?')[0].replace(OSS_DOMAIN,'')` |
| Quota guard probe | vary cookie / UA / device fp / IP headers one at a time; see what flips the code |

---

## Pitfalls (learned the hard way)

- **Don't assume encryption is required.** Try `request_type:1` plaintext body first — many SPA vendors ship crypto for one flow and accept plaintext for another. A guest account often has NO server-side crypto check.
- **AAD/IV layout:** if the helper does `iv + ciphertext`, the IV is **prepended**, not passed separately. Getting this wrong = silent decrypt failure.
- **RSA padding:** JSEncrypt defaults to **PKCS#1 v1.5** (`PKCS1_v1_5`), not OAEP. Wrong padding = signature rejected.
- **AES mode:** CryptoJS `AES.encrypt` defaults to **CBC + Pkcs7**, key+iv both from the (Utf8) string.
- **Don't trust header-spoofing for quotas.** Cloudflare strips `CF-Connecting-IP` (→ 403) and often ignores `X-Forwarded-For`. Try a **fresh egress IP** (residential proxy) instead.
- **Presigned upload result is a relative path**, not a URL — reconstruct it as `OSS_DOMAIN + path`. The raw upload path is not publicly writable/readable at the app origin.
- **Match exact field names.** Reading the JS body dict beats guessing (`start`/`end`/`type` vs `duration`).
- **Vendor codes differ per guard** — read the message string, don't pattern-match on HTTP 200.
- **SOCKS proxies** need `requests[socks]` / `pysocks` in the *same* interpreter you run from (`python3 -m pip install pysocks`); check which venv shebang your script uses.

---

## Verification checklist
- [ ] Endpoint reached and returns a **positive** app-level `code` (not just HTTP 200).
- [ ] Task/action accepted (got an id / resource reference).
- [ ] Terminal state reached (poll returns done + result URL), OR the exact guard code + message documented.
- [ ] Claim marked `[CONFIRMED]` only if the end artifact was produced; else `[LIKELY]` / `[NEEDS-TEST]`.

## Delivery surface is a separate decision from the reverse-engineering

Rebuilding the client gets you *callability*; **how the user drives it** is a second choice, and it
changes the whole UX. Don't default to a web UI. Match the surface to the constraint:

- **Web UI + Cloudflare/edge tunnel** — convenient on desktop, but a large upload (≈10MB) can hit the
  edge's ~100s origin timeout and die with `524` *at the edge, not the app*. Frameworks also add
  weight the user may reject.
- **Telegram / chat bot** — frequently the better surface for a **batch, long-running job**, and the
  one this user preferred over a web UI. No tunnel-timeout on the upload, progress + the finished
  artifact pushed straight into the chat, usable from a phone with zero DNS/browser setup.
- **CLI wrapper** — best for local/scripted runs; no inbound surface at all.

Whichever you pick, the compute pipeline (upload → per-item generate → poll → collect → zip) is
unchanged and shared. Build the pipeline surface-agnostic first, then bolt the delivery layer on.
When the user says "jangan di web UI" / "mungkin lebih work via bot", treat it as a **delivery-surface
preference**, not a rewrite — only the thin transport layer changes.

Bot recipe (sync-job → async-progress bridge, separate-token rule to avoid polling 409, systemd
unit): `chiper-aifaceswap-api` → `references/telegram-bot-delivery.md`.

**Chat-bot delivery gotchas (cost real debugging time — see the recipe for the full fixes):**
- A background worker thread + async bot needs the loop captured at handler time and
  `asyncio.run_coroutine_threadsafe(...).result()` — *resolve the future*, don't fire-and-forget.
  The common killer: `push()` that returns nothing → `message_id` is `None` → every progress edit
  400s → the user sees a frozen status and thinks the bot died.
- `send_document` must be resolved + retried, with a path fallback; a swallowed error means the job
  finishes but the artifact never arrives and the user waits forever.
- Telegram 400s on editing a message to identical text — cache last text and skip no-op edits.
- A dropped import in a refactor (e.g. `InlineKeyboardButton`) only fails at the *first button tap*;
  register `app.add_error_handler(...)` so handler exceptions surface in chat, not just the log.
- UX: for a multi-step input flow give the user a **button-driven wizard** (start button, "step 1/2"
  counter, confirm gate) with inline keyboards — bare "send X then Y" text is confusing. Users ask
  for this explicitly ("harus ada opsi biar mudah … biar ada instruksi").

## Reference cases
- `references/aifaceswap-case.md` — full aifaceswap.io guest video-faceswap reconstruction: crypto scheme, OSS presign flow, quota-guard findings.
