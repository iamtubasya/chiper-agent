# Source-code audit: the same false-negative class, applied to a Rust/FRAME repo

Section 2a of the parent skill covers web probes. This file covers the **source-code**
form, learned on a Substrate pallet audit where a truncation bug made a 138 KB file look
like a clean negative.

## The truncation that fabricated a "no findings"

To drop test modules from a Rust pallet, the obvious move is:

```python
body = re.split(r"#\[cfg\(test\)\]", src)[0]     # WRONG
```

FRAME pallets declare their test modules at the **top** of the file:

```rust
#[cfg(test)]
mod mock;
#[cfg(test)]
mod tests;

pub mod slashing;
// ... 138 KB of real logic, 39 extrinsics ...
```

So the split returned **903 bytes** for a file containing the actual bug. Every grep
afterwards reported zero hits and the run read as a clean negative. The finding was only
recovered because a later check compared byte counts.

```python
m = list(re.finditer(r"#\[cfg\(test\)\]", src))
body = src[:m[-1].start()] if m else src          # LAST occurrence, not first

assert len(body) > 0.5 * os.path.getsize(path), \
    f"truncated at header: {len(body)} vs {os.path.getsize(path)} bytes"
```

**Generalise it:** any time a negative depends on "not found", assert how much you
actually scanned against the source of truth's size.

## Two more silent-zero traps in the same session

| artefact | how it lies | gate |
|---|---|---|
| shell `grep -rn "for .* in .*::<.*>::iter"` under MSYS bash | returns 0 and reads as "no unbounded loops" | use Python `re`, not shell grep, for `::<T>::` patterns |
| `ls -la \| awk '{print $5,$9}'` | column 5 is bytes, not a file count | `wc -l` |
| `ExtBuilder::default()` in a crate that only has `new_test_ext()` | test fails to compile → looks like a target problem | read `tests.rs` imports before writing a test in a new crate |

## Coverage vocabulary that survives review

An operator's complaint — *"cepat sekali menyerah nya"* — was factually correct: the
closing statement said "nothing payable" while the artefact still listed untested surface.

Use three states, never two:

```
diuji                -> executed, artefact on disk
BELUM — hard gate    -> unreachable for a named structural reason (KYC, device signature, OOS)
BELUM                -> MUST NOT appear in a closing statement; go run it
```

If a reviewer can point at a line in your own notes you did not execute, the coverage
claim collapses regardless of how many tools ran.

## Sequencing that produced the real finding

1. Web surface exhausted behind a gate you cannot pass (email verifyCode / OAuth only).
2. **Pivot to the source-available component rather than stopping** — the chain repo needs
   no account.
3. Recon the repo by LOC + money-touching pallets, then list extrinsics via
   `#[pallet::call_index(` not by reading functions.
4. Grep classes in priority order, keeping a **reject table** with the killing fact for
   each dead lead (nine died in one pass; recording *why* is what makes the remaining one
   credible).
5. PoC in the mock runtime, printing measured numbers.
6. Gate the audited commit against the deployed runtime version before drafting.

Step 2 is the transferable move: when the paid surface is account-gated, look for a
component of the same product that is source-available — chain repo, SDK, open-source
client, published runtime WASM. Those have no signup gate.
