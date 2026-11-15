# Verification recipe — accounting / bookkeeping app business logic

Verified against a live UK tax (Making Tax Digital) app, 2026. Patterns generalise to any app that
turns user entries into period totals + export files.

## Principle: ground truth is the export, not the UI

Read the page and you get pagination, CSS-truncated figures and RSC noise. Download the
authoritative export and diff it against what you submitted. For xlsx, shared strings must be
resolved (`t="s"` cells index into `xl/sharedStrings.xml`) or every cell prints as a number:

```python
import zipfile, io, re
z = zipfile.ZipFile(io.BytesIO(export_bytes))
strs = re.findall(r'<t[^>]*>(.*?)</t>', z.read('xl/sharedStrings.xml').decode(), re.S)
for rn, body in re.findall(r'<row[^>]*r="(\d+)"[^>]*>(.*?)</row>', z.read('xl/worksheets/sheet1.xml').decode(), re.S):
    cells = []
    for m in re.finditer(r'<c[^>]*?r="([A-Z]+)\d+"([^>]*)>(.*?)</c>', body, re.S):
        attrs, inner = m.group(2), m.group(3)
        v = re.search(r'<v>([^<]*)</v>', inner)
        val = v.group(1) if v else ''
        if 't="s"' in attrs and val.isdigit(): val = strs[int(val)]
        cells.append(val)
    print(rn, ' | '.join(cells))
```

## Test matrix

### (a) Precision / rounding — minor-unit storage
Add `0.01` three times; assert the stored total is **exactly `0.03`** (integer-penny storage shows
no float drift). Assert net = income − expenses to the penny.

### (b) Period (tax-year / fiscal-year) boundary mapping — the classic off-by-one
Give each boundary case a **unique value** so you can find it later, then read back which export
year contains it. For a 6 Apr–5 Apr tax year:

| entry date | expected year |
|---|---|
| <start−1 day> | previous year |
| <start> | current year (first day) |
| <end> | current year (last day) |
| <end+1 day> | next year (first day) |

Then per-year export totals must equal the sum of their members. **Absence of boundary leakage /
double-count is a strong positive result** and worth stating explicitly.

### (c) Idempotency
Replay the same submission id (the app sends `_1_submissionId`) — the second must dedupe, not
double-count.

**You cannot replay a hand-built body for this.** On a React-bound form action a reconstructed
request returns `500 + opaque digest` (bound args), which is indistinguishable from a refusal —
see §Race in the parent SKILL.md. Capture the app's OWN request instead:

```python
cap = {}
def on_req(req):
    if req.method == "POST" and "/app/" in req.url and "submissionId" in (req.post_data or ""):
        cap.update(url=req.url, headers=dict(req.headers), body=req.post_data)
pg.on("request", on_req)          # Playwright network event; req.post_data carries FormData/multipart verbatim
# ...fill and submit the real form once, then:
for i in (1, 2):
    ctx.request.post(cap["url"], headers={k: cap["headers"][k] for k in
        ("content-type", "accept", "next-action", "next-router-state-tree") if k in cap["headers"]},
        data=cap["body"])          # ctx.request shares the browser session cookie jar
```

Observed dedupe refusal (a **pass** — quote it):
`{"error":"This entry was already sent. Check the list before adding it again."}`
Both replays rejected, entry count unchanged.

> Prefer `page.on("request")` + `req.post_data` over a JS `fetch` monkey-patch: an init-script hook
> can silently be missing (a later `window.__drain` call then throws), and it misses native form
> POSTs entirely.

### (d) Input validation sweep
Type-vs-category mismatch, unsupported precision (`10.555`), negative, zero,
`999999999999999999`, empty, `1e5`, `NaN`, `Infinity`, Arabic-Indic digits, `1';DROP--`,
`<img src=x>`, padded spaces. Expect: hard rejects on all but the last (lenient-but-correct
parsing of `1,000.00` / `£100` / ` 100 ` is a hardening note, not a bug).

### (e) Rounding batch
100 × `£0.01` for slow-drift checks over large row counts.

### (f) Ownership share — is it date-effective?
A single scalar share with no effective-date field cannot represent a mid-year or mid-month
change of ownership. Test: seed entries dated before *and* after a hypothetical transfer date,
read the tax-year totals at 100%, set the share to 50% through the real form, read again. If
the pre-transfer entries are halved too, the app cannot express a transfer and every option
misstates half the year. Report as a product-correctness / tax-accuracy gap, low severity,
self-scoped — not access control. (Detail in `uk-property-tax-compliance-review.md`.)

### (g) Statutory ceiling / basis check
For UK property income, cash basis is HMRC's default but is **disapplied once cash receipts
exceed £150,000** in a tax year. Push one year's receipts well past that with a single entry and
look for a warning, an accruals option, or any mention of the figure. Silence = gap.

### (h) UI-hidden enum differential
Extract every option key the client filters out of a `<select>` (e.g. keys flagged `nrlOnly`),
inject each as an `<option>`, submit through the real form, and record the server's response per
key. Verify acceptance against the **export**, not the closed modal. One key accepted out of N
is a validation-asymmetry finding; all N rejected is a strong positive.

### (i) Output-file sink check before calling anything a finding
A user value appearing raw in an exported file is not a finding until the sink is checked:
CSV → is there an apostrophe prefix (parse with `csv.reader`, not eyeball — a quoted field
starting with `"` makes a naive `startswith("'")` check lie)? XLSX → is the cell `t="s"`, or
does the sheet contain `<f>` formula elements? PDF → never a sink. Full chain and the
cross-user guard matrix in `uk-property-tax-compliance-review.md`.

## Fields captured from a real transaction form (for reference)
```
_1_submissionId=<uuid>   _1_propertyId=<uuid>   _1_type=income|expense
_1_category=turnover|<hmrc-key>   _1_amount=950.00   _1_txnDate=YYYY-MM-DD
0=[{},"$K1"]
```

### (f) Export formula-injection — verify by CELL TYPE, not by raw text

The tempting false positive: set a description to `=2+2`, download the xlsx, grep
`sharedStrings.xml`, see `<t>=2+2</t>`, and report "formula injection survives into the export".
**That is wrong.** Check the cell's type before claiming anything:

```python
# a formula cell is a <c> containing an <f> element:
#   <c r="D6"><f>=2+2</f><v>4</v></c>
# a TEXT cell references the shared string:
#   <c r="D6" t="s"><v>11</v></c>
sheet = z.read('xl/worksheets/sheet1.xml').decode()
formula_cells = re.findall(r'<f[ >]', sheet)      # must be > 0 for injection to be live
text_cells    = re.findall(r't="s"', sheet)
```
`t="s"` = shared string = Excel treats it as **text**, no execution. A raw `=` sitting in
`sharedStrings.xml` proves nothing on its own. On Quarterwise the export had **0** `<f>`
elements — the class was inert on the xlsx path, and the finding was downgraded to a
defence-in-depth note ("the CSV path applies an apostrophe guard, the XLSX path does not;
hoist the guard into the data layer"). Do not report the raw-string version.

**CSV guard must be verified AFTER parsing, not by eyeballing the line.** A field containing
commas or quotes is wrapped in quotes, so the raw line starts with `"` and a naive
`field.startswith("'")` returns False even when the guard is correctly applied:

```python
row = next(csv.reader(io.StringIO(csv_text)))
guarded = row[0].startswith("'")     # correct: apostrophe is inside the quoted field
```

**Test guard COMPLETENESS, not just `=`.** Payloads that Excel/LibreOffice/Sheets may evaluate:
`=` `+` `-` `@`, a leading TAB, and a leading CR. Send each as the display name (or any
field that reaches the export) and record what comes back. On Quarterwise all six were
prefixed with `'` after correct CSV quoting — a complete mitigation, i.e. a **negative**, not
a finding. Writing up `=` alone would have been a partial and misleading report.

## Auth-hardening observations worth a vendor one-liner (NOT findings)
- **Client-posted device fingerprint** (`fph`: deviceId, timezone, screen px, UA, public IP) —
  untrustworthy for security decisions; privacy/telemetry note only, unless a decision actually
  depends on it.
- **MFA enrolment that requires the account password** before revealing the TOTP secret
  ("a stolen session cannot do it") is a *positive* design — call it out as such.
- **Sensitive ID save gated on a fresh MFA code** (e.g. national-insurance number) is a positive.
- Unhandled `500` on absurd input with an **empty body** = info only (no stack, no oracle).

## Provider-credential-gated flows
Tax filings / bank feeds / KYC final steps sit behind credentials you legitimately do not have.
Confirm the *gate chain* (e.g. 2FA → ID saved → provider authorisation) and report the untestable
tail as a **coverage gap**, not a finding.
