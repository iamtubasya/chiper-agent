# Compound v2 Fork Analysis — Chain-Specific Pitfalls & Methodology

*Extracted from BenQI (Avalanche) analysis session. Applies to ANY Compound v2 fork on non-Ethereum chains.*

> **Companion KB:** `references/onchain-token-side-audit.md` — verifying the ERC20s
> behind cTokens (fee/rebase/blacklist vs exchange-rate accounting), OZ AccessControl
> role archaeology via RoleGranted logs, EIP-1967 proxy/admin topology, and RPC
> plumbing pitfalls (getLogs 10k range, whitelisted-method public RPCs, chain
> misidentification).

---

## 1. IRM (Interest Rate Model) Timing Mechanism

**Critical pitfall:** Compound v2 original uses **block-based** IRMs (`baseRatePerBlock`, `multiplierPerBlock`, `jumpMultiplierPerBlock`, `blocksPerYear`). Some forks — notably **BenQI on Avalanche** — use **timestamp-based** IRMs instead:

```
baseRatePerTimestamp()     ← NOT baseRatePerBlock
multiplierPerTimestamp()   ← NOT multiplierPerBlock
jumpMultiplierPerTimestamp() ← NOT jumpMultiplierPerBlock
timestampsPerYear()        ← NOT blocksPerYear (value: 31,536,000 = seconds/year)
```

**If you call the wrong selector on a timestamp-based IRM, it REVERTS.** This caused false "kink unknown" results in the initial BenQI analysis. All four parameters reverted because the function signatures were wrong.

**Detection method:** Try both selector families. If `baseRatePerBlock()` reverts but `baseRatePerTimestamp()` succeeds → timestamp-based.

**Why this matters for exploits:** If you're computing expected borrow/supply rates for a flash loan attack or rate manipulation PoC, using the wrong timing base gives wrong numbers. Timestamp-based rates are **much smaller per unit** than block-based rates (31M timestamps/year vs ~2.6M blocks/year on Ethereum), so the multipliers are proportionally larger.

---

## 2. Native AVAX Market (No underlying())

The qiAVAX market's `underlying()` function **reverts** — it's a native AVAX market, not an ERC20 wrapper. This means:
- `underlying()` cannot be called to get the token address
- The market directly holds native AVAX (deposited/withdrawn via payable functions)
- This is common for the native gas token on many chains

---

## 3. Python Keccak256 Limitation (Windows + Python 3.14)

`hashlib.new('keccak_256')` raises `ValueError: unsupported hash type keccak_256` on Python 3.14+ (Windows). The keccak module is not bundled.

**Workaround:** Use Foundry's `cast sig` to compute function selectors:
```bash
cast sig "functionName(argType1,argType2)"
# Returns 4-byte hex selector, e.g. 0x12345678
```

---

## 4. Snowtrace API Rate Limiting

Rapid consecutive calls to `api.snowtrace.io` cause `ConnectionResetError`. The API silently drops connections after ~5-10 rapid requests.

**Mitigation:**
- Add `time.sleep(1)` between calls
- Batch reads via `cast` (uses RPC, not Snowtrace)
- Fallback: use blockchain RPC directly for on-chain data (no rate limit)

---

## 5. Governance Analysis Methodology (Compound v2 Forks)

### Step 1: Identify Admin
```bash
cast call <COMPTROLLER> "admin()(address)" --rpc-url $RPC
```

### Step 2: Check if Contract or EOA
```bash
cast code <ADMIN_ADDRESS> --rpc-url $RPC
# Empty = EOA, Non-empty = contract
```

### Step 3: If Contract — Identify Type
- **Gnosis Safe**: `getThreshold()`, `getOwners()`, `nonce()`
- **TimelockController**: `delay()`, `getMinDelay()`

### Step 4: If Multisig — Check Owner Types
```bash
cast call <SAFE> "getOwners()(address[])" --rpc-url $RPC
# Check each owner for contract vs EOA
```

**Red flag:** 3-of-10 multisig with all EOA owners = **no timelock**, admin can change parameters immediately.

---

## 6. Fee-on-Transfer Token Check

Standard Avalanche bridge tokens (USDT.e, USDC.e, BTC.b, DAI.e, LINK.e) do NOT have fee-on-transfer. Detection:

```bash
balance_before=$(cast call <TOKEN> "balanceOf(address)(uint)" <RECIPIENT> --rpc-url $RPC)
# ... execute transfer ...
balance_after=$(cast call <TOKEN> "balanceOf(address)(uint)" <RECIPIENT> --rpc-url $RPC)
# diff != amount = fee-on-transfer
```

---

## 7. IRM Anomaly Detection

If an IRM's storage variables don't match known patterns, it may be:
- Custom IRM (project-specific logic)
- Different storage layout (same interface, different slot ordering)
- Proxy pointing to different implementation

**BenQI qiQI IRM anomaly:** `kink()` and `jumpMultiplierPerTimestamp()` revert, but `baseRatePerTimestamp()` and `multiplierPerTimestamp()` succeed. This is a **potential finding** worth investigating — hidden parameters could mean unexpected rate behavior.
