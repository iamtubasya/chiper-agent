# UK property-tax SaaS: compliance review + the "raw value ≠ finding" trap

Session-derived. Verified against live HMRC rules (Sept 2026) and a live MTD product.
Covers two things a normal authz sweep misses: (1) is the *tax arithmetic* right against
current rules, and (2) does a value that looks dangerous in an output file actually reach a
sink. Reusable on any UK bookkeeping / MTD / property-software target.

---

## 1. The formula-injection trap (read this before writing any CSV/Excel finding)

Seeing `=2+2` sitting raw inside a generated file is **not** a finding. Check the sink:

| Output | What "raw" really means | Executable? |
|---|---|---|
| CSV | Does the generator prefix `'`? | Only if no prefix |
| XLSX | Is the cell `t="s"` (shared string) or a formula `<c><f>…</f></c>`? | Only if `<f>` present |
| PDF | Text-showing operand — not a spreadsheet | Never |

Proof chain that flipped a "P4 finding" into a verified-negative:
- `xl/sharedStrings.xml` held `<si><t>=2+2</t></si>` → looked bad
- `xl/worksheets/sheet1.xml` cell was `<c r="D6" t="s"><v>11</v></c>` and the whole sheet had
  **0 `<f>` elements** → Excel reads `t="s"` as TEXT, never evaluates
- The CSV path *was* guarded: `'=2+2`

**Cross-user CSV guard matrix** (payload put in a field the *second* identity downloads, e.g.
an adviser's client list) — run all of these, then parse with `csv.reader`:

    =1+1        -> '=1+1        guarded
    +1+1        -> '+1+1        guarded
    -1+1        -> '-1+1        guarded
    @SUM(1)     -> '@SUM(1)     guarded
    <TAB>=1+1   -> '=1+1        guarded
    <CR>=1+1    -> '=1+1        guarded
    =cmd|'/C calc'!A0 -> guarded
    =HYPERLINK("http://x/","c") -> raw: "'=HYPERLINK(""http://x/"",""c"")"

**The parsing trap:** a payload containing a comma or quote makes the raw field start with the
CSV quoting character `"`, so a naive `field.startswith("'")` returns **False** and you will
falsely conclude the guard is missing. Always `list(csv.reader(io.StringIO(text)))` and inspect
`row[0]`. Correct output for the HYPERLINK case: `'=HYPERLINK("http://x/","c")` — apostrophe
inserted *after* quoting, which is the only correct placement.

Residual note worth sending (hardening, not a bug): the XLSX path stores the value without
the `'` prefix the CSV path applies. Inert today only because the cell is text-typed. Recommend
prefixing at the data layer so every export inherits it.

---

## 2. UK rules worth checking on a property/MTD product (with sources)

- **MTD quarterly update dates** (2026/27): 7 Aug 2026 · 7 Nov 2026 · 7 Feb 2027 · 7 May 2027.
  A dashboard showing "Q1 7 Aug" / "Next deadline 7 Nov" is correct — check it against these
  exact dates before calling it a bug.
- **MTD thresholds**: £10k (Apr 2024) → **£50k (Apr 2026)** → £30k (Apr 2027) → £20k (Apr 2028).
- **Furnished Holiday Lettings abolished** from 6 April 2025 (Finance (No. 2) Act 2024; HMRC PIM4165).
  A product marketing to Airbnb/Vrbo hosts **must** say so. Correct wording to look for:
  "the furnished holiday lettings regime was abolished from April 2025, so short-term let
  income is now ordinary UK property income". Platform reporting (Airbnb/Vrbo/Booking.com
  reporting to HMRC) is also correct from Jan 2025.
- **Accounting basis**: for *property income*, **cash basis is HMRC's default** (since 2017/18);
  accruals requires an election. A product saying "cash basis (HMRC's default)" is right — do
  not "correct" it (this is commonly confused with the trading-income rules).
- **£150,000 cash-receipts ceiling**: the cash basis is disapplied when property cash receipts
  exceed £150,000 in a tax year (HMRC Property Income Manual, e.g. PIM1098 mentions the £150,000
  cash-receipts test). Test: push one year's receipts well past it and look for a warning, an
  accruals option, or any mention of the figure. Silence is a product-correctness gap.
- **Joint ownership / beneficial split**: HMRC's default is **50:50** for jointly-owned property
  unless a **Form 17** declaration states the actual beneficial ownership (ACCA/ICAS confirm).
  The 60/40 first-year banding applies only to property owned before 1 Jan 2001 by spouses or
  civil partners. If a product lets the user set an arbitrary share it should at least prompt
  about Form 17 and evidence retention — a user who sets 80/20 with no Form 17 gets reassessed.
- **Section 24** finance-cost restriction, **Rent a Room** (£1,000), **capital gains on
  disposal**, and the **year-end lock** ("declare opens after 5 April") are the other
  checkpoints.

---

## 3. Testing the ownership-share / mid-year transfer question

The most valuable test on this product class, because a scalar data model cannot express it.

Look in the bundle for the share control:

    <label for="ownerPercent">Your ownership share</label>
    <input id="ownerPercent" name="percent" inputMode="decimal" value="100" />

A single scalar, **no effective-date field**, no "sold / completed on" concept.

Prove it:
1. Give the property entries dated both before and after a hypothetical transfer date.
2. Read the tax-year totals at share = 100%.
3. Set share = 50% through the real form.
4. Read the totals again.

Observed: 100% → £4,878.08; 50% → £2,439.04, i.e. the **April entries were halved too**, and
the page states "You own this property and have 50% … you file your 50% share with HMRC."

Verdict wording: the app cannot represent a mid-month/mid-year change of ownership; every
option (100% all year / 50% all year) misstates one half of the year. Report as a
**product-correctness / tax-accuracy gap**, low severity, self-scoped — not an access-control
finding. Note the positives: co-owner share changes that require a current MFA code are a
genuinely good design choice.

---

## 4. Pro gate bypass by injecting the gated field name

Prop-driven gates leak the field name. Component signature found in the bundle:

    function v(){ let {thenSe:e=!1, allowForeign:t=!1, onCancel:n} = ... }
    ... t ? <><input type="checkbox" .../><span>This property is outside the UK</span></> : null
         i ? <select id="countryCode" name="countryCode" required>…</select> : null

So the honest field is `countryCode`. Inject it (plus plausible aliases `outsideUk`,
`isOverseas`) into the genuine create action via a hidden input beside the real ones, then click
the real submit so the React binding stays valid. Result: server replied
**"Overseas property is part of Pro. Upgrade to add a property outside the UK."** and created
nothing → clean negative. Also try the *settings/update* action, not just create.

---

## 5. Session-rotation discipline for these tests

`qw_session`-style cookies rotate frequently. A jar captured earlier will 307 to `/login`
mid-run and a "0 properties" reading will look like a successful deletion. Rules:
- Refresh the cookie jar from the storage_state file **immediately before** each batch.
- For anything that mutates, do login → attack → verify **inside one process/context**.
- Verify the session with a `Welcome,`/`Log out` marker in the body, not just a 200 (a 200 can
  be the login page after a redirect chain).
- When replaying a captured action returns `500 {"digest":...}` and the same request worked in
  the browser earlier, the cause is almost always per-render binding, not a finding. Confirm
  by re-capturing with fresh headers before concluding anything.

## 6. Coverage gaps to state honestly

FTCR computation and its cap, accruals arithmetic, Section 24 restriction, 60/40 banding, CGT on
disposal, and the real HMRC submission payloads usually sit behind Pro + a Government Gateway
authorisation. If you cannot pass that gate, say so — do not claim those are safe or unsafe.
