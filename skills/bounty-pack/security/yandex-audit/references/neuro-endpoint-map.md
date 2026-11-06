# Neuro (Yandex search AI) — endpoint map (fingerprint 2026-11-02)

## Generative answer endpoint (the Neuro panel)
- **`POST https://yandex.ru/search/generative_answer?reqid=<reqid>&from=teaser_bsa`**
- Content-Type: `text/plain` (odd), Referer = the SERP page.
- Request body (JSON):
```json
{
  "request_context": {
    "user_id": "<decimal yandexuid>",
    "text": "<the search query>",
    "lr": 213,
    "parent_request_id": "<yandexuid>_<ts_ms>"
  },
  "coded_request_context": "<opaque obfuscated blob>"
}
```
- Response (200 application/json):
```json
{"is_answer_rejected":false,"data":"","is_complete_result":false,
 "user_error_info":"","signature_tag":"<decimal>","use_manual_generation_confirm":true}
```
- `coded_request_context` is an **obfuscated/encoded blob** (NOT plain base64): a leading `"2M"` prefix
  then segments joined by `.`. Each segment appears XOR/entropy-encoded — decoding as base64 yields
  binary garbage. It is Yandex's client-side request signing/context-wrapping; forging it requires
  deobfuscating the nova3 bundle (`yastatic.net/s3/home-static/_/nova3/*.js`).
- Note the captured response had `data:""` — the `from=teaser_bsa` flow only registers a teaser and
  does NOT return the actual generative text; the real answer comes from a follow-up in the SERP
  Neuro panel (different param/flow) that was not yet captured.

## SERP bundle (nova3)
- Static bundles live at `https://yastatic.net/s3/home-static/_/nova3/<sha256>.js` (content-hashed,
  rotate on deploy). `yandex.ru/search/yandcache.js` is the cache layer.
- The `generative_answer` caller + the `coded_request_context` encoder live in one of these bundles.

## Other search-side endpoints observed
- `POST /ick/r` — interaction/click telemetry (also carries an obfuscated `coded` value).
- `POST /clck/safeclick/data=...` — safe-click redirect telemetry.
- `GET /search/generative_answer` requires using the browser's own cookies (`yandexuid`, `yashr`, etc.).

## Honest status (do not claim)
- No AI-impact finding demonstrated: `data` was empty, no OOB callback, no cross-user read, no
  system-prompt/technical-secret leak.
- `coded_request_context` is opaque; forging it = request tampering + likely requires bundle
  deobfuscation, which is heavy and sits near the "reverse engineering" exclusion line.
- Next concrete probes (all own-account, no hammering):
  1. Trigger the FULL SERP Neuro panel (not teaser) and capture the completion response to see the
     real `data` shape and whether a `text` field flows back unescaped (reflection guardrail test).
  2. Grep the nova3 bundle for `generative_answer` to locate the encoder + the endpoint's auth/ACL.
  3. Diff `request_context` across two own accounts for an IDOR-shaped user_id trust (only 2 own accts).