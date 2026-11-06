# rules body 04 (moved out of SKILL.md 20261010_094721 to stay under the 100k char limit)

### RULE 31b — two silent-failure traps that bit 40-file edit sweeps (2026-10-10)


Editing many SKILL.md/scripts at once produced two failure classes that look like success. Both are
worth 30 seconds of defence because they cost far more to debug later.

**Trap 1 — CRLF: a multi-line anchor written with `\n` silently matches nothing.**
The host's Markdown/scripts are CRLF. `src.replace("line A\nline B", …)` returns the input unchanged
→ the patch reports "success" while nothing was written. Hit **four times** in one session.
```python
# WRONG — silent no-op on a CRLF file
txt = open(fp, encoding="utf-8").read()
txt = txt.replace("A\nB", "X")                      # newline translation also REWRITES the whole file
# RIGHT — no translation on read OR write, and let the regex tolerate the CR
with open(fp, encoding="utf-8", newline="") as f:   # newline="" keeps \r\n intact
    txt = f.read()
txt, n = re.subn(r"A\r?\nB", "X", txt, count=1)
assert n, "anchor not found — do NOT assume the patch applied"
```
Then **prove** it: `raw=open(fp,'rb').read(); raw.count(b'\r\n')` must be unchanged (± the lines you
added/removed). A whole-file line-ending flip makes the diff 1,000+ lines of noise and hides real
edits. When a line-anchored edit is simpler, read lines with `newline=""` and write them back — that
preserves endings for free.

**Trap 2 — `ast.parse` passes, the module still explodes on first use.**
A patch made `log()` call `re.match(...)` in a module that never imported `re`. `python -m py_compile`
and `ast.parse` were both **green**; the pipeline died 8 seconds into the run with
`NameError: name 're' is not defined`. Syntax is not importability, and importability is not
callability.
```python
# after patching ANY script, smoke it for real
python -c "import importlib.util as u; s=u.spec_from_file_location('m', r'<fp>'); m=u.module_from_spec(s); s.loader.exec_module(m)"
```
`hermes-health-audit.py` now runs this import-smoke test over the pipeline scripts and reports
`import_fail=` separately from `syntax_fail=` — run it after any bulk edit.

**Trap 2b — import-smoke is not callability either. A `NameError` inside a METHOD body stays
invisible until the method is CALLED.** Three instances in one session; the first was caught by the
run (the `re` case above), the next two were caught only because the new method was exercised
directly against a real target dir:

- a method building evidence text referenced `nl` — defined in the *patching script*, never in the
  class → `NameError: name 'nl' is not defined`, fired once per asset (5 swallowed exceptions, 0
  files written);
- the same method's sibling used `_nl` the same way.

`ast.parse` green, import-smoke green, run still produces nothing. Guard rails:

```python
# after adding/altering any method, EXERCISE IT — not just the module
o = AuditPipelineOrchestrator("<target>", "<tech>", Path("<a real run dir>"), scope="x")
o._new_method(...)          # and assert on a real artefact it should have produced
```
- Any local the method needs (`nl`, `_nl`) must be defined **inside** the method. A patcher's module
  scope does not travel into the class.
- Assert on the **output**: `assert (run_dir/"skill-evidence").exists()`, then count and size the
  files. "It imported" proves nothing about a method body.
- Verification method itself can lie: `'_nl' in method.__code__.co_varnames` returned `False` for
  code that was in fact correct (stale module object). Trust the artefact, not an introspection
  shortcut.

The general shape: **syntax → import → call → effect** are four increasing bars, and each one has
passed while the next failed in this session. Pick the bar that matches what you changed.

**Two static guards now exist — RUN them, do not rediscover the bug.** After a third instance of the
unbound-name class, `hermes-health-audit.py` grew two checks that read the pipeline scripts and fail
loudly before a run starts:

| check | catches | why it matters |
|---|---|---|
| `unbound_name_fail` | a name USED in a function but bound in no enclosing scope (scope-chain aware, so closures are not false-flagged) | this is exactly the `nl` / `_nl` / `_re` class above. Caught a real `_re` reference in `_recon_record_usage` that sat inside a `try/except` and was therefore being silently reported as a **tool** `RAN_WITH_ERROR` — i.e. the code's own bug was disguised as the tool's failure |
| `budget_arith_fail` | `… + budget` not guarded by `if budget`, and `budget or 0` | `0` is a *valid-but-fatal* budget: `deadline = now` → every unit of work skipped, silently, with a clean exit code |

Both must read **BERSIH** before a run. When you build a new check of this shape, **validate it
against a known-bad fixture first** — the first version of the unbound-name guard flagged 37
false positives (it ignored closures); a noisy guard is worse than none, because it trains you to
ignore the real one.

**Never let a `try/except Exception` swallow a defect into a status field.** The `_re` case above is
the pattern to refuse: an internal coding error became `"status": "RAN_WITH_ERROR"` on an asset entry,
which reads downstream as *the tool failed* rather than *my code failed*. If a handler is broad, it
must still record **which exception**, not a plausible-sounding outcome. `RAN_WITH_ERROR` on every
asset in a batch is a smell — check the code path before believing the tools were at fault.

**Discipline that caught both:** back up every touched file (`.bak_<reason>_<ts>`), then `diff` the
backup against the result and confirm the change set is exactly what you intended. A 4-line diff on a
592-line file is a pass; a 1,184-line diff is a line-ending flip masquerading as an edit.

## ⛔ RULE 3: Timeout = Retry, Not Skip — **SUPERSEDED 2026-10-10 by the unbounded-run policy**


**Operator rule (2026-10-10), verbatim:** *"batas waktu per tool tidak ada, selagi masih berjalan,
biarkan sampai selesai, kl time out atau stuck, berikan sy warning, dan perbaiki spy lancar lagi"* —
and the reason it matters: *"kdg diskip yg buat akhirnya cm curl dan sia2 hasilnya sampah semua."*

The mechanism changed; the intent did not. There is **no per-tool wall-clock timeout any more**
(the 38 orchestrator step-timeouts and every `_run(cmd, timeout=N)` were removed). A tool that is
producing output runs to completion. What replaces the timeout ladder:

| old (timeout ladder) | new (2026-10-10) |
|---|---|
| run as-is with 2× timeout | run unbounded; `toolguard.py` warns at `BB_STALL_WARN` (300 s tool / 900 s step) |
| background + 2× + rate limit | same escalation, triggered by the STALL WARN not by a clock |
| subset (critical,high only) | `autofix.py` repairs the cause and **re-runs the same tool** |
| lightweight alternative | only if the signature is genuinely `UNFIXABLE` (e.g. CLI too old) |
| skip after 4 methods | **NO RESULT**, recorded; **never** a hand `curl` |

1. **Never kill a working tool.** `toolguard.run_guarded` MANDATES this.
2. **A stall is a warning, not a death.** `[STALL-WARN]` names the PID + exact command; unblocking is
   deliberate (`toolguard.py unblock --pid N`).
3. **A failure is repaired and re-run**, not downgraded (`autofix.py`, 7 signatures).
4. **`NO_CURL_FALLBACK` is a hard rule** (`tool_router.NO_CURL_FALLBACK = True`). A vector that cannot
   run is NO RESULT and gets retried later — substituting a hand curl produces garbage that reads
   like coverage, which is exactly what the operator complained about.
5. **48 h is the only real ceiling** — say so out loud rather than silently skipping.

Detail + the signature table: `references/runtime-execution-policy-2026-10-10.md`.
Stale per-tool numbers: `references/rules/46-*` is HISTORICAL — those defaults no longer exist.

## ⛔ RULE 4: Reload After Compression


After context compression, reload top 5 reference files before continuing testing.

## ⛔ RULE 5: Verification Log Before COMPLETE


Before claiming Phase 0C COMPLETE, generate verification log: tool name → command → output → result. If ANY entry is missing, the test was NOT done.

## ⛔ RULE 7: Self-Check Every 5 Tool Calls


After every 5 tool calls: "Am I executing or just loading?"

## ⛔ RULE 8: Track Every Ref File Execution


**MANDATORY:** Create audit tracker at audit start. Update AFTER EACH ref file execution.

## ⛔ RULE 9: Proven ≠ Theoretical — NEVER Overclaim


A finding is ONLY "proven" if EVERY step in the attack chain has actual tool output demonstrating the result.

**Classification:**
- ✅ curl → 200 + data returned = PROVEN
- ❌ "Attacker would then..." = THEORETICAL
- ❌ "If victim signs..." = THEORETICAL
- ❌ Missing tool output = UNPROVEN

## ⛔ RULE 10: Minimum Severity Threshold for Reporting


**User correction (2026-09-22): "minimal medium baru kt fu temuannya"**

When the user asks for findings or report, do NOT present Low/Info findings as reportable findings. Only present findings that reach **Medium severity or higher**.

**Workflow:**
- During audit: document ALL findings (including Low/Info) in `findings.json` for completeness
- When reporting to user: FILTER — only show Medium+ findings
- If ALL findings are Low/Info: state clearly "Tidak ada Medium+ findings. Target ini well-hardened."
- Do NOT pad the report with Low/Info findings to make it look substantial
- Do NOT inflate severity to meet the threshold

**Exception:** If the user explicitly asks for ALL findings regardless of severity, then show everything. But default assumption is Medium+ threshold.

## ⛔ RULE 19: Minimum 3 Bypass Attempts Before "Blocked" Claim


Before declaring any attack vector "blocked by WAF":
1. Try the direct payload
2. Try with encoding bypass (URL encode, double encode, Unicode)
3. Try with protocol trick (Content-Type switch, chunked, HTTP method change)
4. Try with path manipulation (normalization, backslash, semicolon)
5. Try with header manipulation (Host, X-Forwarded-For, True-Client-IP)

If ALL 5 fail → THEN you may claim "blocked" — but document each attempt.

## ⛔ MECHANICAL ENFORCEMENT


```
PRIMARY PIPELINE (one command — full orchestrator, gate + auto-rework built in):
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-pipeline-orchestrator.py <TARGET> --tech "<tech>"

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
         ⛔ WHOLE-RUN CAP (seen live 2026-10-09, quarterwise): the orchestrator wraps this step in
         `subprocess.run(..., timeout=3600)` and kills it at the hour. Per-tool timeouts exist
         (sqlmap 900s, most ~300s) but there is NO budget ACROSS tools, so on a Cloudflare-fronted
         SPA two slow tools (arjun + sqlmap) can exhaust the whole hour and the step ends with just
         those two on disk — `PIPELINE EXCEPTION: ... timed out after 3600 seconds` + "PARTIAL STATE
         SAVED — resume dari 0C". A resume re-runs the SAME sequence and re-times-out. The step is
         idempotent (merged, above), so partial progress is kept, but you will need several cycles —
         or drive the remaining tools manually into the same `tool-evidence/` + `tools-usage.json`.
         Do NOT narrate a capped step as "the tools failed": nothing failed, the budget ran out.
         Tell the operator which tools got done, which did not, and offer the three options
         (resume cycles / manual drive / accept the manual deep-dive). See
         `references/pipeline-tool-timeout-budget.md`.
Step 1.4 execute-variants.py           → variant-usage.json + variants/*.txt (payload libs fired one-by-one vs recon URLs)
         execute-business-logic.py        → business-logic-usage.json + business-logic/*.txt (15 vectors: IDOR, priv-esc, mass-assign, CSRF, file-upload, cache-poison, 403-bypass, pw-reset, websocket, api-versioning, rate-limit, 3rd-party, source-maps, http-smuggling, biz-logic)
         track-poc-execution.py        → poc-execution.json + poc-evidence/*.txt (ALL matched repos w/ entry point, cap 25, required types first)
         execute-poc-variants.py       → poc-variant-usage.json + poc-variants/*.txt (payload FILES extracted FROM matched PoC repos and fired; CVE-*/exploit*/main.py + code-file fallback)
         execute-references.py         → reference-usage.json + references-evidence/*.txt (C6: reference clues converted to REAL requests: HEADER_ATTACK / ENDPOINT_PROBE / PAYLOAD_INJECT — see RULE 25)
         execute-poc-techniques.py     → poc-techniques-usage.json + poc-techniques-evidence/*.txt (C6b: attack TECHNIQUES extracted from ALL 2223 PoC repos fired at target — see RULE 26)
Step 1.4b prepare_coverage_gate()      → seeds asset-coverage.json (--init) and fills it from REAL
         artefacts (--derive); writes loaded-skills.txt with the track's MANDATED skill set.
         Nothing is assumed: an asset is USED only if its evidence is on disk.
Step 1.5 verify-tool-usage.py GATE     → 13 checks read from DISK (not claims):
         C1 tools-usage.json exists · C2 evidence file per EXECUTED tool · C3 evidence ≥100B ·
         C4 all tools accounted + UNACCOUNTED-status detector · C5 ≥3 tools with real evidence ·
         C6 variants executed + evidence files · C7 PoC executions have output on disk ·
         C8 PoC variant usage + evidence · C9 business-logic vectors executed + evidence ·
         C10 reference-usage.json exists + evidence files ≥30% (refs USED, not just loaded) ·
         C11 poc-techniques-usage.json exists + non-empty + evidence ≥30% (techniques from 2223 repos USED)
         C12 asset-coverage clean for 0B/0C/0D — every mandated skill/tool/ref/payload/cookbook USED
         C13 skill-usage.json — every skill in loaded-skills.txt recorded APPLIED **with evidence**
         Evidence QUALITY: the file must carry its writer's own marker (`# TOOL EVIDENCE:` for
         tools, `# VARIANT EVIDENCE:`, `# BUSINESS-LOGIC EVIDENCE:`, `# REFERENCE-DRIVEN ATTACK
         EVIDENCE`). A same-sized filler file fails C12 — size alone proves nothing.

         Two `asset-coverage.py` traps seen live (2026-10-09, quarterwise):
         (a) `--mark` accepts ONE asset per invocation — passing several `--mark` flags keeps only
         the LAST, the rest stay NOT_RUN. Loop: one `--mark <asset>=<status>` call per asset.
         (b) An N/A reason is INVALIDATED if it contains `skip` / `timeout` / `no time` /
         `gak sempat` / `belum` / `tidak sempat` — so a natural `"documented skip: FUZZ_ONLY"`
         FAILS the check it looks like it satisfies. Write the real reason instead
         (`"binary absent on host"`, `"target is not WordPress"`, `"no gRPC service exposed"`).
         Also: after adding evidence files, re-run `--derive` LAST — it rebuilds the ledger from
         `tools-usage.json` and wipes hand-edited statuses.
         CROSS-ARTEFACT: `# TARGET:` must match the run target and `# TIMESTAMP:` must fall inside
         the run window (from run-meta.json) — borrowed/stale evidence is rejected, not counted.
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
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-exec-tracker.py init <target>

# After EVERY exploit attempt
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-exec-tracker.py log <target> --vector "<name>" --result <result> --evidence <file>

# Before claiming phase complete
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-exec-tracker.py gate <target> --phase <0A|0B|0C-Web2|0C-Web3|0D>
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

## ⛔ RULE 25: References MUST Be USED — Not Just Loaded (C6)


**User correction (2026-09-26): "Ini semua Pipeline dan file, bukan cm d load dan dbaca aja ya, tapi pakai secara maksimal, termasuk all tools, jgn hanya curl aja"**

Loading/reading reference files is NOT enough — the pipeline must make real requests from them. Lesson learned: `load_all_references()` wrote `references-index.json` (88 refs, ~3,884 clues) but NOTHING read that index → it was a dead dump. The user caught this.

**The contract (enforced by Gate CHECK 10):**
1. `force-full-execution.py` → `load_all_references()`: reads ALL 88 refs' CONTENT (not just existence), extracts attack clues (endpoint/header/payload lines), writes `references-index.json`.
2. `execute-references.py` (C6, called by orchestrator after C5): reads `references-index.json`, classifies each clue:
   - `HEADER_ATTACK` → real request with special headers (X-Forwarded-For, X-Original-URL, Host, CRLF)
   - `ENDPOINT_PROBE` → GET/POST to extracted path (strip foreign host: `https://target.com/admin` → `root + /admin`, NOT `//target.com/admin`)
   - `PAYLOAD_INJECT` → inject payload into target param via urllib
   - Fires to target with rate limit + timeout 120s → `references-evidence/clue-NNNN.txt` + `reference-usage.json`
3. `verify-tool-usage.py` **CHECK 10**: `reference-usage.json` must exist, non-empty, ≥30% evidence files on disk. Missing → Gate FAIL → rework runs execute-references.py → HARD BLOCK if still missing.

**Pitfalls:**
- A clues file that is ONLY written and never read is a dead dump — same class of bug as dual-runner drift. Audit who READS each artifact.
- Refs are guides, not payloads: from ~60 classified clues only ~16-20 produce executable requests (methods/pseudocode don't fire). That's normal; what matters is the actionable ones are fired with real evidence.
- Full URLs in clues must be reduced to their PATH against the target root.

**Script:** `execute-references.py` (Global scripts dir). Gate CHECK 10 = "refs used, not just read".

## ⛔ RULE 24: Candidate Review SOP — Temuan = CANDIDATE, 3x Cek, Low→High, Satu-Persatu (MANDATORY)


**User correction (2026-09-26): "Setiap temuan adalah candidate, dan candidate di list setelah semua proses dan tools selesai, setelah dilist, kamu cek kembali mulai dari severity plg rendah sampai tertinggi, apakah temuan candidate tersebut valid, bisa diduplikasi, menimbulkan impact apa, dan step by step yg jelas, minimal 3x cek per candidate, jgn kerjakan sekaligus, tp satu persatu Candidate, tidak apa2 kalau proses nya lama, yg pngt dilakukan secara hati2"**

Every finding is a CANDIDATE. Nothing is a finding until it survives review. The reviewer runs `scripts/review-candidates.py`:

1. **LIST** — all candidates AFTER every tool/phase is done (input = findings.json).
2. **SORT** — severity lowest → highest (Low → Medium → High → Critical). Review order is deliberate.
3. **PER CANDIDATE, ONE AT A TIME, 3x CHECK**:
   - **CEK-1 VALID**: benar bug? Reject by-design / intended-behavior / phishing-social / speculative-info ("could be/may be/missing header/cookie-flags-harding").
   - **CEK-2 REPRODUCIBLE**: evidence file on-disk ≥100B + status HTTP / payload / tool output tercatat. No evidence file = REJECT ("tidak ada evidence di disk").
   - **CEK-3 IMPACT**: impact nyata (data/dana/user/sistem: ssn/balance/admin/ssrf/sqli/xss/ssti/etc) + step-by-step yang jelas. No impact signal or no steps = REJECT.
4. **ONLY candidates that pass ALL 3 checks → verdict READY → masuk ready-candidates.json → report 0F.**

Outputs: `review-candidates.json` (per-candidate cek1/cek2/cek3 + why + verdict + rationale), `review-candidates.md` (human-readable low→high).

**Wiring:** orchestrator 0E → `run_review_candidates()` → 0F `generate_report()` reads ready-candidates.json. If review-candidates fails/never runs → report BLOCKED.

**Pitfalls fixed in dev (2026-09-26):**
- CEK-1 "cookie" blanket-reject was WRONG — payload XSS legitimately contains `document.cookie`. Use context: only reject "missing/absent cookie flags" / "missing security header" patterns, not bare keyword "cookie".
- CEK-3 must recognize SSTI/template-injection (`{{7*7}}`, `${7*7}`) as an impact signal — else real SSTI findings get REJECTED.
- Candidates with empty `source_file` → no evidence file → REJECTED at CEK-2. That is correct (can't reproduce = don't report), not a bug.
- Slow = by design. Do not sprint the review; one candidate fully reviewed before the next.

## ⛔ RULE 39: The Gate Must Be FAIL-CLOSED — a fail-open gate is a finding-generator


**User correction (2026-10-07): "hasil temuannya ngaco, banyak temuan yg hanya formalitas, by design, informational, dan tidak terkait dgn keamanan data, user, sistem, business logic ataupun dana/keuangan."**

Root cause found in `finding_gate.py`: `verdict = "REPORT"` was the **default** (fail-open), impact
regexes ran over the whole text **including the test/vector label**, "proof" accepted `Exit code: 0`,
and there was no junk filter — so a **test file's name** scored 16 (code-exec+ssrf) and tool errors
became findings. On the real `gated.json` (83 candidates) the old gate emitted **12 REPORT**, all junk.
Separately, 0E fed the **raw** `findings.json` to the report chain (gate bypassed) and 0F **wrote a
report even with 0 findings** ("No findings … ✅ All steps completed") — a false completed audit.

**Rules — apply to any script gate that classifies findings (REPORT/DOWNGRADE/DROP):**
1. **Default is DOWNGRADE/DROP, never REPORT.** A finding must EARN REPORT with impact **AND** proof.
2. **Strip labels first** (test/vector/`Target:`/`Tool:` scaffolding), then match impact regexes on
   the finding's *own claim* — otherwise the procedure name drives the score.
3. **"The tool ran" is not proof.** Require an HTTP status line, a response body, an observed state
   change, or a leaked value. `Exit code: 0` alone is **not** evidence.
4. **Filter non-findings and junk**: tool errors (`command not found`, `curl: … failed`, `timed out`,
   `traceback`), reference/payload listings (`Ref File`, `Payloads (20 loaded)`, `Output`), and
   metadata-only scaffolds. Skip self-generated sources (`REPORT-survivors.md`, `gated.json`) and
   dedupe — or the gate feeds on itself.
5. **Report only from the gate's survivors**: `gate → survivors.json → validate → report`. Never hand
   the raw candidate list to the report step. Gate error ⇒ **STOP**; 0 survivors ⇒ **suppress report**.
   A "no findings" report that still reads "all steps completed ✅" is worse than silence.
6. **Verify with a control pair**: one garbage + one real entry must split (junk→DROP, real→REPORT).
   **A gate that never returns 0 is not filtering.** Re-run it on the last engagement's artifacts
   after any change to the gate or 0E.

Detail, evidence, and the measured before/after: `references/finding-gate-fail-open-2026-10-07.md`.

