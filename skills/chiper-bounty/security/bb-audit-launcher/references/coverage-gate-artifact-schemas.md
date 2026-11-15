# Coverage-gate artifact schemas — what the 0C/0D gates actually read

Reverse-engineered 2026-10-08 (quarterwise v5) after burning ~10 turns guessing the shapes.
The gates read **files from disk**, so a wrong shape reads as "phase never ran".
Write these from the real results — never to make the gate green.

## Files and exact shapes

| file | shape | gate rule |
|---|---|---|
| `tools-usage.json` | **flat JSON list** (NOT `{"tools":[...]}`) | >=3 entries `status=="EXECUTED"` whose `evidence_file` path exists **and is >=100 bytes** |
| `variant-usage.json` | flat list | >=8 entries `status=="EXECUTED"` |
| `business-logic-usage.json` | flat list | >=12 entries `status=="EXECUTED"` |
| `poc-execution.json` | flat list | >=1 `status=="EXECUTED"`, **or** every entry `status=="NO_POC_MATCHED"` (logged no-tech-match) |
| `poc-variant-usage.json` | flat list | >=1 `status in ("EXECUTED","NO_PAYLOAD_FILES")` and file >=50 bytes |
| `asset-coverage.json` | **dict** keyed `"<phase>:<class>:<asset>"` -> `{asset,class,phase,status,evidence,reason}` | every mandated asset must be `USED` with evidence |
| `skill-usage.json`, `candidates.json` | any JSON object | existence only (0C) |
| `subs.txt`, `live.txt`, `urls.txt`, `ports.txt`, `crawled.txt` | plain text | >1 / >1 / >5 / >0 / >0 lines |

**`evidence_file` MUST be absolute.** A relative path is resolved against the *caller's* CWD
(usually `D:/data hermes/bug-bounty`), so `tool-evidence/nuclei.txt` "does not exist" and the gate
reports `4 EXECUTED, 0 real-evidence` while the files are sitting right there.

## verify-tool-usage.py — the only accepted `status` vocabulary

```
EXECUTED | RAN_WITH_ERROR | NO_OUTPUT | NOT_FOUND | ERROR
SKIPPED_WEB_TARGET | SKIP_NO_URL_TARGET | SKIPPED_NO_SOLIDITY_TECH | SKIP_WITH_REASON
SKIPPED | SKIP_NO_PARAM | NEEDS_REQUEST_TEMPLATE | FUZZ_ONLY | STARTED_NO_TOKEN
FAILED_USAGE | FAILED        <- hard block, never use casually
```
Anything else lands in **CHECK 2b "unaccounted statuses"** and fails the gate with a message that
names your invented statuses. Map to the list above: a scanner the policy forbade ->
`SKIP_WITH_REASON` (put the policy clause in `reason`); a scanner that ran and died ->
`RAN_WITH_ERROR`; not installed -> `SKIP_WITH_REASON`.

## asset-coverage.py — the ledger tool

```
skills/security/audit-execution-discipline/scripts/asset-coverage.py <target_dir> [--phase 0B|0C|0D|--all]
    --init                 seed every mandated asset as PENDING
    --derive               auto-populate from the real artefacts (tools-usage.json etc.)
    --mark <asset>=<STATUS> [--evidence PATH] [--reason TEXT]
```

Pitfalls:
- `--init` **merges** into an existing `asset-coverage.json`. If you wrote your own hand-rolled
  `{"assets":[...]}` first, the merge produces a mixed structure and every later `--derive` dies
  with `TypeError: string indices must be integers`. Rename the hand-rolled file and `--init` into
  a clean directory.
- `--derive` reads `tools-usage.json`; a non-list shape crashes the same way.
- After `--derive`, anything still `PENDING` is a FAIL. Mark each one deliberately:
  `--mark nuclei=USED --evidence tool-evidence/nuclei.err --reason "rate 5, timed out at 420s"`.

## Policy-limited engagement -> the honest end state

When the program forbids scanner load, the checkpoint will never go green. That is the correct
result, not a defect to paper over. Report it as:

```
audit-checkpoint.py --phase all  ->  30/33
the 3 remaining FAIL are ONE root cause, marked N/A-BLOCKED (never "passed"):
  program rule: "<quote the clause verbatim>"
```

Do **not** invent `USED` rows for tools that never fired. The gate is a claim about what happened;
the honest red gate plus a per-asset ledger (USED / NOT_RUN / NOT_APPLICABLE counts) is the
deliverable. Say "manual/targeted, scanners NOT run (program rule)" — never "all tools run".

## Ordering that avoids rework

1. Run the tools you are actually allowed to run; confirm each wrote a **body** (rc=0 + 0 bytes is
   fake coverage).
2. Write `tools-usage.json` (list, absolute `evidence_file`), `variant-usage.json`,
   `business-logic-usage.json`, `poc-execution.json`, `poc-variant-usage.json`.
3. `asset-coverage.py <dir> --init` in a clean dir, then `--derive`, then `--mark` the remainder.
4. Write `validated-findings.json`, `review-candidates.json`, `REPORT-survivors.md`, `findings.json`
   for 0E (all four are existence-checked; `findings.json` may carry `observations[]` with
   `validated_findings: []`).
5. `audit-checkpoint.py <dir> --phase all` and quote the honest score.
