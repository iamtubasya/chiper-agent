# Reference-implementation differential review (ports / forks / reimplementations)

Technique + worked case. Use when the in-scope target is a port or fork of a known upstream.
Finding one real bug in a heavily pre-audited codebase came down to this — after the memory-safety
surface had been cleared by its own KAT harness.

## Why it works

A port's comments cite its upstream constantly ("Ported from RenzoDD/digiasset-core BitIO.cpp",
"confirmed vs digiasset-core DigiByteTransaction.cpp:257-329"). Those citations are a ready-made
function↔function map. A faithful port is boring; the interesting question is only **where it
stopped being faithful**.

## Recipe

1. **Locate the reference** — grep the target for `Ported from` / `confirmed vs` / `see <f>.cpp:`.
2. **Clone it** (`git clone --depth 1`).
3. **Pair the units**, then compare only what can differ:
   - bit/field widths
   - **condition scoping** — does the guard carry the operation / type / version?
   - loop stop conditions
   - defaults
   - overflow behaviour
4. **Prefer a divergence the port ALSO contradicts itself on** — strongest, pre-empts "by design".
5. **Check test coverage of the divergent branch** — grep the test tree for the flag/construct; if
   the tests only hit one branch, the divergence is uncovered.
6. **Write it as two-sided citations + a simulation.**

## Worked case — DigiByte Android wallet, DigiAsset decoder (2026-10)

Target: `JohnnyLawDGB/digibytewallet-android` v4.0.87 (bug-bounty, source-only track).
Reference: `RenzoDD/digiasset-core`.

**Divergence (F4).** In DigiAsset v3, a non-range transfer instruction whose output field is 31 is
the destroy/burn marker. The reference scopes that meaning to the BURN operation only:

```cpp
// ref-core/src/DigiByteTransaction.cpp:317
if ((type == DIGIASSET_BURN) && (!range) && (output == 31)) {
    // burn asset so do nothing
} else {
    size_t startI = range ? 0 : output;
    ...
    for (size_t vout = startI; vout <= output; vout++) addAssetToOutput(vout, removedAsset);
```

The port drops the operation guard:

```kotlin
// core/src/main/java/io/digibyte/core/asset/DigiAssetDecoder.kt:241
val burn = !range && output == 31          // `operation` is passed in but used only for footerBits
...
isBurn = burn
```

…and the crediting path trusts that flag, so the instruction is dropped while its amount is still
counted as consumed:

```kotlin
// AssetTxQuantity.kt:40  (forOutput, TRANSFER)
.filter { !it.percent && !it.isBurn }      // credited 0
// AssetTxQuantity.kt:139 (targetsOutput) — the SAME marker, correctly scoped
val destroyMarkerApplies = header.operation == AssetOperation.BURN
```

**Internal contradiction:** the crediting path (40) and the protection path (139) disagree about the
same output. **External divergence:** the reference credits `amount` to output 31 in a transfer.

**Simulation** (re-implement both branches, print the totals) — TRANSFER, 32 outputs, input 100,
instruction `output31 = 70`:

```
                 output31 credited | implicit change | total credited
  wallet v4.0.87          0        |        0        |       30
  reference              70        |        0        |      100
  units unaccounted for by the wallet: 70
```

**Coverage gap:** `AssetImplicitChangeTest` only builds `outputIndex = 31` with `isBurn = true`
(tests at lines 69 and 118 hardcode the flag, and line 114 uses `operation = BURN, opcode = 0x25`).
The TRANSFER + output-31 path is never exercised, so CI is green.

**Severity, honestly:** LOW. The direction is fail-closed (the wallet under-counts rather than
invents), it needs a transaction with ≥32 outputs, and there is no theft. It is a silent
disagreement with every other implementation about who owns what, in the quantity-attribution path
the program names as paid.

### Second divergence in the SAME function — the ERROR path (F5, HIGH)

F4 came from the reference's *success* semantics. The bigger bug came from re-reading the same
function for its *error* semantics. The reference applies instructions one at a time and **aborts
the whole transfer** if any instruction names an output the transaction does not have:

```cpp
// ref-core/src/DigiByteTransaction.cpp
322:  if (output >= _outputs.size()) {
323:      throw DigiAsset::exceptionInvalidTransfer();
324:  }
...
336:  } catch (const std::exception& e) {
338:      for (AssetUTXO& vout: _outputs) {
339:          vout.assets.clear();               // EVERY output's credit is discarded
340:      }
342:      inputs.clear(); ...                    // inputs restored in full
344:      break;
...
354:  size_t lastOutput = _outputs.size() - 1;   // all remaining input units -> LAST output
```

The port credits each owned output independently and has **no whole-transfer validity step**:

```kotlin
// AssetTxQuantity.kt:40-43   forOutput, AssetOperation.TRANSFER
.filter { !it.percent && !it.isBurn }
.filter { inst -> if (inst.range) vout <= inst.outputIndex else inst.outputIndex == vout }
.sumOf { it.amount }
// AssetManager.kt:978 — forOutputTotal persisted with no output-count validation anywhere
```

**Simulation** — 3 outputs (0 = recipient, 1 = OP_RETURN, 2 = last/sender), 15 units in,
instructions `{output 0, amount 10}` and `{output 5, amount 5}` (index 5 >= 3):

```
  0  :       10                0  <- recipient
  1  :        0                0  <- OP_RETURN
  2  :        0               15  <- last/sender
```

The wallet credits the recipient 10 units the chain places at the sender's last output — a
**false-positive receive**. Reachable because the non-range output field is 5 bits (any value past
the real output count triggers it) and an OP_RETURN is consensus-valid data that mines normally;
DigiAsset semantics are applied by indexers off-chain, so the transaction is real while the port's
view of it is wrong.

**Severity, honestly:** HIGH per the program's own taxonomy ("wallet credits the user without
on-chain backing"), unlike F4's fail-closed LOW. Proven at source level against the reference
version the port's own comments cite (they cite `DigiByteTransaction.cpp:257-329`, which contains
line 322); end-to-end indexer confirmation would need a running reference node and was therefore
**not** executed — state exactly that rather than implying it was.

**Takeaway worth keeping:** having found one divergence in a function is a reason to re-read that
function for its *abort* branches, not a reason to move on. Same reference function, same technique,
and the error path was the exploitable one.

### Third divergence in the same family — a DIFFERENT invalidation trigger (F6, MEDIUM)

F5's trigger was an instruction naming a non-existent output. The reference has **more than one** way
to invalidate a transfer, and each is its own divergence candidate. The second trigger is the rules
check: `checkRulesPass()` runs on every non-issuance transfer and throws on any rule failure, and the
caller's handler clears every output.

```cpp
// ref-core/src/DigiByteTransaction.cpp:382
if (type != DIGIASSET_ISSUANCE) checkRulesPass();
// DigiAsset.cpp:796                       if (_rules.empty()) return;   // rule-free asset passes
// DigiAsset.cpp:841/873/887/893/899/911   throw exceptionRuleFailed("Signers"/"Royalty"/"KYC"/"Expiry"/"Vote"/"Deflation");
// back in decodeAssetTX:  catch(exceptionRuleFailed) -> for (_outputs) assets.clear(); return;
```

The port enforces rules on the **write** path only — `transferRuleState(...)` is consulted in
`sendAsset` (AssetManager.kt:2344) and in the recovery classifiers — but nothing on the **credit**
path (`processIncomingAssetTx` → `AssetTxQuantity.forOutputTotal` → `persistDetectedAssetOutput`)
evaluates rules at all, so it credits a rule-bound asset's transfer the reference wiped.

**The reusable pattern this exposes:** a control the port enforces on the WRITE/send path but **not**
on the READ/credit path is a bug class by itself. Grep every gate the port applies before *acting*,
then ask whether the same condition also governs *accepting* state. Note also that "the port refuses
to send it" did **not** close the finding — it caps the severity, it does not remove the divergence.

**Severity, honestly:** MEDIUM, not HIGH. Same false-positive-receive shape as F5, but the port
classifies the asset RULE_BOUND and refuses to send it, so the phantom balance is inert; what remains
is display integrity plus scam framing. State the mitigating factor; do not promote it to HIGH.

### Enumerate ALL of the reference's invalidation triggers — make it a checklist

Finding F5 is a reason to *enumerate*, not to stop. Walk every abort path in the reference function
and ask, for each, what the reference's state is afterwards and whether the port models it:

| Trigger class | Reference behaviour | What to check in the port |
|---|---|---|
| argument / instruction invalid (index out of range, bad count) | abort, clear all outputs, inputs → last output | is there any whole-transfer validity step? (**F5**) |
| rule / permission failure | abort, clear all outputs | does the **CREDIT** path run the rule check, or only the SEND path? (**F6**) |
| pre-classification precedence (the tx is a *different* kind) | a separate handler runs and `return`s early, so the asset path never runs | does the port pre-classify, or treat every magic-prefixed payload as an asset tx? |

The third row is a real shape — the reference checks `decodeKYC` / `decodeExchangeRate` **before**
`decodeAssetTX` and `return`s early — but reachability was **not** established: a misclassification
needs the exchange-rate matcher to fire, which requires `vout.size()==2`, output[1] to be a known
watch/exchange address, and a data length that is a multiple of 8 bytes. **Record it as an unproven
candidate, not a finding.** Handling an unproven trigger well = name it, state the gate that stopped
you, and stop; that is a deliverable in itself (it tells the next pass where to look) and it is what
keeps the report's claims honest.

## Candidates that DIED on the same pass (record as verified negatives, don't report)

- **"The parent-walk follows `input[0]` and could name the wrong asset."** Dead: `input[0]` *is* the
  convention — `AssetDuplicateDetector.kt` states the asset id is derived from `input[0]` of the
  issuance. The port is consistent with the protocol.
- **"`implicitChangeVout(outputCount)` points at the wrong output."** Dead — but **not** for the
  reason the port's own comment implies. `outputCount` is `outputLines.size`, and reading the native
  enumerator (`native/.../jni_asset.c`, `getTransactionOutputsForHash`) shows it emits **all**
  outputs, `for i in 0..tx->outCount`, with **raw** indices — the OP_RETURN is *included*, at its real
  vout. So `outputCount == _outputs.size()` and `outputCount - 1` is exactly the reference's
  `_outputs.size() - 1`. (The comment saying callers "exclude the OP_RETURN" describes the per-output
  *iteration*, not the list length.) The verified negative stands; the *reason* is corrected here
  because the wrong reason would mislead a future pass — **read the bridge, not the comment, to
  settle an index-space question** (recipe step 8).
- **"`mantissa * pow10(exponent)` can overflow Long."** Dead *as a finding*: the reference's
  `BitIO::getFixedPrecision` returns the same `uint64_t` multiply with identical wraparound. Matches
  the reference → not a divergence.

## Also check

- A port shipping `#ifndef WIRE_COUNT_BOUNDS_UNFIXED`-style KAT flags and per-count `invariant:`
  comments has already hardened that surface. Skip re-deriving memory-safety; hunt LOGIC
  (attribution, scoping, ordering, which-entity) instead — the flags don't cover it.
- Cite the reference line number in the finding. It converts "I think this is wrong" into "your
  implementation disagrees with the implementation your own comments cite".
