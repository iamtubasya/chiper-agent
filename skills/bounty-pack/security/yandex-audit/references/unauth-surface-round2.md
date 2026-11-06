# Unauth surface — re-check results (2026-11-02, round 2, unauth-only focus)

Operator directive: focus UNAUTH surface only, re-check everything. Drop the account/BOLA path.

## Neuro `generative_answer` — unauth auth-model (measured)
- Raw `urllib` (no browser, cookie-jar seeded from a fresh GET but NO signed context):
  - `POST /search/generative_answer {text, from:teaser_bsa}` → **400 body `go away`** (2/2, different yandexuid each time).
  - `go away` = Yandex anti-bot/WAF rejection, not "no such endpoint". Endpoint exists; it refuses
    requests lacking the real cookie session + signed `coded_request_context`.
- Contrast (from round 1, headed browser with real anonymous cookies): the SAME endpoint fired and
  returned `200 {"is_answer_rejected":false,"data":"","is_complete_result":false, ...}`. So:
  - The endpoint does NOT require login (anonymous browser cookies suffice),
  - but it DOES require (a) the anti-bot cookie set present in a real browser, and (b) the signed
    `coded_request_context` that the SERP's JS produces.
- Conclusion (honest): **unauth raw-HTTP injection into Neuro is gated by anti-bot + request signing.**
  The query `text` is the only user-controlled payload, and it flows only from inside a real browser
  session. No unauth prompt-injection path exists without deobfuscating the signer (OOS-leaning).

## Alice WS — unauth (anonymous) state
- `SynchronizeState` (no auth_token) → accepted, returns `SessionId` (anonymous mode, by-design).
- `TextInput` hand-built frame → `EventException scope=MEGAMIND_RUN code=fail_parse_megamind_response`
  (`Code 400`) — my frame was malformed (missing required Vins payload fields), NOT a server rejection
  of injection. A correct TextInput frame (captured from the real UI) would stream a reply — but that
  is just the model answering its OWN user, i.e. self-XSS at best, and Alice anonymous mode already
  scopes dialogs to the device's yandexuid. No cross-user unauth vector evident.

## Register (unauth) — phone-gated hard
- Yandex ID registration loops survey → Gosuslugi promo → phone SMS. "Create ID" / "Other login method"
  do not offer an email-only path; phone verification is mandatory. (Operator: do NOT use others'
  numbers / disposable SMS abuse per policy — so no second account, hence no BOLA test.)

## Unauth verdict (honest, coverage-tagged)
- **Tested:** Neuro unauth raw (400 go away ×2), Neuro via anon browser (200, data empty), Alice WS
  anon handshake (SessionId, by-design), Alice WS TextInput malformed (400, my frame bug), register path
  (phone-gated).
- **NOT tested (blocked):** full SERP Neuro panel completion (not yet captured — needs authentic
  browser SERP interaction), Alice WS correct-frame TextInput injection (needs exact captured frame),
  any cross-account BOLA (no 2nd account, phone-gated).
- **No unauth finding confirmed.** Anti-bot + signing hold on the AI surfaces reachable without login.