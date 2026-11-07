# Maintaining the pipeline scripts without breaking them

Lessons from 2026-10-30, when six real gate defects were found and fixed in one session — and two
of the fixes were themselves destructive. The defects matter less than the **method**, because the
same traps will be hit again by anyone patching `scripts/*.py` under time pressure.

Read this before editing any script in `~/.chiper/skills/bounty-pack/`.

---

## 1. Patch a SET LITERAL by line anchor, never by block replace

A hand-built replacement for a multi-line literal silently corrupts indentation:

```python
# WRONG — replacing the whole EXCLUDE_DIRS = {...} block
new = 'EXCLUDE_DIRS = {"a", "b",\n                "c"}'
# produced: IndentationError: unexpected indent, at the NEXT statement
```

The file is then **corrupt**, not merely unpatched, and every later step inherits the breakage.

```python
# RIGHT — split to lines, find the closing line, insert whole lines before it
lines = s.splitlines(keepends=True)
target = next(i for i, l in enumerate(lines)
              if "manifest-work" in l and "}" in l)
lines[target] = lines[target].replace('"manifest-work"}', '"manifest-work",')
lines[target+1:target+1] = [indent + '"evidence", "tool-evidence"}\n']
```

For everything that is **not** a set/dict literal, prefer a short unique `old_string` (10–20 chars
of context is enough) and assert it was found before writing:

```python
assert old in s, "anchor not found — do not proceed"
s = s.replace(old, new, 1)
```

Never slice with computed indexes (`s[:start] + s[end+1:]`). A previous incident destroyed a
103 KB SKILL.md down to 2.6 KB exactly that way.

---

## 2. Restore by mtime, then ASSERT the patches survived

`glob(...)[-1]` returns **glob order, not newest**. Restoring with it selected an 8-day-old backup
and silently reverted every patch made that day — the file compiled cleanly, so nothing announced
the loss.

```python
bak = sorted(glob.glob(p + ".bak_*"), key=os.path.getmtime)[-1]   # newest, not last alphabetically
shutil.copy2(bak, p)
py_compile.compile(p, doraise=True)

# then PROVE the day's work is still there
s = open(p, encoding="utf-8").read()
for marker in ("_msys_norm", "WEAPONIZATION.md", "EXCLUDE_DIRS"):
    assert marker in s, f"RESTORE LOST: {marker}"
```

A char count moving in a direction you did not expect is a signal — diff the restored file against
the backup and check `lines lost = 0` before continuing.

---

## 3. Never invent a method name — grep for `def <name>` first

`self._classify_target()` compiles perfectly and fails only at runtime; the target-type check
actually lives inside `run_scope_check`. Invented names are invisible to `py_compile`.

```bash
grep -n "def _classify\|def run_scope" scripts/audit-pipeline-orchestrator.py
```

Cheap inline alternative when you only need a guard: write the condition locally rather than
calling a method you assume exists.

---

## 4. Two parser/aggregator defects worth remembering

### 4a. `evidence/` directories are not findings
`aggregate-findings.py` walks with `rglob("*")`, so it descended into `evidence/` and
`parse_plain_findings` manufactured a candidate **out of the raw request/response capture**:

```
- '[evidence\p] 1 notable response(s) — Medium'   | src: evidence\p.txt
- 'IDOR cross-tenant invoice read exposes IBAN'   | src: worker-01.md
```

One real finding became two, and the phantom consumed a gate slot. Filename-level `SKIP_NAMES`
does not help here — it is a **directory** exclusion:

```python
EXCLUDE_DIRS = {..., "evidence", "tool-evidence", "poc-evidence",
                "raw", "_raw", "captures", "screenshots", "logs", "artifacts"}
```

**Verification habit that catches this whole class:** assert the aggregated count equals the
number of findings you wrote. `Total findings: 2` after writing 1 is always a parser bug, never a
bonus.

### 4b. A gate with zero path normalisation has never been exercised
`weaponize-gate.py` had `grep -c _msys_norm` = **0** while every other gate had it. It stayed
invisible because the gate normally exits early (`no input findings — nothing to weaponize`)
*before* touching an output path — so it only detonated on a run that had real findings.

```bash
for f in scripts/*.py; do
  n=$(grep -c "_msys_norm" "$f" || true)
  [ "$n" -eq 0 ] && grep -q "Path(args\.\|Path(sys.argv" "$f" && echo "NO-NORM: $f"
done
```

Rule: after adding any new gate script, normalisation must be present in the same change.

---

## 5. Scaffolding gaps that make 0A fail before any hunting starts

- **`_progress/_template/PHASE_LOG.md` may not exist.** SKILL.md points a new engagement at it; an
  empty `_progress/` means every engagement is hand-written and a wrong shape fails 0A with
  `PHASE_LOG.md exists` / `target specified` / `scope specified` in red. Minimum viable shape is
  the three keys the check greps for — `target:`, `scope:`, plus phase headings marked COMPLETE.
  Verified 4/4.
- **The orchestrator created its output dir before validating the target**, so a typo (`--help`,
  a bare flag) left a permanent empty `poc-plans/orchestrator---help/` behind. A cheap pre-check
  (scheme / dot / `0x` / `.sol` / `os.path.isdir`) before `mkdir` exits 2 with no scaffolding.
  Symptom to watch: `poc-plans/orchestrator-*` directories named after flags.
- **Banner drift:** the orchestrator advertised `verify-tool-usage (11 checks)` while the script
  enforces **13** — check 12 (asset-coverage) and check 13 (skill-usage) were invisible. When a
  count appears in both a banner and a script, verify against the script.

---

## 6. Readiness claims need an end-to-end run, not a compile

`py_compile` passing proves nothing about whether the chain produces output. The only acceptable
readiness evidence is a full run from an empty engagement directory:

```
0A 4/4 → C7 aggregate(1) → weaponize(1 SHIP) → chain → E4 REPORT:1
       → E5 100% → E6 1/1 PASS → 0F READY
```

Build the fixture with a **complete** finding record. Omitting `fix_regression` causes a correct
`DROP` (`FIX_REGRESSION empty — does the fix break legit use…`), which is the gate working — not a
bug to patch away. Distinguish "gate correctly rejected my fixture" from "gate is broken" by
checking whether the reason is one you can fix in the fixture.
