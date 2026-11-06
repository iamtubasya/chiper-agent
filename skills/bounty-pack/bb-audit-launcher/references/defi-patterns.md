# DeFi & Web3 Patterns — Curated from 18 Repos
> Smart contract vulnerabilities, DeFi exploit patterns, audit checklists.

## Vulnerability Catalog

### Critical (P1-P2)
1. **Reentrancy** — state change after external call
   ```solidity
   // BAD: external call before state update
   (bool success, ) = recipient.call{value: amount}("");
   balances[recipient] -= amount;
   
   // GOOD: state update before external call
   balances[recipient] -= amount;
   (bool success, ) = recipient.call{value: amount}("");
   ```

2. **Access Control** — missing onlyOwner/onlyRole
   ```solidity
   // BAD: no access control
   function withdraw() external {
       payable(msg.sender).transfer(address(this).balance);
   }
   
   // GOOD: access control
   function withdraw() external onlyOwner { ... }
   ```

3. **Flashloan Attack** — price oracle manipulation
   - Use TWAP oracles, not spot prices
   - Check block.timestamp manipulation

4. **Integer Overflow/Underflow** — Solidity <0.8
   ```solidity
   // Use SafeMath or Solidity 0.8+
   using SafeMath for uint256;
   ```

5. **Front-running** — MEV sandwich attacks
   - Use commit-reveal schemes
   - Use Flashbots Protect

### High (P3)
6. **Unchecked Return Values** — low-level call without success check
7. **Delegatecall Injection** — user-controlled delegatecall target
8. **Selfdestruct Force** — force ETH into contract
9. **Block Timestamp Manipulation** — miner can adjust ±15 seconds
10. **Denial of Service** — unbounded gas consumption

### Medium (P4)
11. **Oracle Manipulation** — single oracle, no validation
12. **Slippage** — no minimum output check
13. **Governance Attack** — flashloan-based voting
14. **Proxy Upgrade** — unsecured upgrade mechanism
15. **Signature Replay** — no nonce in EIP-712

---

## Audit Checklist (from tamjid0x01/SmartContracts-audit-checklist)

### Pre-Audit
- [ ] Understand business logic
- [ ] Identify external dependencies
- [ ] Check Solidity version
- [ ] Review compiler optimizations

### Code Review
- [ ] Access control on all functions
- [ ] Reentrancy guards (ReentrancyGuard)
- [ ] Integer overflow protection
- [ ] Input validation
- [ ] Return value checks
- [ ] Gas optimization
- [ ] Event emission for state changes
- [ ] Timelock for admin functions
- [ ] Multisig for critical operations

### DeFi-Specific
- [ ] Oracle price validation
- [ ] Flashloan resistance
- [ ] MEV protection
- [ ] Slippage protection
- [ ] Fee calculation accuracy
- [ ] Reward distribution fairness

---

## Security Standard: solcurity
- https://github.com/transmissions11/solcurity
- Opinionated security and code quality standard for Solidity

---

## Tool Commands

### Static Analysis
```bash
slither .                    # Comprehensive static analysis
aderyn .                     # Solidity static analysis (WSL)
mythril analyze Contract.sol # Symbolic execution (WSL)
```

### Fuzzing
```bash
echidna-test . --test-mode assertion  # Property-based fuzzer
medusa test                              # Alternative fuzzer
```

### Formal Verification
```bash
halmos --test-contract TestContract  # Symbolic testing
```

### Bytecode Analysis
```bash
# heimdall-rs (for unverified contracts)
heimdall disassemble $CONTRACT_ADDRESS
heimdall decompile $CONTRACT_ADDRESS
```

---

## Integrated Repos (18)

| Repo | Stars | What We Took |
|------|-------|--------------|
| OpenZeppelin/openzeppelin-contracts | 27.2K | Secure contract library |
| ConsenSysDiligence/smart-contract-best-practices | 7.6K | Best practices guide |
| ConsenSysDiligence/mythril | 4.3K | Symbolic execution tool |
| crytic/echidna | 3.2K | Property-based fuzzer |
| kadenzipfel/smart-contract-vulnerabilities | 2.5K | Vuln catalog |
| crytic/not-so-smart-contracts | 2.2K | Vuln examples |
| transmissions11/solcurity | 2.2K | Security standard |
| Jon-Becker/heimdall-rs | 1.6K | Bytecode analysis |
| sigp/solidity-security-blog | 1.5K | Attack vectors |
| crytic/awesome-ethereum-security | 1.5K | ETH sec index |
| TokenMarketNet/smart-contracts | 1.3K | Token contracts |
| blst-security/cherrybomb | 1.2K | API spec audit |
| nascentxyz/simple-security-toolkit | 1.2K | Audit guides |
| raineorshine/solgraph | 1K | Control flow viz |
| tamjid0x01/SmartContracts-audit-checklist | 798 | Audit checklist |
| nascentxyz/pyrometer | 797 | Parameter analysis |
| saeidshirazi/Awesome-Smart-Contract-Security | 906 | SC sec index |
| immunefi-team/Web3-Security-Library | 2.2K | Web3 sec tutorials |

---

## Cross-References
- Contract audit → `smart-contract-audit` skill
- Onchain verification → `onchain-finding-verification` skill
- Report → `bug-report-delivery` (Phase 0F, ABSOLUTE LAST)
