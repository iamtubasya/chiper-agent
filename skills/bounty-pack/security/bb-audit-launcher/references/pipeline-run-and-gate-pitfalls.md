# Pipeline run & gate pitfalls (0A→0F orchestrator)

Measured 2026-10-12 on spectrocoin.com — the first full 0A→0F run through this pipeline
(219 artifacts, 33/33 checkpoint, honest NEGATIVE). Everything below cost real time.

## 1. The 0D gate loops on a STALE `asset-coverage.json` after a rework  (was a real bug — patched)

**Symptom.** `STEP 1.5: GATE check (attempt N/3)` → `❌ asset-coverage FAIL for phase(s): ['0C']
— some asset was READ not USED / skipped-timeout` with the **identical** message on attempt 1, 2 and
3, then `HARD BLOCK` → RuntimeError → no 0E/0F, no report.

**Why it is a lie.** The rework really did run the 15 "missing" tools — `wpscan, nikto, subzy,
trufflehog, gitleaks, kiterunner, grpcurl, …` were all present in `tools-usage.json` with evidence
files on disk. CHECK 12 reads `asset-coverage.json`, which is *derived from* `tools-usage.json`;
`verify_tool_usage()` → `run_step5_tools()` re-ran force-execution but **never re-derived**, so the
gate re-read the same stale ledger every attempt.

**Fix applied (additive, in `run_step5_tools`).** After a successful rework, run
`asset-coverage.py <out_dir> --derive`. Backup: `audit-pipeline-orchestrator.py.bak_gate_rederive_*`.

**Unblocking a run already in flight** (a source edit does NOT reload into the running process):
keep the ledger fresh from a second shell — this is what turned attempt 3 into PASS:

```bash
while :; do python "<skill>/asset-coverage.py" "<out_dir>" --derive; sleep 4; done
```

Then confirm: `asset-coverage.py <out_dir> --phase 0C` → all `OK`.

**Diagnosis recipe** (do this before believing a `not USED` verdict):
`python -c "import json;d=json.load(open('tools-usage.json'));print(sorted({(e.get('tool') or '') for e in d}))"`
— if the tool IS listed with `EXECUTED`/`RAN_WITH_ERROR`/`NOT_FOUND`, the ledger is stale, not the run.

## 2. The gates read the TARGET DIR — bridge with a FULL copy, never a partial one

The orchestrator **writes** to `~/AppData/Local/hermes/poc-plans/orchestrator-<host>_<...>/`;
`audit-checkpoint.py` and `deep-audit-mode.py guard` **read** the target dir
(`D:/data hermes/bug-bounty/<target>/`). A partial bridge (`cp *.json *.txt`) sails through the
orchestrator's own `TOTAL: 33/33` but makes `deep-audit-mode guard` FAIL with *misleading* reasons —
`0B subs.txt/live.txt NOT_RUN`, `0C poc-variants(C5) NOT_RUN`, `skills claimed applied w/o evidence` —
because `derive()` can only see files that are physically present.

Copy **every** artefact dir, then re-derive and re-verify:

```
business-logic/  dom-xss-evidence/  dork-recon/  impact-verification/  recon-evidence/
tool-evidence/   variants/         references-evidence/  poc-evidence/
poc-techniques-evidence/  poc-variants/  rce-verification/  sqlmap-out/  skill-evidence/
plus  *.json  *.txt  *.md
```

```bash
python "<skill>/asset-coverage.py"   "<dir>" --derive      # rebuild the ledger
python scripts/verify-tool-usage.py  "<dir>"               # want "ALL 13 CHECKS PASSED"
python scripts/deep-audit-mode.py guard "<dir>"            # want "DEEP-AUDIT GATE: pipeline evidence OK"
```

Diff the two trees (`find . -type f | sort` + `comm -23`) until the only delta is your own scratch
files — that delta IS the reason the guard fails.

## 3. `dom-xss-test.py` hits are FALSE POSITIVES by construction

The detector sets `window.__DOMXSS=1` from a `MutationObserver` that fires on **any** added
`IMG`/`SCRIPT`/`SVG` node. The Cloudflare "Just a moment…" challenge page and every React render
trip it, so on any JS-driven site it emits a pile of "findings" (148 here; 47 with real page titles).
Its ledger is still valid as a *coverage* record (asset-coverage maps the stage `USED`) — but never
report its hits without independent proof of execution. `impact-verify` correctly zeroed them; keep
it that way, and say so in the report rather than shipping them.

## 4. `[STALL-WARN] no step progress for Ns` is usually a FALSE ALARM

Orchestrator stdout is piped to `tee` → **block-buffered**, so the log can sit unchanged for 15+ min
while tools are actively working. Before killing anything:

- check `tool-evidence/` + `variants/` **mtimes** (`find … -newermt "-5 minutes"`);
- check the process list (`ps -W`, `tasklist`) and CPU — a live `nuclei/sqlmap/arjun` means "working".

Kill only a *stale orphan* (a tool whose hash/start-time predates the current step AND whose evidence
file is not growing), never the orchestrator. On a 4-vCPU/6 GB box a full 500-URL force-execution run
pushes load to ~80; the first `tasklist` can hang — that is load, not a crash.

## 5. Cloudflare 1015 during scanning

Rapid probes / scanners trip CF's rate-limit (`error code: 1015`, HTTP 429) on the **main** host while
sibling subdomains stay 200. Throttle manual probes; remember the pipeline's own scans draw on the
same budget, so a 429-saturated scan is a **coverage gap**, not "clean". Record it as
`Residual coverage (honest gaps)`.

## 6. Next.js / SPA exchange — one-pass surface recon (spectrocoin.com pattern)

Cheap, high-yield, and it front-loads the real attack surface before any scanner fires:

- **`/gen-cfg.js`** → `window.<App>FeConfig` = `BASE_URL`, `AUTH_DOMAIN`, `EXCHANGE_PUBLIC_API_URL`,
  `RECAPTCHA_SITEKEY`. One request gives the whole estate's entry points.
- **`_next/static/chunks/pages/_app-<hash>.js`** → the route map, in one grep:
  `grep -oE '[a-zA-Z0-9_]+:function\(\)\{return"/[a-zA-Z0-9/_.?$-]*"'` → every BFF path
  (`/api/fe/profile`, `/api/fe/exchanges/calculate`, `/crypto-loans/api/…`, …).
- **IdP host** → `/.well-known/openid-configuration` + `/.well-known/jwks.json`: endpoints, grant
  types, PKCE methods, signing alg — the OAuth attack surface with zero guessing.
- **Legacy surface** → probe `?wsdl` on API paths. Found a public SOAP service this way
  (`OAuth2ServiceService` at `/api/oauth2?wsdl`, ns `spectrofinance.lt`) that no web2 scanner hits.
- **Backend fingerprint** → BFF error envelope `{errorCode,category,key,defaultMessage,spanId,traceId}`
  = Spring; CSRF enforced (`403 invalid_csrf_token`).
- **CORS** → ACAO here is a *fixed* value, not reflected. Always send lookalike origins
  (`*.evil.example`, `http://`, `null`, `host:evil`) and confirm it does NOT echo — a single
  `Origin: https://app.tld` test proves nothing.
