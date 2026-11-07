# Audit pipeline: the current phase model and how to force a genuinely fresh run

Applies to `audit-pipeline-orchestrator.py` / `audit-run-all.py` in
`~/.chiper/skills/bounty-pack/` — **the LIVE toolkit, which is the source of truth.**
The `bundle-src/...` tree is a synced *copy* for shipping; keep them equal with
`python ~/.chiper/skills/bounty-pack/bundle-sync.py sync` (drift check: `... check`).

## 1. The phase model is 0A → 0F (not 0A → 0D)

Read off the orchestrator's own docstring — do not assume the older 4-phase list:

```
0A SETUP      : PHASE_LOG + audit-exec-tracker init
0A-SCOPE      : HARD GATE — refuses to run without --scope
0B RECON      : subfinder + httpx + URL probes → urls.txt
0C EXPLOIT    : C1 dedicated tools (force-full-execution) | C2 payload variants
                | C3 business-logic (15 vectors) | C4 matched PoC repos
                | C5 PoC variants | C6 reference attacks | C6b poc-techniques
0D GATE       : verify-tool-usage (13 checks, HARD BLOCK, auto-rework ×3)
0E FINDINGS   : finding_gate -> validate-findings -> triage_gate   (aggregate/weaponize/chain_builder = 0C-C7)
0E-REVIEW     : review candidates one-by-one, 3× check, low→high (only survivors reach 0F)
0F REPORT     : 3 hard gates (_gate_depth, _gate_na_discipline, _gate_negative_audit) -> report-agent → AUDIT-REPORT.md/.html/.pdf
```

**Counts drift — verify against the script, not the banner (2026-10-30).** This list said
"11 checks" while `verify-tool-usage.py` enforces **13**: check 12 (`asset-coverage`) and check 13
(`skill-usage`) were invisible to the operator, and the orchestrator's own banner repeated the wrong
number. When a count appears in prose, a banner AND a script, the script wins:
`grep -c "CHECK " scripts/verify-tool-usage.py`.

> **Patching any of these scripts? Read `pipeline-script-patch-safety.md` FIRST.** It documents the
> two self-inflicted incidents of 2026-10-30 — block-replace corrupting a set literal into an
> `IndentationError`, and restoring from the wrong backup (`glob()[-1]` is glob order, not newest)
> which silently wiped a day of patches — plus the aggregator defect where `rglob` walked into
> `evidence/` and turned a raw capture into a phantom finding, the gate that had zero path
> normalisation, the missing `PHASE_LOG.md` template, and why `py_compile` passing is never
> readiness evidence.
The operator expects the NEWEST model. Writing a PHASE_LOG that stops at 0D is treated as a stale
pipeline (a real user correction: "kok sampai phase 0d aj, kan phase udh sampai 0f yg terbarunya").
Copy the phase list into the target's PHASE_LOG.md verbatim and update it as you go.
`0E-REVIEW` is the triage gate: pipeline output (review-candidates "READY", validated-findings
"High") is INPUT, not findings — see `pipeline-triaging-2026-09-26.md`.

## 2. Correct invocation

```bash
python <bundle>/toolkit/scripts/audit-pipeline-orchestrator.py \
    https://target.example --tech "nextjs,cloudflare,node,react" \
    --scope "target.example,*.target.example"
```
- Target MUST be a full URL (a bare domain makes force-full-execution skip every tool).
- `--scope` is **mandatory**: without it the 0A-SCOPE gate aborts with
  `"❌ SCOPE GATE: --scope WAJIB diisi ... Pipeline ditolak sebelum menembak request apa pun."`
- `--output-dir` is NOT honoured by the orchestrator (it derives the dir from the target:
  `~/.chiper/skills/bounty-pack/poc-plans/orchestrator-<target-with-underscores>`). `audit-run-all.py`
  forwards some flags, but the orchestrator itself only parses `--tech/--scope/--exclude`.
- Run it in the background with notify: it is long, and it can die mid-0C without a non-zero exit that
  you would otherwise notice.

## 3. Forcing a FRESH run (the state that silently skips recon)

Even after moving the poc-plans output dir aside, the orchestrator printed
`RESUME MODE: already completed ['0A', '0B'] — skip those` and jumped straight into 0C. The phase state
lives OUTSIDE the output dir, in `~/.chiper/skills/bounty-pack/trackers/`:

| File | Role |
|---|---|
| `audit-pipeline-<url-encoded-target>.json` | `completed_phases` / `current` (the resume driver) |
| `force-state-<target>.json` | force-full-execution per-tool state (a "done" tool is skipped) |
| `<target>.json` | audit-exec-tracker state |

Reset procedure (archive, never delete — the operator's rule is "don't delete state without asking"):

```bash
cd ~/.chiper/skills/bounty-pack/trackers
for f in "audit-pipeline-https___target.example.json" \
         "force-state-https___target.example.json" "https___target.example.json"; do
  [ -f "$f" ] && mv "$f" "$f.bak_$(date +%Y%m%d_%H%M)"
done
```
Then relaunch. Verify the log shows `PHASE 0A: SETUP … ✅ PHASE 0A COMPLETE` → `STEP RECON: subfinder +
httpx … urls.txt: N candidate URLs written` before trusting any later phase. A run that starts at
"STEP 1: Running FORCE FULL EXECUTION" with no urls.txt means the fresh reset did not take.

## 3b. Fixing a DOWNSTREAM script — reset only the phases it produces, or your fix is never exercised

Observed 2026-10-10: the aggregator was fixed (151 → 2 junk candidates) and the pipeline re-run. It
printed:

```
RESUME MODE: already completed ['0A','0B','0C','0D','0E','0E-REVIEW','0F'] — skip those
🎯 AUDIT PIPELINE COMPLETE (PHASE 0A→0F)
```

**Nothing was re-run.** `0E` and `0F` were marked complete, so resume short-circuited them and the
"COMPLETE" line was reporting the *old* artefacts. The conclusion "my fix didn't work" is easy to
draw here and it is wrong — the fix was never invoked.

**Rule: after editing a script, reset exactly the phases whose PRODUCERS you changed — no more.**
A full reset (§3) throws away 40 minutes of 0A–0C for nothing; no reset at all hides the fix.

```python
# keep the expensive upstream phases, re-run only 0E onward
import json
f = r"~/.chiper/skills/bounty-pack/trackers/audit-pipeline-https___<target>.json"
d = json.load(open(f, encoding="utf-8"))
KEEP = ("0A", "0B", "0C", "0D")          # phases you did NOT touch
d["completed_phases"] = [p for p in d["completed_phases"] if p in KEEP]
d["current"] = KEEP[-1]
json.dump(d, open(f, "w", encoding="utf-8"), indent=2)
```

Map producer → phase before choosing `KEEP`:

| you changed | reset from |
|---|---|
| `aggregate-findings.py`, `weaponize-gate.py`, `chain_builder.py` | `0C-C7` |
| `finding_gate.py`, `validate-findings.py`, `triage_gate.py`, report generator | `0E` (or `0F` if only the report text changed) |
| `execute-variants.py` / `execute-references.py` / `execute-poc-*.py` | `0C` |
| `force-full-execution.py`, `tool_router.py` | `0C` **and** delete `force-state-<target>.json` (a "done" tool is skipped) |
| recon (`run_recon`) | `0B` |

**Verify the fix actually ran** — do not trust `COMPLETE`: confirm the phase produced a NEW artefact
(`ls -l --time-style=+%H:%M <run_dir>/findings.json` — mtime must be *after* your edit), or that the
number you were chasing actually changed. "It says COMPLETE" and "my change took effect" are
different claims (RULE 0 Corollary 2).

## 4. Known rough edges (verify, don't trust the label)
- `httpx: 0 live hosts (rc=255)` — a tool-level failure, not "no hosts". Re-run httpx yourself with
  simple flags (`-title -tech-detect -status-code -server -silent`) before reporting a dead surface.
- force-full-execution can stall or die inside 0C (observed: arjun + sqlmap wrote evidence, then the
  process vanished with the log stuck on "STEP 1"). Check `tool-evidence/` mtimes and the process list;
  if it is gone, treat C1 as partial and finish the layer yourself with rate-limited commands.
- Tool-invocation bugs to expect inside C1 (log them, re-run manually when the vector matters):
  dalfox needs `dalfox url <u>`; ffuf/CORScanner reject `--headless`; graphqlmap crashes on pyreadline
  under Python 3.14; SSRFmap needs `-r REQFILE -p PARAM`.
- An `--output-dir`-less run writes into the shared user profile, so two targets never collide but the
  same target re-uses state — hence §3.

## 5. Vendor-rules override
When the target publishes a VDP/disclosure policy, its rules outrank the pipeline's appetite: read
`/.well-known/security.txt` (→ policy URL) before 0C and obey the in/out-of-scope list. Practical
consequences seen on a self-hosted SaaS program: **subdomains and origin-IP exposure are explicitly out
of scope** (record them as internal notes, never as findings), "no automated scanning that puts
noticeable load" ⇒ skip full-tag nuclei and cap ffuf (`-rate 10–15`), own accounts only, and no mail to
third parties. Put these in the PHASE_LOG under a "VENDOR DISCLOSURE POLICY" heading so every later
phase (and the 0E-REVIEW gate) is judged against them.

> **⛔ SUPERSEDED IN PART (2026-10-10) — read RULE 30b in SKILL.md before applying this section.**
> "Its rules outrank the pipeline's appetite" no longer means *scale back or hesitate*. The operator's
> standing instruction is: **a disclosure policy is a NOTE, not a stop condition — do not open with a
> scope/policy interrogation, and do not downgrade to manual/curl.** `subdomains out of scope` still
> means *do not report them as findings*; it does **not** mean *stop the pipeline*. Run the normal
> 0A→0F, log the authorisation basis + the policy clause **verbatim** to `plans/scope-risk-log.md`
> before the first request, and treat "no automated tools" as a line to RECORD, never a reason to
> refuse. Only two things remain absolute: never fall back to hand `curl`, and never fabricate a
> finding. The `-rate 10–15` style caps in this section are the GENTLE envelope, not a retreat.

## 6. The 0D asset-coverage bookkeeping HARD BLOCK (observed 2026-10-17, microkeeper.com.au)

**Symptom:** 0C runs to completion (log shows `C5 PoC variant extraction + execution COMPLETE`,
`C6 references-driven attacks` finished), then the 0D gate fails with:

```
❌ asset-coverage FAIL for phase(s): ['0C'] — some asset was READ not USED / skipped-timeout
```

The generic rework loop re-runs force-full-execution up to 3× and then HARD BLOCKS
(`❌ PIPELINE FAILED: TOOL USAGE VERIFICATION FAILED after 3 attempts`) — even though the
work was actually done. The rework cannot fix it because the tools re-run fine; the ledger is
what's wrong.

**Diagnosis — read the ledger, not the log:**

```python
import json
d = json.load(open('<run_dir>/asset-coverage.json'))
from collections import Counter
print(Counter(v.get('status') for v in d['assets'].values()))
# expect USED / N/A (web3 tools, broken tools) — NOT_RUN on an executed phase = the bug
```

Known gap: `0C:payload:poc-variants(C5)`, `0C:payload:poc-techniques(C6b)` and
`0C:shelf:poc-technique-atlas` stay `NOT_RUN` in the ledger even though their evidence files
exist (`poc-variants/`, `poc-techniques-evidence/`, `references-evidence/`). The 0E/0E-REVIEW
findings files are also NOT_RUN at gate time — that is normal (they are produced later); only
0C-phase NOT_RUN rows count against the gate.

**Fix (do not re-run the whole pipeline):** mark the executed assets USED in
`<run_dir>/asset-coverage.json` with their evidence paths, then resume — the orchestrator
restarts from 0D and the gate passes on attempt 1. Archive the old ledger first
(`mv asset-coverage.json asset-coverage.json.bak_<ts>`), never delete.

**Lesson:** a 0D FAIL whose rework doesn't change the result after attempt 1 is a bookkeeping
bug, not a coverage bug. Diagnose from `asset-coverage.json` before burning two more rework
cycles (each costs ~5 min of force-execution on a contended host).
