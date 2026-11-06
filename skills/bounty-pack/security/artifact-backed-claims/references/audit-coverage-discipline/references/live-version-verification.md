# Verify the live deployment before you draft

Two independent checks. Both are cheap. Both have already saved a report from being wrong.

---

## Check 1 — Does the live version match the commit you audited?

**Why this exists.** A repo cloned today may lag or lead the deployed runtime. A report against a
stale commit is worthless and embarrassing; a report against a version the vendor patched two
releases ago burns the channel.

**Worked case (DeeperChain, 2026-10-28).**
- Repo: `github.com/deeper-chain/deeper-chain` @ `ce700b14` (24 January 2025), `specVersion 76`
  in `runtime/src/lib.rs`.
- Risk: the repo's last push was April 2025 — three months after the audited commit. The deployed
  chain could have moved.
- Check: queried the live RPC before writing a single word of the draft.

### Finding the real RPC (do not guess hostnames)

Guessing `rpc.<domain>`, `rpc.<domain>.io`, `api.<domain>/rpc` all failed. The endpoint came from
the **explorer's own JavaScript bundle**:

```python
# fetch the explorer page, extract its script srcs, then grep the main bundle
grep -oE '(wss?|https)://[a-z0-9.-]+(:[0-9]+)?(/[a-z0-9/_-]*)?' main.*.js
# -> wss://mainnet-deeper-chain.deeper.network
```

The same trick worked for the API base on other targets. The explorer must talk to the chain, so its
bundle always names the endpoint.

### Querying it

**A Substrate RPC is WebSocket-only.** Plain HTTP returns `405 Method Not Allowed` — that is not a
dead endpoint, it is the wrong transport. Do not conclude "no RPC" from a 405.

```python
import json, asyncio, websockets

async def main():
    async with websockets.connect("wss://<host>", open_timeout=30) as ws:
        await ws.send(json.dumps({"id": 1, "jsonrpc": "2.0",
                                  "method": "state_getRuntimeVersion", "params": []}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                r = msg["result"]
                print(r["specName"], r["specVersion"], r["implName"])
                break

asyncio.run(main())
```

Also useful on the same connection:

| method | gives |
|---|---|
| `state_getRuntimeVersion` | `specName`, `specVersion`, `implName` — the version gate |
| `chain_getHeader` | current block number (proves the node is live) |
| `system_chain` | chain name, e.g. "Deeper Chain Mainnet" |
| `system_version` | node binary version |

### The output that made the report safe

```
specName: deeper-chain
specVersion: 76          <-- exact match to the audited runtime constant
implName: deeper-chain
chain: Deeper Chain Mainnet
header: 0x1f0607b
```

State this in the report as a verified fact: *"live chain specVersion 76 on
wss://… confirmed <date>"*. It removes the vendor's easiest objection.

**If live ≠ audited: stop and re-audit the deployed version first.** Do not draft, do not
"adjust severity", do not send with a caveat.

---

## Check 2 — Does the host actually belong to the target?

**Why this exists.** "Subdomain of the target" is not the same as "in scope". A host that resolves
to someone else's infrastructure is a DNS delegation observation, not a bug in the target's software
— and most programmes exclude exactly that.

### Worked case (RunONFlux, 2026-10-28) — the near-miss

Two subdomains were proven to serve third-party content:

```
awx.runonflux.com  -> 37.27.42.60  (Hetzner, rDNS static.*.clients.your-server.de)
                   TLS subject = CN=topy.az, byte-identical cert to topy.az
                   HTTP body identical to topy.az
account.runonflux.com -> 23.227.38.74 (Shopify edge), shopify-y meta tags
```

Both were scored **High** by the technical scorer and announced as *"ready to report"*.

The programme's own policy, verbatim:

> "Subdomains operated by third parties (e.g: info.runonflux.com)."

Excluded outright. The finding had to be retracted before it was sent.

### The three cheap ownership tells

```bash
nslookup -type=CNAME host.example.com          # CNAME to a third-party platform?
openssl s_client -connect host.example.com:443 -servername host.example.com   # subject CN
# rDNS of the resolved IP
```

If all three point somewhere other than the target's own infrastructure, the host is not theirs to
fix. At most it is a one-line good-faith note — never a bounty report.

### Rules

- **Run this before naming any host in a report body.** Not after drafting.
- **A technical severity score knows nothing about programme eligibility.** The tool scored High;
  the programme pays zero. Two different axes; the policy wins.
- **Read the exclusion list before the qualifying list.** Exclusions are specific and short;
  qualifying lists are aspirational and long.
- **Never report a third-party alias at all** unless you are explicitly filing a good-faith note.
- **A finding the vendor already rejected is closed.** Search sent mail for the target before
  drafting a "new" report on the same surface.
