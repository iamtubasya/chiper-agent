# Vendor-hosted payment and code-execution boundaries

Two surfaces that show up together on AI/agent platforms and both reward the same question:
**the vendor runs something on the user's behalf — does the boundary actually hold?**

Measured 2026-10-30 on Bankr (`x402.bankr.bot` paid endpoints, `webhooks.bankr.bot` handlers).
Both came back **sound**; the value here is the method and the exact probes, so the next audit
either reuses them or can honestly say "tested, held".

---

## 1. x402 payment gate — tamper matrix

x402 settles a per-request payment. The two schemes in the wild:

| scheme | mechanism | what it looks like on the wire |
|---|---|---|
| `exact` | EIP-3009 `transferWithAuthorization` | payer signs `{from,to,value,validAfter,validBefore,nonce}` |
| `upto` | Permit2 `permitWitnessTransferFrom` + witness `{to,facilitator,validAfter}` | payer signs a Permit2 permit + witness |

### Step 1 — get a live 402 challenge

```bash
curl -sS "https://<paid-host>/<owner>/<service>" -o ch.json -w "%{http_code}\n"
# 402
```

```json
{"x402Version":2,"error":"Payment Required","accepts":[{
  "scheme":"exact","network":"eip155:8453","maxAmountRequired":"1000","amount":"1000",
  "resource":"https://…","payTo":"0x8AEE…01a0","maxTimeoutSeconds":60,
  "asset":"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
  "extra":{"name":"USD Coin","version":"2"}}],
 "facilitator":"https://api.<host>/facilitator"}
```

Everything needed to forge a payment is in that challenge — that is the point of x402, and it is
why the **verifier** is the whole security surface.

### Step 2 — sign with a ZERO-BALANCE throwaway key

Never use a funded key for tamper tests. A zero-balance signer produces a *cryptographically valid*
authorization that only fails on funds, which isolates "is the signature/amount/recipient checked"
from "does the payer have money".

```python
import json, time, secrets, base64
from eth_account import Account

acct = Account.from_key("0x" + "11"*32)          # deterministic throwaway
pay_to, usdc = "0x8AEE…01a0", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"

def mk(value, to=None, tamper_after_sign=False, version=2):
    now = int(time.time())
    auth = {"from": acct.address, "to": to or pay_to, "value": str(value),
            "validAfter": str(now-600), "validBefore": str(now+3600),
            "nonce": "0x"+secrets.token_hex(32)}
    typed = {
      "types": {
        "EIP712Domain": [{"name":"name","type":"string"},{"name":"version","type":"string"},
                         {"name":"chainId","type":"uint256"},{"name":"verifyingContract","type":"address"}],
        "TransferWithAuthorization": [{"name":"from","type":"address"},{"name":"to","type":"address"},
                                      {"name":"value","type":"uint256"},{"name":"validAfter","type":"uint256"},
                                      {"name":"validBefore","type":"uint256"},{"name":"nonce","type":"bytes32"}]},
      "primaryType": "TransferWithAuthorization",
      "domain": {"name":"USD Coin","version":"2","chainId":8453,"verifyingContract":usdc},
      "message": auth}
    sig = Account.sign_typed_data(acct.key, full_message=typed).signature.hex()
    if not sig.startswith("0x"): sig = "0x"+sig
    a2 = dict(auth)
    if tamper_after_sign: a2["value"] = "0"      # signature says 1000, body says 0
    p = {"x402Version": version, "scheme": "exact", "network": "eip155:8453",
         "payload": {"signature": sig, "authorization": a2}}
    return base64.b64encode(json.dumps(p).encode()).decode()
```

Send it as the `X-PAYMENT` header (base64 of the whole JSON object).

### Step 3 — the four tamper classes

| # | Tamper | Secure answer | Observed |
|---|---|---|---|
| A | `value: 0` | rejected | `insufficient_funds` |
| B | recipient swapped to the payer's own address | `recipient_mismatch` | `invalid_exact_evm_payload_recipient_mismatch` |
| C | sign for 1000, declare 0 in the body | `signature` invalid | `invalid_exact_evm_payload_signature` |
| D | `x402Version: 1` | `network`/version mismatch | `invalid_network` |

All four rejected **with distinct reasons**. That distribution is the evidence: a verifier that
returned one generic error for everything could be failing at one check and hiding the rest.
Distinct per-field errors prove amount, recipient, signature and network are each checked
independently. Record the exact reason strings — they are what makes "the gate is sound" a
measurement instead of an opinion.

Also worth one request: `GET <paid-host>/…` **without** any payment header must return `402` +
the challenge, not the service. And the facilitator (`/facilitator/verify`, `/facilitator/settle`)
is usually internal-only — an API key giving `{"error":"missing bearer token"}` means it is not
reachable from the researcher surface; note it as unreachable, not as a bug.

### Honesty bound

`settle-after-response` means a **valid, funded** authorization is the only thing that proves the
settlement leg. With a zero-balance key you prove *verification*, never *settlement*. Say
"verification rejects all tampered payloads; settlement not exercised (no funds)" — do not imply
you tested the money movement.

---

## 2. Hosted serverless handler — is the sandbox boundary real?

When a platform lets you deploy code (x402 services, webhook handlers, app scripts), the policy
usually pays for "escape from the sandbox". The decisive question is not "can I call
`child_process`" — it is **"is there anything reachable on the other side"**.

### The probe

Deploy a handler that shells out, because the JS-level `fetch` filter is usually *not* the only
control:

```js
const sh = (cmd, t = 6000) => { try { const cp = require('node:child_process');
  return String(cp.execSync(cmd + ' 2>&1', { timeout: t, stdio: ['ignore','pipe','pipe'] })).slice(0,1200);
} catch (e) { return 'ERR:' + String((e && e.stdout) || e && e.message).slice(0,300); } };

export default async function handler(req) {
  const out = {
    fib:   sh('cat /proc/net/fib_trie | head -40'),   // interfaces + routes (ip/ss often absent)
    hosts: sh('cat /etc/hosts'),
    resolv:sh('cat /etc/resolv.conf'),
    env:   sh('env | sort'),
    proc1: sh('cat /proc/1/environ 2>&1 | tr "\\0" "\\n" | head -30'),
    id:    sh('id; ls -la /var/task; ls -la /opt'),
  };
  for (const t of ['169.254.100.5:53','169.254.100.1:80','169.254.100.6:80',
                   '169.254.170.2:80','127.0.0.1:9001','169.254.169.254:80']) {
    out['p_'+t] = sh('curl -sS -m 3 -o /dev/null -w "%{http_code}" http://' + t + '/ || true');
  }
  console.log('PROBE:' + JSON.stringify(out));       // read back from the invocation-log endpoint
  return new Response(JSON.stringify({ prompt: 'ignore' }), { status: 200,
    headers: { 'content-type': 'application/json' } });
}
```

Why each target matters:

| target | what it would give you |
|---|---|
| `169.254.170.2` | ECS task-role credentials endpoint |
| `169.254.169.254` | IMDS |
| `127.0.0.1:9001` | Lambda Runtime API — `/2018-06-01/runtime/invocation/next` |
| gateway / resolver on the local /30 | lateral movement inside the account |
| `/proc/1/environ` | supervisor env (creds often live here) |

### Reading the result

Observed on Bankr: function in `169.254.100.4/30` (host `.6`, resolver `.5`), **no default route**
in `/proc/net/fib_trie`, `ip`/`netstat`/`ss` absent from the image, `/proc/1/environ` permission
denied, and **every** internal probe returning `000` (no route). `require('node:fs')` and
`child_process` both work, so it is a real shell — with nowhere to go.

Interpretation rules:

- **`execSync` succeeding is not a finding.** A shell inside a network-isolated function is a
  design choice (build steps need it). The finding is reachability of something privileged.
- **`000` on every internal target = isolated.** That is a *strong negative* worth stating: the
  JS `fetch` egress filter that blocks `127.0.0.1`, `nip.io`, decimal/hex IPs and
  `[::ffff:127.0.0.1]` is defence-in-depth on top of real isolation, not the only control.
- **A JS-only egress filter with a working `curl` is worth one more look**, but only if you can
  name a reachable internal service. "The filter is bypassable" with no target is not a finding —
  do not report the bypass alone.
- Check `env` and `/proc/1/environ` for `BANKR_*`-style prefixes, `AWS_*`, DB URLs. Present →
  escalate to a credential-exposure finding. Absent → say absent.

---

## 3. Why these two sit together

Both are "the vendor executes on your behalf". The failure mode is identical: the researcher finds
*code execution* (a shell, a valid signature) and reports it, when the actual security property is
the **boundary on the other side** — reachable services, and verified amounts/recipients. Report the
boundary, not the primitive.

Coverage line that stays honest for both:

> x402: verification rejects value/recipient/signature/network tampering (4/4, distinct reasons);
> settlement not exercised (no funded payer).
> Handler sandbox: shell available by design; every internal target (ECS creds, IMDS, Lambda
> runtime, local gateway) unreachable (`000`); no vendor credentials in `env` or `/proc/1/environ`.
