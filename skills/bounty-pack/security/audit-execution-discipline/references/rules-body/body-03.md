# rules body 03 (moved out of SKILL.md 20261010_094721 to stay under the 100k char limit)

### ⛔ Checklish aset WAJIB track-aware — kalau tidak, target kontrak gagal palsu


Terbukti 2026-10-08 pada run relay.link: manifest-nya **web-sentris**, jadi target **kontrak-only**
(0x…) dituntut `subfinder/httpx/nuclei/ffuf/dalfox/…` yang mustahil jalan tanpa hostname →
**49 dari 76 aset NOT_RUN → 0C FAIL**, padahal tidak ada yang salah dengan targetnya.

Aturan yang berlaku sekarang (`asset-coverage.py`):

| track | 0B recon | 0C tools |
|---|---|---|
| **web** (domain/URL) | subfinder, httpx, katana, gau, … (seperti biasa) | nuclei, ffuf, sqlmap, dalfox, … |
| **web3/kontrak** (`_is_web3()` dari `run-meta.json:tech`, fallback file `.sol`) | **0 aset** — semua web-only di-set N/A, bukan FAIL | **wajib `slither`, `aderyn`, `myth`, `echidna`, `medusa`** |

`WEB_ONLY` = aset yang tak ada artinya tanpa host → di-skip pada track kontrak. `SC_ONLY` =
tools SC → di-skip pada track web (jangan sampai audit web2 dituntut slither).

**Pelajaran umumnya:** setiap kelish aset di manifest harus punya jawaban untuk pertanyaan
*"bisakah ini jalan di SEMUA tipe target yang pipeline terima?"* Kalau tidak, ia akan jadi
**false-FAIL** — dan false-FAIL sama merusaknya dengan false-PASS, karena auditor akan
terbiasa mengabaikan gate.

### ⛔ Tool yang exit≠0 karena MENEMUKAN isu bukan "error"


`force-full-execution.py` sempat menilai status dari exit code saja, sehingga run
slither yang **berhasil menemukan 68 isu** dicatat `RAN_WITH_ERROR`. Analyser kontrak
memang keluar non-zero justru saat bekerja:
slither (ADA deteksi), echidna/medusa (assertion GAGAL = temuannya), aderyn.
Fix: `_SC_DONE_MARKERS` — marker penyelesaian (`analyzed (`, `result(s) found`,
`running 88 detectors`, `report printed`, `total calls`, `assertionfailed`,
`test(s) passed`, `test summary`, `fuzz: elapsed`, `analysis was completed`)
**mengalahkan** exit code dan menetapkan `EXECUTED`.

Jangan pernah menyimpulkan "tool gagal" dari exit code pada analyser — cari marker
penyelesaian di body bukti, dan pastikan `# COMMAND:` menunjuk file yang benar.

## ➕ Additive companion — `autonomous-exploration` (optional sidecar)


> Purely additive. Nothing above changes. These tools only CREATE files under
> `<target_dir>/_graph`, `/_plan`, `/_traces`, `/_traffic`; they never modify pipeline scripts,
> and the 0A–0F pipeline runs identically with or without them.

- `dualgraph.py` — asset graph + exploration graph + anchors (SQLite); coverage/lineage queries
- `chainplan.py` — dependency-gated step ledger; `next` = the ONLY step you may dispatch now
- `tracestore.py` — cross-step trace exchange (reuse raw observations from other steps/subagents)
- `trafficrec.py` — on-demand mitmproxy recorder (automatic PoC transcript, port 8081)

Load skill **`autonomous-exploration`** when you need queryable coverage, a dependent multi-step
chain, or automatic PoC capture. Optional — a normal run does not require it.

> This is a *tooling sidecar*, not a rule change: the execution discipline above still governs.
> If a rule and a sidecar convenience ever conflict, the rule wins.

---

## ➕ Runtime execution policy (2026-10-10)


Unbounded runs, stall = WARN (never kill), auto-diagnose → auto-fix → **re-run** the tool,
and **no curl fallback** (a vector that cannot run is NO RESULT, never a hand curl).
GENTLE rate envelope + distillation cadence + **§8 multi-product engagements (one product per run,
restart at 0A)** + **§9 reporting cadence (per phase CHANGE only, terse — operator: "knp lama")** +
**§10 neutralising a budget breaks its arithmetic consumers** +
**§11 GENTLE flags belong to GENTLE MODE ONLY — a command written into a script carries NO rate
flags; `apply_gentle` is the single choke point** +
**§12 Windows process triage (MSYS mangles `taskkill /F` → `F:/`; prove a process is STALE via
`CreationDate`+`CommandLine` before killing it, then re-assert your own run survived)**:
`references/runtime-execution-policy-2026-10-10.md`.
Tools: `toolguard.py` (stall) · `autofix.py` (repair+re-run) · `bundle-sync.py` (drift).

## ➕ The "failure that pretends to be a result" family — INDEX (2026-10-10)


The gates can be **all green while the run tested nothing**, and a document can be **honest but
useless**. Before trusting any "0 findings", any gate failure that looks impossible, or any number the
pipeline printed, read `references/coverage-lies-and-report-quality.md`.

It is a **map, not a manual**: eight hard failures in one session were all one shape — *nothing
crashes, a number/status/document looks produced and is wrong*. Each has its own sibling reference
(phantom requirements · unreadable/AV-quarantined evidence · aggregator junk-ingestion · negative-report
substance · gates blocking a correct outcome · gates scoring their own echo); the index tells you which
one to open, gives the one-line discriminators, and records the meta-rule:

> after patching pipeline code, pick the verification bar that matches the change —
> **syntax → import → call → effect** — each bar passed while the next failed.

Cross-reference: when the gates are green but the vectors never reached a real surface (a redirector, a
catch-all, an edge rule), the fix is in `bug-bounty-exhaustive-testing` →
`references/cdn-redirector-signed-url-audit.md`.
`phase-watch.py` (silent phase-transition reporter for the operator).
---
name: audit-execution-discipline
author: RESEARCHER_NAME
description: "Rules enforcing execution over skill loading. PRIMARY: audit-pipeline-orchestrator.py (force-full-execution → variants → PoC exec → PoC variants → references-exec → 13-check disk gate at 0D with auto-rework loop → validate → review → report → post-0F coverage/checkpoint gate). Secondary: manual rules for edge cases. Tool mapping: sqlmap/dalfox/SSRFmap/etc, curl=LAST RESORT."
tags: [bug-bounty, security, execution, discipline, audit, tracker]
---

# Audit Execution Discipline Protocol

**User identified repeated failure modes. This protocol ENFORCES execution over loading.**

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

