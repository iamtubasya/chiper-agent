# Harness artifacts read as target defects (and the reverse)

Every item below happened in ONE engagement (relay-settlement, 2026-10-08). Eight times I formed
a conclusion and said it out loud before checking the thing that decides it. Seven were caught
only by running a control. The pattern is not "be more careful" — it is that **a failing test,
a compile error, and a stopped log are all ambiguous between "the target is broken" and "my rig
is broken", and the rig is the far more likely cause at the start of an engagement.**

Write the disambiguation into the workflow, not into your intentions.

---

## 1. Control fails → suspect the harness BEFORE the target

Reproducing the deposit-address trigger, the control failed:

```
[FAIL: control: a normal trigger must be accepted]
[PASS] test_B_callerChosenOracleAccepted
[PASS] test_C_sameOrderIdTriggeredTwice
```

Two "real" tests passing while the control fails is the signature of a broken rig, not a
vulnerability. Cause: I passed a **bare EOA address** as the pricing oracle.
`IPricingOracle(eoa).resolveUsdPrices(...)` *succeeds* and returns **empty returndata**, so the
solidity-side `abi.decode(..., (Price[]))` reverts. The contract was fine; my fixture was not.

Fix: substitute a real contract (transcribed oracle) and the control passes, which is what makes
B and C evidence.

**Rule:** never cite a test that shares a rig with a failing control. Get the control green
first; only then does a non-control failure mean anything.

**Common harness-vs-target confusions on EVM:**

| symptom | harness cause to eliminate first |
|---|---|
| call to target reverts in the fixture but not on-chain | you passed an **EOA** where a **contract interface** is expected → empty returndata → decode revert |
| decode revert on a `try`-style path | your ABI encoding of the struct differs (tuple vs flat) — re-derive from the interface file |
| `Stack too deep` / `Yul exception ... too deep in the stack` | **your** `optimizer` is off. The vendor's `foundry.toml` usually sets `optimizer = true` |
| token transfer reverts in test only | you used a `MockERC20` whose approve/transfer differ from the real one |

## 2. A compile error is not a finding until you compile with THEIR settings

`Sha512.sol` failed to build in my project:

```
Error: Yul exception: Variable zero_array_uint64_mpos is 1 too deep in the stack
```

That reads like a genuine defect. It was my config. The repo's `foundry.toml`:

```toml
optimizer = true
optimizer_runs = 200
solc_version = "0.8.28"
bytecode_hash = "none"
cbor_metadata = false
```

With those, it compiles clean. **Read `foundry.toml` and mirror it into your scratch project
before you characterise any build failure.** `optimizer` is not decoration — it performs the
stack-to-memory spilling that makes deep-frame functions compile at all.

## 3. Their own test suite is the strongest evidence, and it is often runnable in isolation

Do not re-implement the vendor's tests. Lift the file that has no external deps and run it:

```bash
# Sha512.t.sol only needs forge-std, so it runs inside MY project
cp <repo>/contracts/payload-builders/utils/Sha512.sol        poc/src/o2/
cp <repo>/test/PayloadBuilders/Sha512.t.sol                  poc/test/o2/Sha512.repo.sol
sed -i 's|"../../contracts/..."|"../../src/o2/Sha512.sol"|'  poc/test/o2/Sha512.repo.sol
forge test --match-path "test/o2/Sha512.repo.sol"
#   -> 11 passed  (test_empty, test_len111_singleBlock, test_len112_twoBlocks,
#                  test_len127, test_len128_fullBlockPlusPadding, test_len129, test_nistTwoBlock …)
```

Note which vectors matter: **the padding boundaries (111/112/127/128/129) are where a
hand-rolled SHA-2/Keccak actually breaks.** "Some tests pass" is not the claim; `N/N including
the boundary vectors` is.

A reproduced vendor test suite beats your own reading — and it is cheap. Check whether a test
file is dependency-light enough to lift before deciding to hand-verify.

## 4. A log that stops growing is NOT a dead run

I reported "pipeline died at PHASE 0C-C6" to the user, twice, with a RAM analysis on top. It had
**completed** — the state file said `completed=[0A,0B,0C,0D,0E,0E-REVIEW,0F]` and the log's last
line was `AUDIT PIPELINE COMPLETE`.

What I had done: read the tail at a moment when the run was between phases, and treated a
snapshot as final.

Disambiguate before ever saying "it died":

```bash
# is the process still there?
wmic process where "commandline like '%<script>%'" get processid
# are the ARTIFACTS still appearing? (growth = alive, even if the log is quiet)
ls -lat "$WORKDIR" | head
# does the STATE tracker say completed?
grep -E "STATE saved|COMPLETE|^=== EXIT" "$LOG" | tail -3
```

Evidence counters rising during the quiet period (14→26 entries, 37→139) is *proof* the run was
working. I had that data in front of me and still said "dead". **If a counter went up, the run is
alive — say nothing about death until a counter and the state file both stop.**

## 5. Inverting the verdict direction (the one that nearly cancelled a true finding)

A harness where `test_defect_*` PASSING means the defect is **present**. When the summary table
read `NOT AFFECTED (guard held)` for nine chains, the labels were reversed relative to what I
was reading — one more turn of that and I would have withdrawn a valid finding.

- Before trusting a summary, read the **assertion** (`require(!ok, "...")` vs `require(ok, ...)`)
  and the test's **name**, and confirm they agree. A name like `test_defect` with `require(!ok)`
  is fine; a name like `test_fixed` with `require(ok)` on the same behaviour is a trap.
- Print the raw observable (`[PASS] test_B_disarm`) alongside any derived label, so a label bug
  cannot hide the observation.

## 6. A `patch` that deletes a `def` line passes the syntax check

Replacing a block with `old_string` ending at `def foo(...):` but not re-including it produced:

```diff
-    def _prepare_sc_project(self, sol_src):
+    # ...my new code...
+
         """Make the recovered source BUILDABLE..."""
```

`ast.parse` said **syntax OK** — because a bare docstring is a legal expression statement. The
function was gone and the module still imported.

**After any patch that touches a `def`/`function` boundary, grep the symbol back:**

```bash
python -c "import ast;ast.parse(open(p,encoding='utf-8').read());print('syntax OK')"
for f in _prepare_sc_project _resolve_solidity_source run_cmd; do
  printf "  %-26s %s\n" "$f" "$(grep -c "def $f" "$p")"     # each must be 1
done
```

A syntax check proves the file parses. It does not prove your edit did what you meant.

## 7. State that resolves by an id the system deletes on success will be re-created

Staging a draft with `PUT /drafts/{id}`, the tracked id 404'd — because the operator had **sent**
it and Gmail removes a draft on send. My script treated 404 as "missing, recreate", so it
re-created a duplicate of something already delivered.

The fix is a distinct, loud marker rather than silent healing:

```python
recreated = False
except urllib.error.HTTPError as e:
    if e.code in (400, 404):
        did, created = None, True
        recreated = True          # <- never heal silently
...
print(f"[{fid}] draft=<{did}> {'created' if created else 'replaced'}"
      + ("   <-- RECREATED: tracked draft was missing (already sent?)" if recreated else ""))
```

Plus an end-of-run sweep that counts instances per identity and flags any duplicate. Silent
self-healing on a consumed id is how a duplicates-in-the-inbox bug hides.

---

## The general rule

**Every claim of the form "the target does X" must survive the question "what in my rig would
also make it look like X?"** For a failing control, a compile error, a quiet log, or an odd
summary label, the answer is usually "my rig" — and the rig is one command away from being
excluded. Cheapest disambiguation first, claim second.

Corollary for reporting: when the disambiguation was *not* done, say so. "I read the tail
mid-run and called it dead; it had completed" is a more useful line than a quietly corrected
number, because it tells the next reader which of your claims were snapshots.
