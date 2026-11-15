# Access Control Modifier Mismatch — Vulnerability Pattern

Discovered: August 28, 2026 in The Graph Protocol (HorizonStaking/SubgraphService)

## Pattern Summary

A contract overrides a virtual function that defines valid parameter ranges, but a different function that ACCEPTS parameter changes uses a weaker access control modifier that SKIPS the range validation.

**Result:** The override is effectively dead code for that particular call path.

## Concrete Example (The Graph)

```solidity
// SubgraphService.sol — override defines range
function _getThawingPeriodRange() internal view override returns (uint64, uint64) {
    uint64 disputePeriod = _disputeManager().getDisputePeriod();
    return (disputePeriod, disputePeriod);  // MIN = MAX = disputePeriod
}

// SubgraphService.sol — accept uses DEFAULT, not VALID_PROVISION
function acceptProvisionPendingParameters(
    address indexer, bytes calldata
) external override enforceService(indexer, DEFAULT) {  // ← DEFAULT!
    _acceptProvisionParameters(indexer);
}

// enforceService only calls _requireValidProvision when VALID_PROVISION is set
function _enforceServiceRequirements(address _serviceProvider, uint256 _checks) private view {
    _requireNotPaused();
    _requireAuthorizedForProvision(_serviceProvider);
    if (_checks & VALID_PROVISION != 0)   // ← NOT SET for DEFAULT
        _requireValidProvision(_serviceProvider);  // ← SKIPPED
}
```

**Impact:** Indexer can set `thawingPeriod = 0`, withdraw all stake before dispute resolves, escape slashing entirely.

## Detection Checklist

When auditing any protocol with parameterized configurations:

1. **Map all parameter setters** — find every function that accepts user-controlled parameter values
2. **Map all access modifiers** — for each setter, what modifier/require is checked?
3. **Map all validation functions** — what range/bounds checks exist? Are they in a virtual function?
4. **Cross-reference:** Does the setter's modifier actually call the validation function?
   - Check modifier flags: if modifier uses `enforceService(addr, DEFAULT)` but validation needs `VALID_PROVISION`, the validation is skipped
   - Check `if (_checks & FLAG != 0)` patterns — these are conditional validations that can be bypassed
5. **Check override chain** — if a child contract overrides a validation function, does the override actually get called in ALL paths, or only some?

## Generic Pattern

```
ParentContract:
  virtual function _getValidRange() → (min, max)
  modifier: enforce(addr, CHECK_A | CHECK_B) → calls _checkValid() only if CHECK_B set

ChildContract:
  override _getValidRange() → tighter range
  BUT: accept() uses enforce(addr, CHECK_A) → CHECK_B not set → _checkValid() skipped
```

## Similar Vulnerable Patterns to Look For

- **Staking/Delegation protocols:** thawing periods, lockup periods, fee cuts
- **Governance:** proposal thresholds, voting periods, quorum requirements
- **AMM/DEX:** slippage limits, fee ranges, pool parameters
- **Lending:** LTV ratios, interest rate models, collateral factors
- **Bridge:** message validation, delay periods, withdrawal limits

## Mitigation Patterns

```solidity
// Option 1: Add validation flag to acceptor function
function acceptParams(...) external enforceService(addr, VALID_PROVISION | DEFAULT) { ... }

// Option 2: Inline validation in acceptor
function acceptParams(...) external {
    uint64 min, max = _getThawingPeriodRange();
    require(newVal >= min && newVal <= max, "Out of range");
}

// Option 3: Validate at storage write time (defense in depth)
function _setParam(uint64 val) internal {
    (uint64 min, uint64 max) = _getValidRange();
    require(val >= min && val <= max, "Out of range");
    param = val;
}
```

## God-Eye Quick Check for This Pattern

When you find an override of a validation/config function, IMMEDIATELY ask:
1. Which functions call the overridden function? (grep for the function name)
2. Which functions SHOULD call it but DON'T? (check access control paths)
3. Is there a conditional flag that gates the call? (check modifier arguments)
