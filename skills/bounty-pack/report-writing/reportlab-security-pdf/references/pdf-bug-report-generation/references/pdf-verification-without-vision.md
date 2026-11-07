# Verifying a generated report PDF without vision

When `vision_analyze` is unavailable (connection error, retried twice, still failing), you must not
ship an unverified PDF and you must not claim it "looks clean". Two mechanical checks replace the
eyeball, and one of them has a built-in false positive you should not chase.

## 1. The authoritative check — `qa_pdf_layout.py`

```bash
python ~/.chiper/skills/bounty-pack/pdf-bug-report-generation/scripts/qa_pdf_layout.py \
  Report.pdf --margin-mm 19.05
# -> pages: 6
# -> layout: clean (no stranded headings, no margin overflow, no overlap)
```

`--margin-mm 19.05` matches `MARGIN = 54.0` pt in `templates/report_style_structured.py`. If you
change MARGIN, change this flag — a mismatch reports false overflow. This script is the verdict.
Everything below is corroboration, not a replacement.

## 2. Content assertions — every claim-critical string must survive rendering

Layout can be clean while a table cell silently truncated. Assert on extracted text:

```python
import pymupdf
d = pymupdf.open("Report.pdf")
t = "".join(p.get_text() for p in d)
print("pages:", len(d), "chars:", len(t))
for k in ["<endpoint-1>", "<endpoint-2>", "<error-code-A>", "<error-code-B>",
          "<custom PII string used as proof>", "What this is NOT", "CVSS", "12 / 12"]:
    print(("OK  " if k in t else "MISS"), k)
```

Pick assertions that would falsify the report if missing: endpoint paths, the exact error codes you
cite, the distinctive nickname you planted as PII proof, the severity number, and the
"What this is NOT" heading (the honesty section — if that is missing, the report overclaims).

## 3. The footer false positive — ignore it, do not "fix" it

A raw block-vs-margin scan flags **every page**:

```python
# DO NOT treat this as a bug
M, W, H = 54.0, 595.28, 841.89
for i, p in enumerate(d):
    for b in p.get_text("blocks"):
        if b[1] > H - M + 18:      # y0 below the bottom margin
            print("OVERFLOW p%d" % (i+1), b[4][:60])
# -> OVERFLOW p1..p6 :: '<report title>'   <-- always, by design
```

`_build()`'s `on_page` callback draws the running footer at `y = MARGIN - 18` and the page number at
the same offset — i.e. deliberately *outside* the text frame, which is normal document design. The
flagged block is the title string on every page. So:

- If the only "overflow" blocks are the repeated title/footer at `y1 > H - M`, layout is fine.
- Investigate only blocks flagged on **some** pages, or whose text is body content.

This is the same discriminator as the SPA-catch-all and body-diff rules: a signal that appears
identically on every sample is the template, not the fault.

## 4. Verify the Gmail draft, not just the "draft created" response

The API returning an id proves nothing about the draft's contents.

```python
d = api("drafts/" + draft_id)          # GET users/me/drafts/{id}
m = d["message"]
h = {x["name"].lower(): x["value"] for x in m["payload"]["headers"]}
assert h["to"] == "security@vendor.example"
assert "DRAFT" in m["labelIds"]        # proves not sent

def walk(p, out):
    if p.get("filename"):
        out.append((p["filename"], p.get("body", {}).get("size")))
    for sp in p.get("parts", []) or []:
        walk(sp, out)
parts = []; walk(m["payload"], parts)
# -> [('Report.pdf', 15435)]   must equal os.path.getsize(pdf)
```

Check all four: recipient, subject, `labelIds == ['DRAFT']`, attachment filename **and byte size
matching the file on disk**. A size mismatch means the attachment was truncated or the wrong file was
attached.

Building the raw message that works:

```python
from email.message import EmailMessage
msg = EmailMessage()
msg["From"] = SENDER; msg["To"] = RECIPIENT; msg["Subject"] = SUBJECT
msg["Date"] = formatdate(localtime=True); msg["Message-ID"] = make_msgid(domain="gmail.com")
msg.set_content(body)
with open(pdf, "rb") as f:
    msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf))
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
# POST users/me/drafts with {"message": {"raw": raw}}
```

## 5. Discipline

- A PDF that passed `qa_pdf_layout.py` **and** the content assertions is verified; say so, and say
  *which* checks ran. Do not say "looks professional" when you did not look.
- If vision is down and the layout checker is unavailable too, the honest output is "layout
  unverified — checker unavailable", not silence.
- One finding, one email. Two findings on different hosts/mechanisms go out as two separate drafts,
  each with its own PDF — merging them invites a "same root cause" downgrade of the stronger one.
