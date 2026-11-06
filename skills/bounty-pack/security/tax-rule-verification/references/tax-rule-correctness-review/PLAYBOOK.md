---
name: tax-rule-correctness-review
description: "Use when reviewing a financial/tax product's arithmetic against statutory tax rules (e.g. UK HMRC) rather than looking for security bugs."
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [tax, hmrc, business-logic, correctness, saas, compliance, uk]
---

# Tax-Rule Correctness Review (financial/tax SaaS)

Use when the ask is not "find a security bug" but "is this product's tax arithmetic right?"
Typical triggers: the user names specific rules ("foreign tax credit cap", "section 24",
"60:40", "acquisitions/accruals basis", "capital gains on disposal"), or a security audit has
already run and the user wants the money-affecting numbers checked too.

This is a DIFFERENT discipline from vuln hunting: no payloads, no auth bypass — you drive
controlled scenarios and compare the product's arithmetic with the statute. Findings are
usually "product correctness" (the vendor's own product-decision category), not CWE classes.
Report them separately from security findings so neither dilutes the other.

## The user's standard (do not skip this)

For this class the bar is: **the rule must be verified against the official source, not
against intuition or a blog.** Fetch gov.uk / the HMRC internal manual (PIM, BIM, HS263…)
and cite the specific rule. Users of financial SaaS ask for this explicitly; asserting a rule
from memory is the failure mode that burns credibility.

## Method

1. **Pin the rules first.** For each rule the user named, get the authoritative statement
   (cap formula, rate, threshold, deadline). Write it down as `expected` before touching the app.
2. **Find the vendor's OWN stated interpretation.** Their marketing/help pages are the yardstick
   they can't argue with:
   - `curl /sitemap.xml` → harvest `/guides/*`, `/tools/*`, `/faq`, `/blog/*`
   - strip tags and grep for the rule keywords + numbers
   - public calculators (`/tools/section-24-calculator`, `/tools/capital-gains-tax-calculator`)
     encode their view of the rule; read the copy AND the inputs they ask for
   - the FAQ often states a capability ("you can record foreign tax and claim FTCR") that the
     in-app arithmetic then does not honour — that mismatch is the finding
3. **Design a scenario where right and wrong give DIFFERENT numbers.** A rule difference that
   cancels out (e.g. Section 24 vs full deduction for a basic-rate taxpayer) proves nothing.
   Push income into the higher band so the two treatments diverge, and compute both by hand.
4. **Drive it with the smallest reliable interface.** Provisioning exact amounts is fastest via
   the product's API; UI automation only where the feature is UI-only. Read results from the
   product's own estimate/panel — see the oracle note below.
5. **Isolate one variable per step.** Add, read, add, read. A missing line item is only evidence
   if the same path works in a control scenario (see "untestable family" below).

## The oracle trick: let the product compute your test

An itemised estimate/report panel is the best oracle available — it shows the intermediate
figures (profit, allowances applied, reliefs, taxable, rate) that let you pinpoint WHERE the
arithmetic diverges instead of only seeing the final number:

```
Total income £130,000.00 | Total expenses £50.00 | Net profit £129,950.00
Before mortgage interest of £20,001.00, which is relief, not a deduction
Taxable: £129,950.00 | Finance costs relief (20%): −£4,000.20
Your actual expenses (£20,051.00) beat the £1,000 property allowance, so we've used those.
```
The line "actual expenses (£20,051)" exposed the bug: that total includes £20,001 of mortgage
interest, i.e. a NON-deductible finance cost, which is what displaced the property allowance.

## Pitfalls that produce false findings

- **Account-level aggregation.** The panel usually totals every source in the account. Adding a
  second property silently changes the first scenario's numbers (£60k became £130k). Either work
  one property at a time with everything else empty, or account for the running total in your
  expected value. Write the expected figure AFTER noting the aggregate.
- **Allowance tapering.** At high income the personal allowance is £0, so `Taxable == Profit`.
  That is correct, not a bug.
- **Don't claim a rule interaction you haven't verified.** e.g. "finance costs must not displace
  the property allowance" is defensible (they are not deductible post-S24); if the interaction is
  subtle, state the caveat ("a specialist should confirm the interaction") rather than overclaiming.
- **A missing feature is not a bug until the vendor claimed it.** "No £150k warning" only counts
  because the vendor said in writing they would add it. Quote their sentence in the report.
- **Untestable family = say so.** If the feature sits behind a gate you are not allowed to pass
  (2FA + a live government gateway, a paid tier, an HMRC connection), record it as
  "not tested within the constraints" — never as a negative result, and never bypass the gate.
- **Estimates legitimately differ from a filed return.** State whether you are judging the
  estimate panel, the export, or the submission payload; a credit that is applied only at
  return stage is not automatically a bug.

## Reporting shape (this class)

- Keep a separate document from the security findings (this user runs both tracks).
- Per rule: `rule (cited) → scenario → what the product output → verdict (correct / bug /
  unverifiable) → money effect at the relevant rate`.
- Quantify in £: "£1,000 of taxable profit lost → £450 at the 45% rate".
- Mark which items are questions to the vendor (e.g. "is FTCR applied at return stage?") versus
  bugs. Vendors accept this category readily and credit it.
- Larger numbers are not better: a wrong £450 estimate is worth reporting, a padded one is not.

## Reference

- `references/quarterwise-uk-property-rules.md` — the UK property/MTD rule set already verified
  in practice (FTCR + its cap, Section 24, the £1,000 property allowance, the £150k cash-basis
  threshold, ownership-share/60:40 arithmetic, CGT 18/24% + £3,000 AEA + 60-day reporting),
  including which are reachable and which sit behind gates.
