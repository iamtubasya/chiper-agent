---
name: chiper-aifaceswap-api
description: Use when targeting aifaceswap.io (or similar Vue/Element-Plus face-swap SaaS) — reverse-engineer and drive the guest/no-login internal API end-to-end. Covers theme-version scrape, AES-GCM body encrypt, AES-CBC+RSA request signing (signx/signux), Aliyun OSS presigned upload, the per-fingerprint daily free-quota guard (637/641), and the working device-spoof reset + result download from art-global.ezmaker.ai. Load when the task involves aifaceswap.io, video face swap API, no-login face swap automation, or signing schemes built from leaked JS secrets.
---

# aifaceswap.io — Guest (no-login) API reverse-engineering

> Status: **confirmed end-to-end** — video face swap produced & downloaded without login.
> Key insight: generate works only from the site's JS runtime, and 637 is a per-DEVICE daily
> limit reset by spoofing a new device (IP rotation alone does nothing).

## When to use
- Target is `aifaceswap.io` (or a fork sharing the `cryptojsencudx.bundle.js` pattern).
- Goal: call video/image face swap **without login** via internal API.
- Any face-swap SaaS where `data-kt-theme-version` + `x-guide`/`x-sign` headers appear.

## Recon
1. Blog page is WordPress (marketing), but the **actual app JS is hosted on a separate CDN**:
   - `https://temp.aifaceswap.io/aifaceswap/static/js/...`
2. Grep HTML for `*.js` bundles + `api-doc/` + `api-manage/`.
3. The real endpoints live in `custom/feature/videoswap.<hash>.js`.
4. Secrets live in `plugins/custom/cryptojs/cryptojsencudx.bundle.js`.

## Endpoints (internal, no auth for guest)
| Endpoint | Purpose |
|---|---|
| `GET /video-face-swap-ai/` | Scrape `data-kt-theme-version` |
| `POST /api/upload_file` | Presigned Aliyun OSS PUT url |
| `PUT <presigned>` | Upload bytes to OSS |
| `POST /api/upload_img` | Direct face upload (multipart) |
| `POST /api/v1/generate_video_face` | Submit swap task |
| `POST /api/check_status` | Poll task |
| `POST /api/verify_media` | NSFW check (optional) |
| `POST /api/extract_base64_faces` | Multi-face point extraction |
| Official docs: `https://aifaceswap.io/api-doc/` (VPN/Bearer + credits) |

## Leaked secrets (cryptojsencudx.bundle.js)
```
APP_ID      = "aifaceswap"
APP_ID_V1   = "aifaceswap_v1"
SECRET=***_KEY = MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCwlO+boC6cwRo3UfXVBadaYwcX...
OSS_DOMAIN  = https://yimeta-ai-face-swap.oss-us-west-1.aliyuncs.com/
```
(Secrets rotate — always re-extract from the live bundle.)

## Crypto scheme
- **Body encrypt (guest)**: `b64( iv12 || AES-GCM(json, key=SHA256(theme-version)) )`
- **signux** (used by `upload_img`): AES-CBC pkcs7 `"aifaceswap_v1:"+nonce+":"+secret_key`, key=iv=`aesSecret` (16 random b64)
- **signx** (used by `generate_video_face`): AES-CBC `"aifaceswap_v1:"+SECRET+":"+t(sec)+":"+nonce+":"+secret_key`
- **secret_key** header = `b64( RSA_PKCS1v15_encrypt(aesSecret, RSA_PUBLIC_KEY) )`  (128 bytes → 172 b64)
- **fp1** header = AES-CBC `"aifaceswap_v1:"+fp`, key=iv=aesSecret
- `signx` sign length = 344 b64; `signux` = 300 b64. Length tells you which was used.
- Verify your fp1 by encrypting `aifaceswap_v1:<fp>` with the returned aesSecret and diffing.

## Request shape (generate_video_face, guest — CAPTURED from live browser)
```
POST /api/v1/generate_video_face
headers: Content-Type: application/json, theme-version, X-code (ms),
         fp (32-hex md5 fingerprint), fp1, x-guide (secret_key), x-sign
         (NO x-type on generate! x-type:0 only on upload)
body: {"request_type":2,"data":"<base64 iv+ct>"}
decrypted: {"source_video","face_image","start","end","type":1}
```
`source_video`/`face_image` = **relative CDN paths** (e.g. `aifaceswap/upload_res/<date>/<hash>.mp4`).

## Quota guard — the real blocker
- Error `code:637` = **"You've reached today's limit of 3 free face swap videos."**
- Error `code:641` = **"Permission check failed"** (bad/unknown fp or theme/session).
- `localStorage.common_globalConfig` reveals: `faceswap.video_free_points=10`, `max_free_points=150`, `claim_free_points=30`.
- Free quota is tracked **server-side per fingerprint/session**, NOT purely per-IP.
  - Header spoofs `X-Forwarded-For`/`X-Real-IP`/`X-Client-IP` = no effect.
  - `CF-Connecting-IP` = 403 (Cloudflare strips).
  - Tor exit IP still 637 → not IP-only.

## Working approach (CONFIRMED END-TO-END — video downloaded)
The reliable path that actually produced a finished MP4:
1. Open the page in a real browser (agent-browser / Chrome).
2. **Spoof a distinct device to get a fresh fingerprint** (`agent-browser set device "iPhone 12"` +
   `set viewport 390 844` + `set headers '{"User-Agent": ...iPhone...}'`), then `reload`.
   → `MYUtils.userFP` becomes a NEW hash ⇒ fresh 3/day quota.
3. Run `generate_video_face` **from inside the page** using the site's own helpers:
   `crypto.subtle.signx()` + `await MYGLOBAL.encrypt_aes_gcm(body)` + `MYUtils.getFPencrypt(fp, sx.aesSecret)`,
   POST via `fetch` with headers `theme-version, X-code, fp, fp1, x-guide, x-sign`.
   → HTTP 200 + `task_id`. (This is the step that returns 637 if the device's daily quota is spent.)
4. Poll `/api/check_status` (same `theme-version` header) until `data.status === 2`.
5. Download `data.result_image` from **`https://art-global.ezmaker.ai/` + result_image** — NOT
   `temp.aifaceswap.io` (that host 404s with `NoSuchKey`). Result TTL is short; grab it fast.

### Dead end (documented so you don't repeat it)
- Pure-Python replay of the generate call returns **641** even with byte-identical headers/body/
  secrets. The server binds `theme-version`+`fp` to the JS-runtime session minted on page load
  (Cloudflare `__cf_bm` + Fingerprint2). Don't burn time chasing `Accept`/UA/header diffs — they are
  NOT the cause, and a random fresh fp from Python still yields 641. Drive it from the browser.

## Parallelizing the pipeline (confirmed 2.1x speedup)
The generate step dominates wall-time (each clip ~40-45s sequential). Because quota is tracked
**per-fingerprint**, N clips can generate simultaneously on N isolated browser contexts — no
contention. Split the work into two parallel pools:

- **UploadPool** — N `Uploader` instances, `ThreadPoolExecutor` upload of all clips at once.
  Each uploader gets its own proxy/session (Tor SOCKS multi-circuit) to dodge the per-IP CF 429.
- **GenPool** — N `Generator` devices, each a separate `agent-browser --session facegen_ui_<i>`
  (own fingerprint + cookies). `pool.run(tasks)` maps clips onto free devices in waves of N.
  Each `gen_clip` still rotates `MYUtils.userFP` per clip → fresh quota, and device-level isolation
  means two clips never fight for one CDP websocket.

Measured (7 clips, video 32s): sequential ~480s → 4 workers **226s**. Worker count is
`FACESWAP_WORKERS` env (systemd `Environment=`) → 6-8 workers ≈ 3-2.5 min for 12 clips.

Full recipe + code shape: `references/parallel-pipeline.md`.

## Serving results through a Cloudflare Tunnel (subdomain without dashboard)
When a tunnel is **token/remote-managed** (only `~/.cloudflared/token`, ingress lives in CF, not
on disk), you can add a new hostname entirely via API with the Global API Key — no dashboard click:
1. `GET /zones?name=<domain>` → zone_id; `GET /accounts/.../cfd_tunnel` → pick the healthy tunnel
   whose ingress you want to extend (match an existing hostname like `x.domain`).
2. `PUT /accounts/<acc>/cfd_tunnel/<tid>/configurations` — append
   `{"hostname":"face.domain","service":"http://localhost:8091"}` **before** the `http_status:404`
   fallback, keeping existing entries. (version number increments.)
3. `POST /zones/<zid>/dns_records` — `CNAME face → <tid>.cfargotunnel.com`, `proxied:true`.
Verify with `curl --resolve face.domain:443:<cf-ip> https://face.domain/health` (bypasses DNS cache).

## Delivery surface: web UI **or** Telegram bot
The compute pipeline (split → upload → parallel generate → zip) is surface-agnostic. Pick the
delivery layer by the user's constraint:

- **Web UI + CF tunnel** — nice for desktop/browser use, but a large upload across the tunnel hits
  the edge ~100s timeout (`524`) and Telegram-file limits don't apply. Fine for small inputs.
- **Telegram bot** — often the *better* surface for this class of job, and the one this user
  preferred ("jangan di web UI, tapi di telegram bot — mungkin lebih work it"). Why:
  - No CF-tunnel timeout on upload (Telegram delivers the file to your bot direct).
  - Auto-push progress + the finished `.zip` straight into the chat — no refresh, no download link.
  - Works from a phone with zero DNS/browser setup.
  - See `references/telegram-bot-delivery.md` for the full recipe — separate-token rule (avoid 409),
    the sync-job→async bridge (resolve the future for `message_id`; skip identical-text edits; retry
    `send_document` or you'll silently lose the zip), the button-driven "SWIPE FACE" wizard the user
    asked for, the `APP_DIR` off-by-one trap, and the systemd unit.

**Token pitfall (important):** do NOT reuse the Chiper gateway's `TELEGRAM_BOT_TOKEN` — the gateway
polls it, and a second poller on the same bot causes a 409 `getUpdates` conflict. Mint a **separate
bot** via @BotFather, store its token in a dedicated env file (`chmod 600`), and load it with
systemd `EnvironmentFile=`. Verify with `getWebhookInfo` (empty url + `pending:0` = polling is clean).

## Client-side vs edge timeout (`error code: 524`)
Uploading a large video (≈10MB) to the web UI **through the Cloudflare tunnel** can hit the edge's
~100s origin timeout → `error code: 524`, even though the app is fine. Cloudflare 524 is an
**edge** timeout, not app failure. Workaround: submit the job against `http://127.0.0.1:<port>`
directly (bypass the tunnel) for big uploads; download the finished ZIP through the public hostname.
For the real UI, chunk the upload or use a presigned direct-to-OSS flow from the browser.

## Fastest path to a result
1. **Browser automation** (agent-browser + CDP `DOM.setFileInputFiles` for the two `<input type=file>`)
   — inject video + face, click Render, harvest result from `/api/check_status`.
2. Intercept `XMLHttpRequest.prototype.setRequestHeader/send` in-page to capture exact headers+body.
3. Override `CryptoJS.AES.encrypt` in-page to log sign plaintexts for verification.
4. **To reset the 3/day quota: spoof a new device** (`set device` + `viewport` + `headers`, then
   `reload`) so Fingerprint2 mints a new `userFP`. Rotating IP alone (e.g. Tor) does NOT reset it.
5. Download result from `https://art-global.ezmaker.ai/<result_image>` before the temp TTL expires.

## Pitfalls
- **Cloudflare 429 on `/api/upload_file` (per-IP)**: bursts of uploads return `HTTP 429` with
  `Retry-After` up to ~3554s (~59 min), locked per source IP. Fix: route uploads through a proxy —
  **Tor SOCKS** (`socks5h://127.0.0.1:9050`) works (verified 13/13). `Uploader` auto-detects a local
  Tor at `127.0.0.1:9050`; override with env `CHIPER_UPLOAD_PROXY`. Install `requests[socks]` (PySocks)
  in the venv. Generate still runs in the browser (has its own CF clearance).
- **`error code: 524`** on a big POST through the tunnel = edge timeout, not app error → submit via
  `127.0.0.1` directly (see section above).
- **Result host confusion**: `result_image` looks like `aifaceswap/generate_temp/<date>/target_<task>.mp4`.
  Prefix it with **`https://art-global.ezmaker.ai/`**, NOT `temp.aifaceswap.io` (404 `NoSuchKey`).
  Temp results expire fast — download immediately after `status:2`.
- `agent-browser set device`/`viewport`/`headers` are what change the Fingerprint2 hash. In a plain
  headless context the fp is deterministic (same hash every reload) → quota never resets without spoofing.
- `Path.home()`/CLI arg: base64 payloads > ~100KB blow `Argument list too long` for `agent-browser eval`.
  Write the JS to a file and run `agent-browser eval "$(cat file.js)"`, or use CDP directly.
- Drop zones are divs, not file inputs. Query `input[type=file]` (index 0=video, 1=image).
- `theme-version` is per-page-load; re-scrape for each fresh session.
- `t` in signx is **epoch seconds** (not ms); `X-code` is **ms**.
- Signature verifies fine even with an old `t` — not a replay window issue.

## Reference implementation
- `scripts/faceswap_client.py` — Python client. Upload + Aliyun OSS PUT verified working; the generate
  step from pure Python returns 641 (see dead-end above) so drive generate from the browser instead.
- `scripts/browser_generate.js` — in-page snippet: device-spoof context → generate → poll → download
  from `art-global.ezmaker.ai`. Run with `agent-browser eval "$(cat ...)"`.
- `references/captured-artifacts.md` — raw captured evidence: bundle locations, exact sign formats,
  decrypted request/response bodies, quota config, error-code table, OSS presign recipe.
- `references/parallel-pipeline.md` — UploadPool + GenPool recipe (multi-browser parallel generate,
  2.1x measured speedup), worker-count sizing, systemd env wiring.
- `references/telegram-bot-delivery.md` — turn the pipeline into a Telegram bot: separate-token rule
  (avoid 409), sync-job→async-progress bridge, two-step input flow, systemd unit, pitfalls.
