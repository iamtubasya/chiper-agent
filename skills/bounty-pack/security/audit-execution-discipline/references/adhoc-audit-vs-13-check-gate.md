# Ad-hoc audit vs the 13-check gate — why an honest manual audit can never reach HIJAU

Measured 2026-10-30 on `bankr.bot`. An audit that executed every mandatory tool by hand,
with real evidence on disk, reached **10/13 PASS and could not reach 11**. Knowing this up
front saves hours of chasing a gate that is structurally unreachable, and — more importantly —
stops you from "fixing" it by rubber-stamping N/A reasons.

## The symptom

`deep-audit-mode.py guard <dir>` → `BLOCKED — tools-usage.json not found`. You write a
truthful `tools-usage.json` from the artefacts you actually produced, and then:

```
✅ CHECK 1  tools-usage.json exists
✅ CHECK 2  all executed tools have evidence files
✅ CHECK 3  all evidence files real content (>=100 bytes)
✅ CHECK 4  all entries accounted for (no silent skip)
✅ CHECK 5  12 tools executed with real evidence
✅ CHECK 6  Variants: 15/15 vectors, 102 requests
✅ CHECK 7  PoC: no repo matched target tech (logged, verified)
✅ CHECK 8  poc-variant-usage.json empty — no tech-matched PoC repos (0C ledger clean)
✅ CHECK 9  Business-logic: 15/15 vectors, 56 probes, 1 interesting
✅ CHECK 11 poc-techniques-usage.json empty — no tech-matched PoC repos
❌ CHECK 10 reference-usage.json missing
❌ CHECK 12 asset-coverage FAIL for phase(s): ['0B', '0C']
❌ CHECK 13 skill-usage.json not found
```

## Why 10/12/13 are unreachable without the orchestrator

| Check | What it wants | Why ad-hoc cannot satisfy it |
|---|---|---|
| 10 | `reference-usage.json` | `execute-references.py` hard-refuses without `references-index.json`, and **only `force-full-execution.py` builds that index**. Running the executor directly prints `❌ references-index.json tidak ada — jalankan force-full-execution dulu`. |
| 12 | every 0B/0C/0D asset `USED` | `asset-coverage.py` accepts `N/A` **only** for reasons matching "feature absent in target". Every other honest reason is rejected — see the rejection table below. |
| 13 | `skill-usage.json` | **No generator script exists on disk.** `ls scripts | grep skill-usage` returns nothing. There is no supported way to produce this ledger. |

## CHECK 12's rejection vocabulary (learned the hard way)

Marking assets `N/A` with a truthful reason still fails, and the failure text names the rule:

```
FAIL 0B:recon:amass    [N/A reason not structural (feature-absent): 'passive sub enum covered
                        by subfinder+assetfinder+crt.sh' -> N/A only for 'fitur tidak ada di target']
FAIL 0C:tools:nikto    [N/A reason not structural (feature-absent): 'superseded: nuclei
                        5741-template sweep ran on all 5 dynamic hosts' -> ...]
FAIL 0C:tools:wpscan   [N/A without evidence (name the tool/probe that proved absence): ...]
FAIL 0C:tools:byp4xx   [N/A reason is a SURRENDER not a reason: '403-bypass vector fired via
                        execute-variants business-logic run' -> rework the tool, do not mark N/A]
```

So these reasons are all **rejected**:

- "covered by X instead" / "superseded by Y" → not structural
- "RoE forbids brute force / port scanning" → not structural
- "vector already fired via execute-variants" → classified as surrender
- "no repo in scope" (trufflehog/gitleaks) → not structural
- "tool binary is broken on this host" → not structural (and per library policy, do not
  encode broken-binary states as durable claims anyway)

The only accepted shape is: the *target* lacks the feature, and you can name the probe that
proved it (`no GraphQL endpoint on any host` after checking `/graphql`, `/v1/graphql`,
introspection). Even then, some tools legitimately cannot be marked N/A at all.

## What to do instead — pick one, never fake it

**Option A — run the orchestrator from the start.** If the engagement might end with a
"estate is clean" claim, launch `audit-pipeline-orchestrator.py` at 0A and let it own the
ledgers. Everything downstream then exists.

**Option B — accept BLOCKED and scope the claim.** This is correct when the audit is
time-boxed or exploratory. Report:

- the finding(s), which stand on their own evidence and do **not** depend on the gate
- the gate status verbatim (`10/13 PASS, BLOCKED`), never "HIJAU"
- coverage as **limited**, with the untested list named explicitly

**Never** mark N/A with an invented structural reason to force green. That converts an
honest BLOCKED into a fabricated coverage claim — the exact failure the gate exists to
prevent. The gate is a guard against over-claiming; satisfying it by lying inverts it.

## Building a truthful tools-usage.json (when you go Option B)

The verifier only demands that every `EXECUTED` entry has a real evidence file ≥1 byte
(CHECK 3 wants ≥100 B of real content), and that nothing is silently unaccounted. So copy
the artefacts you already have:

```python
rows = [  # (tool, status, source_artifact, note)
  ("nuclei","EXECUTED","nuclei_dyn.txt","5741 templates, 66400 req, 49 matches all info/low"),
  ("sqlmap","EXECUTED","sqlmap_tokens.log","not injectable"),
  ("dalfox","SKIP_WITH_REASON",None,"API is JSON-only, no HTML reflection point"),
  ("jsluice","NOT_FOUND",None,"binary not installed"),
  ("proxy/mitm","N/A",None,"no authenticated browser flow needing interception"),
]
```

Copy each source into `tool-evidence/<tool>.txt` and set `evidence_file` to the
target-dir-relative path. Valid statuses that do not block: `EXECUTED`, `RAN_WITH_ERROR`,
`NO_OUTPUT`, `NOT_FOUND`, `ERROR`, `TIMEOUT`, plus the skip family (`SKIP_WITH_REASON`,
`N/A`, `SKIP_NO_PARAM`, …). `FAILED_USAGE` blocks — it means the CLI was wrong and the tool
never scanned.

## Reusable scripts that DO run standalone

These produce real ledgers and are worth running even in Option B, because they genuinely
expand coverage rather than just bookkeeping:

```bash
python execute-business-logic.py <TARGET> --target-dir <DIR> --rate 1.5
# 15 vectors, ~56 probes: idor-bola, privesc, business-logic, mass-assignment, csrf,
# file-upload-bypass, cache-poisoning, 403-bypass, password-reset, websocket-abuse,
# api-versioning, rate-limiting, third-party, source-maps, http-smuggling

python execute-variants.py <TARGET> --target-dir <DIR> --max-variants 30 --rate 2 --budget 600
# 15 payload vectors, ~102 requests, loads the payload libraries from security-arsenal

python track-poc-execution.py <TARGET> --target-dir <DIR>
python execute-poc-variants.py <TARGET> --target-dir <DIR>      # empty+evidence if NO_PLAN
python execute-poc-techniques.py <TARGET> --target-dir <DIR>    # empty+evidence if NO_PLAN
```

Note `execute-variants` / `execute-business-logic` shell out to `nuclei` for several vectors,
so they take 10–15 minutes even at a bounded rate. Run them with `background=true`.

## Post-run note: `--derive` under-reports what you actually did

`asset-coverage.py --derive` populates from **pipeline-shaped artefact names**, so a manual
audit's evidence is invisible to it and 60 assets come back `NOT_RUN` even though the tools
ran. Fix the *names*, then re-derive or `--mark`:

```bash
cp 0B_recon/all_subs.txt subs.txt
cp 0B_recon/httpx.txt    live.txt
cp 0B_recon/katana_urls.txt urls.txt
python asset-coverage.py <DIR> --derive
python asset-coverage.py <DIR> --mark "nuclei=USED" --evidence tool-evidence/nuclei.txt \
  --reason "5741 templates, 66400 req, 49 matches" --phase 0C
```
