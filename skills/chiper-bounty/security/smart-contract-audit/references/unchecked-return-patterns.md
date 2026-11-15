# Unchecked Return Value Patterns — Exploitation Guide

## Attacker Philosophy
When a contract calls an external function and ignores the return value, the call might silently fail. This = fund loss, state corruption, phantom operations.

## Vulnerable Pattern
```solidity
// VULNERABLE — return value ignored
pool.withdraw(asset, amount, recipient);
// If this fails, funds are LOST

// VULNERABLE — approve ignored
token.approve(spender, amount);
// If this fails, next transfer fails silently

// VULNERABLE — transfer ignored
token.transfer(to, amount);
// If this fails (fee-on-transfer, blacklisted), funds stuck
```

## Safe Pattern
```solidity
// SAFE — check return value
(bool success, ) = pool.withdraw(asset, amount, recipient);
require(success, "Withdraw failed");

// SAFE — SafeERC20 from OZ
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
SafeERC20.safeTransfer(token, to, amount);

// SAFE — IERC20 with check
bool success = token.transfer(to, amount);
require(success, "Transfer failed");
```

## Exploitation Scenarios

### 1. Phantom Withdrawal
```solidity
// Attacker calls withdraw on pool that returns false on failure
// Contract ignores return value, marks withdrawal as "completed"
// Attacker never receives funds, but balance is deducted
function withdraw(uint256 amount) external {
    pool.withdraw(asset, amount, msg.sender); // Return value ignored!
    balance[msg.sender] -= amount; // Balance deducted even if withdraw failed
}
```

### 2. Fee-on-Transfer Exploit
```solidity
// Token takes 1% fee on transfer
// Contract expects exact amount, ignores transfer return
token.transfer(recipient, 100); // Returns true, but only 99 received
// Contract thinks 100 was sent, accounting mismatch
```

### 3. Blacklisted Address Bypass
```solidity
// Some tokens (USDT) have blacklist
// Contract tries to transfer to blacklisted address
// Transfer returns false, contract ignores it
token.transfer(blacklistedAddress, amount); // Silent failure
// Contract thinks transfer succeeded
```

## Detection Checklist
```
□ Grep for external calls without require/if:
  - .withdraw(
  - .transfer(
  - .transferFrom(
  - .approve(
  - .safeTransfer(
  - .safeTransferFrom(
  
□ For each unchecked call, ask:
  - Does the callee REVERT on failure? (If yes → informational)
  - Does the callee RETURN FALSE on failure? (If yes → exploitable)
  - Can the caller detect the failure? (If no → exploitable)

□ Common false positives:
  - Aave V3 pool calls revert on failure → unchecked is OK
  - OpenZeppelin ERC20 reverts on failure → unchecked is OK
  - Custom ERC20 that returns false → exploitable
```

## Severity
| Pattern | Severity |
|---------|----------|
| Unchecked withdrawal (returns false) | HIGH — fund loss |
| Unchecked transfer (fee-on-transfer token) | MEDIUM — accounting mismatch |
| Unchecked approve (returns false) | MEDIUM — broken functionality |
| Unchecked call to reverting function | INFO — defense in depth |

## Foundry Test
```solidity
function test_uncheckedReturnValue() public {
    // Deploy mock that returns false on failure
    MockPool pool = new MockPool();
    pool.setShouldFailWithdraw(true);
    
    // Call withdraw without checking return
    // In real code, this would silently fail
    // Test should demonstrate: balance deducted but funds not received
    
    uint256 before = token.balanceOf(address(pool));
    pool.withdraw(asset, 100, address(this));
    uint256 after = token.balanceOf(address(pool));
    
    // If return value unchecked: after == before (funds stuck)
    // If return value checked: revert "Withdraw failed"
}
```
