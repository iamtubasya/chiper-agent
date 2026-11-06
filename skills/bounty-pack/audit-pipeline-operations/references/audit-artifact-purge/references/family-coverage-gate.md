# Family coverage-gate strengthening

The other shape of "strengthen the skills": not one technique, but a **capability challenge
aimed at a whole family**. "Kamu kurang kuat utk temuan bug critical" is a statement about 59
`hunt-*` skills, not one.

Worked instance: 2026-10-26, `hunt-*` family, four structural gates, **3/59 → 59/59** on all
four, with 216 verified CVE IDs landing in the family.

Same shape as a purge: enumerate → classify → act with a manifest → verify both halves. The
difference is that the "disk" is a skill family and the "artifacts" are missing gates.

## 1. Measure before promising

One grep per gate, print the number. "56 of 59 skills lack the minimum-probe gate" is a plan;
"I'll make it stronger" is a vibe.

```bash
cd ~/.hermes/skills
for gate in "Minimum 5 probes" "Gate 0 Validation" "Eskalasi wajib" "2026 sweep"; do
  printf "%-22s %s/%s\n" "$gate" \
    "$(grep -l "^## $gate" hunt-*/SKILL.md 2>/dev/null | wc -l)" "$(ls -d hunt-*/ | wc -l)"
done
```

**Pick the blocking gate first and say why.** Coverage gates precede technique content:
without a minimum-probe gate, new techniques can be skipped silently and a "0 temuan" claim
stays unverifiable. This operator approved exactly that ordering ("Tahap 1 tutup lubang
coverage dulu, Tahap 2 isi teknik") and then said "Ya" to proceed.

## 2. Extract the template from the skills that already have it

Never invent a format. Read the complete exemplars verbatim and copy their heading text, table
columns, and closing rule sentence. Consistency across N files is what keeps the gate
greppable in the next audit — a per-file heading variant makes the verification grep silently
under-count.

## 3. Author per-item content, not one generic block

A `hunt-business-logic` probe set and a `hunt-websocket` probe set share a table shape and
nothing else. Author each class's probes from that class's own crown jewels.

### Anti-fabrication rule (non-negotiable for technique content)

When a sweep section needs CVE IDs, **every ID must come from a live lookup** — NVD, GitHub
Security Advisories, vendor advisories, WPScan/Patchstack, OSV. A plausible-looking
`CVE-2026-XXXXX` that was never fetched is worse than no CVE: it is a hallucinated fact a
future session will cite as verified. Search first, author second. If a class has no verifiable
2026 CVE, write the sweep from *technique patterns* and say so.

Capture the **lesson** per item, not just the ID. "CVE-2026-79630: check `product_id`, not the
displayed name" transfers to the next target; "CVE-2026-79630 exists" does not.

## 4. Bulk-insert: idempotent + anchor-based + manifest-logged

```python
# three rules that make a 59-file insert safe
if "## <Gate>" not in text:                    # 1. skip-if-present -> re-run always safe
    i = next((text.find(a) for a in           # 2. semantic anchor, never a line number
              ("## Eskalasi wajib", "## Related Skills & Chains",
               "## Real Impact Examples") if text.find(a) > 0), len(text))
    text = text[:i] + block + text[i:]
log.write("UPDATED|%s|+M5+G0\n" % name)        # 3. per-file manifest -> auditable, resumable
```

**Write the script to a file and run it** (`python script.py`). Never an inline heredoc: long
inline commands get blocked by the hardline parser on this host, and heredocs mangle escapes.
Clean the scratch script when done.

## 5. Verify by re-running the SAME grep, then spot-check

Report the before/after table, not "done". Spot-check 3–5 rendered files end-to-end — does the
table render, does the anchor order still read correctly. A count that went 3→59 proves the
insert ran; only reading a file proves it landed well.

## Pitfalls

- **Multi-class skills need a cross-class probe set, not one class's.** `hunt-misc` covers 225
  public reports across many classes; giving it one class's 5 probes would be wrong. Its block
  is a polyglot burst that closes four classes at once, with a "kelas yang ditutup" column.
- **A skill that already has the gate under a different heading is not missing it.** Check for
  both `## 2026 sweep` and `## 2026 techniques` before deciding to append — 33 of 59 already
  had one of the two.
- **Expect a second pass.** The first insert left 9 skills with no authored block and 1 with a
  failed anchor match; a second targeted script closed them. Budget for it rather than trying
  to be exhaustive in one script.
- **Don't stop at the count.** The deliverable is per-class content a future session can act
  on, not a uniform heading across N files.
- **Cross-link the family to the consumer skill.** The 2026 sweeps only pay off if the skill
  that reads them knows they exist — after the insert, verify the consumer's class list and the
  family's sweep sections point at each other.

## Related

- `security/report-gotchas` — the consumer side: per-class proof bar + AI-slop detector, and
  the skill that owns this procedure's output.
- `security/technique-capture` — the single-technique learning loop this complements
  (user-owned; read it, do not edit).
- `security/poc-corpus-to-technique-atlas` — when the input is a corpus rather than a family.
