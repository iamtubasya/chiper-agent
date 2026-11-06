# Gate, REWORK, and step-log persistence

Discovered 2026-10-08 during a relay.link (web3) run that hard-blocked at 0D three
times in a row with **zero progress between attempts**. This is the failure mode
that looks like "the pipeline is broken / the host is too weak" but is actually a
one-line persistence bug repeated across every step script.

## The signature

Read the gate output across attempts, not just once. Pathological pattern:

```
attempt 1 -> FAIL (2)   ❌ tools-usage.json not found
attempt 2 -> FAIL (6)   ❌ reference-usage.json missing
                        ❌ business-logic-usage.json missing
                        ❌ asset-coverage FAIL (0C, 0D)
attempt 3 -> FAIL (5)   ❌ tools-usage.json not found      <-- same as attempt 1
-> HARD BLOCK
```

The tell: **the failing set changes and GROWS between attempts**, and a failure
that attempt 2 had "fixed" is back at attempt 3. That is not a target problem —
it is artefacts being rewritten from empty.

## Root cause

Every step script built its usage list in memory and wrote the JSON **once, at the
bottom of `main()`**:

```
execute-references.py:     write at line 316 of 326
execute-business-logic.py: write at line 412 of 423
execute-poc-variants.py:   write at line 354 of 366
force-full-execution.py:   tool_usage_log.write_text(...)  # single write at the end
```

So any interruption — a killed child, a timeout, memory pressure, a `taskkill`
on the parent — leaves **no file at all**. The gate then reports `X not found`,
REWORK re-runs the same step the same way, and the loop burns its 3 attempts
without ever producing the artefact it is waiting for.

## The rule

**Every step script must persist its usage JSON on every append, not at the end.**
Merge by a stable key so re-running is idempotent and never loses earlier entries.

Pattern (drop-in, no imports needed — `json` and the target path are already in scope):

```python
_usage_path = target_dir / "reference-usage.json"

class _PersistList(list):
    def append(self, item):
        super().append(item)
        try:
            _usage_path.write_text(json.dumps(self, indent=2), encoding="utf-8")
        except Exception:
            pass          # NEVER let logging kill the run

usage = _PersistList()
```

For `force-full-execution.py` the merge must also union with whatever is already on
disk (keys `(tool, vuln_type, executed_at)`), because it re-runs over a prior log:

```python
merged = [e for e in existing if isinstance(e, dict)]
keys = {(e.get("tool"), e.get("vuln_type"), e.get("executed_at", "")) for e in merged}
for e in self:
    k = (e.get("tool"), e.get("vuln_type"), e.get("executed_at", ""))
    if k not in keys:
        merged.append(e); keys.add(k)
_usage_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
```

## Verification that proves it

Do not trust the code change — kill the step mid-flight and look for the file:

```bash
T=<tmpdir>; rm -rf $T; mkdir -p $T
timeout -s KILL 75 python force-full-execution.py <TARGET> --tech "solidity web3 evm" --output-dir $T
ls -la $T/tools-usage.json      # MUST exist
```

Observed after the fix: killed at 75 s, `tools-usage.json` present with **26 entries**
(arjun, sqlmap, dalfox, kxss, SSRFmap, Interactsh, …). Before the fix: absent.

## Secondary rule: check the OTHER writers too

Fixing one script is not enough — grep for the shape across the whole family:

```bash
for f in execute-*.py track-*.py force-*.py; do
  echo "$f: writes=$(grep -cE 'write_text\(json|json\.dump' $f) appends=$(grep -cE '\.append\(' $f)"
done
# then confirm the write sits at/near the end of the file:
for f in execute-references.py execute-business-logic.py execute-poc-variants.py; do
  echo "$f write@$(grep -nE 'write_text\(json' $f | tail -1 | cut -d: -f1) / $(wc -l < $f)"
done
```

A write line whose number is within ~15 of the file's last line is the bug.

## REWORK can make things worse — cap it mentally

REWORK maps a failure string to a re-run of one step. Because those steps rewrote
from empty, each REWORK round **destroyed more than it repaired** (2 → 6 → 5
failures). If you see the failure count rise across attempts, stop the loop and fix
persistence instead of watching attempt 3.

## Related: is the pipeline actually dead?

Not necessarily — see `references/run-observation-discipline.md`. Twice in that
session a run was declared dead from a mid-run log tail; both had in fact completed
to 0D and been blocked by the gate. Confirm with the process list and file mtime
growth BEFORE concluding anything about the host or the code.
