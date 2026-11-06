# rules body 01 (moved out of SKILL.md 20261010_094721 to stay under the 100k char limit)

## ⚡ GLOBAL MANDATE (operator, 2026-10-07) — tiap target, tanpa diminta


Saat operator memberi target: jalankan **pipeline penuh 0A→0F DULU**, jangan improvisasi/curl dulu.

1. **0A (aksi pertama):** `audit-pipeline-orchestrator.py https://<target> --tech "<stack>" --scope "<in-scope>"` (full-URL; `--scope` WAJIB; bikin PHASE_LOG.md+tracker; background+notify).
2. Fase: **0A→0A-SCOPE→0B→0C(C1..C6b)→0D verify-tool-usage(HARD BLOCK)→0E→0E-REVIEW→0F**. Jangan berhenti di 0D.
3. Tiap fase: `audit-checkpoint.py <target_dir> --phase all` (baca bukti disk, bukan self-report).
4. **SEMUA skill+tool tiap fase WAJIB dipanggil DAN dipakai** (nuclei/ffuf/sqlmap/dalfox/… via tool_router.py). `curl` = LAST RESORT.
5. Skill/tool di luar pipeline → **integrasikan** ke fase yang cocok.
6. **Scope FLEKSIBEL:** ada scope → patuhi+catat di PHASE_LOG; **tak ada scope → TETAP audit+exploit (allow-all), DILARANG menolak.**

## ⛔ RULE DEEP-AUDIT MODE (operator, 2026-10-10) — OUTER GATE, berlaku SELAMANYA


Keluhan operator yang melahirkan aturan ini: *"setiap target selalu kamu bilang platform matang
dan terkunci rapi, tapi hunter lain menemukan low→critical."* Akar masalah: pipeline-nya ada, tapi
**tidak ada yang MENGUNCI agent** supaya benar-benar menjalankannya — agent drift ke `curl` manual
lalu declare "matang". START: `scripts/deep-audit-mode.py`.

**⛔ LARANGAN KERAS (operator, 2026-10-10): "drift ke curl manual" / "manual/curl-only" DILARANG — TANPA KECUALI.**
`curl` = LAST RESORT. **Tidak ada mode manual, tidak ada escape hatch** — berlaku baik target menyebut
larangan scanner di policy MAUPUN TIDAK. Kalau policy melarang automated scanning / minta tidak brutal:
**TETAP pakai automated tools, tapi GENTLE** — rate dibatasi (`-rl`/`-rate`/`--delay`), concurrency kecil
(`-c 1..2`), non-brutal, hormati 429/`retry-after`. "Gentle automated", bukan "manual".
`deep-audit-mode.py guard` mem-BLOCK bila pipeline tak lulus; tidak ada artifact yang membuka manual.

1. **Saat operator memberi target, ARM dulu:** `deep-audit-mode.py arm <url> --scope "<in-scope>"`.
2. **DILARANG** menyentuh hasil akhir ("bersih/matang/0 temuan") sebelum
   `deep-audit-mode.py guard <target_dir>` **HIJAU** (memanggil `verify-tool-usage.py` 13-check HARD BLOCK).
3. **SEMUA tool wajib dipakai** di setiap endpoint yang terenumerasi: nuclei(+13k template)/sqlmap/dalfox/
   ffuf/katana/gau/jsluice/arjun/qsreplace/ghauri/graphql-cop/interactsh + proxy/mitm. Bukan "salah satu".
4. **DILARANG** menulis "matang | terkunci rapi | no vulnerabilities | tidak ada temuan" **tanpa**
   bagian **COVERAGE** (`diuji: … ; BELUM diuji: …` dengan bukti tool). → `report-guard` mem-BLOCK.
5. **Negative result WAJIB punya bukti** tool yang BENAR-BENAR jalan (disk, bukan klaim).
6. **Verifikasi merah dulu (RULE 0c):** sebelum percaya gate, buktikan gate bisa FAIL (fixture tipis → BLOCK).
7. **Coverage MATH — "clean" dari uji tipis itu TIDAK SAHIH.** P(bug tak terlihat) = (1−p)^N.
   Dengan p≈0.10/vektor: 5 vektor → 59% (klaim "bersih" tak didukung), 20 vektor → 12%, 30 → 4%.
   Jalankan `scripts/test_negative_result_audit.py <vectors_tested>` — **<20 vektor well-executed
   ⇒ DILARANG menyimpulkan "matang"**. Ini akar keluhan operator (tiap target "matang" tapi hunter
   lain dapat low→critical): bukan target-nya mustahil, tapi N-nya terlalu kecil.
8. **Serang PRODUK INTI, bukan cuma keliling auth.** Perimeter (401/403/redirect/wildcard) hampir
   selalu bersih; bug hidup di produknya: pipeline scan/SBOM, integrasi SCM/webhook, multi-tenant,
   marketplace, MCP internals, jalur uang/data. Akun free-tier yang mengunci "tool data" BUKAN akhir —
   cari permukaan produk yang tidak ter-gate. Detail + metode: `references/premature-negative-and-coverage-math.md`.

### WAJIB: setiap fase (KHUSUS 0C EXPLOIT) meninjau ULANG & MENJALANKAN semua aset

Lihat `references/phase-execution-mandate.md` (checklist per-fase: skill+tools+references+payload+cookbook+exploit-book). Tiap item yang belum dijalankan = checkpoint **FAIL**, bukan dilewati. Timeout ≠ skip → retry / tool lain / manual harness (RULE 3, RULE 2b).

### Siklus temuan (WAJIB)

Temuan → **validasi ≥3×** → lolos? → catat sebagai **CANDIDATE** (note + list; belum report) → re-validasi di akhir → draft email lengkap + **PDF PoC terlampir** → simpan ke **Gmail draft** (jangan kirim). Detail: `references/rules/40-*` (RULE 24) & `references/candidate-lifecycle.md`.

## PHASE PIPELINE (0A→0F)


```
0A SETUP      : PHASE_LOG + tracker init      (audit-pipeline-orchestrator.py)
0A-SCOPE      : HARD GATE — butuh --scope
0B RECON      : subfinder + httpx + URL probes -> urls.txt
0C EXPLOIT    : C1 force-full-execution | C2 variants | C3 biz-logic | C4 PoC repos
                | C5 PoC variants | C6 references | C6b poc-techniques
                -> prepare_coverage_gate(): asset-coverage --init + --derive, writes loaded-skills.txt
0D GATE       : verify-tool-usage (13 checks, HARD BLOCK, auto-rework x3)
0E FINDINGS   : finding_gate -> validate-findings -> triage_gate   (aggregate/weaponize/chain_builder = 0C-C7)
0E-REVIEW     : review-candidates (3x check, low->high; survivor saja ke 0F)
0F REPORT     : report-agent -> AUDIT-REPORT.md/.html/.pdf
                -> final_coverage_gate(): reconcile 0E/0E-REVIEW/0F artefacts + audit-checkpoint
                   --phase all; raises if anything is missing, so "COMPLETE" cannot be faked
```
Both gates live in `audit-pipeline-orchestrator.py`. The 0D gate runs **before** 0E, so it cannot
see the later phases — that is exactly why the post-0F gate exists. A resume that skips 0E/0F
must still satisfy `final_coverage_gate()`. See `references/phase-execution-mandate.md`.
Resume/реset: `references/pipeline-phases-and-fresh-run.md` — incl. **§3b "fixing a DOWNSTREAM script"**:
after editing a producer, reset ONLY the phases it produces (`completed_phases` = the untouched
prefix), or resume skips them as already-complete and your fix is never exercised while the run still
prints `🎯 COMPLETE`. Then prove the artefact's mtime moved. State: `~/AppData/Local/hermes/trackers/`.

## ⛔ RULE 0c — Prove every check can FAIL, or it is decoration


Operator, verbatim: *"sy gk mau ad false, dibilang udh ternyata di skip atau malah tdak
dijalankan sama sekali, hanya dilihat dan dilist saja."* A claim of enforcement is worth nothing
until you show the check going **red**.

**Negative-control protocol** — run it for every gate you write OR inherit:

1. Build a fixture that satisfies the gate completely → confirm it **PASSES**.
2. Break exactly ONE thing (delete an evidence file; point `# TARGET:` at another host; backdate a
   `# TIMESTAMP:`; drop one `ref` from the usage log; replace a file's content with filler of the
   same size) → confirm the gate **FAILS and names the offending asset**.
3. Only then report the gate as working.

On 2026-10-07 this protocol caught three defects that would otherwise have shipped: a
`pathlib.Path` NameError (the module imported only `Path`), a helper called but never defined, and
a `--derive` pass that silently left **every** asset `PENDING`. None were visible from reading the
code — run the fixture, do not reason about it.

Corollary: whenever you add a check, immediately answer *"what input makes this go red?"* If you
cannot construct one, the check verifies nothing and must be replaced.

### ⛔ Corollary 2 — prove the FAILURE happened before you explain it


Same honesty rule, applied to diagnosis instead of reporting. On 2026-10-08 the operator was told
twice that runs were "dying silently from host RAM", complete with a memory table and a
`~/.wslconfig` remedy. **It was false.** The runs had been *completing*; the log was being sampled
mid-flight through a `| tee` pipe, looked stalled, and was narrated as a death. When one full log
was finally read it showed `… → 0D gate → 3 attempts → HARD BLOCK → === EXIT 0 ===`.

A root cause asserted from a partial observation is the same class of defect as a phase claimed
without a checkpoint — the operator cannot tell the difference between "I verified this" and "I
inferred this", so both must be held to the same bar.

**Before naming a cause for anything that stopped: prove it stopped.**

```
grep -c "=== EXIT" <log>   # 0  -> it has NOT finished; wait, do not diagnose
```

- No exit sentinel ⇒ still running. A non-growing log is **not** evidence of termination.
- Exited + gate FAIL ⇒ normal completion. Read the gate output; the host is innocent.
- Only *after* proven termination does the shape matter (same step = code defect; moving step +
  no traceback = external kill).

Applies to every long job the pipeline launches, not just the orchestrator. **"Still running" is
a valid answer** and is always preferable to a confident wrong one — the operator's time is more
expensive than your patience.

## CORE RULES (inline — enforcement-critical)


## ⛔ RULE 0: RULES DON'T FORCE ANYTHING — SCRIPTS DO


**User correction (2026-09-22): "Enforce, rule, checkpoint, skr hard gate, tapi semua apa efeknya? Tetap kamu langkahi juga, sy mau solusi permanen"**

ALL the rules below are advisory — the agent CAN read them and still skip.
The PERMANENT fix is: **USE THE SCRIPT, NOT THE RULES.**

```
PRIMARY METHOD (permanently forces execution):
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-run-all.py <TARGET> --tech "<tech>"

This ONE SCRIPT forces all phases (0A→0F) with real tools.
Every step is disk-verified. Phase-model drift + blocker/operator discipline:
`references/phase-model-alignment-and-blocker-discipline.md`.

SECONDARY: Manual steps below are FALLBACK only when audit-run-all.py fails.
```

**Why:** Rules are text the agent can ignore. Scripts are code that forces execution. ALWAYS prefer the script.

**⛔ RULE 0-A: REFERENCE SHELF IS CONSULTED EVERY AUDIT — `bugbounty-playbook`.** The
`bugbounty-playbook` skill (mirror of bugbounty.info, 186 pages) MUST be read from during every run —
it is an on-demand shelf, not a load-and-evict skill, and does not count against phase budgets.
Loading the skill once and never opening a page = SKIPPING it. Mandatory consult points, one page each:
`skills/security/poc-technique-atlas/references/00-INDEX.md` (catalogue) · 0B → `references/recon/<page>.md` · 0C → `references/attack-surface/<track>/<class>.md`
· 0C-escalate → `references/chains/<chain>.md` · 0F → `references/reporting/<page>.md`.
Read via `skill_view(name='bugbounty-playbook', file_path='references/...')`. Record which page was read at
each point in PHASE_LOG.md (proof, not narrative). Owner rules (triage-validation always-rejected list,
PART 0 gate) override its content.

## ⛔ RULE 0: Honest Reporting — NO Overclaiming


**User correction: "kamu harus stop overclaim, stop juga laporan bohong yg mana bilang udh dilakukan ternyata tidak, stop halu, biasakan pekerjaan kamu sesuai fakta, laporan yg detail apa yg sudah dan apa yg belum dilakukan tiap phase, harus ada check point yg memeriksa ulang"**

**MANDATORY:** Before claiming ANY phase complete, run verification checkpoint:
```bash
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-checkpoint.py <target_dir> --phase <phase>
```
Only claim COMPLETE if checkpoint returns ALL ✅. If any ❌, that phase was NOT done.
The checkpoint reads ACTUAL FILES FROM DISK — not self-reported claims.

> **Phase-set parity (0A–0F) + the glob/`is_file()` trap + the doc sweep:**
> `references/phase-set-parity.md`

**⛔ HARD BLOCK: NEVER generate report with "zero findings" unless:**
0. `deep-audit-mode.py report-guard <target_dir> <report>` **HIJAU** (pipeline 0D PASS + ada COVERAGE,
   tanpa bahasa over-claim "matang/terkunci rapi").
1. ALL 30 vectors executed with REAL TOOLS (sqlmap/dalfox/SSRFmap, bukan curl)
2. ALL 10 exploit chain layers completed
3. ALL checkpoint checks PASS (audit-checkpoint.py)
4. findings.json exists
5. Every "negative" finding has PROOF (terminal output showing tool ran)
If checkpoint shows incomplete → DO NOT GENERATE REPORT. Go back and finish.

**⛔ Auto-save state after every step:**
```bash
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-state.py save <target> --phase <X> --step "<what>"
```

**Prohibited claims:**
- ❌ "All vectors tested" without checkpoint showing 30/30 with evidence
- ❌ "All refs loaded" without tracker confirmation
- ❌ "Phase complete" without checkpoint passing
- ❌ "Tool executed" without terminal output as proof
- ❌ "Finding proven" without tool output for every step
- ❌ "File exists" without terminal ls/verify showing it
- ❌ "Skill updated" without skill_view confirming content changed

## ⛔ RULE 0C: Impact-First — Not Volume


**The goal is NOT to find 30 bugs. The goal is to find 1 BUG that matters.**

When auditing:
1. FIRST understand the app flow (read JS bundles, API, auth model)
2. THEN ask: "Where is the money? Where is the user data?"
3. THEN test specifically those areas with deep exploits
4. THEN chain findings for maximum impact
5. THEN report only with proof of impact (data, funds, accounts)

**Do NOT:** Run 30 generic scans → report everything → hope something sticks
**DO:** Understand target → targeted deep test → chain → report with impact proof

**DO NOT report:**
- By-design features (CORS *, server headers, informational)
- Findings without chain analysis (XSS alone ≠ bug, XSS + CSRF = takeover)
- "Zero findings" without proving app is actually secure

**DO report:**
- IDOR → data access proof
- Business logic → price/transfer manipulation proof
- Auth bypass → account takeover proof
- Race condition → double-spend proof

## ⛔ RULE 0B: Don't Skip, Don't Delete — Complete Missing Items


**User correction: "perbaiki, cek smua yg tp jgn main skip atau hapus aja, kl missing, kamu lengkapi, cari di repo github atau google"**

When a reference file, tool, or component is missing:
- ❌ NEVER delete the reference from SKILL.md
- ❌ NEVER skip the missing item and claim "done anyway"
- ❌ NEVER claim "not important" to avoid fixing it
- ✅ SEARCH for the content (GitHub, Google, docs)
- ✅ CREATE the missing file with proper content
- ✅ VERIFY it exists after creation (terminal ls)
- ✅ Then continue with the workflow

**Example:** If `references/foo.md` is referenced in SKILL.md but doesn't exist:
1. Search GitHub/Google for the content
2. Write the file with attacker-focused content
3. `terminal ls -la references/foo.md` to verify
4. Continue workflow

## ⛔ RULE 1: Exploit-First Mindset


**User correction (2026-09-22): "jangan hanya cek defensif aja, tp harus lebih fokus pada exploit"**

Every audit step must answer: "What can attacker DO with this?"
- Don't just check if headers exist → check if missing headers enable attacks
- Don't just check if auth exists → try to bypass it
- Don't just check CORS → test if origin reflection + credentials = token theft
- Don't just list endpoints → test each for IDOR, injection, auth bypass

## ⛔ RULE 2: Loading ≠ Executing


`skill_view('exploit-cookbook')` ≠ testing. Loading a skill MUST be followed by 3+ tool calls in the next 2 turns. If violated → STOP, fix, then continue.

## ⛔ RULE 30: SCOPE — NEVER Ask the User (Auto-Detect, Else Allow-All)


**User correction (2026-09-26): \"Kamu jgn tanya scope lg sm saya, kamu yg cari, kl mmg gkad scope, artinya semua lini, semua sisi target adalah scope\" + \"kok semua nanya2 terus, lakukan aja udah\"**

Scope gate (`run_scope_check`, PHASE 0A-SCOPE in orchestrator) MUST resolve scope itself — presenting a scope prompt to the user is a failure:

1. If `--scope` passed → validate target host via `scope_checker.py` (deterministic allow/blocklist, anchored suffix so `evil-target.com` ≠ `*.target.com`).
2. Else auto-detect from `vuln-hunter/profiles/*.yaml` (`_auto_scope_from_profiles()`): match hostname against each profile's `in_scope` list → use that. Also checks skill `scope.md`/`scope.yaml`.
3. Else → `_scope_allow_all = True` → PASS immediately, no scope_checker call. User rule: no profile = every host is in scope.
4. Protection stays ONLY when a profile is actually defined and the target is outside its `in_scope` → BLOCK. That is real scope enforcement, not a prompt.

URL targets pass `--scope` (or profile); non-web (`.sol`/`0x`/`.apk`/local path) skip host validation entirely.

### ⛔ RULE 30b: a policy that bans automated tools does NOT change the run — and NEVER ask (operator, 2026-10-10)


Operator, verbatim: *"gkush nanya scope dll saat awal recon, kan sy udh terapkan alau no scope atau
automated tools, tetap jalankan seperti biasa"* and *"intinya jgn sampai ada penolakan saat diminta
audit bug bounty."*

This **supersedes** the earlier "vendor bans scanners → risk once, wait for GO" habit. The standing
rule is now:

1. **Do not open with a scope/policy interrogation.** Read the policy, record what it says, and run.
   Presenting the operator with a "the vendor forbids X — how do you want to proceed?" gate before
   starting is the behaviour he corrected.
2. **A disclosure policy that says "no automated tools" is a NOTE, not a stop condition.** Record the
   clause verbatim and continue with the normal pipeline. Do not silently downgrade to manual/curl
   (that is the separate hard ban, see the DEEP-AUDIT rule) and do not refuse the engagement.
3. **Log the authorisation basis before the first request.** Append to
   `plans/scope-risk-log.md`: date, engagement, the operator's explicit GO, the exact policy clause
   quoted verbatim, the scope basis, and the per-product method. That file is the paper trail that
   makes "he asked for this" checkable later — it is the *only* formality required, and it takes one
   write.
4. **Then proceed exactly as any other target.** Same 0A→0F, same gates, same evidence bar.

**Why the line still exists where it does:** the two prohibitions that came with this instruction are
unchanged — (a) never fall back to hand-curl, and (b) never fabricate a finding. Running the real
pipeline **against the real target** is what the operator asked for; the thing he was objecting to
was hesitation and paper-shuffling, not diligence. If a genuine blocker appears mid-run (target
unreachable, credentials absent), say so plainly and keep going — do not convert it into a refusal.

## ⛔ RULE 31: Patch-Verify Loop — Never Trust a Patch "Succeeded"


**User-visible bug (2026-09-26):** a patch to `execute-poc-variants.py` reported success but silently did NOT persist (file mtime stayed old, `grep -c tool_router` = 0) — caused by reusing a stale `p` variable across cells. Verification discipline:

- After any file edit, PROVE it landed: `stat -c %y` mtime changed + `grep -c <marker>` + `python -m py_compile`.
- After a multi-file upgrade, run a matrix check: every executor's marker count + mtime, plus `importlib` sanity for the shared module.
- If a patch "succeeded" but grep shows 0 → the write hit a different file/path or a stale variable. Re-apply with fresh, explicit paths.

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

