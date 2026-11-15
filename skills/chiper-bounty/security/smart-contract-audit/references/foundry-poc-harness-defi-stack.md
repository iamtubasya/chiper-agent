# Foundry PoC harness for a full governed-DeFi stack

Pattern for standing up a Foundry PoC project around a vendor's hardhat repo when the audit needs
end-to-end tests (deploy → configure → act → assert invariants), not just static analysis. Verified
2026-10-23 on the ACE protocol (hub + 2 vaults + 2 controllers + diamond + oracle + lottery).

Bootstrap mechanics (remappings, vendoring, viaIR) live in
`hardhat-monorepo-to-foundry-bootstrap.md` and `forge-buildinfo-and-deployed-source-verification.md`;
this file is the *harness design* once it compiles.

## 1. Deployment order (governed stack)

1. **Governance hub first** — everything else validates against it (`authorityEpoch() != 0`).
2. **Vaults** — constructor takes the hub; hub lands DEFAULT_ADMIN + CIRCUIT_BREAKER.
3. **Controllers** — constructor takes vault + hub; admin/judgeAdmin = hub.
4. `vm.prank(hub); vault.setBusinessController(controller)` on each vault.
5. **Oracle adapter** (MockPyth + adapter with real price-feed IDs).
6. **Facet** — constructor binds controllers/vaults and computes `bindingsHash`.
7. **Diamond** — cut = facet selectors; `initCalldata = abi.encodeWithSelector(initialize.selector, hub, operator)`
   (diamonds typically pin admin == timelock and check `initCalldata.length == 68`).
8. `vm.prank(hub); controller.setJudge(diamond)` on each controller.
9. Unpause: `vm.prank(hub); hub.unpause(1)` (hubs usually ship paused).
10. **Configure the market on BOTH sides** — the Judge's `configureMarket` AND each controller's
    `configureMarket(marketId, true, capacityBps)` are separate storage. Missing the controller
    one surfaces much later as `InvalidMarket()`/`CapacityStressed()` on the first commit.

⛔ **Governance parties must be contracts.** A hub that models Safes rejects EOAs
(`account.code.length == 0` → `InvalidPartyAddress`). Deploy a `contract DummyParty {}` per party.

⛔ **Both asset vaults need NAV before any round opens.** Round capacity is
`capacityBps × riskBackingAssets`; a zero-NAV vault makes `openMarketRoundCapacity` revert
`CapacityStressed` even if the other side is funded.

## 2. Diamond cut selectors

Compute with `cast sig "<signature>"` and hardcode as `bytes4` constants — enum/struct params need
the exact canonical form (`commitJudgment(bytes32,uint256,uint8,uint8,uint256)`). Include EVERY
function the test (or a downstream reader contract) will call through the diamond — including
public getters like `judgments(uint256)` / `rounds(bytes32,uint256)` if a lottery or integrator
reads them. A missing selector surfaces as `Diamond: selector missing` at call time.

## 3. MockPyth window semantics

`createPriceFeedUpdateData(id, price, conf, expo, emaPrice, emaConf, publishTime, prevPublishTime)`
builds a VAA. `parsePriceFeedUpdatesUnique(data, ids, min, max)` accepts a feed only if
`min <= publishTime <= max` **and** `prevPublishTime < min` (first-update-at-or-after-t). So for a
window `[t, t+2]`: set `publishTime = t`, `prevPublishTime = t - 10`. For round-start prices the
adapter reads the *stored* price (`getPriceNoOlderThan`) — pre-seed via `updatePriceFeeds` and pass
empty update data with 0 value. Confidence must be tiny relative to `maxConfidenceBps`.

## 4. Timing model (round-based protocols)

Rounds are usually 5-min aligned with a ±30s gate: warp to an exact aligned timestamp
(e.g. 300_000) so `_alignedRoundStart` accepts it. lockTime = start+300, settleTime = start+600.
Consecutive rounds need consecutive slots (`roundIdByMarketStartTime` blocks reuse) — warp +300
between starts. **Commit inside each round's entry window** (before its lockTime), not after all
starts. Lock/settle are usually permissionless after their timestamps; settle may be operator-only
for a grace period.

## 5. ⛔ THE PRANK-CONSUMPTION PITFALL (hit 3× in one session)

`vm.prank(x)` / `vm.expectRevert(...)` apply to the **next call** — and a staticcall used as an
*argument* is a call:

```solidity
vm.prank(alice);
vm.expectRevert(DailyBudgetExceeded.selector);
lucky.requestDraw(j, 1, 1, lucky.economicsVersion(), ...);   // BROKEN
```

`economicsVersion()` consumes the prank AND the expectRevert; the real call then runs from the test
contract and the cheatcode reports `next call did not revert as expected`. Same trap with
`vault.claimBusinessPayout(alice, vault.claimableAssets(alice))` (claim reverts
`ClaimableBalanceExceeded` because msg.sender became the test contract).

**Fix — hoist every read above the cheatcode:**

```solidity
uint64 ev = lucky.economicsVersion();
uint256 claimable = vault.claimableAssets(alice);
vm.prank(alice);
vm.expectRevert(...);
lucky.requestDraw(j, 1, 1, ev, ...);
```

## 6. Solidity shapes that bite

- **Public struct-mapping getters return the FULL tuple** (a 48-field struct → 48 components).
  Partial destructuring fails (`Different number of components`); you cannot assign the tuple to a
  struct either. Use full destructure with blanks, or
  `abi.decode(abi.encode(c.getter(k)), (StructName))`.
- **`private` state has no getter** — use the public view (`totalAssets()`, not `activeAssets()`).
- **Base vaults often disable share transfers** (`transfer` reverts `ShareTransferDisabled`) — the
  harness itself must be the LP (deposit/redeem to `address(this)`), there is no moving shares to a
  puppet address.
- Enums need explicit values at call sites: `Contract.EnumName.Value` (no implicit int_const).

## 7. Invariants worth asserting every time

- Custody covers accounting: `active + escrow + claimable + unallocated <= custodiedAssets()`
- Reserve solvency: `reservedBusinessPayout <= activeAssets + businessEscrowAssets`
- Post-settlement drainage: escrow / reserved / open-round-count / unallocated all return to 0
- Rolling risk windows fully decay after window+1 (catches bucket double-subtract on wrap)
- Global conservation across a multi-round stress (win / tie / refund, both assets)
