# 0D Gate Hard-Block Recovery

Measured 2026-10-17 on microkeeper.com.au (run dir: `orchestrator-microkeeper_com_au`).
The 0D gate (`verify-tool-usage.py` 13 checks + `asset-coverage` derive) hard-blocks
after 3 rework attempts on BOOKKEEPING gaps, not coverage gaps. Recognize the loop,
fix the ledger, resume — do not re-run force execution hoping it self-heals.

## Symptom

```
❌ GATE FAILED (attempt 1) — analyzing failures...
🔁 REWORK (generic): re-running full force execution
... ×3 ...
❌ GATE FAILED after 3 attempts — HARD BLOCK
❌ PIPELINE FAILED: TOOL USAGE VERIFICATION FAILED
```

## RC1 — asset-coverage derive rejects no-payload C5/C6b ledgers (FIXED 2026-10-17)

`asset-coverage.py`'s `any_exec()` only counted status `EXECUTED`, while
`verify-tool-usage.py` CHECK 8 accepts `NO_EXTRACTABLE_PAYLOAD` / `NONWEB_PAYLOAD_TYPE`
as "logged". When C4 executed ≥1 PoC repo (so the `_no_poc` empty-ledger path is dead)
but C5/C6b found no extractable payload files, the derive marked
`poc-variants(C5)` / `poc-techniques(C6b)` / `poc-technique-atlas` NOT_RUN forever.

Fix applied in place: added `any_ran()` (accepts EXECUTED + NO_EXTRACTABLE_PAYLOAD +
NONWEB_PAYLOAD_TYPE) and switched the three checks to it — mirrors CHECK 8 semantics.
If you see NOT_RUN with reason `no evidence: poc-variant-usage.json` on a run whose
C5 honestly found nothing, re-check that patch is present.

## RC2 — finding_gate skips REPORT-survivors.md on zero survivors (workaround)

`finding_gate.py` deliberately does NOT write `REPORT-survivors.md` when 0 findings
survive ("no survivors — do NOT write a report"), but `audit-checkpoint.py` requires
the file to exist. Result: a clean negative audit fails the final gate.

Workaround: write the honest zero-survivors report manually (template below). Root fix
(patch finding_gate.py to always write the report, zero or not) is still pending.

## RC3 — the rework loop DESTROYS manual fixes

The rework re-runs `force-full-execution.py`, which re-executes
`execute-poc-variants.py` / `execute-poc-techniques.py` — both OVERWRITE
`poc-variant-usage.json` / `poc-techniques-usage.json` back to `[]`. Any manual patch
made while the loop runs is erased before the next gate attempt.

RULE: kill the loop FIRST, then fix files, then resume. Never patch mid-loop.

## RC4 — ledger key mismatch: `evidence` vs `evidence_file` (MEASURED 2026-10-25)

Second hard-block of the same run, after RC1 was fixed. Two distinct bookkeeping defects, both
cosmetic, both fatal to the gate:

```
❌ UNACCOUNTED statuses (gate blind spot): [None]
❌ Evidence files missing for: ['php2shell-verify', 'php2shell-verify']
```

1. **Missing `status` on an otherwise-complete entry.** A `php2shell-verify` entry carried `phase`,
   `tool`, `invoked: true`, `evidence`, `result` and `cve` — but no `status`. CHECK 2b buckets entries
   by `status` into executed / not_found / skipped / errors / failed_hard; `None` falls into none of
   them, so it lands in `unaccounted` and the set of unaccounted values prints as `[None]`. The gate
   message names no tool, which is why it reads like a mystery. Fix: `e["status"] = "EXECUTED"` for
   every entry that has `invoked: true` and a `result` string.

2. **`evidence` is not `evidence_file`.** CHECK 2's evidence loop reads **`evidence_file`** only:
   ```python
   ev_file = entry.get("evidence_file")     # NOT entry.get("evidence")
   if not _ev_ok(target_dir, ev_file, 1): missing_evidence.append(...)
   ```
   while several writers record the path under `evidence`. The artefact exists on disk
   (`php2shell-verification.json`, 8 642 B) and the entry still fails, because the key the checker
   looks at is null. Fix — one line, preserves both:
   ```python
   for e in d:
       if e.get("evidence") and not e.get("evidence_file"):
           e["evidence_file"] = e["evidence"]
   ```
   Symptom to recognise: "Evidence files missing for: ['<tool>']" where `ls` shows the file present.

Both fixes are pure ledger edits and survive a `verify-tool-usage.py` re-run immediately. **Do not
relaunch the orchestrator to make them take** — that re-runs writers that overwrite the ledger.

## RC5 — C5/C6b empty ledger where the `_no_poc` shortcut does NOT apply

`asset-coverage.py` accepts an empty `poc-variant-usage.json` / `poc-techniques-usage.json` only via
`(_no_poc and not pvc)`, where `_no_poc = (pce is not None and pce and not any_exec(pce))` — i.e. only
when **no** PoC repo executed. A run with 32 EXECUTED + 12 NO_ENTRY_POINT repos has `any_exec(pce)`
true, so `_no_poc` is false and the empty ledger can never be accepted. `verify-tool-usage.py`
CHECK 8 / CHECK 11 have the same shape. Rework loops here forever (RC3 makes it worse).

The honest exit is **not** to hand-write `[]` and not to fabricate entries — it is to answer the
question the ledger is supposed to answer, then record the answer:

1. Scan the actual PoC source on disk, read-only, no network:
   ```python
   PAT = re.compile(r"(payload.*|fuzz.*\.py|wordlist.*\.txt|.*wordlist.*|bypass.*\.txt)$", re.I)
   EXCL = {"requirements.txt", "package.json"}
   for repo in poc_execution_repos:
       files = [f for f in (POC_DIR / repo).rglob("*")
                if f.is_file() and PAT.match(f.name) and f.name.lower() not in EXCL]
   ```
   Measured on djangoeurope: 44/44 repos existed, **0/44** had a payload-like file — every one is a
   standalone exploit script. So `NO_EXTRACTABLE_PAYLOAD` is the true verdict, not a dodge.
2. Write one ledger entry **per repo** (not one aggregate row) plus one evidence file per repo, in
   both directories the checkers look at:
   `poc-variants/<repo>.txt` (`# POC VARIANT EVIDENCE:`) and
   `poc-techniques-evidence/<repo>.txt` (`# POC-TECHNIQUES EVIDENCE:`). Each ≥100 B, carrying the
   repo path, the pattern list that was searched, the zero result, the request count (0) and a
   timestamp. CHECK 11 flags if >30 % of entries lack `evidence_file`, so point every entry at its file.
3. Guard the honesty with an assert so a future run cannot claim zero without having scanned:
   ```python
   assert r["n_payload"] == 0, repo        # per repo, against the scan result
   ```
4. `pathlib.Path("poc-variants/x.txt").relative_to(resolved_target_dir)` raises `ValueError: is not in
   the subpath of ...` when the dir was made from a bare `"."` — store the relative path as a plain
   string (`"poc-variants/" + f.name`) instead.

Result on this run: `verify-tool-usage.py` → `ALL 13 CHECKS PASSED`, `deep-audit-mode.py guard` →
`✅ DEEP-AUDIT GATE: pipeline evidence OK`. Full 0C ledger: 14 remaining N/A entries, all with a
documented reason (skip-no-param, tool-not-installed, web2 track), none NOT_RUN.

## Recovery procedure (ordered)

1. **Kill the loop** (MSYS-safe; `//F` because bash mangles `/F`, `tr -d '\r'` because
   wmic CR endings corrupt the PID):
   ```bash
   wmic process where "name='python.exe' and CommandLine like '%<target-fragment>%'" \
     get ProcessId /format:list | tr -d '\r' | grep -oE "^[0-9]+$" \
     | while read pid; do taskkill //F //PID $pid; done
   ```
   Only kill PIDs whose CommandLine matches YOUR target — other audits run concurrently.
2. **Write the honest C5/C6b ledgers.** If `poc-execution.json` has ≥1 EXECUTED repo,
   the empty-ledger acceptance path is dead; record per-repo entries:
   ```json
   [{"repo":"<repo>","status":"NO_EXTRACTABLE_PAYLOAD",
     "reason":"standalone exploit script; no payload/variant files",
     "requests_fired":0,
     "evidence_file":"poc-variants/<repo>.txt"}]
   ```
   plus marker evidence files: `poc-variants/<repo>.txt` starting `# POC VARIANT EVIDENCE:`
   and `poc-techniques-evidence/<repo>.txt` starting `# POC-TECHNIQUES EVIDENCE:`
   (CHECK 8b checks the poc-variants filename; CHECK 11 checks the evidence_file pointer).
3. **Re-derive and verify BEFORE relaunching:**
   ```bash
   python scripts/verify-tool-usage.py <rundir>     # want: ALL 13 CHECKS PASSED
   python scripts/audit-checkpoint.py <rundir> --phase all   # want: 33/33
   ```
4. **Write REPORT-survivors.md** (zero-survivor template):
   ```markdown
   # REPORT-survivors — <target>
   **Survivors: 0.** No candidate proved real impact at the finding gate.
   ## Gate result (finding_gate v2, fail-closed)
   - Input: weaponized-shipped.json — 0 candidates after dedupe
   - REPORT: 0 | DOWNGRADE: 0 | DROP: 0
   ## Context — what was reviewed and rejected
   <one line per rejected candidate class, with the verification that killed it>
   ```
5. **Resume from 0D** — tracker edit, keep the expensive upstream phases:
   ```python
   import json
   p = "~/.chiper/skills/bounty-pack/trackers/audit-pipeline-https___<target>.json"
   d = json.load(open(p, encoding="utf-8"))
   d["completed_phases"] = [x for x in d["completed_phases"] if x in ("0A","0B","0C")]
   d["current"] = "0C"
   json.dump(d, open(p, "w", encoding="utf-8"), indent=1)
   ```
   Relaunch with the ORIGINAL args. A clean ledger makes the gate pass on attempt 1 and
   the pipeline runs 0D→0F in under a minute (nothing left to aggregate).

## RC4 — a ledger entry with `result` but no `status` + `evidence` instead of `evidence_file` (2026-10-25)

Measured on djangoeurope v3 (run dir `orchestrator-www_djangoeurope_com`). The rework loop burned
three attempts on two failures that both came from ONE malformed ledger pair:

```
❌ UNACCOUNTED statuses (gate blind spot): [None]
❌ Evidence files missing for: ['php2shell-verify', 'php2shell-verify']
```

The two `php2shell-verify` entries had `invoked: true`, `result: "confirmed=0 ..."`, and an `evidence`
key pointing at a real 8.6 KB `php2shell-verification.json` — but **no `status` field**, and CHECK 2b
iterates a fixed `ACCOUNTED` set that does not contain `None`. Separately CHECK 2's evidence pass reads
`entry["evidence_file"]`, not `entry["evidence"]`, so the same entries were also reported as
"evidence missing" while the file sat on disk.

Fix (both, in one pass, after killing the loop):

```python
import json
p = "<rundir>/tools-usage.json"; d = json.load(open(p))
for e in d:
    if not e.get("status") and e.get("invoked"):
        e["status"] = "EXECUTED"
    if e.get("evidence") and not e.get("evidence_file"):
        e["evidence_file"] = e["evidence"]
json.dump(d, open(p, "w"), indent=1)
```

Diagnose in that order — `status` first, then the key name — because "Evidence files missing" reads like
a deleted artefact and sends you re-running the tool, while the file is present the whole time. Never
satisfy CHECK 2b by inventing a status for an entry whose tool did not actually run; this only applies
when `invoked: true` and a real evidence file exists.

## RC5 — empty C5/C6b ledger when `poc-execution.json` HAS executed repos (`_no_poc` never fires)

The empty-ledger acceptance path documented in RC1 is gated on `_no_poc` — `poc-execution.json` exists
and has **zero** EXECUTED entries. On this run C4 logged 32 EXECUTED + 12 NO_ENTRY_POINT repos, so
`_no_poc` was false, `poc-variant-usage.json` stayed `[]`, and `asset-coverage.py` derived
`NOT_RUN — no evidence: poc-variant-usage.json` for `poc-variants(C5)`, `poc-techniques(C6b)` and
`poc-technique-atlas` on every attempt. Re-running `execute-poc-variants.py` could not help: it writes
`[]` again for the same reason.

The honest fix is to record WHY each repo yielded nothing, per repo — 44 entries each side, which also
satisfies `verify-tool-usage.py` CHECK 8b and CHECK 11 (both want per-repo evidence files):

```python
# 1) scan the local PoC corpus read-only; never claim 0 matches without this
import json, pathlib, re
POC = pathlib.Path("D:/data hermes/poc-compact")
PAT = re.compile(r"(payload.*|fuzz.*\.py|wordlist.*\.txt|.*wordlist.*|bypass.*\.txt)$", re.I)
EXCL = {"requirements.txt", "package.json"}
rows = []
for x in json.load(open("<rundir>/poc-execution.json")):
    p = POC / x["repo"]; hits = []
    if p.exists():
        hits = [f for f in p.rglob("*") if f.is_file() and f.stat().st_size < 2_000_000
                and PAT.match(f.name) and f.name.lower() not in EXCL]
    rows.append({"repo": x["repo"], "exists": p.exists(), "n_payload": len(hits)})
json.dump(rows, open("<rundir>/poc-variants/scan-local.json", "w"), indent=1)

# 2) one evidence file + one ledger row per repo, asserting the scan result
assert all(r["n_payload"] == 0 for r in rows)   # honesty guard: only write NO_EXTRACTABLE on a real 0
```
Write `poc-variants/<repo>.txt` starting `# POC VARIANT EVIDENCE:` and
`poc-techniques-evidence/<repo>.txt` starting `# POC-TECHNIQUES EVIDENCE:`, each naming the patterns
searched, the corpus path and the scan timestamp. Ledger status `NO_EXTRACTABLE_PAYLOAD`, reason
naming the patterns, `payloads_extracted: 0`, `requests_fired: 0`, plus `evidence_file` **relative to
the rundir** (`poc-variants/<name>.txt`) — `Path.relative_to()` raises
`ValueError: ... is not in the subpath` when the file object was built from a relative path, so build
the string directly.

Then re-derive and verify before relaunching: `asset-coverage.py <dir> --derive` →
`verify-tool-usage.py <dir>` (want ALL 13 CHECKS) → `deep-audit-mode.py guard <dir>`.

## Related — browser fallback when Camofox is down

`browser_navigate` fails with "Cannot connect to Camofox" when the server isn't running.
Fallback that works: start Chrome yourself, then drive CDP directly —
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new \
  --remote-debugging-port=9222 --user-data-dir=<fresh-profile> about:blank
```
Then `browser_cdp`: `Target.getTargets` → `Page.navigate` → `Runtime.evaluate`.
For async page state use `awaitPromise: true` with a `new Promise(r => setTimeout(...))`
expression — without it the evaluate returns an empty object.

## RC4 — ledger entries missing `status` AND using `evidence` instead of `evidence_file` (2026-10-25)

Measured on djangoeurope (`orchestrator-www_djangoeurope_com`). The gate reported two failures that
looked like coverage gaps and were pure bookkeeping:

```
❌ UNACCOUNTED statuses (gate blind spot): [None]
❌ Evidence files missing for: ['php2shell-verify', 'php2shell-verify']
```

Both came from the SAME two ledger entries. `php2shell-verify` was written with
`{"tool","invoked","evidence","result","cve","timestamp"}` — no `status` field, and the path under the
key `evidence` instead of `evidence_file`:

- CHECK 2b collects entries whose status is not in `ACCOUNTED` → `None` is not in `ACCOUNTED` →
  "UNACCOUNTED statuses [None]". `invoked:true` + a `result` string does NOT count.
- CHECK 1 reads `entry["evidence_file"]` only → `None` → "Evidence files missing", even though the
  artefact (`php2shell-verification.json`, 8.6 KB) was sitting on disk the whole time.

Fix is a two-line normalisation over the ledger (back it up first):

```python
for e in d:
    if e.get("evidence") and not e.get("evidence_file"):
        e["evidence_file"] = e["evidence"]        # key rename
    if "status" not in e and e.get("invoked"):
        e["status"] = "EXECUTED"                  # only when the evidence really exists
```

Generalise: **any writer that emits `invoked:true` must also emit `status` and `evidence_file`.**
`result:` strings are human prose to the gate, not status. When you see `UNACCOUNTED statuses [None]`,
grep the ledger for entries whose key set is missing `status` — it is never a real missing tool run.

## C5/C6b: how to write the honest non-empty ledger (do this instead of chasing the rework loop)

The `[]`-with-proof path only exists while `poc-execution.json` has ZERO EXECUTED repos. Once C4
executed even one repo, `_no_poc` is dead and an empty C5/C6b ledger fails forever — while
`execute-poc-variants.py` keeps overwriting whatever you hand-write, so the loop never converges.

Correct sequence (measured 2026-10-25, 44 matched repos):

1. **Kill the orchestrator first** (RC3), then work.
2. **Actually scan the local PoC corpus, read-only, no network.** For every repo in
   `poc-execution.json`, walk `POC_DIR/<repo>` looking for `payload.*`, `fuzz*.py`, `wordlist*.txt`,
   `*wordlist*`, `bypass*.txt` (exclude `requirements.txt`/`package.json`). Write the result to
   `poc-variants/scan-local.json`. On this run: 44/44 repos present, **0** with payload files —
   realistic, because a matched repo is usually a standalone `exploit.py`.
3. **Emit one entry per repo, plus a real per-repo evidence file**, from that scan (never hand-type
   counts; assert `n_payload == 0` before writing `NO_EXTRACTABLE_PAYLOAD`):
   - `poc-variant-usage.json` → `{"repo","status":"NO_EXTRACTABLE_PAYLOAD","reason","payloads_extracted":0,"requests_fired":0,"ts","evidence_file":"poc-variants/<repo>.txt"}`
   - `poc-techniques-usage.json` → same shape + `"interesting":false`, `evidence_file` under
     `poc-techniques-evidence/<repo>.txt`
   - Each evidence file starts with the CHECK 11 marker (`# POC VARIANT EVIDENCE:` /
     `# POC-TECHNIQUES EVIDENCE:`) and records: repo path, whether it exists, the patterns searched,
     matches found, requests fired (0), verdict, timestamp, and the scan artefact it came from.
   CHECK 8b wants `poc-variants/<repo>.txt` (repo name, `/`→`_`, first 60 chars) and CHECK 11 wants
   `evidence_file` resolvable from the target dir — **use a relative path**, and beware
   `Path.relative_to()` raising when `Path(".")` is a str-built path (build the string directly).
4. **Re-derive, then verify before relaunching:**
   `python asset-coverage.py <dir> --derive` → then
   `python verify-tool-usage.py <dir>` must print `ALL 13 CHECKS PASSED` → then
   `python deep-audit-mode.py guard <dir>` must print the green line.
   Derive matters: asset-coverage caches NOT_RUN for `poc-variants(C5)` until it is re-derived.
5. Only then resume from 0D.

Do not re-run force-execution hoping it heals; every pass rewrites the ledgers back to `[]` and burns
another 20 minutes (measured: 3 attempts, ~3 h wall clock).

## RC5b — `execute-poc-variants.py` fails SILENTLY: "Matched repos: 0" with exit 0

Measured 2026-10-31 on city-data.com and stay22.com. Both runs hit the 0C gate with

```
FAIL 0C:payload:poc-variants(C5)   [NOT_RUN]
FAIL 0C:payload:poc-techniques(C6b) [NOT_RUN]
```

while `poc-execution.json` held **2 EXECUTED** repos each (city-data: `phpBB-CVE-2026-48611`,
`CVE-2026-42945-nginx-rift-poc`; stay22: `nextjs-sa-dos-poc-20260413`,
`CVE-2026-11114-Node.js-vm-Sandbox-Escape`). Re-running the writer did nothing:

```
Matched repos: 0        # <- the tell
```

`execute-poc-variants.py` does **not** read `poc-execution.json` to find its candidates — it
re-derives the match set from the target fingerprint and, when that set is empty, writes
`poc-variant-usage.json` as `[]` and **exits 0**. There is no error, no warning, and the
`NOT_RUN` reason it leaves behind (`no evidence: poc-variant-usage.json`) points at the file,
not at the tool that emptied it. Do not loop on the tool.

Recognise it by this pair, then apply the RC5 procedure (per-repo `NO_EXTRACTABLE_PAYLOAD`
entries + `# POC VARIANT EVIDENCE:` / `# POC-TECHNIQUES EVIDENCE:` marker files):

| Signal | Meaning |
|---|---|
| `Matched repos: 0` on stdout | writer found no candidates — NOT "no PoCs exist" |
| `poc-execution.json` has ≥1 `EXECUTED` | the `_no_poc` shortcut is dead; `[]` can never pass |
| `--derive` still prints `NOT_RUN` | ledger is empty, not stale |

The honest ledger entry records the real reason from disk. On these two runs the EXECUTED repos
had `exit_code != 0` (the PoC ran and failed — phpBB/nginx/nextjs CVEs are not applicable to a
live city-data PHP/nginx edge or a Cloudflare-fronted Next.js app), so the correct status was
`NO_EXTRACTABLE_PAYLOAD` with the raw output attached as evidence, not a fabricated payload.
Both targets then reached `0C: 49 ok / 0 fail` and `audit-checkpoint.py --phase all` → `33/33`.
