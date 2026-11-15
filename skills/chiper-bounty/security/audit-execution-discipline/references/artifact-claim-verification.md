# Artifact-claim verification — read the authoritative signal before stating a conclusion

Every failure below has the same shape: **a conclusion was stated from a proxy signal
when the authoritative signal was available and cheap to read.** The fix is not "be
more careful" — it is a specific command per claim type. Run the command; then speak.

Recurrence count in one session (2026-10-08): **eight**. Two of them were
consequential — one nearly discarded a *correct* finding, one reported a *successful*
pipeline as failed to the user.

## The table — claim → the thing that actually settles it

| About to claim | Do NOT rely on | AUTHORITATIVE check |
|---|---|---|
| "the run died" | mid-run log tail, mtime, absence of traceback | `grep -c '^=== EXIT' "$LOG"` — sentinel present ⇒ FINISHED |
| "this deployment is not vulnerable" | your runner's PASS/FAIL summary line | re-read the assertion direction; confirm against a chain already proven affected |
| "my report bundles two findings / breaks RULE 0" | memory of what you wrote | `pdftotext`/pypdf the PDF and grep for the second finding's keywords |
| "token X is missing from the PDF" | a case-sensitive `in` test | tokens must be matched case-sensitively **to what the generator emits**, not to the source spelling |
| "the draft was replaced" | your script's own log line | list every draft and COUNT — `created` vs `replaced` is a hint, not evidence |
| "the function still exists after the patch" | `ast.parse` succeeding | `grep -c "def <name>" file.py` — a removed `def` can parse fine |
| "the scanner found nothing ⇒ clean" | exit code alone | read the analysand path out of the evidence header (SC tools exit non-zero on success) |
| "the target is in scope / this address is live" | the deployment registry | the protocol's own live API response |

## The four that actually cost something

### 1. Inverted verdict — nearly discarded a real finding

A multi-chain probe printed `base -> NOT AFFECTED (guard held)` while a fork test had
already **proven** Base affected. The runner mapped `test_B` *passing* → "not affected",
but `test_B` passes precisely when the defect is present. The contradiction with prior
evidence is the only reason it was caught.

Rule: when a named test's PASS means "the defect is present", say so in the assertion
message (`require(probe.reentered(), "guard HELD - NOT affected")`) and **re-read the
direction before trusting any summary table your own script prints.**

### 2. Reporting success as failure

Stated "pipeline died at 0C-C6" from a 29-line sample; the log reached 66 lines and
`=== EXIT 0 ===`. Worse: `tools-usage.json` and `poc-variant-usage.json` had been
**observed growing** in that same window and were discarded as corroboration. See
`run-observation-discipline.md` CHECK ZERO.

### 3. Phantom own-rule violation

Told the user a report violated the operator's "1 finding = 1 draft = 1 PDF" rule —
without opening the PDF. The second finding was not in it (`dangling`: 0 occurrences).
A false confession costs the same credibility as a false claim.

Rule: **before confessing a violation, read the artifact and show the count.**

### 4. A patch that deleted the function it was editing

A replace-mode patch had `old_string` ending in:

```python
    def _prepare_sc_project(self, sol_src):
```

The replacement kept the body but dropped the `def` line. `ast.parse` returned clean,
because the function's docstring became a harmless bare expression statement — the file
still parsed, and the function was **gone**.

Rule: after any replace-mode patch to a `.py` file, verify the symbols:

```bash
python -c "import ast;ast.parse(open(r'FILE',encoding='utf-8').read());print('syntax OK')"
for f in <symbols you touched>; do printf "  %-26s %s\n" "$f" "$(grep -c "def $f" FILE)"; done
```

A green syntax check is not a green structure check. Always include the `def` line **and
its first body line** in `old_string`, so the match cannot land mid-definition.

## Cheap habits that catch all of these

- **State the signal you read.** "the log's last line is X" is an observation; "the run
  is dead" is a conclusion. Only promote after the authoritative check.
- **Contradiction with prior evidence is a stop sign**, not noise. Two of the eight were
  caught solely because the result disagreed with something already proven.
- **Growing ledgers/artifacts are dispositive of life.** Shrinking or static plus no
  sentinel is the only real death signal.
- **Read the count, not the vibe.** `0x` vs `1x` occurrence, draft count, `grep -c`.
