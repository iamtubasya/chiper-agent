# 03 — Routing detail

## Live finding → atlas (the common case)

1. Stage it the moment you notice it, not at the end (you will forget the detail).
2. At the cadence point, run `dedupe --atlas <atlas>/references`.
3. Distil with `poc-corpus-to-technique-atlas` Mode B. That pipeline is authoritative for:
   classify → pull the *method* → filter malware/scam → dedupe → per-class file + `00-INDEX`.
4. `promote --id N --atlas <atlas>/references`.
5. Append a **pointer line** to the owner skill (append-only, never a rewrite):
   `- \`references/<class>.md\` §<technique> — <one line>`

## A site URL → its own skill

Use `site-to-skill-mirror` **Mode A**. Do not hand-copy pages, and do not run it through the atlas
pipeline — Mode A owns generator fingerprinting, entity normalisation, layout, the index, the
additive cross-link step, and the verify step (readable files, YAML still parses, counts match).

Typical invocation pattern (see that skill for the exact flags):

```bash
python "$LOCALAPPDATA/hermes/scripts/…mirror_site_to_skill.py" <url> <outdir>
```

Then: verify readability, verify the new SKILL.md YAML-parses, and cross-link the owner skill.

## A corpus / an oversized shelf → the atlas

Use `poc-corpus-to-technique-atlas` **Mode B**. Trigger phrase examples from that skill:
"extract the techniques from this corpus", "80k PoCs but not all extracted", "the reference dir has
grown too large to read".

## When both apply

If a URL contains a corpus (a blog with a technique table, a write-up index), mirror the site
**first** (Mode A, so the raw material is preserved and verifiable), then distil the interesting
methods out of it with Mode B. Do not skip the mirror step — it is what makes the distillation
re-checkable later.
