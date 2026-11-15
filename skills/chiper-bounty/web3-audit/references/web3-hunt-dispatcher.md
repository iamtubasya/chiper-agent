# Web3 Hunt Dispatcher — fingerprint → skill → kill signal → first probe

One table to route a web3 target to the right `hunt-*` skill. The individual hunt skills
(vault-inflation, oracle-l2, permit2, amm-hooks, aa-modular, diamond-proxy, intent-settlement,
restaking-lrt) are already exhaustive — each carries Phase 0 kill test, 5 minimum probes, Gate 0,
runnable `cast` probes, by-design calibration, and a lab calibration with real numbers. This file is
**only** the routing index so you start on the right skill instead of re-reading all eight.

## When to use (instead of guessing)

You have a target address / repo / protocol brand. Fingerprint it, look up the row, run the kill
signal, then open the named skill.

## Dispatch table

| Fingerprint (repo/ABI/on-chain) | Skill | Pre-dive KILL signal | First probe |
|---|---|---|---|
| `convertToShares` / `convertToAssets` / `previewDeposit` / `totalAssets`, any vault/LRT/LP receipt | `hunt-vault-inflation` | single-party? (`public(address)` + gated deposit/withdraw) — if one actor, kill | `convertToShares(1e18)` + donation `transfer` + victim deposit → shares==0? |
| `sequencerUptimeFeed` / `latestRoundData` / `getPriceUnsafe` / `.conf` / any L2 lending-perp with price | `hunt-oracle-l2` | is the price *read by a privileged action* (borrow/liquidate)? if not, hardening note | `borrow()` with a mocked-down sequencer → succeeds? |
| `permit` / `transferWithAuthorization` / `permit2` / `ISignatureTransfer` / EIP-712 approval | `hunt-permit2-signature` | domain separator census: is `chainId` + `verifyingContract` bound? | same signature replayed on 2nd deploy / 2nd execution → accepted? |
| `PoolManager` / `swap` / `beforeSwap` / `afterSwap` / hooks / singleton AMM | `hunt-amm-hooks` | is the hook address bound into `PoolKey` + gated at `initialize`? | `initialize` a pool with attacker `hooks` → accepted? |
| `installModule` / `setValidator` / `setExecutor` / module registry / EIP-7702 | `hunt-aa-modular` | does module install require allowlist + owner? (delegatecall + no allowlist = already Critical) | `installModule(1, ATTACKER, "")` from controlled acct → installed? |
| `diamondCut` / `facet` / `upgradeTo` / `upgradeToAndCall` / proxy / beacon | `hunt-diamond-proxy` | upgrade authority: timelocked multisig? (EOA owner = centralization, not bug) | `diamondCut` from non-owner → reverts? |
| `solve` / `fill` / `settle` / attestor / off-chain solver / bridge settle / RFQ | `hunt-intent-settlement` | "parameter accepted but never validated" — allowlist declared but not read in the write path? | `fill()` with an unapproved solver → accepted? |
| `slash` / `withdrawal` queue / `exchangeRate` / operator registry / AVS / LRT | `hunt-restaking-lrt` | can an attacker trigger slash, or does a committee + challenge window gate it? | `slash(op, amt, fabricatedOffence)` from no-role key → executes? |
| Move-VM (Supra/Aptos/Sui), no source repo, RPC only | `web3-audit` class 12 | sweep every `is_entry` fn with no `&signer` | read `/resources/<TYPE>` payload, execute `view` math |
| Solidity/Vyper/Rust generic protocol audit, no specific class yet | `web3-audit` | PRE-DIVE: TVL < $500K / 2+ top audits / <500 LOC → skip | repo reality checks (live version, language, vendored split, compiler CVE, source==deployed) |

## Cross-class composition (one primitive feeds the next)

```
flash loan / donation  →  hunt-amm-hooks (pool as oracle)  →  hunt-oracle-l2 (downstream reads it)
oracle manipulation   →  hunt-restaking-lrt (LRT rate desync)  →  hunt-vault-inflation (share drain)
permit replay         →  hunt-permit2-signature  →  hunt-intent-settlement (attestation under-bound)
diamond storage coll. →  hunt-diamond-proxy  →  hunt-aa-modular (module = facet)
```

## The one grep that finds most of them (run before opening any skill)

```bash
# "parameter accepted but never validated" seeds every class above
rg -n "function (swap|solve|fill|settle|slash|installModule|diamondCut|permit|deposit|mint)\(" -A 25 \
  | rg -n "external|public"        # write paths = where the auth/validation omission lives
rg -n "mapping\(address => bool\)" -A 1    # allowlist declared -> is it READ in the write path?
rg -n "msg.sender ==|onlyOwner|onlySolver|onlyCommittee|require\(msg.sender" -B 1 -A 1
```

## Two rules that span every class

1. **The kill test goes first.** Every class has a cheap discriminator (single-party vault,
   "price read by nothing", "owner is timelocked multisig", "allowlist declared but never read")
   that kills the claim before a long PoC. A `cast call` showing a missing guard is a *hypothesis*;
   the finding needs the mutation to succeed on a fork and move value.
2. **Attacker P&L must be positive after gas, and a victim must be named.** "Can manipulate X"
   without a harmed counterparty (LP / taker / delegator / holder / user / protocol) and a number
   (`X ETH`, `Y% NAV`, `Z wei share`) is a hardening note, not a finding.

## Where the labs live

Each hunt skill's `## Lab calibration` section points at `D:/isplab/web3-lab/` with a
`test/<Class>Calibration.t.sol` (vault → `VaultInflationCalibration`, oracle →
`OracleL2Calibration`, permit → `Permit2Calibration`, AMM → `AmmHooksCalibration`, AA →
`AAModularCalibration`, diamond/restaking/intent → `RestakingIntentDiamondCalibration`). Run the
matching `--match-contract` probe suite to calibrate your own harness BEFORE trusting a negative: