# Open-source client — protocol reconstruction & auth trust-model probing

Worked case: `nym-vpn-client` (Rust) + the NymVPN public API, 2026-10. The client repo was public, so
nothing was obfuscated — the whole auth scheme was readable, and the engagement's value came from
reconstructing it and then **systematically trying to break the server's trust in it**.

Use this when the in-scope program ships an open-source client/SDK and the API behind it is the target.

---

## 1. Reconstruct the scheme from the repo (skip de-obfuscation entirely)

Read these, in order:

1. **The request-body structs** — they give you field names *and* the casing rules.
   ```rust
   #[derive(Serialize)]
   #[serde(rename_all = "snake_case")]      // <- snake_case here ...
   pub struct CreateAppleAccountRequestBody { account_addr, pub_key, signature_base64, kind }

   #[derive(Serialize)]
   #[serde(rename_all = "camelCase")]       // <- ... but camelCase on the sibling struct
   pub struct RegisterDeviceRequestBody { device_identity_key, signature }
   ```
   Reading `request.rs` beats guessing at the wire format. Mixed casing rules across neighbouring
   structs is the single most common 400-generator.

2. **The account/onboarding type** — it shows exactly what is signed.
   ```rust
   // "Base64-encoded signature on the account identifier of this account."
   let signature = wallet.sign_raw(&address, &id)?;   // => sign the address STRING, raw bytes
   let signature_base64 = base64_url::encode(&signature.to_bytes());
   ```
   Note the comment: *"only ever used once during account creation"*. Confirmed live — the raw-address
   signature was accepted; signing `sha256(address)` was rejected with
   `"...signature_does_not_match"`. **The signing input is the part you cannot guess — read it.**

3. **The token builder** — header/alg, claims, and the signed message.
   ```rust
   // {"typ":"JWT","alg":"ES256K"} . {"iat","exp","pubkey","sub"} . sig(header_b64 "." payload_b64)
   ```
   The payload carrying **`pubkey`** is the tell that the server may recover the signer from the
   signature rather than trust the claim.

4. **The second token type** — a device/agent JWT authenticated by its own header
   (`x-device-authorization`) is usually bound *only* to the device key, not the user account.

5. **The route constants** — `routes.rs` enumerates the real API surface (account / device / zknym /
   subscription / freepass). Free endpoint list without brute-forcing.

## 2. Self-provision an account (own-account testing, explicitly allowed by the program)

Generate the keypair, derive the address, sign the challenge, POST the registration body. That gets you
the authenticated surface immediately. Two notes:

- Signup may be **gated** (see §4) — but **already-registered sessions keep working** after the public
  signup path closes. Persist the key material when you create it; you may not be able to make another.
- Registration may need **no purchase proof** on one platform branch (`/account/apple` took just
  addr+pubkey+sig) while its sibling (`/account/android`) demands a `purchase_token`. Try both.

## 3. Probe the trust model — differential table

Every row is a cheap request. Compare **status + verbatim message**, not just pass/fail.

| Probe | Observed | Conclusion |
|---|---|---|
| valid sig, signer == `sub` | passes auth, reaches business logic | signature is actually verified |
| `sha256(address)` instead of raw address | `403 signature_does_not_match` | signing input is exact — good validation |
| token for A, path for B (`/account/{B}/...`) | `403 "Requested account id does not match authenticated account address"` | **no BOLA** — path is bound to the token subject |
| `alg:none` | rejected | alg pinned |
| 9 weak HS256 secrets | all rejected | no weak-secret HMAC path |
| claim `pubkey` removed from the payload | `500 "An unknown error occurred…"` | the server **reads that claim itself** → 500 is an oracle, not a vuln (report as robustness) |
| same request on prod and sandbox | identical | behaviour is global, not env-specific |
| `exp` raised past the window | `"JWT has validity great than 60 seconds"` | the real cap, leaked in the error text |
| POST subscription with no payment proof | `200` but server forces `status:"pending"`; `isActive:false` | client-supplied `status` is **not** mass-assignable |
| credential request on a *pending* subscription | `403 "...You do not have an active subscription."` | entitlement is enforced server-side, and it runs **before** body validation |

The last row closed the engagement's main hypothesis with a verbatim server quote — that is the ideal
way to close a lead: **the server states the control it applied.**

## 4. The trap that fakes a finding: identical reference ids

Across four different keypairs — and with a valid signature, `sha256`, garbage, *and an empty string* —
the registration endpoint returned the **same** `codeReferenceId` on both production and sandbox.
An id that never varies is not computed per-request: the response is **canned** (feature-gated,
disabled, or edge-blocked). Inferring "my signature is wrong" from it would have sent the session
chasing a phantom for hours.

**Rule: before concluding anything from an error, run a null-input control (empty/garbage) and compare
the request id.** If the control matches your "finding", you have learned about the gate, not the bug.

Related masking effects seen the same session:

- edge caching returning stale `403`s — vary a cache-buster and read `X-Vercel-Cache`/`Age`;
- local-vs-server clock skew producing `JWT has expired` for a token you just minted — sync `iat` from
  the server's own timestamp endpoint and reuse the offset.

## 5. What to write up

- The scheme itself is **N/A** ("I reconstructed your auth") — never a finding.
- Real deliverables were: the API's **verified negatives** (no forgery, no BOLA, no entitlement bypass,
  alg pinned, freshness enforced) as a coverage ledger, plus the genuinely weak items found elsewhere
  (a 500 on a malformed token = robustness; a fail-open in the *client* daemon — see
  `codebase-bounty-review/references/native-client-fail-open-casebook.md`).
- Report `security@`/channel handling and the delivery mechanics via `bug-report-delivery`.
