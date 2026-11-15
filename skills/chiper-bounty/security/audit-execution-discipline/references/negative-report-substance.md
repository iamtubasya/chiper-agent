# A negative report must be a DELIVERABLE, not just an honest one

Operator asked for a report review (2026-10-10, `download.jetbrains.com`). The report was 851 bytes:

```
# Audit report — https://download.jetbrains.com
**Result: NO REPORTABLE FINDINGS.**
## Why this report is empty
`0 findings cleared impact + triage gates`. No candidate met the reporting bar…
## What was actually done
| artefact | count |
| candidates collected | 151 | … | cleared validation | 4 |
## Evidence
Tool evidence: `tool-evidence/` · references: `reference-usage.json` · …
```

**Honest — and not good enough to send.** RULE 41 guarantees a negative result *exists*; this
reference is about making it *usable*. The distinction matters because a negative report is the
artifact an operator forwards to a programme, and it is also the artifact he will re-read months
later to decide whether a re-run is worth it.

## The four gaps, each with the data that was already on disk

Every item below was **already written** by the pipeline — the report simply did not read it.

| gap | why it matters | where the data already was |
|---|---|---|
| **No per-candidate rejection reason** — "17 ready after review" with no list | the reader cannot tell *rejected on merit* from *never examined*; "17 READY → 0 passed" invites exactly the question the operator then asked | `review-candidates.json` (per-candidate cek-1/2/3 + `why` + verdict), `gated.json` (impact verdict + `drop_flags`) |
| **No coverage summary** — nothing says what was actually exercised | this is the whole difference between *"tested and clean"* and *"not tested"*; RULE 41's marker dirs exist precisely to make that distinction, and then the report throws it away | `tools-usage.json`, `variant-usage.json`, `business-logic-usage.json`, `poc-execution.json`, `reference-usage.json`, `asset-coverage.json` |
| **No negative-coverage statement** — no `diuji: … ; BELUM diuji: …` | the DEEP-AUDIT rule REQUIRES this block for any "clean/mature" claim; a negative report is that claim in its strongest form | `asset-coverage.json` (USED vs N/A + the reason for each N/A) |
| **No statement of what was NOT covered** | honest negatives name their own boundary; without it the report reads as a completeness claim it cannot support | the N/A reasons (`binary absent on host`, `target is not WordPress`) and the tool statuses (`NOT_FOUND`, `SKIP_WITH_REASON`) |

## Shape a negative report should have

Sections, in this order. All of it is derived, none of it is prose invention:

1. **Result** — one line, no hedging.
2. **Why empty** — which gates dropped what, with counts.
3. **Coverage — what was actually exercised.** Per class, the *count and where the evidence lives*:
   dedicated tools (N executed / M accounted), payload variants (V vectors / R requests),
   business-logic (V vectors / P probes), PoC (N executed, K logged no-entry-point),
   references (N requests), techniques (N fired), recon (N assets). Cite the artefact next to each
   number so the claim is checkable.
4. **Candidates and why each failed** — for the READY set, one line each: id/class → the cek that
   rejected it → the flag. Group by rejection reason if the list is long.
5. **Not covered / boundary** — every `N/A` grouped by reason, plus any `NOT_FOUND` tool. This is the
   honest edge of the audit and the most valuable paragraph in the document.
6. **Evidence index** — the artefact map (already present; keep it).

## Consumer↔producer contract — two mis-reads that fail SILENTLY

Deriving the report from artefacts introduced two bugs that produced a **factually wrong but
perfectly plausible-looking** document. Both are the same class: **the consumer assumed a contract
(key name, container shape) that the producer never agreed to, and the wrong guess rendered as
"data absent" instead of raising.** Neither threw. Both shipped into the report.

| mis-read | what the producer actually wrote | what the consumer assumed | what the report said |
|---|---|---|---|
| **field NAME** | `reasons: [...]` (list) **+** `drop_flags: [...]` | `reason` (scalar) | `(no reason recorded)` in **every** row — as if the gate had dropped 100 candidates without explaining itself |
| **container SHAPE** | `{"metadata": {...}}` (dict wrapper) for `validated-findings.json` | row-list | `cleared validation 4` when the true count was **0** — `len(dict)` counted *keys* |

Both are worse than a crash. A crash stops the run; these produce a report a reader will believe —
and the second one is a **stale nonzero count on a negative report**, i.e. exactly the over-claiming
RULE 0 exists to prevent, arriving through the back door.

**Rules when a consumer reads a producer's artefact:**

1. **Read the producer's actual output before writing the reader.** `python -c "import json;
   print(list(json.load(open('<artefact>'))[0].keys()))"` — one command, settles both the key name
   and the value type. Do not infer the schema from the field's *purpose*.
2. **Accept the field in every shape it plausibly arrives in**, and say which one you took:
   a list under `reasons` / a scalar under `reason` / a list under `drop_flags` — collect all, then
   join. A reader that handles one shape and silently yields `None` for the other is a trap.
3. **A counter must know the container.** `len(x)` is correct for a bare list and *wrong by
   definition* for a dict wrapper (it counts keys). Write it shape-aware, or normalise the artefact
   to a row list first:
   ```python
   def _rows(name):                      # list OR {"findings": [...]} OR {"metadata": {...}}
       for key in (None, "findings", "candidates", "tools", "chains"):
           ...
           if key is None and isinstance(d, list):      return d
           elif isinstance(d, dict) and isinstance(d.get(key), list): return d[key]
       return []                          # unknown wrapper -> 0 rows, never key-count
   ```
4. **Prefer an explicit unknown over a plausible default.** `"(gate recorded no reason)"` is
   acceptable only when the gate genuinely wrote none — not when your key was wrong. If the reader
   cannot find a field it *expects*, print the keys it did find (`keys=[…]`) so the mismatch is
   visible in the output rather than laundered into a sentence.
5. **Sanity-check a negative report against the funnel below it.** A count that is nonzero while
   every stage beneath it is zero (`cleared validation 4` under `survivors 0`) is internally
   contradictory — assert the funnel is monotonic non-increasing before writing.

Cheap verification: build the report, then re-read it as a stranger and ask of every number and
every `(…)` placeholder — *which artefact is this derived from, and did I read that artefact's real
key?* The 851→2631-byte rewrite took one pass; the two mis-reads above survived **three** runs
before being caught, because the output looked complete.

## Rules

- **Derive every number from an artefact, and name the artefact.** A coverage claim without a file
  behind it is the over-claiming RULE 0 exists to stop.
- **Never dress a negative as a positive** (`"all steps completed ✅"` on an empty run — the exact
  failure RULE 41 was written for). Equally: never pad a negative with Low/Info noise (RULE 10).
- **Do not report `N/A` as coverage.** "wpscan: target is not WordPress" is a correct skip and
  belongs in the *boundary* section, not the *tested* section. Mixing them re-creates the
  false-completeness the coverage math
  (`references/premature-negative-and-coverage-math.md`) exists to prevent.
- **Length is a symptom, not the goal.** 851 bytes was too short because it omitted derived data,
  not because a number was missed. A negative report with a small surface can still be short — the
  test is whether a reader can answer *"what was tried, what was refused, and where is the proof."*
