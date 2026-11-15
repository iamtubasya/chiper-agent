# Choosing a Platform

> tags: business, programs

> related: Business-of-Bounties/For-Organisations/Starting-a-Program, Business-of-Bounties/For-Organisations/Setting-Bounty-Tables, Business-of-Bounties/For-Organisations/Scoping-a-Program

Choosing a Platform
The platform you choose shapes your programme's researcher base, your triage experience, and your ongoing costs for years. Getting this decision right early is worth the time. Getting it wrong means either a painful migration or accepting a suboptimal setup indefinitely.
The three platforms with significant market share are HackerOne, Bugcrowd, and Intigriti. Synack, YesWeHack, and Immunefi occupy meaningful niches. Each makes a different set of trade-offs.
Pricing Models
Platform pricing is not transparent  -  you'll need to request quotes  -  but the structure follows a consistent pattern across providers:
Annual platform fee. A base licensing fee to run your programme on the platform. This covers access to the submission portal, the dashboard, integrations, and (at some tiers) basic triage tooling.
Per-bounty platform fee. Most platforms charge a fee on top of each bounty paid out. Rates typically range from 15% to 30% of the bounty amount. When you set a $1,000 bounty, budget $1,150 to $1,300 in actual spend.
Managed triage fee. If you use the platform's triage team rather than doing first-line review yourself, expect a separate service fee  -  either a monthly retainer or a per-report charge. This is the cost line that surprises organisations most because it compounds quickly on a busy programme.
Researcher incentive programmes. Some platforms charge for access to their premium researcher pools (invitation-only groups, vetted tiers, or private cohorts).
Get itemised quotes from at least two platforms before committing. The total cost of ownership at 100 reports per year looks very different from the headline licensing fee.
Triage Model Differences
How reports get assessed before they reach your security team is one of the most operationally significant differences between platforms.
HackerOne Operations team: HackerOne's internal triage staff handle initial validation for programmes on managed plans. They're generalist security engineers, experienced with the platform, and process high volumes. SLAs for initial triage response typically run 2-4 business days on standard managed plans. The quality is consistent; the depth on very specialised findings (cloud misconfiguration, hardware, specific frameworks) can require escalation.
Bugcrowd ASE (Application Security Engineer) model: Bugcrowd's managed triage is staffed by ASEs who have domain specialisations. If your programme has a specific technology focus, Bugcrowd can often assign ASEs with relevant experience. The programme ramp-up period is slightly longer than HackerOne's, but the specialisation matching is a genuine advantage for technical programmes.
Intigriti community triage: Intigriti uses a peer-review model where a subset of vetted researchers perform initial triage. This produces faster initial response times on active programmes, and the reviewers are often closer to the current researcher mindset than staff triagers. The trade-off is less consistency  -  community triage quality varies more than staff triage quality.
Synack in-house vetted model: Synack's Red Team (SRT) is an invite-only pool of researchers who go through background checks and security vetting. Every researcher on the platform is pre-vetted. Triage is handled internally. This model is designed for organisations with strict compliance requirements around who can test their systems  -  financial services, government contractors, healthcare. It's the most expensive model and the most controlled.
SLA Commitments
Ask for specific SLA numbers in writing during contract negotiations. The relevant SLAs to nail down:

























MetricWhat to ask forInitial triage acknowledgmentTime from submission to first triage responseTriage decisionTime from submission to valid/invalid determinationPayout processingTime from approved report to researcher paymentEscalation responseTime from your question to platform support response
Industry norms: initial acknowledgment within 5 business days, triage decision within 15 business days, payout within 30 days of approval. Top-tier managed programmes can commit to tighter windows. If a platform won't put SLAs in the contract, treat that as a signal.
Programme Visibility Tiers
All major platforms offer multiple visibility configurations:
Private, invite-only: Only researchers you explicitly invite can see and submit to the programme. Useful for soft launches, programmes with sensitive scope, and organisations not ready for public volume. Researcher pool is small; you control who's in it.
Private, application-based: Researchers can apply for access; you approve or deny. Larger pool than invite-only, still controlled. This is the most common starting configuration for new programmes.
Public: Any registered researcher on the platform can submit. Maximises researcher coverage. Also maximises report volume, including noise. Only move public when your triage capacity can handle it.
Most programmes launch private and go public after the first 3-6 months, once the programme scope is stable and the triage team has calibrated to the finding rate.
Researcher Base and Vertical Fit
The platform with the largest nominal researcher count isn't always the best fit for your programme's scope.
HackerOne has the largest active researcher base and the most programme diversity. It's the default choice for general web application programmes and well-known consumer-facing businesses. Private invitation pools are large. Leaderboard researchers prioritise HackerOne because reputation scores there carry the most weight for private invites.
Bugcrowd has particular depth in enterprise software and government-adjacent programmes. Its researcher base skews toward more experienced participants than the platform average on HackerOne, in part because the onboarding process is more selective.
Intigriti is strongest in Europe. If your application's user base, infrastructure, or regulatory exposure is EU-focused, Intigriti's researcher community  -  which has more EU-based participants than any other major platform  -  is a genuine advantage. GDPR-aware researchers who understand European compliance context are easier to find here.
Synack for organisations with regulatory or vetting requirements. The vetted pool model is the right choice when your compliance framework requires knowing who is testing your systems.
Immunefi for web3 and smart contract security. The researcher base is specialised in Solidity, Rust on Solana, Move, and other blockchain-specific stacks. A traditional web2 programme on Immunefi would be mismatched to the audience.
Managed Services vs. Self-Service
Self-service means your team handles triage, researcher communications, and payout approval directly. This is viable if you have a security team member who can dedicate meaningful time to programme operations  -  realistically, at least one day per week at programme launch, settling to a few hours per week once the programme is mature.
Managed services offload first-line triage to the platform. Your team only sees validated findings. The advantages: faster researcher response times (researchers hate waiting), consistent triage quality, and the platform relationship management during disputes. The cost is significant. For organisations without dedicated security engineering capacity, managed services are usually the right choice despite the cost.
A rough decision framework:

You have a full-time AppSec team of 3+: self-service is viable
You have one AppSec engineer with other responsibilities: start managed, evaluate at 6 months
You have no dedicated AppSec: managed is the only realistic path

Switching Platforms
Switching after launch is disruptive but not fatal. The main costs:
Researcher reputation is not portable. A researcher's HackerOne reputation, signal score, and private invite history don't transfer to Bugcrowd. You'll rebuild momentum from a smaller engaged researcher base while researchers decide whether the programme is worth their time on the new platform.
Programme history stays on the old platform. Closed, resolved, and paid reports remain on your previous platform. You can export data, but the researcher-facing history doesn't follow you.
Contract timing. Most platform contracts are annual. Early termination fees vary. Factor in contract end dates when evaluating a switch.
The right time to switch is at contract renewal, with a 2-3 month transition period where you wind down submissions on the old platform while ramping up on the new one. Running both simultaneously for a quarter is expensive but gives researchers continuity.
Negotiating Platform Fees
Platform fees are more negotiable than the pricing pages suggest, particularly on the per-bounty percentage. Negotiating positions:

Volume commitments: "We project 150+ valid reports in year one" produces lower per-report rates
Longer contract terms: 2-year commitments typically reduce the annual platform fee by 10-20%
Referrals and case studies: platforms value being able to reference enterprise customers

If you're a large organisation running multiple programmes, negotiate an enterprise agreement that covers all programmes rather than signing each individually.
Red Flags
Walk away from, or push back hard on, these terms during contract negotiations:
Vague triage SLAs. "We aim to respond within a reasonable time" is not an SLA. Get specific numbers in the contract or don't sign.
Mandatory exclusivity clauses. Some platform contracts prohibit running a programme on a competing platform simultaneously. This limits your options at contract renewal and reduces your negotiating position. Push to have exclusivity clauses removed.
Unlimited liability waivers. A platform asking you to indemnify them against any researcher-caused damages without a liability cap is an unreasonable term. Negotiate a cap tied to the contract value or a reasonable fixed amount.
No data portability. Confirm in writing that you can export all report data, researcher communications, and programme history at any time and at contract end. Platforms that resist data portability are creating lock-in risk.

Related

Starting a Program
Setting Bounty Tables
Scoping a Program
