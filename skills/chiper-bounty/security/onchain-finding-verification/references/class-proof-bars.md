# Web3 Class Proof Bars — what each class must prove before it is a finding

> Companion to the Parent "Minimum 5 probes" table. Probes tell you what to test; this file
> tells you what the *result* has to show before it may be written up. Derived from the
> 2026-10-27 calibration lab (`D:/isplab/web3-lab`, 8 suites / 48 tests green) where every
> probe was run against a deliberately-vulnerable contract and the claimed framing was
> checked against measured numbers.
>
> Read the row for your class, then check the two universal traps at the end.

## Why the web2 proof bar does not transfer

| | web2 | web3 |
|---|---|---|
| Minimum proof | a request + response pair | a `forge test` that runs and asserts |
| Severity currency | data / account reach | funds **moved, locked, or lost** |
| Priors that kill a finding | "by design", "out of scope" | "no path to loss of funds", "on-chain discoverable" |

**Two vendor phrases close almost every web3 report** — pre-empt them in the report instead of
discovering them after submission:

1. *"No path to the locking, loss, or theft of funds."* An API authz bug, an info leak, or a
   centralization observation on a fund-scoped program gets this even when the scope text
   admits the surface. If the finding does not move funds, it is recon for an economic chain.
2. *"On-chain discoverable = not confidential."* Kills raw chain-data exposure claims.

---

## Vault inflation / share price (ERC-4626, LRT, staking receipt)

**Must prove:** attacker P&L **and** victim loss, both computed.

```solidity
assertEq(vault.balanceOf(victim), 0);          // victim got nothing
emit log_named_uint("attacker net gain", net); // after subtracting the donation
```

- **Measured (lab):** donation 1000e18 → attacker nets **500e18 (50%)**, victim loses
  **100% of the deposit**. "Attacker steals 1000" is refutable — the triager points at the
  attacker's own capital outlay. Write *victim loss*.
- **Kill test first:** single-party pool (`public(address) lender`, both `deposit` and
  `withdraw` gated to it) → the write-off lands on the person who triggers it. Not a finding.
- **`require(shares > 0)`** in the target kills the inflation path but leaves the rounding
  leak alive (dust deposit returns 0 shares and takes the assets). Two bugs, two severities.
- **Economics gate:** `claim − (initial + injected + gas)`. Net ~0 = hardening note.
- **Duplication:** same root cause fixed in git history / CHANGELOG / an audit PDF in the PR →
  sibling path is a known issue, out of scope.

## Modular / smart account (ERC-7579, ERC-4337, EIP-7702)

**Must prove:** a module you control installed, and the delegatecall landing in the account's
storage — or the drain.

- **Measured (lab):** **any** module whose first state variable sits in slot 0 clobbers
  `owner`. No purpose-built payload needed. The value written is `address(this)`, which
  inside `delegatecall` **is the account** — so `owner` becomes the account itself and the
  original owner is evicted. Stronger than "the module becomes owner".
- **Do not claim** "nonce incremented after the external call = replay". A naive reentrant
  `execute()` **fails**: the re-entrant `msg.sender` is the callee, not the owner. The
  ordering defect is real and measurable (nonce still old *inside* the call), but exploitation
  needs a second path carrying the same `msg.sender` — entryPoint-batched executes, or a
  multicall that delegatecalls back. State that path or drop the replay claim.
- **By design:** module restricted to `call` (not `delegatecall`) with approvals scoped;
  registry allowlist + timelock.

## Signed approvals (Permit2, ERC-3009, EIP-712)

**Must prove:** the same signature accepted twice, or accepted on a second deployment / fork,
with the resulting balance shown.

- **Cheapest decisive probe:** deploy the contract twice and compare `digestOf(struct)`.
  Identical digest = no `verifyingContract` bound = replay across deployments. No crypto
  assumptions left to argue about.
- **Separate the two bugs:** allowance **not decremented** (double spend) and nonce **not
  consumed** (authorisation replay) are different defects with different fixes. Name the one
  you proved.
- **Witness not binding:** sign `witness = keccak256("order-123-to-Bob")`, submit with
  `keccak256("order-999-to-Attacker")`. If accepted, the witness is decorative.
- **By design:** reference Permit2 nonce scoping; `sigDeadline` + nonce invalidation both present.

## AMM / pool (Uniswap v4 hooks, Balancer v3, singleton)

**Must prove:** the manipulated state read back after the operation, and the loss it implies.

- **Measured (lab):** fee 3000 → 500000 (0.3% → 50%) inside a single swap.
- **Overclaim trap that kills real findings:** raising the fee on the **wrong pool**.
  `keccak256(abi.encode(poolKey))` differs when the `hooks` field differs — the mutation lands
  elsewhere, reads as "no effect", and the finding dies. Pass the hook its own key.
- **Architecture claim:** cross-pool reentrancy exists because one contract holds every pool.
  It does not exist in v2/v3 per-pool design. Say which architecture the target runs.
- **By design:** JIT liquidity in a pool built for it; hook allowlist enforced at `initialize`.

## Restaking / LRT

**Must prove:** the slash executed (stake delta), or the withdrawal completed before the delay,
or the post-slash redemption at the stale rate — with both numbers.

- **Measured (lab):** pool 7000e18 slashed to 6000e18 while `rateSnapshot` stayed 1e18 →
  1000 shares paid 1000e18 when fair value was 3000e18. The **difference** is the loss.
- **Unrestricted slash is the most direct Critical:** a stranger with no role dropping an
  honest operator's stake 1000 → 500 with no proof, committee, or challenge window.
- **By design:** committee-gated slash + challenge window + a delay that cannot be reset.

## Intent / solver / attestor settlement

**Must prove:** an unapproved solver settling, an attestation credited twice, or the delivered
amount below the signed `minOut`.

- **Grep first — declared but never read.** In the lab all four bugs shared one shape:
  `mapping(address => bool) solvers` existed and was never consulted in `solve()`. A
  **declared-but-unused** allowlist is more common than a missing one. Grep the declaration,
  then grep its use on the write path.
- **By design:** solver allowlist + bond/slash; attestation bound to chainId + nonce +
  recipient with an m-of-n threshold.
- **Honesty rule:** a chain that ends at "the server validates it" is UNPROVEN — not a finding
  and not a verified negative. Name the single unproven hop and which credential would settle it.

## Oracle / L2 / sequencer

**Must prove:** a privileged action (borrow / liquidate / mint / settle) executing against the
bad price, with the resulting position or balance. Without this it is a hardening note.

- **Measured (lab) — the differential is the proof:** two functions in the same contract.
  `borrow()` (no uptime check) succeeds while the sequencer is DOWN; `borrowSafe()` reverts.
- **Silent-false-pass trap:** a feed mock (or integration) whose return shape is simpler than
  reality. A 2-tuple uptime mock makes `startedAt` read 0, so `block.timestamp - 0` always
  exceeds the grace period and the check "passes" falsely. Chainlink's uptime feed is a
  **5-tuple**. Verify the interface before concluding a consumer is safe.
- **Negative price survives arithmetically-safe code:** `answer = 0` happens to zero out
  `maxBorrow`, looking safe — but `answer = -1` cast to `uint256` underflows. The consumer was
  never checking `answer > 0`; it survived by coincidence.
- **By design:** `getPriceUnsafe` on a display-only path; heartbeat + `updatedAt` checked.

## Upgradeability / diamond / proxy

**Must prove:** the effect read back — the selector now pointing at your facet, or the
colliding slot showing your value.

- **Measured (lab):** write `FacetA.setTotalA(111)`, then read `FacetB.getFeeB()` → **111**.
  Two facets declaring their first state variable at slot 0. Theory without a number is not proof.
- **Harness trap that fakes a negative:** to call facet functions through the diamond, **every**
  selector you use must be cut — setter **and** getter. Cut only `setFeeB` and `getFeeB()` falls
  to the fallback without a facet, returning garbage that looks like "no collision".
- **`initialize()` replay:** no `initializer` modifier and no `_disableInitializers()` → owner
  taken over repeatedly by successive callers.
- **"Owner can upgrade"** is a centralization note unless you show what the replacement facet
  *does*. Most programs reject admin-malice assumptions.

---

## The universal overclaim traps

| Trap | Why it fails |
|---|---|
| Severity without a `forge test` | Immunefi auto-rejects PoC-less submissions; a multi-step "first deploy this, then call that" PoC gets downgraded |
| "Attacker steals X" when they spent Y | state victim loss, not attacker gain |
| Raw aggregate statistic without a control | 71% of settlements going DOWN in a falling market is the market, not bias |
| A technique / pattern match presented as a finding | it is a lead; it must pass this skill's fork-PoC gate |
| Analyzer output as evidence | every slither/aderyn hit needs a named disposition (real, or the FP reason) or it does not count |
| A blocked chain reported as High | a chain dying at step 2 is informational — say plainly where it dies |
| A number read off a stale scenario | after seeding a pool / changing state, recompute expected values; do not carry forward pre-seed arithmetic |

## Severity

Use **Immunefi VSS v2.3 by domain** (Smart Contracts / Blockchain-DLT / Websites-and-Apps),
**not CVSS**. Two boundaries decide the level:

- **principal vs unclaimed yield** — Critical vs High
- **temporary vs permanent freeze**

Read the program's own severity table before writing the word Critical.
