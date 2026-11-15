# Privy SIWS Authentication Bypass — Full API Access Without a Real Wallet

**Session: pvpbattle.xyz 2026-09-07.** Privy (auth.privy.io) is a wallet-auth-as-a-service used by many web3 dApps. Its SIWS (Sign-In With Solana) flow can be completed ENTIRELY from Python with a locally-generated keypair — no real wallet, no funds, no browser needed. Result: full authenticated API access (JWT) for any Privy-protected app in ~10 seconds.

**Why this matters:** Most web3 bounties have an authentication wall ("need an account"). Privy apps have NONE — you ARE the account. Every authenticated endpoint becomes testable immediately (wallet, matches, profile, trading, withdrawals).

---

## The Flow (3 requests, all to auth.privy.io)

```
1. POST /api/v1/siws/init          → returns fresh nonce
2. (local) sign SIWS message with Ed25519 keypair
3. POST /api/v1/siws/authenticate  → returns {token, identity_token, user}
   → JWT is then used as `Authorization: Bearer <token>` on the app's API
```

## Working Python Recipe (proven on pvpbattle.xyz)

```python
import json, base64, os, uuid, urllib.request, urllib.error
from datetime import datetime, timezone
from nacl.signing import SigningKey  # pip install pynacl

PRIVY_APP_ID = "cmt9yym5l00200ckz4unjduhl"  # from JS bundle: grep -oP 'privy[^"]*app[-_]?id[^"]*' *.js
APP_ORIGIN = "https://www.pvpbattle.xyz"     # target's frontend origin

# 1. Generate keypair locally (real Ed25519 — cryptographically valid)
sk = SigningKey.generate()
pk = sk.verify_key
pubkey_b58 = b58encode(bytes(pk))            # Solana addresses are base58 of pubkey

# 2. Get nonce
req = urllib.request.Request(
    "https://auth.privy.io/api/v1/siws/init",
    data=json.dumps({"address": pubkey_b58, "create_account": True}).encode(),
    headers={
        "privy-app-id": PRIVY_APP_ID,
        "privy-ca-id": str(uuid.uuid4()),     # any UUID works
        "Origin": APP_ORIGIN,                  # REQUIRED — validated server-side
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
    }, method="POST")
nonce = json.loads(urllib.request.urlopen(req, timeout=15).read())["nonce"]

# 3. Build SIWS message — EXACT format matters
issued_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
host = "www.pvpbattle.xyz"                   # window.location.host in client
message = (f"{host} wants you to sign in with your Solana account:\n"
           f"{pubkey_b58}\n\n"
           f"You are proving you own {pubkey_b58}.\n\n"
           f"URI: {APP_ORIGIN}\nVersion: 1\nChain ID: mainnet\n"
           f"Nonce: {nonce}\nIssued At: {issued_at}\n"
           f"Resources:\n- https://privy.io")
signature = sk.sign(message.encode()).signature

# 4. Authenticate
req = urllib.request.Request(
    "https://auth.privy.io/api/v1/siws/authenticate",
    data=json.dumps({
        "address": pubkey_b58,
        "signature": base64.b64encode(signature).decode(),  # base64, NOT hex
        "message": message,
        "nonce": nonce,
        "idempotencyId": str(uuid.uuid4()),   # REQUIRED — "Invalid idempotencyId" without it
        "mode": "wallet",
    }).encode(),
    headers={  # same headers as init }, method="POST")
resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
token = resp["token"]  # → Bearer token for the app's API
```

## Common Failure Modes ("Invalid SIWS message and/or nonce")

| Cause | Fix |
|---|---|
| Wrong message format | Grep the client JS for the exact template: `grep -oP '.{0,100}wants you to sign.{0,300}' chunk_*.js` — format varies per app (statement text, Chain ID, Resources list) |
| Nonce expired | Nonces are short-lived; get fresh one immediately before signing |
| Domain mismatch | `host` in message must equal what the real client sends (`window.location.host`) |
| hex instead of base64 signature | Privy expects base64-encoded Ed25519 signature |
| Missing `idempotencyId` | Required on authenticate step |
| Missing `Origin` header | Privy validates origin against app registration |
| `ed25519` lib | Use `nacl.signing.SigningKey` (PyNaCl), not the `ed25519` package |

## Finding the Privy App ID + Message Format from JS Bundle

```bash
# App ID
grep -oP '"privy[^"]*"|privy[-_]?app[-_]?id[^,;]{0,60}' *.js | head

# SIWS message template (exact per-app format)
grep -oP '.{0,100}wants you to sign.{0,300}' chunk_*.js

# API surface from minified chunks (Hono/Express route table pattern)
grep -oP '\{path:"[^"]+",method:"[A-Z]+"\}' chunk_*.js
grep -oP '`/[^`]{2,60}`' chunk_*.js
```

## Post-Auth API Testing Checklist (what to probe once authenticated)

1. `/auth/me` — user object, custodial wallet address, internal IDs
2. Wallet endpoints — balance, deposit-address, sync, withdraw (note: withdraw needs Idempotency-Key header)
3. Boundary test all numeric caps — send values 1→N+10 to find exact server max (see below)
4. Mass-assignment — add unknown fields to POST bodies (see SSRF note)
5. IDOR on `/matches/{id}`, `/profile/by-name/{h}` — compare own data vs others'

## By-Design Analysis: "UI Cap vs Server Cap" (pvpbattle leverage case)

**Initial hypothesis:** Server accepts `leverageCap: 50` but UI only offers 25 → bypass finding.
**Reality:** UI code contained `u=eZ.filter(e=>e<=i)` — UI renders whatever the server returns. Live matches already used 50x.

**Lesson:** Before claiming a client-vs-server enforcement mismatch, verify how the UI renders the value. If the UI dynamically displays the server-returned value (no hardcoded max), the server IS the authority and the behavior is by design. Grep for the render logic: `grep -oP '.{0,150}leverageCap.{0,150}' page-*.js`.

**Boundary-test method that produced the truth:** send the disputed parameter across the full range (1→60) in one script, record server-accepted vs server-capped vs server-rejected for each value. The exact server boundary (accepted ≤50, 400 at ≥51) settled it in one run.

## SSRF via Unknown POST Fields — Verify Storage, Not Acceptance

Server returned 200 when match creation included `videoUrl: "http://169.254.169.254/..."` — looked like SSRF. But `GET /matches/{id}` showed the field was **silently dropped** (not in response keys, not stored, never fetched).

**Rule:** HTTP 200 on a POST with an injected URL ≠ the server processes it. Always re-read the stored object and check the field exists. Silent field-dropping is the expected behavior for strict validators (this one passed).

## Minimal Auto-Cancel Hygiene

When creating test matches/orders on a live platform, cancel each one immediately after creation (`POST /matches/{id}/cancel`). Boundary tests creating ~15 matches in a loop MUST clean up after each iteration — don't leave junk matches visible in the public lobby.
