# Product-correctness report shape (non-security deliverable)

Written after a second-pass tax/estimate review of a UK MTD landlord product (2026-09). The vendor
had already received the security report in their own thread; this document is the *separate* artifact
for the calculation findings. Verified on build: 4 pages (English version), `pdf_layout_check.py` →
`problems=0`, no watermark, no raw entities, every key figure present in the text layer.

## Language: every vendor-facing artifact is ENGLISH (hard rule for this operator)

His working notes, briefs and evidence files are Indonesian — that is fine and expected. Anything that
leaves the machine for the target/vendor is **English**: email subject, email body, PDF title, PDF
running header, PDF body, attachment filenames.

- **Never mix within one deliverable.** The failure that triggered this rule: a corrected, English
  body was sent with an Indonesian *subject* and an Indonesian *PDF*, because the PDF had been drafted
  with the same heading conventions as the internal notes and the filename was reused verbatim for the
  subject line. The operator caught it in review ("draft emailnya kenapa dalam bahasa indonesia") —
  after the draft had already been staged and the PDF built.
- **Derive the subject from the deliverable's purpose, not from the local filename.** Draft the English
  subject first, then name the file after it — not the other way round.
- **Keep the internal-language copy if it is useful for the operator to read**, but rename it so it can
  never be attached by accident: prefix it, e.g. `_INTERNAL_id_<name>.pdf`, and say in the handover
  which file is the vendor copy and which is internal-only.
- **Verify language programmatically before staging**, next to the layout check: extract the PDF text
  and assert none of the operator's common function words appear
  (`re.search(r"\b(yang|tidak|adalah|dengan|untuk|pajak)\b", text, re.I)` must be `None`), and re-check
  each staged draft's subject/body the same way. Cheap; catches the exact mistake above.


## Why separate, and how to label it

- Different audience (product/engineering, not security triage) and different severity language.
- A calculation bug inside a security-report thread gets triaged as a security item and argued about
  on the wrong axis. Separating them also lets the correctness report carry the "what is correct"
  evidence without bloating the security reply.
- Label so it cannot be mistaken for a vulnerability report (English, see the language section above):
  - PDF running header (ASCII only — `canvas.drawString` does not parse HTML entities):
    `Quarterwise - tax estimate accuracy review`
  - PDF footer: `<researcher> - product correctness review (not a security report)`
  - doc title + email subject: `Quarterwise - tax estimate accuracy review (second pass, not a
    security report)`
  - first paragraph states plainly: this is about whether the numbers are right, not access; no
    claim and no payment request attached.
- Send as its own draft with its own subject. Keep it out of the `Re: <vendor>` reply thread.
- Stage the *corrected* version by deleting the superseded draft in the same run that appends the new
  one (match on the old subject), then re-list the folder and assert every remaining vendor draft is
  English — do not leave two versions of the same report sitting in the mailbox for the operator to
  pick from.

## Section order that survived review

1. **Title + one-paragraph framing** — method, what it is not, no ask.
2. **Metadata table** — method sentence, date/time + timezone, IP used, accounts and test objects
   used, the external-system rule obeyed ("no connection/submission to the authority throughout"),
   path of the underlying evidence file. Same discipline as the security report.
3. **Summary table** — one row per item: id, finding, *direction of the error*, is it visible to a
   user?, who is affected. "Direction of the error" (overstates vs understates the number) is the
   column that makes an accountant act; add it explicitly.
4. **One section per item** — what happens, the exact scenario (code block with the entries and the
   dates), a `product says / should be` table with the money difference, then "why it matters" and a
   one-line suggested fix. Quote the product's own panel text verbatim.
5. **"What is correct" section** — the hand-computed cases that matched to the penny, in a table
   (test / expected / product / verdict). Non-negotiable: a report with only defects reads as an
   attack. Example rows that landed well: personal-allowance taper (£120k → taxable £115,930, tax
   £38,832), additional rate (£130k → £44,253), public CGT calculator on three band splits
   (£28,218 / £30,164 / £42,618), 6 Apr / 5 Apr period boundary.
6. **Honesty limits** — what could not be tested and why (no connection to the tax authority, a
   value-level period split that only exists at filing time, single-source scenarios).
7. **Suggested fixes table** — one row per item, short imperative sentences.
8. **Rule references** — cite the statute/manual family in a small-font footer, not inline.

## Two items that generalise beyond this vendor

- When the product's own copy (marketing page, FAQ, pricing table) makes a claim the arithmetic does
  not support, quote that copy in the item — it converts "I think this is wrong" into a
  contradiction the vendor can act on. Record the mismatch as a *disclosure* item, not a bug.
- Items whose error direction is "overstates the charge" should be grouped and stated as such in the
  summary: for a bookkeeping product that is the more serious direction, and it is the one a support
  inbox will recognise from user complaints.
