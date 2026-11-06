# Career Strategy

> tags: business, career

> related: Reporting/Report-Writing, Programs/, Business-of-Bounties/Financial, Business-of-Bounties/Mental-Health, Business-of-Bounties/Running-a-Program

Career Strategy
Most people don't do the math before going full-time. I didn't either, the first time I considered it. That was almost a mistake.
Full-Time vs Side Hustle: The Actual Economics
Here's the thing about bug bounty income: it's lumpy. You might go three months finding nothing critical, then land a $15k report in a week. That variance is brutal when rent is due.
Before you quit your job, you need:

Six months of living expenses saved, minimum. A year is better.
A realistic average of your last 12 months of bounty income, not your best month.
An honest look at your current earnings trajectory. Is it going up, flat, or was last month a fluke?

The math most people skip: take your annual salary, add benefits (health insurance alone is $300-600/month out of pocket in the US), and that's your replacement target. A $70k/year job costs you more like $85k to replace when you account for self-employment taxes and benefits.
Realistic income brackets, roughly:






























LevelSituationMonthly RangeBeginner (0-1 yr)First few finds, learning$0 - $500Intermediate (1-3 yr)Consistent finds, some crits$500 - $3,000Experienced (3-5 yr)Known in community, private invites$3,000 - $10,000Top tierPrivate program access, specialized$10,000 - $30,000+
Those ranges aren't guarantees. They're what I've seen people actually pull in. The top tier numbers are real but rare, and they come after years of compounding reputation and skill.
The side hustle model isn't giving up. It's often smarter. You hunt evenings and weekends, bank the income, build reputation without pressure. Pressure kills creativity in this work. When you're desperate to find something, you miss things.
Building a Public Profile
Your public profile is compounding interest. Every writeup, every talk, every leaderboard placement is an asset that keeps paying.
Writeups. Write them even when they feel trivial. Your first IDOR writeup is boring to you. It's genuinely useful to someone six months behind you. More importantly, it signals that you understand the vulnerability, not just that you found it. Recruiters and program managers read writeups.
Where to publish: HackerOne Hacktivity, your own blog (even a free one), Medium, or GitHub Pages. Own your content. Platform-hosted-only writeups disappear when platforms change.
Talks. Submitting to BSides is approachable. DEF CON and Black Hat are not as impossible as they feel. One real talk does more for your profile than 50 tweets. The barrier is lower than you think once you have one interesting finding or methodology.
Leaderboards and reputation scores. These matter for private program invites more than anything else. HackerOne reputation, Bugcrowd points, these get you into programs with less competition and higher payouts. Treat them like a professional credential.
See also: Report Writing, Programs
How This Translates to Employment
Bug bounty experience is genuinely respected in the security industry. Here's what it actually opens:
Application Security Engineer. This is the most direct path. Companies hiring AppSec engineers want people who can find vulns, not just talk about them. A portfolio of real findings is better than most certifications. Salary range: $120k-$200k in the US depending on company and seniority.
Penetration Tester. Consultancies and internal pentest teams hire bug bounty researchers constantly. You already know how to scope an assessment, write findings, and explain impact. The transition is mostly about learning report format and client communication. Salary range: $90k-$160k.
Security Consultant. Senior consultants with public track records can bill $200-400/hour independently. This is a longer-term play. It requires business development skills bug bounty doesn't teach you. But the technical credibility transfers directly.
Program Operations / Triage. Some researchers end up on the other side of the table, running programs or doing triage for platforms. It pays less than finding vulns but it's steady.
The underrated path: leveraging both. I've known researchers who hunt part-time while working as AppSec engineers. Their day job makes them better at finding business logic bugs. Their hunting keeps their skills sharp in ways enterprise work doesn't. It's a strong combination if you can manage the hours.
What Actually Builds a Career
Depth beats breadth. A researcher who deeply understands one or two vulnerability classes will consistently outperform someone with shallow knowledge of twenty. Pick something, go deep, become known for it.
Write about what you find. Teach what you know. Be the person who explains things clearly, not just the person who finds them. The community is smaller than it looks and reputation compounds.
Don't wait until you're "ready" to apply for jobs or submit to programs. You're never ready. Ship the writeup. Submit the talk. Apply for the role. The feedback loop only starts when you put something out there.
See also: Financial, Mental Health, Running a Program
Post-Bounty Career Paths
Bug bounty is a starting point, not a ceiling. The paths out of it are better than most researchers realise when they're still building their first finding history.
Pentest and Offensive Consulting
This is the most direct conversion. Consultancies  -  both boutique and Big Four  -  hire researchers who can demonstrate real-world finding ability. Your disclosed reports are your portfolio. A triaged critical on a known programme is worth more in an interview than most certifications.
The typical conversion path: one to two years of consistent finding, a few public disclosures or writeups, and an OSCP or equivalent to show you understand the assessment methodology (not just the finding methodology). The main skill gap between bounty and pentest is report writing for a client audience  -  scope summaries, executive impact, remediation guidance. That's learnable quickly if you've already been writing detailed bounty reports.
Junior pentesters at consultancies start around $80-100k in the US. Senior roles at specialist firms go higher. The ceiling in consulting is less about salary and more about billable rate if you eventually go independent.
Red Team at Large Enterprises
Enterprise red team roles are increasingly filled by former bounty researchers. The work is closer to bug bounty than a typical pentest  -  longer engagements, more freedom to follow threads, less report-factory pressure. The difference is you're attacking one organisation deeply rather than many organisations broadly.
These roles tend to appear at financial services firms, large technology companies, and defence contractors. The hiring criteria is almost always finding history over certifications. Some red teams specifically advertise for bounty experience because the adversarial mindset is harder to teach than the specific techniques.
Security Research at Labs and Vendors
Google Project Zero, MSRC (Microsoft Security Response Center), PortSwigger Research, and Trail of Bits all hire independent security researchers. What they're looking for is different from each other:

Project Zero: Novel vulnerability research and original defensive contributions. Published CVEs and public technical writing matter more than bounty income.
MSRC: Deep Windows or Azure security knowledge, experience with the Microsoft vulnerability disclosure process, and evidence you can work with a large internal team.
PortSwigger: Web security depth. If you write the kind of research that ends up cited in other people's writeups, this is the audience for it.
Trail of Bits: Cryptographic and smart contract security, compiler and toolchain security, formal methods. A narrower fit, but one of the best research environments in the industry.

These are competitive roles. The path in usually involves public research output  -  a CVE, a detailed blog post, a conference talk  -  before you apply.
Founding a Security Company
A disproportionate number of security founders come from vulnerability research. CrowdStrike's founders came from McAfee's advanced threat research team. Detectify was built by researchers who had been active on HackerOne's predecessor. Bishop Fox, NCC Group's US expansion, and numerous smaller boutiques were started by people with offensive research backgrounds.
The pattern: a researcher develops depth in a specific area, realises the market doesn't have a good tool or service for it, and builds one. The technical credibility from public research makes fundraising and customer development easier than starting from scratch in most industries.
Going this route takes more than technical skill. Sales, finance, hiring  -  none of these are things bounty hunting teaches. But the technical foundation and the network are real advantages. The security industry is small enough that a reputation for quality research opens doors that take years to open in other sectors.
Embedding with a Single Programme
Some researchers effectively become extensions of one company's security team without being employees. They focus exclusively on that programme, build deep knowledge of the codebase and architecture, and generate a consistent stream of findings that the security team couldn't produce internally.
This arrangement works best with large programmes that have complex, long-lived codebases  -  enterprise software companies, financial services platforms, large SaaS providers. The researcher gets predictable income and deep access. The programme gets a specialist who knows their architecture better than any external pentester. Some of these arrangements formalise into retainer agreements or eventually full-time roles.
Staff and Principal Security Engineering
Product companies  -  particularly in cloud infrastructure, payments, and developer tools  -  hire for staff and principal security engineer roles that look a lot like applied research. The job is to find vulnerabilities in the company's own products before external researchers do, to drive secure design at the architecture level, and to manage the external disclosure programme.
Bounty hunters who know how programmes look from the outside bring something internal teams often lack: genuine attacker perspective. The salary ranges at principal level ($200-350k at senior US tech companies) are well above what most researchers earn on bounty alone, and the benefits are significant.
Writing, Speaking, and Teaching
Some of the most influential people in the security community primarily do none of the above. They write, speak, and teach.
A Black Hat or DEF CON talk on a specific vulnerability class or research methodology reaches thousands of people who will remember your name when they're hiring, when they're deciding who to invite to a private programme, or when they're recommending someone for a role. The CFP process is competitive but not closed. One genuinely new piece of research or a well-structured methodology talk has a real chance.
SANS instructors earn course royalties and consulting work from the association with a known training brand. PortSwigger's blog has published researcher-contributed posts that became widely cited. HackerOne's LevelUp events surface researcher voices to the platform's programme manager audience.
Hall of Fame Entries and Portfolio Management
Hall of fame entries are underused as portfolio items. When a programme publicly acknowledges your finding  -  even without a dollar figure  -  that's a verifiable record of valid security work.
List them on your profile and your CV. Be specific: not "found vulnerabilities in Fortune 500 companies" but "identified a stored XSS leading to account takeover in [programme name]'s mobile web application, acknowledged in their security hall of fame, [year]." The specificity is what makes it credible.
For disclosed reports where the programme has made the finding public on HackerOne Hacktivity, link directly. Anyone can click through and read the original report, the triage response, and the severity assessment. That transparency is more convincing than any self-description.
Building a public profile doesn't require a large social media presence. A blog with five detailed technical writeups and ten linked disclosed reports is worth more than a prolific Twitter/X feed. Write once, write well, and let the content compound.