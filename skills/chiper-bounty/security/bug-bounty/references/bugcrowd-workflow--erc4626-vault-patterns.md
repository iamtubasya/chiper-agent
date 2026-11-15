# ERC4626 Vault — Vulnerability Patterns

## Overview
ERC4626 is a tokenized vault standard. Each deposit mints shares, each withdrawal burns shares. The share:asset ratio is the attack surface.

## Critical Pattern: Inflation Attack (First-Depositor)
**Severity:** CRITICAL
**Impact:** Steal all subsequent deposits

### Attack Flow
1. Attacker deposits tiny amount (e.g., 1 wei) → gets 1 share
2. Attacker donates large amount directly to vault (not through deposit) → share price inflates
3. Victim deposits → due to rounding, gets 0 shares
4. Attacker withdraws → receives victim's entire deposit

### Why It Works
```solidity
shares = (assets * totalSupply) / totalAssets;
// If totalAssets is huge and totalSupply is small,
// shares rounds down to 0 for small deposits
```

### Detection Checklist
- [ ] Does vault have virtual shares offset? (e.g., `totalSupply + 1e3` or `1e6`)
- [ ] Does vault have virtual assets offset?
- [ ] Is there a minimum deposit amount?
- [ ] Is there a minimum lock period?
- [ ] Does deposit round DOWN (favor protocol)?
- [ ] Does withdraw round UP (favor protocol)?

### Known Mitigations
1. **Virtual offset:** Add 1e3+ to totalSupply and totalAssets in share calculation
2. **Minimum deposit:** Reject deposits below threshold
3. **First-depositor protection:** Don't allow tiny initial deposits
4. **Round in protocol's favor:** `shares = (assets * supply) / assets + 1` (round up on mint)

## Pattern: Share Price Manipulation via Donation
**Severity:** HIGH
**Impact:** Inflate share price to grief or extract value

### Attack Flow
1. Attacker donates tokens to vault (bypassing deposit)
2. Share price increases
3. Next depositor gets fewer shares than expected
4. Attacker can profit by withdrawing at inflated price

### Detection
- [ ] Is there a time-weighted average price mechanism?
- [ ] Can donations bypass the deposit function?
- [ ] Is the share price calculated per-block or cumulative?

## Pattern: Fee-on-Transfer Token Incompatibility
**Severity:** MEDIUM-HIGH
**Impact:** Accounting mismatch, potential fund loss

### Detection
- [ ] Does vault handle fee-on-transfer tokens?
- [ ] Is `actualAmount = amount - fee` used instead of `amount`?
- [ ] Does deposit/withdraw use the correct received amount?

## Pattern: ERC4626 + Aave/Venus Wrapper Issues
**Severity:** HIGH
**Impact:** Underlying protocol interaction bugs

### Detection
- [ ] Does the wrapper correctly handle underlying token transfers?
- [ ] Is the exchange rate calculated correctly?
- [ ] Can the wrapper be manipulated via flash loans to underlying?
- [ ] Does the wrapper handle underlying protocol upgrades?

## Vulnerable Code Patterns
```solidity
// VULNERABLE: No virtual offset
function _convertToShares(uint256 assets) internal view returns (uint256) {
    return assets * totalSupply / totalAssets();
}

// SAFE: With virtual offset
function _convertToShares(uint256 assets) internal view returns (uint256) {
    return assets * (totalSupply + 1e3) / (totalAssets() + 1e3);
}

// VULNERABLE: Rounding favors attacker
shares = assets * supply / assets; // rounds down = fewer shares for depositor

// SAFE: Rounding favors protocol
shares = (assets * supply + assets - 1) / assets; // rounds up
```
