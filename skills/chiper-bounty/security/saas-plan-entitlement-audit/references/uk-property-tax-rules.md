# UK property-income tax rules a bookkeeping/MTD tool must honour

Authoritative-enough notes for reviewing whether a product's logic is current. Always
re-verify before reporting — rules move. Verified against HMRC public material 2026-09.

## Making Tax Digital — thresholds and dates (these move; check)
| Tax year | Qualifying income threshold (landlords & self-employment) | Must use MTD from |
|----------|--------------------------------------------------------|-------------------|
| 2024/25  | £10,000                                                | 6 Apr 2025         |
| 2025/26  | £10,000                                                | 6 Apr 2026         |
| **2026/27** | **£50,000**                                         | 6 Apr 2026         |
| 2027/28  | £30,000                                                | 6 Apr 2027         |
| 2028/29  | £20,000                                                | 6 Apr 2028         |

Quarterly update deadlines for 2026/27 (published by HMRC):
**7 Aug 2026, 7 Nov 2026, 7 Feb 2027, 7 May 2027.**
A tool that renders a different date is wrong; one that matches is a positive result worth
telling them.

## Furnished holiday lettings (FHL) — ABOLISHED
- FA(No.2) Act 2024: the FHL regime **ceases to apply for tax years commencing on or after
  6 April 2025** (Income Tax). HMRC PIM4165.
- Short-term-let income is now **ordinary UK property income**: same expense categories,
  Section 24 finance-cost restriction applies, no new capital allowances, standard residential
  CGT on disposal.
- Practical review test: a product marketing to Airbnb/Vrbo hosts that still implies FHL
  treatment is out of date. A product that explicitly states the abolition and the switch to
  ordinary property income is current — say so in the report; it is a genuine positive.

## Accounting basis — the common factual error
- **Cash basis has been the DEFAULT for property income since 2017/18**; accruals requires an
  election. (Do not confuse this with trading income, where the same change applied from
  2024/25.)
- **Cash basis is disallowed where cash receipts from property exceed £150,000 in a tax year**
  (HMRC Property Income Manual; the £150k figure appears in PIM1098). Above that ceiling a
  landlord must be on accruals.
- Review test: push a property's annual cash receipts past £150,000 (a single large entry is
  enough) and search the property page, settings, dashboard and export for any warning, any
  accruals option, or any mention of the ceiling. Nothing at all = a correctness gap: the
  tool keeps producing cash-basis figures that are no longer permissible, and the user only
  finds out from an HMRC letter.
- Anything about the old cash-basis election thresholds: confirm against current PIM before
  quoting a number. The £250k figure circulated for years; don't assert it unverified.

## Jointly owned property — Form 17
- HMRC's **default is an even 50:50 split** of the income, regardless of actual ownership.
- A different split applies only where beneficial ownership genuinely differs, and in that case
  the owners must make a **Form 17** declaration. Evidence must be retained.
- Property owned **before 1 January 2001** by spouses/civil partners: the separate 60/40
  first-year banding applies.
- Where one owner is on accruals, the couple cannot simply split 50/50 (ITA 2007 s.836
  interaction) — a real-world trap.
- Review test: a tool that lets a user type any ownership percentage with **no mention of
  Form 17, no "have you declared?" prompt and no evidence-retention note** produces figures
  that HMRC will reassess. That is a correctness/documentation gap, not a security bug.

## Tax year boundaries
- UK income tax year: **6 April to 5 April**. Test with a unique value per edge case:
      <start−1 day> -> previous year
      start         -> current year (first day)
      end           -> current year (last day)
      end+1 day     -> next year (first day)
  Then read back from the authoritative export, not the UI. Absence of off-by-one,
  boundary leakage or double counting is a strong positive result worth stating.

## Precision
- Store in integer minor units. `0.01 × 3` must be exactly `0.03`; net must equal
  income − expenses to the penny. Float drift in a tax figure is a real defect.

## Idempotency
- Replay a submission identifier the client already used; a correct backend dedupes and
  returns a message like "This entry was already sent." rather than creating a duplicate.

## Business-logic defect that recurs: scalar ownership with no effective date
A property record with a single "your ownership share %" and **no date / no "sold on" field**
cannot represent a change of ownership part-way through a tax year. The share is applied to
the whole year, so the user is forced into one of two wrong answers:
  - keep 100% ⇒ months before the transfer overstated, tax under-paid
  - set 50%   ⇒ months after the transfer understated, tax over-paid
Proof recipe: add entries dated both before and after a hypothetical transfer date, then flip
the share 100% → 50% and read the totals. If the pre-transfer entries are halved too, the
single scalar is confirmed to be applied to the whole year. Report the impact in those terms
("the taxpayer's figure is wrong, and the shortfall falls on them"), not as a security
boundary crossing — the actor only alters their own records.
