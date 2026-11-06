# Term Structure Labs V2 — Oracle Timelock Bypass Analysis

**Date:** 24 August 2026
**Platform:** Immunefi
**Max Bounty:** $80,000 (Smart Contracts)

## Target
- **Contract:** OracleAggregatorV2
- **ETH Mainnet:** 0x16110F65047a46D39FFEB3dadd61ed33ec9FaBC2
- **ARB Mainnet:** 0xDF020051fc6f3378459bc9269372AA46fEEa77CA
- **Owner (ETH):** 0xDA4aAF85Bb924B53DCc2DFFa9e1A9C2Ef97aCFDF

## Finding: Oracle Parameter Update Timelock Bypass

### Vulnerability
`submitPendingOracle()` lines 128-132:
```solidity
Oracle memory oldOracle = oracles[asset];
if (oldOracle.aggregator == oracle.aggregator && oldOracle.backupAggregator == oracle.backupAggregator) {
    _updateOracle(asset, oracle);  // IMMEDIATE UPDATE -- no timelock!
    return;
}
```

### Impact
1. **Heartbeat=0 bypass:** Owner sets heartbeat=0 -> staleness check disabled -> stale prices accepted
2. **DoS via price bounds:** Owner sets maxPrice < actual price -> `getPrice()` REVERTS -> all protocol ops revert
3. **Timelock defeated:** Critical parameter changes happen instantly without user notification period

### `_checkAnswer` Behavior (Critical)
```solidity
function _checkAnswer(int256 answer, Oracle memory oracle) internal pure returns (bool) {
    if (answer < 0) return false;
    if (oracle.maxPrice != 0 && answer > oracle.maxPrice) return false; // REVERTS!
    if (oracle.minPrice != 0 && answer < oracle.minPrice) return false; // REVERTS!
    return true;
}
```
When returns false, `getPrice()` reverts with `OracleIsNotWorking`. This is DoS, not price clamping.

## Dedup Results

| Report | Scope | Oracle Timelock Bypass? |
|--------|-------|------------------------|
| ABDK Phase1-v2 | V1 Market/Order/Vault/Router | Not in scope |
| ABDK Phase2 | V1 Vault reentrancy | Not in scope |
| ABDK Phase3-v2 | V2 All contracts | CVF-10 FIXED (price clamping, different issue) |
| ABDK TMX-v1.0 | OFT token only | Not in scope |
| Cantina Competition | V1 contracts | Not in scope |

**Result:** Finding is GENUINELY NEW.

## PoC Test Results (4/4 PASS)

```
[PASS] test_TimelockBypass_SameAggregator_ImmediateUpdate
  - heartbeat changed 3600 -> 0 INSTANTLY (no timelock)
  - Stale price accepted after 365 days

[PASS] test_TimelockBypass_DifferentAggregator_TimelockEnforced
  - Different aggregator correctly requires timelock (control test)

[PASS] test_TimelockBypass_MaxPriceDoS
  - getPrice REVERTS when maxPrice=$100 (actual=$2000)
  - DoS: all protocol ops that need price revert

[PASS] test_TimelockBypass_MinPriceDoS
  - getPrice REVERTS when minPrice=$10000 (actual=$2000)
  - DoS: same as maxPrice
```

## Deployment Info
- **Git Commit:** 0x82afc5cf998559008bd5fc339dff30cbdf7d2e1f
- **Deploy Block (ETH):** 24883366
- **Deployer:** 0x56E3665038C5F0b56Cc7D81aC66C86521274B251
- **Admin:** 0x8409a9C1A911CED491892c5694E43994c9d47E8f

## Files
- PoC: `~/AppData/Local/Temp/PoC_Oracle_Timelock_Bypass.t.sol`
- Report: `~/AppData/Local/Temp/termstructure-bounty-final-report.md`
