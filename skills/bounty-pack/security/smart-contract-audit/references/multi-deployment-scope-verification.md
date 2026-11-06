# Multi-deployment scope: one bug, N chains, and which address is actually live

For any protocol deployed by CREATE2 across many chains. A finding is not "a bug in contract X" —
it is "a bug in *this deployed instance*", and those differ per chain more often than you expect.
Established on a Relay v3 Router audit (2026-10-08) where the answer flipped twice.

## 1. The registry is not the live system

`deployments/<ver>/addresses.json` in the repo gives you the map — chainId, router, approval
proxy, evmVersion. Read it first; it is the cheapest complete inventory you will get.

```python
d = json.loads(Path("deployments/v3/addresses.json").read_text())
# group by address to see the blast radius instantly
from collections import Counter
Counter(e["relayRouter"].lower() for e in d if e.get("relayRouter"))
```

That single grouping is what turned "one contract on Base" into **2 router addresses across 83
chains**. Always group by address before writing a word of impact.

**But do not trust it as truth.** In the session, the registry said Base used
`0xe6b730e5…` while the public quote API returned `0xb92fe925…` as the referenced order address
on live routes. Two routers were deployed on Base; the registry named the newer one, production
used the older one. **The registry tells you what exists; the API and the chain tell you what is
used.** Cite the API/chain evidence in the report, not the registry.

How to find what production really uses when the docs are ambiguous:

```bash
curl -s -X POST https://api.<target>/quote -H 'Content-Type: application/json' \
  -d '{"user":"0x1111…","recipient":"0x2222…","originChainId":8453,"destinationChainId":42161, …}' \
  | grep -oE '"extraData":"0x[0-9a-f]{64}"'
```
An ABI-padded 32-byte value whose low 20 bytes are a known deployment address is the protocol
telling you which contract it routes to. Query several routes (both directions, several chains) —
one route can be a special case.

## 2. Probe the DEPLOYED bytecode, never the repo

State the finding against the chain's own code. A local tree can be ahead of, behind, or simply
different from what is deployed, and "the repo has the fix" is not "the contract has the fix".

```bash
forge test --match-path test/MultiChain.run.sol --fork-url <rpc> -vv
```

One test file, the router address as a constant the runner rewrites per chain, and the fork RPC
selecting the chain. That is enough to sweep every deployment.

## 3. Harness traps that produce CONFIDENT WRONG ANSWERS

These are the ones that bit, in order of danger:

**(a) The verdict label can be inverted, and nothing crashes.** The probe's `test_B` PASSES when
the assertion `require(probe.reentered())` holds — i.e. PASS means VULNERABLE. A runner that maps
`"[PASS] test_B" -> "NOT AFFECTED"` reports a vulnerable contract as healthy, silently, with a
green suite. **Always cross-check at least one chain whose verdict you already proved
independently.** In the session Base read "NOT AFFECTED" from the runner while a previously-verified
fork test had proven it vulnerable — that contradiction is the only reason it was caught. Prefer
naming tests for the OBSERVATION (`test_guard_is_disarmed`) over the conclusion, and print the raw
assertion message next to the verdict.

**(b) Solidity rejects non-checksummed address literals; the registry stores lowercase.**
`address constant R = 0xb92fe925DC…` fails to compile when the case is wrong. Hand-rolling EIP-55
is a trap because Python's `hashlib.sha3_256` is **NIST SHA3, not keccak256** — you will produce a
valid-looking checksum that Solidity rejects. Sidestep both: construct from a decimal literal.

```python
t = re.sub(r"address constant ROUTER = [^;]+;",
           f"address constant ROUTER = address(uint160({int(addr, 16)}));", t)
```
Related: `printf '%d' 0xb92fe925…` overflows bash's integer (**"Numerical result out of range"**)
and yields a truncated constant — do hex→decimal in Python, not the shell.

**(c) Public RPCs flake, and a flake must never become a verdict.** Seen in one sweep: `403
Forbidden` from `urllib` on a host that answers `curl` fine (send a User-Agent), `eth_getLogs`
range caps that make a log count come back `0` for an active contract, and `eth_getCode` errors
that make a binary-search-for-deployment-block drift to the chain head (it reported both routers
as "deployed 91 blocks ago"). Rules:
- retry with backoff (3 attempts), and treat exhaustion as **`RPC_FAIL` / `INCONCLUSIVE`**, never
  as "not affected";
- distinguish `INCONCLUSIVE (control did not pass)` from a real negative. A control that fails
  means the harness or the RPC broke, not that the target is safe;
- if two chains disagree with a third known result, suspect the harness before the target.

## 4. Report the scope you can defend

Split the deployments into a table with a state per group, and say which were probed and which
were not:

| router | chains | guard state |
|---|---|---|
| 0xe6b730e5… | 54 | corrected |
| 0xb92fe925… | 22 | **subject of this report** |

Then: "every probe of the 54-chain router returned *guard held*; every probe of this address
returned *guard disarmed*, each with its own passing control." That sentence is worth more than a
claim of "affects 83 chains" — and the narrower number is the one that survives triage.

Chains that share one address share one verdict. You may probe a representative subset, but SAY
so rather than implying per-chain testing.

## 5. Checklist

- [ ] Grouped the registry by address to get the real blast radius
- [ ] Found which address the LIVE API/chain actually references (registry ≠ live)
- [ ] Every verdict comes from a fork against deployed bytecode, not from reading the repo
- [ ] ≥1 chain already proven independently is used to validate the runner's labelling
- [ ] Hex→decimal conversions done in Python (`address(uint160(<int>))`), never `printf`
- [ ] RPC failures landed in `INCONCLUSIVE`/`RPC_FAIL`, not in "not affected"
- [ ] Report names the probed address, the chains it serves, and which chains were not probed
