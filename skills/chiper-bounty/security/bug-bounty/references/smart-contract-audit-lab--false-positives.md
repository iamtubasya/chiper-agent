# False Positive Patterns — Smart Contract Audit

## By-Design Patterns (Reject Immediately)

### HTLC Secret in Events
```solidity
event Redeemed(bytes32 indexed orderID, bytes32 indexed secretHash, bytes secret);
```
**Why invalid:** HTLCs MUST reveal secret for atomic swaps. Every HTLC implementation does this. The secret is also in calldata, not just events.

### Cleanup Mechanism Exists
```solidity
function refund(bytes32 stakeID) external {
    require(stake.expiry < block.number, "Not expired");
    fillers[stake.filler].delegateStakeIDs.remove(stakeID);
    SEED.safeTransfer(stake.owner, stake.stake);  // Users get tokens back
}
```
**Why invalid:** Users economically incentivized to call cleanup (get tokens back). DoS only works if users sacrifice own tokens (irrational).

### Access Control (Admin Functions)
```solidity
function setFee(uint256 fee) external onlyOwner { ... }
```
**Why invalid:** Only owner can call. By design — owner is trusted.

## Mitigated Patterns (Reject After Verification)

### Reentrancy Mitigated by Atomicity
```solidity
function closeChannel(uint256 amount_) internal {
    token.safeTransfer(recipient, amount_);  // Hook fires here
    // But: factory.closed(recipient) prevents double-close
    // And: Solidity atomicity reverts inner call
}
```
**Why invalid:** Even if reentrancy occurs, inner call reverts. No fund loss.

### Signature Mismatch Requiring Off-Chain Bug
```solidity
bytes32 claimID = claimHash(amount_, nonce_, htlcs);  // Original amount
if (nonce == nonce_ && expiration != 0) {
    amount_ = amount;  // Override
}
// Signatures verified against claimID (original amount)
```
**Why invalid:** Requires off-chain system to send stale data. Not directly exploitable.

### Gas DoS with Economic Cleanup
```solidity
function getVotes(address filler) external view returns (uint256) {
    for (uint256 i = 0; i < delegateLength; i++) {
        // Iterates ALL stakes including expired
    }
}
```
**Why invalid:** Users incentivized to call refund() to get tokens back. No rational user lets tokens expire without cleanup.

## Unrealistic Exploitation Patterns (Reject After Analysis)

### Requires Flash Loan + Specific Conditions
Flash loans are atomic — attacker must profit in same transaction. If profit requires specific market conditions (not guaranteed), unrealistic.

### Requires Collusion Between Parties
Social engineering, not technical vulnerability. Bug bounty programs don't cover social engineering.

### Requires Compromised Off-Chain System
Not directly exploitable. If attacker already has off-chain access, they have bigger problems to solve.

### Requires Irrational Behavior
Attacker must lose money to execute attack. No rational attacker would do this.

## Slither False Positives on Proxy/Upgradeable Contracts

**These appear on EVERY proxy-based contract (EIP-1967, OpenZeppelin Transparent/UUPS). If >50% of Slither output is these, the scan is dominated by proxy noise.**

### uninitialized-state (MOST COMMON — often 100+ hits)
```solidity
contract MyToken is Initializable, ERC20Upgradeable {
    uint256 public totalRewards;
    function initialize(uint256 _initial) public initializer {
        totalRewards = _initial;  // Slither doesn't track initialize()
    }
}
```
**Why false:** Proxy storage is initialized via `initialize()`, not constructor. Slither's state initialization analysis doesn't follow the proxy pattern. This is standard EIP-1967 behavior.

### external-function
**Why false:** Proxy admin routing makes "unprotected" external calls actually admin-only through the TransparentUpgradeableProxy's fallback. The function is externally callable but only reachable through the proxy's admin path.

### constable-states
**Why false:** Implementation contract states are actually proxy storage slots — immutable in practice. The "mutable" states are proxy-scoped.

### arbitrary-send-eth on TimelockController
```solidity
// OZ TimelockController.executeBatch() sends ETH to recipients
// Slither flags this as "arbitrary send"
```
**Why false:** TimelockController's `executeBatch` is designed to send ETH. The "arbitrary" recipient is approved through the timelock's scheduling mechanism.

### incorrect-exp on OpenZeppelin Math.sol
```solidity
// XOR swap pattern in Math.sol for gas-efficient value exchange
// Slither misinterprets XOR (^) as exponentiation
```
**Why false:** XOR is used intentionally for gas-efficient swap, not exponentiation. Slither's operator analysis produces false positives here.
