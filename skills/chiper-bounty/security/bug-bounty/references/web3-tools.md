# Web3 Security Tools — Complete Ecosystem

## Frameworks

### Foundry (Solidity)
```bash
# Install
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Usage
forge test                          # Run tests
forge test --fork-url $RPC_URL     # Fork mainnet
forge test -vvvv                    # Verbose output
forge test --match-contract Exploit # Run specific test
```

### Hardhat (JavaScript)
```bash
# Install
npm install --save-dev hardhat

# Usage
npx hardhat test                    # Run tests
npx hardhat test --fork $RPC_URL   # Fork mainnet
npx hardhat console                 # Interactive console
```

---

## Static Analysis

### Slither
```bash
# Install
pip install slither-analyzer

# Usage
slither .                           # Analyze current project
slither . --print human-summary     # Human-readable summary
slither . --detect reentrancy-eth   # Detect specific vulnerability
```

### SolFlow (Call-Graph Visualization)
```bash
# Install
pipx install solflow
pipx install solc-select

# Usage
solflow .                    # Start server at http://127.0.0.1:8080
solflow --expand-all .       # All flows fully expanded
solflow --port 9090 .        # Custom port

# Config (solflow.toml)
[scope]
exclude_paths = ["**/*.t.sol", "**/test/**"]
exclude_contracts = ["*Mock*"]
inline_libraries = ["openzeppelin-contracts"]
```

### SolidityScan
```bash
# CLI
solidityscan scan contracts/

# Features
- 90+ vulnerability detectors
- Gas optimization suggestions
- Code quality metrics
```

### Securify2
```bash
# Docker
docker run -it securify2

# Usage
securify2 contracts/
```

---

## Fuzzing

### Echidna
```bash
# Install
brew install echidna

# Usage
echidna-test contracts/Exploit.sol --contract ExploitTest
echidna-test contracts/Exploit.sol --config echidna.yaml
```

### Manticore
```bash
# Install
pip install manticore

# Usage
manticore contracts/Exploit.sol
manticore contracts/Exploit.sol --contract ExploitTest
```

### Mythril
```bash
# Install
pip install mythril

# Usage
myth analyze contracts/Exploit.sol
myth analyze contracts/Exploit.sol --execution-timeout 90
```

---

## Visualization

### solgraph
```bash
# Install
npm install -g solgraph

# Usage
solgraph contracts/Exploit.sol > graph.dot
dot -Tpng graph.dot > graph.png
```

### SOL2UML
```bash
# Install
npm install -g sol2uml

# Usage
sol2uml class contracts/ > classDiagram.svg
sol2uml storage contracts/ > storageLayout.svg
```

### Sūrya
```bash
# Install
npm install -g surya

# Usage
surya describe contracts/Exploit.sol
surya graph contracts/Exploit.sol | dot -Tpng > graph.png
```

---

## Blockchain Analysis

### Etherscan
- Contract source code verification
- Transaction history
- Internal transactions
- Token transfers

### Tenderly
- Transaction simulation
- Gas estimation
- State diffs
- Debug traces

### BlockSec Tools
- Transaction analysis
- MEV detection
- Flashloan tracking

---

## Monitoring

### Forta Protocol
```bash
# Install
npm install -g @fortanetwork/forta-agent

# Usage
forta-agent init
forta-agent run
```

### Tenderly
- Real-time monitoring
- Alerting
- Dashboard

---

## DeFi-Specific Tools

### DEX Tools
- **DEX Screener** — Price charts, liquidity
- **DEXTools** — Trading data
- **CoinGecko** — Token info

### Wallet Tracking
- **Arkham Intelligence** — Wallet labels
- **Nansen** — Smart money tracking
- **DeBank** — Portfolio tracking

### MEV Tools
- **Flashbots** — Private transactions
- **MEV-Boost** — Block builder
- **EigenPhi** — MEV data

---

## Quick Reference — Which Tool for What?

| Task | Tool |
|------|------|
| Smart contract testing | Foundry / Hardhat |
| Static analysis | Slither / SolidityScan |
| Fuzzing | Echidna / Mythril |
| Visualization | solgraph / SOL2UML / Sūrya |
| Transaction analysis | Tenderly / BlockSec |
| Monitoring | Forta / Tenderly |
| Price data | DEX Screener / CoinGecko |
| Wallet tracking | Arkham / Nansen |
| MEV analysis | Flashbots / EigenPhi |
| Solana BPF decompile | llvm-objdump / llvm-readobj (WSL) |
| Solana source audit | cargo audit / clippy |

---

## EVM Decompilation (Unverified Contracts)

**See also:** `web3-tools-solana.md` for Solana BPF decompilation (WSL required).

**Kapan pakai:** Contract TIDAK verified di Etherscan. Source code tidak available. Perlu analisis bytecode langsung.

### Tools:

#### cast disassemble (Foundry - VERIFIED WORKING ✓)
```bash
# Get bytecode
BYTECODE=$(cast code CONTRACT_ADDRESS --rpc-url $RPC_URL)

# Disassemble to opcodes
cast disassemble $BYTECODE

# Extract function selectors
cast selectors $BYTECODE

# Decode selectors
cast 4byte 0xa9059cbb    # → transfer(address,uint256)
```
**Status:** ✅ Installed, tested, working on Windows.

#### pyevmasm (Python - VERIFIED WORKING ✓)
```python
from pyevmasm import evmasm
bytecode = "6080604052..."
disassembled = evmasm.disassemble(bytes.fromhex(bytecode))
print(disassembled)
```
**Status:** ✅ Installed (v0.2.3), tested, working on Windows.

#### Dedaub (Web-based - NO INSTALL NEEDED)
```
https://dedaub.net/
Paste contract address → auto-decompile
Shows function signatures, storage layout, cross-references
Free tier available
```
**Status:** ✅ Web-based, always available.

#### 4byte.directory (Function selector lookup)
```bash
cast 4byte 0xdeadbeef  # Foundry (recommended)
# OR
curl "https://www.4byte.directory/api/v1/signatures/?hex_signature=0xdeadbeef"
```
**Status:** ✅ cast 4byte tested and working.

### EVM Decompilation Workflow:
```
1. GET BYTECODE
   └─ etherscan "Read Contract" → byte code
   └─ OR: cast code 0xContract --rpc-url $RPC_URL
   └─ OR: eth_getCode JSON-RPC

2. DISASSEMBLE
   └─ cast disassemble → opcodes (VERIFIED ✓)
   └─ OR: Dedaub web → visual function explorer (VERIFIED ✓)

3. ANALYZE DECOMPILED CODE
   □ Unprotected functions (no modifier/access control)
   □ Delegatecall to user-controlled address
   □ Selfdestruct callable by anyone
   □ Storage layout (slot 0 = owner)
   □ Hardcoded addresses (old admin)
   □ Fallback/receive function behavior
   □ Function selector matching (known vuln patterns)

4. RECONSTRUCT LOGIC
   □ Map function selectors → parameters (4byte.directory)
   □ Cross-reference with known contract patterns
   □ Identify upgrade mechanisms (proxy, diamond, beacon)

5. BUILD EXPLOIT
   □ Craft calldata for vulnerable function
   □ Test via Foundry fork: forge test --fork-url $RPC
   □ Verify exploit works on-chain
```

### Common Vulnerable Patterns (decompiled):
| Pattern | Opcode | Risk |
|---------|--------|------|
| CALL to user addr | CALL with calldata | Delegatecall exploit |
| SSTORE without auth | SSTORE any slot | Storage manipulation |
| SELFDESTRUCT | SELFDESTRUCT | Contract destruction |
| CREATE2 with user salt | CREATE2 | Deploy attacker contract |
| Balance manipulation | BALANCE | Flashloan vector |
| Block hash access | BLOCKHASH | Predictable randomness |

### Decision Tree:
```
Contract verified?
  ├─ YES → Source code tools (Slither, Mythril, Echidna)
  └─ NO  → EVM decompile (cast disassemble, pyevmasm, Dedaub)
      └─ Decompiled code clear?
          ├─ YES → Analyze directly
          └─ NO  → 4byte.directory + manual opcode analysis

Solana program?
  ├─ Has source → cargo audit + clippy
  └─ No source  → Solana BPF decompile (see: web3-tools-solana.md)
      └─ Decompiled clear?
          ├─ YES → Analyze entrypoint + CPI
          └─ NO  → Black-box (RPC tracing)
```
