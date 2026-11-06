---
name: technique-capture
description: "The learning loop: capture a technique learned during an engagement (or from a URL/corpus), stage it, dedupe it against the atlas, distil it, and land it in poc-technique-atlas plus the owner skill. Use when an audit surfaces a method worth keeping, when given a site link to mine into a skill, or when asked 'can the audit learn new things' / 'add this to the skills' / 'extract this page into a skill'."
category: security
metadata:
  hermes:
    tags: [security, learning, technique-atlas, skills, distillation, capture, growth]
---

# Technique capture — the learning loop

Ties together three pieces that each already exist, and supplies the one that was missing: the
**trigger**.

```
   engagement finding / a site URL / a corpus
                    |
        [ technique-log.py  <<< THIS SKILL ]      stage + dedupe + decide
                    |
      +-------------+----------------------------+
      |             |                            |
 site-to-skill-   poc-corpus-to-            (already-covered)
 mirror (Mode A)  technique-atlas (B)        -> merge, do not re-add
      |             |
   new skill    atlas class file  --->  owner skill cross-link
```

> **Additive.** This skill creates nothing that other skills depend on, and changes no pipeline
> script. It stages candidates in a ledger and routes them. Skip it entirely on a normal run.

## When to load

- An engagement produced a **method** you have not seen in the atlas ("that trick was new")
- You are given a **site link** to mine into a skill
- You are given a **corpus** (PoC dump, nuclei templates, a shelf that has outgrown itself)
- You want to borrow **mechanisms from an external project** under a licence (copyleft repo, skill
  pack, defence guide) — the clean-room rules decide what may be reused and how
- The user asks: *"can the audit learn new things?"*, *"add this to the skills"*,
  *"extract this page into a skill"*, *"80k PoCs but not all extracted"*

## The three entry points (pick by input)

| input | route | do NOT |
|---|---|---|
| a **live finding/method** from an engagement | `technique-log.py add` → `dedupe` → distil | do not append straight into an atlas class file |
| a **site URL** | `site-to-skill-mirror` Mode A (it owns the extractor + layout + index) | do not hand-copy pages |
| a **corpus / oversized shelf** | `poc-corpus-to-technique-atlas` Mode B | do not dump payloads into a skill |
| an **external licensed project** | read for mechanism → re-implement → verify (see `references/04-clean-room-adoption.md`) | never copy source, prose, rule bodies or identifiers into our library |

## The loop in four steps

```bash
S="$LOCALAPPDATA/hermes/scripts"
A="D:/data hermes/..."                          # wherever the atlas lives
L="<target>/_techniques"                        # the staging ledger

# 1. STAGE (refused without evidence) - one line per technique, as you find it
python "$S/technique-log.py" "$L" add --class rce --title "RSC flight-data tamper" \
      --evidence "GET / -> self.__next_f escaped; commit POST stored raw" --target host

# 2. DEDUPE against the atlas index before spending effort
python "$S/technique-log.py" "$L" dedupe --atlas "$A/references"

# 3. DISTIL with the atlas pipeline (Mode B), never by hand
#    -> writes/updates <atlas>/references/<class>.md

# 4. CLOSE the ledger entry
python "$S/technique-log.py" "$L" promote --id 3 --atlas "$A/references"
```

Trigger reference: `references/01-the-loop.md` · capture rules: `references/02-capture-rules.md`
· routing detail: `references/03-routing.md` · external/licensed sources:
`references/04-clean-room-adoption.md` · the ledger CLI: `technique-log.py <dir> verify`.

## The rules that keep this honest

1. **No evidence, no entry.** `technique-log.py add` refuses without `--evidence`. A technique you
   did not reproduce is a claim — the same rule that governs findings governs techniques.
2. **Dedupe before you distil.** If the class is already covered, the *technique* may still be new —
   `dedupe` distinguishes "class exists" from "duplicate of another staged entry".
3. **"Neutral over fabricated."** If you cannot verify a claim, record what you *did* observe and mark
   it `--confidence inferred`. Never write a technique you only half-understood.
4. **Methods, never payloads.** The atlas is a method shelf. No exploit bodies, no malware.
5. **Close every entry.** `promote` or `reject` with a reason — the ledger must not silently grow.
6. **Cross-link, don't duplicate.** When the atlas gains a technique, the owner skill gets a pointer
   line (append-only). The concept lives in one place.
7. **Licence is a boundary, not a vibe.** Before reusing anything from an external project, state its
   licence and pick the branch: private use (free) / re-implement clean-room (with a provenance header
   and a credit line) / do not adopt. Then **grep your new files for their identifiers and expect 0
   hits** — the verification is cheap and skipping it is the whole risk. Details in
   `references/04-clean-room-adoption.md`.

## Files / tooling

- `technique-log.py` (in `$LOCALAPPDATA/hermes/scripts/`) — the staging ledger; `verify` self-tests it.
- Companion skills it routes to: `site-to-skill-mirror` (Mode A), `poc-corpus-to-technique-atlas`
  (Mode B), and the shelf `poc-technique-atlas` (the destination).
