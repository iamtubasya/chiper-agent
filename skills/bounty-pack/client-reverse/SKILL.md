---
name: client-reverse
description: 'Client-side request-signing and anti-bot token reversal for bug bounty — when a request carries a sign/sig/hmac/token/nonce/timestamp/X-Sensor header that Burp Repeater cannot replay, recover the signer just enough to reproduce the request outside the client. Packet-first staging (capture real request → prove replay works → only reverse if replay fails) across the locate→recover→runtime→validation→replay spine. Covers tracing backward from the signature field (writer→builder→entry→source), isolating user-mutable sign inputs (timestamp/nonce/deviceId/body) vs constants (secret key), hooking fetch/XHR in DevTools, JS deobfuscation basics (webpack/wasm/JSVMP), and the bounty payoff: reach the protected API to then hunt IDOR/auth/business-logic. Use when Burp/mitmproxy replay of a signed or anti-bot-gated request fails and you suspect a client-computed field is blocking you.'
---

# CLIENT-SIDE REQUEST-SIGNING / ANTI-BOT TOKEN REVERSAL

You hit a request you cannot replay. Burp Repeater returns `401 invalid signature` or `403 bot detected` even though the browser/app does it fine. There is a `sign`, `sig`, `X-Signature`, `_token`, `nonce`, `X-Acf-Sensor-Data`, or encrypted body the client computes. This skill recovers **just enough** of that signer to reproduce the request **outside** the client.

> **Why a bug bounty hunter cares:** the signature is not the bug. The signature is the **lock on the door**. Behind it is an API the program assumed only their own client would ever reach — so that API is often under-tested for IDOR, BOLA, mass assignment, and business logic. Reversing the signer is the cost of admission; the **payout** comes from what you fuzz once you're inside. Never report "I reversed your sign algorithm" as a finding on its own — that is N/A. Report the IDOR/auth bug you reached **through** it.

---

## THE CORE PRINCIPLE: PACKET-FIRST

> Reverse engineering is a **blocker-resolution step, not the default entrypoint.** Capture the real request first. Prove whether it already replays. Only reverse the signer if replay actually fails.

Most hunters waste hours decompiling JS for a "signature" that turns out to be replayable as-is, or gated by a timestamp that's valid for 5 minutes. Run this gate **before** opening DevTools Sources:

```
1. Capture the real request    (Burp/mitmproxy proxy, or DevTools → Network → Copy as cURL)
2. Replay it UNCHANGED          (paste cURL into terminal, or Burp Repeater)
   → 200 / works?  → IT'S NOT SIGNED. Skip all reversing. Go fuzz it.
3. Replay it again 5 min later  → still 200?  → no freshness check (replay window is wide/infinite)
4. Mutate ONE non-signed field  (e.g. change an `id` in the body, keep sign as-is)
   → 200?  → the sign does NOT cover that field → tamper freely, no reversing needed
   → 401?  → the sign covers it → NOW you reverse (continue to STAGES below)
```

Steps 2–4 alone kill ~half of "I need to reverse this" assumptions. A signature that omits the payload or endpoint, or never expires, is itself the bug — see the CoinMate pattern in **Real Paid Examples**.

---

## STAGE SPINE: locate → recover → runtime → validation → replay

Pick the stage from **engineering state**, not from clue words. "I see the word `sign`" does not mean you're in `recover`. You are in `locate` until you can point at the exact line that writes the signature.

```
intake → evidence → locate → recover → runtime → validation → replay
```

| Stage | Enter when... | Goal | Exit when... |
|---|---|---|---|
| **locate** | the signing function / write boundary is unproven | find where the sign field is written and what feeds it | you can point at writer ← builder ← entry ← source |
| **recover** | boundary is real but the code is obfuscated/opaque | de-shell only the layer blocking you (webpack/wasm/JSVMP) | you have a readable or callable signer contract |
| **runtime** | code is clear but browser-exec ≠ your-exec diverge | find the first divergence (missing object/state/anti-debug) | local run reproduces browser sign output |
| **validation** | remaining work is equivalence proof | match checkpoints, not just final output | sign(input) == observed for fresh inputs |
| **replay** | sign reproduces outside the client | Burp/Python baseline request you can fuzz | a stable request you can mutate for IDOR/auth |

Carry a one-line handoff between stages. Do not promote a guess to a fact:

```text
--- Stage Handoff ---
From: locate  To: recover
Proven: sign written at app.min.js:1, line ~4021; inputs = ts, nonce, JSON body, deviceId
Open:   builder is inside webpack module 5f3 behind a string-table — need to de-shell that one module
Invalid: assumption that deviceId was constant (it rotates per session)
```

---

## STAGE 1 — LOCATE: trace backward from the signature field

You know the **output** (the `sign` value on the wire). Walk backward to the **source**. Keep each layer distinct:

```text
writer  <-  builder  <-  entry  <-  source
```

- **writer** — the line that finally puts `sign` into the body/header/query/cookie/WS frame
- **builder** — the transform: `HMAC`, `MD5`, `AES`, sort-then-concat, `JSON.stringify` ordering
- **entry** — the UI action / callback / response that kicks off the chain
- **source** — what feeds the inputs: upstream response, localStorage, cookie, `Date.now()`, `crypto.getRandomValues`, user input

### Browser: find the writer in Chrome DevTools

```text
# 1. XHR/fetch breakpoint — break the moment the signed request fires
DevTools → Sources → XHR/fetch Breakpoints → + → paste the endpoint path (e.g. /api/order)
   trigger the action → execution pauses inside the request stack
   → walk UP the Call Stack panel: the frame that mutates headers/body is your writer

# 2. Search the bundle for the field name (catches the writer fast)
DevTools → Sources → Ctrl+Shift+F (search all loaded scripts)
   search: "sign"  "X-Signature"  ".sign ="  "headers["  "signature"
   click {} (pretty-print) on the minified file so line numbers are stable

# 3. DOM/event breakpoint when a click triggers it
DevTools → Elements → right-click the button → Break on → subtree/attribute modifications
```

### Strong first observation points (where to put the breakpoint)

| Sink (where sign lands) | First place to prove |
|---|---|
| request body field | final `JSON.stringify` / submit / `fetch(body=...)` |
| request header | the `headers[...] =` or `setRequestHeader` call |
| JS-set cookie | the `document.cookie =` setter |
| WebSocket frame | the final envelope object right before `ws.send(...)` |
| anti-bot blob (`X-Sensor-Data`, `_px`) | the SDK `init()` and the getter that returns the blob |

**Do NOT** broad-deobfuscate before the boundary is real. Keyword hits are not proof — many bundles ship `sign` strings that never run.

---

## STAGE 2 — RECOVER: de-shell only what blocks you

Enter only after the boundary is proven and the **only** remaining blocker is that the code is unreadable. Reduce the **single** layer in your way — never the whole bundle.

| Shell you hit | What it means | Minimal move |
|---|---|---|
| webpack bootstrap | modules wrapped in `__webpack_require__` | break inside the target module, read the local closure — don't unpack the whole bundle |
| string-array obfuscation | `_0x4a2b[12]` lookups | in console, print the decoder array; or set a breakpoint and read decoded values live |
| worker / `postMessage` bridge | sign runs in a Web Worker | breakpoint the worker script; treat `postMessage` payload as the contract |
| wasm loader | sign math compiled to wasm | hook the JS↔wasm boundary; capture inputs/outputs rather than decompiling wasm |
| JSVMP (custom bytecode VM) | a dispatcher loop interpreting bytes | **do not** reverse the VM — go runtime: hook inputs+output and treat sign as a black box |

> **The black-box shortcut beats decompilation 90% of the time.** You almost never need to understand the HMAC math. You need the **input tuple** and a way to **call the function**. Capture `sign(input) → output` pairs at runtime; if you can call the page's own signer, you never have to reimplement it.

### Reimplement vs reuse the page's signer

```javascript
// REUSE — if the signer is a reachable function, just call it from the console.
// Works when the page exposes it or you grab a reference at a breakpoint.
window.__sign = signFn;                 // assign at a breakpoint inside the builder
window.__sign({id: 999, ts: Date.now()})// → get a valid sig for ANY payload you want

// HOOK to log every real sign(input)->output the app produces (no reimplementation):
(function(){
  const orig = CryptoSigner.prototype.sign;        // adapt to the real object/method
  CryptoSigner.prototype.sign = function(...a){
    const out = orig.apply(this, a);
    console.log('SIGN', JSON.stringify(a), '=>', out);  // copy pairs for offline replay
    return out;
  };
})();
```

---

## STAGE 3 — ISOLATE THE INPUTS (the part that decides if replay is even possible)

For every input to the signer, classify it. This is the **whole game** — it tells you what you can mutate and whether you even need the secret.

| Input | Type | Attacker-mutable? | Implication |
|---|---|---|---|
| `timestamp` / `ts` | per-request | yes (you set it) | fine — regenerate per replay; check the validity window |
| `nonce` / `requestId` | per-request random | yes | fine — generate fresh; check if server enforces uniqueness (replay protection) |
| `deviceId` / `uuid` | per-session | yes (one value, reusable) | grab once, pin it — usually constant for your session |
| request **body** / **path** | per-request | yes | **the prize** — if sign covers it, you mutate body + re-sign to fuzz IDOR/mass-assignment |
| **secret key** / `appSecret` | constant, baked in | **no (you extract it)** | if it's in the JS bundle / APK, extraction = full forge ability for any request |

```text
DECISION:
  secret is in the client (hardcoded in JS or APK strings)
      → you can re-sign ANY request offline → full replay, fuzz everything
  secret is server-side only, but you can call the page's signer function
      → you can sign any payload while the page is open → replay via headless browser bridge
  secret is server-side AND signer is uncallable (heavy anti-debug)
      → you may only replay UNCHANGED requests
      → then test: does the sign omit the path/body? (CoinMate pattern) → forge anyway
      → does it never expire? → replay-window bug, report that
```

Hunt the bundle for a baked secret before doing anything clever:

```bash
# Pull the JS and grep for the secret feeding the signer
wget -q -r -l1 -A '*.js' -P /tmp/js/ "https://target.com" 2>/dev/null
grep -rnoE "appSecret|secretKey|signKey|HMAC|hmac|['\"][A-Za-z0-9+/]{24,}={0,2}['\"]" /tmp/js/ | head
# Cross-reference with /secrets-hunt --js-bundle for entropy-scored hits
```

---

## STAGE 4 — RUNTIME & VALIDATION: prove your sign == the app's sign

If you reimplemented the signer in Python, prove equivalence on a **fresh** input before trusting it. Compare checkpoints, not just the final byte:

```python
import hmac, hashlib, json, time

def sign(body: dict, ts: str, nonce: str, secret: bytes) -> str:
    # Reproduce the EXACT canonicalization the JS does — order, separators, encoding.
    # Get these by reading the builder, NOT by guessing.
    payload = json.dumps(body, separators=(',', ':'), sort_keys=False)  # JS JSON.stringify keeps INSERTION order, not sorted — set sort_keys=True ONLY if the builder explicitly sorts keys
    msg = f"{ts}{nonce}{payload}".encode()                            # match JS concat order!
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()

# VALIDATE: feed an input you captured from the browser, compare to the observed sig.
# checkpoints that must each match: canonical body string → message tuple → final digest
assert sign(captured_body, captured_ts, captured_nonce, SECRET) == observed_sig
```

The two killers are almost always **(a)** JSON key ordering / separator whitespace, and **(b)** concatenation order of the input fields. If your digest is wrong, diff the **pre-hash message string** against the one the app builds (log it at a breakpoint), not the output hash.

---

## STAGE 5 — REPLAY: build the request you'll actually fuzz

You are ready only when you can answer all five:

```
[ ] where is the signed field written?
[ ] which inputs are constants (secret, deviceId) vs per-request (ts, nonce, body)?
[ ] which inputs come from upstream responses / cookies / storage / page lifecycle?
[ ] does request ORDER or session STATE matter (does a prior call seed the nonce)?
[ ] which fields can I mutate and still produce a valid sign?
```

Then drive it from Python so you can fuzz at scale:

```python
import requests, time, uuid

SECRET = b"extracted_from_bundle"          # or call the page's signer via a headless bridge
DEVICE = "pinned-session-device-id"

def signed_request(body):
    ts = str(int(time.time()*1000))
    nonce = uuid.uuid4().hex
    sig = sign(body, ts, nonce, SECRET)    # your validated signer from Stage 4
    return requests.post("https://target.com/api/order",
        json=body,
        headers={"X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": sig,
                 "X-Device-Id": DEVICE})

# NOW the bug hunt begins — mutate the body to reach the protected logic:
for victim_id in range(1000, 1100):        # IDOR sweep behind the signature
    r = signed_request({"orderId": victim_id})
    if r.status_code == 200 and "not authorized" not in r.text:
        print(f"IDOR: read order {victim_id}", r.json())
```

> Bridge option when the secret is server-side: keep a headless browser open, expose the page's own `sign()` via a tiny local HTTP shim, and have your Python fuzzer call out to it per request. You never reimplement crypto — the app signs for you.

---

## VARIANT — CLIENT-SIDE BUSINESS LOGIC (calculators, price/quote/tax engines)

Same discipline, different target: the client computes a **number** the user acts on (tax, price,
quote, penalty, interest). You don't need to unlock anything — you need to prove the number is wrong
**and** name the exact line, because "your calculator is wrong" without a cause gets triaged as
"works as intended".

**Black-box first, then read the code — never fit a model and call it the cause.**

```
1. Sweep the input over a range, capture the rendered result each time (Playwright + native setter
   for React inputs). Derive the error surface: where it starts, its slope, where it plateaus.
2. Enumerate the chunks the page ACTUALLY loads — both response listeners AND
   `performance.getEntriesByType('resource')`. Do not assume the chunk from the HTML/curl is the one
   that runs.
3. Fetch that chunk **inside the page context** (`await fetch(url).then(r=>r.text())`) so CDN/bot
   serving can't hand you a different build than the browser executed.
4. Re-implement the suspect function **in-page** and assert it reproduces the DOM value at every point
   of the sweep. Only then is the root cause proven. Quote the verbatim minified source in the report.
5. State the fix as a diff. If you cannot express the fix in a line or two, you do not yet understand
   the cause.
```

**Pitfalls (paid for the hard way):**

- **Hand-tracing minified JS by eye is where you will be wrong.** Real case (Quarterwise, 2026-10):
  a band-width bug was mis-traced on paper as "correct" (an arithmetic slip on `125140-50270`), the
  wrong root cause ("the taper is wrong") was written into a PDF and an email draft, and it was only
  caught because the re-implementation in-page disagreed with the hand trace. **Execute the code; do
  not read it for the answer.**
- **A black-box fit can produce a confident wrong mechanism.** The isolated `+£629` plateau and exact
  break point looked like a taper defect; the actual cause was the *band limits* being shifted down by
  a fixed personal allowance. The fit predicted the numbers correctly and still named the wrong cause.
- **Distinguish "the rule" from "the vendor's other implementation".** The strongest evidence is
  internal inconsistency: the vendor's own app engine returning the correct figure for the same input,
  or the UI printing one marginal rate while the code charges another (here: label said 60%, code
  charged 67.5%). Independent rule sources (gov.uk etc.) come second; a fit never counts.
- **Don't call a defect by the wrong subsystem in a deliverable.** If a report/draft already shipped
  the earlier wording, regenerate the artifact and **replace** the draft — a superseded explanation in
  the mailbox is worse than a delayed send.

Deliverable shape that lands: reproduce table (input → shown → correct → error), the verbatim source,
one sentence of arithmetic (`error = 5% × (taxable − 112,570)`, capped at `5% × 12,570`), the one-line
fix, and the corroboration. Vendors fix that in an afternoon.

---

## VARIANT — OPEN-SOURCE CLIENT (reconstruct the protocol, don't de-obfuscate it)

If the app's client is **open source** (Rust/Go/Swift/Kotlin SDK, a `*-api-client` crate, a published
mobile repo), delete the recover stage entirely — the signer is not hidden, it is *documented*. The
repo is a spec for the wire protocol, and the real work becomes **(a) reconstruct the auth scheme**
and **(b) adversarially probe the server's trust model**, which is where the findings are.

**Reconstruct (the repo gives you all of it):**

- the **registration/onboarding request** — exact path, body field names, and what the signature is
  computed over. Find the request-body struct and the client method that POSTs it.
- the **auth token** — header/alg, which claims it carries, and **what string is actually signed**
  (commonly `header_b64 . payload_b64`). Whether the token embeds your public key is decisive.
- **session vs device tokens** — a second token type (e.g. a device JWT authenticated via a separate
  header) often has *weaker* identity binding than the user token.
- the serde/rename rules — `#[serde(rename_all = "camelCase")]` on one struct and snake_case on its
  neighbour is a classic 400-generator. Read them, don't guess the casing.

You can then often **self-provision a real account** (generate a keypair, derive the address, sign the
challenge, POST the registration) — which buys you the authenticated surface without waiting on anyone.
If signup is gated, you may still hold **already-registered** sessions: existing credentials keep
working after the signup path closes, so keep them.

**Probe the trust model with differentials — the server's error strings are the oracle.**

| Probe | What it reveals |
|---|---|
| valid signature vs `sha256(msg)` vs garbage vs **empty** | whether the server actually evaluates your signature |
| same request across **direct host and sandbox/staging** | whether a behaviour is global or env-specific |
| `alg:none` + a weak-HMAC secret sweep | whether the verifier pins the algorithm |
| **remove a claim the token normally carries** | if the server 500s/errors differently, it consumes that claim itself |
| exceed the documented freshness window | the real `exp` cap (error text names it) |
| sign for identity A, request identity B | whether path/body identity is bound to the token subject |

**Pitfalls that manufacture fake findings:**

- ⛔ **An identical `codeReferenceId` (or request-id) across different inputs means the response is
  CANNED, not computed.** In this session every variant — valid sig, sha256, garbage, *and empty* —
  returned the same id on both prod and sandbox. That is a gated/disabled endpoint or an
  edge-cached/blocked response. It is **not** evidence of a signature bug. Compare ids before drawing
  any conclusion; a "signature does not match" error that fires for an empty string proves nothing.
- ⛔ **Caching masquerades as behaviour.** Edge caches serve stale 403s; a cache-buster query param
  and `X-Vercel-Cache`/`Age` headers tell you whether you are reading the origin at all.
- ⛔ **A clock skew between you and the server looks like an auth failure.** Sync `iat` from the
  server's own health/timestamp endpoint (compute the offset once, reuse it) — mixing in local time
  produces "expired" errors that look like a finding and aren't.
- ✅ **Negative results are deliverables.** Proving the trust model is sound (no forgery, no BOLA,
  no entitlement bypass) is real work worth writing down — record *which* probes and *what* the server
  said, so the next session doesn't re-derive it.

Worked example with the exact protocol-reconstruction path and differential table:
`references/open-source-client-auth-probing.md`.

---

## ANTI-BOT TOKENS (Akamai / DataDome / PerimeterX / hCaptcha-style)

Same spine, harder shell. These ship an SDK that emits an opaque sensor blob (`X-Acf-Sensor-Data`, `_px`, `datadome` cookie). Two realistic paths for a bounty hunter:

- **Reuse, don't reverse.** Grab one fresh valid token from a real browser session and replay it within its (short) validity window. Enough to prove an authenticated/protected endpoint is reachable and then demonstrate IDOR/auth there. You usually do **not** need to generate tokens at scale to prove one bug.
- **Headless bridge.** Drive a real browser (Selenium/Playwright) to mint the token, hand it to your Python fuzzer. Standard tooling, no SDK reversing.

> Full reversal of Akamai v3 sensor-data (PRNG-shuffled, file-hash + cookie-hash seeded) or PerimeterX's compiled SDK is a week-long research effort — **out of scope for a single bounty.** If the anti-bot itself is misconfigured (token never expires, token from `accountA` validates `accountB`'s requests, the protected endpoint is also reachable on a sibling host with no anti-bot), report **that** — it's a real finding without reversing anything. See the Stack→sibling-host idea in `web2-recon`.

---

## WHAT'S SUBMITTABLE vs N/A

| Finding | Verdict |
|---|---|
| "I reversed your client signing algorithm" | **N/A** — not a vuln by itself |
| Signed request replays unchanged forever (no timestamp/nonce freshness) | **Low/Medium** — replay-attack window; report it |
| Sign omits endpoint/payload → forge requests without the secret (CoinMate pattern) | **Medium/High** — request forgery |
| Secret key hardcoded in JS bundle / APK → forge any request | **Medium** alone; **High/Critical** chained to the API you unlock |
| Reached a protected API via reversed sign → **IDOR / BOLA / mass assignment** found there | **High/Critical** — the real prize; report the downstream bug |
| One user's anti-bot token validates another user's request | **Medium** — broken token binding |

> The deliverable is almost never the signing weakness. It is the **access-control or business-logic bug on the endpoint the signature was guarding.** Reach it, then run the IDOR / Broken Auth / Mass Assignment / Business Logic playbooks from `web2-vuln-classes`.

---

## TOOL MAP (standard tools — no special MCP needed)

| Need | Tool |
|---|---|
| capture the real request | Burp Suite proxy, or mitmproxy, or DevTools Network → Copy as cURL |
| break on the signed request | Chrome DevTools → Sources → XHR/fetch Breakpoints |
| read minified code | DevTools `{}` pretty-print + `Ctrl+Shift+F` global search |
| hook fetch/XHR / log sign() | DevTools console snippet (`Object.defineProperty` / method override) |
| grep bundle for the secret | `wget -r -A '*.js'` + `grep`, or `/secrets-hunt --js-bundle` |
| find hidden endpoints in JS | LinkFinder / jsluice (see `web2-recon`) |
| replay + fuzz at scale | Python `requests` (Stage 5 template) |
| mint anti-bot tokens | Selenium / Playwright headless bridge |
| mobile app variant (signer in APK) | `apktool` + `jadx` (static), `objection` / `frida` CLI (runtime hook) — same locate→recover→runtime→replay spine, packet-first |

> **Mobile note:** for an authorized Android app, the packet-first rule still wins — drive the app, watch Burp/mitmproxy, and only `jadx`/`frida` the APK when the packet is encrypted or unreplayable. Decompiling first is the rookie move.

---

## REAL PAID EXAMPLES

- **CoinMate API (HackerOne, disclosed)** — HMAC signature verification omitted the endpoint and payload, so requests could be forged that appeared legitimate without the correct secret (request forgery via incomplete signature coverage). This is the canonical "the sign doesn't actually cover what you'd mutate" win — find it with Stage 0 step 4.
- **Replay window on HMAC-SHA256 headers (API pentest pattern, disclosed write-ups)** — custom auth headers signed with HMAC but lacking timestamp/nonce freshness; captured valid requests replay hours/days later. Prove it with Stage 0 steps 2–3, no reversing required.
- **PerimeterX iOS SDK reversal (public research)** — compiled-to-ARM bot SDK reversed to a working token generator in ~1 week, disproving "compiled = unreverseable." Cited here as the realistic effort ceiling: pattern seen across anti-bot bypass research — for a single bounty, prefer token-reuse or a headless bridge over full SDK reversal.
- **Hardcoded HMAC secret in Android APK (mobile API pattern, disclosed write-ups)** — secret extracted from the APK lets an attacker sign arbitrary API requests, fully bypassing request validation. Find it with the Stage 3 bundle/APK secret grep.

> Cross-reference: once you're through the signature, run **IDOR**, **Broken Auth / Access Control**, **Mass Assignment**, and **Business Logic** from `web2-vuln-classes`; use `web2-recon` for hidden-endpoint and sibling-host discovery; validate with the 7-Question Gate before reporting.

See `references/browser-js-signing.md` for the full browser-JS staging detail, the boundary model, and handoff-card discipline, and `references/open-source-client-auth-probing.md` for the open-source-client variant (reconstruct the scheme from the repo, self-provision an account, the trust-model differential table, and the identical-reference-id trap that fakes a finding). ALTCHA proof-of-work CAPTCHAs (the `altcha-widget` PoW used on registration/contact/password-reset forms) are fully reversed - challenge endpoint, PBKDF2 password format, version-dependent payload shape, Python solver - in `references/altcha-pow-captcha-reversal.md`.

For the envelope shape that dominates modern web3-adjacent APIs — `Authorization: Web3Signed <base64url(json)>.<0x sig>`, EIP-191 over the payload, `bodyHash`/`aud`/`method`/`uri` binding, and the EIP-712 typed-data registrations they sit next to — see `references/web3signed-eip191-envelope.md`. It carries the two canonicalization traps that cost cycles (bare-hex `bodyHash`, sorted-key compact JSON) and the `expected vs actual` hash oracle the server hands you.
