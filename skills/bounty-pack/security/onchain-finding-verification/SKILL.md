---
name: onchain-finding-verification
description: "Use when verifying an on-chain finding before reporting."
version: "1.1"
author: RESEARCHER_NAME
license: "internal"
tags: [web3, smart-contract, defi, verification, false-positive, severity, evidence]
metadata:
  hermes:
    tags: [web3, smart-contract, defi, verification, false-positive, severity, evidence]
    related_skills: [bug-bounty, vuln-hunter]
---

# On-chain Finding Verification

## ⛔ CANDIDATE RULE (MANDATORY — EVERY TEST)
- **Each test = one candidate. Finding something = mark candidate. CONTINUE to next test.**
- **Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0F).**
- **DO NOT generate report during Phase 0C. Report = ABSOLUTE LAST.**
- **If you find CRITICAL → mark candidate → KEEP TESTING. Do NOT stop.**

## ⛔ REFERENCE AUTO-LOAD (MANDATORY — load when this skill is activated)
When this skill is loaded, IMMEDIATELY read these reference files:
```
read_file('references/decode-false-positives.md')
read_file('references/ern-protocol-case-study.md')
read_file('references/bulk-exchange-case-study.md')
read_file('references/forensics-trace.md')
read_file('references/move-supra-rpc-verification.md')   # only when the target is Move/Supra
read_file('references/solana-blackbox-forensics-method.md')   # only when the target is Solana and source is closed but a client IDL exists
read_file('references/storage-ring-and-accessor-negatives.md')   # before claiming "no samples / empty array / never populated"
```

The gate between "I saw something alarming on-chain" and "I am reporting this".

An on-chain anomaly is not a finding. Before any report, PoC, or severity claim, the anomaly
must survive the staged verification in sections 1-3 -- and the first suspect is always
your own decoder. This skill exists because a large share of on-chain "CRITICAL" alarms are
self-inflicted artifacts, and because a fabricated `from` can invent a dead exploit chain --
which is INFORMATIONAL, never HIGH.

> Companion technique detail: `references/decode-false-positives.md` (the full
> alarm -> real-cause table, pagination rules, and the honest severity floor).

## When to Use

Load this before writing up, PoC-ing, or severity-rating any on-chain / DeFi finding --
and whenever an on-chain read produces an alarming result that would make a great headline.

Trigger phrases: "verify this finding", "is this on-chain bug real", "escrow underfunded",
"claim path bricked", "role revoked so payouts stopped", "drain", "unverified contract holds
a role", or any point where a decoded value is about to become a report.

Do not load it for pure recon (address discovery, ABI fetching) with no finding claimed yet.

### Extra trigger: a finding derived from a historical-exploit pattern

If the finding came from matching a known technique rather than from reading the code cold — i.e. you
arrived here because the protocol's shape resembles an exploited one (share↔asset conversion
rounding, a batch dispatch entry, solver-based invariants, a declared field trusted over an
independent source) — this skill still applies, **unchanged**, and one extra rule is mandatory:

> **A technique match is a lead, not a finding.** The historical case proves the *shape* is
> exploitable somewhere; it says nothing about whether *this* deployment is reachable by it.

So the verification must still establish reachability on the live contract: real caller, real state,
real value at risk. Cite the historical exploit tx hash as *corroboration* in the report — never as
the proof.

Where the shapes come from: `defi-exploit-forensics` → `skills/security/defi-exploit-forensics/references/technique-library-2025-2026.md`
(T1–T12) and `skills/security/defi-exploit-forensics/references/detection-patterns.md` (patterns 1–9). Confirm the deployment actually
carries the vulnerable code before any severity claim — the fast path is the selector pre-check in
`live-vs-source-bytecode-forensics`.

---

## 1. The #1 killer -- simulating with the WRONG `from`

Never run a capability probe with a `from` address that has no business being the caller.

Probing a role-gated function with `from=0x0` returns `AccessControl.MissingRole` and
"proves" the path is bricked. It proves nothing -- only that `0x0` lacks the role.

The decisive test is a REPLAY of a historical successful transaction, at the current block:

```
eth_call({ from: <original tx.sender>, to: <contract>, data: <original tx.input>, value: 0 })
```

| Outcome | Meaning |
|---|---|
| Reverts with a later, deeper error ("Invalid proof", a business require) | The gate before it passed -> path is LIVE |
| Reverts with the access-control error | Genuinely blocked for that caller |
| Succeeds | Currently live for that caller |

The position of the revert in the call chain is the entire signal. Note that read-only
reads (`balanceOf`, `getCode`) do not enforce `msg.sender` and work with any `from` -- do not
let that lull you into a bogus `from` for a state-changing signature. Probes must stay
read-only; a probe that would move funds is not a probe.

---

## 1b. Dormant contract triage -- BEFORE any severity claim

User correction (Ern Protocol audit 2026-09-15): "Jgn kasih sy potensial, kasih yg real."
Code vulnerability with zero on-chain impact is INFORMATIONAL, never HIGH/CRITICAL.

Before claiming ANY severity, run this check:

```bash
# 1. Contract balance (ETH + major ERC20s)
cast balance $CONTRACT --rpc-url $RPC
cast call $USDC "balanceOf(address)(uint256)" $CONTRACT --rpc-url $RPC
cast call $USDT "balanceOf(address)(uint256)" $CONTRACT --rpc-url $RPC
cast call $DAI  "balanceOf(address)(uint256)" $CONTRACT --rpc-url $RPC
cast call $WETH "balanceOf(address)(uint256)" $CONTRACT --rpc-url $RPC

# 2. Transaction count -- has this contract ever been used?
cast tx-count $CONTRACT --rpc-url $RPC

# 3. Log events -- any activity at all?
cast logs $CONTRACT --from-block 0 --to-block latest --rpc-url $RPC
```

| Outcome | Action |
|---------|--------|
| Zero balance + zero txns + zero logs | STOP. Contract is dormant. Vulnerability = code-only finding. Report as INFORMATIONAL/LOW with note: "currently dormant, risk materializes if assets deposited." |
| Zero balance but has past txns | Check if funds were drained or never deposited. Historical != current. |
| Non-zero balance | Proceed to full verification (section 2). |
| Unknown (RPC fails) | Try alternate RPC. Do NOT skip this step. |

Severity mapping for dormant contracts:

| Code vuln severity | On-chain state | Report as |
|-------------------|---------------|-----------|
| CRITICAL | Zero balance, zero activity | INFORMATIONAL -- "code vulnerability exists but contract is dormant" |
| HIGH | Zero balance, zero activity | LOW -- "architectural risk, no current impact" |
| MEDIUM | Zero balance, zero activity | LOW/INFO -- "design flaw, dormant" |
| Any | Non-zero balance | Full severity (verify section 2) |

This is the #1 false-severity trap in bug bounties. Programs reject "CRITICAL" findings on
dormant contracts. Honest severity = faster payout.

See: references/ern-protocol-case-study.md

---

## 1c. Solana program verification — RPC-based live analysis

When the BPF source is unavailable (closed-source, only client SDK found), verify
program state and architecture purely via Solana RPC calls. No decompilation needed.

### Step 1: Program existence and upgradeability

```bash
SOL_RPC="https://api.mainnet-beta.solana.com"

# Check program account — BPFLoaderUpgradeab1e = upgradeable
curl -s -X POST "$SOL_RPC" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1,
  "method": "getAccountInfo",
  "params": ["PROGRAM_ID", {"encoding": "jsonParsed"}]
}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
info = d['result']['value']
print(f'Owner: {info[\"owner\"]}')  # BPFLoaderUpgradeab1e = upgradeable
print(f'Executable: {info[\"executable\"]}')
print(f'Lamports: {info[\"lamports\"]}')
data = info['data']
if isinstance(data, dict):
    print(f'Program data: {data.get(\"parsed\",{}).get(\"info\",{}).get(\"programData\",\"N/A\")}')
"
```

| Owner | Meaning |
|-------|---------|
| BPFLoaderUpgradeab1e | Program is UPGRADEABLE — find upgrade authority |
| BPFLoader2002728 | Program is immutable (deployed before upgradeable loader) |

### Step 2: Extract upgrade authority

```bash
# Get program data account from Step 1, then decode it
curl -s -X POST "$SOL_RPC" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1,
  "method": "getAccountInfo",
  "params": ["PROGRAM_DATA_ACCOUNT", {"encoding": "base64"}]
}' | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
raw = base64.b64decode(d['result']['value']['data'][0])
print(f'Data length: {len(raw)} bytes')
# First 4 bytes: slot as u32, next 4: padding
# Last 32 bytes: upgrade authority pubkey (if set, all zeros if none)
auth = raw[-32:]
if auth == b'\x00' * 32:
    print('Upgrade authority: NONE (immutable)')
else:
    import base58 as b58
    print(f'Upgrade authority: {b58.b58encode(auth).decode()}')
    print(f'Authority is EOA (not multisig) → single key compromise risk')
"
```

**CRITICAL:** If upgrade authority is an EOA (not Squads multisig), the program can be
silently upgraded to steal all funds. Cross-check with docs claims — if docs say
"multisig" but on-chain shows EOA, that's a finding.

### Step 6: API attack surface enumeration (for DEX / CeFi targets)

Solana DEX targets almost always have offchain API servers — these are OUT of scope
for on-chain audits but are prime IDOR/auth-escalation targets.

**Subdomain discovery:**
```bash
subfinder -d target.trade -all 2>/dev/null | sort -u
# Look for: api, mainnet-api, staging-api, admin, docs, app, ws, mobile
```

**API endpoint enumeration:**
```bash
# Probe discovered subdomains
for sub in api mainnet-api staging admin docs mobile ws; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://${sub}.target.trade" --max-time 5)
  echo "$sub: $code"
done
```

**IDOR test on DEX account endpoints:**
```bash
# Most DEX APIs expose account data via POST with user pubkey
API="https://mainnet-api1.target.trade/api/v1"
curl -s -X POST "$API/account" \
  -H "Content-Type: application/json" \
  -d '{"type":"fullAccount","user":"<KNOWN_USER_PUBKEY>"}'
# If returns position data → IDOR confirmed
# Test sub-types: positions, orders, balances, margin, equity, subAccounts
```

**User pubkey source for batch IDOR:**
```bash
# Get real users from on-chain transaction history
curl -s -X POST "https://api.mainnet-beta.solana.com" \
  -H "Content-Type: application/json" -d '{
    "jsonrpc":"2.0","id":1,
    "method":"getSignaturesForAddress",
    "params":["PROGRAM_ID",{"limit":50}]
  }'
# For each signature, decode instruction to extract signer pubkey
# Then test IDOR against each discovered pubkey
```

**Zellic/audit blind spot:** On-chain program audits (Zellic, OtterSec, Neodyme) do NOT
cover offchain API endpoints. IDOR on API is a separate finding class — always test.

### Step 3: Vault/token balance verification

```bash
# Get vault ATA balance
curl -s -X POST "$SOL_RPC" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1,
  "method": "getTokenAccountBalance",
  "params": ["VAULT_ATA_ADDRESS"]
}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
bal = d['result']['value']
amt = int(bal['amount'])
dec = bal['decimals']
human = amt / (10 ** dec)
print(f'Vault balance: \${human:,.2f} ({amt} raw, {dec} decimals)')
if human > 1_000_000:
    print('HIGH TVL — real money at risk')
"
```

### Step 4: Instruction decoding from transactions

```bash
# Get recent signatures for program
curl -s -X POST "$SOL_RPC" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1,
  "method": "getSignaturesForAddress",
  "params": ["PROGRAM_ID", {"limit": 10}]
}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
for s in d.get('result', []):
    print(f\"{s['signature']}  {s.get('err', 'OK')}\")
"

# Decode instruction data (base58 → opcode + params)
python3 -c "
import base58
data = 'BASE58_INSTRUCTION_DATA'
raw = base58.b58decode(data)
print(f'Opcode byte: {raw[0]}')
print(f'Full data: {raw.hex()}')
# Common Solana DEX patterns:
# byte 0 = instruction discriminator
# bytes 1-8 = amount (u64 little-endian)
if len(raw) >= 9:
    import struct
    amount = struct.unpack('<Q', raw[1:9])[0]
    print(f'Amount: {amount}')
"
```

### Step 5: Cross-reference SDK source with on-chain transactions

When a public client SDK exists (e.g. Rust crate), cross-reference:

1. **PDA derivation** — Verify on-chain vault PDA matches SDK's PDA seeds
2. **Instruction format** — Verify opcode bytes match SDK's `Action` enum
3. **Account layout** — Verify transaction accounts match expected positions
4. **Signing** — Compare clear-sign message format with what user actually signs

**Red flags when cross-referencing:**
- SDK shows different signing paths (e.g. V1 vs V2) for same instruction
- On-chain instruction has accounts NOT in SDK's expected layout
- SDK documents fee caps but on-chain has no cap enforcement

### Solana-specific severity mapping

| Finding | On-chain state | Report as |
|---------|---------------|-----------|
| Upgradeable program, EOA authority | TVL > $1M | HIGH — single key can steal all funds |
| Upgradeable program, EOA authority | TVL < $100K | MEDIUM — limited impact |
| Upgradeable program, multisig authority | Any TVL | LOW/INFO — governance mechanism exists |
| SDK signing divergence | Active users signing | HIGH — user may unknowingly sign wrong data |
| Missing on-chain validation | Offchain matching only | HIGH — no settlement guarantees |
| Admin-controlled risk params | Active liquidations | MEDIUM — manipulation possible |

See: references/bulk-exchange-case-study.md

Companion for closed-source Solana targets WITH a client IDL (codama-generated):
`references/solana-blackbox-forensics-method.md` — building a validated borsh account decoder
from the generated types (Loan LEN=1634 checksum), decoding fixed-format oracle accounts
(pubkey-find → stride inference → cross-check against the off-chain DB), the per-instruction
signer-map regex across the whole IDL, the Squads-vs-EOA one-query table, the health/liquidation
scan via the target's own indexed API, and the `getProgramAccounts` zero-length-dataSlice memcmp
pitfall. Also: trace a loan's creation tx before calling an absurd-looking position a bug —
protocol-created test positions via Squads VaultTransactionExecute look like overleveraging.

---

## 1d. Move / Supra program verification — RPC-based live analysis

Supra's public RPC is as rich as Solana's for black-box work, and richer than most EVM nodes:
you can enumerate every module, read the **full ABI including struct field types**, and
**execute view functions** to test the protocol's own math. No explorer, source, or GitHub
needed. Full recipe: `references/move-supra-rpc-verification.md`.

Shape of it:
- `GET /rpc/v1/accounts/{addr}/modules` → module list; the *names* reveal the design
  (`voter`+`voting_escrow`+`gauge_*`+`bribe`+`fee_distributor`+`minter` = ve(3,3) port;
  `clmm_math`+`tick_math` = concentrated liquidity).
- `GET /rpc/v1/accounts/{addr}/modules/{name}` → `exposed_functions`
  (`is_entry`, `is_view`, full param types) + `structs` (state layout and integer widths —
  where overflow lives) + `friends`.
- `POST /rpc/v1/view` with `{"function":"0xPKG::mod::fn","type_arguments":[],"arguments":[…]}`.
  **u64/u128/u256 are JSON strings, not numbers.** Struct args are objects of their fields.
  Read the parse errors — they name the expected type.
- **ABI only, no bytecode/source.** Plan around it.

### The Move access-control sweep — cheap, high-signal, do it first

Enumerate every module, take every function with `is_entry == true`, and split:

```
entry WITHOUT "&signer"                        -> callable by ANYONE, review hard
entry WITH "&signer" AND a bare "address"      -> ownership-check review
```

**The reasoning rule that kills most false positives:**

> A Move function with **neither `&signer` nor `&TxContext` cannot know who called it**, so it
> cannot pay the caller. Any value it releases must be credited to an address it was *given*.
> A no-signer function taking `address` and paying that address is a gasless
> "poke / claim for someone else" helper — not a theft primitive.

This disposed of two alarming-looking candidates in one session
(`voter::claim_bribes_for_address(address, …)` with no signer while every sibling claim had
one; `vesting::vest_individual(address, address)`). It is a filter, not a proof: it rules out
*paying the caller*, so still check whether an authorization is required for the named address
and whether shared state can be advanced in the caller's favour.

Signed integers are per-package structs, so the **same type name can carry two encodings**
(Dexlyn: core `{bits:u64}` two's complement vs tokenomics `{value:u64,is_negative:bool}` s
sign-magnitude). Negative values arrive as `bits - 2**64`. Two encodings is a hardening note,
not a finding, until you show a value crossing between them.

---

## 1e. Solana read-only execution — simulate the program, never submit

§2b item 5 says "execute it or drop it". On Solana the execution that costs nothing is
`simulateTransaction` with `sigVerify: false`: the program really runs, you get its actual
Anchor error code and `Program log:` lines, and **no state changes and no signature** are
needed. Use it whenever the hypothesis is about what the program *enforces* (claim window,
proof binding, ownership, ordering) rather than what account *state* says — an account-state
read can only ever tell you what was recorded, not what will be rejected.

Full recipe + the worked case (Merkle-distributor "claim window closed" hypothesis, refuted in
one call): `references/solana-read-only-simulation.md`.
Runnable builder: `scripts/simulate_solana_ix.py` (JSON ix spec → legacy wire format → simulate).

Four things that decide whether it works:

1. **Validate your layout offsets against a field you already know.** Re-implement the client's
   own parser (it is in the JS bundle), then assert the `mint` field equals the token mint you
   expect and the 8-byte Anchor discriminator matches. If `mint` does not round-trip, every
   timestamp you read from that struct is fiction — a wrong offset here produced a whole
   "claim window closed 26 hours ago, 138,123 users locked out" story that the simulation then
   killed in one call.
2. **Message-level counts are shortvec; Anchor `Vec` lengths inside instruction data are u32
   LE.** Mixing them yields `InstructionDidNotDeserialize (102 / 0x66)`, which reads like a
   wrong discriminator but is only a wrong length prefix. The instruction's 8-byte
   discriminator itself comes from the client bundle, not from guesswork.
3. **Instruction order is part of the contract.** An account-creating instruction (e.g. ATA
   `CreateIdempotent`, opcode `0x01`) must come *before* the instruction that reads that
   account, or you get `AccountNotInitialized (3012)` naming the *consumer's* account — a
   message about your harness order, not about the program's security. ComputeBudget ixs are
   optional for simulation; the client's own order is the template to copy.
4. **The success log is the evidence, and it can refute you.** A passing simulation prints the
   program's own interpretation of the fields
   (`Created new claim with locked 0 and 2985147 unlocked with lockup start:1791822372 end:1791822672`)
   — that single line both disproved the window hypothesis (those are *vesting* timestamps, and
   `end` had already passed) and confirmed the rest of the parse.

Pitfalls: a public RPC will 429 after a handful of calls — pace, and never read that as
target-side blocking. Getting `Instruction: <Name> invoke [1]` into the logs already proves the
discriminator and account list are correct even when the program then fails; iterate from that
point instead of rebuilding. And remember that a *successful* simulation only proves the
instruction would be accepted — the missing signature is the real gate, so state that gate
explicitly rather than implying the call could be landed.

---

## 1f. An accessor returning 0 is NOT "the array is empty" -- decode the storage

Hit live 2026-10-27 (Tacit TacVault). `latest()` returned `0` on both venue oracles, and a sweep
of `sampleOf(i)` over 140 consecutive intervals returned `(0, 0)` for every one. Reported as
"the oracle has no samples / the ring is empty". **Wrong.** `eth_getStorageAt` over the whole
ring showed **128 / 128 slots populated**, every one of them stale: the newest record was ~540
intervals behind where the contract would price, so the sweep window (anchored on the *current*
index, not on the newest *recorded* one) walked straight past all the real data.

The distinction that changes the finding, and the severity:

| What the accessor proves | What it does NOT prove |
|---|---|
| No record inside the window the accessor reads | That no record exists at all |
| The read is unusable *now* | That it was never usable, or that it can never be repaired |

Three rules:

1. **A bounded negative is not absence.** Before writing "empty / never populated / zero
   samples", read the storage and count. A packed array or ring is reachable with
   `eth_getStorageAt` at consecutive slots from its declared base; decode the packing and print
   how many slots are non-zero. `0 of N` is evidence; "my loop returned zeros" is not.
2. **Anchor the sweep on the recorded max, not the expected index.** Compute what the contract
   *would* use now (for an interval oracle: `(block - 1 - GRACE) / STEP - 1`), but derive the
   sweep from the **newest value you actually find in storage**. The delta between the two is
   the finding: it converts straight into age (`intervals_behind * STEP * 12 / 86400` days),
   which is far more persuasive than "the read reverts".
3. **"Never recorded" and "stopped recording N days ago" are different findings.** The first
   points at deploy/config; the second at an unmonitored operational dependency. They carry
   different severity and different remediation. Never let a `0` from an accessor pick one.

Corollary for the honesty block: if the first write-up said "empty" and storage then showed
"full but stale", that is a **correction to state in the report and to the operator**, not a
silent rewrite. Re-derive any "cannot be repaired" claim from the contract's own bound (here
`RING = 128` intervals, so gaps older than ~21 h are permanently unrecordable) instead of
asserting it.

Full recipe: packing decode, provider constraints, deploy-block binary search --
`references/storage-ring-and-accessor-negatives.md`.

---

## 2. Staged verification order -- stop at the first contradiction

1. Role truth -- `hasRole(role, candidate)` for every actor (admin, operator, contract, EOA);
   plus `getRoleAdmin(role)` and whether the admin can re-grant. If `getRoleMemberCount`
   reverts, the contract is plain AccessControl, not Enumerable -- enumerate by
   candidate list instead of giving up and declaring the role unknown.
2. Capability -- replay a historical successful call at the current block (section 1). Never fabricate `from`.
3. Actor identity -- `eth_getCode` for every privileged address. Contract vs EOA changes
   the whole narrative; an unverified contract holding a privileged role is a different
   finding from an EOA holding it. Never trust a single mis-parsed `code_len`.
4. Magnitude -- the real at-risk amount: Active-state records only, correct `decimals()`
   read from the token, and a fixed pagination window.
5. Destination -- identify every outflow counterparty before calling it a drain
   (a verified CErc20Delegator is a yield deposit, not a rug).

Only when all five agree do you have a finding. Contradiction between any two = decoder bug,
not a vulnerability.

---

## 2b. Fork-PoC controls -- what makes an integration finding defensible

A PoC that only shows the bad thing happening is half evidence. A PoC with both controls is
what a triager cannot wave away with "maybe your test is wrong". Three assertions, every time:

1. **Healthy-environment control.** One call that must SUCCEED and prove the harness is real:
   a selector the live contract genuinely implements, a live read returning a sane value.
   Without it, "X reverts" is indistinguishable from a bad RPC, a wrong address, or a stale
   fork block. `cast call <live addr> "currentRound()(uint256)"` returning a plausible number
   is enough, and it costs one call.
2. **Root-cause assertion.** Isolate the MECHANISM, not just the symptom: assert the exact
   thing that is missing. For a selector that does not exist, assert the `staticcall` returns
   `ok == false` **with EMPTY revert data** -- empty payload is what distinguishes "no such
   selector and no fallback" from "the function exists and reverted for a business reason".
3. **Positive control.** Drive the SAME code path with the broken input replaced by a working
   one, and assert it then behaves correctly. This is the assertion that proves "the defect is
   the wiring, not the logic", and it is the one that closes the "your harness is broken"
   reply. Worked shape (TimbSwap F1): vault wired to the live registry -> `release()` reverts
   (effect); the SAME vault wired to a three-line `MockOracle` returning a matured value ->
   `release()` pays exactly half and credits the treasury (positive control). Two
   environments, one variable changed.
4. **The blocked path must have a path that SUCCEEDS.** When the finding is "this guard stopped
   me", the probed call has to succeed the moment the guard lets it through — otherwise a
   revert from the call BODY is indistinguishable from the guard holding, and the test reports
   the OPPOSITE of the truth.

   Live example (2026-10-08, a reentrancy-guard finding): the probe wrapped its reentrant call
   in `try/catch` and scored any revert as "guard blocked me". It went green. But the revert
   was `safeTransfer` failing on an empty balance — the guard was *already* defeated and the
   test said it held. Fixing the probe to call a **successful no-op when permitted**
   (`cleanupNative(0, address(this), "")`, which does nothing but must not revert) flipped the
   result to the real one:

   ```solidity
   try router.cleanupNative(0, address(this), "") {
       reentered = true;              // guard let us through
   } catch {
       reentryReverted = true;        // guard held
   }
   ```

   Two corollaries. (a) If EVERY path reverts, you have measured nothing — go read the revert
   selector before concluding the control protected anything. (b) A guard keyed on `msg.sender`
   rejects a *different* address with its own error (e.g. `InvalidMsgSender(stored, actual)`),
   so an intermediate contract calling in on your behalf fails for the wrong reason; pick a
   trigger the guard is designed to admit (a self-call, `target == address(this)`) and let the
   disarm do the work.

5. **A hypothesis formed by READING is not evidence. Execute it or drop it.** The single most
   repeated failure mode in this class of work is a confident source-reading that turns out to
   be wrong the moment it runs. Four in one session (2026-10-08), each of which would have been
   a false positive shipped to a program that only pays for real impact:

   | Reading said | Execution showed | Why the reading was wrong |
   |---|---|---|
   | `memoryToBytes(ptr, 0)` skips its `assembly` block → returns a null `bytes` → reads scratch space | pointer `0x60`, length `0`, unaffected by a value planted at `0x00` | Solidity **pre-allocates** memory variables; the block only *reassigns*, so length 0 returns a valid empty `bytes` |
   | `claim_bribes_for_address` (no `&signer`) lets anyone claim a victim's bribes | no signer and no `&TxContext` ⇒ cannot know the caller ⇒ must credit the `address` arg | Move semantics — see §1d |
   | probe's `try/catch` scoring any revert as "guard held" | the revert was `safeTransfer` on an empty balance; the guard was *already* defeated | §2b item 4 — the blocked path needs a path that SUCCEEDS |
   | a `forge test` run read as total failure | tests had actually passed | output parsed wrong |

   Two rules fall out, and they are the honest counterpart of §2b:

   - **Build the control first.** Every one of these was caught by the control assertion
     (§2b items 1 and 3), not by re-reading the code more carefully. If a candidate has no
     control, it has no result.
   - **A failed hypothesis is a NEGATIVE, and negatives get stated, not silently dropped.**
     Report "tested, disproved" to the operator with the same clarity as a find. A reading-based
     claim that never executed is the thing that damages credibility — and it taints the valid
     findings sitting next to it in the same report.

   Corollary for the operator's own framing: when a session produces only negatives, say so
   plainly. Do not promote a structural curiosity (e.g. two encodings of one integer type) to a
   finding to avoid an empty result.

**⛔ Before reporting: does the vendor already know?** Grep their own test/audit tree for the
mechanism and for issue IDs (`VIG`, `AUDIT-`, `SEC-`, `FIX-` in filenames). This session found
`ReentrancyGuardMsgSenderVIG084Test.sol` asserting the guard must **not** be cleared — the class
was known internally, and the fix existed in the repo while the **deployed** contract still
carried the vulnerable code. That changes the framing, the expected triage reply, and whether to
spend a report slot at all: say "known internally, still not deployed" in the report instead of
discovering it from the response. Confirm it behaviourally on a fork (§2b) — a behavioural proof
survives any argument about which source is authoritative. Detection shape and the deployed-vs-repo
diff: `smart-contract-audit` → `skills/security/smart-contract-audit/references/reentrancy-guard-and-approval-defects.md`.

**Live-fork assertion discipline.** On `--fork-url`, any address that exists on the live chain
already has a balance, so an ABSOLUTE assertion is a false failure waiting to happen:
`assertEq(token.balanceOf(TREASURY), 0.5e18)` FAILED against a fork where the treasury already
held ~31,928 TIMBS -- and the failure text reads like a finding when it is only the test's
fault. Snapshot first, assert the DELTA:

```solidity
uint256 before = IERC20(T).balanceOf(dest);
... act ...
assertEq(IERC20(T).balanceOf(dest) - before, expected, "delta");
```

Also `deal()` the actor's balance instead of assuming it, and pick an amount the token will
actually move -- if the token has a transfer cap / whitelist, read it and size the transfer
against it, or the test dies on the setup line. Two setup cycles lost to exactly this.

Two compile-side details that cost cycles against a Cancun contract: an `address constant`
hard-coded in the test must be **EIP-55 checksummed** or solc refuses the file outright with
`Invalid checksum ... please prepend '00'` (it will hand you the corrected literal — copy it,
do not reformat by eye), and `foundry.toml` needs `evm_version = "cancun"` whenever the contract
under test (or the harness) touches transient storage, or compilation fails on `tstore`/`tload`.

**Deliver the test, not a transcript.** Name the runnable path and the one-line command
(`forge test --match-contract <Name> -vv --rpc-url <rpc>`) plus the verbatim output. A triager
re-running it themselves is the strongest acceptance a finding can get, and it also makes your
own later re-verification free.

---

## 3. Non-negotiable habits

- Cross-check your decode against the explorer's `decoded` fields. Disagreement means you
  are wrong -- find out why before writing anything.
- Report the real revert string. A permission revert means one thing; a business-logic
  revert ("Invalid proof") means the earlier gate passed. Never collapse the two into
  "access denied".
- Role events invert easily -- decode in spec order. OZ:
  `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` ->
  `topics[1]=role`, `topics[2]=account`, `topics[3]=sender`. Never conclude "payouts stopped"
  from a RoleRevoked without a later event that proves the path is dead.
- Identifiers are not always numeric. Check whether the id is an ASCII string before
  indexing a mapping by integer.
- Scope the vendor audit before invoking "by-design". If the audit covered a different
  component (e.g. a Compound fork while the finding sits in an un-audited reward registry),
  then "already audited" does not apply -- but the finding still does not become Critical.

---

## 4. Honest severity floor for trust-model findings

A capability that requires already-privileged access is a trust-model note, never a
severity-inflated exploit. The residue after false positives are removed is typically:

- A privileged escrow whose payout validation is delegated downstream (no per-recipient proof
  at the registry layer) -> Low/Medium trust assumption, not an exploit -- no attacker
  capability was demonstrated.
- A privileged role held by an unverified deployed contract -> transparency gap -> Low.
- All roles in one EOA, no multisig -> Info unless the program scopes it.

Standing user rule: severity inflation is omong kosong -- a blocked exploit chain is
informational, never HIGH or CRITICAL. State plainly when a finding dies.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Reproduksi PoC di fork block lokal (`anvil --fork-url`) — bukan simulasi di kepala | Klaim tanpa eksekusi = hipotesis |
| 2 | Attacker P&L eksplisit: `claim − (initial + injected + gas)` dihitung, bukan diperkirakan | "Missing slippage" terlihat seperti theft tapi sering net ~0 |
| 3 | Bytecode-vs-source selector diff pada alamat yang dipakai PoC | PoC bisa jalan terhadap kode yang sudah tidak deployed |
| 4 | Partial-solution control: kirim solusi yang cocok sebagian (prefix N byte) → harus DITOLAK | do.de lesson: partial match diterima = klaim "server verify cuma N byte" palsu |
| 5 | Negative control: kirim input invalid/sentinel ke endpoint sama → harus gagal | Tanpa negative control, "bug" bisa saja by-design |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

### Per-class proof bar — what the RESULT must show, per class

Probes tell you what to test; they do not tell you what a passing result has to contain. That
per-class bar lives in `references/class-proof-bars.md` — vault inflation, modular accounts,
signed approvals, AMM hooks, restaking/LRT, intent settlement, oracle/L2, upgradeability. Read
the row for your class **before** drafting severity. It carries the measured numbers from the
2026-10-27 eight-suite calibration lab, including three claims that were wrong as originally
written.

### Calibration corrections that apply to every class (measured 2026-10-27)

- **State victim loss, not attacker gain.** In the lab the classic donation inflation nets the
  attacker **50% of the donation** while the victim loses **100% of the deposit**. A report
  saying "attacker steals N" is refutable — the triager points at the attacker's own capital
  outlay. The number that belongs in the report is the victim's loss.
- **A severity claim needs the exploit's second path, not just the defect.** "Nonce incremented
  after the external call" is real and measurable (the nonce is still the old value *inside* the
  call), but a naive reentrant `execute()` **fails**, because the re-entrant `msg.sender` is the
  callee and not the owner. Exploitation needs a path carrying the same `msg.sender`
  (entryPoint-batched executes, multicall delegatecalling back). Without that path the replay
  claim is refutable — say "ordering defect, exploitation requires X" instead.
- **Verify the interface of your own mock.** A mock whose return shape is simpler than the real
  feed makes checks pass falsely: a 2-tuple uptime mock reads `startedAt` as 0, so
  `block.timestamp - 0` always exceeds the grace period. Chainlink's uptime feed is a **5-tuple**.
  Before concluding a consumer is safe, confirm the shape you mock is the shape that ships.
- **A guard that fires for a coincidental reason is not a guard.** A consumer with `answer = 0`
  zeroes out `maxBorrow` and looks safe; `answer = -1` cast to `uint256` underflows. It never
  checked `answer > 0` — it survived by arithmetic accident. Absence of an exploitable *outcome*
  is not presence of a *control*.

## 2026 sweep (verification yang masih jadi jebakan)

- **Precomputed challenge reuse** — kalau challenge di-cache, accepted run bisa jadi full-prefix match sementara klaimmu soal partial match salah. Selalu uji partial yang TIDAK cocok prefix penuh.
- **Second-wallet claim tanpa capture** — jangan klaim "verified against a second wallet" kalau capture-nya sudah hilang. Re-capture atau turunkan klaim.
- **Route-family auth asymmetry** — "endpoint tetangga 401" BUKAN bukti access-control gap kalau dua route family didokumentasikan beda (`security: required:false` vs `required:true`).
- **SimulateTransaction rollback** — Solana `simulateTransaction` menjalankan instruksi lalu rollback; pakai untuk hipotesis yang kalau tidak akan butuh transfer nyata.
- **By-design vs bug pada single-party pool** — OTC pool dengan satu `lender` address: write-off jatuh ke orang yang sama yang ambil NFT. Kill claim sebelum difile.


## Critical severity anchor (apa yang membuat temuan dari skill ini Critical)

Skill ini adalah **gate**, bukan penghasil temuan. Yang membuat temuan yang lolos gate ini
Critical adalah kalau PoC-nya membuktikan:

| Bukti di PoC | Severity |
|---|---|
| `assertEq` pada balance victim yang turun / balance attacker yang naik | Critical |
| Mint share/token arbitrer | Critical |
| State corruption yang membuat protokol insolvent | Critical |
| Eksploit yang butuh asumsi admin jahat | Info (kebanyakan program mengecualikannya) |
| Rantai yang mati di link 1 | **informational** — severity inflation adalah omong kosong |

**Kalibrasi wajib:** blocked exploit chain = informational, never HIGH or CRITICAL. Kalau PoC
tidak bisa dijalankan sebagai satu `forge test`, turunkan severity. Kalau attacker P&L net ~0,
itu hardening note.
