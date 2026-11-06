# Solana Security — Audit Patterns
> Source: github.com/sannykim/solsec (891★)
> Source: itsabhay83/solana-exploit-tracker

## Common Solana Exploit Patterns

### 1. Account Substitution
- Attacker passes different accounts than expected
- Fix: Validate all accounts in instruction context

### 2. Missing Owner Checks
- Program doesn't verify account ownership
- Fix: Check `account.owner == program_id`

### 3. PDA Bump Seed Manipulation
- Attacker uses different bump seeds
- Fix: Store bump in account, verify on every call

### 4. Reentrancy via CPI
- Cross-Program Invocation reentrancy
- Fix: Use Lamport balance check before/after CPI

### 5. Integer Overflow
- Solana programs use Rust, but unchecked arithmetic possible
- Fix: Use `checked_add`, `checked_sub`, `checked_mul`

### 6. Close Account Exploit
- Attacker closes account mid-transaction
- Fix: Check account.lamports > 0 after operations

### 7. Account Data Matching
- Cross-program invocation with mismatched accounts
- Fix: Verify `account_info.key == expected_key`

## Audit Tools
```bash
# Cargo audit for Rust dependencies
cargo audit

# Anchor security checks
anchor build

# Solana program validator
solana program deploy --program-id $KEY $BPF_OUT_DIR/$PROGRAM.so

# Custom checks via solana CLI
solana account $ACCOUNT --output json-compact
solana transaction $TX --output json
```

## Pipeline
- Phase 0B: Identify if target is Solana-based
- Phase 0C: Load solana-specific audit checklist
- Phase 0C: Run cargo audit on program dependencies
- Phase 0C: Manual review of account validation
