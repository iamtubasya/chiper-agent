# Renderer pitfalls — things that silently corrupt a reportlab deliverable

Learned building the Proton Lumo SSRF report (2026-10-25, 3-page report, 10 KB). None of these throw;
they all produce a PDF that *looks* fine and is wrong or missing content.

## 1. HTML entities leak as literal text

`Paragraph` accepts a small HTML-ish markup subset (`<b>`, `<i>`, `<font>`, `<br/>`) but it does **not**
decode HTML entities. Putting `&#8212;` or `&#8211;` or `&nbsp;` in the text renders the literal
characters `&#8212;` in the output PDF.

```
WRONG:  Paragraph("Lumo by Proton &#8212; in scope", style)   → "Lumo by Proton &#8212; in scope"
RIGHT:  Paragraph("Lumo by Proton \u2014 in scope", style)     → "Lumo by Proton — in scope"
```

If the build script is written through a shell heredoc, `\u2014` may be eaten before Python sees it —
define `EM, EN, NB = "\u2014", "\u2013", "\u00a0"` at the top of the script and concatenate.

## 2. Never build the script with a giant bash heredoc

A 100+ line `cat > build.py <<'EOF' … EOF` containing quotes, `$`, backticks, `<`, `>`, and triple-quoted
Python reliably dies with `unexpected EOF while looking for matching '` — and the partial file may be
left behind. Write the script with a file-writing tool (`execute_code` writing the file, or `write_file`),
then run it. This also makes the build reproducible, which matters because the PDF hash goes in the report.

## 3. Verify by extracting the text back out

`os.path.getsize() > 0` is not verification. Extract and read the first page before staging:

```python
from pypdf import PdfReader          # or PyPDF2
r = PdfReader("Report.pdf")
print(len(r.pages), r.pages[0].extract_text()[:600])
```

This is what catches entity leaks, missing tables and truncated appendices. Page count from
`grep -c '/Type /Page'` is unreliable — use the library.

## 4. Table width must be budgeted, not guessed

`SimpleDocTemplate` with `leftMargin=17mm, rightMargin=15mm` on A4 leaves ~178 mm of usable width.
Column widths that sum above that push content off the page silently. Budget the columns before writing
the rows; for a 4-column evidence table `62 + 11 + 13 + 74 = 160 mm` leaves room for padding.
`repeatRows=1` keeps the header on page 2+ — set it whenever a table can split.

## 5. Long monospace blocks

`Preformatted` does not wrap. Long collaborator-log lines and raw request dumps get clipped at the right
edge. Either `maxLineLength=` with short source lines, or pre-truncate the strings when building the
block (`re.sub(r'\s+', ' ', line)[:110]`). Check the widest line against the frame width before shipping.

## 6. Hash the finished artefact and put the hash in the report

Compute `sha256` **after** the final build, store it in the findings JSON, and cite it in Appendix.
Re-building changes the hash, so an out-of-date hash is a real defect in a disclosure package — recompute
and rewrite the findings record every time you touch the layout.
