# Ern Protocol — RewardsDistributor Deep Dive Case Study

## Protocol
- **Contract**: `0x9F76037494092aCeAc5B23E21C20B1970a866eF5`
- **Source**: 185 lines, OZ AccessControlUpgradeable + PausableUpgradeable
- **Roles**: DEFAULT_ADMIN_ROLE, ALLOCATOR_ROLE, DISTRIBUTOR_ROLE
- **Deployer** = admin + allocator (same address)
- **DISTRIBUTOR** = unassigned (no holder)

## Findings Summary (7 vulnerabilities, 17 vectors tested)

| # | Title | Severity | Root Cause |
|---|-------|----------|-----------|
| F1 | Allocator Drain | HIGH | No safeguard on reduceAllocations |
| F2 | Cross-Allocator Theft | HIGH | No allocator isolation |
| F3 | Pause Inconsistency | HIGH | Pause blocks claim, not reduce |
| F4 | Emergency Without Check | HIGH | emergencyWithdraw ignores allocations |
| F5 | Unbounded Batch Drain | HIGH | No loop limit on batch operations |
| F6 | Phantom Allocation | MEDIUM | Emergency creates impossible state |
| F7 | Front-Run Claim | MEDIUM | No timelock on reduce |

## Key Technical Lessons

### 1. OZ v5 `_transfer` NOT virtual
Can't override `_transfer` in test mocks that inherit OZ ERC20. Solution: manual IERC20.

### 2. `vm.startPrank` + `new Constructor()` fails
Use one-shot `vm.prank` before `new`, not `vm.startPrank`.

### 3. Struct qualification required
`RewardsDistributor.Allocation[]` — bare `Allocation` causes Error 7920.

### 4. 17-Vector Deep Dive Framework
Systematic testing of ALL attack surfaces, not just the obvious one. See smart-contract-audit skill Phase 4b.

### 5. File Write Limits
split_content >8K tokens into multiple writes. Use Python terminal scripts for in-place edits.

## Files
- `src/RewardsDistributor.sol` — source (185 lines)
- `test/F1-DeepDive.t.sol` — 17 PoC tests (all PASS)
- `REWARDS_DISTRIBUTOR_ANALYSIS.md` — full analysis report
- `references/web3-exploit-patterns-ern.md` — 3 new exploit patterns
