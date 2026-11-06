# Web3 Vulnerability Patterns — Comprehensive Reference

**Source:** Immunefi Web3-Security-Library + Top Bounty Writeups

---

## 1. Uninitialized Proxy ($10M+ Bounties)

### Pattern
- Implementation contract not initialized after deploy
- Attacker calls `initialize()` → becomes owner
- Can selfdestruct implementation or hijack proxy

### Real Cases
- **Wormhole** ($10M) — Executor uninitialized
- **88mph** ($3M) — Pool contract uninitialized
- **Teller** ($1M) — Queue contract uninitialized
- **Belt** — Vault uninitialized

### Detection
```bash
# Find proxy contracts
grep -r "delegatecall" contracts/
grep -r "implementation" contracts/
# Check if initialize() exists and was called
```

### Fix
```solidity
// OpenZeppelin Initializable
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";

contract Implementation is Initializable {
    function initialize() public initializer {
        _disableInitializers();
        owner = msg.sender;
    }
}
```

---

## 2. Reentrancy

### Pattern
- External call before state update
- Attacker re-enters function before balance updated

### Example
```solidity
// VULNERABLE
function withdraw() public {
    uint balance = balances[msg.sender];
    (bool success, ) = msg.sender.call{value: balance}("");
    balances[msg.sender] = 0; // State updated AFTER external call
}

// SAFE — Check-Effects-Interactions
function withdraw() public {
    uint balance = balances[msg.sender];
    balances[msg.sender] = 0; // State updated BEFORE external call
    (bool success, ) = msg.sender.call{value: balance}("");
}
```

### Detection
- Look for `call{value:}()` before state updates
- Check for non-reentrant guard (`nonReentrant` modifier)

---

## 3. Flashloan Attacks

### Pattern
- Borrow massive funds in single tx
- Manipulate price/oracle
- Exploit vulnerability
- Repay loan + profit

### Common Targets
- Price oracle manipulation
- AMM reserve manipulation
- Governance voting with borrowed tokens
- Liquidation manipulation

### Example
```solidity
function testFlashloanAttack() public {
    // 1. Flashloan 1000 ETH from Aave
    aavePool.flashLoan(address(this), 1000 ether, "", "");

    // 2. Manipulate price on DEX
    // 3. Exploit vulnerability
    // 4. Repay flashloan
}

function executeOperation(uint amount, ...) external {
    // Attack logic here
    // Repay Aave
    IERC20(TOKEN).approve(address(aavePool), amount + fee);
}
```

---

## 4. Oracle Manipulation

### Pattern
- Single-source oracle vulnerable
- Price feed manipulated via flash loan or MEV
- TWA oracle can be manipulated over multiple blocks

### Detection
```solidity
// Check for single oracle source
oracle.getLatestPrice(); // Single call = vulnerable
// Should use multiple oracles + TWAP
```

### Common Vectors
- Spot price vs TWAP
- Single DEX pair for pricing
- Stale price feed (no heartbeat check)
- Manipulated block.timestamp

---

## 5. Access Control

### Pattern
- Unprotected critical functions
- Broken signature validation
- tx.origin phishing
- msg.value reuse

### Detection
```bash
# Find unprotected functions
grep -r "function.*public" contracts/
# Check for onlyOwner modifier
grep -r "onlyOwner\|require.*msg.sender" contracts/
```

### Example
```solidity
// VULNERABLE — no access control
function withdrawAll() public {
    payable(owner).transfer(address(this).balance);
}

// SAFE
function withdrawAll() public onlyOwner {
    payable(owner).transfer(address(this).balance);
}
```

---

## 6. Integer Overflow/Underflow

### Pattern
- Pre-Solidity 0.8.0: arithmetic overflow/underflow
- Post-0.8.0: auto-reverts (safe by default)
- But: unchecked blocks can still overflow

### Detection
```solidity
// Check compiler version
pragma solidity ^0.7.0; // VULNERABLE (pre-0.8)
pragma solidity ^0.8.0; // SAFE (auto-reverts)

// Check unchecked blocks
unchecked {
    uint x = a - b; // Can underflow!
}
```

---

## 7. Delegatecall Injection

### Pattern
- delegatecall runs code in calling contract's context
- Attacker manipulates storage layout
- Can overwrite critical storage slots

### Example
```solidity
// VULNERABLE — delegatecall to user-controlled address
function execute(address _target, bytes memory _data) public {
    (bool success, ) = _target.delegatecall(_data); // DANGEROUS
}

// Attacker calls execute(attackerContract, data)
// Attacker's code runs in THIS contract's context
```

---

## 8. Bridge Vulnerabilities

### Pattern
- Cross-chain message spoofing
- Missing validation on destination
- Relayer compromise
- Replay attacks across chains

### Real Cases
- **Wormhole** ($10M) — Validator set manipulation
- **Aurora** ($6M) — Infinite spend
- **Optimism** ($2M) — Infinite money duplication
- **Scroll** ($1M) — Message spoofing

---

## 9. Bad Randomness

### Pattern
- Using block variables for randomness
- `block.difficulty`, `blockhash(block.number-1)`, `block.timestamp`
- Predictable by miners/validators

### Fix
- Use Chainlink VRF for verifiable randomness
- Never use block variables for security-critical decisions

---

## 10. MEV (Miner Extractable Value)

### Pattern
- Transaction reordering
- Front-running
- Sandwich attacks

### Detection
- Check if transactions can be front-run
- Check for slippage protection
- Check for private mempool usage

---

## 11. Fee-on-Transfer Tokens

### Pattern
- ERC20 tokens with transfer fees
- Contract assumes full amount received
- Balance calculations wrong

### Example
```solidity
// VULNERABLE — doesn't account for fee
function deposit() public {
    token.transferFrom(msg.sender, address(this), amount);
    balances[msg.sender] += amount; // Wrong! Actual received < amount
}

// SAFE — check actual balance change
function deposit() public {
    uint balBefore = token.balanceOf(address(this));
    token.transferFrom(msg.sender, address(this), amount);
    uint balAfter = token.balanceOf(address(this));
    balances[msg.sender] += (balAfter - balBefore); // Correct
}
```

---

## 12. Logic Errors

### Pattern
- Incorrect business logic
- Wrong formula implementation
- Edge case handling

### Common in
- AMM calculations
- Reward distribution
- Liquidation logic
- Governance proposals

---

## Top Vulnerability Pattern Frequency (from $10M+ bounties)

1. **Uninitialized Proxy** — Wormhole, 88mph, Teller
2. **Logic Error** — Yield Protocol, Silo, Beanstalk
3. **Rounding Error** — DFX Finance, Balancer
4. **Access Control** — Enzyme, Alchemix
5. **Oracle Manipulation** — Enzyme Finance
6. **Flashloan** — Fei, Cream
7. **Library Truncation** — Moonbeam/Astar/Acala
8. **Bridge Vulnerabilities** — Wormhole, Aurora, Optimism, Scroll
