# Reviewing circom circuits and zkVM guests on a source-available protocol

Use when the target's state transitions are **proven** rather than merely executed: circom + Groth16 /
Halo2, an SP1 / RISC Zero guest verifying BN254 proofs on-chain, an immutable pool whose docs claim
"validity from data alone". Worked end-to-end on Tacit (2026-10-27): ~20 vendor-run audit reports on
the immutable surface, so the productive angle was *not* re-reading what they had already read.

## 0. Rank the four layers before reading anything

| layer | what lives there | why it matters |
|---|---|---|
| zkVM **guest** (Rust) | the real semantics of every op | proof forgery lives here; also the least-reviewed code |
| **circuit** (.circom) | constraints on the witness | under-constraint = a prover picks its own inputs |
| **contract** (Solidity) | re-decodes the public values | cheap to review, usually correct — spend little time |
| **JS indexer** | a *second* implementation of the same rules | divergence between the two is a mintable bug class |

A repo that says "where this document and the reference implementation disagree, the implementation
wins" is telling you two implementations exist. Diff them op by op; that instruction is a bug magnet
dressed as a spec rule.

## 1. Read a live target that will not compile

Cutting-edge repos pin a compiler that is not released yet (`pragma solidity 0.8.36;` / `0.8.37` →
`forge build`: *"No solc version exists that matches the version requirement"*), which takes
slither / aderyn / mythril / echidna off the table for the whole tree. Do not stop: derive everything
from the live chain plus the source text.

**Revert selector → the declared custom error.** A live `eth_call` returns
`error code 3: execution reverted, data: "0xa889a81f"`. Hash every `error Name(type,...)` declared in
the repo and match the 4-byte selector — that names the contract *and* the reason, in one pass:

```python
from Crypto.Hash import keccak as K
def sel(sig):
    h = K.new(digest_bits=256); h.update(sig.encode()); return "0x" + h.hexdigest()[:8]
# per file: re.finditer(r"error\s+(\w+)\s*\(([^)]*)\)\s*;", src) -> "Name(type1,type2)"
# then: sel("TooFewSamples()") == "0xa889a81f"
```

`cast sig "TooFewSamples()"` cross-checks a single candidate. This turned an opaque hex blob into
*"an interval oracle whose price window is empty"* — then §2 measures **why** it is empty (stale ring
vs never recorded; they are different findings). Write the selector→error
map into the evidence file: it is what makes a revert reproducible for a triager.

## 1b. A "cannot compile" target may still be EXECUTABLE — look for a pure crate

`solc` being unreleased blocks the *Solidity* tree. It does not block the crypto. In these repos the
verification math almost always lives in its own crate with **no zkVM dependency** (comment like *"no
SP1 deps, so it `cargo test`s natively against fixtures"*), and that crate is a direct dependency of the
guest — so testing it **is** testing the guest's semantics.

```bash
cd contracts/sp1/confidential/cxfer-core
cargo test --release          # 214 passed on Tacit; the whole verification core, natively
```

Then write your own adversarial tests against those real functions (`tests/adversarial_*.rs`). This is
the difference between "I read `verify_clearing` and the comments look right" and "here is an executable
proof it rejects inflation". Keep them in the repo's own crate so `cargo test` runs them and the
submission carries a script a triager can execute.

⛔ **Every negative test needs a POSITIVE CONTROL, or the file proves nothing.** A verifier that always
returns `false` passes every "rejects X" assertion. Assert the honest construction first and fail loudly
if it does not verify, then the negatives have meaning. My first version of the Tacit suite had two tests
that were *passing for the wrong reason*; the positive controls caught both:

- **Structurally wrong side.** I asserted the asset-A aggregate identity would catch an inflated
  *asset-B* receipt. It cannot and should not: the A-side sum only sees A inputs and A outputs, so an
  unrelated B receipt is invisible to it. The real guard is the B-side check. Fixing the construction
  turned a false negative into a true positive-coverage result.
- **Invalid construction with no discrete log.** I signed a Schnorr kernel with `delta=600` while the
  input was `1000`, so the excess carried a `400·H` component and no `dlog` existed. The verifier was
  right; my witness was impossible.

Both read as "the code rejects it" — the correct conclusion from a broken test is *nothing*, so state
the control explicitly in the test and in the evidence log.

The suite worth writing for an AMM/note protocol, each with its control:

| invariant | positive control | negatives that must fail |
|---|---|---|
| one note ⇒ one nullifier | honest spender derives ν | ν ≠ leaf-bound scheme; only 1 of 256 candidate secrets satisfies `owner == H(nk‖dom)` |
| aggregate conservation | both asset sides verify | delta ±1; an output inflated 100× on *each* side; wrong blinding excess; receipts reordered vs intents |
| blind kernel = knowledge proof | honest Schnorr verifies | wrong `z`; the *same* signature under another `pool_id`; under another `chain_binding` |

Also grep for the *choke point*: if one helper selects the nullifier scheme (`native_input` /
`native_nu`), confirm every value-bearing path calls it, and that the only direct `nullifier(leaf)`
call sites are lanes the contract pins to a specific root (Tacit: `bridge_mint` /
`bridge_stealth_mint`, gated on `knownBitcoinRoot`), so a native leaf can never reach them.

## 2. Read-path liveness sweep — the class source-only review cannot see

Every reviewer reads the *write* path. The freeze lives in the *read* path.

1. For each money-path function, list every external `view` call it makes (`withdraw` → health check →
   `prices(window)` → `depthMin(...)`).
2. `eth_call` each of those reads against the **live** deployment, at a known block.
3. A read that reverts is a path that is **already frozen**. That is not a hypothetical.

Worked case: a proof-based interval oracle whose `latest()` returned 0 on both venues and whose
`prices()/depthMin()/recovery()` all reverted → on both live vaults `withdraw` (any open debt),
`borrow`, `liquidate`, `cancel`, third-party `bid` and `redeem` all reverted, while `deposit` and
`repay` still worked. Collateral could only be released by repaying in full, and the liquidation
engine was dead.

⛔ **Prove empty vs transient — and DO NOT trust an accessor sweep to do it.** An earlier version of
this file recommended a `sampleOf(expected_interval)` sweep as the proof. **That recipe is wrong and it
produced a false negative on Tacit.** It "proved" the ring was empty; the ring was in fact **128/128
populated with stale samples**, 541 intervals (3.76 days) behind on one venue and 1,053 (7.31 days) on
the other. Those are different findings, and the wrong one is what you get for free if you only call
accessors.

Why it lies: a ring store is indexed by `interval % RING`, and `sampleOf(i)` returns `(0, 0)` unless the
slot currently holds interval `i` (`_has(s,i)` → `s >> 208 == i`). Probing the indices you *expect*
therefore lands on slots holding *other* intervals and answers zero however full the ring is. The sweep
is anchored to the wrong end: **physical slot order ≠ interval order.**

Correct method — dump the storage, decode it, then compute the age:

```bash
for i in $(seq 0 127); do cast storage $ORACLE $i --rpc-url $RPC; done   # no accessor involved
```
```python
# packed layout taken from the source: interval << 208 | value << 104 | depth
v = int(slot_hex, 16)
interval, value, depth = v >> 208, (v >> 104) & ((1 << 104) - 1), v & ((1 << 104) - 1)

newest   = max(intervals)                          # newest record ACTUALLY in the ring
expected = (block_number - 1 - GRACE) // STEP - 1  # the interval the contract would price at
behind   = expected - newest
age_days = behind * STEP * 12 / 86400
```

Then confirm the boundary with two accessor calls **at the right intervals**: `sampleOf(newest)` must
return a real sample and `sampleOf(newest + 1)` must return zero. That pair is a genuine proof that
recording **stopped**; a sweep over expected indices is not.

Say "recording stopped N days ago", never "the oracle has no samples". The age is what makes it Medium
rather than Low, and it is what tells you whether the back-fill window (`RING`) is already blown.

Then read the acceptance rule for *why it cannot self-heal*: `record()` refusing intervals older than
`RING` (here 128 intervals ≈ 21 h) means a gap longer than that can never be back-filled, and a
`depthMin()` that requires `n == points` (100 % coverage) means one missed interval disables borrow
until it ages out. **An unrecorded window with no mandatory recorder is a permanent defect even if the
current outage turns out to be transient** — say that split out loud in the report and let the vendor
classify the ops side.

Severity framing: collateral freeze + halted liquidation, no fund loss → Medium, and concede Low if
they show the recorder is a monitored component. The structural part (`depthMin` full coverage +
non-repairable history) is what survives that argument.

## 3. Circuit checklist

Each item is a real under-constraint shape, not a theory list.

1. **Padding slots.** An "empty" slot must be constrained empty (`outV[k] * outEmpty[k].out === 0`,
   same for inputs). Without it a prover smuggles value through a slot the semantics call zero.
2. **Witness ↔ public equality.** Any private witness standing in for a public value needs its own
   constraint (`tip_amount_witness[i] === tip_amount[i]`). Missing = the prover chooses.
3. **Selector booleans.** `direction*(direction-1)===0`, sign bits, `variant`, `is_spot`. Also
   *canonicalise* inert bits (`is_spot * (signA + signB) === 0`) or one statement has two proofs.
4. **circomlib `SMTVerifier` non-inclusion — the known soundness hole.** Its verifier takes `isOld0`
   as *given* and weights the terminal node by `1 - isOld0`. Without an in-circuit
   `smtIsOld0 * (smtIsOld0 - 1) === 0`, a prover picks the terminal node and can present a
   **spent nullifier as absent** (fake non-membership). Grep for that booleanity line in any circuit
   that proves "not yet spent"; its absence is Critical. Also confirm `fnc`, `enabled`, and that the
   looked-up `value` really is constrained to 0.
5. **Range bounds under `LessThan`.** `LessThan(n)` is only sound if the operands are `< 2^n`.
   When the divisor is one of two globals, range-check the globals (`Num2Bits(69)` on `P_num`/`P_den`)
   instead of per-slot — but check *something* bounds them, or `rem < divisor` proves nothing.
6. **Floor division.** `in * mult === out * div + rem` **and** `rem < div`. One without the other lets
   the prover pick `out`.
7. **Aggregate accumulators.** `tipSumA[N_MAX] === tip_A_amount` — watch the off-by-one: a sum taken
   at `[N_MAX-1]` silently drops the last slot.
8. **Public inputs with no constraint — and how to MEASURE it instead of arguing.** The circom source
   often says a public input is deliberately left unconstrained ("modern circom + snarkjs preserves it,
   no explicit constraint needed"). Read that as a hypothesis, never as a fact: if it were true and the
   circuit carried no other binding, a proof for pool X would replay for pool Y.
   ⛔ **The verifying key answers this in one pass, with no prover and no compiler.** A public input
   with no constraint contributes `IC_i = identity` to the key (its `L_i ≡ 0` vanishes), so:

   ```python
   vk = json.load(open('fixtures/<circuit>_vk.json'))
   assert len(vk["IC"]) == vk["nPublic"] + 1
   is_inf = lambda pt: all(int(x) == 0 for x in pt)
   unbound = [i for i, pt in enumerate(vk["IC"]) if is_inf(pt)]   # [] == every public IS bound
   ```
   Map `index i → public signal i-1` (IC[0] is the constant term) and print the table. On Tacit this
   killed my best Critical: the circom comment implied `pool_id_fr` was unconstrained, and since
   `amm_swap_batch` has **no asset signal at all**, `pool_id_fr` was the *only* pool binding — a
   replay hole if the comment were true. Measured: `nPublic=123`, `IC` length 124, **zero identity
   points** → all 123 publics bound, hypothesis dead. Run this before writing a single word of the
   finding, and pin the key file's sha256 against the value the docs/pin file claims.
   ⛔ A confirmed-unbound public is only reportable if you can name what it lets a prover *do*
   (replay across pools, forge a delta, reuse a nullifier). Unbound-but-inert is hardening.
9. **Membership skip.** A slot skipping the Merkle check "because `v == 0`" is fine only if `v` is
   itself constrained; otherwise an attacker sends value 0 with any leaf.
10. **Insertion vs stale root.** The contract must require `oldRoot == current head` and the proven
    `startIndex == nextIndex()`; otherwise two provers fill the same leaf pair.
11. **Nullifier binding.** Confirm `nf = H(secret_nk, leaf, index)` and not `H(leaf, index)` — a
    public-leaf nullifier lets anyone derive it.
12. **Cross-curve sigma.** If a BabyJubJub commitment is linked to a secp256k1 Pedersen commitment
    out-of-circuit, the link must carry a response bound across both groups plus range checks; without
    it the on-chain amount and the proven amount are unrelated.

## 4. Guest checklist

- **Re-derive, never trust.** Find where the guest consumes a public field that it *could* recompute
  (`verify_clearing(...)`, "declared price is the fee-clearing price"). A field the guest accepts
  without recomputation is the whole exploit.
- **Enumerate value-bearing fields per lane.** If the contract has branches like `btcHomed`, the
  branch must bar *every* field that moves value (`withdrawals`, `fees`, `leaves`, `swaps`,
  `liquidity`, `cdp*`, `cbtc*`, `crossOuts`) and record the source nullifier. A new field added to
  the struct but not to the bar is the classic escalation — check the struct's encoded width is
  pinned by a test so a silent addition trips it.
- **"Skips, and never panics on"** is a griefing surface: the skipped op's inputs are still spent on
  the parent chain, so its value is destroyed. Worth a line in the report even at Low.
- **Dual implementation.** Diff the guest's op handling against the JS indexer's for the same opcode.
  Guest-accepts-but-indexer-rejects (or the reverse) is a real bug class, not a style difference.

## 5. What not to report here

- Stated limitations in the vendor's own audit docs ("relayed settles can be front-run", "cBTC is
  economically secured, not custodially guaranteed", "reorg deeper than N halts reflection") —
  by-design, cite them and move on.
- A field that is signed but never validated *and* inert downstream — hardening, not a finding (see
  `oracle-signed-message-and-commitment-review.md` for the discriminator).
- An unreleasable compiler as a finding. It is a **coverage gap**: ledger row reads
  `BLOCKED: pragma 0.8.36 not released → no forge/slither`, never `clean`.

## 6. Reporting shape that survived the audit-heavy vendor

Lead with the *live* measurement (block number, `eth_call` output, selector→error name), then the
source path that explains it, then the value at stake read from chain (collateral, debt, TVL at the
protocol's own spot mark). State the ops-versus-code split explicitly and give them the cheaper
reading. On a target with 20 prior audit reports, credibility comes from "here is chain state you can
re-run", not from another opinion about their code.
