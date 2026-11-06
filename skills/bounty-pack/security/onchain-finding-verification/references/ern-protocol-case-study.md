# Ern Protocol — RewardsDistributor Case Study

## Summary
Code vulnerability confirmed (HIGH severity in isolation) but ZERO on-chain impact.
Contract is dormant: zero balance, zero transactions, zero activity since deployment.

## Contract
- Address: 0x9F76037494092aCeAc5B23E21C20B1970a866eF5
- Source: github.com/ernorg/ern-app/blob/main/apps/platform/contracts/v1/src/RewardsDistributor.sol
- Lines: 185

## Vulnerability (in code)
ALLOCATOR_ROLE can call reduceAllocations() to zero out any user allocation,
then emergencyWithdraw() to drain all tokens. No timelock, no multisig, no cap.

## On-chain reality (verified 2026-09-15)
- ETH balance: 0
- USDC balance: 0
- USDT balance: 0
- DAI balance: 0
- WETH balance: 0
- Transaction count: 0
- Log events: 0
- Contract paused: false

## What to learn
1. Code vulnerability + dormant contract = INFORMATIONAL, not HIGH
2. Always check on-chain state BEFORE claiming severity
3. What COULD happen is not the same as what IS happening
4. Programs reject inflated findings — honest severity = faster payout
5. Source code audit found 7 vulnerabilities, 44/44 tests pass — all irrelevant if contract holds nothing

## Report classification
Severity: INFORMATIONAL (or LOW maximum)
Title: "RewardsDistributor has architectural trust model risks but is currently dormant"
Note: "Risk materializes if/when contract receives deposits"
