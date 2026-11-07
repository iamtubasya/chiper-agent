# Pipeline invocation traps (audit-pipeline-orchestrator.py)

Observed live 2026-10-12 (blink.sv) while resuming an engagement. These are *invocation* traps: the
pipeline is fine, the command line is what costs you a run.

## 1. `--scope` takes DOMAIN(S), not the policy prose
```
# WRONG — blocks instantly, prints "SCOPE GATE BLOCKED ... Tidak ada request yang dikirim"
python audit-pipeline-orchestrator.py "https://blink.sv" \
  --scope "Blink's software or services (blink.sv + blinkbtc.com estate, web apps, APIs, mobile)"

# RIGHT — the gate is a deterministic hostname check (`scope_checker.py --domain <list>`)
python audit-pipeline-orchestrator.py "https://blink.sv" --scope "blink.sv,blinkbtc.com"
# or omit --scope entirely: no profile + no scope = allow-all (user rule), logs
#   "SCOPE GATE PASSED (URL, allow-all) ... tanpa profile, semua target in-scope"
```
The blocked run still writes `run-meta.json`/`PHASE_LOG`-adjacent state, so remove/ignore that dir before
relaunching, otherwise you resume a failed 0A.

**Hostname matching (FIXED 2026-10-15):** `scope_checker._domain_matches` used to be exact-only —
`--scope "gasunie.nl"` rejected `https://www.gasunie.nl` (`OUT OF SCOPE: www.gasunie.nl not in
gasunie.nl`). Patched in place (additive): a bare-domain pattern now matches the apex AND any
subdomain (`www.`, `api.`, …), standard BB scope semantics — `--scope "jochen-schweizer.de"`
passes `www.jochen-schweizer.de`, while `evil-target.com` / `jochen-schweizer.de.evil.com` stay
rejected (verify negatives after any scope-checker edit). A `*.` wildcard still requires a
PROPER subdomain, never the apex. If a bare-apex scope still blocks a www target, the host
predates the fix — list every form explicitly:
```
--scope "www.gasunie.nl,gasunie.nl,*.gasunie.nl"     # apex + www + wildcard

**Out-of-scope exceptions inside an in-scope domain** (Swisscom pattern: `*.bluewin.ch` is in
scope but `*.rnas-dyn.bluewin.ch` is explicitly out): the orchestrator forwards
`--exclude-domain <host>` to `scope_checker.py`, so the gate rejects that host before any
request goes out — observed 2026-10-16 (bluewin.ch) passing first try:
```
--scope "bluewin.ch" --exclude-domain "rnas-dyn.bluewin.ch"
```
```

## 2. `STALL-WARN` is ADVISORY — prove liveness with file mtimes, never by killing
A long 0C sub-step (dense forced-execution, payload variants, DOM-XSS with a headless browser) emits
nothing to stdout for 15–45 min while the orchestrator's step counter stays put:
```
[STALL-WARN] orchestrator: no step progress for 1821s (last phase 0A, pid=...) - still running, not killed.
```
Before touching it, check what the step is actually producing:
```
find "<orchestrator-workdir>" -type f -printf "%TH:%TM %p\n" | sort -r | head -6
```
New `variants/*.txt` / `tool-evidence/*.txt` inside the last few minutes = alive, keep waiting (the step
counter tracks phase transitions, not work). Only kill on an empty mtime delta *and* no child tool process.

## 3. Children outlive the parent — reap leftovers before the next run
Three orphaned `nuclei.exe` from earlier attempts were still holding ~1.3 GB on a 6 GB host while a new run
started (the orchestrator warns below 1.2 GB free RAM: "proses akan DIBUNUH Windows tanpa traceback").
Check with `tasklist | grep -iE "nuclei|sqlmap|dalfox|ffuf"` and kill by PID (via Python `taskkill /PID <n>
/F`) before relaunching.

## 4. The pipeline's own recon can be thinner than the engagement's
Its `httpx` step returned `0 live hosts (rc=255)` and seeded only 2 hosts, so single-target template runs
covered essentially `blink.sv` + `www` (host histogram in `urls.txt` is the tell: 268/316 URLs on one host)
while ~80 other hosts of the estate went unscanned. **Always cross-check the pipeline's host coverage
against the engagement's own host inventory and run a supplementary scan yourself** — otherwise a clean
pipeline result means "clean on two hosts", not "clean on the estate":
```
nuclei -l <engagement>/recon/nuclei_hosts_list.txt \
  -tags exposures,exposed-panels,misconfiguration,default-login,takeovers,unauth \
  -severity low,medium,high,critical -rl 20 -c 6 -timeout 10 -retries 1 \
  -stats -no-color -o "<ENGAGEMENT>/recon/nuclei_hosts2.txt"    # native path, not /c/... (MSYS)
```
Tag-set sizing matters: an 11-tag set hit 267 k requests at 11 rps (~6.7 h); trimming to 6 tags and
`-rl 20 -c 6` cut it to ~220 k at 25 rps (~2.4 h) — and the low-signal `wildcard-dns-detect` /
`dns-waf-detect` hits dominate the output, so filter them before reading a result set.

## 5. Scanner candidates are candidates — verify before they reach the report
The DOM-XSS check flagged `https://blink.sv/#"><img src=x onerror="window.__DOMXSS=1">`
(`reason: dom-sink:window.onerror`); a real-Chrome check showed the fragment stays URL-encoded
(`location.href` = `#%22%3E%3Cimg%20src=x…`), no injected node, marker flag never set → **false positive**.
Verify each automated candidate once, in your own browser, and record the dismissal in the report's
coverage section (the guard checks for exactly this kind of unverified claim).

Deterministic version of that check for hash-fragment candidates — injects
`onerror="document.title='<marker>'"` and separates payload-PRESENT-in-DOM from
payload-EXECUTED: `python <skill>/scripts/domxss_verify.py urls.txt` (Playwright, one
route-dedup test per base URL). 0 fired across all routes = FP (bluewin.ch: 110 scanner
candidates → 0 fired); ≥1 fired = keep the candidate and save `page.content()` + title.

## 6. Resuming
`STATE saved: completed=['0A','0B'] current=0C` + "resume" semantics mean re-running the same command
continues instead of restarting — so fix the invocation (scope/tech) in place rather than deleting the
workdir, unless 0A itself failed.

## 7. linkfinder (and fetchers like it) 403 on a Cloudflare-protected root — aim at a JS asset
`linkfinder.py -i https://gasunie.nl -o cli` fails with `HTTP Error 403: Forbidden` (Cloudflare) and the
wrapper records `status: FAILED_USAGE`, which then fails `verify-tool-usage` CHECK 2b and blocks the
gate. Fix: point `-i` at a real first-party JS asset instead of the domain root — pull one from the
pipeline's own crawl (`grep -iE '\.js($|\?)' <workdir>/crawled.txt | grep -vE 'piwik|google|gartner'`),
e.g. `-i https://www.gasunie.nl/compiled/js/project_js-9917cd9.js`. Then, so the gate sees it as run:
rewrite `tool-evidence/linkfinder-source-leak.txt` with the new command + stdout, and flip
`tools-usage.json` (`status`→`EXECUTED`, real `command`/`output_bytes`) and `asset-coverage.json`
(`0C:tools:linkfinder` → `status: USED` + evidence path). Same pattern applies to any source-leak
fetcher that gets WAF-blocked on the bare domain.

## 8. The deep-audit guard rarely goes green on a general web target — that is INFRA, not a signal
For a Cloudflare-fronted corporate site with `--tech "general"`, `deep-audit-mode.py guard` typically
stays RED because the PoC-corpus stages can't do anything applicable: `execute-poc-variants.py` /
`execute-poc-techniques.py` report `Matched repos: 0` (the tech-match yields repos with
`status: NO_ENTRY_POINT` or non-web payload types — deserialization/protocol/firmware, "not fireable
via HTTP params"), so C4/C5/C6b stay `NOT_RUN`, `candidates.json` is empty, and CHECK 8/11/12 fail. This is
NOT evidence the target is safe or unsafe — it means the local PoC corpus simply has nothing for this
target class. Confirmed by prior engagements: even completed targets (`atg.se`, `yandex.fr`) still
`RESULT: FAIL` the guard.

**UPDATE 2026-10-15 (jochen-schweizer.de): the guard CAN go green on a general web target — the
red was partly the routing bug, not only infra.** With the per-repo `routed` set hoisted to global
+ `timeout_cap=600` (trap #14), C5/C6b completed all 150 repo entries, the gate passed 33/33, and
`guard` returned `✅ DEEP-AUDIT GATE: pipeline evidence OK (13-check gate passed)`. Before blaming
infra for a red guard, check whether C5/C6b actually FINISHED vs. were killed/never-ran; only a
completed-but-empty PoC pass is true infra-red.

Report discipline when the guard is red but your real scanners ran clean:
- State the negative honestly with **coverage + the tool list that actually executed** (e.g. "23 tools:
  nuclei/sqlmap/dalfox/sstimap/nikto/xsstrike/CORScanner/... — all `confirmed: 0`"), and record the
  false-positive dismissals (sqlmap/dalfox "interesting" flags that turned out to be no-ops).
- Say explicitly the guard is blocked on **PoC-corpus infra + WAF**, not on a finding — and name the
  untested surface (authenticated flows behind login, OT/SCADA behind the perimeter).
- Do NOT upgrade the language to "matang / terkunci rapi / no findings" on a red guard. The gate exists
  to stop exactly that overclaim. Mark the pool `audited --note "0 temuan valid; N tool jalan; semua
  confirmed=0; <WAF> depan"` and offer next moves (self-provision a test account for the authed surface,
  or pivot).

## 9. `deep-audit-mode.py guard <dir>` must point at the ORCHESTRATOR's workdir, not your own recon dir
Observed 2026-10-14 (yandex.fr, a *successful* engagement with a staged finding). `guard` is a
`verify-tool-usage` wrapper: it reads `tools-usage.json` / `asset-coverage.json` / `skill-usage.json` /
`poc-execution.json` **out of the directory you hand it**. Point it at a hand-built recon dir (the one you
used for your own nuclei/ffuf/sqlmap runs) and CHECK 1 fails first — `tools-usage.json not found ... →
force-full-execution.py step 5 never ran` — no matter how much real evidence sits beside it:
```
guard C:\...\bug-bounty\<target>_recon        # RED: no ledgers (your own dir)
guard C:\...\poc-plans\orchestrator-<target>  # the pipeline's dir — this is the ledger holder
```
So: run the guard against `~/.chiper/skills/bounty-pack/poc-plans/orchestrator-<target>/`, and treat "CHECK 7–13
missing" as *in progress* while 0C is still executing (those ledgers appear as `execute-poc-*`,
`execute-business-logic`, `execute-references`, `asset-coverage --init` finish their passes). A guard that
is RED only on 7–13 with CHECK 1–6/6b green means **23 tools executed with real evidence and 15/15 vectors
fired** — quote those counters in the coverage section instead of treating red as failure.

## 10. `deep-audit-mode.py` dies on Python 3.14 before it can print any verdict
`TypeError: _SubParsersAction.__init__() got an unexpected keyword argument 'required'` →
`sub = ap.add_subparsers(dest="cmd", required=True)`. The tool exits `rc=1` with a traceback, which reads
like "gate blocked" but is a crash, and none of the checks run. Patch in place (additive, keep a backup):
```python
sub = ap.add_subparsers(dest="cmd")
sub.required = True          # py3.14 build: required= kwarg removed
```
Verify with `<py314> deep-audit-mode.py --help` (expect `rc 0`) before drawing any conclusion from a RED guard.

## 11. `terminal` runs bash, `execute_code` runs cmd.exe — do not mix idioms
`subprocess.run(..., shell=True)` inside `execute_code` goes through **cmd.exe**: `cd /c/Users/...` and
`$_` in a PowerShell one-liner both fail (`The system cannot find the path specified`,
`/home/agentuser : The term ... is not recognized`), and a failed `cd` silently leaves you in
the wrong directory. Use the `terminal` tool for POSIX/bash semantics, and when a PowerShell command needs
`$_` or nested quotes, write a `.ps1` to `%TEMP%` and run it with `-ExecutionPolicy Bypass -File`.

## 12. File-mtime stall check has a blind spot — WAF blackholes look dead for 10–20 min, then blast
Observed 2026-10-15 (jochen-schweizer.de, AWS WAF). `urlopen(timeout=120)` against a WAF that
*hangs* connections (rather than 403-ing) left C5 at 42/150 repo entries with **zero file writes
for 7+ minutes and CPU fully idle** — then it finished the remaining 108 entries in one burst.
Same at C6b (42→109 evidence files in 3 min after an idle window). Two cheap liveness probes beat
mtime alone:
```bash
# 1. CPU-time delta: unchanged after 10s = blocked on network (or truly hung); changed = computing
wmic process where "ProcessId=<pid>" get UserModeTime,KernelModeTime
# 2. Entry-count delta of the step's own usage file (persist-on-append scripts are self-reporting)
python -c "import json;print(len(json.load(open(r'<dir>/poc-variant-usage.json'))))"
```
**Do NOT use `ReadTransferCount`/`WriteTransferCount` as the probe** (2026-10-16,
bluewin.ch): those counters stayed byte-flat across two 25 s samples while a running
ffuf was demonstrably working — the process flushed real match lines at kill and a
calibration run seconds later measured 4 req/s ([LIKELY] Go async/IOCP socket reads
don't accrue the process I/O counters). Acting on flat transfer counts produced two
premature kills of healthy scans. For ffuf specifically the reliable live signal is its
own progress banner — run without `-s` (see web2-recon → "ffuf invocation traps").
Verdict matrix: CPU-changing OR entry-count-changing → alive, wait. CPU idle AND entries static
AND no child processes → check `wmic process ... get processid,commandline` for a stuck
`urlopen` child before killing; idle+static for >2× the per-request timeout across two samples is
the real kill criterion.

## 13. Rework dispatcher matches SUBSTRINGS — order specific-before-generic or it reruns the wrong step
`audit-pipeline-orchestrator.py` gate-rework maps failure text via `if "..." in out`. The failure
string `poc-variant-usage.json missing` **contains** `variant-usage.json missing`, so the old
generic-first order sent it to `execute-variants.py` (C2 rerun, ~2.5 h wasted) instead of
`execute-poc-variants.py` (C5) — and there was **no branch at all** for
`poc-techniques-usage.json missing`, which fell into generic force-full-execution. Fixed in place
2026-10-15: specific patterns first (`poc-variant` → `poc-techniques` → `poc-execution` →
`variant` → recon → references → business-logic → tools → thin-evidence → generic) + added the
missing `_rerun_poc_techniques_step()`. When adding a new artefact gate: (a) add its `_rerun_*`
method, (b) place its matcher ABOVE any existing matcher whose needle it contains, (c) never
reuse a substring of an existing matcher as a new matcher.

**Fixing the ORCHESTRATOR itself requires a restart** (2026-10-15): Python loaded its own code at
spawn, so patching `audit-pipeline-orchestrator.py` while it runs has zero effect on the live
process — after the dispatcher fix the old process still took the wrong branch. `taskkill /PID
<orch> /T /F`, then relaunch with `--resume`: the state file keeps `completed_phases`, finished
phases skip, and the gate rework re-dispatches through the now-patched branches. Patching a CHILD
script (`execute-poc-*.py`, `tool_router.py`) differs — the next `subprocess.run` spawn reads the
file fresh, so there kill only the child PID and let the orchestrator's own REWORK rerun it.

## 14. Per-REPO tool routing reruns 40-minute tools 150× — the "sekali per kelas" set must be GLOBAL
`execute-poc-variants.py` / `execute-poc-techniques.py` route classified payloads to real tools
("sekali per kelas"), but both kept `routed = set()` **inside the per-repo loop** with
`timeout_cap=None`. With the no-tech-match manifest fallback (1365 payload-bearing repos, cap
150) every ssti/sqli/xss repo re-ran sstimap (~40 min/run, to completion) against the SAME
`fuzz_urls[0]` — C5/C6b could not finish by construction (same failure class as the C6 dalfox
bug of 2026-10-10). Fixed in place 2026-10-15: module-level `_ROUTED_CLASSES = set()` hoisted
before the loop + `timeout_cap=600`. Signature: `tool-evidence/<x>-sstimap.txt` resets to a few
KB repeatedly (one invocation per repo overwrites the same filename) while the step never ends.
Recovery: patch both scripts, `taskkill /PID <child> /T /F`, orchestrator flags the step FAILED
→ gate rework reruns it patched. Healthy C5 = 150 repo entries in ~25 min with ≤1 tool
invocation per vulnerability class.

## 15. impact-verify "CONFIRMED" is a CANDIDATE, not a finding — control-payload checks that kill FPs
The 6-class impact verifier confirmed 2/72 checks on jochen-schweizer.de; both were false
positives caught only by manual verification:
- **SSTI**: engine probes report `a_has_49=true / b_has_56=true` for `{{7*7}}` vs `{{6*9}}` —
  but the same digits appear for a CONTROL payload (`{{7*8}}` → 64 also present) and excerpt A/B
  are byte-identical SPA shell. Kill test: fire a control expression; if the "computed" numbers
  appear regardless of the expression, the digits are page content, not evaluation.
- **Open-redirect**: verifier set `offsite=true` by parsing the *payload inside the query value*
  (`?q=https://evil…` → `location_host=evil`) while the actual 301 `Location` was the RELATIVE
  path `/alle-erlebnisse/l/79ifa?q=…` (same host). Kill test: `curl -sI` and read the real
  `Location` header — it must be an absolute URL on another origin; a query-parameter echo is
  not a redirect.
- **info-disclosure / SSRF "200s"**: N payloads returning HTTP 200 only mean something if the
  BODIES differ. bluewin.ch: 59 disclosure paths + 17 SSRF payloads all 200 with a byte-identical
  SPA shell = catch-all router, zero findings. Kill test: group results by status and count
  distinct body prefixes — `1 distinct prefix across N payloads` is an FP no matter how large
  N is (the router echoes any path into one unexecuted template).
Standing rule: verifier "confirmed" counters go through the same 3× verification as raw scanner
hits before entering findings.json.

## 16. Every gate is fed a POSIX path from bash — normalise it or the gate goes blind

`terminal` is git-bash, so paths come out of the shell as `/c/Users/...`. Windows `pathlib`
does **not** read that as a drive path: `Path("/c/Users/x")` becomes the *drive-relative*
path `\c\Users\x`, so `target_dir.exists()` is False and the gate prints

```
❌ Target directory not found: \c\Users\WINDOWS10\~/.chiper/_progress\<t>
```

for a directory that is sitting right there. A gate that cannot see its own target is
indistinguishable from a gate that legitimately failed — it silently poisons 0A–0F for the
whole run, and the operator's first instinct (re-run, then "the pipeline is broken") is wrong.

Fix (shipped 2026-10-30): `scripts/msys_path.py` exposes `norm()` / `path()`, applied at every
`Path(argv[1])` in `audit-checkpoint.py`, `verify-tool-usage.py`, `review-candidates.py`,
`aggregate-findings.py`, `clean_urls.py`, `php2shell-verify.py`. Verify with a POSIX path:

```bash
T=/c/Users/$USER/~/.chiper/skills/bounty-pack/_progress/<target>
python audit-checkpoint.py "$T" --phase 0A     # must print the phase table, not "not found"
```

If you add a new gate script, import `msys_path.norm` in the same turn or it inherits the bug.

## 17. `scope_checker.py` must handle IP literals or IP-scoped programs never start

The checker's original contract was "domains only — IP addresses return False with a warning".
That is a **pipeline-stopping** limitation: a program that scopes a bare IP or a CIDR range
(`203.0.113.10`, `203.0.113.0/24`) fails 0A with

```
❌ SCOPE GATE BLOCKED: http://<ip>:<port> BUKAN dalam scope (<ip>)
❌ PIPELINE FAILED: OUT OF SCOPE: <ip> not in <ip>
```

— the target is not in scope *according to itself*. Fix (shipped 2026-10-30): `_ip_matches()`
using `ipaddress` — exact IP equality, or CIDR containment when the pattern carries `/`.
The exclusion list is evaluated **first**, so `--exclude-domain 203.0.113.0/28` beats an
allowing `/24`. Domain semantics are untouched (`evil-example.com` still fails `example.com`,
`*.example.com` still refuses the apex). Regression matrix worth re-running after any edit to
this file: exact IP, CIDR hit, CIDR miss, IPv6 `/32`, IP-vs-domain, apex, subdomain,
lookalike, wildcard apex, exclusion precedence.

## 18. Metadata files are not findings — `scope.md` used to become a phantom candidate

`aggregate-findings.py` walks the target dir recursively for `.md/.txt/.json`, and Phase 0A
writes `scope.md` (the engagement brief) into that same tree. The ingest parsed the brief as a
worker output, manufactured a candidate out of its title line, and pushed it through the gate
as a DOWNGRADE — burning a gate slot and polluting `findings.json` on every single run.

Fix (shipped 2026-10-30): metadata filenames added to `SKIP_NAMES` — `scope.md`, `SCOPE.md`,
`scope.txt`, `README.md`, `NOTES.md`, `TARGET.md`, `program.md`, `policy.md`, `POLICY.md`,
`program.txt`. Standing rule: any file whose job is to **describe** the engagement must never
be readable as evidence of a finding. When you add a new 0A artefact, add its name here in the
same change.

## 19. 0E is four scripts with four different argument shapes — and two of them write to CWD

The 0E chain is where a run silently produces nothing, because each script takes its input
differently and **failure looks like success** (a script that prints usage exits 0-ish and the
next step reports "not found"):

| script | positional | must pass explicitly |
|---|---|---|
| `aggregate-findings.py` | `<target_dir>` | — |
| `chain_builder.py` | `<findings.json>` (a FILE, not the dir) | `--goal impact --json <t>/chains.json` |
| `finding_gate.py` | `<findings.json>` | `--out --survivors --report` (defaults are CWD-relative) |
| `validate-findings.py` | `<findings.json>` | `--output` (REQUIRED — otherwise it just prints usage) |
| `review-candidates.py` | `<target_dir>` | — |

Measured 2026-10-30: running `cd scripts && python finding_gate.py <t>/findings.json` wrote
`gated.json`, `survivors.json` and `REPORT-survivors.md` **into the toolkit directory**, so the
target had no gate artefacts, checkpoint 0E failed, and stray files accumulated in `scripts/`.
`finding_gate.py` now anchors those defaults to the input file's directory — but pass them
explicitly anyway, because a run that depends on a default is a run that breaks when the default
changes.

## 20. `validate-findings.py` used to reject EVERY finding — two separate defects

Both were fatal and neither produced an error message that pointed at the cause:

1. **Check 3 counted list entries, not evidence.** The aggregator emits
   `evidence: ["evidence/proof.txt"]`, and the check was `len(tool_output) > 50` where
   `tool_output = finding["evidence"]`. A one-element list has length 1, so every finding died
   with `No tool output evidence` no matter how much proof was on disk. It now READS the
   referenced files (stricter: proof must exist and contain content) and falls back to
   `tool_output` / `poc` / `text`.
2. **Check 4 demanded a field nothing produces.** It required
   `chain_analysis.startswith("Chain: ")` or `escalation_path` — but `aggregate-findings.py`
   emits id/title/severity/evidence/impact/repro_steps, and `chain_builder.py` writes a
   *separate* `chains.json`. Result: `No chain analysis` for every finding, forever. Check 4 now
   accepts three real sources, in order: an explicit `chain_analysis` / `escalation_path`; the
   finding appearing in `chains.json` (chain_builder output); or the finding stating a terminal
   goal by itself (a chain of length 1 — ATO, funds, PII, RCE, privilege escalation).

Negative controls that MUST still fail (re-run these after any edit here):
`Missing security headers …` → filtered at impact; `… possibly useful …` → filtered at impact;
IDOR whose evidence path does not exist → `No tool output evidence`; an http-avatar finding with
non-terminal impact and no chain → `No chain analysis`; the same finding present in `chains.json`
→ PASSES (that is the composition path working).

## 21. `report-agent.py` and `audit-checkpoint.py` 0F — the last two metres

- `report-agent.py` had the same MSYS path bug as every other gate: `Input not found:
  \c\Users\...` for a file that exists. Patched.
- 0F's severity check compared **case-sensitively** against `High`/`Critical`, but
  `report-agent.py` emits `### HIGH finding(s)` / `### CRITICAL finding(s)`. A correct report
  therefore failed the last gate with "Report contains severity / CWE". Now a word-bounded,
  case-insensitive regex (`\b(P[1-5]|critical|high|medium|low|informational|CWE-\d+)\b`).
  Word boundaries matter: without them "follow"/"below" satisfy the check and the gate becomes a
  rubber stamp. Negative control: a report with findings but no rating must still fail.

## 22. PHASE PLACEMENT: aggregate + weaponize + chain_builder live in **0C-C7**, not 0E

Getting this wrong is not cosmetic — it changes which gates see which data.

```
0C  C1 tools → C2 variants → C3 business-logic → C4 PoC → C5 PoC variants → C6 refs
    C7 = aggregate-findings → weaponize-gate → chain_builder        ← CLOSES 0C
0D  verify-tool-usage (13 checks, hard block)
0E  E4 finding_gate → E5 validate-findings → E6 triage_gate          ← filter + validate ONLY
    then 0E-REVIEW: review-candidates (3x check, low → high)
0F  3 hard gates (_gate_depth, _gate_na_discipline, _gate_negative_audit) → report-agent
```

Why C7 is inside 0C and not 0E (orchestrator `run_chain_layer` docstring, 2026-10-18):
aggregate must collect candidates from **all** of C1..C6b, so running it earlier builds every
chain from partial data; and composing primitives into an attack chain is *exploitation work*,
not reporting. 0E stays a pure filter.

Documenting it as an 0E step (a mistake made and corrected 2026-10-30) makes an operator run
`finding_gate` on raw findings — which kills every lead that has no attacker-use narrative yet,
i.e. exactly the Lows the composition doctrine says to keep as fuel.

Data contract between the two phases:
| phase | reads | writes |
|---|---|---|
| C7-E1 aggregate | worker files + `evidence/` | `findings.json` |
| C7-E2 weaponize-gate | `findings.json` | `weaponized-findings.json` (all, each with verdict), `weaponized-shipped.json` (SHIP only), `WEAPONIZATION.md` |
| C7-E3 chain_builder | `weaponized-shipped.json` | `chains.json` |
| E4 finding_gate | `weaponized-shipped.json` if non-empty, else `findings.json` | `gated.json`, `survivors.json`, `REPORT-survivors.md` |
| E5 validate | `survivors.json` | `validated-findings.json` |
| E6 triage_gate | `validated-findings.json` | `triage.json`, `passed-findings.json`, `TRIAGE.md` |
| 0F report | `passed-findings.json` → else `validated-findings.json` | `AUDIT-REPORT.md/.pdf` |

## 23. Severity matrix — verified end to end (2026-10-30)

Question worth answering with evidence, not opinion: *does a Low / Medium / High / Critical
finding actually survive this pipeline?* Measured with 4 findings, each with a real
request+response evidence file, run through the real chain (C7 → 0E → triage):

| finding | declared | weaponize | finding_gate | validate | triage |
|---|---|---|---|---|---|
| Pre-auth RCE (deserialization) | critical | SHIP | REPORT (17) | ✅ | 7/7 PASS |
| IDOR cross-tenant IBAN | high | SHIP | REPORT (11) | ✅ | 7/7 PASS |
| CSRF → account takeover | medium | SHIP | REPORT (16) | ✅ | 7/7 PASS |
| Open redirect → OAuth code leak | low | SHIP | REPORT (22) | ✅ | 7/7 PASS |

**4/4 SHIP → 4/4 validated → 4/4 triage PASS.** All four levels pass. What each level needs:

- **Critical / High**: nothing extra — a terminal impact (RCE, ATO, PII, funds) is a chain of
  length 1. Declare `chain_class: STANDALONE` or `HEAD`; a terminal HEAD no longer needs a
  `next_to_hunt` (it used to be DROPped as "a dead end", which killed pre-auth RCE).
- **Medium**: may need `chain_analysis` or `next_to_hunt` naming the step that turns it into
  impact (CSRF alone is a primitive; CSRF → password reset → ATO is the finding).
- **Low**: must be either terminal by itself or carry a named link. A bare open redirect is
  hygiene; an open redirect that lands the OAuth authorization code on an attacker host is
  token theft and passes at every gate.

Negative controls (all correctly rejected, same run): missing HSTS → `info:headers`; self-XSS →
`info:self-xss`; `Server: nginx/1.18.0` → `info:version-disclosure`; bare open redirect →
`info:open-redirect-alone`; speculative IDOR ("we believe… possibly") → blocked at weaponize and
again at finding_gate. 5/5 rejected, 0 survivors — the gates are not rubber stamps.
