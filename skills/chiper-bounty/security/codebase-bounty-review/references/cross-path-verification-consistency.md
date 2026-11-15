# Cross-path verification consistency (a sibling path already verifies it)

Companion to PART 8 item 11. The shape: the codebase **has** a verification norm, applies it on one
path, and skips it on a sibling path that consumes the same datum. This is stronger than an
external-reference divergence because the contrast is internal — "by design" is dead on arrival,
and the fix is a line the project already wrote somewhere else.

Worked case below is a real finding (F9, 2026-10, Android SPV wallet — HIGH, false balance).

## The technique

For any datum that drives a **state write** (a balance, a ledger row, a confirmation height, an
attribution), enumerate every function that obtains it, and check they all verify it the same way:

```bash
# every consumer of the datum
rg -n "register|import|reconcile|fetch" --type kotlin --type c core/ native/
# then read each one's transport-of-trust: is the bytes→id (or value→proof) link checked?
```

Cheap tell: **the project already documented the rule for one path.** A comment like *"accepted
only when its bytes hash to the id asked for"* sitting in one file is your argument for the other
file — quote it beside the unguarded call.

## Worked case — F9 (DigiByte Wallet v4.0.87)

**Checked paths (the norm):**

```
ChainReconciliationService.kt:277-290   fetchTransactionBytes
  /** The first source whose bytes hash to [txid]; when none does, the last bytes any source
   *  gave (the walk then rejects them), or null. */
  if (NativeBridge.rawTransactionId(bytes)?.lowercase() == txid.lowercase()) return bytes
```

`MultiEndpointAssetClient.getRawTransaction` mirrors it (`transactionIdOf(raw) == requested`,
else the endpoint is counted as failed and the next one is tried).

**Unchecked path (same file, different flow):**

```
ChainReconciliationService.kt:377    fetch = { tx -> nodeClient.fetchRawTx(tx.txid, tx.height) }
ChainReconciliationService.kt:507-511
    val raw = fetch(tx)
    val bytes = decodeHex(raw.hex) ?: continue
    if (register(bytes, raw.blockHeight, raw.blockTime)) { imported++ }
        # no comparison of bytes against tx.txid anywhere

native jni_transaction.c:535  Java_..._registerRawTransaction(env, rawTx, blockHeight, blockTimestamp)
    # signature has NO expected txid
    tx->blockHeight = (uint32_t)blockHeight;   # caller-claimed
    tx->timestamp   = (uint32_t)blockTimestamp;
    int ok = BRWalletRegisterTransaction(g_wallet, tx);
```

`registerRawTransaction` requires only *signed* + *associated with a wallet address*; it registers
under the hash of whatever bytes arrived, at the height the caller supplied. Nothing later removes a
registered tx, so its outputs enter the balance.

**Result:** an answer whose bytes are not the planned transaction — a lying node, or any endpoint
that misroutes or bugs — becomes a confirmed transaction the chain does not have. False DGB
balance; the outputs are unspendable network-side, so the harm is a balance the user acts on.

## Two reusable rules from it

1. **A missing parameter is structural.** The leaf function had no argument for the expected
   identity, so no call site could check it. Write the fix as *add the expected txid to
   `registerRawTransaction` and reject a mismatch there* — a caller-side comparison leaves the next
   caller to reintroduce the hole. (Contrast with the more common "add the `if`" fix, which is
   right only when the leaf already receives what it needs to compare.)
2. **Where to look first: reconcile / recovery / re-import / repair flows.** They are written as
   best-effort bulk re-ingestion — the optimistic "just re-import it" shape — which is exactly where
   a verification norm from the primary path gets dropped. Grep for functions taking a **claimed
   height / index / position** alongside the payload; a caller-supplied position is the tell that
   the value is trusted rather than derived.

## Severity framing (who must misbehave)

State the gate explicitly, because it decides the tier:

- the answer only needs to *differ* from what was asked ⇒ a buggy/desynced node produces it as
  readily as a hostile one ⇒ the severity does **not** rest on an adversary (F9: HIGH).
- the datum comes from a cert-pinned first party that must actively lie ⇒ MEDIUM (F8, see
  `references/trust-boundary-source-asymmetry.md`).
- **verify the pinning before claiming a MITM path** — grep the pins (`*Pins.kt`, `CertificatePinner`)
  rather than assuming an unauthenticated network attacker.

## Reporting shape

Cite the checked sibling and the unchecked sibling side by side, then the leaf's signature. Reading
order that lands: *"you already made this exact point about the other fetchers; this is the one that
was missed"* — followed by the concrete fix on the leaf. The same-datum/different-path contrast
also pre-empts "the node is the user's own / trusted anyway": a verification that only exists to
defeat malice is still skipped by a bug, and the project wrote the check for that reason.
