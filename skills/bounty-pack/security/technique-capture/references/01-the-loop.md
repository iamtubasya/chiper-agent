# 01 — The loop, end to end

## Why a trigger was the missing piece

Everything downstream already existed:

| stage | owner | what it does |
|---|---|---|
| learn from a **URL** | `site-to-skill-mirror` Mode A | fingerprint generator → normalize → layout → 00-INDEX → create the skill → cross-link owner skills → verify |
| learn from a **corpus** | `poc-corpus-to-technique-atlas` Mode B | classify → pull the method → filter malware → dedupe → per-class files + 00-INDEX |
| the **shelf** | `poc-technique-atlas` | ~1,950 techniques across class files, read one per phase |

What had no home: *"I just learned something during this engagement — where does it go?"* That is
this skill. It is a router plus a ledger, deliberately small.

## Lifecycle of one technique

```
new (staged) --dedupe--> already covered?  --> merge into the existing entry instead
                       \-> genuinely new   --> distil (Mode B) --> atlas class file
                                                              --> owner-skill pointer
                                            --> promoted
                       \-> not reproducible --> rejected (with a reason)
```

## Where things are written

| artefact | location | written by |
|---|---|---|
| staging ledger | `<staging_dir>/techniques.jsonl` | `technique-log.py` |
| atlas class files | `<atlas>/references/<class>.md` | the atlas pipeline (Mode B) |
| atlas index | `<atlas>/references/00-INDEX.md` | the atlas pipeline |
| a mirrored site skill | its own new skill dir | `site-to-skill-mirror` Mode A |
| owner-skill pointer | the owner skill's SKILL.md (append-only) | you, after distillation |

## Cadence (pick one and stick to it)

- **Per engagement, at the end** — cheapest, batches the work, keeps the ledger from interrupting the
  audit.
- **Per N new techniques** (e.g. every 5 staged) — keeps the ledger short.
- **Per URL/corpus on demand** — the user-driven path.

Do **not** distil mid-audit. Capturing is cheap; distilling is not, and the audit is the priority.
