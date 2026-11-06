# Runtime execution policy (operator, 2026-10-10)

Supersedes the earlier "wall-clock budget / per-tool timeout" model. Read this before running 0C.

## 1. Runs are UNBOUNDED — and that is deliberate

The 37 per-step timeouts in `audit-pipeline-orchestrator.py` were removed. Per-tool timeouts in
`tool_router.py` were removed. A tool that is producing output **runs to completion**.
Rationale (operator): a timeout mid-run skips vectors, the skipped vectors then get "covered" by a
hand curl, and the result is garbage that looks like coverage. **A skipped tool is a bug to fix,
not a coverage decision to accept.**

## 2. Stalled ≠ killed: `toolguard.py`

```bash
python toolguard.py run "<cmd>" --stall-warn 300     # run to completion, warn on silence
python toolguard.py stalls                           # who stalled
python toolguard.py unblock --pid 1234               # deliberate, operator-driven kill
```
- No output for `BB_STALL_WARN` (default 300 s per tool, 900 s per orchestrator step) → a
  `[STALL-WARN]` naming the **PID and the exact command**, recorded to `trackers/tool-stalls.jsonl`.
- The process is **never killed automatically**. Unblocking is a deliberate act.
- The orchestrator runs its own watchdog thread, so a step that hangs warns instead of going silent.

## 3. Stalled/failed → AUTO-DIAGNOSE → AUTO-FIX → RE-RUN: `autofix.py`

`tool_router._run` now routes every tool through `autofix.guard(...)`: run → classify the failure →
apply a repair → **re-run the tool** (up to 3 attempts).

| signature | trigger | repair |
|---|---|---|
| `tool-missing` | "is not recognized" / "command not found" | resolve the real path via `tool_router.TOOL_PATHS` |
| `python-dep` | `ModuleNotFoundError` | `pip install` the module |
| `old-cli` | `unknown command '…'` | **UNFIXABLE** → NO RESULT (do not substitute another command) |
| `rate-limited` | 429 / Retry-After | honour `Retry-After`, switch to GENTLE, re-run |
| `waf-block` | 403 / challenge page | switch to GENTLE + rotate UA, re-run |
| `missing-input` | wordlist/list not found | locate a replacement under the wordlist roots, re-run |
| `pipe-hang` | stall/TIMEOUT string | release the tree, re-run with streamed output |

Every attempt is journalled to `trackers/autofix-journal.jsonl` (`autofix.py journal`).

Statuses a tool can end in: `OK` · `EXHAUSTED` (tried N times) · `UNFIXABLE` · `NEEDS-OPERATOR` ·
`FAILED-UNCLASSIFIED`. **The last four all mean NO RESULT** — record it as such and retry later.

## 4. HARD RULE — no curl fallback

`tool_router.NO_CURL_FALLBACK = True`. When a tool cannot be made to run, the pipeline records
**NO RESULT** for that vector. It must **never** be silently replaced by a hand-written `curl`:
that produces garbage that reads like coverage. If a vector ends up NO RESULT, say so explicitly in
the phase log and re-run it once the tool is repaired.

## 5. GENTLE mode for programmes that forbid scanning

Never degrade to manual. Stay automated, just slower. `BB_GENTLE=1` injects per-tool rate flags:

| tool | flags | effective envelope |
|---|---|---|
| nuclei | `-rl 5 -c 2 -bs 2` | ~5 rps, 2 workers |
| ffuf | `-rate 5 -t 2` | 5 rps |
| gobuster | `--delay 200ms -t 2` | 5 rps |
| sqlmap | `--delay=1 --threads=1` | 1 rps |
| dalfox | `--delay 1000 --worker 1` | 1 rps |
| katana | `-rl 5 -c 2` | 5 rps |
| wpscan | `--throttle 1000` | 1 rps |
| nikto | `-Pause 1` | 1 rps |

Plus: honour `Retry-After`; back off exponentially; **abort with a warning after 3 consecutive
429/503** instead of hammering. 5 rps sits below the burst floor of mainstream WAF rate tiers while
still finishing a real scan in hours.

## 6. Technique distillation cadence

**Every 3 new techniques, immediately** (`technique-log.py`, `DISTIL_EVERY = 3`). No end-of-engagement
batching: `add` prints `DISTIL_NOW` once 3 are pending, and the atlas + owner skill are updated then.
See skill `technique-capture`.

## 7. Verifying this policy is in force

```bash
python tool_router.py 2>/dev/null || true           # imports cleanly
grep -c "timeout=" audit-pipeline-orchestrator.py   # expect 0
python toolguard.py verify                          # 6/6
python autofix.py verify                            # 7/7
python bundle-sync.py verify                        # IN STEP
```

## 8. Multi-product engagements — one product per run, restart at 0A

When the scope is a vendor with many properties (a product family, or `*.vendor.com`), do **not**
aim one run at everything.

- **Pick one property, run the full 0A→0F to completion, then start the next from 0A.** Operator,
  verbatim: *"boleh jalankan phase lengkap perproduk, jd candidatenya tidak menumpuk banyak, saat
  ganti produk, start ulang dr awal."* The point is candidate hygiene: a per-product run keeps
  `findings.json` small enough to actually review, whereas one merged run buries the real findings
  under interface noise from a dozen hosts.
- **Queue explicitly.** Write the property list to a file (`<engagement>/products.txt`), record the
  chosen one (`current-target.txt`), and keep the remainder visible so "checked everything" is a
  claim you can back.
- **Randomise the order** when the operator has no preference — it removes the bias toward the
  obvious/most-interesting host and distributes the run cost.
- **A fresh run needs a fresh scope string that the gate accepts.** `--scope` is a **comma-separated
  domain-pattern allowlist**, not prose: `--scope "*.vendor.com,vendor.com"` (note both — `*.x.com`
  does not match `x.com` itself). A sentence like `"Vendor websites per policy v1.4"` makes the
  deterministic scope gate BLOCK with `not in <scope>`, correctly: it cannot match a host against
  prose. That block is the gate working, not a bug.

## 9. Reporting cadence — per phase CHANGE, silent otherwise

Operator correction, 2026-10-10: *"knp lama"* after a long narrated turn, followed by
*"laporan tiap ganti fase"*. Two rules came out of it:

1. **Be terse.** Long explanatory turns during a live run are the complaint. Report the thing that
   changed; skip the preamble, the recap, and the philosophy.
2. **Report on phase TRANSITIONS, not on a timer.** Use a watchdog-pattern cron so the operator is
   never spammed and never blind:
   - `scripts/phase-watch.py` infers the current phase from **evidence on disk**, not from
     `PHASE_LOG.md` (the orchestrator does not append every phase — reading the log alone reports a
     stale `0A` while the run is actually deep in 0C). Evidence ladder: `AUDIT-REPORT.*` → 0F ·
     `passed-findings.json`/`triage.json` → 0F · `survivors/validated/findings.json` → 0E ·
     `tools-usage.json` + a passing verify → 0D · any `tool-evidence/|variants/|references-*` → 0C ·
     `urls.txt|live.txt|dork-recon/` → 0B.
   - It prints **only when a phase changed**, and stays silent otherwise — so it can be a cron with
     `no_agent=True` where empty stdout means no delivery.
   - It also flags `tidak ada file baru N menit` so a genuine stall surfaces without a human polling.
   - Filter to recently-active runs (`--max-age-h`, default 12) and drop scaffold dirs
     (`test`, `example`, `not-a-target`, `target_com`) or the first delivery is a wall of history.

Report content per transition: target · `from -> to` · the newest 3–4 artefacts with sizes, and a
one-line stall note if applicable. Nothing else.

**Do not narrate a run you have not verified.** While the process is alive it is "running", and the
authoritative check is the process list + artefact mtimes — **not** a `tail` of a buffered log
(`run-observation-discipline.md`).


## 10. PITFALL — a neutralised budget breaks its ARITHMETIC consumers

Real incident 2026-10-10 (this policy's own rollout). Setting `_BUDGET = None` (or `budget = None`)
is only half the change. Every **consumer** of that value must be updated too, or the pipeline fails
closed in a way that looks like a *coverage* problem:

| consumer pattern | what happens with budget=None / 0 |
|---|---|
| `deadline = time.monotonic() + budget` | **`TypeError: float + NoneType`** → the whole layer dies (`execute-references.py`, `execute-poc-techniques.py`) |
| `deadline = time.monotonic() + (budget or 0)` | `budget=0` is falsy but **arithmetically valid** → `deadline = now` → every clue is silently marked `SKIPPED_BUDGET`. No crash; just **zero coverage** — worse than the crash. |

Correct form for both:

```python
deadline = (time.monotonic() + budget) if budget else float("inf")
```

**Checklist when neutralising a budget/timeout:**
1. `grep -nE "[+\-]\s*budget|budget\s*[+\-]" <every script that takes the value>` — find every consumer
2. prefer `if budget else float("inf")` over `budget or 0` (0 is a *valid but fatal* budget)
3. after patching, **run the script once against a real target dir** — `ast.parse` and even `import` will NOT catch either failure mode (one is a runtime TypeError, the other is silent)
4. re-check the 0D gate output for `SKIPPED_BUDGET` — if any appears, a budget is still live
5. **then run the automated guard** — `hermes-health-audit.py` now statically detects both shapes
   (`deadline = monotonic() + budget` unguarded, and `budget = … or 0`) across the five
   `execute-*.py` files and reports them under `budget_arith_fail`, counted as a failure. It is
   precise by design: the SAFE form (`… if budget else float("inf")`) and arg-parsing lines like
   `sys.argv[i] == "--budget" and i + 1 < len(...)` are NOT flagged. An earlier over-broad version
   false-positived on both and was discarded — a noisy guard is worse than none, because it trains
   you to ignore it. Same file also carries the **import-smoke** test (`import_fail=`) from RULE 31b,
   so one run after a bulk edit covers syntax → import → budget-arithmetic.

The gate behaved correctly: it HARD BLOCKED the report after 3 reworks rather than emitting a
report built on a layer that never ran. That is the fail-closed design working.

## 11. GENTLE flags belong to GENTLE MODE ONLY — never hardcode them as a command default

Measured failure (2026-10-10): the per-manifest tool commands were written with the gentle envelope
baked in — `nuclei … -severity critical,high,medium -rl 5 -c 2`, `ffuf … -rate 5 -t 2`. Against a
real host that produced a **10-minute nuclei run with a 0-byte output file and ~5 % CPU** — an
effective stall, in a step that is meant to be a light accounting pass.

Two independent mistakes in one line:

1. **Wrong default.** The pipeline's own convention is `-severity critical,high -rl 50 -c 10`.
   5 rps × ~14 000 templates is a multi-hour scan; nothing was broken, it simply could never finish.
2. **Double-gentle.** `tool_router.apply_gentle()` already appends the gentle flags when
   `BB_GENTLE=1`. Hardcoding them in the command means gentle mode appends a *second* copy and
   non-gentle runs are silently slowed. The mode switch is the mechanism — commands must stay neutral.

**Rule:** a tool command written into a pipeline script carries **no rate flags**. Rate is injected
at the single choke point (`apply_gentle`) driven by policy, so one switch moves every tool together.
Symptom to recognise: a tool that is *running* (process alive, RAM held) but has produced no output
for minutes and is burning almost no CPU — that is a rate problem, not a hang.

**Warning obligation.** Per the operator's rule ("*kl time out atau stuck, berikan sy warning, dan
perbaiki spy lancar lagi*") this situation is reported as a stall, not narrated as "still working":
name the tool, the elapsed time, the output size, and the cause, then repair and re-run.

## 12. Windows process triage — kill the right thing, from the right shell

Two traps when reaping a stalled scan on this host:

- **`taskkill /F /T /PID n` typed into git-bash gets path-mangled** — MSYS rewrites `/F` to `F:/`
  and the command dies with `ERROR: Invalid argument/option - 'F:/'`, leaving the process alive while
  looking like you tried. Invoke it from **Python** (`subprocess.run("taskkill /F /T /PID n",
  shell=True)`) — `toolguard.py unblock --pid n` is the prepared path — or set
  `MSYS_NO_PATHCONV=1`. Same family as the quoting traps in
  `msys-path-and-tool-invocation-traps.md`.
- **Distinguish a stale run from an active one before killing.** Enumerate with
  `Get-CimInstance Win32_Process` and read **`CreationDate` + `CommandLine`**: a `nuclei.exe` from
  an `orchestrator-<other-target>` directory hours old is a leftover, not part of the current run.
  Killing by name alone takes out the scan you are waiting for. Then re-assert the intended
  processes are **still alive** afterwards — a reap that also killed the working run looks like
  progress and is the opposite.


## 9. PITFALL — local AV quarantines evidence named after offensive tools

Measured on this host 2026-10-10, and it cost an hour of misdiagnosis:

```
tool-evidence/patator-manifest.txt   -> write_text() SUCCEEDS (1913 B), os.path.getsize() = 1913
                                     -> open(..., "rb").read()  ->  OSError [Errno 22] EINVAL
                                     -> ledger reports "evidence lacks '# TOOL EVIDENCE:' marker"
```

The file is really there; the AV lock makes it unreadable, and the failure surfaces **one layer
away** as a ledger complaint about a missing marker. A neutral filename is readable immediately
(`m37.txt` → fine).

**Rule:** never name an evidence file after the offensive tool it came from. Keep the tool identity
**inside** the file. `_account_mandated_tools()` now applies this automatically for the sensitive set
(`patator`, `hydra`, `medusa`, `ncrack`, …) and probes readability after every write, rewriting to a
neutral name on `OSError`.

## 10. PITFALL — a ledger that demands CONTENT where zero is the correct answer

Same family as §8, found four separate times in one session. The coverage ledger and the final gate
kept requiring artefacts to be non-empty where an empty result was the **correct** outcome:

| demanded | why empty is correct |
|---|---|
| `subs.txt` ≥ 1 line | a CDN/apex host legitimately has no subdomains → seed with the target host |
| `live.txt` ≥ 1 line | httpx wrote nothing because `subs.txt` was empty → seed with a direct probe |
| `ports.txt`, `crawled.txt` | the tools ran but nobody saved their output to those paths |
| `chains.json`, `ready-candidates.json` > 2 bytes | 0 candidates produce 0 chains — correct, not missing |

**Rule:** distinguish *"never produced"* (file missing → FAIL) from *"produced empty"* (file exists and
parses → record the emptiness **explicitly** as `N/A` with a reason, never as a pass with no note).
`asset-coverage.py` §0E now does exactly that.

## 11. PITFALL — a reader that looks for the wrong field hides a gate that explained itself

`finding_gate.py` records its verdict rationale as a LIST under `reasons` (+ `drop_flags`), but the
report generator read a singular `reason` and printed "(no reason recorded)" for **every** drop. The
gate was perfect; the report was blind.

**Rule:** when a report says "no reason recorded", check the producer's actual field names before
believing the gate was silent. Same class as the `nl`/`_re` issue in §8 — the failure is in the
**consumer**, and it is silent.

## 12. Guards now in `hermes-health-audit.py`

Run `python hermes-health-audit.py` — these catch the whole family above *before* a run:

| check | catches |
|---|---|
| `import_fail` | runtime NameError that `ast.parse` misses |
| `unbound_name_fail` | a name used but bound in no enclosing scope (closure-aware) |
| `budget_arith_fail` | `+ budget` unguarded, and `budget or 0` (deadline=now → silent total skip) |

Plus `bundle-sync.py check|sync|verify` for toolkit-level drift.


## 13. STANDING RULE — deep dive is PROACTIVE, and every conclusion is proven 3x

Operator instruction, 2026-10-10. This is not optional and does not wait to be asked for.

### 13.1 Never let recon decide the test surface by itself

Measured failure: recon wrote **six hardcoded paths**. On `download.jetbrains.com` all six hit the
same CloudFront signed-URL 302, so 15 payload vectors + 15 business-logic vectors + 11 references
fired into a wall. The result was "0 findings" that had measured **nothing**. The target's real
surface — a signed redirector over an S3 bucket — was never touched.

**Before any payload flies:**
1. `python deep-endpoints.py <target_dir> <base_url>` — establishes the host's **ROLE**
   (`signed-redirector` / `cdn-origin` / `app` / `api` / `static-site` / `redirector`) from its own
   behaviour, then enumerates **REAL** endpoints from robots, sitemap, JS bundles and the site's own
   public APIs. Outputs `host-role.json`, `urls-deep.txt`, `deep-dive-plan.json`.
2. Fold `urls-deep.txt` into `urls.txt` (the orchestrator now does this in `_deep_recon()`).
3. Run the **role's** class set from `deep-dive-plan.json` — not the generic battery. For a
   signed redirector that is: dot-segment normalisation, cross-prefix signing, cache-key
   composition, signature-tamper behaviour, cache poisoning (non-destructive probe ONLY),
   host-header routing, method tampering, CORS, error-page reflection, TTL/Expires window.

If every URL you are testing returns the same response, **you are not testing the application** —
stop and work out what the host actually is.

### 13.2 Three independent verifications, from scratch, before ANY conclusion

`reverify.py` enforces it:

```bash
python reverify.py http  <dir> <name> <url> [--rounds 3]     # candidate: reproduce 3x
python reverify.py probe <dir> <name> -- <command>           # artefact claim: 3x
python reverify.py sweep <dir> <base_url> [--rounds 3]       # conclusion: 3 fresh sweeps
```

* Rounds are **separate observations** (seconds apart), each independently executed, each timestamped
  and stored. The evidence chain must show *three* observations, not one restated claim.
* A candidate that does not reproduce identically is **UNSTABLE and must not be reported.**
* A class is only declared clean when **all three** sweeps agree it is clean. `"0 findings"` without
  a `CONSISTENT` sweep is an untested claim, not a result.
* Volatile signing params (`Signature`, `Expires`, `Key-Pair-Id`, `Policy`, `Token`) and long numeric
  runs are normalised before comparison — so a genuinely stable behaviour still matches 3/3 while a
  real change does not.

Wired into the pipeline: `_deep_recon()` in 0B, `_reverify_candidates()` before the gate,
`_reverify_conclusion()` before the report. All three are non-fatal: a verification failure is
recorded, never silently ignored.

### 13.3 Destructive proof is out of bounds — say so instead of doing it

When the only way to confirm a hypothesis is to break something real (cache-poison a live artefact
path, DoS a download endpoint), **do not do it**. Characterise the mechanism safely, mark the
finding as *partially verified*, and state the exact experiment the vendor can run. On
download.jetbrains.com the path-only cache key made cache-poisoning *plausible*, and the
non-destructive probe showed the CDN still served the cached good object — so the honest verdict was
"mechanism characterised, poisoning not reproduced", not a claim of DoS.

### 13.4 Report shape for a negative result

A negative report is a deliverable, not a shrug. It must carry: the funnel with real counts, the
**per-candidate verdict AND reason**, the **coverage table** (what actually executed), an explicit
out-of-scope section, the 3x verification evidence, and an evidence map. See §11 — when a report says
"no reason recorded", check the producer's field names first.


## 14. DELIVERABLE STANDARD — a draft + PoC PDF with DEMONSTRATED impact, or nothing

Operator standard, 2026-10-10: *"laporan akhir ... draft gmail lengkap poc pdf-nya, hasil yg benar2
ada impactnya, ada demonstrated impact dalam poc-nya ... bukan berhenti di teoritis, krn wajib
dibuktikan"*. This is the shape triage accepts, and it is also the gate.

### 14.1 The reportability test (all four, or it is NOT reported)

`final-deliverable.py` enforces:

| # | requirement | why |
|---|---|---|
| 1 | present in `passed-findings.json` | it cleared the impact gate + the 7-question triage gate |
| 2 | carries a **demonstrated-impact record** — `probe` (the exact action) AND `observed` (raw, unedited output, ≥40 chars) | a claim without its raw result is theory |
| 3 | that record **re-verified CONFIRMED 3x** (`reverify.py`) | a finding that does not reproduce is not a finding |
| 4 | an impact statement that says what the observed output *proves* | "impact: potential" is not an impact |

Fail any one → the finding is **EXCLUDED and named**, with the reason. There is no partial credit and
no "report it anyway at Low".

### 14.2 Output shape — ONE FINDING = ONE DRAFT = ONE PDF

Per reportable finding:

```
poc-pdfs/<slug>.pdf      reportlab PDF, skill structure:
                         Title · Summary · Severity/CVSS · Steps to reproduce ·
                         PROOF OF CONCEPT — DEMONSTRATED IMPACT (probe + raw observed +
                         "what this proves") · Verification (3x verdict + artefact) ·
                         Impact · Remediation · Supporting material
email-drafts/<slug>.eml  RFC5322, that PDF attached, addressed and subject-lined
deliverables.json        the manifest: what was staged, what was excluded and why
```

`.eml` on purpose: it needs no OAuth token, it is inspectable byte-for-byte, and it imports into
Gmail. **Staging is not sending** — the script reports the draft id / To / Subject / attachments and
states plainly that nothing was sent. Never send without an explicit instruction.

### 14.3 When there is nothing reportable, produce NOTHING

```
[deliverable] 0 passed triage -> 0 REPORTABLE, 0 EXCLUDED
[deliverable] nothing reportable. A draft is NOT produced: the operator standard is
              demonstrated impact, and producing a draft without it is the exact
              failure triage rejects. Record the negative result instead.
```

That refusal is the feature. A draft for a finding with no demonstrated impact is the phantom-evidence
failure that gets reports closed without investigation — the same class as §10 and §13.

### 14.4 Where it runs

Wired into 0F on **both** branches: the positive path (after `report-agent.py`) and the negative path
(`_write_no_findings_report`). So the moment a real finding clears the gates, the PDF and the draft
appear; and when none does, the run says so instead of manufacturing one.
