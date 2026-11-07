---

## Solana BPF Decompilation (Verified Working ✓)

**Kapan pakai:** Audit Solana program tanpa source code. Program compiled ke SBF (Solana Binary Format). Perlu decompile untuk analisis.

### Tools:

#### llvm-objdump (Solana Platform-Tools - VERIFIED WORKING ✓)
```bash
# Location (WSL): ~/.cache/solana/v1.54/platform-tools/llvm/bin/
LLVM_OBJDUMP=~/.cache/solana/v1.54/platform-tools/llvm/bin/llvm-objdump

# Disassemble BPF program
$LLVM_OBJDUMP -d program.so

# Disassemble without raw bytes
$LLVM_OBJDUMP -d --no-show-raw-insn program.so

# Show ELF headers
$LLVM_OBJDUMP -f program.so
```
**Status:** ✅ Installed, tested, working in WSL.

#### llvm-readobj (Solana Platform-Tools - VERIFIED WORKING ✓)
```bash
# ELF headers
$LLVM_READOBJ --headers program.so

# Sections
$LLVM_READOBJ --sections program.so

# Symbols
$LLVM_READOBJ --symbols program.so
```
**Status:** ✅ Installed, tested, working in WSL.

#### cargo-build-sbf (Solana CLI - VERIFIED WORKING ✓)
```bash
# Build from source
cargo-build-sbf --manifest-path Cargo.toml
# Output: target/deploy/program.so
```
**Status:** ✅ Installed, tested, working in WSL.

#### Wrapper Script
```bash
# Usage (Windows): wsl -e bash -c "bash ~/.chiper/skills/bounty-pack/solana_decompile.sh program.so"
# Usage (WSL): bash ~/.local/hermes/scripts/solana_decompile.sh program.so
```
**Status:** ✅ Created and tested.

### Solana BPF Decompilation Workflow:
```
1. GET PROGRAM BINARY
   └─ Download .so from deployed program (GitHub, deploy artifact)
   └─ OR: cargo-build-sbf from source code
   └─ Format: ELF64-SBF (Solana Binary Format)

2. DISASSEMBLE
   └─ llvm-objdump -d program.so → BPF assembly (VERIFIED ✓)
   └─ Entry point: 0x138 (standard SBF entrypoint)

3. ANALYZE DISASSEMBLED CODE
   □ Entry point validation (program_id check)
   □ Account validation (is_signer, is_writable checks)
   □ CPI calls (cross-program invocations)
   □ Instruction discriminator matching (first 8 bytes)
   □ Unsafe blocks / unchecked math
   □ Account data parsing
   □ Error handling (unwrap vs proper error)

4. MAP INSTRUCTIONS TO LOGIC
   □ Discriminator → function mapping (Anchor IDL or manual)
   □ Account structures (Accounts trait)
   □ CPI targets (System Program, Token Program, etc.)
   □ Serialization format (Borsh)

5. BUILD EXPLOIT
   □ Craft instruction with discriminator + accounts + data
   □ Test via solana-test-validator (local validator)
   □ Verify exploit on devnet/testnet
```

### Common Vulnerable Patterns (Solana):
| Pattern | Assembly Signature | Risk |
|---------|-------------------|------|
| Missing signer check | No `is_signer` validation | Privilege escalation |
| Missing owner check | No `account.owner` compare | Account takeover |
| Incorrect CPI target | `call` to wrong program | CPI theft |
| Unsafe math | No overflow checks | Arithmetic exploit |
| Account reuse | No `close` instruction | State confusion |
| Discriminator bypass | Wrong instruction matching | Wrong function call |

### Decision Tree:
```
Solana program?
  ├─ Has source code → cargo audit + clippy + manual review
  └─ No source code  → Solana BPF decompile (llvm-objdump, llvm-readobj)
      └─ Decompiled code clear?
          ├─ YES → Analyze entrypoint + CPI calls
          └─ NO  → Black-box analysis (RPC, transaction tracing)
              └─ See: rust-solana-audit--blackbox-onchain-analysis.md
```
