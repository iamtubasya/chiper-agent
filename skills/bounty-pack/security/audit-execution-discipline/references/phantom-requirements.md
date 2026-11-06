# Phantom requirements — a gate that demands an artefact NOTHING writes

A gate is only passable if **some producer exists for every artefact it demands**. When a mandate is
added to the manifest but no step is wired to satisfy it, the gate is unsatisfiable *by
construction* — every run hard-blocks, the REWORK loop re-runs the same steps for the same 3
attempts, and the operator sees "gate FAILED" on an engagement that did nothing wrong.

This is a distinct family from the other gate defects already documented:

| family | symptom | where the fix goes |
|---|---|---|
| fail-OPEN gate (`finding-gate-fail-open-*`, RULE 39) | junk reaches the report | the classifier defaults / label stripping |
| gate scores its own echo (`mechanical-triage-gate-and-self-echo`) | 22 PASS from gate output | `unwrap()` + scaffold scrub |
| phase-inappropriate demand (`terminal-state-and-phase-appropriate-gates` §1) | 0D demands a 0E artefact | split the mandate by phase |
| **phantom requirement (this file)** | **the artefact has no producer at all** | **add the producer, or make it derive from what ran** |

## Two measured instances (2026-10-10, same run)

### 1. 0B recon ledger — 13 mandated assets, 0 recorded

`asset-coverage.py` `MANIFEST["0B"]["recon"]` mandates:

```
subfinder, amass, puredns, httpx, katana, gau, waymore, jsluice, naabu, dork-recon,
subs.txt, live.txt, urls.txt
```

`--derive` marks the **tools** `USED` from an entry in `tools-usage.json` + an evidence file carrying
`# TOOL EVIDENCE:`. The orchestrator's `run_recon` ran **only** `subfinder` + `httpx`, and recorded
**neither**. Result: `uncovered assets in ['0B'] (fail=12)` on every target.

### 2. `skill-evidence/hunt-*.md` — demanded by CHECK 13, written by nothing

Covered in full (round 2) in `references/autofill-skill-rules-gap-web-hunt-skills.md`.

### 3. `subs.txt` / `live.txt` must be NON-EMPTY — impossible on a CDN/apex host

The 0B ledger also demands `subs.txt ≥ 1 line` and `live.txt ≥ 1 line`. Pointed at a CDN/apex
hostname, `subfinder` legitimately returns **0** subdomains → `subs.txt` is empty → the chained
`httpx` has no input → **`live.txt` is never created at all**. Two ledger rows are then `NOT_RUN`
("subs.txt missing or < 1 lines") on a target where nothing went wrong.

This is the **second sub-class** of phantom requirement, and it is the nastier one: it is not
"nobody wrote the producer", it is **"the producer runs and correctly produces nothing"**. The gate
demands *content* where the target's shape legitimately yields none.

**Resolution — seeding is not fabrication.** Standard recon practice is that the target host is
itself an in-scope asset, so 0B now seeds it:
```python
# after subfinder: the target host IS an in-scope asset, so seed it
if domain not in subs_lines: subs_f.write_text(... subs_lines + [domain] ...)
# after httpx: if it produced nothing, write the direct probe result
if not live_rows: live_f.write_text("\n".join(f"{u} [{status}]" for u in (root, target)) ...)
```
This is honest because the row records a **real observation** (the direct probe's status), not an
invented subdomain. State the distinction explicitly when you do it: *seeding the apex = recording a
true fact; inventing a subdomain = fabricating coverage.*

**Generalised rule:** before demanding "file exists AND is non-empty", ask *"can this legitimately
be empty for some accepted target shape?"* If yes, either seed it from the target itself or teach
the checker that empty-with-a-reason is `N/A`, not `NOT_RUN`.

### 4. Manifest breadth vs producer subset — 55 mandated 0C tools, force-exec records ~10

`MANIFEST["0C"]["tools"]` mandates ~55 tools. `force-full-execution.py` runs the subset matching the
detected tech and records **only those**, so every other mandated tool stayed
`NOT_RUN — "no entry in tools-usage.json"`. `fail=16` on a run whose 0C had genuinely executed
C1–C5. Same class, twice the blast radius: the wider the manifest, the more rows are unpassable.

**Resolution — account for the manifest, don't widen the producer.** A single step iterates the
MANIFEST itself and gives every unrecorded tool an entry:
- binary resolvable → **run it** with a light target-appropriate command, write marker evidence,
  record `EXECUTED`/`RAN_WITH_ERROR` from the real exit;
- binary absent → record `NOT_FOUND` (derive → honest `N/A "tool not installed"`, which passes);
- read the manifest **from `asset-coverage.py`** rather than re-listing it, so the two cannot drift.

## The three producers this class produced (reusable shapes)

| shape | when to use it | what it does |
|---|---|---|
| **record-what-ran** (`_recon_record_usage`) | a phase ran tools but recorded none | write a `# TOOL EVIDENCE:` file + a `tools-usage.json` row for each; run the unrun remainder of the mandate |
| **account-the-manifest** (`_account_mandated_tools`) | the manifest is wider than any producer | iterate the mandate; run-or-`NOT_FOUND` each missing entry; never a fabricated `USED` |
| **derive-from-artefacts** (`_write_skill_evidence`) | the gate wants a *human-readable* proof per skill | build the file from the run's own usage/evidence rows; **no rows ⇒ write no file** so the skill stays `applied=false` and the gate still fails |

All three share one invariant: **nothing is marked used without an execution.** The fix removes the
*impossibility*; it never lowers the bar. An absent tool is `NOT_FOUND`, never `USED`.

## The discriminator — run this BEFORE blaming the run

```bash
# 1. does anything WRITE the demanded artefact?
grep -rn "<demanded-name>" scripts/ "$LOCALAPPDATA/hermes/skills" 2>/dev/null
```
- Hits only inside the *gate/checker* → **no producer → phantom requirement → unpassable.**
- Hits inside a *producer* (writer, `write_text`, `json.dump`) → real requirement; the run is at fault.

```bash
# 2. had ANY previous run ever satisfied it?  (the strongest single signal)
ls -d "$LOCALAPPDATA/hermes/poc-plans"/orchestrator-* | head -20
# then, on the most recent run that reached 0F:
python -c "import json,os; p=r'<run>/asset-coverage.json'; print('ledger present:', os.path.exists(p))"
```
If an older run that **reached 0F** has *no* ledger / *no* `<artefact>` at all, then the requirement
is **newer than the last thing that ever passed** — i.e. nothing has ever satisfied it. That is the
decisive evidence, and it took one `ls` to get. (Both instances above were confirmed this way: the
older passing runs had no `asset-coverage.json`, and no `skill-evidence/`.)

```bash
# 3. compare the gate's vocabulary against the producer's fields
grep -n "<asset>" <checker>.py          # what key does it read?
grep -n "<tool>" <producer>.py          # what key does the producer write?
```
Mismatched vocabulary is the sibling bug (see `gate-design-and-track-awareness.md` §6b) — check it in
the same pass, because both present as "the gate says I never ran it".

## Fix pattern — produce it from what actually ran, never from a claim

1. **Wire the producer into the pipeline step that owns the phase**, not into the checker.
2. **Record only what executed.** The evidence file must carry the writer's marker
   (`# TOOL EVIDENCE:` etc.) or the quality check rejects it as filler.
3. **An absent tool is `NOT_FOUND`, not `USED`.** `--derive` turns `NOT_FOUND` into an honest
   `N/A "tool not installed"` which *passes*; a fabricated `USED` passes too but corrupts the audit.
4. **No rows → no file → the skill/asset stays `applied=false`/`NOT_RUN` and the gate still fails.**
   That is correct behaviour: the fix removes the *impossibility*, not the *standard*.
5. **Call the producer before the gate reads it.** Ordering matters — this bit once: the 0B recorder
   was first called *before* `run_dork_recon()`, so `dork-recon` had no artefacts to record and was
   the one asset still missing. Move the call after the last producer for that phase.

## Why this class is worse than a normal bug

- It **looks like a coverage failure**, so the operator's instinct is to distrust the target or the
  tools — the exact inverse of the truth.
- The REWORK loop **cannot** fix it (it re-runs producers that were never supposed to exist), so it
  burns 3 attempts × the phase runtime and ends in HARD BLOCK every time.
- It makes the gate itself untrustworthy: an operator who hits this twice starts ignoring FAIL lines,
  which is how a real uncovered asset gets waved through later.

**Rule of thumb:** whenever a mandate is ADDED to a manifest/checklist, the same commit must add the
producer for it — or a `--derive` rule that computes it from artefacts that already exist. A mandate
without a producer is a bug report against the gate, not against the run.
