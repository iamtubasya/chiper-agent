# rules body 02 (moved out of SKILL.md 20261010_094721 to stay under the 100k char limit)

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

## ⛔ RULE 39b: A gate must never score its OWN echo — unwrap, then strip scaffolding


**Same session, next failure (2026-10-09).** After RULE 39 fixed the fail-open default, the real
83-record `gated.json` *still* produced 22 PASS — because the records scored were not findings but
**echoes of the gate's own output**, re-ingested from `REPORT-survivors.md`:

```
{"title":"# Vector 4: RCE/SSRF",
 "text":"{\"title\":\"# Vector 4: RCE/SSRF\", \"text\":\"**Target**: …\\n**Tool**: curl\\n**Exit code**: 0\"}",
 "impacts":["code-exec","ssrf"],"impact_score":16,"has_evidence":true}
```

1. **The nested JSON *is counted as proof** — an "actual JSON body" pattern matched the echoed
   record itself; `"impacts":["code-exec","ssrf"]` handed the impact class over for free.
2. **Labels survive JSON encoding** — `**Target** … **Exit code**: 0` sit inside a string, so a
   line-anchored label strip never sees them.
3. **Gate metadata looks like content** — `- impact classes: …`, `evidence present: True`,
   `"text":`, code fences.

Class of bug: **a gate that reads a file it (or an earlier step) wrote will grade its own
scaffolding as signal** — the same family as "skip self-generated sources" (RULE 39 §4) and the
dead-dump trap (RULE 25).

**Rules — before any scoring regex runs, in BOTH gates (`finding_gate` and `triage_gate`):**
1. **`unwrap()`** — if `text`/`evidence` is itself JSON, peel inner keys
   (`text|evidence|description|details|body|poc|repro`) up to 3 levels (handle a list too). Score the
   *original* finding, never the envelope.
2. **Strip labels inline, not just at line start** (`vector N: …` anywhere in a line).
3. **Scrub scaffolding** — drop gate/report metadata lines (`impact score|impact classes|evidence
   present|source|severity|verdict|reasons|drop_flags`), JSON keys (`"title":|"text":|"impacts":`),
   not-a-finding titles (`Ref File`, `Payloads (\d+ loaded)`, `Output`, `Index`,
   `REPORT-WORTHY FINDINGS`, `Survivors`), `read_file(` lines and fences; require **≥60 chars of
   surviving content** or it is metadata, not a finding.
4. **Dedupe + skip self-sources** (`REPORT-survivors.md`, `gated.json`, `survivors.json`).

**MECHANICAL 7-QUESTION GATE (new — `triage_gate.py`, wired as E5 between validate and report):**
the `triage-validation` skill's 7 questions are now **enforced, not advised**. PASS requires **all 7
YES** (Q1 real impact · Q2 proven request/response · Q3 in-scope · Q4 chain reaches · Q5 not
by-design · Q6 not info/hygiene · Q7 not tool-error). Chain:
`gate → survivors.json → validate → triage → passed-findings.json`; **0F reads `passed-findings.json`
ONLY**, and 0 PASS ⇒ an explicit **NEGATIVE report** (not silence, not a fake "no findings" shell —
see RULE 41).

**Control-pair validation (extends RULE 0c):** after any gate edit assert BOTH directions — a junk
corpus must yield 0 PASS, and a real finding (`GET /api/patient/2 → HTTP/1.1 200 … {"ssn":…} another
patient PII, reproducible`) must PASS 7/7. A gate that cannot return 0 is not filtering; one that
fails the real case is over-filtering.

**Related — budget-safe reachability:** an always-on phase lists only what runs *every* engagement;
conditional skills go in `bb-audit-launcher/references/situational-skill-router.md` (condition → skill,
loaded on demand) so ~60 correct-but-unreachable skills stop being list-only without bloating the
120 KB phase budget.

Detail, code, and the measured before/after: `references/mechanical-triage-gate-and-self-echo.md`.

## ⛔ RULE 41: A gate must not block on a CORRECT outcome — and a refusal must still leave a record


**Operator, 2026-10-08.** After every check finally passed, the run still hard-blocked at 0F
because the pipeline had done the *right* thing: 559 candidates → 105 READY → **0 cleared
validation**, so 0F correctly refused to write a report. `final_coverage_gate` then failed on
`0F:report:AUDIT-REPORT.md [NOT_RUN]` — so an honest, fully successful **negative** audit could
never be marked complete. RULE 39 (below) guards against reporting what was not proven; this
rule guards against the mirror failure, a gate that only accepts a run which found something.

**"Nothing found" is a RESULT, not an absence.** Silence is the right output for a *claim*;
it is the wrong output for a *record*. Every terminal branch that returns `None` because it has
nothing to do must instead write a "nothing to do, and here is why" artefact, with real counts.
Otherwise a correct negative is byte-for-byte indistinguishable from a crash — and the gate
cannot tell them apart either. Create the marker dirs it looks for **present but empty + README**,
so "no drafts because no findings" is distinguishable from "the drafting step never ran".

Four questions to run whenever a gate blocks and the run looks fine:

1. **Does the artefact exist on disk right now?** If not, does anything ever WRITE it?
   (`grep -rn "<name>" scripts/`) — a name nothing produces is an unpassable requirement.
2. **Can the thing it demands exist AT THIS PHASE?** A 0D gate demanding 0E-phase skills
   (`triage-validation`, `onchain-finding-verification` → need `findings.json`) is impossible by
   construction. Split the mandate: `loaded-skills.txt` (0D) vs `late-skills.txt` (final gate).
3. **Are all consumers reading the SAME bar?** 0F demanded drafts from `ready-candidates.json`
   (105) while the report used `validated-findings.json` (0) — two bars, so the gate demanded
   drafts for findings the report had already refused to make. `ready` ≠ `validated`.
4. **Does empty mean FAILED, or NOT APPLICABLE?** A boolean written `X > 0 and all(...)` is
   `False` for the empty case. Empty `poc-execution.json` means "no PoC applied" = N/A, not fail.

Also applies to `audit-checkpoint.py` — it carried four of these at once (0B web-recon files on a
contract target, 0F severity/CWE in a negative report, the dead name `candidates.json`, the C4
empty-list trap) in a *different script* from the gate already fixed, which is why they survived
the first pass. When you fix a gate, grep for its siblings.

Measured end state after all of it: `0A→0F`, 0D gate PASS, `final_coverage_gate` PASS,
`audit-checkpoint 33/33`, report = honest negative.
Detail + code: `references/terminal-state-and-phase-appropriate-gates.md`.

**⛔ Corollary — "the negative report EXISTS" is not the same as "it is sendable".** Verified
2026-10-10: the gate chain produced a correct negative report in **851 bytes** and the operator's
next question was *"review laporan"* — because it named the funnel counts but never said **what was
tested**, **why each READY candidate failed**, or **what was out of scope**. Every one of those facts
was already on disk. A negative report is the artefact that gets forwarded and re-read months later;
write it as a deliverable: result → cause → **coverage per class with the artefact cited** →
**per-candidate rejection reason** → **boundary / N-A grouped by reason** → evidence index.
`N/A` is a boundary, never coverage. Full shape + the four gaps:
`references/negative-report-substance.md`.

## ⛔ RULE 40: Target the CANONICAL host — a bare-host 301 turns every path tool into a false-positive machine


Symptom (riello-ups.com.ar, 2026-10-08): the orchestrator was pointed at `https://<bare-domain>`,
which **301-redirects EVERY path** to `https://www.<domain>/<path>`. Result: ffuf/gobuster matched
**every** path (all 301), nuclei/arjun/dalfox produced zero real signal, and gobuster itself printed
*"the server returns a status code that matches ... for non existing urls"* — the entire 0C batch was
noise against the redirect, not the app. Budget burned, no coverage.

Rules:
1. **Resolve the canonical host BEFORE 0A.** `curl -sI https://<host>/` — if it 3xx-redirects to
   another host, run the pipeline at the **redirect target** (usually `www.`), not the bare host.
   Check both `http://` and `https://` variants first.
2. **A 301-to-elsewhere is not a finding by itself** — the real app lives at the target. BUT a 301
   whose `Location` is `http://…` (scheme downgrade) IS worth recording.
3. **Filter cross-domain noise from recon.** On a multi-country site, hreflang / `<link rel=alternate>`
   injects foreign hosts (`*.ru`, `*.it`, …) into katana/gau output — scope the URL list to the
   in-scope host (katana `-fs rdn`, or grep-filter) before feeding variants.
4. When a per-path tool returns *"everything matches"* / wildcard-length warnings, **STOP** — you are
   scanning a redirect, not the app. Re-point and re-run; never "triage" the noise.
5. **Fragile origin ⇒ low concurrency.** Some targets drop connections under modest concurrency
   (a 15-thread nuclei pass briefly knocked riello-ups.com.ar offline). That is *not* something to
   exploit — it is a signal to run serial / 1–3 concurrency for that engagement.

## ⛔ RULE 42: A terse continuation names no target — reconstruct the engagement from DISK first


Messaging-platform operators reply with two-word continuations into a **fresh session with no prior
context** (*"Nggak ada temuan sama sekali ya / Kamu saja yg buat, teruskan ceknya sampai tuntas semua
sisi"*). Do not ask which target, and do not answer from imagination. Four reads settle it:
newest `sessions` row in `%LOCALAPPDATA%\hermes\state.db` (recover the pending ask verbatim) →
newest dir in `_progress/` by mtime → that dir's `TRIAGE.md` + `findings.json` (including the items
the gate **DROPPED**) → `deep-audit-mode.py guard <dir>`.

That last call is the **fastest truth instrument available**: `⛔ BLOCKED — tools-usage.json not
found` is a positive fact about the previous session — the earlier "0 findings / clean" statement
was **never gated**, so the honest report to the operator is *"uji belum tuntas"*, never *"platform
bersih"*. Then `arm` + launch the orchestrator backgrounded into the engagement dir; watch it with
the RULE 0c Corollary-2 termination test, not a narrated log tail. Full recipe, exact Python, and
the pitfalls (incl. the recursive-`find` timeout, and answering the operational question instead of
re-litigating identity/system-prompt content): `references/engagement-identification-from-terse-operator-message.md`.

## Config Requirements


- `context_length`: 1,000,000
- `max_iterations`: 200
- `max_tool_calls`: 300

---
*Created: 2026-09-20 | Updated: 2026-09-26 (RULE 27 multi-session resume; caps →150)*
*Source: User-identified failure modes + overclaiming corrections*

---

### Track web3 WAJIB memuat `defi-exploit-forensics-in-pipeline.md`


Tabel insersi per-fase: **0B** pattern-prior sebelum baca kode → **0C** apa yang dites + bentuk
hasil positif → **0E** cek apakah insiden nyata sudah mendemonstrasikan teknik ini → **0F** tx
hash exploit jadi bukti yang bisa dikutip triager.

**Enforcement (bukan sukarela lagi, sejak 2026-10-07):**
- `loaded-skills.txt` untuk track web3 memuat `defi-exploit-forensics` + `onchain-finding-verification`
  + `live-vs-source-bytecode-forensics` → masing-masing WAJIB punya entri `applied:true` + `evidence`
  di `skill-usage.json`, atau **CHECK 13 FAIL di 0D**.
- Kelas `refs_web3` di `asset-coverage.py` menuntut teknik/case library benar-benar **menembakkan
  ≥1 request** (`reference-usage.json`), atau **CHECK 12 FAIL di 0D**.

### Aturan yang berlaku ke SETIAP track (dari run web3 nyata 2026-10-08)


Empat pelajaran yang lahir dari audit Relay v3 Router — semuanya membuat pipeline **tampak jalan
padahal tidak**. Detail + kode: `references/track-aware-gates-and-run-lifecycle.md`.

1. **Manifest harus track-aware.** Daftar aset wajib yang web-sentris menggagalkan 49/76 aset
   pada target kontrak (subfinder/httpx/nuclei tak mungkin jalan tanpa hostname). `needed_for()`
   = satu-satunya sumber kebenaran; web-only dibuang di track kontrak, SC-only dibuang di track
   web. Uji **dua arah** (web2 PASS, web3-tanpa-corpus FAIL, web3-dengan-corpus PASS).
2. **Exit code ≠ status.** slither/echidna/aderyn/medusa **exit non-zero justru saat BERHASIL
   menemukan isu**. Pakai *completion marker* yang mengalahkan exit code — tapi cek
   `FAILED_USAGE` LEBIH DULU, jangan sampai output `--help` dicap EXECUTED.
3. **Verifikasi APA yang dianalisis**, bukan bahwa tool-nya jalan. `slither` exit 0 dengan
   "6 results" pernah berarti ia menganalisis **library yang salah**. Baca `# COMMAND` di header
   bukti sebelum percaya — terutama sebelum melaporkan hasil **negatif**.
4. **Kill parent ≠ kill cucu (Windows).** `force-full-execution` yang jadi yatim tetap selesai
   dan menulis `force-state=complete` → run berikutnya **skip seluruh fase SC**. Saat re-run:
   kill tree (`/T`) + hapus state + hapus bukti **bersamaan**; menghapus salah satu saja lebih
   buruk daripada tidak membersihkan sama sekali.

**Jangan pernah melonggarkan gate yang FAIL.** Tiga run berturut-turut diblokir dan ketiganya
benar; tiap kegagalan menunjuk cacat nyata di script dan diperbaiki di sumbernya. Gate yang
menolak melaporkan pekerjaan yang tidak dilakukan adalah **fiturnya**, bukan bug.

