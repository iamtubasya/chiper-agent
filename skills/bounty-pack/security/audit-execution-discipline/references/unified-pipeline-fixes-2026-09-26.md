# Unified Pipeline hard-won fixes + Findings Quality Bar (2026-09-26)

## Infinite recursion (why "STEP 1" never finished)

`force-full-execution.py` had `run_full_pipeline()` which called `audit-run-all.py`
→ orchestrator → `force-full-execution.py` → ... forever. The process tree showed
nested python procs; STEP 1 kept "running" past any timeout.

FIX (do not re-introduce):
- `force-full-execution.py` is a LEAF — `run()` runs steps 1-5 + validate + save; it
  must NOT re-spawn the orchestrator. Remove `self.run_full_pipeline()`.
- `validate_before_report` "Pipeline execution" check → `pipeline_ok = True`
  (the outer orchestrator owns the pipeline; a leaf can't know about it).
- Verify: after fix, force-full-execution exits in ~60s (not forever).

## Orchestrator output dir sanitize (Windows)

`output_dir = Path.home() / "~/.chiper/skills/bounty-pack/poc-plans/orchestrator-{target...}"`
must strip scheme and replace `:/?=.` → `_`, else `os.mkdir` fails
(`NotADirectoryError: 'C:\...\orchestrator-https:__httpbin_org'`).

```python
safe = target.replace('https://','').replace('http://','').replace('/','_').replace(':','_').replace('.','_').replace('?','_').replace('=','_')
```

Same class of bug: `audit-exec-tracker init <url>` wrote `https:\httpbin.org.json`
(invalid on Windows) → rc=1. Sanitize with `re.sub(r"[^A-Za-z0-9._-]", "_", target)`.

## C4 track-poc: execute ALL matched, not just REQUIRED_TYPES

Old code executed only REQUIRED_TYPES (RCE/SQLi/Auth/SSRF/IDOR/...) → 1/51 repos
executed, 49 sat as PLANNED_NON_REQUIRED, C5 starved. FIX:
- `to_execute = (required_items + others)[:25]` — required first, then the rest, cap 25.
- Entry-point finder: explicit names (exploit.py/main.py/poc.py/attack.py/...),
  then `CVE-*.py / exploit*.py / poc*.py / check*.py / scan*.py` keywords, then
  single-root-.py fallback.

## C5 execute-poc-variants: payload-pattern was too narrow → 0/51

Old patterns only matched `payload.* / fuzz* / *wordlist* / *bypass*` → 0/51 repos.
FIX:
- Add `^cve[-_].*\.(py|php|js|sh|rb|go|c|nse|pl)$`
- Add `^(exploit|poc|main|run|attack|checker|scanner|detector)[_-]?\w*\.(...)$`
- Fallback: if no named pattern hits, use any code file from
  `PAYLOAD_CODE_EXTS = {.py,.php,.js,.sh,.rb,.go,.c,.nse,.pl,.java,.ps1,.bat}` (cap 5)
- Exclusion: requirements.txt, package.json, setup.py, pyproject.toml, go.mod,
  readme*, license*.

## aggregate-findings: root-only + wrong output path

Old aggregate globbed root dir only (skipped tool-evidence/variants/business-logic/
poc-evidence/poc-variants) and wrote findings.json to CWD. FIX:
- `worker_dir.rglob("*")` recursive; SKIP_NAMES for meta files (findings.json,
  PHASE_LOG.md, state.json, subs.txt, live.txt, urls.txt, recon-raw.txt, gated.json,
  REPORT-survivors.md, AUDIT-REPORT.md, chains.json, manifest.json).
- Default output = `<target_dir>/findings.json` when --output not absolute.
- Evidence `.txt` lines → meaningful findings: extract "notable" lines (status
  2xx/5xx + keyword), skip 404/403/401/405 unless "interesting". Schema-complete:
  title, severity, poc, evidence, impact, chain_analysis, source_file.
- Severity mapping from evidence keywords: ssn/balance/db_password/sk-live/
  role:"admin"/isadmin/stack-trace/admin@corp → High; <script/onerror=/redirect/
  url=http/169.254.169.254/api_key/debug/sensitive/quantity/price → Medium.

## chain_builder hang (permutation explosion)

`itertools.permutations(range(n=120), length ≤4)` ≈ 208M combos → hang. FIX:
- Filter items to signal-findings only (`goals or entries or caps`), cap 40,
  `--max-len 3`. Bounded & still thorough.

## validate-findings "No PoC provided" for everything

Aggregated findings used `evidence`/`text` (not `poc` field) → validator dropped all.
FIX: poc = finding.get("poc") or finding.get("evidence") or finding.get("text").
  PLUS auto-reject by-design + phishing/social BEFORE PoC check (user rule).

## The `.py` file association = VS Code trap (Windows)

If a pipeline runs `"C:\...\tool.py" -u URL` via `shell=True`, Windows OPENS VS CODE
in that file instead of executing it — exit code 0 (fake), tool never ran, and VS Code
keeps popping up. This is the #1 cause of "tool shows EXECUTED but 18 bytes evidence".
FIX: `tool_cmd_prefix = f'"{sys.executable}" '` for any tool whose resolved path ends
in `.py`, prefix all commands with it. Same in Interactsh handling: never Popen a `.bat`
alias, resolve to the real `.exe`.

User-visible symptom: "VS Code app opens by itself after I close it" → check pipeline
processed a `.py` tool. (VS Code updater logs in /tmp/vscode-inno-updater-*.log are
separate.)

## Findings Quality Bar (user mandate — enforced in finding_gate.py + validate-findings.py)

- DROP (unconditional): by-design/intended; phishing/social-engineering (patterns:
  phish, social eng, credential harvest, lure/bait, deceive/trick user, ui-redress,
  email-spoof, impersonate/masquerade, vishing/smishing); info-class only
  (headers/version/cookie-flags/CORS-alone/self-xss); dead-chain ("not reproducible,"
  "theoretical", "blocked by"); speculative ("could be," "may be," "potential," relying
  on "consider/recommendation"); CORS without data; open-redirect alone.
- DOWNGRADE: overclaim language ("total compromise," "all users affected," "guaranteed,"
  "0-click") without step-by-step proof; 4xx-as-success (404/403/401/405 presented as a
  vuln without exploitation proof); no evidence marker (curl/HTTP\d/status:NNN/poc/
  screenshot); impact_score == 0; info-phrasing alongside impact (tighten evidence).
- REPORT requires: evidence marker + real impact signal (authz/code-exec/SSRF/
  cross-tenant-read/PII/privilege-escalation/fund-loss/control-bypass/webhook-abuse).
- Low findings still allowed (user: "kalau low masih boleh") — but don't pad the
  report; present Medium+ unless user asks for all.

## Proven validation technique: known-vulnerable test app

When user asks "why no Medium+ findings — are tools/knowledge insufficient?", DO NOT
argue theory. Build a small intentionally-vulnerable express app (XSS reflected,
IDOR + ssn/balance, mass-assignment role=admin, SSRF endpoint, .env disclosure, open
redirect, LFI, business-logic qty/price), run the full pipeline, compare.
Real result (2026-09): vulnerable app → **13 validated High in ~10 min**; httpbin.org
(intentionally clean) → 0. Conclusion: tools+knowledge+payloads are sufficient; a
clean target yields 0 legit findings, and recon depth (link crawling) + aggregator
schema-completeness matter more than adding more tools.