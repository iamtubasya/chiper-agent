# SolFlow Integration — Solidity Call-Graph Visualization

## What is SolFlow
SolFlow compiles a Solidity repo, extracts call-graph facts via Slither, and serves one interactive Flow (call tree) per external entry point. Every node shows real source code. Local-only, no network calls.

**GitHub:** https://github.com/norah1499/solidity-flow-navigator
**Install:** `pipx install solflow && pipx install solc-select`

## When to Use SolFlow

### ✅ USE for:
- Complex DeFi protocols (Uniswap, Aave, Morpho-style)
- Multi-contract architectures with deep inheritance
- Protocols with many entry points (>20 external functions)
- Cross-contract call tracing (DEX → Oracle → Lending → Governance)
- Understanding virtual dispatch / override chains
- Identifying unresolved calls (potential attack surface)

### ❌ SKIP for:
- Simple single-contract tokens (ERC20/ERC721)
- Protocols you already know well
- Quick IDOR / web-api testing (not Solidity-related)

## Integration with Bug Bounty Workflow

### Phase 2 (Recon) — Entry Point Enumeration
```bash
# After cloning target repo
solflow path/to/target

# Server starts at http://127.0.0.1:8080
# Index shows ALL external entry points grouped by contract
# Filter: mutating (state-changing) vs read-only (view/pure)
```

**What to look for:**
- Entry points with no access control (public functions without onlyOwner/modifier)
- Mutating functions that accept user-controlled addresses
- Functions that make external calls (high_level/low_level call edges)
- Entry points with many modifiers (complex auth logic = more room for bypass)

### Phase 3 (Analyze) — Call Flow Tracing
For each suspicious entry point, expand the Flow to see:
1. **Full call tree** — entry → internal calls → library calls → external calls
2. **Modifier chain** — all modifiers applied, folded into the tree
3. **Virtual dispatch** — which override actually runs at runtime
4. **Unresolved nodes** — interface calls without binding, low-level calls, Yul dispatch

**Attack surface indicators:**
- 🔴 `UnresolvedNode(LOW_LEVEL_CALL)` — dynamic call target, potential injection
- 🔴 `UnresolvedNode(INTERFACE_CALL_NO_BINDING)` — can't trace, needs manual binding
- 🟡 `ExternalNode` — calls into dependencies (check for known vulns)
- 🟢 `FunctionNode` — resolved, can trace full path

### Phase 4 (Verify) — PoC Development
Use SolFlow to:
- Trace exact function path from entry to vulnerable code
- Identify all state changes along the path
- Find prerequisite calls (setup functions, initialization)
- Map cross-contract dependencies for flashloan/race conditions

## CLI Reference
```bash
solflow path/to/project                    # Basic usage
solflow --expand-all path/to/project       # All flows fully expanded
solflow --port 9090 path/to/project        # Custom port
solflow --exclude-path "test/**" path      # Exclude test files
solflow --exclude-contract "*Mock*" path   # Exclude mock contracts
solflow --inline-library OpenZeppelin path # Inline OZ dependency
solflow --stub-path "lib/math/**" path     # Stub dense math libs
```

## Config File (solflow.toml)
```toml
[scope]
exclude_paths = ["**/*.t.sol", "**/test/**", "**/mocks/**"]
exclude_contracts = ["*Mock*", "*Test*"]
inline_libraries = ["openzeppelin-contracts"]
stub_paths = []

[bindings]
# Bind interface to concrete implementation
ISwapRouter = "SwapRouter"
IVault = "Vault"
```

## Workflow Integration

### Step 1: Setup (once per target)
```bash
cd ~/targets/{protocol}
git clone https://github.com/{protocol}/{repo}.git
cd {repo}

# Ensure correct solc version
solc-select install 0.8.20 && solc-select use 0.8.20

# Install dependencies
forge install  # or npm install

# Start SolFlow
solflow .
```

### Step 2: Entry Point Audit
1. Open http://127.0.0.1:8080
2. Filter: **Mutating** only (state-changing functions = attack surface)
3. For each entry point:
   - Check access control (modifiers shown in flow)
   - Expand call tree to see full execution path
   - Note any `UnresolvedNode` (potential vulnerability)
   - Bookmark interesting entry points

### Step 3: Deep Trace
For bookmarked entry points:
1. Expand ALL nodes (bird's-eye view)
2. Trace: entry → modifier → internal calls → external calls → state changes
3. Identify trust boundaries (where does user input reach external calls?)
4. Cross-reference with known vulnerability patterns:
   - Uninitialized proxy? (check for `initialize()` in call tree)
   - Reentrancy? (check for external calls before state updates)
   - Flashloan surface? (check for single-tx state manipulation)

### Step 4: Interface Binding
For unresolved interface calls:
1. Click the `UnresolvedNode` in the flow
2. Use the Bindings panel to pin the concrete contract
3. SolFlow resolves into the bound contract's body
4. Save bindings to `solflow.toml` for persistence

## Limitations
- **Not a vulnerability scanner** — it shows code shape, not bugs
- **Requires compilation** — target must build successfully
- **Slither-dependent** — if Slither can't analyze it, SolFlow can't visualize it
- **No auto-detection** — auditor must interpret the call graphs
- **Local only** — no cloud/team collaboration

## Complementary Tools
| Tool | Use With SolFlow For |
|------|---------------------|
| Slither | Direct static analysis (detectors, printers) |
| Aderyn | Independent vulnerability detection |
| Mythril | Symbolic execution for specific paths |
| Echidna | Fuzzing stateful properties |
| Foundry | Writing & running PoC exploits |

## Example: Trace a Swap
```
Entry: PoolManager.swap(PoolKey, SwapParams)
  ├─ modifier: onlyInitialized
  │   └─ Pool.getPool() → Reserves
  ├─ Pool.swap()
  │   ├─ DexSwap.swap() → UniswapV3
  │   │   └─ Oracle.getTWAP() → Chainlink
  │   ├─ Pool._updateReserves()
  │   └─ Pool._emitSwapEvent()
  └─ [emit Swap]
```

From this trace you can see:
- Oracle dependency (Chainlink TWAP) — check for manipulation
- External call to UniswapV3 — check for slippage protection
- State update after external call — potential reentrancy vector
