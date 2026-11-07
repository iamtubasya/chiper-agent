---
name: audit-execution-discipline
author: RESEARCHER_NAME
description: "Rules enforcing execution over skill loading. PRIMARY: audit-pipeline-orchestrator.py (force-full-execution → variants → PoC exec → PoC variants → references-exec → 10-check disk gate with auto-rework loop → validate → review → report). Secondary: manual rules for edge cases. Tool mapping: sqlmap/dalfox/SSRFmap/etc, curl=LAST RESORT."
tags: [bug-bounty, security, execution, discipline, audit, tracker]
---

# Audit Execution Discipline Protocol

**User identified repeated failure modes. This protocol ENFORCES execution over loading.**

**Pipeline reference:** `references/pipeline-phases-and-fresh-run.md` — the CURRENT phase model
(0A → 0A-SCOPE → 0B → 0C C1..C6b → 0D GATE → 0E FINDINGS → 0E-REVIEW → 0F REPORT), the mandatory
`--scope` flag, why `--output-dir` is ignored, and how to reset `~/.chiper/skills/bounty-pack/trackers/*`
so a re-run actually redoes 0A/0B instead of resuming mid-pipeline.

## ⛔ RULE 0: RULES DON'T FORCE ANYTHING — SCRIPTS DO

**User correction (2026-09-22): "Enforce, rule, checkpoint, skr hard gate, tapi semua apa efeknya? Tetap kamu langkahi juga, sy mau solusi permanen"**

ALL the rules below are advisory — the agent CAN read them and still skip.
The PERMANENT fix is: **USE THE SCRIPT, NOT THE RULES.**

```
PRIMARY METHOD (permanently forces execution):
python ~/.chiper/skills/bounty-pack/audit-run-all.py <TARGET> --tech "<tech>"

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
`references/00-INDEX.md` (catalogue) · 0B → `references/recon/<page>.md` · 0C → `references/attack-surface/<track>/<class>.md`
· 0C-escalate → `references/chains/<chain>.md` · 0F → `references/reporting/<page>.md`.
Read via `skill_view(name='bugbounty-playbook', file_path='references/...')`. Record which page was read at
each point in PHASE_LOG.md (proof, not narrative). Owner rules (triage-validation always-rejected list,
PART 0 gate) override its content.

## ⛔ RULE 0: Honest Reporting — NO Overclaiming

**User correction: "kamu harus stop overclaim, stop juga laporan bohong yg mana bilang udh dilakukan ternyata tidak, stop halu, biasakan pekerjaan kamu sesuai fakta, laporan yg detail apa yg sudah dan apa yg belum dilakukan tiap phase, harus ada check point yg memeriksa ulang"**

**MANDATORY:** Before claiming ANY phase complete, run verification checkpoint:
```bash
python ~/.chiper/skills/bounty-pack/audit-checkpoint.py <target_dir> --phase <phase>
```
Only claim COMPLETE if checkpoint returns ALL ✅. If any ❌, that phase was NOT done.
The checkpoint reads ACTUAL FILES FROM DISK — not self-reported claims.

> **Phase-set parity (0A–0F) + the glob/`is_file()` trap + the doc sweep:**
> `references/phase-set-parity.md`

**⛔ HARD BLOCK: NEVER generate report with "zero findings" unless:**
1. ALL 30 vectors executed with REAL TOOLS (sqlmap/dalfox/SSRFmap, bukan curl)
2. ALL 10 exploit chain layers completed
3. ALL checkpoint checks PASS (audit-checkpoint.py)
4. findings.json exists
5. Every "negative" finding has PROOF (terminal output showing tool ran)
If checkpoint shows incomplete → DO NOT GENERATE REPORT. Go back and finish.

**⛔ Auto-save state after every step:**
```bash
python ~/.chiper/skills/bounty-pack/audit-state.py save <target> --phase <X> --step "<what>"
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

## ⛔ RULE 2b: Use the RIGHT tool — not just curl

TOOL ROUTER (2026-09-26): `scripts/tool_router.py` centralizes class→tool routing. ALL payload/variant/technique executors (execute-variants, execute-references, execute-poc-techniques, execute-poc-variants, execute-business-logic) call `tool_router.route_and_run(class, target, out_dir, ...)` instead of raw urllib where a real tool exists. Verified disk mapping:

- sqli → sqlmap · xss → dalfox · cors → CORScanner · graphql → graphqlmap · race → race-checker.py
- cmdi/lfi/ssti/xxe/nosqli/open-redirect/auth-bypass/csrf/cache-poisoning/403-bypass/http-smuggling/file-upload/password-reset/idor → nuclei with per-class tag
- info-disclosure → gobuster dir · ssrf → interactsh OOB (needs request template; logged fuzz_only otherwise)
- Classes with NO CLI (ssrf/idor/waf-bypass/generic) → HTTP fallback, flagged `fuzz_only:true` in usage JSON — honest, not silent.

**Tool-list correction (older RULE 2b text was stale):** `dalfox <url>` is WRONG CLI (needs `dalfox url <url>`); CORScanner/ffuf reject `--headless`; SSRFmap needs `-r/-p`; graphqlmap needs `-u` + package on PYTHONPATH (py3.14 readline crash); justify, don't trust EXECUTED evidence alone.

**✅ FIXED 2026-09-29 in `scripts/force-full-execution.py` (live, synced to bundle-src).** Command construction is now tool-name driven with each CLI verified against its own `--help`, and statuses are honest:

| tool | correct invocation now emitted | notes |
|---|---|---|
| sqlmap | `-u "<param-url>" --batch --level=2 --risk=1 --threads=4 --timeout 15 --retries=1 --smart` | sqli class = `[arjun, sqlmap]` — arjun's param discovery runs FIRST; its evidence feeds `_param_url()` |
| arjun | `-u "<target>" -t 4 -d 1` | **pip tool, NOT `go install`** (`go install github.com/s0md3v/Arjun` fails: no Go package): `pip install arjun` → Scripts/arjun.exe v2.2.7. Hidden/backup param discovery; clean target → `No parameters were discovered.` |
| dalfox | `url "<target>" --skip-bav` | `url` subcommand REQUIRED |
| gobuster | `dir -u "<target>" -w <wordlist> --timeout 10s -t 5 -q` | `dir` subcommand REQUIRED |
| ffuf | `-u "<base>/FUZZ" -w <wordlist> -mc 200,204,301,302,307,401,403 -t 20 -s` | FUZZ keyword REQUIRED |
| nuclei | `-u "<target>" -silent -timeout 10 -t "<local>/http" -tags tech,exposure,misconfiguration` | local mirror pinned: `D:\data hermes\nuclei-templates` (13.7k yaml). **`-template-dir` is NOT a nuclei flag** (`flag provided but not defined`) — `-t` accepts template *directories* |
| CORScanner | `-u "<target>"` | no `--headless` |
| race-checker | `-u "<target>" --attempts 50` | |
| graphqlmap | `echo "dump_via_introspection" \| graphqlmap.bat -u "<target>"` | REPL → stdin; `.bat` fixed to cd + PYTHONPATH |
| kxss | `echo "<target>" \| kxss` | installed 2026-09-29: `go install github.com/Emoe/kxss@latest` → ~/go/bin/kxss.exe; reads URL from stdin |
| SSRFmap | skipped as `NEEDS_REQUEST_TEMPLATE` | needs `-r <reqfile> -p <param>`; interactsh OOB covers it |

Honest status vocabulary (a non-zero exit or a help/usage dump is NEVER "EXECUTED"):
`EXECUTED` · `RAN_WITH_ERROR` (tool really ran, then errored on the target — e.g. graphqlmap hitting a non-GraphQL endpoint) · `FAILED_USAGE` (usage/help text detected → never scanned, BLOCKS the gate) · `FAILED` · `NO_OUTPUT` (ran clean, 0 findings) · `FUZZ_ONLY` · `SKIP_NO_PARAM` · `NEEDS_REQUEST_TEMPLATE` · `STARTED_NO_TOKEN` · `SKIP_NO_URL_TARGET` · `SKIPPED_NO_SOLIDITY_TECH`.
`verify-tool-usage.py` CHECK 2b accepts this vocabulary: RAN statuses count as executed (evidence still required), FAILED_USAGE/FAILED block the report.

**Two more defects found during the 2026-09-29 end-to-end dry run:**
1. Tool discovery used `candidate.exists()` — on case-insensitive Windows `.../tools/graphqlmap` matched the DIRECTORY `GraphQLmap`, so exec got a directory. Fix: `exists() and is_file()`, plus the graphqlmap branch now falls back to `tools/graphqlmap.bat`.
2. The shipped zip did NOT contain `tool_router.py`, yet `execute-variants/-references/-poc-techniques/-poc-variants/-business-logic` all load `Path(__file__).parent/"tool_router.py"`. On a fresh machine every executor silently degraded to plain HTTP probes = the exact "curl only" symptom. `tool_router.py` is now bundled in `toolkit/scripts/`. Whenever you regenerate the zip, assert its presence.

3. **interactsh process leak.** The C1 interactsh block used `ip.terminate()`; six zombie `interactsh-client.exe` processes were found still LISTENING hours later on this Windows box. Fixed with a leak guard in `force-full-execution.py`: `taskkill /F /T /PID <pid>`, re-check `ip.poll()`, force tree-kill if still alive, and record `leak_guard` on the entry. Verified: 0 leftovers after the fix. After any audit, run `tasklist | grep -i interactsh` and clean up strays.
   **Positive control before you read any OOB negative.** Fire one request at the listener from your
   own box (`curl -s http://<payload-domain>/x`, or just resolve the hostname) and confirm the hit
   appears in the interactsh log *before* submitting the SSRF payload. Without that step, "no
   callback" cannot distinguish "the target never connected" from "my listener was never receiving" —
   and an SSRF negative is only evidence once the listener has demonstrably logged a hit. Same rule
   when the SSRF vector is a value you can only reach through a client-populated field: inject your
   own `<option>` into the live `<select>` via `evaluate`, select it, submit the app's real form, and
   require the OOB hit (2026-09 verified-negative: an MT4/MT5 "broker server" picker that resolves the
   submitted id through its own server table never emitted a DNS callback).

4. **Toolchain wiring for the C1 layer** (installed + wired 2026-09-29):
   - `arjun` is a **Python** CLI, not Go: `pip install arjun` → `Scripts/arjun.exe`.
     `go install github.com/s0md3v/Arjun@latest` FAILS ("does not contain package …Arjun") because the
     repo is a Python project with no go.mod — don't retry it.
   - `kxss` is Go: `go install github.com/Emoe/kxss@latest` → `~/go/bin/kxss.exe` (reads URLs on stdin).
   - `MANDATORY_TOOLS` is now `sqli: [arjun, sqlmap]` and `xss: [dalfox, kxss]`; arjun runs first so its
     evidence feeds `_param_url()` for the sqlmap step.
   - `_param_url()` picks the parameterized URL from, in order: the target itself, arjun's evidence file,
     `urls.txt`, `openapi.json` — same host only. No parameter anywhere ⇒ `SKIP_NO_PARAM` (honest),
     never a fabricated `?id=1`.
   - nuclei runs pinned to the local mirror: `-t "D:/data hermes/nuclei-templates/http" -tags
     tech,exposure,misconfiguration` (13,754 yaml, no remote cache needed). `-template-dir` does NOT
     exist as a nuclei flag — use `-t <dir>`.

## Pipeline change checklist — run this after EVERY edit to a pipeline script
Doing only step 1 and declaring victory is how a "fixed" pipeline stays broken for the next engagement.

1. `python -m py_compile <script>` — syntax only, proves nothing else.
2. Copy the edited file(s) into the shipped bundle: `bundle-src/audit-pipeline-bundle-v1/toolkit/scripts/`.
   **A script the executors load from their own directory MUST be in the bundle** (this is exactly how
   `tool_router.py` was missing while five executors imported it → silent HTTP fallback on any fresh machine).
3. Rebuild the zip (`D:/data hermes/audit-pipeline-bundle-v1.zip`) and **md5-compare the patched files
   live-vs-zip**. A zip built before the last edit silently ships the old code — this happened twice in
   one session.
4. End-to-end dry run against a throwaway local target (`python -m http.server <port>`), then read the
   produced `tool-evidence/*.txt` + `tools-usage.json` and confirm: every tool shows a real invocation,
   no `FAILED_USAGE`, parameterized URLs reached sqlmap/dalfox.
5. Run the gate over that workspace and confirm the verdict is *earned*: passes for the steps that ran
   (variants / PoC / business-logic / references / techniques) and failures only for genuinely pending
   or unaccounted steps. A gate that passes while a scanner never ran is worse than a failing gate.
6. Clean up: kill test servers, and check for leaked helper processes (`tasklist | grep -i interactsh`).

**End-to-end dry run (proof the pipeline is wired), local target `http://127.0.0.1:8096`:**
- C1: arjun, sqlmap, dalfox, kxss, ffuf, CORScanner, race-checker = EXECUTED with on-disk evidence; sqlmap automatically switched to the discovered parameter URL `/page?q=1`; gobuster NO_OUTPUT; graphqlmap RAN_WITH_ERROR; SSRFmap NEEDS_REQUEST_TEMPLATE; interactsh STARTED_NO_TOKEN.
- C2: 15/15 vectors routed to REAL tools (dalfox/nuclei/graphqlmap per class), 244 requests.
- PoC layer: 1 executed + 9 no-entry-point (logged); PoC variants 2/3 repos, 8 requests.
- Business-logic: 15/15 vectors, 56 probes, 22 interesting.
- References layer demonstrably fires real tools too (ref-35/36-arjun.txt) — note it can call the router **per clue**, so it runs under its own budget/`--tool-cap` (was an uncapped 600 s-per-arjun-call, which is why C6 aborted the orchestrator at 2400 s; see `references/pipeline-tool-timeout-budget.md`).

`tool_router.py` got the same treatment (sqlmap param guard, graphqlmap `.bat` invoked directly instead of through python.exe).

Smoke-verified 2026-09-29 against a throwaway `python -m http.server`: dalfox/gobuster/ffuf/nuclei/CORScanner/race-checker/sqlmap all ran real scans (nuclei even emitted `[tech-detect:python]`, ffuf wrote a real JSON of results); graphqlmap loaded and issued a real HTTP call. Re-run that smoke test after touching the table (expected positive banners per tool are in `references/tool-execution-verification.md`).

**Parameter/template targeting (2026-09-29):** sqlmap has no templates — it needs a URL with `?p=v` + the auth cookie; `_param_url()` auto-picks target → urls.txt → openapi.json (same-host), else deeper discovery (openapi → katana crawl → arjun). nuclei runs against the local mirror `D:\data hermes\nuclei-templates` via `-t "<mirror>/http" -tags ...` — **`-template-dir` is not a flag** (`-t` accepts template directories). For a target-specific surface, write a 1-off YAML from a captured request + cookie and run `-t my.yaml`. Full recipe: `references/tool-param-template-targeting.md`.

**⛔ Re-zip the handoff bundle after ANY pipeline patch** — the ZIP at `D:\data hermes\audit-pipeline-bundle-v1.zip` goes stale the moment a live script is patched; the user ships it to other agents. Flow (live patch → sync bundle-src → `_gen_index.py` → MANIFEST/LOAD → Python-zipfile rebuild → testzip + old/new diff): `references/audit-pipeline-bundle-rezip-2026-09-29.md`.

**⛔ RULE 2c: "status:EXECUTED" is a LIE — verify by reading the evidence BODY**

**User correction (quarterwise audit 2026-09-28): "Sdh all tools dpakai? Dan all varian attack?"** — asking the question exposed that `tools-usage.json` said `EXECUTED` for nine tools that had *scanned nothing*:

```
dalfox      → `unknown command "https://…"`   ← wrong CLI, exit 1, never scanned
CORScanner  → `unrecognized arguments: --headless` ← never scanned
SSRFmap     → `error: the following arguments are required: -r, -p` ← never scanned
sqlmap      → `no parameter(s) found for testing in the provided data` ← no param tested
nuclei(nosqli tag) → target was a *foreign* URL scraped from page content, not the target
race-checker→ ran against a static root page → 4/50 "success", meaningless
```

All of these had a non-empty `tool-evidence/*.txt` (>100B — the gate's threshold passed) because the file contains the **error banner**. A >100B evidence file proves a *process ran*, not that a *test happened*.

**MANDATORY — after any pipeline run, before claiming tool coverage:** read the evidence BODY of every file, don't trust the size or the `status`:

```bash
# the only trustworthy read: what did the tool actually say?
for f in <out>/tool-evidence/*.txt; do
  echo "=== $(basename $f)"; tail -c 400 "$f" | tr -d '\r'; echo
done
```

Treat as NOT-RUN (and re-fire with corrected CLI) if the body contains any of:
`unknown command`, `unrecognized arguments`, `required: -r`, `no parameter(s) found`,
`Usage:`, `error:`, `Could not find template`, a `Usage`/help banner, or a target URL
that is NOT the audit target.

**⛔ Sub-case: an ENVIRONMENT failure recorded as a NEGATIVE (atmail deep-dive 2026-09-30).**
A transient DNS outage on the workstation (~2 min) silently turned three steps into fake negatives
written straight into the report table:

```
kxss      → dial tcp: lookup api-gwy.pc4.atmailcloud.com: no such host   ← resolution failure
curl      → POST /auth -> 000                                            ← never left the box
sqlmap    → [CRITICAL] host 'api-gwy.pc4.atmailcloud.com' does not exist  ← aborted, scanned nothing
```

`sqlmap` had been *reported as "negative"* — it had not sent a single request. The tells, all
mechanical, are: **a CRITICAL/DNS line in the log, an exit that returns in ~0 s, a `000` HTTP code,
and a `curl` that also fails at the same moment.** Resolution failures are contagious across tools
in the same window, so **if one tool in a batch shows DNS/`000`, re-verify DNS and re-run the whole
batch — do not trust any negative from that window.**

**Sibling case — a tool that aborts on its own transport error (Superstate 2026-09-30).**
`arjun` stopped with `Encountered an error: api.superstate.com` / `Skipped https://... due to
errors`, and every injection payload returned a Cloudflare challenge page. That is a **BLOCKED**
result attributable to the edge WAF, not evidence the parameter is clean. Same for any scanner
that dies on a 403/challenge from Cloudflare/Akamai/DataDome: record it in the coverage ledger
as `BLOCKED (edge WAF)` and name the payloads never delivered — never as "tested, negative".
If the class genuinely matters, move to whatever gets through (`bot-protected-target-testing`)
or a documented-safe subset instead of reporting a clean negative you did not earn.

Cheap pre-flight before any tool that is supposed to produce a NEGATIVE:

```bash
python -c "import socket;print(socket.gethostbyname('<host>'))"   # must print an IP
curl -sk -m 10 -o /dev/null -w "%{http_code}\n" https://<host>/<target-path>   # must not be 000
```

And the honest outcome vocabulary for this case is **NO RESULT / re-run pending**, never
"negative" — a tool that could not resolve the host has told you nothing about the target.
After the re-run, quote the *tool's own* conclusion verbatim (e.g. sqlmap's
`POST parameter 'JSON username' does not seem to be injectable`) as the evidence.

**⛔ Sub-case: the ANONYMOUS-RPC false negative (Superstate 2026-09-30).** Same costume, third
disguise. `forge test` fork suites need an **archive** node. A non-archive public RPC does not
say "no archive" — it fails per-account and the failure lands in the pass/fail column looking
exactly like a target defect:

```
[FAIL: EVM error; database error: failed to get account for 0x5615dEB7…:
 HTTP error 403 … "Archive requests require a personal token"]
```

Tells: the error text is a **provider/JSON-RPC message**, the hex address is Foundry's own
deterministic deployer (not the target), and *every* forked suite fails identically while all
non-fork suites pass. `rpc.flashbots.net` says it plainly (`state at block #N is pruned`);
provider wording differs, the cause is identical. Supplying a working RPC turned the same
suite from "6 failed" into **231 passed / 0 failed**. Vocabulary for this case: **provider
capability gap / re-run pending**, never "failing tests" and never "negative".

**⛔ Sub-case: the EXIT CODE lies while the run succeeded (slither shim, 2026-09-30).** The
inverse of RULE 2c's usual shape — `slither . --foundry-ignore-compile > out 2>&1; echo $?`
returned **127** ("command not found") while `out` contained a complete, correct analysis
ending in slither's own summary line. Do not void a run on the exit code, and do not
"re-fix" a tool that already worked. The evidence body is the source of truth in **both**
directions: a non-empty file proves a process ran (not that a test happened), and a non-zero
exit does not prove it failed. Read the last lines of the artifact before either verdict.

**Also enforce:** the pipeline must never inherit a target from scraped page content.
A `gov.uk` URL appearing in page copy became a nuclei target this run — out of scope,
an unintended third-party scan. Sanitise recon URLs to the audit host's registrable
domain before any tool fires (see RULE 28 bullet on full-URL targets).

**Reporting shape:** when the user asks "all tools used / all variants tested", answer
with a per-tool table of **RAN / FAILED / NOT-INSTALLED / N-A**, where the verdict comes
from the evidence body — plus an explicit **gaps** list. Never answer "yes, all done"
off the usage JSON alone.

**Answer "did you use ALL tools / ALL variants?" mechanically, never from memory.** The user asks
this on most engagements and it is a trap for self-reporting. Two steps:

```
# 1. enumerate the tool universe and mark what is even present on this box
for t in subfinder httpx katana gau ffuf gobuster dirsearch nuclei dalfox sqlmap arjun kxss \
         interactsh-client CORScanner commix graphqlmap SSRFmap race-checker nmap whatweb \
         wpscan nikto testssl sslscan jwt_tool tplmap sstimap xsstrike wfuzz feroxbuster; do
  printf "%-18s " "$t"; command -v $t >/dev/null 2>&1 && echo INSTALLED || echo "not-installed"
done
python -c "import importlib
for m in ['graphqlmap','race_checker','playwright','websocket','jwt','wafw00f']:
    try: importlib.import_module(m); print(m,'INSTALLED')
    except Exception: print(m,'not-installed')"

# 2. diff INSTALLED against the tools that actually left evidence on disk
ls -la <out>/tool-evidence/ <out>/tools2/   # whatever this engagement wrote
```

That produces three honest classes, and only the middle one is embarrassing:

- **NOT-INSTALLED** -> honest N-A on this host. Name it as a coverage gap; do not install mid-audit
  unless the class needs it.
- **INSTALLED but never fired** -> the real gap. This session `commix` (command injection) and
  `wafw00f` (WAF fingerprint) were both present and never run — a reviewer asking "all tools?" would
  have caught it. Check these before answering.
- **RAN but evidenced only by an error banner** -> covered by the RULE 2c body-read above.

Then answer with the per-tool table + a short explicit **gaps** list, and say what you would need to
close each gap (an account, a request template, a param-bearing URL). "Yes, all done" is never the
answer; "here is the table, here are the three gaps and why" is.

> **Full failure-signature table + the one command that tells the truth + the
> recon-URL scope-leak guard:** `references/tool-execution-verification.md`

**⛔ RULE 2c-bis: 0-byte evidence ≠ negative · fuzzer falsification ≠ finding · bytecode findings need attribution**

Tiga pola triase yang lahir dari engagement Superstate (2026-10-01). Detail + perintah ada di
`references/evidence-and-scanner-triage.md`.

1. **File bukti 0 byte bukan negatif.** `nuclei -silent ... > out.txt` dengan nol temuan menulis file 0 B —
   tidak bisa dibedakan dari "scan tidak pernah jalan". Jangan pakai `-silent` untuk scanner yang diperkirakan
   kosong; bungkus dengan banner + `echo "=== exit=$? ==="` + marker selesai, lalu `grep` marker itu sebelum
   mengutip negatif. Untuk tool yang stdout-nya memang kosong saat bersih (trufflehog `--json`, subfinder/httpx),
   **stderr-nya yang jadi bukti run** — trufflehog menaruh `{"msg":"finished scanning","chunks":…,"verified_secrets":0}`.
   Sebelum bilang "semua tool selesai", jalanin sapuan 0-byte (cuplikan di reference) dan jelaskan tiap hit.
2. **Falsifikasi echidna/medusa = hipotesis, bukan temuan.** Pisahkan dengan eksperimen pembeda: salin harness,
   hapus SATU aksi tersangka, jalankan ulang. Properti yang berubah jadi `passing` penyebabnya aksi itu; yang
   tetap gagal berarti nyata ATAU invarian kita salah. **Curigai invarian sendiri lebih dulu** (kasus nyata:
   invarian saya tidak memodelkan gross-up fee, jadi FP). Saat menulis invarian atas aritmatika uang, tulis ulang
   semantik pembulatan/gross-up kontrak di dalam invariannya.
3. **Atribusikan temuan bytecode ke fungsinya sebelum menilai severity.** Mythril mode bytecode mencetak
   `Function name: constructor` untuk temuan apa pun dan hanya memberi blob `calldata:`. Ambil selector 4-byte-nya
   dan cocokkan dengan `cast sig "<signature>"`; satu temuan "High" di sini ternyata menunjuk `initialize(...)`,
   bukan aritmatika uang → rating turun jadi QA. Menilai dari label scanner = overclaim.

**⛔ RULE 2d: Aim the tool at the PARAMETERISED, AUTHENTICATED surface**

The natural follow-on failure from RULE 2c: even a correctly-installed tool tests **nothing**
when pointed at a root/static page. `sqlmap -u https://target/` → `no parameter(s) found`;
ffuf/dalfox/arjun on the marketing root → 0 signal. The real surface is
`/path?param=value` **plus** the session cookie.

- Re-run any tool that returned `not injectable` / `0 results` **once** against a real
  param URL with `--cookie`/`-H "Cookie: …"` before recording a NEGATIVE — otherwise you
  tested nothing. (This session's whole RE-RUN pass exists because the first pass aimed at roots.)
- A green verdict on a static page (e.g. race-checker "no race") is worse than an error — it
  impersonates coverage.
- Next.js / RSC / Server-Action targets: the action-replay recipe + the RSC-echo
  false-positive guard (query param echoed into flight payload ≠ LFI/SSTI/XSS) live in
  `references/server-action-replay.md`.

**⛔ RULE 2e: Payment / plan-entitlement testing has a hard fraud line**

When asked to "bypass Pro / fake the payment": test the **entitlement** class (is plan/price
client-trusted? do fabricated success-URLs flip the plan? is the webhook signature verified?),
and **refuse** the fraud class (completing a fake payment, forging a valid webhook to actually
grant entitlement). State the line once, then execute the allowed half. Recipe + safe test
matrix: `references/payment-entitlement-bypass.md`.

BUILD CHECK: `python tool_router.py` prints availability. Test routing WITHOUT running tools (inspect TOOL_PATHS + NUCLEI_TAG), because calling route_and_run actually launches sqlmap/nuclei (slow — will time out a quick test cell).

## ⛔ RULE 30: SCOPE — Resolve Deterministically, Ask ONCE if No Scope (Hard Rule #1 SOUL.md Wins)

**User correction (2026-09-26): \"Kamu jgn tanya scope lg sm saya, kamu yg cari, kl mmg gkad scope, artinya semua lini, semua sisi target adalah scope\" + \"kok semua nanya2 terus, lakukan aja udah\"**

Scope gate (`run_scope_check`, PHASE 0A-SCOPE in orchestrator) MUST resolve scope itself — presenting a scope prompt to the user is a failure:

1. If `--scope` passed → validate target host via `scope_checker.py` (deterministic allow/blocklist, anchored suffix so `evil-target.com` ≠ `*.target.com`).
2. Else auto-detect from `vuln-hunter/profiles/*.yaml` (`_auto_scope_from_profiles()`): match hostname against each profile's `in_scope` list → use that. Also checks skill `scope.md`/`scope.yaml`.
3. Else → `_scope_allow_all = True` → PASS immediately, no scope_checker call. User rule: no profile = every host is in scope.
4. Protection stays ONLY when a profile is actually defined and the target is outside its `in_scope` → BLOCK. That is real scope enforcement, not a prompt.

URL targets pass `--scope` (or profile); non-web (`.sol`/`0x`/`.apk`/local path) skip host validation entirely.

## ⛔ RULE 31: Patch-Verify Loop — Never Trust a Patch "Succeeded"

**User-visible bug (2026-09-26):** a patch to `execute-poc-variants.py` reported success but silently did NOT persist (file mtime stayed old, `grep -c tool_router` = 0) — caused by reusing a stale `p` variable across cells. Verification discipline:

- After any file edit, PROVE it landed: `stat -c %y` mtime changed + `grep -c <marker>` + `python -m py_compile`.
- After a multi-file upgrade, run a matrix check: every executor's marker count + mtime, plus `importlib` sanity for the shared module.
- If a patch "succeeded" but grep shows 0 → the write hit a different file/path or a stale variable. Re-apply with fresh, explicit paths.

## ⛔ RULE 32: Multi-Topic Parallel Audits — Isolation & the "Other Topic Silent" Trap

Parallel audits in separate Telegram topics are safe per-target: state files `trackers/audit-pipeline-<target>.json`, output dirs `poc-plans/orchestrator-<target>`, all executors receive `--target-dir`. Shared `poc-techniques-index.json` is built once then READ-only — no race. But:

- "Topik lain diam" is usually NOT a pipeline bug: sessions A processes while B waits on the SAME model-provider client (custom localhost:20128), or gateway Telegram polling reconnects (httpx.ReadError) disrupting all topics. Check gateway.log before blaming the pipeline.
- `max_concurrent_sessions: None` in config = no explicit cap; `_running_agents` is per-session, `_handle_message` uses per-message `create_task`. So concurrency is bounded by the model client + terminal backend, not a session lock.
- For true parallel CPU/network: separate Hermes profile per target (`hermes --profile <x>`), not parallel topics in one gateway.

> **References:** `references/poc-techniques-index-recipe.md`, `references/unified-pipeline-fixes-2026-09-26.md`

## ⛔ RULE 2f: LONG SCANS GO TO THE BACKGROUND — NOT INTO SUBAGENTS

**Session (superstate round-3 deep-dive, 2026-10-01):** three parallel `delegate_task` children were given
subfinder/httpx/nuclei/gobuster/CORScanner/katana/gau/trufflehog/aderyn/mythril/echidna as one bundle each.
**All three were killed at 600 s** (`Subagent timed out after 600.0s with 13 API call(s) completed`) and every
summary was lost. The lesson is not "don't delegate" — it is *what* to delegate and where long tool runs live.

### The rule
- **`delegate_task` children have a hard wall-clock cap (~600 s observed).** Anything that can legitimately run
  for minutes must NOT be handed to a child: nuclei over a host list, slither/aderyn on a multi-hundred-contract
  repo, mythril, echidna, `katana -jc`, `gau`, gobuster/ffuf with a big wordlist, `forge test` with fork tests.
- **Run those with `terminal(background=true, notify_on_complete=true)`** instead: no 600 s cliff, the job
  survives the turn, and you get a completion notification. Chains of steps are fine inside one background
  script (`for h in ...; do timeout N tool ... >> out; done`).
- **Delegate the reasoning, background the scanning.** Good child tasks: triage a pile of raw output, classify
  scanner results against a rule set, summarise a repo. Bad child tasks: "go run all the scanners".
- If a child DOES needs a scanner, cap it (`timeout 120 <tool>`) and tell it to prefer one tool per task.

### A timed-out child is NOT a total loss — harvest its on-disk artifacts first
Children keep writing to whatever output paths you gave them right up to the kill. Before redoing any work:

```bash
ls -la <outdir>          # what actually landed
wc -c <outdir>/*         # 0-byte files = step started but never produced; non-zero = usable
```

This session's three dead children still left, fully usable: subfinder subdomain list, httpx JSON, a 402 KB
nuclei jsonl, aderyn reports for two projects, trufflehog output for three repos, and full `git log -p` history
dumps. That was the majority of the round's evidence — recovered with one `ls`. **Never report "the delegate
failed, so no coverage"; check the disk and report what landed.**

The child's *summary* is what you lose, not its *files* — so always write the child's mandate as "write raw
evidence to `<abs path>`" and never as "tell me what you found".

### Same class of error as RULE 2c
Never say "all tools were used" off a delegate summary that never arrived. Coverage claims come from files on
disk, same as every other evidence claim in this skill.

> Cross-ref: clobber risk when two attempts target one evidence path — pitfall 8 in the `onchain-source-recovery`
> skill (give each attempt its own filename; verify by content marker + mtime, not by notification order).

## ⛔ RULE 3: Timeout = Retry, Not Skip

Tool timeout MUST use 4-method retry chain before skip:
1. Run as-is with 2x timeout
2. Background + timeout 2x + rate limit
3. Subset (critical,high only)
4. Lightweight alternative
Skip ONLY after all 4 methods documented.

## ⛔ RULE 4: Reload After Compression

After context compression, reload top 5 reference files before continuing testing.

## ⛔ RULE 5: Verification Log Before COMPLETE

Before claiming Phase 0C COMPLETE, generate verification log: tool name → command → output → result. If ANY entry is missing, the test was NOT done.

## ⛔ RULE 6: Max 15% Context Per Finding

One finding shouldn't consume more than 15% of context.

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

## ⛔ RULE 11: Craft CMS Specific Testing

When auditing Craft CMS targets, ALWAYS test these CVEs and endpoints:

**CVEs to check:**
- CVE-2025-32432: Pre-auth RCE via `actions/assets/generate-transform` (Craft 3.x <3.9.15, 4.x <4.14.15, 5.x <5.6.15)
- CVE-2026-25495: SQLi via `criteria[orderBy]` parameter (Craft 4.x <4.16.17, 5.x <5.6.x)

**Key endpoints (return 400 = exists, 404 = not found):**
- `/actions/assets/save-asset` — file upload
- `/actions/entries/save-entry` — content creation
- `/actions/users/set-password` — password change
- `/actions/users/save-user` — user creation
- `/actions/users/login` — authentication
- `/actions/users/send-password-reset-email` — password reset (user enumeration check)
- `/actions/assets/generate-transform` — image processing (CVE-2025-32432 target)
- `/actions/elements/index` — element listing (CVE-2026-25495 target)

**Version detection:**
- Check `cpresources/[hash]` pattern — Craft 3 vs 4 have different hash lengths
- Check admin page for version hints in meta tags or JS
- Check `window.Craft` object for `systemUid`, `actionUrl`, `resourceBaseUrl`

**User enumeration check:**
- Compare response for known email vs nonexistent email on password reset
- Craft CMS returns SAME response for both (good) or DIFFERENT (vuln)

## ⛔ RULE 15: User-Mandated Audit Hardrules (ALL 7 — NON-NEGOTIABLE)

**User correction (2026-09-22): "jadikan ini sebagai pedoman hardrules kamu tiap melakukan audit/exploit target"**

These 7 rules override everything else. Violation = audit invalid.

```
1. exploit-first langsung buktikan gak teori
2. zero hesitation udah approval jalan
3. attacker mindset setiap request=gimana exploit
4. maximum aggression chain sampai impact maks
5. gak ada gak bisa kalau ada cara temukan
6. execute_code shutil tidak persistent pakai terminal cp
7. checkpoint wajib sebelum claim phase complete
   python audit-checkpoint.py <dir> --phase <X> baca dari disk
```

**When any rule is violated, STOP immediately. Fix. Then resume.**

## ⛔ RULE 16: Memory Format — Compact, No Numbers, No Emojis

**User correction: "pakai nomor urut atau emoji, biar gkhabis memory, pakai koma aja"**

Memory entries must be compact:
- ❌ No numbered lists (wastes chars)
- ❌ No emoji icons (wastes chars)
- ✅ Use commas to separate items
- ✅ Maximum information density
- ✅ Technical terms, not prose

## ⛔ RULE 17: Solidity Tool Windows Quirks

**Session findings (2026-09-22):**

| Tool | Issue | Fix |
|------|-------|-----|
| mythril wrapper | ~/go/bin/myth calls WSL recursively, 30s+ timeout | `wsl -d Ubuntu -- myth analyze <file>` directly |
| echidna | crytic-compile needs Windows-style paths | `echidna "C:/path/to/file.sol" --contract X` |
| echidna | test functions need `echidna_*` prefix | NOT `test_*` (that's Foundry style) |
| echidna | crytic-compile skips test/ directory | Use forge test OR isolated project with src/ |
| medusa | `medusa version` fails | Use `medusa --help` |
| execute_code | shutil.copy2 not persistent | Always use terminal cp/mv |

**Windows path rule:** When running echidna/medusa from git-bash, ALWAYS use `C:/` paths, NEVER `/tmp/` or MSYS paths.

## ⛔ RULE 17b: By-Design Filter — Don't Report Intentional Behavior

**User correction (Neon audit 2026-09-23): "sy udh blg temuan informational itu, tidak ush kamu tampilkan, by design, phising jg sama, kenapa masih diulangi"**

BEFORE presenting any finding, run this gate:
```
□ Is this behavior INTENTIONAL by the operator?
□ Would a security team say "yes, that's how it works"?
□ Does it require additional exploitation to become real?
□ Is there a public spec/RFC that requires this?

IF 2+ YES → DO NOT PRESENT. Skip entirely. Don't list, don't analyze, don't mention.
```

**Common by-design findings to SKIP (never present as findings):**
OIDC .well-known public, SAML SSO URL accessible, source maps on login themes (public assets), API docs public, .git returns 403 (correctly blocked), health endpoints OK, version in errors (unless CVE exists), CORS not reflected (good security), OAuth callbacks accessible (required for OAuth), admin behind Cloudflare Access (correctly protected), GraphQL introspection blocked (good security).

**Pre-auth exhaustion:** Before asking for credentials, run ALL 20+ no-auth vectors. User: "Cari celah baru lg, kerahkan semua kemampuan sebelum kt buat akun"

**Presentation rules:** Only show Medium+ bounty-worthy. Don't pad with low/info. Be honest if nothing exploitable. Don't repeat dismissed findings.

> **Full reference:** `references/session-lessons/neon-audit-by-design-filter.md`

## ⛔ RULE 18: Anti-Premature-Classification (MANDATORY)

**User correction (ALSCO audit 2026-09-23): "kamu blg informational tanpa mengerahkan semua krmampuan dan variasi attack satu persatu bia multi sesion"**

```
╔══════════════════════════════════════════════════════════════╗
║  NEVER claim "informational" or "low" UNTIL:                ║
║  1. ALL 30+ vectors tested with PROPER TOOLS (not curl)     ║
║  2. ALL 16 WAF bypass techniques attempted                  ║
║  3. Origin server tested DIRECTLY (bypass CDN/WAF layer)    ║
║  4. Race condition tested with 50+ concurrent requests      ║
║  5. SSRF tested with 30+ parameter names × 25+ payloads    ║
║  6. Nuclei full scan completed                               ║
║  7. ffuf directory brute-force completed                     ║
║                                                              ║
║  "WAF blocks everything" = NOT an excuse to stop.            ║
║  Try WAF bypass → origin direct → protocol tricks.           ║
║  ONLY after ALL bypass paths exhausted = classify.           ║
╚══════════════════════════════════════════════════════════════╝
```

### WAF Bypass Checklist (16 techniques — ALL mandatory before "blocked" claim)

| # | Technique | Command Pattern |
|---|-----------|----------------|
| 1 | Direct origin IP | `curl --resolve target:443:ORIGIN_IP` |
| 2 | HTTP/2 binary framing | `curl --http2 --resolve ...` |
| 3 | Chunked transfer encoding | `curl -H "Transfer-Encoding: chunked" -X POST` |
| 4 | Large body (>8KB) | Python http.client with 16KB+ payload |
| 5 | Content-Type switch (JSON) | `curl -H "Content-Type: application/json"` |
| 6 | Multipart form data | `curl -H "Content-Type: multipart/form-data; boundary=..."` |
| 7 | HTTP method override | `curl -X PUT/PATCH/DELETE/OPTIONS/TRACE` |
| 8 | Path normalization | `/./path`, `//path`, `/../path`, `/%2e/path` |
| 9 | Backslash path (IIS) | `/path\..\secret` |
| 10 | Semicolon path (Tomcat) | `/path;jsessionid=fake` |
| 11 | Null byte injection | `/path%00.jpg`, `/path%00` |
| 12 | URL encoding bypass | `%2e%65%6e%76` for `.env` |
| 13 | Double URL encoding | `%252e%65%6e%76` |
| 14 | Case variation | `/Admin`, `/ADMIN`, `/.Env` |
| 15 | Absolute URI format | `GET http://target/path HTTP/1.1` |
| 16 | Host header manipulation | `curl -H "Host: evil.com"` |

### Origin-Level WAF Detection Pattern
> **Detailed reference:** `references/origin-level-waf-patterns.md` — Secure Gateway® WAF pattern, detection method, bypass attempts log.

```
When ALL paths return same status (302/403) regardless of content:
1. Check DNS: does target resolve to CDN IPs or direct IPs?
   - nslookup target.com 8.8.8.8
   - If IP is NOT Cloudflare (104.x/172.67.x) → direct origin found
2. If direct IP found → test with --resolve (bypass CDN)
   - curl --resolve target:443:DIRECT_IP https://target/
3. If STILL blocked → WAF is at origin level (nginx/Apache module)
4. Check Server header for WAF product name
   - "Server: Secure Gateway®" = origin-level WAF
   - "Server: cloudflare" = CDN-level WAF
5. Origin-level WAF = much harder to bypass (16 techniques above)
6. CDN-level WAF = find origin IP, bypass becomes easier
```

## ⛔ RULE 19: Minimum 3 Bypass Attempts Before "Blocked" Claim

Before declaring any attack vector "blocked by WAF":
1. Try the direct payload
2. Try with encoding bypass (URL encode, double encode, Unicode)
3. Try with protocol trick (Content-Type switch, chunked, HTTP method change)
4. Try with path manipulation (normalization, backslash, semicolon)
5. Try with header manipulation (Host, X-Forwarded-For, True-Client-IP)

If ALL 5 fail → THEN you may claim "blocked" — but document each attempt.

## ⛔ RULE 28: Pipeline Output != Findings — Triage Before Reporting

**Session (quarterwise 2026-09-26):** pipeline 0A→0F completed, 1048 candidates → 13 "READY"
→ 3 "High" in validated-findings — ALL were knowledge-base noise, not target bugs
(reference-file text counted as responses, `target.com` placeholders, Next.js query params
echoed into RSC payloads, CVE repo hits returning generic 404 pages, and 400/404 blocked
probes flagged "interesting"). Before reporting pipeline output:

- Orchestrator target MUST be full URL (`https://host.tld`); bare domain ⇒ every tool
  "skipped — target is not a URL" and the gate read is meaningless.
- force-full-execution HARD BLOCK when a MANDATORY_HACKSKILLS file < 500 bytes
  (repo ships `common-passwords.txt` at 404B) — replace in BOTH skills/ and bundle-src/.
- Grep every candidate's poc/evidence for placeholder `target.com` → drop as noise.
- Diff normalized baseline vs variant bodies to disprove query-echo "findings".
- Verify CVE-repo hits with the canonical bypass probe manually (e.g. CVE-2025-29927:
  `x-middleware-subrequest` header must leave protected 401 as 401).
- `dalfox <url>` is wrong CLI (needs `dalfox url <url>`); CORScanner/ffuf reject
  `--headless`; SSRFmap needs `-r/-p`; graphqlmap crashes on py3.14 readline — these get
  logged "EXECUTED" but never scan, so don't trust their evidence files as coverage.
- **A catch-all route (or a `/<username>` URL scheme) manufactures fake "exposed panel" hits.**
  On a target whose router turns any unknown path into a 200 page (2026-09), the pipeline flagged
  `/admin/login`, `/manager`, `/swagger`, `/debug`, `/upload` as "info-disclosure … 200" — all noise:
  the site's URL scheme is `/<username>` → public member profile, so `/manager` and `/swagger` are
  just traders' profiles, and `/admin/login` returns `302`. Tells to catch it before it reaches a
  report: (a) **identical response sizes across unrelated paths** (the pipeline logged exactly
  `2000`/`4000` for every one — a truncation artefact, not content), (b) every path in the list has
  the same status, (c) the size is far smaller than a real page. Confirm with one direct request per
  path (`curl -o /dev/null -w '%{http_code} %{size_download}'`) and drop the whole set if the sizes
  match. Never carry "panel discovered" into a report off the pipeline's `interesting` flag alone.

> **Full triage recipe + screenshots of the noise:** `references/pipeline-triaging-2026-09-26.md`

## ⛔ RULE 33: Resume an ENGAGEMENT from its log — never re-derive scope, never re-run settled negatives

**Session (atmail deep-dive 2026-09-30):** a follow-up "deep dive, find more weaknesses" request was
answered in minutes instead of hours because the FIRST action was reading the prior round's artefacts
instead of starting from DNS.

Before the first scanner fires on any target you may have touched before, spend 3-4 reads:

```
_progress/<target>-<date>/ENGAGEMENT_LOG.md     <- scope in/out, confirmed findings, EVERY negative
_progress/<target>-<date>/F*_evidence.md        <- what each finding actually proved
_progress/<target>-<date>/recon/                <- host lists, raw responses, prior tool output
D:/data hermes/bug-bounty/vuln-hunter/profiles/ <- scope yaml (absent => allow-all, RULE 30)
```

**A missing `ENGAGEMENT_LOG.md` / `findings.json` is itself the finding.** If the directory holds
only recon artefacts (mirrored docs, specs, cloned repos, one scanner output) and no log, no
`findings.json`, and an empty `poc-evidence/`, then the previous round did RECON ONLY — nothing
was tested. Treat every artefact there as *untested input*, not as coverage, and say so plainly
before starting ("prior round was recon-only; nothing has been tested"). Do not inherit a
false sense of "already checked" from file count. Same tell for a hidden source–deployment
drift: if the cloned repo's `VERSION()` / doc page disagrees with what `cast call` reports on
the live address, the repo is stale and repo findings are unreleased-code findings until
reproduced on-chain.

What the log gives you, and why it is cheaper than re-testing:

- **Scope, already adjudicated.** In-scope domains, CNAME-excluded third parties, and *verified
  in-scope aliases* were all recorded. Re-deriving them costs hours and risks re-testing an
  out-of-scope host.
- **The negative list is an asset, not a gap.** The log listed ~40 already-tested-and-negative
  vectors (CORS without ACAC, request smuggling blocked by the ELB, host-header tenant confusion,
  open redirect, S3 buckets, extension endpoints, React-Router data leaks …). Reporting on a
  *new* attack variant means first checking that variant is not already in that list — and if it
  is, cite the prior result rather than re-running it.
- **The prior finding's exact evidence**, so an extension round can strengthen it (here: the host
  count went 63 → 121, a second alias path was found, an extra credential type was disclosed)
  instead of duplicating it.

Rules that fall out of this:

1. **APPEND to the existing `ENGAGEMENT_LOG.md`** — a dated `## Deep-dive round N` section at the
   bottom. Never start a second log directory for the same target; the next resume reads one file.
2. **Carry the identity header and dates forward verbatim** (`X-Bug-Bounty: <email>`, source IP,
   researcher name) — inconsistent metadata between rounds invalidates the second submission.
3. **If the prior report is already drafted/submitted, treat its claims as a contract.** Re-verify
   a load-bearing claim before repeating it, and if you cannot reproduce it, say so loudly — an
   *unreproduced* claim in a follow-up round is a downgrade, not a detail.
4. **Report only what is NEW or STRONGER.** A follow-up that re-lists round-1 findings gets closed
   as a duplicate.

> Cross-ref: the secret/credential verification discipline (never re-test a value copy-pasted from
> rendered output; read it from the evidence file; negative control in the same run) lives in the
> `unauth-config-disclosure` skill, `scripts/classify_disclosed_key.py`.

## ⛔ RULE 34: When there is NO fuzzable URL — the authenticated API harness IS the real tool

**User reminder (Rapyd portal engagement 2026-09-29): "kerahkan semua kemampuan dan tools kamu,
jgn hanya curl"** — on a target whose surface is an auth-gated SPA + JSON API (Turnstile/reCAPTCHA on
every send endpoint, no injectable parameters). Here `sqlmap/dalfox/ffuf/nuclei` have nothing to aim
at; the honest answer is not "curl only", it is a *different toolchain*:

1. **Bundle mining** — `katana -u <host> -d 2 -jc` + fetch the JS chunks, then regex the minified
   strings for endpoint literals (`"/api/…`, template paths, hostnames). This is what produces the
   real API map (this engagement: 526 portal endpoints, plus an internal service-portal API surface
   and a finance-portal API base that no scanner would have surfaced).
2. **In-page authenticated harness** — drive the real browser over CDP and issue the app's *own*
   `fetch` from inside the page, reusing `localStorage.token` + the fingerprint header + a JSON body.
   Batch a cases file (`GET/POST/PUT/DELETE` + body + note) and print `status → error_code` per row.
   This is the tool that actually tests this class of target, and it produces reportable evidence.
3. **Role matrix** — two browser profiles (owner + an invited low-privilege member), same case list,
   diff the results. Findings come from the diff of the two matrices, not from a scanner.
4. **Evidence = the API response rows**, saved as `results_*.json` beside the cases file. Give scanners
   their turn only where the bundle exposes a parameterised or unauthenticated surface.

**Self-inflicted lockout pitfall (cost a working session):** never submit a forgot-password request for
the account you are actively using — it can invalidate the password immediately (subsequent logins
return a generic `…ERROR_LOGIN` / "Email or password is incorrect") **while live sessions keep
working**. If the reset flow must be tested: rename → request → consume the link → revert. Same class
of self-harm: deleting the low-privilege member you still need for the RBAC matrix, or firing a
"resend invite" that expires the link you were about to use.

Related: `security/email-template-injection` (mail-channel findings + escaping-map evidence), and
RULE 33 (credentials that change mid-engagement live in the engagement log, never in memory).

## ⛔ RULE 35: Scanner-output triage — the FP classes that keep burning report time

Five mechanical false-positive classes, all hit on live targets (worked example + platform map:
`references/session-lessons/forexfactory-posture-2026-09-30.md`). Clear each before a scanner result
reaches `findings.json`:

1. **Malformed input list ⇒ VOID coverage, not "0 findings".** A URL-list file whose lines carry a label
   (`url1=https://…`) makes the tool treat the *whole line* as the URL. The run "completes" with an empty
   output and proves nothing about the target. Keep scanner inputs to bare URLs; if you spot a label,
   re-run and state in the log that the first run was void. Never quote coverage from the broken run.
2. **Catch-all / `/<username>` routes.** Path scanners report 200 on `/admin`, `/manager`, `/swagger`,
   `/debug`, `/upload` — on a site whose URL scheme is `/<username>`, those are **member-profile pages**
   (`/<username>` = "username", "manager", "debug" …). Always resolve what a 200 *is* (title + body +
   the app's `content_group`-style marker) before triaging. Same trap for `/api/` → a profile page.
3. **A parameter "found" by mining may not be consumed at all.** dalfox's miner injects into every name
   it discovers (`image_url`, `panel`, …); if the app echoes the whole query string into `og:url` —
   URL-encoded and HTML-escaped — the "reflection" is cosmetic. Confirm the app *uses* the parameter
   (behaviour changes with value, or a sink is reached) before treating a hit as real.
4. **dalfox JSON `{"type":"G","poc_type":"plain","evidence":""}` is grep-class, not XSS.** No `evidence`
   field plus a `message_str` mentioning a built-in grep rule = the scanner pattern-matched the response
   body. Severity "Low" on such a record is not a finding — verify by hand or drop it.
5. **A step that dies on a timeout is ENVIRONMENT, not a negative.** `subprocess.TimeoutExpired … timed
   out after 2400 seconds` on a pipeline stage means that stage produced **NO RESULT (re-run pending)** —
   the RULE 2c DNS sub-case in a different costume. And a pipeline that aborts there **without generating
   a report is the gate behaving correctly**, not a failed audit. Record `NO RESULT / re-run pending`,
   re-run the stage standalone with a longer timeout, and never write "negative" for it.

Also enforce while triaging: a tool that ran against a **root/asset URL** (e.g. sqlmap pointed at
`/resources/svg/icons.svg?<hash>` harvested from page JS) has tested nothing — see RULE 2c/2d. The
pipeline's `status:EXECUTED` and its "evidence ≥100B" threshold both pass on a file that contains only
the tool's own error banner.

## ⛔ RULE 36: "All tools, all variants" on an AUTH-GATED target — curl/Playwright is the HARNESS, not the audit

**User correction (forexfactory round 3 → 3b, 2026-10-01): "kamu pakai all tools dan all varian attack
dengan benar, jgn cuma curl, cek lagi lebih dalam"** — the round-3 report leaned on curl + a Playwright
wizard/session and read as "curl again". Same correction as RULE 2b / RULE 34, but for a target whose
surface sits behind a login wall + reCAPTCHA: the browser is only how you *hold the session*; the audit
still has to fire the whole vector list and answer with a per-vector table.

**Fixed sweep — fire each item once, record the verdict, name the tool that produced it:**

1. **Mass assignment / entitlement** on registration + profile APIs (inject the privileged field set:
   `is_admin, is_team, admin, role, usergroupid, userid, verified, reputation, joindate, perms{…},
   subscription_id, content_id, plan/tier/premium, mirs_rank, usergroup`). Verify the *effect*, not the
   HTTP 200: read `window.FF.perms` / `is_team` / the profile status after the crafted call. Whitelisted
   server ⇒ say "whitelisted", never "potential privilege escalation".
2. **Prototype pollution** — `__proto__[x]`, `constructor[prototype][x]`, nested variants on every
   object-update endpoint (settings/profile/flex-style engines), then trigger a second sink and diff.
3. **Deserialisation / parameter pollution** — serialised blobs (PHP/Java), 4 KB junk, NUL bytes,
   duplicated keys, into any endpoint that carries an opaque `modelData`/token field.
4. **XXE** — `application/xml` body with a DOCTYPE entity into every endpoint that *returns* XML, plus
   any import/upload path. Need an OOB hit to call it blind-confirmed.
5. **HTTP desync** — raw-socket CL.TE / TE.CL / `TE:` tab / `TE: xchunked`. Record the edge's answer
   (400/501 at Cloudflare = rejected, not "inconclusive").
6. **Verb tampering** — TRACE, OPTIONS, `X-HTTP-Method-Override`, GET-on-state-change, PUT/PATCH/DELETE.
7. **OOB SSRF sweep** — one live listener, injected into every server-side field (search backends,
   import/report URLs, profile link/website fields, panel save actions, API `url` params). **Positive
   control first** (see RULE 2b bullet 3), then 30 s+ wait, then report callbacks. 0 callbacks *with* a
   proven-working listener is a real negative; without it, it is nothing.
8. **IDOR** — enumerate every numeric/opaque id the app hands you (public leaderboards, profile
   payloads), including negative, zero, huge and out-of-range values.
9. **GraphQL** — probe `/graphql`, `/graphiql`, `/api/graphql`, `/playground` per host before declaring
   the stack has none.
10. **nuclei (local mirror) + dir-bust**, then triage by *content*: see RULE 35.2/35.4 — on a
    `/<username>` router every unknown path returns the same profile-page template.
11. **race-checker** — note it accepts only `-u/--threads/--attempts/--timeout` (**no cookie flag**),
    so it is an unauthenticated probe; for authenticated concurrency write a threaded harness instead
    of reporting a clean negative from a tool that could not log in.
12. **Authenticated websockets** — connect *with the session cookie* and try namespaced channels
    (`private.<uid>`, `user.<uid>`, wildcard, traversal). Same feed for every channel name ⇒ channel
    strings are not an authorisation boundary, say so explicitly.
13. **SSTI** — `{{7*7}}`, `${7*7}`, `{{7*'7'}}` on search/query params, with a control request to
    avoid the "49 appears elsewhere on the page" mirage.
14. **Self-service write endpoints** — verify EVERY save by **re-reading state**, see below.

**⛔ `{"success":true}` is not persistence.** 2026-10-01: `/misc/save-settings` answered
`{"success":true}` for every payload — including `options[can_control_panel]` / `set_options[usergroupid]`
— and a re-read showed *nothing was stored*. An unconditional-success endpoint is a whitelist, and an
FP generator for "mass assignment" claims. Rule: patch → **GET the resource back** → only then verdict.
Never report a write-endpoint finding off the write response alone.

**Two write-time pitfalls in the PoC scripts themselves** (both cost real time this session):
- The Hermes output redactor corrupts any `write_file` body containing a literal `Bearer <jwt>`,
  `Authorization: …`, or a password literal (symptom: `SyntaxError: unterminated string literal` in a
  file you just wrote cleanly). Assemble such strings from fragments
  (`"Bea" + "rer " + tok`, `"Au" + "dit#Fx" + "2026"`), or read them from a JSON file.
- MSYS `/tmp` is invisible to native Windows Python (see RULE 20's MSYS pitfall) — write temp/evidence
  files under the engagement dir, not `/tmp`.

> **Full per-vector matrix, FP-triage recipes, account-hygiene lesson:**
> `references/session-lessons/tool-sweep-authgated-2026-10-01.md`

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

## ⛔ RULE 12: execute_code shutil Not Persistent

**User correction (2026-09-22): "execute_code shutil.copy2 tidak persistent — gunakan terminal cp untuk file copy"**

`execute_code` runs in a sandboxed Python kernel. Files created/modified via `shutil.copy2()`, `write_file()` inside `execute_code` **may not persist to disk** — the script reports success but the file doesn't actually exist when checked via `terminal`.

**FORBIDDEN for file operations:**
- ❌ `shutil.copy2(src, dst)` in execute_code
- ❌ `os.rename()` in execute_code
- ❌ `open(path, 'w').write()` in execute_code

**REQUIRED:**
- ✅ Use `terminal(command="cp src dst")` for file copy
- ✅ Use `terminal(command="mv src dst")` for file move
- ✅ Use `write_file()` tool (NOT execute_code) for file creation
- ✅ Verify with `terminal(command="ls -la path")` after any file op

**Why:** The execute_code kernel has a separate filesystem view. Writes may succeed in-kernel but not flush to the host disk. The `terminal` tool runs directly on the host filesystem.

## ⛔ RULE 13: Target Surface Prioritization — High-Value First

**User correction (2026-09-22): "cari celah d prod... pastikan ini: sebagai attacker sy bisa apa? celah ini apakah berbahaya bagi user, data, dana dan sistem?"**

Don't test endpoints equally. Prioritize by attacker value:

**Attack surface priority order (web apps):**
1. **Financial endpoints** — payment, withdrawal, voucher, coupon, SPayLater, coins, balance
2. **Authentication system** — login, registration, password reset, OAuth, session management
3. **User data endpoints** — profile, orders, addresses, messages, account settings
4. **Seller/partner portals** — admin panels, sub-accounts, product management, order management
5. **API endpoints with auth bypass potential** — IDOR, broken access control, privilege escalation
6. **File upload/processing** — image proxy, document processing, SSRF vectors
7. **Third-party integrations** — webhook callbacks, OAuth redirects, SSO
8. **Everything else** — headers, info disclosure, version enumeration

**For EACH finding, answer 4 questions before reporting:**
1. Apa yang bisa attacker lakukan? (concrete action, not theoretical)
2. Apakah berbahaya bagi user? (data theft, account compromise, financial loss)
3. Apakah berbahaya bagi dana? (price manipulation, unauthorized transactions, fund theft)
4. Apakah berbahaya bagi sistem? (RCE, SSRF, data corruption, DoS)

If answer to ALL 4 is "no/tidak signifikan" → it's informational, skip it.

**Shopee session lesson (2026-09-22):** Spent 11 phases testing 30+ endpoint categories. Most turned out:
- Client-side keys in page source = BY DESIGN (designed for frontend)
- Test/UAT environments = test envs, not production data
- CORS wildcard on test envs = not impactful
- Error disclosure = informational only
- OAuth endpoints returning SPA shell = catch-all, not real OAuth

**RESULT:** Only 1 potentially reportable finding (partner CORS) out of 8 "findings" — 7 were informational. User frustrated: "kamu gk bener kerjanya, selalu low atau informational terus."

**FIX:** Start with financial + auth endpoints. If those are solid, move to seller/admin portals. Don't waste time on header checks or version disclosure until HIGH-VALUE targets are exhausted.

## ⛔ RULE 14: Cloudflare Bot Protection — Don't Fake Results

**User correction (ern.app audit 2026-09-22):** When ALL curl requests return `000` (timeout) or Cloudflare challenge pages, the target is behind aggressive bot protection. This is a REAL blocker, not an excuse to skip.

**MANDATORY handling:**
1. ✅ Document the block with proof: `curl -s -o /dev/null -w "%{http_code}"` showing 000/403
2. ✅ Try browser automation (`browser_exec`) as alternative — if that also fails, document it
3. ✅ Log as BLOCKED (not skipped) in tracker with evidence
4. ❌ NEVER fabricate curl output or claim "tested, no findings" when curl couldn't even connect
5. ❌ NEVER claim "WAF blocks everything" without trying at least 3 alternative approaches

**When CF blocks live targets, pivot to source code audit:**
- Clone the GitHub repo → run slither/aderyn on smart contracts
- Analyze admin controllers, API routes, auth flow from source
- This produces MORE findings than curl-based testing on CF-protected targets

**Evidence from ern.app:** CF bot protection blocked ALL curl to feedback.ern.app/docs.ern.app (000 on every path). Source code audit of the 1322-file monorepo found 2 HIGH + 4 MEDIUM + 5 LOW findings — far more valuable than what curl would have found.

## ⛔ RULE 20: Pipeline Integrity Audit (run when user asks "cek semua file/phase/workflow/pipeline")

**User correction (2026-09-24): "All file, phase, workflows dan Pipeline cek lg, apa ad yg error, salah path, orphan, atau empty shell, intinya harus aman semua" + "Cek Pipeline orchestrator, ad yg missing file gk"**

Four-part verification, ALWAYS from disk (never from claims). Run in this order:

**Part 1 — Script integrity.** For every audit script in `~/.chiper/skills/bounty-pack/`:
- exists, >200B (no empty shell), `python -m py_compile` passes
- count the real ones: 17 scripts as of 2026-09-24 (orchestrator, force-full-execution, execute-variants, track-poc-execution, execute-poc-variants, verify-tool-usage, validate-findings, report-agent, audit-sequential, audit-checkpoint, audit-state, audit-exec-tracker, aggregate-findings, poc-pipeline, audit-run-all, finding_gate, chain_builder)

**Part 2 — Cross-script contracts.** What the GATE reads must be exactly what executors write:
- `verify-tool-usage.py` reads: tools-usage.json, variant-usage.json, poc-execution.json, poc-variant-usage.json, variants/, poc-variants/
- grep the `target_dir / "..."` write patterns in each executor and diff. Any gate-read file with no writer = contract gap = pipeline silently passes/fails wrong.

**Part 3 — Flag & path cross-check (the #1 silent bug class).**
- Every `--flag` the orchestrator passes to a subprocess MUST exist in that script's argv parser. Live bug found 2026-09-24: orchestrator called `audit-sequential.py --recon-only` (flag doesn't exist) so auto-rework recon was a guaranteed failure.
- Every skill-reference path in scripts MUST resolve: payload/hackskill files live in `skills/security/exploit-cookbook/references/` (92 files). Scripts had pointed at `bb-audit-launcher/references/` (wrong dir, 0/20 refs) — all 3 occurrences fixed.
- Skill-level: grep SKILL.md internal refs (`references/x.md`, `scripts/x.py`) against the skill dir + global scripts dir. 0 broken refs allowed in security/ (audit pipeline); other domains are lower priority.

**Part 4 — Data integrity + manifest sweep.**
- `D:/data hermes/poc-compact/manifest.json`: valid JSON, count repos (2223)
- `nuclei-index.json` + `nuclei-templates/` exist
- FULL sweep: for every manifest entry, `repo_dir / f` must exist (try `\\`→`/` and `/`→`\\` variants — manifest uses backslashes). 2026-09-24 sweep: 61,135 files, found 40 missing across 36 repos → all recovered via raw.githubusercontent.com fetch (`https://raw.githubusercontent.com/{owner}/{repo}/main/{path}`, fallback `master`). Repo name format: `Owner_RepoName` (first `_` splits owner/repo).
- Zero-file repos (304) are legit empty entries, not data loss — do not "fix" them.

**MSYS pitfall (recurring):** MSYS `/tmp` ≠ Windows `C:\tmp` for native Python; `python "C:\tmp\..."` fails. Copy to `$LOCALAPPDATA/Temp` with native-style `/home/agentuser` paths, or `wslpath -w` to convert.

**When a fix is needed:** patch the script, re-run `py_compile`, re-run the failed part of the sweep, report before/after with numbers.

> **Recipes & sweep code:** `references/poc-data-integrity.md` — full manifest sweep + GitHub raw-fetch recovery + MSYS path gotchas.

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

## ⛔ RULE 26: PoC Repos → Extract TECHNIQUES, Not Just Execute 1% (C6b)

**User correction (2026-09-26): "Bagaimana dgn POC varian attack yg udh ad? Ribuan file itu, udh kamu jadikan sumber cara attack exploit blm?"**

Executing matched PoC repos by NAME uses only ~1% of the library: 2,223 repos, 70% are CVE-specific (require identical product/version, never match a generic target), old name-matching + cap 25-50 left 26 repos `PLANNED_BEYOND_CAP` and only ~21 actually executed. The user called this out. The fix is NOT to execute all 2,223 — it's to EXTRACT the attack techniques from ALL of them and fire those at any target.

**The technique-extraction pattern (proven on 2,223 repos → 3,014 unique techniques):**

1. `poc-techniques-index.py` (build once, ~8 min for 2,223 repos): scan EVERY repo's file content (.py/.sh/.md/.txt/.php), extract per file (cap 120 files/repo, 30KB/file):
   - `ENDPOINT` — URL/path with params (classify into sqli/xss/xxe/lfi/ssrf/ssti/cmdi/auth/upload/admin-config/generic)
   - `CURL_TEMPLATE` — `curl ...` command lines (with `-X METHOD`, `-H header`)
   - Dedupe by (type, endpoint|curl) → `poc-techniques-index.json` (3,014 unique)
2. `execute-poc-techniques.py` (C6b, called by orchestrator after C6 refs):
   - Read index → fire technique to target root (relativize endpoints: keep path only)
   - Apply method/headers from curl template → real request via urllib (never shell curl)
   - Rate-limit 0.3s, timeout 120s → `poc-techniques-evidence/tech-NNNN.txt` + `poc-techniques-usage.json`
3. **GATE CHECK 11**: `poc-techniques-usage.json` must exist, non-empty, ≥30% evidence on-disk → else HARD BLOCK.

**Pitfalls:**
- Don't judge the repo library by "how many repos I executed" — judge by "how many TECHNIQUES I extracted and fired". 3,014 unique techniques from 2,223 repos is the real coverage number.
- CVE-specific repos DO contribute: their exploit.py/README contains endpoint+payload patterns reusable on other targets.
- Fire cap per run (~150-300) is fine — the index persists; more techniques = more coverage each run.
- Keep caps growing: track-poc MAX_EXEC 25→50, execute-poc-variants cap 50→100.

**Scripts:** `poc-techniques-index.py` (build) + `execute-poc-techniques.py` (fire). Gate CHECK 11 enforces usage.

**Cap updates (2026-09-26):** track-poc `MAX_EXEC = 150` (was 25→50), execute-poc-variants `matched_names[:150]` (was 50→100). Cap = max repos EXECUTED/extracted per audit to bound runtime — NOT a limit on which repos contribute techniques (the technique index always scans ALL 2,223).

## ⛔ RULE 27: Multi-Session Resume — Per-Phase State, Never Restart from 0A

**User requirement (2026-09-26): "Pastikan jg kalau proses audit Exploit ny makan waktu, session dan context, agar bisa djalankan multi session tanpa harus mengulang dr awal"**

Long audits (0C alone can run hours: C1-C6b with 150-repo caps) MUST survive session/context/provider loss. Two-level resume, both disk-based:

**Level 1 — per-phase (0A→0F).** Orchestrator `run_pipeline` wraps every phase:
```python
if not self._phase_done("0A"):
    self.run_setup()
    self._save_state(completed_phase="0A", current="0B")
```
State file: `~/.chiper/skills/bounty-pack/trackers/audit-pipeline-<safe-target>.json`
`{target, tech, completed_phases:[...], current, updated}` — helpers `_state_file()`, `_load_state()`, `_save_state()`, `_phase_done()`.

**Level 2 — per-sub-phase inside 0C (C2..C6b).** The sub-phase scripts write their own usage JSON; on re-run, orchestrator skips any whose output file already exists on disk (>100B):
- C2 `variant-usage.json`, C3 `business-logic-usage.json`, C4 `poc-execution.json`, C5 `poc-variant-usage.json`, C6 `reference-usage.json`, C6b `poc-techniques-usage.json`

So if 0C dies at C4, resume continues from C5 — C2/C3 are NOT re-run. This is the "exported artifact = resume checkpoint" pattern, same rule as the gate (truth from disk, not claims).

**Pitfall:** `audit-state.py list` (old resume tool) only tracked phase+step historically; the orchestrator now uses its own per-phase state file. Don't confuse the two. If session breaks → just re-run the SAME orchestrator command; it auto-resumes and prints `RESUME MODE: already completed [...]`.

> **Reproduction recipe + measured numbers:** `references/poc-techniques-index-recipe.md` — build command, extraction regex per technique type, fire rules, gate check, and the 3014-techniques build output.

## ⛔ RULE 23: Unified Pipeline Hard-Won Fixes + Findings Quality Bar

**Session findings (2026-09-26):** full end-to-end run (0A→0F) exposed real bugs and a user-mandated quality bar. Read the full transcript + code recipes in `references/unified-pipeline-fixes-2026-09-26.md`:

- **Infinite recursion**: `force-full-execution.py` must be a LEAF — never re-spawn `audit-run-all.py`/orchestrator (that's what made "STEP 1 never finish").
- **URL→filename sanitization** on Windows for output dirs AND tracker names (no `://`, `/`, `:`, `?`, `=` in paths).
- **C4**: execute ALL matched PoC repos with entry point (required types first, cap 25) — not just REQUIRED_TYPES (else C5 starves).
- **C5**: payload-file patterns must include `CVE-*.py`/`exploit*.py`/`main.py` + code-file fallback (old patterns matched 0/51 repos).
- **aggregate-findings**: recursive rglob (was root-only), schema-complete findings (severity/poc/impact/chain), severity mapped from evidence keywords.
- **chain_builder**: cap 40 signal-findings + `--max-len 3` (permutations of 120 findings = hang).
- **validate-findings**: accept `poc` OR `evidence` OR `text`; auto-reject by-design + phishing/social BEFORE PoC check.
- **`.py` file association on Windows = VS Code opens instead of executing** — always prefix `python.exe "tool.py"`.
- **Findings Quality Bar (finding_gate.py + validate-findings.py)**: DROP = by-design / phishing-social / info-class / dead-chain / speculative. DOWNGRADE = overclaim language / 4xx-as-success / no evidence marker / no impact signal. REPORT = evidence marker + real impact signal. **Low still allowed.**
- **Proof technique**: known-vulnerable express app (13 validated High in ~10 min) vs clean httpbin (0) — proves tools+knowledge sufficient; missing findings = shallow recon (add depth-1 link crawl) or aggregator schema gap, NOT missing tools.

## ⛔ RULE 21: POC Execution Plan Generation Fix (Windows path resolution)

**Live discovery (2026-09-24):** `track-poc-execution.py`'s `generate_plan()` always returned `None` because it tried to parse `poc-pipeline.py full`'s stdout as JSON — but the script writes a human-readable banner to stdout AND saves machine-readable JSON to `~/.chiper/skills/bounty-pack/poc-plans/<target>.json`. Reading stdout failed → `NO_POC_MATCHED` → 0 PoCs executed → Gate C8 (`poc-variant-usage.json empty`) failed repeatedly.

**The FIX:** Change `generate_plan()` to **read the saved plan file first**, only fall back to stdout parsing if the file is missing.

```python
def generate_plan(target, tech_list):
    """Run poc-pipeline.py full; read the JSON plan it saves to disk.

    Note: poc-pipeline 'full' prints a human-readable banner to stdout and
    writes the machine-readable plan to OUTPUT_DIR/<target>.json — it does NOT
    print JSON to stdout. So read the saved file (fall back to stdout parse).
    """
    cmd = f'python "{SCRIPTS_DIR}/poc-pipeline.py" full "{target}" --tech "{tech_list}"'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        log(f"⚠️  poc-pipeline.py exit {r.returncode}: {r.stderr[:300]}")
        return None

    # Primary: read the JSON plan poc-pipeline saves (OUTPUT_DIR/<target>.json)
    out_dir = Path(os.path.expanduser("~/.chiper/skills/bounty-pack/poc-plans"))
    safe = target.replace("https://", "").replace("http://", "").replace("/", "_")
    plan_file = out_dir / f"{safe}.json"
    if plan_file.exists():
        try:
            plan = json.loads(plan_file.read_text())
            if isinstance(plan, dict) and "plan" in plan:
                return plan
        except Exception as e:
            log(f"⚠️  Could not read plan file {plan_file.name}: {e}")

    # Fallback: parse JSON from stdout (older poc-pipeline printed JSON)
    try:
        start = r.stdout.index("{")
        plan = json.loads(r.stdout[start:])
        return plan
    except (ValueError, json.JSONDecodeError):
        log("⚠️  Could not parse plan from poc-pipeline output")
        return None
```

Also ensure `--tech` is passed properly (orchestrator used positional arg without flag earlier). Add `import os` at top for `os.path.expanduser()`.

> **Debugging transcript:** `references/session-lessons/orchestrator-poc-plan-fix-2026-09-24.md` — full conversation transcript showing the triple-rework loop until the fix landed.

## ⛔ RULE 22: Tool Detection on Windows — Use shutil.which + Explicit Paths

**Live discovery (2026-09-24):** `force-full-execution.py` hardcoded Linux bin paths (`/home/windows10/go/bin/`) → tools like `sqlmap`, `dalfox`, `nuclei` showed `NOT_FOUND` even though they were installed under `C:/go/bin` and `/home/agentuser/go/bin`. The gate checked 5 static paths that didn't include Windows locations.

**The FIX:** First call `shutil.which(tool)` for standard PATH lookup; if that fails, check explicit Windows dirs:
- `Path.home() / "go/bin"`
- `"C:/go/bin"`
- `Path.home() / "/usr/local/bin"`
- `Path.home() / "~/.chiper/skills/bounty-pack/bin"`

Try extensions `.exe` explicitly too (native Python doesn't add it in PATH search). This pattern ensures tools fire reliably across both Unix and Windows environments.

> **Reference:** `references/tool-detection-windows.md` — full list of tool paths and verification commands for each.

## Per-Tool Timeout Values (tool_router.route_and_run defaults)

| Tool | Timeout | Max Retry |
|------|---------|-----------|
| sqlmap | 900s | 3x |
| dalfox | 600s | 3x |
| nuclei (per tag) | 600s | 3x |
| gobuster dir | 600s | 3x |
| CORScanner | 300s | 3x |
| race-checker.py | 300s | 3x |
| graphqlmap | 120s | 3x |
| subfinder | 180s | 2x |
| httpx | 240s | 2x |
| curl manual | 30s | 3x |

### ⛔ Cap a layer that LOOPS the router — per-tool timeouts multiply (C6) ⛔

`execute-references.py` (and the other looping executors) call `tool_router.route_and_run` **once per
clue** — up to `--max-clues 200`. With no cap inside the router the arithmetic is
`200 clues × up to 1200 s` against the orchestrator's **single** `timeout=2400` for that step, so any
target with ≥4 heavy tool calls is *guaranteed* to die at C6 with
`subprocess.TimeoutExpired … timed out after 2400 seconds`. That abort is an **environment failure →
`NO RESULT / re-run pending`**, never a target negative (RULE 35.5), and it costs the whole report
because the gate never passes.

**Rule: a layer that can invoke a tool more than once must carry its own wall-clock budget.**

```
route_and_run(class, target, out_dir, vector="", ev_dir=None, timeout_cap=None)
    # timeout_cap clamps EVERY tool call (module global _TIMEOUT_CAP); default None = unchanged
    # behaviour for C1/force-full-execution and every other single-shot caller

execute-references.py --max-clues 200 --budget 900 --tool-cap 120
    # --budget : monotonic deadline checked at the top of the clue loop; on exhaustion the loop
    #            stops and the remainder is recorded as a SKIPPED_BUDGET meta entry in
    #            reference-usage.json (skipped ≠ negative — say "re-run pending", never "clean")
```

**Second, Windows-specific trap in the same code path:** `subprocess.run(…, shell=True, timeout=N)`
kills only `cmd.exe`; the grandchild (sqlmap/arjun/nuclei) keeps the stdout pipe open so `communicate()`
blocks until the grandchild finishes — **the timeout value is a lie** (measured: a 3 s child under
`timeout=1` returned after 3.2 s while reporting `TIMEOUT 1s`). `_run()` must `Popen` and then
`taskkill /F /T /PID <pid>` on timeout, keeping the literal `TIMEOUT <n>s` substring so the status
classifiers still match.

Verify the patch landed AND that wall clock is bounded (both, or you have fixed nothing):

```bash
python -m py_compile tool_router.py execute-references.py
grep -c _TIMEOUT_CAP tool_router.py ; grep -c timeout_cap tool_router.py execute-references.py
python -c "import importlib.util as u;s=u.spec_from_file_location('tr','<scripts>/tool_router.py');tr=u.module_from_spec(s);s.loader.exec_module(tr);tr._TIMEOUT_CAP=2;import time;t=time.monotonic();rc,o,e=tr._run('python -c \"import time;time.sleep(30)\"',timeout=900);print(rc,round(time.monotonic()-t,1),e[-40:])"
# expect rc=-1, ≈2.6 s, 'TIMEOUT 2s (process tree killed)'
```

Then re-run the failed stage standalone with the flags above and re-zip the bundle (the zip goes stale the
moment a live script is patched — inject the two entries surgically, assert per-entry md5 + the entry
count, back up first).

> **Full recipe (root cause, both patches, verification commands + measured numbers, surgical zip rebuild,
> and which looping executors share the same cliff):** `references/pipeline-tool-timeout-budget.md`

## ⛔ RULE 36: EVM static-tool SEVERITY LABELS ARE NOT FINDINGS — triage every one

`aderyn` and `mythril` emit confident "High" labels that evaporate on inspection. Verified 2026-10-01 on the
Superstate engagement: **4 scanner "High" findings, 0 real vulnerabilities**. Do the triage, don't pass the label through.

**aderyn's `High` classes are mostly template matches on the *shape* of a call.** All three that fired were FPs:
- `ETH transferred without address checks` -> it flagged plain `redeem(...)` functions. The caller pays and
  `receive()`/`fallback()` revert, so the contract holds no ETH.
- `Arbitrary from passed to transferFrom` -> the flagged line was `ERC20Upgradeable.transferFrom({from: src, ...})`
  inside a normal `transferFrom(src,dst,amount)` that spends the allowance first. That IS the ERC20 signature.
- `Storage array edited with memory` -> the helper was `internal pure`, comparing keccak hashes only; the real
  write was the next line. Read the callee before believing the label.

Rule: for each aderyn High, open the cited `file:line` **and the callee**, and write one sentence saying why it is
or isn't reachable. If you cannot name an actor who gains something, it is not a finding.

**mythril in bytecode mode cannot know the caller, so it labels arithmetic it cannot prove safe as High.** Attribute
the finding to a real function before judging it: mythril prints the calldata it used, so map the 4-byte selector
yourself.

```bash
# txn sequence from the mythril report: calldata e24df75400000...
cast sig "initialize(address,uint256,address,uint256)"   # -> 0xe24df754  <- attribution
cast sig "redeem(uint256)"                               # -> 0xdb006a75
```
On this target `e24df754` was `initialize(...)`, not the money math — which is what downgraded a "High" to QA.
Generating the whole selector table up front (`for s in "<each public fn>"; do cast sig "$s"; done`) makes
attribution a lookup instead of a guess.

**Your PoC must be able to FALSIFY your own model.** The first PoC for that finding asserted the contract was
*permanently* bricked. It FAILED, because `setRedemptionFee(0)` still succeeds — the cap only blocks increases
above the bound, so the owner can lower it back and recover. The failing assertion is what produced the correct
rating (Informational/QA). A PoC that only ever confirms your hypothesis is worthless: write the assertion you
expect to be hardest to satisfy, and if it fails, you learned the severity.

**Honest vocabulary for the result** — never "mythril says High so we have a High":
`CONFIRMED (PoC passes, actor + impact named)` · `FP (cited line read, impact impossible)` ·
`REAL BUT QA (reachable only by owner/deployer, self-recoverable, no funds at risk)` · `NO RESULT (tool never completed)`.
Record the downgrade and the reason in `findings.json`; the failed assertion is evidence, keep it.

## ⛔ RULE 37: A delegated subagent that times out at 600s has still WRITTEN TO DISK

`delegate_task` children are killed at 600s and **their summaries are discarded** — but their files are not.
Verified 2026-10-01: three batch children timed out; the disk held subfinder/httpx/nuclei output (402 KB of nuclei
JSONL), full-git-history patches for 3 repos, the decoded malware payload, and two aderyn reports. That partial
output turned out to be the session's most valuable material.

Before redoing a timed-out child's work, ALWAYS harvest first:

```bash
ls -la <out_dir>/            # per child: did it create its output folder?
find <out_dir> -type f -newermt '-2 hours' | head -40
wc -c <out_dir>/*            # a 0-byte json + a populated sibling = tool ran but produced nothing
```

Then judge each artifact on its own: a `trufflehog.json` of 0 bytes WITH a populated `.stderr` means the tool ran
and found nothing; a 0-byte file with no stderr means it never started. Write the child's intended summary yourself
from the artifacts.

Design children so this is cheap: make each one write raw tool output to its own directory **first** and reason
afterwards, and put the output path in the task so the artifacts are findable. A child whose only product is prose
in its final message loses everything on timeout.

## ⛔ RULE 38: Enumerated hosts and SPA routes need a DIFFERENTIAL — most "found" surface is noise

Three differentials that turned would-be false findings into verified negatives on 2026-10-01:

1. **Wildcard DNS kills half of subfinder's output.** Prove it with random names before reporting any host:
   ```bash
   for h in zzz-nope-12345.target.com totally-random-9f3a.target.com; do
     python -c "import socket;print(socket.gethostbyname('$h'))" 2>/dev/null || echo NXDOMAIN; done
   ```
   NXDOMAIN on both => no wildcard => hosts that DO resolve are real. On this engagement that test proved 10
   subfinder hosts (`eks.ci`, `eks.security`, `app`, `test`, `preview`, `bbs`, `doc`, `mail`, `openpgpkey`,
   `assets-worker.devddx`) were NXDOMAIN FPs that would otherwise have been reported as "internal hosts discovered".
   A host that resolves but serves no working HTTPS (000) and has no CNAME is a dangling proxied record —
   informational, NOT a takeover candidate. Real takeover check: `nuclei -l subs.txt -t <mirror>/http/takeovers`.
2. **`.well-known/*` on an SPA returns 200 for everything.** Seven paths all returned 200 with ~31.5 KB — the exact
   same size. Confirm by diffing content against a deliberately bogus path:
   ```bash
   curl -s https://target/.well-known/security.txt -o a.html
   curl -s https://target/zzz-not-a-real-path-98765 -o b.html
   grep -oE '<title>[^<]*</title>' a.html b.html    # same title => catch-all, NOT real files
   ```
   Without this check, seven 200s become seven report entries.
3. **`OPTIONS` separates a real SPA app-API route from the catch-all.** A SvelteKit/Next server route handler is
   method-specific, so `GET` on it returns the SPA shell (indistinguishable from a bogus path) while `OPTIONS`
   tells the truth:
   ```bash
   curl -s -X OPTIONS -o /dev/null -w '%{http_code} allow=%header{allow}\n' https://target/api/admin/x
   # 405 allow=GET, HEAD   -> route EXISTS
   # 200 allow=            -> unhandled OPTIONS / catch-all, NOT evidence of a route
   ```
   Only the 405-with-`allow` result counts as proof a route exists. Mine discovered route JS bundles had already
   named (`/api/admin/funds/{id}/gas-costs/invoice`) — bundle mining finds the *name*, OPTIONS proves the *route*.

**Scoring rule for what comes out of this:** a route that answers an unauthenticated `GET` with `500` instead of
`401/403` is a LEAD, not a finding. No data, no side effect, no proof of an authorization gap => record it as
"unrated - lead", state exactly what is and is not proven, and never send a state-changing method to confirm it
(that would violate the vendor's "no state changes" rule and the `payment-entitlement-bypass` line).

> Full walkthrough with the raw transcripts: `references/evm-and-recon-triage-2026-10-01.md`

## Config Requirements

- `context_length`: 1,000,000
- `max_iterations`: 200
- `max_tool_calls`: 300

---
*Created: 2026-09-20 | Updated: 2026-09-26 (RULE 27 multi-session resume; caps →150)*
*Source: User-identified failure modes + overclaiming corrections*

---

## Companion Reference — `poc-technique-atlas` (additive, never overrides)

Method-level technique shelf extracted from a 2,223-repo local PoC corpus (filtered of
malware/scam, deduped) + PortSwigger WSA. **Read ONE class file per phase** — it does NOT
count against the phase context budget (on-demand shelf).

- `references/00-INDEX.md` → 27 classes (RCE 357, IDOR/BOLA 87, SQLi 83, Crypto 75,
  Auth-bypass 68, XSS 59, Info-disclosure 48, LFI 47, Deserialization 22, SSRF 19,
  Cloud 14, SSTI 7, Race 5, XXE 5, Prototype-pollution 2, …). 1,901 techniques total.
- `references/portswigger/00-INDEX.md` → 29 WSA topics.
- Use it to pick the *method* for the class you are testing; owner skill rules still win.
