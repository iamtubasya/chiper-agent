# UK tax rule bank — 2026-27 (authority figures, quotable)

Condensed from gov.uk so a future audit does not need to re-fetch everything. Every figure here
was pulled from the authority (not from a product) and used as the "expected" column in a
2026-10 tax-correctness audit. **Re-fetch before quoting in a report** — thresholds move.

Fetch recipe (web_extract is often search-only/ddgs on this host, so use curl):

```bash
curl -s -A "Mozilla/5.0" "<gov.uk url>" | python -c "
import sys,re,html
t=sys.stdin.read()
t=re.sub(r'<script.*?</script>','',t,flags=re.S); t=re.sub(r'<style.*?</style>','',t,flags=re.S)
t=re.sub(r'<[^>]+>',' ',t); t=re.sub(r'\s+',' ',html.unescape(t)); print(t[:2000])"
# for tables:
#   re.findall(r'<tr>(.*?)</tr>', raw, re.S) -> strip <t[hd]> per cell
```

## Income tax — rUK 2026-27
Source: https://www.gov.uk/income-tax-rates

| Band | Taxable income | Rate |
|---|---|---|
| Personal Allowance | up to £12,570 | 0% |
| Basic | £12,571–£50,270 | 20% |
| Higher | £50,271–£125,140 | 40% |
| Additional | over £125,140 | 45% |

=> band widths on taxable income: 37,700 @20% · 87,440 @40% · above 125,140 @45%.

**PA taper (quoted):** "If you earn more than £100,000 your personal allowance goes down by £1 for
every £2 that your adjusted net income is above £100,000 … your allowance is zero if your income is
£125,140 or above."

Worked checks (used to expose the vendor's calculator bug):
```
profit 119,000 -> PA = 12,570-(119,000-100,000)/2 = 3,070 -> taxable 115,930
              -> 0.2*37,700 + 0.4*(115,930-37,700) = 38,832
profit 129,000 -> PA = 0 -> taxable 129,000
              -> 7,540 + 34,976 + 1,737 = 44,253
```
Scotland/Wales use different bands — grep the product bundle for `scotland|scottish|welsh`; 0 hits
means those bands are not modelled at all.

## Property allowance £1,000 vs Section 24
Sources: https://www.gov.uk/guidance/tax-free-allowances-on-property-and-trading-income and
HMRC PIM4400–PIM4460.

- Finance costs (residential mortgage interest) are **added back** from profit and given as a
  **20% tax reducer**, limited to the lower of the finance cost / property profits / adjusted net
  income above the PA. Excess carries forward.
- **Quoted exclusion:** "You cannot use the property allowance if you … claim the tax reducer for
  finance costs such as mortgage interest for a residential property." So allowance and
  expenses+finance-relief is an **either/or election** — the product must compare and pick the
  cheaper. Worked: rent £130,000 + £50 + £2,000 interest → allowance wins ("saves you £27.50");
  with £20,001 interest → expenses+relief wins. A product that always uses one side is the bug.

## Cash basis £150,000
Source: HMRC PIM1092. Cash basis is the default for individuals/partnerships with receipts **≤
£150,000**; above that the default changes. A cash-basis-only product should warn at >£150k.

## Rent a Room
Relief is £7,500 (£3,750 if shared). Some products are entry-driven (you type the "amount
claimed") rather than auto-applying it — that is a model choice, document it, don't call it a bug.

## Joint ownership / Form 17
Spouses/civil partners jointly owning a rental default to **50:50**; a **Form 17** election
declares actual beneficial shares (60:40 etc.). Non-spouse joint owners generally follow ownership
shares. A single percentage field with no date range means a mid-year change applies to the whole
year — a limitation, not a bug.

## Making Tax Digital for Income Tax — phases & deadlines
Sources: https://www.gov.uk/guidance/penalties-for-making-tax-digital-for-income-tax and the MTD
guidance pages.

- Mandation thresholds by qualifying income (turnover, NOT profit): **£50,000 from 6 April 2026 ·
  £30,000 from 6 April 2027 · £20,000 from 6 April 2028**.
- Quarterly periods end 5 Jul / 5 Oct / 5 Jan / 5 Apr; deadlines are **7 Aug / 7 Nov / 7 Feb /
  7 May**. Tax return + balance due **31 January** after year end.
- Late submission = **points-based**: 1 point per missed deadline, threshold **4 points** → **£200**,
  and £200 for each further miss. **Quoted grace:** "There are no penalties for missing a quarterly
  update deadline for the 2026 to 2027 tax year" (points start from tax years after 2026-27).
- Late **payment** penalties (non-points, per payment), two rate sets by tax year:

| | 2026-27 | 2027-28 |
|---|---|---|
| up to 15 days late | no penalty | no penalty |
| 16–30 days late | 3% at day 15 (nil in your first year) | **4%** at day 15 (nil in first year) |
| 31+ days late | 3% at day 15 + 3% at day 30, plus 10%/yr charged daily from day 31 | **4% + 4%** + 10%/yr from day 31 |

**Trap this exposed:** a product that stores ONE set of late-payment rates and applies it to every
selected tax year understates 2027-28 (observed: £5,000 paid 40 days late → £314 in both years;
2027-28 should be 4%·5,000 + 4%·5,000 + 10%·5,000·(10/365) = £413.70). Check the constant is keyed
on the selected tax year.

## SDLT — residential, England & Northern Ireland
Source: https://www.gov.uk/stamp-duty-land-tax/residential-property-rates

Bands: 0% to £125,000 · 2% £125,001–£250,000 · 5% £250,001–£925,000 · 10% £925,001–£1.5m · 12%
above. **+5%** additional-dwelling surcharge (applies where consideration > £40,000). First-time
buyer relief: 0% to £300,000, 5% £300,001–£500,000, and **no relief at all if price > £500,000**
(the FTB relief does not combine with the additional-property surcharge).

Checks: £295,000 single → £4,750 (the gov.uk worked example); £295,000 additional → £19,500;
£400,000 FTB → £5,000; £600,000 FTB → £20,000 (relief gone).

## Capital gains tax — residential property
Annual exempt amount **£3,000**; **18%** to the extent of remaining basic-rate band then **24%**;
Private Residence Relief final **9 months** exempt. UK residential disposals are reported and paid
within **60 days** of completion (separate from the return). PIM1092: disposal receipts for an
asset whose cost was deducted under the cash basis are treated as **income**, not a gain.
Checks: sale 400k / cost 250k / fees 20k → £28,218; same + other income 45k → £30,164;
300k/100k/10k → £42,618.

## Reporting the result
Three buckets, in order: **verified correct** (exact figures), **wrong arithmetic** (state the £ at
20/40/45%), **not implemented / not testable** (with the reason). A product that *discloses* an
exclusion on its dashboard (e.g. "estimate does not include losses from earlier years,
self-employment, Class 4 NI, FTCR, Scottish rates") downgrades that item from "bug" to "disclosed
limitation" — quote the product's own copy back. Keep calculation-correctness as its own artifact,
separate from the security report.
