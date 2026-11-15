# The proofread structure every report now uses (from a real vendor rejection)

## Where this came from

On 2026-10-27 a vendor triager (Paul Sharpe, Deeper Network) returned a batch of
reports not with a triage verdict but with a formatting complaint, and attached a
`Summary.docx` as the model to copy. Verbatim, from three separate replies:

> "Can you please submit the BUG Report in a properly formatted word document.
> Reading the above is very difficult. You can copy the format in the attached
> file for your first BUG REPORT."

> "I have had to reformat all of them. Next time, please consider the reader.
> Dense text is very difficult to read. Please use bullet points and numbered
> lists, Please separate sections properly"

> "Please consider using numbered lists and bullet points. ... This here is also
> multiple sections bundles into one paragraph. This should be:"

Two things follow. First, presentation is a delivery gate, not a nicety: the
reports were semantically fine and still came back unread. Second, the fix is
mechanical, so it belongs in a template rather than in good intentions.

## The skeleton (copy this order, do not improvise)

| # | Section | What goes in it |
|---|---------|-----------------|
| 1 | **Title** | One sentence, specific. Name the actor + the effect, not the CWE. |
| 2 | **Summary** | 2 to 4 short paragraphs. What happens, why it is wrong, what you observed. One idea per paragraph. |
| 3 | **Affected component** | Bullets. Host, route, version, build, commit, file paths. Precise enough that an engineer can open the file. |
| 4 | **Steps to reproduce** | `Step 1.` … `Step N.` each followed by its code block indented under it. Must run end to end with no missing key. |
| 5 | **Expected result** | What correct behaviour looks like. Cite the product's own strings, docs, or policy where they prove intent. |
| 6 | **Actual result** | What the server actually did. Facts only. |
| 7 | **Attack scenario** | Numbered attacker steps. **State the precondition honestly in one line** ("the attacker needs X"). |
| 8 | **Result** | One or two sentences: what the attacker ends up holding. |
| 9 | **Impact** | Bullets: who loses what. Then two labelled paragraphs: **What this is NOT** and **On severity**. |
| 10 | **Evidence** | Table of runs (run / input / response / timestamp). Mention where raw captures are. |
| 11 | **Figure** | One rendered screenshot of the decisive request/response pairs. |
| 12 | **Recommended remediation** | Numbered, concrete, one change per item. Include the cheap version and the structural version. |
| 13 | **Scope and conduct** | Bullets: in-scope confirmation, accounts owned, volume used, source IP, disclosure status. |

The two paragraphs in section 9 are the credibility engine. **"What this is
NOT"** stops the triager from reading more into the finding than you proved.
**"On severity"** maps your claim onto the programme's own published tier table,
states where you deliberately did not inflate, and names the single condition
that would move it up. Vendors argue with those two paragraphs far less than
with a severity number alone.

## Progressive disclosure: PDF carries the detail, the e-mail carries the shape

The e-mail body uses the same order but is not a transcription:

- Same 13 sections, numbered `1.` to `10.` (Evidence/Figure collapse into one
  closing line that says the PDF has them).
- Body indent 3 spaces, step continuation aligned under the step text
  (`Step 2. ` is 8 chars, so continuation indents to 11), code blocks at 15.
- Wrap at 76 columns. Never let a prose line exceed 78.
- Always end with the PDF pointer, thanks, signature with the operator's real
  name and contact.

Generate it with `scripts/render_email_body.py` rather than writing prose and
wrapping by hand. Blocks are typed, wrapping is deterministic, and the renderer
inserts the blank lines that separate sections. Hand-wrapping plus a later
re-wrap pass is what merged three bullets into one paragraph and turned an
aligned `Field : value` block into a run-on sentence.

## Typography for the PDF

Use `templates/report_style_structured.py` (`MARGIN = 54` pt = 19.05 mm, so the
layout gate runs with `--margin-mm 19.05`). It exposes:

- `P`, `H2P`, `H3P`, `BUL(t, lvl)`, `NUMB(n, t)`, `CODE_BLOCK`, `CODE_IN`,
  `dt(rows, widths)`, `kv(pairs)`, `note(label, text)`, `SP(n)`, `make_docs`.

Measured indents that read correctly (verified on the Yarbo reports): body at
x=60, bullet glyph 63 with text at 77, step number 62 with text at 84, code
under a step at 90. Keep table widths summing to `<= FRAME_W` (487 pt at this
margin).

## Checklist before staging anything

```python
# 1. every section present in the PDF text
need = ["Summary", "Affected component", "Steps to reproduce", "Expected result",
        "Actual result", "Attack scenario", "Result", "Impact",
        "Recommended remediation", "Evidence"]
assert all(s in pdf_text for s in need)

# 2. the e-mail carries the same skeleton and no line is unreadable
assert all(s in body for s in ["1. Summary", "3. Steps to reproduce", "5. Actual result",
                               "8. Impact", "10. Suggested fix"])
assert max(len(l) for l in body.split(chr(10))) <= 80

# 3. honesty furniture survived the rewrite
assert "What this is NOT" in pdf_text and "What this is NOT" in body
assert "What this is NOT" in pdf_text.replace(chr(10), " ") or "What this is NOT" in pdf_text

# 4. layout gate
# python scripts/qa_pdf_layout.py out.pdf --margin-mm 19.05   -> must print "layout: clean"
```

Rewrite the finding, do not patch it. A generator that was authored as prose
paragraphs cannot be converted into a numbered list by string surgery; build the
new one from blocks and delete the old file.

## The other lesson from that thread

The vendor also complained that the same finding was described in a paragraph
where a list was obviously correct, and that "multiple sections" were bundled
into one paragraph. When you write the Summary, ask per sentence: is this the
same idea as the previous sentence? If not, it is a new paragraph. If it is a
sequence of actions, it is a numbered list. If it enumerates properties, it is
bullets.
