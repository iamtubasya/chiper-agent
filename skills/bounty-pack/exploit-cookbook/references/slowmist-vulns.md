# SlowMist — Cryptocurrency Security Audit Guide
> Source: github.com/slowmist/Cryptocurrency-Security-Audit-Guide (268★)

## Common Vulnerability Categories

### Smart Contract Vulnerabilities
1. Reentrancy
2. Integer Overflow/Underflow
3. Delegatecall Injection
4. Access Control Issues
5. Logic Errors
6. Denial of Service
7. Flash Loan Attacks
8. Oracle Manipulation
9. Front-running
10. Timestamp Dependence

### Blockchain Protocol Vulnerabilities
1. Consensus Algorithm Flaws
2. P2P Network Attacks
3. Eclipse Attacks
4. Sybil Attacks
5. Long-range Attacks
6. Nothing-at-Stake

### Wallet Vulnerabilities
1. Private Key Exposure
2. Seed Phrase Security
3. Multisig Configuration
4. Hardware Wallet Attacks
5. Phishing Attacks

### Exchange Vulnerabilities
1. Hot Wallet Security
2. API Key Management
3. Deposit/Withdrawal Logic
4. KYC/AML Bypass

## Audit Checklist
```
□ Static analysis (Slither, Aderyn, Mythril)
□ Formal verification (Halmos, Certora)
□ Manual code review
□ Economic model analysis
□ Gas optimization review
□ Upgrade path verification
□ Event emission checks
□ External dependency audit
□ Integration testing
□ Stress testing
```

## Severity Classification (SlowMist)
- **Critical:** Direct fund loss, protocol insolvency
- **High:** Significant fund loss risk, privilege escalation
- **Medium:** Limited fund loss, DoS, information leakage
- **Low:** Code quality, best practice violations
- **Informational:** Optimizations, style issues

## Pipeline
- Phase 0C: Load this checklist for web3 testing
- Phase 0C: Cross-reference with target's codebase
- Phase 0F: Use severity classification in report
