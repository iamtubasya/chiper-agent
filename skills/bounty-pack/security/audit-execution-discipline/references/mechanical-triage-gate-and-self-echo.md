# The mechanical pre-report gate — and why a gate must never read its own echo

Session: 2026-10-09. Follows RULE 39 (fail-open finding gate, 2026-10-07). RULE 39 fixed the
*default* and the *label* problem in `finding_gate.py`. This session found the **next** failure:
even with the gate fixed, garbage still reached the report — because the records being scored were
**echoes of the gate's own output**.

## Part 1 — `triage_gate.py` (mechanical 7-question enforcement)

Operator wants the `triage-validation` skill's 7 questions **enforced, not advised**. New script
`~/hermes/scripts/triage_gate.py`, wired into the orchestrator as **E5** between `validate-findings`
and `report`:

```
0C-C7: aggregate → weaponize-gate → chain_builder | 0E: finding_gate v2 → validate-findings → TRIAGE GATE → passed-findings.json
0F: report-agent reads passed-findings.json ONLY; 0 PASS ⇒ explicit NEGATIVE report (never silence,
    never a fake "no findings" shell — see RULE 41)
```

Per finding it answers 7 questions and **PASS requires all 7 YES**:

| Q | Question | Signal used |
|---|---|---|
| Q1 | real impact on data / user / system / business-logic / funds | impact-class regex on the finding's own claim |
| Q2 | proven with a reproducible request/response | HTTP status line, JSON/HTML body, before/after, leaked value, `reproduc`, `step N` |
| Q3 | impact in the program's in-scope impact list | Q1 AND not hygiene |
| Q4 | chain reaches the impact (no dead step) | `not reproducible`, `unable to`, `theoretical`, `chain dead/blocked` |
| Q5 | NOT by-design / documented | `by-design`, `intended behaviour`, `per documentation` |
| Q6 | NOT only info / version / header | hygiene regex + ≥60 chars of real content |
| Q7 | NOT a tool error / empty output | `command not found`, `curl: … failed`, `timed out`, `traceback` |

Outputs: `triage.json` (per-question answers + failed list = audit trail), `passed-findings.json`
(the ONLY report input), `TRIAGE.md`. `--min-yes` defaults to 7.

## Part 2 — the defect: a gate that scores its own echo

**Symptom.** After `finding_gate.py` v2 was fixed, the real 83-record `gated.json` still produced
**22 PASS** (later 2) at 7/7 on the triage gate. Every one was junk (`# Vector 4: RCE/SSRF`,
`Output`, `Ref File`, `Payloads (20 loaded)`).

**Root cause.** The records were *not* the original findings — they were echoes of the gate's own
output that had been re-ingested:

```
{"title": "# Vector 4: RCE/SSRF",
 "text": "{\"title\": \"# Vector 4: RCE/SSRF\", \"text\": \"# Vector 4: RCE/SSRF\\n**Target**: …
          \\n**Tool**: curl\\n**Exit code**: 0\"}",
 "impacts": ["code-exec","ssrf"], "impact_score": 16, "has_evidence": true}
```

Three things conspired:

1. **The nested JSON *was* the proof.** Q2's "an actual JSON body" pattern matched the echoed
   `{…}` record itself; `"impacts":["code-exec","ssrf"]` handed Q1 its class for free.
2. **Labels survived JSON encoding.** `**Target**: … **Tool**: … **Exit code**: 0` are nested
   inside a string, so the line-anchored label strip never saw them.
3. **Gate metadata looked like content.** `- impact classes: code-exec`, `evidence present: True`,
   `"text":`, `` ``` `` fences — all of it scored.

The class of bug: **a gate that reads a file it (or a prior step) wrote will grade its own
scaffolding as signal.** Same family as RULE 39's "skip self-generated sources" and the
"dead dump" trap in RULE 25.

## Part 3 — the fix (proven)

Three helpers in `triage_gate.py`, applied before any regex:

1. **`unwrap()`** — if the record's `text`/`evidence` is itself JSON, peel inner keys
   (`text`, `evidence`, `description`, `details`, `body`, `poc`, `repro`) up to 3 levels; handle a
   list of records too. What is scored is the *original* finding, not the envelope.
2. **inline label strip** — `VECTOR_INLINE_RE` removes `vector N:` anywhere in a line (not just at
   the start), so a nested/encoded label cannot reintroduce the procedure name.
3. **`clean()` scaffold scrub** — drop lines matching gate/report metadata
   (`impact score|impact classes|evidence present|source|severity|verdict|reasons|drop_flags`),
   scrub JSON keys (`"title":|"text":|"impacts":|"impact_score":` …), drop "not-a-finding" titles
   (`Ref File`, `Reference`, `Payloads (\d+ loaded)`, `Output`, `Notes`, `Index`,
   `REPORT-WORTHY FINDINGS`, `Survivors`), strip `read_file(` calls and code fences, and require
   **≥60 chars of surviving content** (below that it is metadata, not a finding).

`finding_gate.py` v2 carries the same three ideas (`strip_labels` + `NOT_A_FINDING_TITLE` +
`SCAFFOLD_RE` + `dedupe`), so the two gates no longer disagree.

## Part 4 — measured result (same input both times)

| Input | finding_gate v2 | triage_gate | Report |
|---|---|---|---|
| 83 real garbage records (`gated.json`) | 0 REPORT / 2 DOWNGRADE / 81 DROP | **0 PASS / 83 BLOCK** | NEGATIVE |
| 1 real finding (IDOR + SSN in body) | 1 REPORT | **7/7 PASS** | written |

Before the session the old gate emitted **12 REPORT**; the pipeline is now `0`.

## Part 5 — control-pair discipline (extends RULE 0c)

Every gate change was validated with a **control pair**, never a single case:

- garbage: `# Vector 4: RCE/SSRF` (label + `Exit code: 0` only) → must BLOCK
- hygiene: `missing HSTS header (best practice)` → must BLOCK
- real: `GET /api/patient/2 → HTTP/1.1 200 … {"ssn":"…"} another patient PII, reproducible` → must PASS 7/7

A gate that cannot return 0 on a junk corpus is not filtering; a gate that fails the real one is
over-filtering. Assert **both** directions after any edit.

## Part 6 — making condition-triggered skills reachable without inflating the budget

Related, from the same session's skill-library audit: ~60 security skills were correct but
**unreachable** (no always-on phase referenced them). Fix = a **condition→skill router**
(`bb-audit-launcher/references/situational-skill-router.md`, wired into 0B `security-recon` Step 3d
+ a pointer in `reference-loader.md`), loaded **on demand** — not added to the always-on bundle,
which would blow the 120 KB phase budget. Rule of thumb: an always-on phase lists what runs *every*
engagement; everything conditional goes in the router and is loaded when its signal matches.

Same principle for helper skills (skill-management, humanizer): give them a row in the router
under the phase where they apply, or they stay list-only forever.
