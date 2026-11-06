# Crypto Exploit Knowledge Bases — Quick Reference
> Aggregated from: Web3Bugs (1822★), slowmist (268★), solsec (891★), web3-security-resources (467★)

## When Loading
Load this during Phase 0A (startup) or Phase 0C (testing) for comprehensive exploit pattern reference.

## Repos Index

### Web3Bugs (ZhangZhuoSJTU)
- 720+ real-world smart contract bugs
- Organized by vulnerability class
- Each bug has: description, PoC, fix recommendation
- **Use for:** Comprehensive vulnerability checklist during audit

### SlowMist Crypto Security Guide
- Audit methodology + vulnerability taxonomy
- Severity classification system
- Exchange, wallet, smart contract categories
- **Use for:** Structured audit approach, report severity levels

### Solana Security (solsec)
- Anchor/Solana-specific vulnerability patterns
- Account validation checklist
- Common Rust/Solana mistakes
- **Use for:** Solana-based project audits

### Web3 Security Resources (Raiders0786)
- Learning paths for Web3 auditors
- Tool recommendations per vulnerability type
- Community write-ups and CTF challenges
- **Use for:** Tool selection guidance, methodology reference

## Quick Lookup by Category
| Vuln Class | Web3Bugs | SlowMist | solsec | Severity |
|------------|----------|----------|--------|----------|
| Reentrancy | ✅ #1 | ✅ #1 | N/A | Critical |
| Access Control | ✅ #2 | ✅ #4 | ✅ | Critical |
| Oracle Manipulation | ✅ #3 | ✅ #8 | N/A | Critical |
| Flash Loan | ✅ #4 | ✅ #7 | N/A | High |
| Integer Overflow | ✅ #5 | ✅ #2 | ✅ | High |
| Delegatecall | ✅ #6 | ✅ #3 | N/A | Critical |
| Selfdestruct | ✅ #7 | ✅ | N/A | High |
| tx.origin | ✅ #8 | ✅ | N/A | Medium |
| Storage Collision | ✅ #11 | N/A | ✅ | High |
| Account Sub | N/A | N/A | ✅ #1 | Critical |
| PDA Bump | N/A | N/A | ✅ #3 | High |

## Pipeline
- Phase 0A: Load for startup knowledge
- Phase 0C: Load per vulnerability class being tested
- Phase 0F: Reference for severity classification in report
