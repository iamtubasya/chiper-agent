# Vendor-run / self-hosted programs — recon + scope gate

For a **vendor-run (self-hosted) bug bounty on a dApp + protocol** — the program lives on the
project's own site, not on HackerOne/Bugcrowd/Immunefi. The program publishes its own scope gate,
its own known-issues list, and often its own copy of the source. Read those before recon.

Worked example: **TimbSwap** (DEX + on-chain prize game, Arbitrum Sepolia). 16 in-scope contracts,
40 sources, full review, 0 new payout-grade findings, 1 real defect found in a non-deployed stub.

---

## 1. Read the program's OWN policy first (it is the scope gate)

Usually `/SECURITY.md`, linked from a `/source/` or `/docs/` page. Extract FIVE things:

| extract | why |
|---|---|
| report channel (e-mail / private advisory) | some take e-mail only; the repo may be unreachable |
| **scope IN** (which deployments count) + **OUT** | OUT usually names contract *groups*, not one contract |
| **known-issues table** (refs like `TS-001…TS-023`) | this is a **do-not-report list** — re-reporting earns $0 |
| severity **tier table** with dollar bands | write impact in THEIR tier language, don't invent CVSS bands |
| rules of engagement | e.g. "prefer your own local fork", "do not DoS the shared testnet/faucet/keepers" |

Terminology that recurs and costs money if misread:
- *"an earlier build than the mainnet source"* → a testnet finding already fixed in the repo's
  mainnet source is **known**, even though the testnet still shows it. You need BOTH sources.
- *"ownership and privileged roles"* → owner/admin/centralisation findings are **out** when the
  deployment is a single key. Filter them out of your candidate list early, not at write-up time.
- *"value stuck, not lost"* → the program's operational tier (DoS/liveness), a lower band than theft.
- Any explicitly enumerated group (`SwapTables (SegmentBoard*, SeedRegistry, PoolLedger)`) is out.

Do the filter **before** deep review. On TimbSwap, ~4 of the first-cut candidates were
unwinnable purely because the policy pre-excluded owner-power and non-deployed stubs.

---

## 2. Get the source even when the repo is down

A project-run site almost always ships the source itself.

```bash
curl -s -L "https://<site>/<project>-source.zip" -o src.zip      # full source at the DEPLOYED commit
unzip -o -q src.zip -d src/ && find src -name '*.sol' | wc -l
curl -s -L "https://<site>/SECURITY.md" -o SECURITY.md
curl -s -L "https://<site>/SPECS.md"   -o SPECS.md
curl -s -L "https://<site>/CHANGELOG.md" -o CHANGELOG.md
```

- The zip is the **deployed** commit. A distinct "mainnet source" may live only in the git repo.
  If the repo is unreachable (account under review, 404 on `raw.githubusercontent.com` and
  `cdn.jsdelivr.net/gh/...`), **say so explicitly in the report** and label the diff as not
  performed — do not silently assume parity.
- The `/source/` page's contract list is frequently split: deployed set first, then
  *"Also in contracts/ (libraries, interfaces, earlier boards, test assets)"*. **Group 2 is
  usually NOT deployed.** Cross-check against the address manifest (below) before writing
  anything up — a real defect in a non-deployed stub is a scope flag, not a payout.
- `CHANGELOG.md` is the ops log: it names incidents, migrations and which preventions shipped.
  Cheap way to learn what the team already knows is fragile.

## 3. The address manifest is `config.js` (for a JS dApp)

```bash
curl -s -L "https://<site>/config.js" -o config.js
grep -oE "0x[a-fA-F0-9]{40}" config.js | sort -u          # the deployed address SET
grep -nE  "0x[a-fA-F0-9]{40}" config.js                   # name <-> address map, one line per role
```

This single file is the fastest possible map of the protocol's shape (factory/router/pair,
prize/registry/escrow/vault, staking/farm/treasury/faucet). Watch for comments like:

```
TimbPrize: "0x6027…", // gen-3 re-migration — aligned prize bound to the new registry … Prev: 0x5AED…
```

Those tell you which contracts were migrated and which fixes already landed — i.e. which landmines
are known. Also grab the site's `landing.js`/page bundles for API endpoints and an `/api/rpc` proxy.

## 4. Prove an interface / integration mismatch on-chain (missing selector)

Cheap, decisive, submittable:

```bash
cast call <ADDR> "fn()(uint256)" --rpc-url $RPC
#  execution reverted, data: "0x"     <-- EMPTY payload = no such selector AND no fallback
cast call <ADDR> "currentRound()(uint256)" --rpc-url $RPC
#  110                                <-- control: proves the RPC/address are fine in the same block
```

Pair it with a source grep proving the identifier exists only in the **caller**:

```bash
grep -rn "cumulativeRounds" contracts/        # only TimbReleaseVault.sol (decl + call site)
grep -n "function cumulativeRounds" contracts/GameRegistry.sol   # no match
```

That combination — "X calls `Y.foo()`; `foo` exists nowhere but X; the live Y reverts on the
selector with an empty payload" — is a complete, verifiable finding. Note it does **not** require
foundry at all.

## 5. Live balance-sheet invariant check (retire whole hypotheses for free)

For any custody/accounting contract, read the counters and assert the sheet balances:

```bash
for f in currentAccumulatedRewards gameUnclaimed_winningsPool protocolCutAccrued; do
  printf "%-28s " "$f"; cast call $PRIZE "$f()(uint256)" --rpc-url $RPC; done
cast balance $ESCROW --rpc-url $RPC
# escrow.balance  ==  pot  +  unclaimedPool  +  cutAccrued      <- must hold to the wei
```

TimbSwap round #110: `0.5020 ETH == 0.4176 + 0 + 0.0843` ✓ exactly. A sheet that balances to the
wei **retires an entire class** of "missing/lost accounting" hypotheses; write it down as a
**verified negative** (the user counts negatives as deliverables). A sheet that does *not* balance
is an immediate candidate.

Also read the config/state counters for anomalies: `pricedForRound` vs `currentRound`, a meter
(`totalEthEscrow`, `activeTimbEntries`) that disagrees with live ticket counts, `entriesPaused`/
`settlementPaused` unexpectedly true, `epoch`/`generation` mismatched between two contracts that
are supposed to move together.

## 6. Build / static analysis on such a repo

```toml
# foundry.toml
[profile.default]
src = "contracts"
out = "out"
libs = ["lib"]
solc = "0.8.24"
optimizer = true
optimizer_runs = 200
via_ir = true                                   # REQUIRED if any contract hits "Stack too deep"
remappings = ["@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/"]
```

- `forge build` failing with `Stack too deep. Try compiling with --via-ir` on **one** contract
  (TimbSwap: `DDJackpot.sol`) → set `via_ir = true`. Expect a much slower build (minutes, not seconds).
- Under `via_ir`, slither's compile step becomes very slow. Run it in the background with a long
  timeout, and/or fall back to **manual review + `cast` live reads**, which is what actually found
  the defect on TimbSwap. If you do run it: `forge build --build-info` first, then
  `slither . --compile-force-framework foundry --solc-remaps "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/"`.
- `forge init --no-git --force` is not needed — the vendor zip already contains `foundry.toml`;
  just `mkdir -p lib && git clone --depth 1 <openzeppelin>` and keep their layout.

## 7. Sweep for un-guarded value-moving functions (fast triage filter)

Enumerate every `external`/`public` function in the in-scope contracts and flag those with no
access modifier, then read each one and decide if it is *intentionally* permissionless
(`settleSegment`, `claimWinnings`, pair `swap/skim/mint/burn`, router swaps) or a miss. A quick
Python/AST-ish grep over the signatures (joining multi-line params) is enough — it catches a
missing `onlyOwner` in seconds and produces the negative list you need for the coverage ledger.

## 8. Scope-flag before you write

```json
{
  "id": "PROJ-001",
  "title": "...",
  "severity": "Medium",
  "target": "contracts/X.sol:38,72  vs  contracts/Y.sol (live 0x…)",
  "scope_note": "SCOPE FLAG: X.sol ships in contracts/ but is absent from config.js / the Docs
                 address table; its header marks it a stub. If the program counts only address-table
                 deployments this is out of scope.",
  "description": "...", "impact": "...", "reproduction": "...", "remediation": "..."
}
```

Keep `description`/`impact` free of the words the local gate treats as by-design admissions —
see the `finding_gate.py` phrasing trap in `vuln-hunter`. Re-run the gate after any rewording.
