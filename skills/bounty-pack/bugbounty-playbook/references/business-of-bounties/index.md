# Business of Bounties

> tags: business, methodology

> related: Business-of-Bounties/Career-Strategy, Business-of-Bounties/Financial, Business-of-Bounties/Mental-Health, Business-of-Bounties/Running-a-Program, Business-of-Bounties/For-Organisations/, Methodology/Target-Selection, Reporting/Severity-Escalation, Programs/

Business of Bounties
Nobody talks about this part. The community obsesses over tools and techniques, which is fair, those are fun. But the difference between a researcher who earns $10k/year and one who earns $200k+ is rarely technical skill. It's strategy, target selection, time management, and understanding the economics of the system you're operating in.
I've spent over a decade on the researcher side and also co-founded and ran a bug bounty program for a multinational bank. That dual perspective has shown me things most hunters never see: how triage teams actually prioritize reports, why some programs pay more than others for the same vuln class, and what motivates companies to increase bounties.
The Economics
Here's the uncomfortable math most people don't do:
flowchart LR
    A[Hours per week] --> D[$ per hour earned]
    B[Target selection] --> D
    C[Technical skill] --> D
    E[Duplicate rate] --> D
    F[Triage speed] --> D
    G[Report quality] --> D

Most hunters optimise for the wrong variable. They try to improve technical skill (diminishing returns past a certain point) when they should be optimising target selection (biggest gains) and report quality (directly affects payout amounts).
Concrete example: spending 20 hours finding a reflected XSS on Google that pays $3,000 is $150/hr. Spending 4 hours finding the same vuln class on a mid-tier SaaS that pays $1,500 is $375/hr. The Google XSS looks better on your profile. The SaaS one pays better per hour.
Track your hourly rate. Track it per program. The data will surprise you.
From the Other Side
Things I learned from running a corporate bug bounty program that most researchers don't know:
Triage teams are overwhelmed. At any decent-sized program the triage queue has dozens of open reports. Your beautifully crafted chain report sits next to 15 "I found a missing HSTS header" reports. The triager has limited time. Making your report easy to assess (clear title, obvious severity, copy-pasteable reproduction steps) directly affects how quickly and favourably it gets handled.
Programs have internal politics. The security team running the bounty program has to justify the spend to leadership. When you submit a critical, the security team has to go to engineering and say "fix this." If your report is well-written and the impact is clear, they can use it as ammunition for their own internal advocacy. Help them help you.
Bounty amounts are negotiable in ways you might not expect. Most programs have ranges, not fixed amounts. The triager has discretion. Programs also periodically review their bounty tables. If you consistently demonstrate that a certain vuln class has higher impact than their table suggests, you're influencing future payouts for everyone.
The researchers they love are the ones who make their job easier. Clear reports, reasonable severity assessments, willingness to retest, professional communication. These researchers get triaged faster, get the benefit of the doubt on borderline severity calls, and get invited to private programs.
Time Management
pie title How I Allocate Bug Bounty Time
    "Active hunting" : 50
    "Recon (new targets)" : 15
    "Recon (monitoring existing)" : 10
    "Report writing" : 10
    "Follow-ups & retests" : 5
    "Tool maintenance" : 5
    "Learning / reading disclosures" : 5

The mistake I see most often is spending 90%+ of time on active hunting with no structured recon time. That means you're always testing the same surface everyone else is testing. Even 15-20% of your time dedicated to recon (especially continuous monitoring) gives you a steady stream of fresh attack surface that nobody else has seen yet.
Sections
Career Strategy
Full-time vs. side hustle economics, building a public profile, translating bounty experience into employment, and the career paths this opens.
Financial
Tax obligations (it's income, you have to report it), payment methods, income tracking, and why you should talk to an accountant before you start earning serious money.
Mental Health
Duplicates aren't personal. Burnout is real. Impostor syndrome affects almost every researcher I know. This section exists because nobody in the community talks about it honestly.
Running a Bug Bounty Program
The corporate perspective. How programs are structured, how triage works, how bounty tables are set, what motivates companies to invest in bug bounty. Understanding this makes you a better researcher.
For Organisations
The other side of the table. Guides for security teams standing up disclosure and bounty programs, defining scope, and building researcher relationships that produce results.
See Also

Target Selection
Severity Escalation
Program Strategy
