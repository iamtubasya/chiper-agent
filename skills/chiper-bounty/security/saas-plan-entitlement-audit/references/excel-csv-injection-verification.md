# Verifying the formula-injection class before you report it

The class is CWE-1236 ("CSV/Formula Injection"). It is the easiest class to **over-report**,
because "my payload appears raw in the export" looks like a win and usually is not.
Verify every export path, then state the residual as hardening — not as a finding.

## 1. Enumerate every export path first
A product commonly has 3+ sinks for the same user-controlled value:
  - **CSV** (dangerous — an unquoted cell starting with `=` executes when opened)
  - **XLSX** (dangerous only if the cell is *formula-typed*)
  - **PDF** (never dangerous — a PDF has no formula engine; the value is a text operand)
  - plus: HTML export, email body, JSON consumed by a spreadsheet script, adviser/reporting CSVs
Testing only the XLSX path and reporting it is the most common overclaim in this class.

## 2. XLSX: "raw in sharedStrings" is NOT execution
XLSX stores text once in `xl/sharedStrings.xml`; a cell points at it by index with `t="s"`.
Excel evaluates a cell only when the sheet contains a formula element `<f>`.

    # decisive check, after unzipping the export
    sheet = zip.read('xl/worksheets/sheet1.xml').decode()
    print("formula cells:", len(re.findall(r'<f[ >]', sheet)))   # 0 => nothing executes
    m = re.search(r'<c[^>]*r="D6"[^>]*>.*?</c>', sheet)
    print(m.group(0))    # t="s"  => text-typed, inert

So "`<t>=2+2</t>` is present in sharedStrings.xml" is **not** a vulnerability.
Only `<c ...><f>=2+2</f><v>…</v></c>` would be.

## 3. CSV: test the guard's COMPLETENESS, then parse the CSV properly
A correct guard prefixes an apostrophe to any cell whose first character could start a
formula. Test every dangerous lead character — spreadsheet parsers differ:

    payload                          expected in CSV            guarded?
    =1+1                            '=1+1                     yes
    +1+1                            '+1+1                     yes  (many forget this)
    -1+1                            '-1+1                     yes
    @SUM(1)                         '@SUM(1)                  yes  (and many forget this)
    <TAB>=1+1                      '=1+1                     yes  (control char stripped first)
    <CR>=1+1                       '=1+1                     yes
    =cmd|'/C calc'!A0              '=cmd|'/C calc'!A0        yes  (DDE; no neutering needed once quoted)
    =HYPERLINK("http://x","c")     "'=HYPERLINK(""http://…"" (apostrophe is the first
                                                 char of the CELL VALUE, after CSV quoting)

That last row is why eyeballing is wrong: the raw field *starts with* `"` (CSV quoting), so a
naive `field.startswith("'")` check reports guarded=False. Always parse:

    import csv, io
    row = list(csv.reader(io.StringIO(raw)))[1]
    assert row[0].startswith("'")            # guard is the first char of the cell VALUE
    assert row[0] == "'" + payload           # value otherwise preserved, not mangled

Cross-user reachability changes the story: a formula in the account holder's own name that
lands in a CSV their **adviser** downloads is stronger than one in their personal export.
Check who else reads the feed.

## 4. Decide honestly, then say so in the report
| Path | Value ends up as | Executes? | Verdict |
|------|------------------|-----------|---------|
| CSV  | `'=payload`, quoted | no | mitigated |
| XLSX | raw string, `t="s"`, 0 `<f>` | no | inert |
| PDF  | text operand | no | N/A |

If every path is safe the finding **is** "verified mitigated — not a reportable finding".
Say that explicitly, then give the vendor one line of residual hardening: the XLSX path does
not carry the apostrophe the CSV path carries, so its safety depends on the library's cell
typing; hoist the guard into the data layer so both exports inherit it.

Downgrading a claim you already made is a strength signal. One overclaimed finding costs the
reader the credibility for the findings that are real.

## 5. Related discipline
- Never use a third party as an oracle. If a credential issued by the target belongs to a
  different vendor's ecosystem, do not exercise it against that vendor — out of scope.
- "Round-trips untouched" is not impact. Impact = someone else can be harmed, or a control
  is bypassed.
