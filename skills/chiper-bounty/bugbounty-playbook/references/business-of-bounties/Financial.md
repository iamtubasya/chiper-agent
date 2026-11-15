# Financial

> tags: business, financial

> related: Attack-Surface/Web3/Tooling, Business-of-Bounties/Career-Strategy, Business-of-Bounties/Mental-Health

Financial
Bug bounty income is real income. The IRS doesn't care that it came from a bug bounty platform instead of an employer. I've seen people get surprised by this the hard way, so let's just get it out of the way early.
It's Income. Report It.
In the US, bounty payments are taxable as self-employment income. That means:

Federal income tax at your marginal rate
Self-employment tax: 15.3% on the first ~$168k (2024 figure, it adjusts annually), which covers both sides of Social Security and Medicare
State income tax if your state has it

The number that shocks people: if you're in the 22% federal bracket and paying self-employment tax, you're looking at roughly 37% of your gross bounty income going to taxes. Plan for it. Set aside 35-40% of every payment in a separate account. Do not touch it. Treat it like it was never yours.
If you're making meaningful bounty income, get a CPA who understands self-employment or freelance income. Not a family friend who does W-2 returns. A real one. The cost of a good accountant is trivial compared to the cost of doing this wrong.
Quarterly Estimated Taxes (US)
Once you're earning bounty income, you'll need to file quarterly estimated taxes. The due dates are roughly April, June, September, and January. Miss them and you owe penalties on top of the tax.
The IRS safe harbor rule: pay either 100% of last year's tax liability or 90% of this year's, and you won't owe underpayment penalties. When in doubt, overpay and get a refund.
Other Jurisdictions, Briefly
I'm not a tax professional anywhere, but here's the pattern: almost everywhere with an income tax treats bounty payments as taxable. The UK treats it as miscellaneous income or potentially trading income if you're doing it seriously. Canada treats it as business income. Australia is similar.
The consistent advice regardless of country: don't assume it's untaxed because it comes from a US company or a platform based elsewhere. Find a local accountant or tax advisor who can give you jurisdiction-specific guidance. The platforms will often issue 1099s (US) or equivalent forms anyway, so there's a paper trail whether you account for it or not.
Payment Methods by Platform
Not all payment methods are equal. Here's what actually works:
PayPal. Most common on HackerOne and Bugcrowd. Works fine for small amounts. For large payouts, PayPal has a history of holding funds or requiring verification at the worst times. Keep your account in good standing and verify your identity proactively, not when you're waiting on a $10k payment.
Wire transfer. Available on most major platforms for larger payouts. Slower (3-5 business days), but it goes directly into your bank. No middleman that can hold your money. Preferred for anything over $1,000 if you have the option. Know your bank's incoming wire details and test it once with a small amount before you need it for something big.
Crypto. Some programs and platforms offer this. It solves the international transfer problem well. It creates its own tax accounting problem, because in the US (and many other countries) receiving crypto as income means you record the USD value at receipt, and any later sale is a capital gains event. If you receive crypto, log the date, amount, and USD value immediately. Don't let this pile up.
Check. Still offered by some programs, especially older corporate programs running their own BBPs. Checks are slow and annoying. Accept them if it's your only option, but advocate for wire if you're dealing with a program regularly.
Platform credits / swag. Not income in the tax sense. Also not rent money. Nice for CTFs, not a business model.
Income Tracking: Do It from Day One
The discipline that separates people who have a sustainable bounty practice from people who scramble at tax time: track everything as it happens.
What to record for every payment:

Date received
Platform
Program name
Report ID or brief description
Gross amount paid
Payment method
Tax withheld (some international programs withhold)

A spreadsheet works fine. There are no special tools required. What matters is doing it consistently.
Why you need this beyond taxes:

You'll want to know which platforms and programs are actually paying you. The answer is often surprising.
When you're deciding whether to go deeper on a target or move on, historical income data tells you things your memory doesn't.
If you ever apply for a mortgage or business loan, you need income documentation. Bug bounty income is real income but it takes more paperwork to prove.

See a sample tracking structure in Tooling.
Business Expenses
If you're treating this seriously, some expenses are deductible against your self-employment income:

VPS and cloud infrastructure for testing
Security tools and software subscriptions
Conference attendance (if you're there for professional development, not just fun)
Home office deduction if applicable
Books, courses, training

Keep receipts. Track them in the same spreadsheet. Your accountant will ask for them.
The Honest Bottom Line
Bug bounty income is great money when it's flowing. It is genuinely unpredictable. Budget off your average, not your best month. Save aggressively when income is good because dry spells are real.
Talk to an accountant before you're earning serious money, not after. The advice is cheap. The mistakes are not.
See also: Career Strategy, Mental Health
Tax Treatment by Jurisdiction
The "other jurisdictions, briefly" section above covers the broad shape. Here's more detail for the countries where most bounty income concentrates.
United States
HackerOne and Bugcrowd both issue 1099-NEC forms (replacing the older 1099-MISC for non-employee compensation) to US-based researchers who receive $600 or more in a calendar year. The form goes to you and to the IRS. Even if you receive under $600 and don't get a 1099, the income is still taxable and you're still required to report it.
Bounty income goes on Schedule C as self-employment income. You pay federal income tax at your marginal rate plus self-employment tax (15.3% up to the Social Security wage base, 2.9% above it). The half of self-employment tax you pay as the "employer" portion is deductible against your income tax, which partially offsets it.
Quarterly estimated taxes. If you expect to owe more than $1,000 in federal tax for the year, you should be paying quarterly estimates. The due dates are mid-April, mid-June, mid-September, and mid-January. The IRS safe harbour: pay 100% of last year's total tax liability across the four quarters, or 90% of this year's. The first approach is easier to calculate if your income is unpredictable.
Schedule C deductions. Document everything you spend on the business: VPS costs, tooling subscriptions, home office (either the simplified $5/sq ft method up to 300 sq ft, or the actual expense method if your dedicated space is larger), conference attendance and travel, training and books. The home office deduction requires the space to be used regularly and exclusively for work  -  a desk in a bedroom doesn't qualify; a dedicated room does.
For non-US researchers, HackerOne issues a 1042-S form for payments where US withholding tax applies under the relevant tax treaty (or at the 30% default rate where no treaty exists). Check whether your country has a US tax treaty and what withholding rate applies. You may be able to claim a foreign tax credit in your home country for the withheld amount.
United Kingdom
Bounty income in the UK is taxable as either miscellaneous income (if you do it occasionally) or trading income (if you do it regularly and with a view to profit  -  which most serious researchers meet). Trading income is the more likely classification for anyone hunting consistently.
You report it on a self-assessment tax return, due by 31 January following the end of the tax year (5 April). If this is your first year of self-employment income, register with HMRC by 5 October of the following tax year to avoid a penalty.
Payments on account. Once your tax bill exceeds a threshold, HMRC requires you to make two advance payments toward next year's tax: one in January, one in July. The first time this hits is a shock  -  you pay this year's bill in January plus 50% of it again as a payment on account for next year. Budget for it.
Sole trader vs. limited company: trading as a limited company becomes worth considering above roughly GBP 50,000 in profit, where Corporation Tax rates and the ability to take income as dividends (taxed at dividend rates rather than income tax rates) can produce a meaningful saving. Below that level, the administrative overhead of running a company typically costs more than it saves. Get specific advice from a UK accountant when you approach that threshold.
European Union
EU VAT is the main complication for EU-based researchers earning from non-EU platforms. If you're registered for VAT, you may need to account for the VAT on services received from non-EU suppliers (reverse charge) and potentially charge VAT on your own services. VAT registration thresholds vary by member state  -  from EUR 0 in Spain (mandatory registration regardless of turnover) to EUR 85,000 in France. Check your local threshold. If your income is below it, you may be exempt, but you lose the ability to reclaim input VAT.
Many EU member states allow deductions for home office costs, equipment, and professional subscriptions against freelance or self-employment income. The specific allowable expenses list varies significantly. Germany's self-employment (Freiberufler) classification, France's auto-entrepreneur scheme, and the Netherlands' ZZP structure all have different rules.
Australia
Australian researchers need an ABN (Australian Business Number) if they're carrying on a business  -  and regular bounty hunting qualifies. Income is reported as business income on your individual tax return.
GST registration is required once your annual turnover exceeds AUD 75,000. Below that threshold, registration is optional but you can voluntarily register to claim GST credits on business inputs. For most researchers, income will be GST-free under the exported services rules (services supplied to overseas entities for use overseas), but confirm with an accountant.
Platform Reporting and Currency Conversion
For payments made in USD to non-US researchers, or in USDC/crypto to anyone, the timing of income recognition matters.
Currency conversion: Income is recognised at the time you receive the payment, at the exchange rate on that date. If you receive USD into a USD account and convert later, many jurisdictions treat the FX gain or loss at the point of conversion as a separate income event. The safest position: log the AUD, GBP, or EUR equivalent at the date of receipt, using the mid-market rate. Don't wait until year-end to calculate it.
Crypto payouts (Immunefi and some direct programmes pay in USDC, ETH, or other tokens): record the fiat value at the moment of receipt. Any later conversion or disposal is a separate capital gains or income event depending on your jurisdiction. This creates a tracking obligation that compounds quickly if you receive many small crypto payments.
Direct Programme and Immunefi Payouts
Not all bounty payments come through platforms that issue tax forms. Direct corporate programmes, and platforms like Immunefi, may pay by wire transfer or crypto without any 1099 or equivalent. The absence of a form doesn't change your reporting obligation. Track these with the same discipline: date, amount, programme name, payment method, fiat value at receipt.
If a direct programme asks you to invoice them, issue the invoice  -  it creates a record on both sides and makes the payment look like legitimate consulting income in your books, which it is.
Record-Keeping
Keep all records for at least 7 years (US: IRS statute of limitations) or 6 years (UK: HMRC). That means: payout statements from platforms, your income tracking spreadsheet, all receipts for deductible expenses, bank statements showing receipt, and  -  for crypto  -  cost basis records for every token received.
When to Get Professional Help
The break-even point for hiring a bookkeeper or accountant is roughly $30-50k in annual bounty income for most researchers. Below that, a careful spreadsheet and a self-filed return work. Above it, the deductions, entity structure questions, and cross-border complications produce enough complexity that professional advice pays for itself in the first year. Get recommendations from other researchers in your jurisdiction, not from generic small-business accountant directories.