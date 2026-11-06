# Web3 — On-Chain Confirmation, Source Acquisition & PoC Hygiene

> Load at **0C-Web3** (before reading any contract) and again at **0D/0E** before a PoC is called
> verified. Companion: `web3-audit-abh.md` (bug classes + grep patterns), `web3-audit` skill
> (10-class deep dive), `onchain-finding-verification` (pre-report verification).

Two failure modes this file exists to prevent: **writing a report about a contract state you never
confirmed on-chain**, and **spending hours on a PoC that requires an admin key the program excludes**.

---

## 1. Phase 0 self-test — kill the class before writing a line of PoC

Read the program's exclusions first, then test your own report sentence:

```
Draft sentence contains:  "a compromised owner could…"  /  "a malicious admin could…"  /
                          "if the deployer were malicious…"  /  "with the multisig key…"
                          ↓
             YES → the finding needs a privileged key. If the program excludes
                   admin-key / centralization / governance scenarios → STOP this class.
                   Pivot to a path an external attacker can reach: public deposit/burn/claim,
                   oracle consumers, comptroller-style external calls, unpermissioned setters.
```

Also decide up front: **primary impact** (loss of funds — the top reward tier) vs **secondary**
(frontend/dApp/UX — lower tier). Aim primary; a perfect secondary report pays a fraction.

And confirm the program actually pays: a `security@…` address with no program page and no reward
schedule is a **disclosure channel**, not a bounty. Check `SECURITY.md`, the platform page, and the
program's own reward table.

### Pre-dive kill signals (before code review)

```
TVL < $500K                                  → max payout too small for the effort
2+ top-tier audits (OZ, ToB, Cyfrin, Halborn) on THIS version, simple protocol → bugs already gone
protocol < 500 lines, single A→B→C flow      → surface too thin
max_payout = min(10% × TVL, program_cap) < $10K → skip
audited + >500K LOC                          → 40+ hours for maybe one finding; go only if floor > $50K
```

Scoring — proceed at **≥ 6/10**: TVL > $10M (+2) · Critical ≥ $50K (+2) · no top-tier audit on the
current version (+2) · deployed < 30 days (+1) · hunted this protocol family before (+1) · source +
natspec available (+1) · upgradeable proxy (+1).

---

## 2. Source acquisition (never audit bytecode blind)

```bash
# Etherscan API v2 (v1 is deprecated)
curl -s "https://api.etherscan.io/v2/api?chainid=1&module=contract&action=getsourcecode&address=ADDR&apikey=KEY"

# Custom explorer, generic shape
curl -s "https://explorer.<chain>.org/api?module=contract&action=getsourcecode&address=ADDR"

# HTML fallback when the API is rate-limited: the verified source lives in data-csource
curl -s -L -A "Mozilla/5.0 Chrome/131" "https://etherscan.io/address/ADDR#code" -o page.html
python - <<'PY'
import re
d=open('page.html',encoding='utf-8',errors='replace').read()
i=d.find('ContractName.sol')
m=re.search(r"data-csource='(.*?)'", d[i:i+200000], re.S)
open('src.sol','w',encoding='utf-8').write(m.group(1))
PY
```

Rules:
- **Verified source ≠ deployed bytecode.** If the finding depends on a specific line, confirm the
  deployed bytecode matches the verified source (compiler version, settings, and — where possible —
  a bytecode hash comparison). `live-vs-source-bytecode-forensics` has the procedure.
- Proxy → implementation: resolve the implementation address (`0x360894…` EIP-1967 slot) and audit
  the **implementation**, then check the admin and upgrade path separately.
- Multi-chain deployment = **variant hunt for free**: same code, different liquidity and different
  guards. A bug that is unreachable on mainnet can be live on an L2.

---

## 3. On-chain confirmation (do this before writing the report)

```bash
RPC=https://ethereum.publicnode.com

# owner() — selector 0x8da5cb5b
curl -s -X POST $RPC -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"ADDR","data":"0x8da5cb5b"},"latest"],"id":1}'

# EOA or contract (multisig / timelock)? 0x = EOA, long bytecode = contract
curl -s -X POST $RPC -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_getCode","params":["OWNER_ADDR","latest"],"id":1}'

# ERC20 balanceOf(ADDR) — selector 0x70a08231 + 32-byte padded address
curl -s -X POST $RPC -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"TOKEN","data":"0x70a08231000000000000000000000000<addr-no-0x>"},"latest"],"id":1}'

# native balance
curl -s -X POST $RPC -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_getBalance","params":["ADDR","latest"],"id":1}'
```

**TVL cross-check (this one has burned real sessions):** summing `balanceOf` over a handful of
well-known tokens **underestimates** TVL when the protocol holds long-tail assets. A spot-RPC total
of $613K vs a real $12.89M (nine tokens, per the explorer's Token Holdings panel) is the measured
gap — and severity is computed off TVL. Always open the explorer's **Token Holdings** section and
use that as the authoritative number; state which method you used in the report.

**Privilege quality** feeds severity directly:

```
owner = EOA, no timelock                       → admin-key risk is real, but program may exclude it
owner = multisig (n-of-m)                      → centralization; typically out of scope
owner = multisig > 5 signers + timelock > 48h  → do NOT claim "malicious team"; auto-downgrade
```

---

## 4. Foundry PoC hygiene (the checks that stop a wasted hour)

```bash
curl -L https://foundry.paradigm.xyz | bash && foundryup
mkdir -p poc && cd poc && forge init --no-git --force
forge install foundry-rs/forge-std --no-git
cast to-check-sum-address 0xabc…        # lowercase addresses fail to compile
sed -i 's/—/-/g; s/“/"/g; s/”/"/g' test/*.sol   # scrub non-ASCII from generated source
forge test --fork-url $RPC --match-path test/MyPoC.t.sol -vvvv
```

Rules for a PoC that survives triage:

- **Pin the fork block.** `vm.createSelectFork(RPC, BLOCK)` — an unpinned fork reproduces today and
  not tomorrow, which reads as unreproducible.
- **Assert the impact, not the call.** `assertGt(balanceAfter, balanceBefore)` on the attacker's
  balance, or `assertEq(totalAssets, expected)` after the drain. A test that only shows "no revert"
  proves nothing.
- **`prank(owner)` / `vm.store` / `deal()` of an unobtainable balance = FIXTURE-VERIFIED.** That
  label caps severity at MEDIUM (`evidence-state-ladder-and-reachability-gate.md`). Build the
  starting state by calling real entry points whenever possible.
- One command must prove it: `forge test --match-test test_exploit -vvvv`. No "first run the setup
  script, then…".

---

## 5. Bridge / cross-chain bonus (highest-paying surface)

```
whitelist of tokens enforced on deposit/burn?          missing → Low/Med
emergencyWithdraw / drain path                        owner EOA? timelock?
depositId / withdrawId replay across chains           → High/Critical
relayer = single EOA vs validator set                  trusted-relayer = weaker
message id built from block.timestamp / block.number   → miner-manipulable
```

Severity map: admin drain from an EOA with no timelock and > $100K at risk = Med–High · missing token
whitelist = Low–Med · replay / depositId reuse = High–Critical · reentrancy on withdraw =
High–Critical. Full checklist: `references/bridge.md` in the `web3-audit` skill and
`hunt-*` cross-chain skills.

---

## 6. Report title shape for on-chain findings

```
[Class] in [Contract::function] allows [actor] to [impact] ($X / N users)
```

Example: `Accounting desync in Vault::withdraw allows any depositor to drain 1.2M USDC of other
users' shares ($1.2M at risk)`.

Everything else follows the standard report gate (`report-writing-advanced.md`,
`triage-validation-7qgate.md`), with the program's own impact matrix as the severity authority.
