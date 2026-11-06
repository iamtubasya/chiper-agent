# The aggregator ingests the RUN TREE — scope it, or it manufactures findings

Measured 2026-10-10 on `download.jetbrains.com` (recorded at the time as 0E; aggregate now runs in 0C-C7, `aggregate-findings.py`).
Before: **151 candidates**, of which **all** were junk. After the fix: **2**.

The gate chain (finding_gate → validate → triage) caught every one of them, so nothing false
shipped — but the aggregator poisoned **every downstream stage** with noise, which is why the
funnel looked like it had 151 things to reason about.

## The three defects, in the order they were found

### 1. Wholesale tree ingestion

```python
for f in sorted(worker_dir.rglob("*")):        # every file under the run dir
    if f.name in SKIP_NAMES:      # a hand-written set of ~8 names
        continue
    if f.suffix not in (".md", ".txt", ".json"):
        continue
```

`rglob` plus an 8-name skip-list means the aggregator eats its **own pipeline metadata**: the asset
ledger, every `*-usage.json`, `references-index.json`, `poc-plan.json`, `skill-evidence/*.md`,
`dork-recon/*`, and its own previous output.

Add **two independent filters**, not one longer list:

- `EXCLUDE_DIRS` — by directory: `skill-evidence/ dork-recon/ sol-source/ crytic-export/
  __pycache__/ graphs/ sqlmap-out/ manifest-work/`
- `EXCLUDE_NAME_RE` — by name regex so future artefacts are covered without another patch:
  `usage|index|-plan|coverage|state|meta|candidates?|chains|gated|survivors|` `^triage|^report-|^summary|^phase-?log|^review-|^audit-|^run-meta`

Skipping by **name only** is what let `findings-new.json` back in (below) — the regex must match
`^findings.*\.json$`, not the literal `findings.json`.

### 2. Keyword matching against FILE PATHS → phantom HIGH

`NOTABLE_KW` included `misconfig`, `exposure`, `disclosure`, `sensitive`, plus bare `200`/`201`/`500`.
`references-index.json` is a JSON list of **nuclei template paths** — `http/misconfiguration/...`,
`http/exposures/...`, `http/vulnerabilities/...`. Every path matched, on the **name** of a template,
with no request ever sent. Result:

```
[poc-plan.json]          30 notable response(s) — Medium
[references-index.json] 333 notable response(s) — HIGH      <-- an INDEX scored HIGH
```

**Rule: a candidate needs a response, not a keyword.** Require, per line:

```python
_STATUS = r"\[(\d{3})\]|(?:^|\s)(\d{3})(?:\s|$)|status[:=]\s*(\d{3})"
_MARKER = r"\[\+\]|vulnerable|identified|injectable|CVE-\d{4}-\d+|leaked|admin[\"']?\s*[:=]\s*true"
_URLISH = r"https?://|(?:^|\s)/[A-Za-z0-9._~/-]{2,}"
_PATHLIKE = r"\.(?:yaml|yml|go|py|json|txt|md|php|js|xml)$"

if _PATHLIKE.search(first_token):        continue   # a filesystem path is not an HTTP response
if not ((_STATUS.search(line) and _URLISH.search(line)) or _MARKER.search(line)):
    continue                                        # keyword-only match -> not a candidate
```

The `_PATHLIKE` guard is the specific fix for the template-path case; the `(status AND url) OR
marker` rule is the general one.

### 3. Self-ingestion — the aggregator grades its own output

Running it a second time produced **duplicates of every candidate** plus documents that had already
been filtered out (they came back in through the previous output file). Two guards:

```python
EXCLUDE_NAME_RE = re.compile(r"^findings.*\.json$|^gated.*\.json$|^survivors.*\.json$|" + ...)
# and, explicitly, never read the file you are about to write
if f.resolve() == (worker_dir / output_file).resolve():
    continue
```

Same family as `finding_gate` scoring `REPORT-survivors.md`
(`references/mechanical-triage-gate-and-self-echo.md`) — **a producer that reads a directory will
eventually read itself.** Any new "collect everything under the run dir" step needs this guard
written at the same time, not after the duplicates appear.

## Verification (RULE 0c — prove it, then prove it again)

Re-run the SAME run dir with the old and the new aggregator and compare counts:

```
SEBELUM : 151 kandidat   (references-index.json = HIGH, 9 skill-evidence headers, TRIAGE.md, duplikat)
SESUDAH :   2 kandidat   — both genuine evidence files
              [tool-evidence\gobuster-cmdi]         1 notable — Medium
              [tool-evidence\race-checker.py-race]  2 notable — Low
```

A **dramatic drop is the expected shape** here (noise removal), unlike a gate fix where the
expected shape is a mixed split. Assert on both: the junk must be gone *and* the two real
candidates must survive — a filter that returns 0 is over-filtering, not a success.

## Pitfalls hit while writing the fix

- **`NameError` from a helper defined in the wrong scope.** `EVIDENCE_HEADER_RE` was defined inside
  `aggregate()` but referenced from `parse_plain_findings()` — a module-level function. Same class as
  the `nl`/`_re` bugs in `references/runtime-execution-policy-2026-10-10.md` §10. The
  `unbound_name_fail` check does NOT catch cross-scope module/function cases; exercising the
  function does.
- **The header guard turned out to be redundant.** Skipping a file whose body is only an evidence
  header was unnecessary — the strict-signal rule already discards it (a header has no status+URL and
  no marker). Prefer deleting a redundant guard over debugging its scope.
- **The strict rule must not kill real evidence.** `variants/*.txt` and `tool-evidence/*.txt` are
  genuine C2/C3 output and must still be ingested — they pass because they contain real
  status/response lines. If a class of genuine evidence starts being dropped, the fix is to check
  what the *writer* emits, not to loosen the signal rule back to keyword matching.
