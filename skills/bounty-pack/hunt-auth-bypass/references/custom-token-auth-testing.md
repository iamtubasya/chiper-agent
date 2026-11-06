# Testing a custom token auth model recovered from the client

For apps that ship an **open-source client** (desktop/mobile) talking to their own API with a
**home-grown token scheme** rather than standard OAuth. The client source *is* the spec: it shows
how tokens are built, what the registration flow requires, and which claims the server checks.
That turns "probe blindly" into "reproduce the scheme, then attack the trust model".

Validated on Nym/NymVPN, 2026-10-06 (2 self-registered accounts, full authed API surface).

## Step 1 — Recover the scheme from the client

Search the client repo for the HTTP client module and the token builder:

```bash
grep -rn "fn jwt\|struct JwtPayload\|struct JwtHeader\|Bearer\|Authorization" <client>/src
grep -rn "signature_base64\|pub_key\|account_addr\|register_account\|CreateAccount" <client>/src
```

Extract four things: **header algs**, **payload claim names**, **the exact byte string that is
signed**, and **the encoding** (base64url vs base64, compressed vs raw pubkey). Note any comments —
they often leak the backend repo path and endpoint list (e.g. a permalink to
`…/vpn-api/src/app/api/public/v1/account/[accountId]/…` in an error-mapping file).

## Step 2 — Self-provision by replaying registration

Registration is usually open and needs only a self-signed proof:

```python
# secp256k1: sign the address string with the derived key (NOT sha256(address))
sig   = b64url(sk.sign_deterministic(address.encode(), hashfunc=hashlib.sha256,
                                    sigencode=ecdsa.util.sigencode_string))
body  = {"account_addr": address, "pub_key": b58(compressed_pub), "signature_base64": sig,
         "kind": "user_generated_secp256k1"}
```

Derive the address like Cosmos: `bech32("n", ripemd160(sha256(compressed_pubkey)))`.
If registration rejects, try the alternate message (raw vs hashed) — the error distinguishes them
(`"Signature does not match account"`). Getting an account is what unlocks the authed surface.

## Step 3 — Probe the trust model with a differential matrix

Do **not** judge by status code alone — the **response body** reveals which check fired and in what
order. Fire a fixed matrix and read the messages:

| token variant | what it proves when accepted/rejected |
|---|---|
| no token | baseline wording (`"Authorization header not set"`) |
| valid self-signed, `sub` matching the key | does the sig check pass at all |
| valid sig but `sub` from a *different* key | `"Recovered address does not match supplied address"` ⇒ server **recovers** the signer and compares to `sub` |
| signature from key B, `pubkey` field = key A | `"Failed to verify signature"` ⇒ server verifies **against the token's own `pubkey`** |
| `alg: none` / wrong alg | reveals whether alg is pinned |
| **omit a required claim** (e.g. `pubkey`) | often a **500** ⇒ the field is read during token processing, i.e. *before* account lookup. Ordering evidence. |
| `exp` beyond the cap | `"validity greater than 60 seconds"` ⇒ caps are enforced |

**Recovery-based verification (`recovered_address == sub`) is secure** — an attacker would need a key
whose address equals the victim's. Do not report that as a vuln just because `pubkey` is
caller-supplied. Conversely, a server that verifies against a caller-supplied `pubkey` *without*
binding it to `sub` **is** forgeable → account takeover.

Latency/order trap: a *missing-claim 500* only makes sense if the field is read before the lookup —
cross-check the message ordering, don't infer from the status code.

## Step 4 — Probe authorization binding (the real bug class)

The client builds paths like `/account/{account.id()}/device/{device.id()}/…` while authenticating
with `Bearer account.jwt()`. So ask: **does the server compare the path id to the token subject?**

```
GET /account/<B>/summary   with A's valid token
  -> 403 "Requested account id does not match authenticated account address"   = bound (good)
  -> 200 with B's data                                                          = BOLA / account takeover
```

Use two accounts **you own** (A and B) so the proof is self-contained and touches no third party.
Prefer this over guessing ids: it cleanly separates "auth bound" from "auth checked only at the gate".

## Step 5 — Probe entitlement / mass-assignment

If the app gates paid features, look for the state-changing endpoints and ask whether the client can
mint the *paid* state:

- `POST /account/{me}/subscription {kind, valid_from_utc}` → if it returns 200 without any payment
  proof, check whether `status`/`isActive`/`tier` are **mass-assignable**. A server that forces
  `status:"pending"` and keeps `summary.subscription.isActive:false` is correctly built.
- Then check the **feature gate itself** (e.g. credential/entitlement issuance). Send a
  structurally-valid-but-garbage body: the error tells you which check runs first.
  `"You do not have an active subscription"` ⇒ entitlement is enforced **and** runs before payload
  validation ⇒ a self-minted pending subscription buys nothing. That single response closes the
  whole hypothesis — cheaper than building the client-side crypto to make a "real" request.

## Diagnostic: identical error id across inputs and hosts = canned, not cached

If every variant — valid, garbage, empty — returns the **byte-identical `codeReferenceId`/`requestId`**,
and the same on *two different hostnames* (prod + sandbox), the endpoint is returning a **static
canned response** (feature-gated / disabled / blocked), and is **not** evaluating your input. A
per-request id is generated fresh; identical ids across independent requests mean the logic never ran.

Distinguish from plain edge caching: add a cache-buster (`?cb=<epoch_ms>`) and re-test. If the id is
*still* identical **and** matches across hosts, it's canned — stop testing that path and say so.

## Client-side fail-open authentication (CWE-636) — a class worth grepping for

In VPN/proxy/privileged-daemon clients, the control channel is often gated by *"is the connecting
process signed by us?"*. Look for the **fail-open** shape: when the daemon cannot verify its **own**
signature, it sets the auth material to `None`, and the auth layer treats `None` as **authorised**.

```rust
let auth_material = if skip_authentication_checks(..) { None } else { Some(auth_material) };
// ...
let authorized = if let Some(m) = auth_material { is_authenticated(..) } else {
    tracing::debug!("Skipping authentication checks");
    true                      // <-- fails OPEN
};
```

Compounding patterns to check alongside it:
- The IPC object's DACL/ACL: `WellKnownSid::World` (= `Everyone`, S-1-1-0) with `GENERIC_READ|WRITE`
  means the ACL is **not** a second line of defence (CWE-732).
- An operator flag / CLI switch that disables verification wholesale (`--disable-client-verification`).
- The same `skip_authentication_checks()` fail-open branch on other platforms (macOS).

Severity honesty: if shipped builds are signed, this is **Low–Medium**, not Critical — the defect is
the fail-open *design* plus the over-broad ACL removing defence-in-depth. Say the precondition out
loud in the report; overclaiming costs credibility with the triager.

Contrast a **correct** design: Linux `SO_PEERCRED` → uid → group membership, else polkit prompt, and
permissions `0600`/`0700` on stored secrets.
