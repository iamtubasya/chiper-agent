# Pipeline Triaging — Interpreting audit-pipeline-orchestrator Output (2026-09-26)

Session-derived lessons (quarterwise.co.uk audit). Real bugs lost in pipeline noise are the
classic failure here. These rules make pipeline output trustworthy.

## 1. Orchestrator target MUST be a full URL

`audit-pipeline-orchestrator.py <TARGET>` with a bare domain (e.g. `quarterwise.co.uk`) causes
force-full-execution to skip every tool:

```
sqlmap: skipped — target is not a URL
dalfox: skipped — target is not a URL
ffuf:   skipped — target is not a URL
```

Then STEP 7 validation fails "4/5 checks passed" (Tools with output ❌). Fix: pass
`https://quarterwise.co.uk` (full URL), not the domain. Scope flag still uses the bare domain
(`--scope "quarterwise.co.uk"`).

## 2. force-full-execution HARD BLOCK: wordlist size gate

force-full-execution.py STEP 1 rejects any MANDATORY_HACKSKILLS file `< 500 bytes`:

```
Error: MISSING 1 hackskills:
  - common-passwords.txt: too small (404 bytes)
```

This blocks the WHOLE pipeline before any tool runs. The repo ships a deliberately tiny
wordlist (17 entries, 404 bytes) — must be replaced with a real list. **Fix BOTH locations**
or a sync/restore step overwrites the first:

- `~/.chiper/skills/bounty-pack/exploit-cookbook/references/common-passwords.txt`
- `~/.chiper/skills/bounty-pack/bundle-src/audit-pipeline-bundle-v1/skills/exploit-cookbook/references/common-passwords.txt`

Source: SecLists 10k-most-common (~73KB):
`curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt`

## 3. review-candidates "READY" + validated-findings are NOT findings

Phase 0E-REVIEW can emit 13 "READY (lolos 3x cek)" from 1048 candidates, and
validated-findings.json claims 3 "High" — **almost all are knowledge-base noise**, not target
results:

- `[references-index.json] 331 notable response(s) — High`: the "PoC" text is literally
  `curl -X POST "https://target.com/admin"` — content extracted from skill/reference
  markdown, counted as if it were a target response. Always grep the PoC/evidence for the
  placeholder `target.com`; if present → noise.
- `[variants\auth bypass] signup?plan=eyJhbG...`: query param echoed into Next.js RSC payload
  (`__PAGE__?{plan:...}`) — client-side searchParams echo, NOT server-side processing.
  Verify by diffing normalized bodies: after stripping query echo + build nonces, bodies are
  identical → no functional change.
- `[poc-variants\CVE-*]` (e.g. nextjs CVE-2025-29927): PoC repos matched by tech run against
  the target but return generic 404/200 landing pages. Verify the actual bypass manually —
  CVE-2025-29927: send `x-middleware-subrequest: middleware` (+ variants) to a protected
  path; 401 stays 401 = patched.
- `[business-logic\07-cache-poisoning]` flags 400 responses (`../secret`,
  `favicon.ico/../../admin`) as "interesting" — the 400 is the SERVER BLOCKING path
  traversal. A blocked probe is negative evidence, not a finding.
- `[variants\sqli/ssrf/ssti/xss/waf/graphql]` "notable" = generic Next.js 404 landing page
  containing words like "not found"/"error". No real target URL in the finding.

## 4. Triage recipe (make pipeline output trustworthy)

1. Collect hits where URL starts with the REAL target AND status is 200/201 (not 400/404).
2. Grep the "poc"/"evidence" text for `target.com` / placeholder hosts → drop as noise.
3. For param-based candidates (`?plan=`, `?role=`, JWT-ish): decode, diff normalized
   responses (baseline vs variant). Length-only differences tracing to the echoed query
   string in `__next_f` are NOT functional changes.
4. For CVE-matched PoC repos, run the canonical bypass probe manually against the real
   protected endpoint before believing the pipeline's Medium/High verdict.
5. `findings.json` from aggregate-findings is INPUT, not output — the gate/report that
   follows auto-tags things "High" from file names alone ("graphql.txt", "auth bypass.txt").

## 6. A "fresh" run is NOT fresh unless you clear the TRACKER, not just the output dir

`audit-pipeline-orchestrator.py` keeps phase state in
`~/.chiper/skills/bounty-pack/trackers/audit-pipeline-<url-encoded-target>.json` (+ siblings
`force-state-<target>.json` and `<target>.json`). Deleting/renaming only the poc-plans output dir leaves
the tracker claiming `completed_phases: ["0A","0B"]`, so the next launch prints
`RESUME MODE: already completed ['0A','0B'] — skip those` and **skips recon entirely** — you then test a
stale surface. To restart from scratch: `mv` all three tracker files aside (`*.bak_<date>`), keep the
poc-plans dir archived too, and confirm the log shows `PHASE 0A: SETUP` rather than `RESUME MODE`.

Also: the scope gate refuses to run at all without `--scope` ("Pipeline ditolak sebelum menembak request
apa pun", exit 1) — always pass `--scope "<domain>,*.<domain>"` with a FULL-URL target.

## 7. force-full-execution can blow the 3600s subprocess timeout (observed 2026-10-01)

The orchestrator runs C1 as `subprocess.run(..., timeout=3600)`. On a pure server-action SPA it can spend
the whole hour and then raise `subprocess.TimeoutExpired` → `PIPELINE EXCEPTION`, exit **1**, with state
saved as `completed=[0A,0B] current=0C` (resumable). Symptoms: the log stops at
`STEP 1: Running FORCE FULL EXECUTION...` and only the first one or two tools' evidence files appear in
`<output>/tool-evidence/` (e.g. `arjun-sqli.txt`, `sqlmap-sqli.txt`) before the hour is up.
Handling: treat C1 as best-effort; extract the evidence that did land, then do the remaining classes with
your own rate-limited commands, and let the report's coverage ledger say which tools ran and which did not.

Also in the recon step: `httpx: 0 live hosts (rc=255)` means the httpx invocation failed (bad flags), not
that the host is down — supply your own live-host list (or a URL list) rather than trusting that zero.

## 5. Tool invocation bugs inside force-full-execution (log, don't trust "EXECUTED")

These tools are recorded "EXECUTED" with evidence files but never actually scanned — verify
the evidence file content; re-run manually when the vector matters:

- dalfox: invoked as `dalfox <url>` but CLI needs `dalfox url <url>` → "unknown command".
- CORScanner: invoked with `--headless` which the CLI doesn't accept → usage error.
- ffuf: same `--headless` misuse.
- graphqlmap: crashes on Python 3.14 `pyreadline` import at startup.
- SSRFmap: invoked without required `-r REQFILE -p PARAM`.

Expect a gap in C1 (dedicated tools) on targets that are pure server-action SPAs — the
business-logic/variants/PoC sub-phases still fire, but the "tools with output" gate check
needs manual top-up for the tools whose invocation is broken.

## 6. The phase model is 0A→0F (NOT 0A→0D) — authoritative, from audit-pipeline-orchestrator.py

```
0A SETUP → 0A-SCOPE (hard gate) → 0B RECON (subfinder+httpx → urls.txt)
→ 0C EXPLOIT: C1 dedicated tools | C2 payload variants | C3 business-logic | C4 matched PoC repos
              | C5 PoC variants | C6 references | C6b poc-techniques
→ 0D GATE    (verify-tool-usage, HARD BLOCK, auto-rework ×3)
→ 0E FINDINGS   : finding_gate -> validate-findings -> triage_gate   (aggregate/weaponize/chain_builder = 0C-C7)
→ 0E-REVIEW  (per candidate, 3× check, low→high; only survivors enter the report)
→ 0F REPORT  (report-agent → AUDIT-REPORT.md/.html/.pdf)
```

A PHASE_LOG that stops at 0D (or calling the pipeline "0A→0D") is wrong — the user corrects it.

### Run it like this; these traps waste an entire run

- Target MUST be a full URL: `audit-pipeline-orchestrator.py https://host --tech "a,b" --scope "host,*.host"`.
  A bare domain makes every tool skip ("target is not a URL"); `--scope` is a hard gate that refuses to
  fire a single request without it.
- Output dir is derived from the target (`~/.chiper/skills/bounty-pack/poc-plans/orchestrator-<host>`);
  `audit-run-all.py --output-dir` is NOT forwarded.
- RESUME state lives in `~/.chiper/skills/bounty-pack/trackers/`: `audit-pipeline-<url-key>.json`,
  `force-state-<url-key>.json`, `<url-key>.json`. If they still list completed phases the run prints
  "RESUME MODE: already completed [...]" and SKIPS recon, so you test a stale surface. To start clean,
  ARCHIVE them (`mv X X.bak_<date>`) — never delete. Same for the poc-plans output dir.
- The pipeline can die mid-C1 (observed right after arjun+sqlmap) and never reach 0D/0E/0F. Normal:
  finish 0D/0E/0E-REVIEW/0F by hand and say so, don't pretend it completed.
- If the vendor policy forbids load-heavy scanning ("no automated scanning that puts noticeable load"),
  skip the full nuclei tag sweep; use targeted/rate-limited runs (`ffuf -rate 10`, sqlmap one URL
  `--threads=4`) and record the deliberate gap.