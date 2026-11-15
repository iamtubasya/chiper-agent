# The `Web3Signed` envelope: EIP-191 JSON auth with a canonical body hash

A very common modern API auth shape (Vana Data Gateway + session relay, and the same pattern shows up in
SIWE-adjacent gateways): the client sends

```
Authorization: Web3Signed <base64url(payload)>.<0x 65-byte signature>
```

with a payload like

```json
{"aud":"https://session-relay.vana.org","bodyHash":"<64 hex>","exp":1791735901,
 "iat":1791735601,"method":"POST","uri":"/v1/session/init"}
```

The signature is **EIP-191 personal_sign over the base64url JSON string** (not over the JSON, not over a
hash of it). Recovering it takes ~20 lines of `eth_account`, and the payload fields are the whole
authorization model — which makes it worth reconstructing properly instead of replaying a captured header.

## The two ways the body hash bites (both hit live, 2 cycles)

| Symptom from the server | Cause | Fix |
|---|---|---|
| `expected 4dd5… actual sha256:4dd5…` | the server's `bodyHash` is **bare lowercase hex**, no `sha256:` prefix | strip the prefix |
| `expected 4dd5… actual <other>` | your JSON is not what it hashes | hash the **canonical** form: `json.dumps(obj, sort_keys=True, separators=(",",":"))` |

The server returning `expected` vs `actual` is a free oracle: you do not have to guess the scheme, you
iterate against the value it prints. Check that first before suspecting the signature.

Build the request so the hash and the body cannot disagree — one string, used twice:

```python
body = json.dumps(obj, sort_keys=True, separators=(",", ":"))     # canonical, compact, sorted
body_hash = hashlib.sha256(body.encode()).hexdigest()             # BARE hex
payload = {"aud": BASE, "bodyHash": body_hash,
           "exp": now + 300, "iat": now, "method": "POST", "uri": "/v1/session/init"}
pb = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
sig = "0x" + Account.sign_message(encode_defunct(text=pb)).signature.hex()
requests.post(BASE + "/v1/session/init", data=body,                 # <- send the SAME canonical string
              headers={"Content-Type": "application/json",
                       "Authorization": f"Web3Signed {pb}.{sig}"})
```

Send the canonical string as the literal body. If you send a differently-keyed JSON of the same object,
the server re-canonicalizes and the hashes diverge again.

## What this envelope gives an auditor (and where the bugs are)

- **`aud` is bound and enforced.** A header signed for one origin fails against another — replay across
  hosts is closed. Verify it (it is a good control) rather than assuming it.
- **`method` + `uri` are bound.** The same signed header cannot be re-aimed at a different endpoint.
- **`bodyHash` is bound.** You cannot re-sign-free mutate a body field. Corollary: if a deployment ever
  computes the hash over a *subset* of the body, or only over the path, that is the CoinMate-style
  finding — check what the server actually hashes by mutating one body field and watching whether it
  still accepts (see the packet-first ladder in the parent skill).
- **Trace the verifier, not just the signer.** In this engagement the interesting findings were on the
  *server* side of the envelope (a relay that marked a session approved without checking the grant the
  payload referenced; a gateway that accepted a self-asserted approval). The signature was sound — the
  authorization decision downstream of it was not.

## Reconstructing it fast

`eth_account` + `eth_keys` in one small module is enough:

```python
from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data
from eth_keys import keys

def uncompressed_pubkey(acct):                     # 0x04… form, when an API wants it
    return "0x04" + keys.PrivateKey(bytes(acct.key)).public_key.to_hex()[2:]
```

EIP-712 typed data (builder/grant/server registrations) uses `encode_typed_data(full_message={...})` with
an explicit `EIP712Domain` entry:

```python
E = [{"name":"name","type":"string"},{"name":"version","type":"string"},
     {"name":"chainId","type":"uint256"},{"name":"verifyingContract","type":"address"}]
td = {"domain":{"name":"Vana Data Portability","version":"1","chainId":1480,
                "verifyingContract":CONTRACT},
      "types":{**TYPES, "EIP712Domain": E}, "primaryType":"GrantRegistration", "message": msg}
sig = "0x" + acct.sign_message(encode_typed_data(full_message=td)).signature.hex()
```

Notes: `acct.sign_message(...).signature.hex()` returns **no `0x` prefix** — prepend it or the API
rejects with a pattern error. And read the domain (`chainId`, `verifyingContract`) out of the vendor's
own client/SDK rather than guessing: getting `chainId` wrong silently produces a valid-looking signature
that never recovers to your address.
