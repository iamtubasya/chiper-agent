# Audit pipeline — the REAL phase model, and how to force a genuine fresh run

Source of truth: `~/.chiper/skills/bounty-pack/` (the LIVE toolkit that actually runs).
`bundle-src/audit-pipeline-bundle-v1/toolkit/scripts/` is a **synced copy** for shipping — keep it in
step with `python ~/.chiper/skills/bounty-pack/bundle-sync.py sync` and check it with `... check`.
(`audit-pipeline-orchestrator.py` = single brain; `audit-run-all.py` = thin wrapper).
Companion: `pipeline-triaging-2026-09-26.md` (how to triage its output — do not trust it blindly).

## 1. Phases are 0A → 0F (a PHASE_LOG that stops at 0D is stale)

```
0A SETUP      PHASE_LOG + audit-exec-tracker init
0A-SCOPE      HARD GATE — refuses to send ANY request without a scope
0B RECON      subfinder + httpx + URL probes → urls.txt
0C EXPLOIT    C1 dedicated tools (force-full-execution) | C2 payload variants
              C3 business-logic (15 vectors) | C4 matched PoC repos
              C5 PoC variants | C6 reference attacks | C6b poc-techniques
0D GATE       verify-tool-usage (11 checks, HARD BLOCK, auto-rework ×3)
0E FINDINGS   : finding_gate -> validate-findings -> triage_gate   (aggregate/weaponize/chain_builder = 0C-C7)
0E-REVIEW     review candidates one-by-one, 3× check, low→high — only survivors reach 0F
0F REPORT     report-agent → AUDIT-REPORT.md/.html/.pdf
```

Write your own PHASE_LOG with all nine rows; reporting "audit done at 0D" is wrong.

## 2. Invocation contract (two ways to fail before doing any work)

```bash
python toolkit/scripts/audit-pipeline-orchestrator.py https://target.example \
    --tech "nextjs,node" --scope "target.example,*.target.example"
```
- **Target arg MUST be a full URL.** A bare domain makes force-full-execution skip sqlmap/dalfox/ffuf
  ("target is not a URL").
- **`--scope` is mandatory.** Without it: `❌ SCOPE GATE: --scope WAJIB diisi` →
  `PIPELINE FAILED` → exit 1, with the reassuring detail that *no request was sent*. Nothing to clean
  up, but nothing was tested either.
- `audit-run-all.py --output-dir DIR` is ACCEPTED and then partially ignored: the orchestrator's
  `main()` only parses `--tech/--scope/--exclude` and computes its own output dir
  (`~/.chiper/skills/bounty-pack/poc-plans/orchestrator-<sanitized-target>/`). Look for artifacts there, not
  in the dir you passed.

## 3. Fresh run ≠ deleting anything: the resume state lives OUTSIDE poc-plans

Symptom of stale state (this is the tell):
```
RESUME MODE: already completed ['0A', '0B'] — skip those
```
…and recon never re-runs, so `urls.txt` is missing/old while the pipeline happily marches into 0C
against a stale surface. Archiving only `poc-plans/orchestrator-<target>/` does NOT fix it.

State files to archive (move to `*.bak_<YYYYMMDD>`, never delete):

```
~/.chiper/skills/bounty-pack/trackers/audit-pipeline-<sanitized-url>.json   # completed_phases / current
~/.chiper/skills/bounty-pack/trackers/force-state-<sanitized-url>.json      # force-full-execution progress
~/.chiper/skills/bounty-pack/trackers/https___<host>.json                   # tracker state
~/.chiper/skills/bounty-pack/trackers/_archive_<target>_*                   # older archives, leave alone
~/.chiper/skills/bounty-pack/poc-plans/orchestrator-<sanitized-target>/     # urls.txt + tool-evidence/
```
Then re-run: the log should show `PHASE 0A: SETUP … ✅ PHASE 0A COMPLETE` and a real
`STEP RECON: subfinder … httpx … urls.txt: N candidate URLs written`.

## 4. When it dies mid-C1 (common) — top up manually, don't restart blindly

- Evidence from a partial 0C lives in `<output-dir>/tool-evidence/<tool>-<vector>.txt` with
  `# TIMESTAMP` / `# EXIT CODE` headers → timestamps tell you exactly how far it got.
- The screenshot of "EXECUTED" is not proof of a real scan: read the evidence body (e.g. arjun on a
  marketing page "finds" JSON-LD `schema.org` keys — pure noise; a sqlmap run that stops after
  `[*] starting` proves nothing).
- Better: finish the round with RATE-LIMITED, targeted runs you control, and publish a
  **tool → result ledger** in the report that names tools you deliberately did NOT run and why
  (e.g. "full nuclei tag sweep skipped: target's policy forbids noticeable-load scanning").

## 5. Scope discipline belongs in your own PHASE_LOG

Before 0B, read the TARGET's own policy page (linked from `/.well-known/security.txt` →
`Policy:`), then copy into your PHASE_LOG: in-scope hosts, explicit out-of-scope list, load limits,
"own accounts only", and report channels. Real example: a vendor policy that put **every subdomain
other than the apex out of scope** and forbade "automated scanning that puts noticeable load" — which
immediately reclassified findings, capped scanner rates (ffuf `-rate 10–15`, single-URL sqlmap), and
made origin-IP/subdomain observations internal notes rather than reportable findings.
