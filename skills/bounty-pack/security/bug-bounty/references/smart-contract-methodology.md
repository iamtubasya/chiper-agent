# Smart Contract Methodology — Attack-First Approach

## Attacker Philosophy
Smart contract = public code. Attacker reads same code as developer. Find bugs developer missed.

## Attack Surface
```
1. PUBLIC FUNCTIONS — any function without access control = attack vector
2. EXTERNAL CALLS — reentrancy, unchecked return values
3. STATE MUTATIONS — state changes after external calls = vulnerable
4. TOKEN INTERACTIONS — fee-on-transfer, rebasing, blacklists
5. PRICE FEEDS — oracle manipulation, stale prices
6. PROXY PATTERNS — upgradeable = admin can change logic
7. SIGNATURES — replay, malleability, missing nonce
```

## Static Analysis (Automated)
```bash
slither . --detect reentrancy-eth,reentrancy-no-eth,unchecked-transfer
aderyn .
myth analyze contracts/ --execution-timeout 90
```

## Manual Review Checklist
```
□ Reentrancy (external call before state update)
□ Access control (谁能调用这个函数?)
□ Integer overflow (pre-0.8.0?)
□ Flash loan (价格操纵?)
□ Oracle (单一数据源?)
□ Proxy (可升级 = admin后门?)
□ Signature (重放攻击?)
□ Fee-on-transfer (余额计算错误?)
□ Rounding (精度损失?)
□ Time dependence (时间戳操纵?)
```

## PoC Development
```solidity
// For EACH finding, write a Foundry test
function test_exploit() public {
    // 1. Deploy contracts
    // 2. Setup victims
    // 3. Execute attack
    // 4. Assert: attacker profit > 0
    // 5. Assert: victim balance = 0
}
```

## Severity
```
CRITICAL: Direct fund theft, complete takeover
HIGH: Significant fund loss, major state corruption
MEDIUM: Limited fund loss, conditional state corruption
LOW: Minor issues, code quality
INFO: Best practice violations
```
