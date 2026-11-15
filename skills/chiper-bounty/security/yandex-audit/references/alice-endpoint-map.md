# Alice (Yandex) — live endpoint map (fingerprint 2026-11-02, headed browser)

## Recon methodology
Headed Playwright + persistent Chrome profile (`browser-profiles/yandex`) to pass SmartCaptcha,
network request/response + WebSocket frame capture. All requests observed in a real browser session.

## LLM WebSocket (the AI generation channel)
- **`wss://uniproxy.alice.yandex.ru/uni.ws`**
- Protocol: JSON frames, Vins V2 (Yandex Intelligent Assistant) protocol.
- Client → server events (namespace `Vins`): `TextInput` (the actual user prompt).
- Server → client: `streaming {source:"InitialRequest", routing:{dialog_id}}` wrapping
  `directive.payload.json_response.base_response.cards[].text_card.text` — the LLM-generated reply
  streams back as progressive `response_partial_num` chunks (`is_last:true` marks the end).
- System namespace frames: `SynchronizeState`, `ClientSubscriptionState`/`ServerSubscriptionState`
  (full-content subscription per dialog_id), `Ping`/`Pong`.

### Identity payload (client-supplied, in SynchronizeState)
```json
{"event":{"header":{"namespace":"System","name":"SynchronizeState","messageId":"..."},
  "payload":{
    "auth_token":"<uuid>",              // per-session, from the login cookie flow
    "uuid":"0000000000000<yandexuid-as-decimal>",
    "yandexuid":"<decimal>",
    "vins":{"application":{"app_id":"ru.yandex.webstandalone.desktop", ...}}
  }}}
```
Note: `auth_token`, `uuid`, `yandexuid` are all supplied by the client. NOT yet proven to cross a
boundary (no foreign-account replay test done — and per llms.txt MUST use only own accounts).

## REST RPC layer (`rpc.alice.yandex.ru`)
- `POST /dialog/list`  body `{"limit":50,"hints":{"not_entrypoint":false}}` → `{"objects":[{"dialog":{dialog_id,title,original_title,creation_ts_ms,...}}]}`. Returns conversation TITLES (the model's first message is stored as title).
- `POST /dialog/update_time_last_read`  body `{"dialog_id":"<uuid>"}`
- `POST /gproxy/get_alice_apps` → `{"apps":[]}`

## Auth model (measured)
- Cookies set on alice.yandex.ru: `yandexuid`, `yashr`, `yuidss`, `i`, `my`, `_yasc`, `cycada`,
  `alice.usage`, `gdpr_popup`, plus SSR state cookies. `_yasc` + `cycada` are Yandex anti-bot.
- `POST /dialog/list` with **no cookies** → **429 `limited`**. With a fresh authed context → also
  **429 after repeated probes** (cooldown). So the endpoint is cookie-gated AND rate-limited; the
  clean-vs-authed differential is inconclusive because both hit the rate limiter.
- SmartCaptcha sits in front of the serp/bounty surfaces and returns the same `429 limited` on
  automated hammering.

## What is NOT yet proven (do not claim)
- No prompt-injection impact demonstrated (no cross-user, no OOB callback yet).
- No IDOR: `dialog_id` values are UUIDv4; a foreign-id read was never attempted (and llms.txt
  forbids testing real/unrelated IDs — two own accounts only).
- No SSRF: the `$ref` tool-schema trick from `hunt-llm-ai` §5 was not tested against Alice (Alice
  web has no tool/function-calling schema surface exposed in the web client).
- No system-prompt leak (the WS only streams generated reply text, not the prompt).

## Retry guidance
- 429 `limited` = cooldown, back off (minutes to hours), do NOT hammer (Yandex "no artificial load").
- Next probe path: `dialog/list` after cooldown with a single authed context; then move to the WS
  `TextInput` echo of a canary to check for reflection/guardrail behaviour (own account only).
- Keep OOB domain ready (`interactsh-client`) — a real AI finding needs an OOB callback, not text.