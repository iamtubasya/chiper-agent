# The disclosure draft pipeline (1 finding = 1 draft = 1 PDF)

RULE 0 in SKILL.md says one finding gets its own draft and its own PDF. This file
is the harness that makes that structural instead of aspirational — it is the
difference between "the operator reminded me" and "the code cannot do otherwise".

Worked on two engagements (a 61-chain settlement protocol and a GRC SaaS). Both
ended with N standalone Gmail drafts, each carrying its own attached PDF, with the
attachments verified by hash after a read-back.

## Shape: one source of truth, two thin scripts

```
<engagement>/
  findings.json        # SOURCE OF TRUTH - every renderer reads this, nothing else
  <target>_pdf.py      # findings.json -> one PDF per LOW+ finding, into pdf/
  <target>_sync.py     # findings.json -> one draft per LOW+ finding, PDF attached
  gmail_draft.py       # optional low-level single-draft upsert
  drafts/              # rendered plain-text bodies (F1.txt, R3.txt, ...)
  pdf/                 # R1-Low-Relay.pdf, R3-Low-Relay.pdf, ...
  draft_state.json     # finding id -> {draft_id, subject, to, attachment}
```

Both scripts loop `findings.json` and key everything off the finding `id`. The
email body and the PDF are rendered from the same record, so they cannot drift.

Deriving both from one store is also what stops the "combinator" failure mode: there
is no code path that can emit two findings into one document.

## findings.json schema that has held up

```json
{
  "subject": "...", "scope": "...", "headline": "...", "updated": "ISO8601",
  "findings": [{
    "id": "R3", "sev": "LOW", "title": "...",
    "component": "exact URL / host / contract address",
    "cwe": "CWE-269 Improper Privilege Management",
    "obs": ["..."], "poc": ["commands + observed output, verified 3x"],
    "impact": ["..."], "fix": ["..."], "refs": ["..."]
  }],
  "positives": ["what is correct - makes the real finding credible"],
  "coverage": [{"status": "done|pending", "area": "...", "note": "..."}],
  "queue": ["next lead"]
}
```

- `coverage[]` is where NEGATIVE results and documented-behaviour dismissals live.
  A long honest coverage list is a deliverable, not clutter.
- `positives[]` is the same move the reportlab skill makes for correctness reports:
  listing what IS correct is what makes the one real defect believable.
- **Assert `component`, `cwe` and `poc` are non-empty for every draftable finding
  before building.** A loop that writes half-filled findings silently produces PDFs
  that render `-` for those fields. This happened; the fix is an explicit assertion
  in the pipeline, and saying so in the recurring-loop prompt.
- SKIP INFO: filter `sev in {"CRITICAL","HIGH","MEDIUM","LOW"}` on the way in. INFO
  findings get a `coverage[]` note and nothing else.

## Severity is a filter, not a label

Keeping INFO out of the draft path is what keeps the operator's inbox signal-dense.
The loop is told explicitly: severities CRITICAL/HIGH/MEDIUM/LOW only, everything
else recorded as coverage. Without that line the loop drafts the noise.

## The recurring loop, and why its prompt carries the rules

A long engagement runs as a cron job that executes one pass per tick. The loop runs
in a FRESH session with no memory of the engagement, so the prompt must be
self-contained and must restate:

- RULE 0 (one draft, one PDF, never combined) and the intro requirement
- the program's scope and out-of-scope list, verbatim enough to be actionable
- the hard rules (unauthenticated, low-volume, manual, no scanners)
- the exact file paths and the exact commands to run, in order
- **"do not add anything you could not reproduce 3x — log the negative instead"**
- the layout-checker gate and the requirement to rerun after a fix
- "do not ask the user anything"

Then the loop's `queue[]` becomes the next tick's worklist, which is how the
engagement keeps moving without a human driving each pass.

Observed payoff: the loop independently produced four standalone findings
(including a decommissioned-oracle documentation divergence and an unenforced
WebSocket auth control) while the interactive session was auditing contracts. It
also wrote its own helper scripts. Treat its output as a peer's work — but verify
every finding yourself before it goes out, exactly as you would your own.

## Cron scheduling trap (cost one lost loop)

`schedule="15m"` was accepted but created a **ONE-SHOT** job ("once in 15m") that
completed after a single run — `last_status: ok`, `state: completed`,
`enabled: false`. A recurring loop needs a cron expression:

```
schedule="*/15 * * * *"
```

After creating any recurring job, read it back and confirm `state: "scheduled"` and
a future `next_run_at`. If it says `completed`, the schedule was parsed as one-shot.
Also confirm a mid-life job that has already fired still reports a future
`next_run_at` — that is the only cheap proof it will fire again.

## Verification gates, in order

1. `pdf_layout_check.py <pdf> --tokens "Page 1 of" "<researcher name>"` → `problems=0`
2. entity scan `&[a-zA-Z]+;` empty · literal-markup scan `</?(b|i|u|font|br)>` empty ·
   `\bwatermark\b` absent
3. sync: attach and compare the read-back attachment's `sha256` to the local file
   plus a `%PDF-` magic check (`format="raw"`, not `"metadata"` — see SKILL.md
   rule 17)
4. re-list drafts and confirm exactly one per finding, each with an attachment

## Iteration loop

When a finding changes, re-render its PDF, then re-run the sync. Do not hand-edit a
draft: the store is the source of truth and the draft is derived. The sync is
keyed by finding id and by subject, so re-running is idempotent and cannot
duplicate.
