## ⛔ MECHANICAL ENFORCEMENT

```
PRIMARY PIPELINE (one command — full orchestrator, gate + auto-rework built in):
python ~/.chiper/skills/bounty-pack/audit-pipeline-orchestrator.py <TARGET> --tech "<tech>"

audit-run-all.py is now a THIN WRAPPER — it just re-invokes the orchestrator.
It is NOT a separate pipeline. Do NOT develop/run two parallel "runners":
the 2026-09-24 "dual-runner drift" (audit-run-all.py had its own stale phase
logic that skipped recon/variants/PoC-variants/gate) was the ROOT CAUSE of
"kurang lengkap / only curl then stop" complaints. Single brain, one pipeline.
```

### Orchestrator pipeline (single-brain — enforced, not advisory)

```
Step 0   run_recon (IN-ORCHESTRATOR)   → subs.txt + live.txt + urls.txt + recon-raw.txt
         (subfinder + httpx). REQUIRED before variants — execute-variants.py reads
         urls.txt from the target dir; without a recon step it has no fuzz targets.
Step 1   force-full-execution.py       → tools-usage.json + tool-evidence/*.txt (raw stdout per tool)
         NOTE: tools-usage.json is now MERGED (dedup by tool+vuln+timestamp), NOT
         overwritten — a re-run of force-full-execution does NOT wipe earlier tool evidence.
Step 1.4 execute-variants.py           → variant-usage.json + variants/*.txt (payload libs fired one-by-one vs recon URLs)
         execute-business-logic.py        → business-logic-usage.json + business-logic/*.txt (15 vectors: IDOR, priv-esc, mass-assign, CSRF, file-upload, cache-poison, 403-bypass, pw-reset, websocket, api-versioning, rate-limit, 3rd-party, source-maps, http-smuggling, biz-logic)
         track-poc-execution.py        → poc-execution.json + poc-evidence/*.txt (ALL matched repos w/ entry point, cap 25, required types first)
         execute-poc-variants.py       → poc-variant-usage.json + poc-variants/*.txt (payload FILES extracted FROM matched PoC repos and fired; CVE-*/exploit*/main.py + code-file fallback)
         execute-references.py         → reference-usage.json + references-evidence/*.txt (C6: reference clues converted to REAL requests: HEADER_ATTACK / ENDPOINT_PROBE / PAYLOAD_INJECT — see RULE 25)
         execute-poc-techniques.py     → poc-techniques-usage.json + poc-techniques-evidence/*.txt (C6b: attack TECHNIQUES extracted from ALL 2223 PoC repos fired at target — see RULE 26)
Step 1.5 verify-tool-usage.py GATE     → 11 checks read from DISK (not claims):
         C1 tools-usage.json exists · C2 evidence file per EXECUTED tool · C3 evidence ≥100B ·
         C4 all tools accounted + UNACCOUNTED-status detector · C5 ≥3 tools with real evidence ·
         C6 variants executed + evidence files · C7 PoC executions have output on disk ·
         C8 PoC variant usage + evidence · C9 business-logic vectors executed + evidence ·
         C10 reference-usage.json exists + evidence files ≥30% (refs USED, not just loaded) ·
         C11 poc-techniques-usage.json exists + non-empty + evidence ≥30% (techniques from 2223 repos USED)
Step 2   validate-findings.py          → validated-findings.json (PoC+impact+chain+tool-evidence gate; FPs filtered)
Step 2.5 review-candidates.py          → review-candidates.json/.md + ready-candidates.json (see RULE 24)
Step 3   report-agent.py              → AUDIT-REPORT.md (+ PDF via bug-report-delivery) — source = ONLY ready-candidates.json (lolos 3x cek)
```

**Single-brain rule (2026-09-24):** if you must add a step, add it to the
orchestrator (or a script the orchestrator calls). Never fork a second runner
with its own copy of the phase list — two runners WILL drift, and the skill
text will silently point at the stale one.

### ⛔ ERROR = REWORK, NEVER SKIP (user rule: "jgn dskip, balik diulang, jgn langsung report")

Gate fail → orchestrator maps failure → RE-RUNS THE SPECIFIC FAILED STEP → re-verifies.
Max 3 attempts. Only then HARD BLOCK (exit 1, NO report, state saved for resume):

| Gate failure signature | Auto-rework action |
|------------------------|--------------------|
| `variant-usage.json missing` | re-run execute-variants.py |
| `no fuzzable URLs` / all variants skipped | re-run recon (subfinder + urls.txt fallback) → re-run variants |
| `poc-execution.json missing` | re-run track-poc-execution.py |
| `poc-variant-usage.json missing` | re-run execute-poc-variants.py |
| `tools-usage.json not found` / `Thin evidence` | re-run force-full-execution.py |

**Prohibited:** seeing a step fail → silently continuing to report generation. The gate
exit code is the single source of truth; a report only exists when the gate exited 0.

### PoC payload classification (do not misread as lazy skipping)

- `NONWEB_PAYLOAD_TYPE` = payload files are deserialization gadgets / plugin files /
  protocol fuzzers / firmware — not fireable via HTTP params. Logged + reason recorded.
  This is a VALID logged status, NOT a silent skip. Manual review item only.
- `NO_ENTRY_POINT` / `SKIP_WITH_REASON` = likewise logged, never dropped.
- The gate FAILS only when entries are entirely missing, all skipped, or claimed
  EXECUTED without output on disk.

Manual fallback (when orchestrator itself fails):
```
# At audit START
python ~/.chiper/skills/bounty-pack/audit-exec-tracker.py init <target>

# After EVERY exploit attempt
python ~/.chiper/skills/bounty-pack/audit-exec-tracker.py log <target> --vector "<name>" --result <result> --evidence <file>

# Before claiming phase complete
python ~/.chiper/skills/bounty-pack/audit-exec-tracker.py gate <target> --phase <0A|0B|0C-Web2|0C-Web3|0D>
```

**⛔ Each log entry MUST include: exploit command + tool output + impact evidence.**
**⛔ "Tested" is NOT enough. "Exploited with working PoC" is the bar.**

### ⛔ Tracker Limitation — log ≠ refs/tools

**User correction (Ern audit 2026-09-22):** Tracker `log` command registers **vectors only**. Refs loaded via `skill_view()` and tools run via `terminal()` are NOT automatically counted by `gate` checks — the gate shows 0/96 refs even after loading 20+ skill references.

**MANDATORY workaround — dual verification:**
1. **Tracker log** for vectors (the `log` command works for this)
2. **Manual summary** for refs/tools — BEFORE claiming phase complete, print a checklist:
   ```
   Phase 0A refs: [list each ref file loaded]
   Phase 0B tools: [list each tool + terminal output proof]
   ```
3. **Never rely solely on `gate` output** — it may show incomplete counts even when work is done
4. **Cross-check with actual files on disk:** `ls -la` on output files to prove they exist

