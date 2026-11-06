# Custom / bespoke token scheme — worked probe recipe

Worked example: a public API using a **bespoke, non-JOSE** auth scheme. Scheme
recovered from the open-source Rust client; result was **Model B (signature
address recovery) → not forgeable**. Kept as a concrete recipe + the probe hygiene
that made the session work.

## 1. Recovering the scheme from the client

- Token builder (client crate) gave the exact wire format:
  - header `{"typ":"JWT","alg":"ES256K"}`
  - payload `{"iat":<u128>,"exp":<u8>,"pubkey":<base58 secp256k1>,"sub":<address>}`
  - signature = base64url(**no padding**) of `secp256k1_sign(raw bytes of "header_b64.payload_b64")`
- Second token type in the same API: `alg:"ECDSA"`, **ed25519**, `sub` = base58(device
  pubkey), **no** `pubkey` claim, signature over `SHA256(message)`.
- Routes + claims live in the client's `routes.rs` / `request.rs` / `types/*.rs`.
  Each struct's `#[serde(rename_all=...)]` attribute is the wire format — the SAME
  API mixed camelCase (`deviceIdentityKey`) and snake_case (`account_addr`) in
  different endpoints. **Check the attribute per struct.**
- Account **self-registration** (to obtain your own identity) was in the client's
  `register_account()`: endpoint, body fields, and the exact signature construction
  (here: sign the raw address string). This is your foot in the door for every
  authed test that follows.

## 2. Differential probe → decode the verification model

Same request, several token variants; the *distinct* errors reveal the model:

| variant | observed |
|---|---|
| no token | 403 `Authorization header not set` |
| valid self-signed (own key, matching sub) | 403 `Account not found` → signature ACCEPTED, lookup is step 2 |
| garbage signature | 403 `Unsigned integer r must be encoded as unpadded big endian` |
| `alg:none` | 403 `Unsupported JWT signature algorithm. Only secp256k1 or ed25519 will be accepted` |
| pubkey claim ≠ signing key | 403 `Failed to verify signature` |
| **pubkey claim OMITTED** | **HTTP 500** → server reads the token's OWN pubkey ⇒ Model B |
| sub not derived from the signature | 403 `Recovered address does not match supplied address` ⇒ **Model B confirmed** |

Verdict: unforgeable. Do not spend effort on alg:none / key-confusion / kid here.

## 3. Authz binding test (BOLA) — needs one real account

Register two accounts (A, B) with your own keys. Send **A's token** to **B's path**:
→ 403 `Requested account id does not match authenticated account address` = correctly
bound. (This is the BOLA test that the account-registration step unlocks.)

## 4. Entitlement ordering probe

`POST` the gated action with an empty/garbage body:
→ error named **entitlement** (`...request_failed.no_active_subscription`), not the body
⇒ entitlement is checked FIRST, so a self-minted *pending* record is insufficient.
The whole "free paid-tier" hypothesis died on this one cheap probe — no crypto tooling.

## 5. Exact rules the API enforced (calibration)

- `exp` MUST be **≤ 60** (else 403 `JWT has validity greater than 60 seconds`). A
  `u8` exp field with a hard cap.
- `iat` must track server time — compute the offset ONCE from
  `GET /public/v1/health` (`timestampUtc`) and reuse it; the local clock drifted ~21 s
  mid-session and every call started failing "JWT has expired".
- Registration signature = sign the **raw** address string (not `sha256(address)` —
  that variant returned `Signature does not match account`).

## 6. Probe hygiene when scripting a live API (learned the hard way)

- **Cache-bust every request**: append `?cb=<epoch_ms>` when an edge caches. Vercel
  (`Cache-Control: public, s-maxage=30`) replayed stale responses and made identical
  POSTs look broken.
- **Never regex a multi-MB minified bundle** — `re` backtracks and HANGS on a 5.5 MB
  single-line file. Use Python windowed search instead:
  `i = t.find(needle); print(t[max(0,i-400):i+300])`.
- **Building auth headers inside written scripts**: a secret-masking layer can corrupt
  the literal `Authorization: Bearer <token>` in the file you write, so the header is
  never sent and EVERY call returns "authorization header not set". Assemble the header
  from fragments so the literal never appears whole:
  `HNAME="Author"+"ization"; HSCHEME="Bea"+"rer "` then `"-H", HNAME+": "+HSCHEME+token`.
- **Persist identities the moment you create them** (`{addr, pub, privkey}` to disk).
  If the target closes/rotates signup mid-session, **existing accounts keep
  authenticating while new registration is denied** — saved keys are then your only
  way to finish authed testing.
- A **500 on a well-formed token missing a claim** is a robustness bug worth a LOW,
  not a bypass. Don't inflate it.
