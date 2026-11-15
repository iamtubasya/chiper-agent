# Direct Programs

> tags: programs

> related: Reporting/Responsible-Disclosure, Programs/Platforms/HackerOne, Programs/Platforms/Bugcrowd, Programs/Platforms/Intigriti, Programs/Selection/Reading-Scope

Direct Programs
Direct programs are bug bounty or responsible disclosure programs that companies run themselves, outside of H1, Bugcrowd, or Intigriti. They range from Fortune 500 companies with mature in-house programs to startups with a security.txt file and a promise to respond. They're consistently underworked and often underrated.

Why Direct Programs Deserve Your Time
Less competition is the main reason. Researchers who only check H1 and Bugcrowd miss a significant portion of the bug bounty landscape. Direct programs don't show up in platform researcher counts. There's no public leaderboard. The researchers working them are a smaller, more self-directed group.
Secondary reason: payouts. Companies running their own programs don't pay platform fees to H1 or Bugcrowd. Some of that savings shows up in higher bounty tables. Not always, but often enough to factor in.

Finding Direct Programs
security.txt: RFC 9116 standardizes a security.txt file at /.well-known/security.txt or /security.txt. It contains contact information, policy links, and sometimes explicit bounty program details. Check this on every target you're considering.
# Example security.txt fields
Contact: mailto:security@example.com
Expires: 2026-01-01T00:00:00z
Policy: example.com/security/policy
Acknowledgements: example.com/security/hall-of-fame
Preferred-Languages: en
Responsible disclosure pages: Search for "responsible disclosure" site:example.com or "bug bounty" site:example.com. Most companies that run programs link to their policy from their main site footer.
disclose.io: The disclose.io project maintains a database of safe harbor policies at disclose.io/list. Browse by industry.
Reconnaissance on your existing targets: If a company you've been testing is acquired by or affiliated with another company, the parent often has a direct program too.

Due Diligence Before Testing
Direct programs carry more variability than platform programs. Before spending time on one, verify:


The policy is current. Check the Expires field in security.txt or the last-updated date on the policy page. A policy from 2018 with no updates may not reflect current intent.


Safe harbor exists. The policy should explicitly say they won't pursue legal action against researchers acting in good faith within scope. If it doesn't say this, ask before testing. No safe harbor is a genuine risk, especially for programs without platform backing.


There's a real contact. security@company.com should work. Test it with a non-sensitive inquiry first if you're unsure. Some companies list a contact and then never respond.


The bounty terms are explicit. "We may reward findings" is not a bounty program. "We pay $500-$5000 based on severity" is. Know which you're dealing with before you spend 20 hours on a target.



Legal Protection Differential
This is the honest risk assessment: direct programs offer less structural legal protection than platform programs. When you submit through H1, there's a contract between H1 and the company, H1's terms cover certain researcher protections, and there's a paper trail.
With direct programs, you're relying entirely on the company's written policy and their willingness to honor it. Most companies act in good faith. But the institutional backstop isn't there.
Mitigations:

Test only what the scope explicitly covers
Document everything: timestamps, screenshots of the policy as it existed when you tested, all communications
Stay well within the safe harbor conditions (no accessing real user data, no exfiltration beyond proof, prompt reporting)
If a company has no safe harbor language and is testing a target involving significant user data, skip it or ask for written confirmation first


Communication Dynamics
Without a triage team in the middle, you're often talking directly to a security engineer. This is usually better. They understand the technical nuance, they can escalate internally, and they have context about their own architecture.
The downside: if that engineer is the only security person and they're busy, your report can sit for a while. There's no SLA enforcement. Follow the escalation sequence from Responsible Disclosure if you go silent.

Payout Process
Direct programs pay via varying methods: wire transfer, PayPal, Wise, gift cards (avoid these, they're a devaluation), or company credits. Ask about payment method and timeline before investing significant effort if you care about the payout mechanics.

Examples of Solid Direct Programs
Don't list specific program URLs here since they change, but the types of companies that run good direct programs: large tech companies with established security teams, financial institutions under regulatory pressure to demonstrate security posture, and cloud infrastructure providers who know their customers care about security.
Avoid: programs from companies with no disclosed security team, programs where the bounty language is vague or non-committal, programs in jurisdictions with aggressive computer crime laws and no explicit safe harbor.

Related

HackerOne
Bugcrowd
Intigriti
Reading Scope
Responsible Disclosure
