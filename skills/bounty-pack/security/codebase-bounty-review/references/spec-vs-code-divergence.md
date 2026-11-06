# Spec-vs-code divergence — diffing a port against its OWN pinned spec

Companion to `references/reference-differential-review.md` (diff vs an *external* upstream). This file
covers the sibling technique: diffing the code against the **canonical-rule document the repo ships and
cites itself**. It found F7 in a heavily pre-audited Android wallet (2026-10) even after the external
differential had been exhausted.

## Why this works when the external diff is exhausted

A port that reimplements a consensus/wire format almost always ships a spec under `docs/…` (e.g.
`docs/superpowers/specs/2026-07-04-<feature>-wire-format.md`) and **cites it by name in the code**
(`See docs/… for the pinned wire format this implements`, `spec §3.2 Phase B`). Those documents
frequently contain a section header of the form:

    ### 3.2 The association rule — CANONICAL (consensus) — PINNED

with the rule stated in prose *and* pseudo-code, and a citation to the upstream file that settles it
(`digidollar/validation.cpp:264-287`). That gives you, inside one repo:

- a **normative** statement of the rule, and
- the implementation that claims to follow it.

If they differ, you have a finding **without the upstream clone**, and the repo's own comment usually
admits it. Read the comment above the divergent line — that is the confession.

## The highest-yield shape: a counter that advances on a different set of items

For anything with **positional binding / ordinal association** (which of N outputs gets amount[k]),
the danger is not the per-item predicate itself but **which items increment the counter**. A predicate
that is *stricter* than the spec silently drops an item from the counter, shifting `k` for **every
subsequent item** — so the bug is not "one output mis-classified", it is "all later outputs bound to the
wrong slot". Look for `k++` / `idx++` / `dd_output_idx++` and compare its guard against the spec's.

## Worked case — F7, DigiDollar cent binding

- **Spec of record** (in-repo, declared CANONICAL, sourced to `digidollar/validation.cpp:264-287`):
  §3.2 pseudo-code line 308 `if scriptPubKey.size()==34 && scriptPubKey[0]==OP_1:` and the prose
  "THE RULE (state it exactly): … otherwise if it is exactly 34 bytes beginning with `OP_1(0x51)` it is
  a **DD output** whose amount is `dd_amounts[k]`, then `k++`."
- **Implementation**: `BRDigiDollar.c:219`
  `if (o->scriptLen == 34 && o->script && o->script[0] == 0x51 && o->script[1] == 0x20) { … k++; }`
- **The confession**, three lines above it: *"Requiring the second byte too keeps a 34-byte OP_1 script
  that is not that exact form from binding to an amount slot."*
- **Consequence**: a 34-byte zero-value output whose first byte is `OP_1` but second byte is not `0x20`
  consumes a slot in the canonical rule and **no** slot in the port ⇒ every later DD output reads
  `dd_amounts[k]` where consensus reads `dd_amounts[k+1]` ⇒ wrong cents credited ⇒ false-positive balance
  (with `amounts = [a0, a1, a2]`, `a1` large and `a2` small, the recipient's wallet shows `a1` where the
  chain gives `a2`).
- **Severity gate**: the trap output is a **non-standard** script, so default relay policy drops it — it
  reaches a block only if a miner includes it ⇒ **MEDIUM**, not HIGH. Say the gate out loud.
- **Fix framing**: "make spec, comment and code agree" — match the pinned rule, or fix §3.2 and the
  comment and cite the reference line. You do not have to adjudicate which side is right; the
  inconsistency around an ordinal that binds *money to outputs* is itself the defect.

## DigiDollar wire-format facts (from the target's own pinned spec — reusable domain notes)

- Tx identity: `(version & 0xFFFF) == 0x0770` (`DD_VERSION_MARKER`); the **high byte** of `version`
  carries the type — `1 = MINT`, `2 = TRANSFER`, `3 = REDEEM`; anything else is not a DD tx.
- Cent amounts live in the OP_RETURN: `6a 02 44 44 01 <type>` then one minimal-CScriptNum push per DD
  output, **no count field**. MINT/REDEEM → first push only; TRANSFER → all pushes.
- A DD token output is a **zero-value** 34-byte BIP-86 key-path P2TR (`51 20 <32>`). Classification
  REQUIRES the parent tx (marker + OP_RETURN positional correspondence) — a lone `51 20 <32>` output is
  not classifiable as DD by script alone. Never credit a bare zero-value P2TR without its parent tx.
- Binding is by **DD-output ordinal, not raw vout**: skip `OP_RETURN`, skip `nValue != 0`; every
  remaining zero-value output consumes a slot. This is why an asset-less fee-change (P2WPKH, non-zero)
  and a mint's collateral never steal an amount slot.
- Wallets credit DD only when the tx is **confirmed at/above the activation floor** (mainnet
  23627520, testnet 600); unconfirmed is treated as ordinary history. A per-output cap mirrors the
  reference (`DD_MAX_OUTPUT_CENTS = 10_000_000` ← `digidollar/validation.cpp:1150`).
- **Two balance sources, don't confuse them**: the local/native balance drives display AND spend sizing;
  a backend `dd_balance_cents` JSON field was confined to the *recovery-scan* path in the port reviewed
  (appropriate — recovery can only discover a foreign address's holdings from an indexer). Check which
  one the spend path actually reads before writing up a "remote balance trusted" claim.

## Sibling discipline: check the WRITE-path preflight before claiming escalation

A read-path divergence ("the wallet credits units the chain does not") tempts the sentence *"the user
then spends the phantom and their real inputs burn"*. Read the send path **first**. In the same port,
`planAssetTransfer` refuses unless the rule state is `NONE` **and** every asset input is confirmed by an
indexer to hold exactly the recorded asset id and quantity (`AssetInputCheck.judge` →
`VERIFIED` / `MISMATCH`⇒set-aside / `UNAVAILABLE`⇒refuse). So the phantom is unspendable and the burn
chain never materialises.

- A fail-closed gate on the write path **caps severity but does not close the divergence** — report the
  divergence, name the gate, stop short of the escalation.
- If you already wrote the escalation into an earlier report, **surface the correction unprompted** and
  offer an erratum. A false escalation is a credibility loss with the triager even when the divergence
  itself is sound.
