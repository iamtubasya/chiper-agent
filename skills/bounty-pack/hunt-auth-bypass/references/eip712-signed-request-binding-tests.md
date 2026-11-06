# EIP-712 / EIP-191 signed-request APIs — how to mint signatures and attack the BINDING

Companion to `custom-token-auth-testing.md`. That file covers home-grown bearer/token schemes; this one covers
targets where the API is authorised by a **wallet signature** (`Authorization: Web3Signed <payload>.<sig>`,
EIP-712 typed data, EIP-3009 authorisations) and ships an open-source client. Verified 2026-10 on a data-portability
gateway: 11 independent negative tests, 2 confirmed findings, and the whole method runs from a throwaway key with no
wallet, no UI and no funded account.

## Step 1 — recover the scheme from the client (fastest route, no guessing)

The client *is* the spec. Grep it for:

- `verifyTypedData` / `_hashTypedDataV4` / `signTypedData` / `encodeTypedData` → the EIP-712 types and the domain;
- the domain constants: `name`, `version`, `chainId`, and **`verifyingContract`** — note that EACH feature has its
  own contract address (builder registry, grants, servers, escrow were four different addresses on the same chain).
  Getting the address wrong only surfaces as "signature verification failed", so lift it from the client config.
- the header scheme: base64url JSON payload + `.` + signature. The payload's field set is the binding list.
- **the client's own comments** — they state the intended invariants ("the signer committed to the nonce inside the
  EIP-3009 signature, so any relayer-substituted `account` yields a nonce the signature doesn't cover"). Every such
  sentence is a row in the binding matrix below. Writing a test per sentence is the fastest way to a strong report.

Server-side source (if published) is the other half: `_isTrustedServer(owner, signer)`-style helpers tell you
exactly which delegate relationship is supposed to hold, and `addPermission(input)` requiring
`input.grantorAddress == msg.sender` tells you the self-signed path is deliberate.

## Step 2 — mint signatures locally with `eth_account`

```python
from eth_account import Account
from eth_account.messages import encode_typed_data, encode_defunct

EIP712_DOMAIN = [{"name":"name","type":"string"},{"name":"version","type":"string"},
                 {"name":"chainId","type":"uint256"},{"name":"verifyingContract","type":"address"}]

# EIP-712: the EIP712Domain entry list MUST be passed explicitly, next to the primary type
sig = acct.sign_message(encode_typed_data(full_message={
        "domain": domain, "types": {**TYPES, "EIP712Domain": EIP712_DOMAIN},
        "primaryType": "BuilderRegistration", "message": msg})).signature.hex()

# header scheme: EIP-191 over the base64url of a SORTED, whitespace-free JSON payload
payload = json.dumps(dict(sorted(fields.items())), separators=(",", ":"))
b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
sig = acct.sign_message(encode_defunct(text=b64)).signature.hex()
hdr = f"Web3Signed {b64}.{sig}"
```

Two mechanics worth memorising:
- `Account.from_key(...)._key_obj.public_key.to_hex()` is the **64-byte x||y** form with no `04` prefix. Uncompressed
  public keys expected as 65 bytes want `"0x04" + hex[2:]`. Sending `"0x"+"04"+hex` produces a 66-byte string and the
  server answers with a shape error, not a signature error — read that error carefully, it is a formatting bug, not
  a detection.
- Always start each test with a **fresh throwaway key**; cold state is what makes "reproduced 3x" real.

## Step 3 — the body-hash trap (costs exactly one cycle, every time)

The same field has two spellings across components of one product:

| component | expected `bodyHash` |
|---|---|
| session relay / one gateway | **bare hex** sha256 of the canonical body |
| other gateway endpoints | `sha256:<hex>` (prefixed) |

The 401 is self-diagnosing — it returns `{"reason":"Body hash mismatch","expected":"4dd5…","actual":"sha256:4dd5…"}`
— so the fix is immediate, but the lesson is: **canonicalise before hashing**, because comparison is on the
canonical form, not on your bytes. Canonical = sorted keys, no whitespace, nested objects sorted too:

```python
body = json.dumps(obj, sort_keys=True, separators=(",", ":"))          # hash THIS
hashlib.sha256(body.encode()).hexdigest()                              # bare hex, no prefix
```

Unsorted-but-equivalent JSON fails the hash while looking identical in a diff. An informative
`expected`/`actual` in the error is itself worth a QA note (it hands an attacker the correct value), but it is not
the finding.

## Step 4 — the binding matrix (each row is one negative test)

| Claim inside the signed payload | Negative test | A PASS looks like |
|---|---|---|
| declared owner vs recovered signer | sign with key A, declare `ownerAddress: B` | 401 signer ≠ owner |
| body integrity | sign a benign body, send a mutated one | 401 hash/verification failure |
| delegate / server authority | owner-B's registered server key signs a grant naming owner A | 401 not-authorised-for-that-owner |
| key ↔ address binding | register A's public key under B's address | 400 "does not correspond" |
| **resource ownership claimed in the payload** | assert a URL/app/domain you do not control | 201 → **finding** |
| monotonic nonce (`grantVersion`-style) | replay v1 after v2 has been written | revert / `InvalidGrantVersion` |
| capability secret + id entropy | guess the secret, probe unknown ids | 403 / 404; 192-bit secret + UUIDv4 id = PASS |
| unauthenticated status read | `GET /session/{id}` or `/operations/{id}` with no creds | status-only = low; full record/grant payload = finding |
| freshness / expiry | omit `iat`/`exp`, or reuse an old one | rejected |
| private-address destinations (webhook-style) | point the callback at `127.0.0.1` / `169.254.169.254` | scheme/destination policy enforced = PASS |

Two rows repeatedly pay: **resource ownership claimed in the payload** (open registries verify the signer but treat
`appUrl`-style fields as free text — the strongest finding of the engagement) and **self-asserted approval**
(a "consent broker" that accepts a fabricated `grantId`, marks the session approved and delivers it downstream —
proof is that the same id returns 404 on the authoritative store).

## Step 5 — failure modes that are NOT findings (write them down as negatives)

- Returning the EIP-712 signature (or `proof.userSignature`) inside a public record — a signature is a proof, not a
  secret. Only becomes a finding if you can *replay* it (test that explicitly; usually the domain pins
  `chainId` + `verifyingContract`).
- Unauthenticated identity/registration lookups when the same data is public on-chain.
- A "relayer-key" endpoint returning a **public** key — that is what the client needs to encrypt to. Check the
  returned key really is the public half before getting excited.
- A rejected malformed signature (`v=85`-style recovery byte errors) — that is your formatting, not their defence.

## Step 6 — report shape that survives triage

Lead with the boundary, not the impact adjective:

> "the gateway verifies the signature, the public-key↔address binding and the owner binding (all three held up in my
> tests) but treats `appUrl` as free text"

Then a `What I did NOT demonstrate` list (e.g. "I did not show a squatted record can receive another party's grants —
grants are keyed to a grantee address and I confirmed that binding is enforced"). The verified-negatives list is what
makes the one positive believable, and it pre-empts the triager's first question. It also converts a "medium, no auth
bypass" finding into a report a vendor can act on without arguing about severity first.
