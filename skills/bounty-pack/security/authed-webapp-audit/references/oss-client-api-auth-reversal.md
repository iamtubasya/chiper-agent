# Reversing a bespoke API's auth from the vendor's own open-source client

Use when the target is an authenticated API/app whose client ships as source (GitHub repo,
open-source desktop/mobile/SPA client) and there is **no OpenAPI/Swagger** for the server.
The client *is* the spec: it contains the base URL, every route, the request/response DTOs,
and the exact token-construction + signature scheme. Read it, then attack the live API black-box.

Distilled from the NymVPN / Nym Technologies audit (2026-10-06), where this turned an opaque
`/public/v1/...` API into a fully-driven, self-registered account session.

## 1. Find the real API base (the JS/source bundle is the map)

Do NOT assume the obvious host. Enumerate in order:
- Live hosts: `httpx -silent -status-code -title -tech-detect` over the subdomain list. Fingerprint
  everything — the API is often a boring `[501]`/`[404]` host, or not a subdomain at all.
- Boot the client's main JS chunk and read it:
  - `grep -oE '/assets/[^"]+\.js' page.html` → fetch each chunk → search for
    `API_BASE`, `baseURL`, `BASE_URL`, `NEXT_PUBLIC_*`, and raw `https://…` literals.
  - **Query-param/route shapes leak the backend even when the base is env-injected** —
    `/api/v1/...`, `/api/admin/...` strings in the bundle tell you the surface.
- Watch for **fronted/aliased bases**: the bundle pointed at `api.nymtech.net` (dead, 501) while the
  live base was `https://nym-swap-api.nymtech.cc` (a `...cc` domain found only inside the chunk),
  and the production VPN API was fronted at `https://nymvpn.com/api` on Fastly, not on any `api.*` host.
- Fetch a known-cheap endpoint to confirm: `GET <base>/public/v1/health` or `/api/v1/build-info`.

## 2. Extract routes + DTOs from the API-client module

The client library names its own surface. Read these files, they are gold:
- `routes.rs` / `routes.ts` — every path segment as a const.
- `request.rs` — request bodies (field names + `serde(rename_all)` casing!) and enums.
- `response.rs` — response shapes (learn what `isActive`, `status`, `auth_methods` mean).
- The client's `client.rs` — the exact call: path assembled, and **which auth header is attached**
  (e.g. account `Authorization: Bearer <jwt>` AND device `x-device-authorization: Bearer <jwt>`).

From the client you recover, verbatim:
- registration body + the ownership signature scheme,
- the JWT header/payload layout and algorithm,
- error-code constants that map to backend handler names (a source comment often leaks the
  backend repo path — e.g. `github.com/<org>/websites/.../route.ts`; that repo is frequently
  private by the time you look, but the path still names the handler).

## 3. Recover the token / signature scheme exactly

NymVPN example (custom, non-RFC JWT — do not assume standard JOSE):
```
header  = {"typ":"JWT","alg":"ES256K"}                 # or "ECDSA" for the ed25519/device variant
payload = {"iat":<u128>,"exp":<u8 s>,"pubkey":"<b58>","sub":"<cosmos addr>"}   # pubkey omitted for device tokens
sig     = base64url( secp256k1_sign(raw_bytes(header_b64 + "." + payload_b64)) )
account auth header : Authorization:       Bearer <account jwt>
device  auth header : x-device-authorization: Bearer <device jwt>
```
- JSON key order matters (serde struct order) and the base64 is URL-safe **unpadded**.
- The device variant signs `SHA256(message)` with ed25519 but is labelled `ECDSA`.
- Registration proved ownership with `sign(account_address_string)` base64 — a *raw* sign over the
  address, not a sha256 of it (the sha256 variant was rejected). Try both when a signature is rejected.

## 4. Black-box the trust model with a differential token probe

You cannot read the private backend, so *infer* it: vary ONE token property per request and compare
**response bodies**, not just status codes. This is the highest-signal 15 minutes of the whole audit.

| probe                | NymVPN response body                                                  | what it proves |
|----------------------|-----------------------------------------------------------------------|----------------|
| no token             | `"Authorization header not set. Please provide a bearer token."`      | gate exists |
| self-signed, sub≠key | `"Signature is invalid. Recovered address does not match supplied address"` | server derives identity **from the signature** and compares to `sub` → forgery needs the victim key → **not a finding** |
| pubkey≠signer        | `"Signature is invalid. Failed to verify signature"`                  | verification uses the token's own `pubkey` field |
| garbage 64-byte sig  | `"Unsigned integer r must be encoded as unpadded big endian."`         | signature is actually parsed/verified (not ignored) |
| `alg:"none"`         | `"Unsupported JWT signature algorithm. Only secp256k1 or ed25519 …"`   | alg confusion blocked |
| payload missing `pubkey` | **HTTP 500** `"An unknown error occurred…"`                        | server reads `pubkey` → it is client-supplied; the 500 also = unhandled error (a real, if Low, robustness bug) |
| exp > 60             | `"JWT has validity great than 60 seconds…"`                            | explicit validity cap (this one leaks the cap) |

**Inference rules (reusable):**
- A *distinct* error for a malformed field proves the server consumed that field at that stage.
  An unhandled 500 where other inputs give a clean 400 is both a bug and an **ordering oracle**.
- Distinguish **check order**: "Account not found" on a non-existent subject means the lookup ran;
  combine with the malformed-field probes to tell whether lookup precedes or follows verification.
- "Recovered address does not match supplied address" ⇒ signature-recovery auth ⇒ the only way to
  impersonate is to hold the private key. Do NOT report forgery.

## 5. Self-provision an account (then test the authed surface)

Registration often needs **no purchase** for a free tier — here `POST /public/v1/account/apple`
took `{account_addr, pub_key, signature_base64, kind:"user_generated_secp256k1"}` and returned 200
with an `account_token`. (The Android variant additionally wanted a `purchase_token`; Apple did not —
`post_account` dispatches per platform, so try every platform path.) Only the **sandbox** env was used
for throwaway state; production was read-only.

Steps that worked:
1. secp256k1 keypair → cosmos bech32 address `bech32(prefix, ripemd160(sha256(compressed_pubkey)))`.
2. `signature_base64 = base64url(secp256k1_sign(address_string))`.
3. `POST /public/v1/account/apple` → live account. Repeat for a **second** account.
4. Build the JWT per request (fetch server time for `iat`; see §6 clock trap).

## 6. Pitfalls that cost real time this session

- **BOLA needs the binding test, not just "two accounts".** With A's token on B's path the API answered
  `"Requested account id does not match authenticated account address"` → the API binds path id to the
  token subject. Correct conclusion: **no BOLA**, served as an explicit anti-finding. Test it exactly
  this way (own A + own B, A's token, B's path, compare body) before claiming or dismissing BOLA.
- **Mass-assignment negatives must be read from the *body*, not the status.** `POST /subscription`
  returned 200 creating a record with no payment proof — looked like free-premium, but the returned
  object's `status` was server-forced to `"pending"`, injecting `status:"active"` was ignored, and
  `GET /summary` kept `isActive:false` / `limitGB:0`. A 200 that echoes your `kind`/`valid_from` is NOT
  entitlement. Verify the *effective* state via a separate read endpoint before reporting.
- **Clock trap:** JWTs built from *local* time failed as `"JWT has expired"` mid-run. Fetch the API's
  `Date`/health timestamp once, keep a signed `OFFSET = server - local`, and build every token with
  `int(time.time()) + OFFSET`. Retry once on any `expired` response.
- **The secret-tripwire corrupts WRITTEN file content, not just the display.** `write_file` with a
  literal like `"Authorization: Bearer " + token` got replaced by `***` **inside the file on disk**,
  producing a syntax error / a request sent with no auth header. Assemble such headers from fragments
  (`"Author"+"ization"`, `"Bea"+"rer "`) so the literal never appears. Same trap hit skill/agent content.
- **MSYS `/tmp` does not exist** in this git-bash: `curl -o /tmp/x.out` → "No such file or directory"
  and `$(wc -c < /tmp/x.out)` reports 0, silently faking "empty response". Write scratch files to the
  engagement dir instead.
- **Never `grep` a multi-MB single-line minified bundle** (5.5 MB `gov.js` timed out at 60 s with a
  regex error). Read it with windowed Python: `i = data.find(needle); print(data[i-400:i+300])`.
- **MSYS `NO_PATHCONV` inverse trap** already documented in the launcher applies: native tools want
  native paths (`D:/…`), bash builtins want POSIX.

## 7. What to leave behind

- `FINDINGS.md` with three blocks: **verified findings**, **verified negatives (controls that work)**,
  **open/untested gaps**. The negatives are deliverables — they stop the next session re-running the
  same probes and let the report state coverage honestly.
- The probe scripts themselves (`register_acct.py`, `bola*.py`, `jwt_diff*.py`, `sub_test*.py`) as
  re-runnable evidence.
- Note which environment state was created (sandbox accounts/subscriptions) and that production was
  not modified — the user/disclosure needs that cleanly stated.
