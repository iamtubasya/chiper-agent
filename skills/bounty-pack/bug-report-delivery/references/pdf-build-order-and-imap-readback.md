# Draft read-back traps + PDF build order (single-finding deliverable)

Two lessons from the djangoeurope F1 deliverable (2026-10-25) that cost real cycles. Both are about the
*transport*, not the finding.

## 1. IMAP read-back: normalise the subject, or you "fail" a draft that staged perfectly

`EmailMessage` folds a long `Subject:` header at ~78 chars, and the appended draft stores the fold as
embedded CRLF. `imap_tools` then hands back:

```
"[Security] Unverified domain ownership on domain onboarding\r\r\n (djangoeurope.com)"
```

An exact `m.subject == subject` comparison misses it and prints

```
APPENDED to [Gmail]/Draf
READ-BACK FAILED: draft not visible in folder
```

which reads as a staging failure. It is not — the draft is there, with its PDF, sha256 intact. The
expensive mistake is believing the false negative and re-appending (then deleting a good draft).

```python
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()
match = [m for m in mb.fetch(limit=8, reverse=True) if norm(m.subject) == norm(subject)]
```

When a read-back does look empty, do not conclude anything until you have listed the draft folders —
more than one exists on this account and they are easy to confuse:

```
['Drafts', 'INBOX.Drafts', '[Gmail]/Draf', '[Gmail]/Drafts']
```

Append to the locale folder (`[Gmail]/Draf` for an Indonesian Gmail) and verify there. And keep subjects
short: a parenthetical clause at the end of the subject is exactly what triggers the fold. Prefer

```
[Security] Unverified domain ownership on domain onboarding (djangoeurope.com)
```

over a subject that spells out the whole impact statement.

## 2. Build order: markdown first, generator second — never hand-splice Python

The instinct when `write_file` is not in the toolset is to build a reportlab generator with
`cat >> gen.py <<'EOF'` chunks. On this host that failed twice for reasons that have nothing to do
with the report:

- a heredoc containing Python squote-strings (`'''`,`'`) dies with
  `unexpected EOF while looking for matching '` — the shell, not Python, is parsing it;
- the output redactor turns an auth-header-shaped literal inside a written file into `AUTH=***`,
  which is *valid Python* and silently wrong (see the host-pitfalls section of SKILL.md);
- splicing a `part2.py` into a half-written generator to get around both produces more moving parts
  than the report itself.

What worked first try: **write the report as markdown, then generate.**

```bash
python ~/.chiper/skills/bounty-pack/skills/report-writing/reportlab-security-pdf/scripts/md_to_report_pdf.py \
    F1.md djangoeurope-F1-Medium-domain-claim.pdf \
    --header-left "djangoeurope.com - Finding F1" --header-right "Medium" --footer-right "F1"
# PDF: ... pages: 6
python .../pdf_layout_check.py djangoeurope-F1-Medium-domain-claim.pdf \
    --tokens "Page 1 of" "F1" "kernel.org" "RESEARCHER_NAME"
# problems=0
```

Markdown heredocs hold prose and fenced code — no shell-hostile tokens — so they chunk safely.

**Constraint that shapes the markdown itself:** `md_to_report_pdf.build_story()` has no markdown-table
branch. A line starting with `|` is swallowed by the paragraph branch, so a table renders as one run-on
paragraph and the layout checker cannot see it. Write comparison tables as **bullets**, e.g.

```
- **1. kernel.org** - real third-party domain - POST /domain/ 201 - zone live with AA=1 - POST /website/ 201.
- **C. control-unclaimed-de-9x7.com** - never claimed - nameserver answers REFUSED, no AA bit.
```

Same for the metadata block and the "observed result" matrix: bullet lists read fine in the PDF and
avoid the silent mangle entirely. Post-build gates that did catch real issues: `re.findall(r"&[a-zA-Z]+;")`
on the extracted text must be empty, and an Indonesian-word scan
(`\b(yang|tidak|adalah|dengan|untuk|laporan|temuan)\b`) must be empty when writing in English.
