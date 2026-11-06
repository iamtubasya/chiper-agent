# Alice — auth-model + hidden-chain probe notes (2026-11-02, adversarial review round)

## The hidden chain (primary hypothesis, still OPEN)
Two "normal" features that may interact dangerously:
1. `POST rpc.alice.yandex.ru/dialog/list` → returns `dialog_id` + `title` (title = the user's first
   message, can hold sensitive text).
2. `wss://uniproxy.alice.yandex.ru/uni.ws` → event `ClientSubscriptionState` with
   `subscriptions:[{ id:"<dialog_id>", state:{ full_content:{} } }]` — client requests FULL content
   of an arbitrary dialog_id.

Chain: if the WS subscription only checks "this SessionId is valid" (not "this dialog_id belongs to
this session"), then any dialog_id can be streamed. NOT yet proven — blocked by 429 cooldown + need
for a 2nd own account (BOLA across two own accounts = allowed by llms.txt; real/unrelated IDs are not).

## Identity fields (all client-supplied in SynchronizeState)
`auth_token` (uuid), `uuid` (device), `yandexuid` (decimal). Server answers `SynchronizeStateResponse`
with a fresh `SessionId` even when ALL are fresh-random or the auth_token is absent (test `D_no_token`).
**This is by-design (Alice anonymous mode), NOT a finding** — do not report.

## Methodology lessons (hard-won)
1. **4 parallel WS connections → all `EventException` (false negative).** I initially misread this as
   server-side identity validation, then as anti-flood. Real cause: my hand-rolled JSON frame was
   malformed (missing `event` envelope / wrong field names). After fixing the frame to the EXACT
   captured shape (`{event:{header:{namespace:'System',name:'SynchronizeState',...},payload:{...}}}`),
   a SINGLE connection gets `SynchronizeStateResponse` + `SessionId`. **ALWAYS verify one baseline
   frame is accepted before comparing identity-field mutations.**
2. `dialog/list` returns `429 {body:"limited"}` once rate-limited — this is the count/cooldown
   limiter, distinct from SmartCaptcha. Both baseline AND mutated requests hit it, so the
   clean-vs-mutated differential is unreadable while cooling down.
3. In-page `fetch()` to `rpc.alice.yandex.ru` hits CORS (blocked). Use Playwright `page.request.post`
   (sends the browser context's cookies) instead — but it still hits the same 429 cooldown.
4. Acceptable frame (from live capture) — reuse verbatim for future tests:
```json
{"event":{"header":{"namespace":"System","name":"SynchronizeState","seqNumber":1,
  "messageId":"<uuid>"},
 "payload":{"auth_token":"<uuid>","uuid":"0000000000000<yandexuuid>","yandexuid":"<decimal>",
   "vins":{"application":{"app_id":"ru.yandex.webstandalone.desktop","app_version":"unknown",
     "platform":"windows","os_version":"mozilla/5.0 ..."}}}}}
```
Server → `directive.header.name = "SynchronizeStateResponse"`,
`directive.payload.SessionId = "<hex:dashed session id>"`.

## BOLA test plan (once 2 own accounts exist + cooldown clears)
- Acct A: create a dialog via Alice (message -> dialog_id `A1`).
- Acct B (fresh session): open WS, send `SynchronizeState` (B's real identity), then `ClientSubscriptionState`
  with `subscriptions:[{id:"A1", state:{full_content:{}}}]`.
- If B receives A1 content → BOLA/IDOR (High/Critical, cross-account data disclosure).
- If B receives empty/denied → subscription is correctly ownership-scoped; record a VERIFIED NEGATIVE.