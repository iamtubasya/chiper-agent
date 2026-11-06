# Off-chain signed-gateway layer: EIP-712 / Web3Signed authorization testing

> When to read this: the protocol's **money or consent logic lives behind an HTTPS API** (an "RPC
> gateway", a relay, a hosted compute service) and the contracts only anchor state. The classic
> shape is a *consent/grant protocol*: users sign grants, an app/gateway stores them, personal
> servers and relays enforce them. Verified end-to-end on Vana (2026-10-11/12).

## 0. The layer exists even when the docs talk contracts

Vana's contracts (`DataPortabilityPermissions/Servers/Grantees/Escrow/DataRegistry`) held the
*anchors*; the actual reads, approvals, grants, webhooks and escrow math ran through
`dp-rpc.<host>`, `session-relay.<host>`, `storage.<host>` and a hosted app. Auditing only the
contracts would have missed every finding that mattered. **Enumerate the HTTPS surfaces first**,
then use the contracts to check whether a client-side assertion is actually enforced on-chain.

## 1. Fingerprint the signature surfaces before probing

| Surface | Where to look | Example seen |
|---|---|---|
| EIP-712 typed data | the protocol's own client SDK/CLI (`*.ts` with `EIP712Domain`, `*_TYPEHASH`) | `BuilderRegistration{ownerAddress,granteeAddress,publicKey,appUrl}`, domain `{name:"Vana Data Portability",version:"1",chainId:1480,verifyingContract:0x...}` |
| EIP-191 signed request header | gateway client code building `Web3Signed <b64url(json)>.<sig>` | `{"aud","bodyHash","exp","iat","method","uri"}` |
| EIP-3009 (gasless token moves) | escrow deposit paths | `receiveWithAuthorization`, nonce = `keccak(account, salt)` |
| Bearer / session token | device-login, CLI tokens | `vana_ps_<random>` |

**Pull the domain constants from the vendor's own client package, never invent them.** Install or
unpack the published SDK/CLI and read the typehash + domain builder; a wrong `verifyingContract`
or `chainId` produces a 401 that reads like "the binding is strong" when it is your signature that
was malformed.

## 2. Build the signatures locally (eth_account)

```python
from eth_account import Account
from eth_account.messages import encode_typed_data, encode_defunct
from eth_keys import keys

E = [{"name":"name","type":"string"},{"name":"version","type":"string"},
     {"name":"chainId","type":"uint256"},{"name":"verifyingContract","type":"address"}]

def typed(acct, contract, tname, tfields, msg):
    full = {"domain": {"name":"<protocol>", "version":"1", "chainId":<id>, "verifyingContract":contract},
            "types": {tname: tfields, "EIP712Domain": E}, "primaryType": tname, "message": msg}
    sig = acct.sign_message(encode_typed_data(full_message=full)).signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig        # .hex() has NO 0x prefix

def web3signed(acct, aud, method, uri, body):
    import hashlib, json, base64, time
    bh = hashlib.sha256(body.encode()).hexdigest() if body else ""
    iat = int(time.time())
    pl = dict(sorted({"aud":aud,"bodyHash":bh,"exp":iat+300,"iat":iat,"method":method,"uri":uri}.items()))
    pb = base64.urlsafe_b64encode(json.dumps(pl, separators=(",",":")).encode()).decode().rstrip("=")
    sg = acct.sign_message(encode_defunct(text=pb)).signature.hex()
    return f"Web3Signed {pb}.{sig if sig.startswith('0x') else '0x'+sg}"

def identity():
    a = Account.from_key("0x"+secrets.token_hex(32))
    return a, "0x04" + keys.PrivateKey(bytes(a.key)).public_key.to_hex()[2:]   # uncompressed pubkey
```

Traps that cost a cycle each:
- `Account.sign_message(...).signature.hex()` returns **no `0x` prefix**; endpoints that pattern-check
  `^0x[a-fA-F0-9]{130}$` reject it with a *different* error and you misread the result.
- The signed body hash is **sha256 of the canonical, compact, sorted-key JSON, bare hex**. A
  `sha256:` prefix, unsorted keys, or `separators` with spaces yields a 401 that looks like a
  binding failure. (The relay even distinguishes the two error types — read the message.)
- The public key must be the **uncompressed** `0x04…` form when the endpoint derives the address.

## 3. The binding test matrix — every row is a deliverable

Run each row and record status + body. A 401 is a *control that works* (write it in the report);
a 201/200 is a finding.

| # | Test | Expected if bound |
|---|---|---|
| 1 | sign with **my** key, claim **victim** as subject (`grantorAddress`, `ownerAddress`) | 401 |
| 2 | sign, then **swap a field** in the body (change grantee/amount/scope, keep the signature) | 401 |
| 3 | register my **own** delegate/server, then sign for **another** owner | 401 |
| 4 | **replay** the same signed request / reuse the signature on a fresh nonce | rejected (look for a monotonic `version`, an explicit nonce, or an expiry) |
| 5 | **binding checks**: pubkey ↔ claimed address; server registration ↔ owner; domain pinning | 400/401 |
| 6 | **open registration**: can I register an identity, app URL, or server I do not control? | if 201 → finding |
| 7 | unauthenticated read/write per endpoint (GETs first, then POSTs that only mutate *your* state) | 401 where authorisation is real |

Also test the *ordering*: a shape like `404 Operation not found` for a resource you cannot own —
with a perfectly valid-format signature — means lookup happened **before** signature verification.
That is an auth-ordering weakness; report it as such (Low) unless you can obtain a real ID that
belongs to someone else, in which case it becomes the IDOR you were looking for.

## 4. Finding shapes this layer produces (all reproduced ≥3× on Vana)

- **Open identity registration with an unowned URL** — `POST /v1/builders` accepted
  `appUrl: https://app.vana.org` from a throwaway key, and the URL was not even unique (a second
  unrelated key registered it again). Impact framing that survived review: a *public registry
  record* under someone else's product URL + no ownership signal. Do **not** claim grants/fees
  flow to the squatter unless you proved it — grants are keyed to the grantee address.
- **Webhook = attacker-controlled outbound request, plus an unverified consent hand-off** —
  a relay accepted `webhookUrl` (https-only, no destination policy) and marked a session
  `approved` from self-asserted values. Proof set that made it undeniable: (a) OOB collector
  received the POST with egress IP + proxy headers quoted, (b) the fabricated `grantId` was
  **404 on the authoritative API**, (c) three runs with distinct markers. The relay itself is the
  component that documents itself as the consent hand-off, which is what makes the gap worth
  reporting.
- **Unauthenticated financial metadata + unauthenticated state trigger** — `balance?account=`,
  `withdraw/nonce?account=`, and a `balance/sync` endpoint that mutates state for any account.
- **Read-back that returns stored signatures** (`proof.userSignature`) — a QA note, not a finding,
  unless you can replay them (the domain pins chainId + verifyingContract).
- **Hosted compute/artifact API where lookups precede signature checks** — record honestly as
  auth-ordering until you hold a real operation ID; do not inflate it into "anyone can read
  anyone's artifacts".

## 5. Method discipline for this layer

- **Register your own identifiers** (builder, server, app) instead of guessing; most findings need a
  valid actor of your own plus a forged claim about someone else.
- **Re-validate 3× from a fresh client context** before writing a word — this is the operator's
  standing rule, and this layer is exactly where one-shot requests lie (rate limits, caches,
  ordering).
- **Assume the doc's claims are marketing until the code shows otherwise.** "The operator cannot
  redirect balances" was true of the *gateway policy* and false of the *contract role*.
- **By-design is a finding's worst enemy — check it explicitly.** A relayer public-key endpoint that
  returns a public key is by design; a debug endpoint in production is not. Label both so the
  triager does not have to guess, and say which one you consider a finding.
- Use **interactsh** for OOB proof and quote the raw interaction (remote address, proxy IDs,
  timestamp) — a "the webhook fired" claim without a captured request is not evidence.
