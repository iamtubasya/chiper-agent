# Privy SIWS Programmatic Auth + Trading-API Recon (Solana/Web2 Crypto Targets)

Session-proven workflow for testing apps that gate their API behind **Privy** (Sign-In with Solana). Privy is the dominant auth stack on Solana perps/betting/gaming targets — this pattern gets you a real Bearer token without a browser or wallet extension.

Reference implementation: `D:/data hermes/bugbounty/pvpbattle/trading_test.py` (pvpbattle.xyz).

---

## 1. Privy SIWS Auth Flow (Python, PyNaCl)

```
deps: pynacl, base58 (pip install pynacl base58)
```

### Step 1 — Generate keypair + derive Solana address
```python
import nacl.signing, base58
sk = nacl.signing.SigningKey.generate()
addr = base58.b58encode(sk.verify_key.encode()).decode()
```
No wallet needed — a fresh keypair works for any app that allows wallet login.

### Step 2 — Get nonce
```python
POST https://auth.privy.io/api/v1/siws/init
Headers: Content-Type: application/json
         Origin: https://<target-host>
         privy-app-id: <APP_ID>
Body: {"address": addr}
→ {"nonce": "...", "address": ..., "expires_at": ...}
```
**Finding the APP_ID:** grep the Next.js layout chunk for `appId:`:
`curl https://target/_next/static/chunks/app/layout-*.js | grep -oP 'appId:.{0,60}'`

### Step 3 — Construct the SIWS message
⚠️ **The message format varies per app.** Privy's default embeds it in the bundle as e.g.:
```js
b=({address:e,nonce:t})=>`${window.location.host} wants you to sign in with your Solana account:\n${e}\n\nYou are proving you own ${e}.\n\nURI: ${window.location.origin}\nVersion: 1\nChain ID: mainnet\nNonce: ${t}\nIssued At: ${(new Date).toISOString()}\nResources:\n- https://privy.io`
```
**Pitfall:** a guessed/simple message (`"{host} wants you to sign in...\n{addr}\n\nNonce: {n}"`) fails with 400 `"Invalid SIWS message and/or nonce"`. Always extract the exact template by grepping the app's Privy JS chunk for `wants you to sign` (search chunk files with Python `re`, NOT shell grep — big minified files make shell grep time out; narrow the regex or extract by offset).

### Step 4 — Sign and authenticate
```python
sig_b64 = base64.b64encode(sk.sign(msg.encode()).signature).decode()
POST https://auth.privy.io/api/v1/siws/authenticate
Body: {"message": msg, "signature": sig_b64, "chain": "solana",
       "chain_id": 1399811149, "address": addr, "nonce": nonce}
→ {"token": "<JWT>", ...}
```
Then call the target API with `Authorization: Bearer <token>`. Each fresh keypair = a fresh identity (useful for opponent-side testing, rate-limit checks, and race conditions).

---

## 2. Next.js Bundle Recon for API Structure

- Enumerate `/_next/static/chunks/*.js` from the build manifest / page HTML.
- **Find endpoint functions:** search all chunks for the API verb (e.g. `createMatch`) — it usually resolves to a small module like `U=e=>c("/matches",{method:"POST",body:e})`. That gives the exact route + that the body is passed through verbatim.
- **Find the exact POST body:** locate the React component that CALLS that function — minified JSX shows the literal body assembly, e.g. `r({wager:F?0:g,durationSec:b,leverageCap:v,mode:w,private:!F&&L})`. This is the authoritative request shape; guessing fields gives 400 `"Invalid body"`.
- **Find preset constants:** Next.js hoists presets into tiny numbered modules (e.g. `48489:(e,t,r)=>{...}` containing wager/duration/leverage option arrays). Grep for the module id colon pattern across chunks.
- **Pitfall:** shell `grep -oP` on multi-MB minified JS silently times out. Use Python: read the file, `re.finditer` with bounded `.{0,300}` windows, print slices.

## 3. Trading-Engine Edge-Case Test Matrix (perps DEX class)

Run every row against a live practice match; record HTTP code per row:
- Open long/short each listed asset at each leverage preset; add to position; flip side; open tiny margin (0.01) and max margin.
- Invalid: negative/zero margin, negative/zero leverage, leverage > cap, unknown asset, missing asset/side/margin/leverage, invalid side string, empty body, no body.
- Extra fields in body (check rejection vs silent ignore), including a spoofed `price`.
- Orders: TP/SL valid; negative/zero trigger; extreme trigger (9,999,999); duplicate TP at same price; TP for asset with no position; invalid `kind`; missing `triggerPrice`.
- Close: normal close, **close with empty body `{}`** (watch for over-broad default), double close, close never-opened asset.
- Lifecycle: surrender, surrender twice, cancel order twice, cancel fake orderId.
- Useful client formulas to verify server-side: `units = marginUsd*leverage/price`, liq at `pnl <= -0.85*margin`, `liqPrice = entry*(1 ± (1/lev - 0.005))`.

## 4. Session Pitfalls

- **Match expiry mid-test:** short-duration matches 404 (`"Match not found"`) partway through the matrix. Always create the match with the longest allowed duration, and split the matrix into batches.
- **None formatting crash:** trades/events return `pnl: None` for open/add entries — `f"{t.get('pnl'):.4f}"` throws `TypeError: unsupported format string passed to NoneType`. Use `t.get('pnl', 'N/A')` or str().
- **Idempotent 200s are still signal:** double-close returning 200 and empty-body close closing *something* are worth checking in the final state snapshot, not just the status code.
