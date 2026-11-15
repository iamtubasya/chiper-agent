# Starting a Program

> tags: business, programs

> related: Business-of-Bounties/For-Organisations/Scoping-a-Program, Business-of-Bounties/For-Organisations/Choosing-a-Platform, Business-of-Bounties/For-Organisations/Setting-Bounty-Tables, Business-of-Bounties/For-Organisations/Researcher-Relationships, Business-of-Bounties/For-Organisations/The-Business-Case, Business-of-Bounties/Running-a-Program, Reporting/Responsible-Disclosure, Programs/Selection/Reading-Scope

Starting a Program
I've started a vulnerability disclosure program from scratch and transitioned it into a paid bug bounty program. The single biggest mistake I see organisations make is launching a bounty program before they're ready for one. You get buried in noise, your engineering team resents the security team, and you burn through budget on findings you could have caught with a scanner.
The right sequence matters more than the right platform.

The Maturity Spectrum
Most organisations think the choice is binary: have a bug bounty program or don't. In reality there's a spectrum, and where you start depends on how mature your security posture is today.
flowchart LR
    A["No policy"] --> B["security.txt"]
    B --> C["VDP"]
    C --> D["Private BBP"]
    D --> E["Public BBP"]
    B -.->|"some orgs skip VDP"| D

Each stage builds on the last. Most organisations should go through them in order, but not all of them do.

Start with a Vulnerability Disclosure Policy
A Vulnerability Disclosure Policy is not a bug bounty program. There's no money. It's a public commitment that says: if you find a security issue, here's how to report it, and here's our promise not to sue you for doing so.
That's it. No bounty table, no triage team, no platform fees. Just a policy page on your website and a monitored inbox.
Why VDP First
You discover your own gaps before paying others to find them. The first wave of reports on any new program are low-hanging fruit: default credentials, exposed admin panels, missing authentication on internal tools, outdated software with public CVEs. If you're paying bounties for findings your own vulnerability scanner should have caught, you're wasting money.
A VDP surfaces this for free, but be realistic about who reports to a VDP. Most experienced researchers won't spend serious time on an unpaid program. They have bills, they have paid programs competing for their attention, and "exposure" doesn't pay rent. The reports you get on a VDP will come from newer researchers building their reputation, hobbyists, and the occasional experienced researcher who happens to stumble on something while looking at your stack for other reasons. That's still valuable for catching low-hanging fruit and building your process, but don't expect the same depth or volume you'd get from a paid program.
Your internal processes aren't ready for volume. A bug bounty program generates reports. Reports need triage. Triage needs to route to engineering. Engineering needs to prioritise, fix, verify, and close the loop. If any part of that pipeline doesn't exist yet, reports pile up, researchers get frustrated, and your program's reputation suffers before it starts.
A VDP gives you low-volume practice. You'll receive a handful of reports per month instead of dozens per week. That's enough to build the triage workflow, train your team on severity assessment, establish SLAs with engineering, and figure out who owns what.
It establishes legal safe harbor. Before anyone tests your systems, you need a legal framework that protects both sides. Your legal team needs to draft safe harbor language, define scope, set rules of engagement, and get sign-off from leadership. Doing this under VDP pressure (low volume, no money) is much easier than doing it while a paid program is already running and researchers are asking why their reports haven't been triaged.
It shows you what your actual attack surface looks like. Most organisations are surprised by the first round of external reports. Assets they forgot about, acquisitions that never got integrated, shadow IT that the security team didn't know existed. A VDP surfaces this cheaply. You can then reduce your attack surface before launching a paid program, which means you're paying bounties for real findings instead of cleanup.
What a VDP Needs
At minimum:

A security.txt file at /.well-known/security.txt (RFC 9116). This is how researchers find your reporting channel.
A policy page describing scope, rules of engagement, and safe harbor. Host it at a stable URL.
A monitored contact channel. Email works. A web form works. Whatever it is, someone needs to check it regularly.
An acknowledgment SLA. Commit to acknowledging receipt within a defined window. Five business days is standard.
Internal routing. When a report comes in, who reads it? Who validates it? Who assigns it to engineering? Define this before the first report arrives.

You don't need a platform. You don't need a triage team. You need a policy, an inbox, and a process.
The honest tradeoff: a VDP is great for building your internal pipeline and catching obvious issues, but it won't attract the researchers who find the hard bugs. Think of it as the training wheels stage. You're building the muscle to run a paid program, not trying to get free security testing. If your organisation has the budget and the maturity to skip it, the section below covers when that's the right call.

Going Straight to a Paid Program
Not every organisation needs the VDP stage. Some skip it entirely and launch directly into a private bug bounty program. This can work, but only under specific conditions.
When Skipping VDP Makes Sense
You already have a mature security program. Your team runs regular pentests, has internal red teaming, runs vulnerability scanners on a schedule, and has a well-defined SDLC with security gates. The low-hanging fruit is already gone. A VDP would mostly surface things you already know about. Paying for researcher time from day one gets you the deeper findings faster.
You're a tech company with security engineering resources. Startups and tech companies with experienced security teams often have the internal tooling and triage capacity to handle paid reports from the start. They don't need a VDP warm-up period because the pipeline already exists for their internal security work. Adding external researchers is just another input to an existing process.
You have budget and executive buy-in already secured. If leadership has already approved a bounty budget and understands the ongoing cost, the VDP stage is mostly about building internal process. If that process already exists, the VDP isn't adding value.
You want to attract top researchers immediately. The best researchers prioritise paid programs. A VDP will get reports from people building their reputation and hobbyists, which is valuable, but it won't attract the researchers who find the critical bugs. If your threat model demands that caliber of testing, paying from day one is the incentive that brings them in.
The Risks of Skipping VDP
Even when the conditions above are met, skipping VDP comes with trade-offs:
You'll pay for findings you could have caught internally. Even mature organisations are surprised by what external researchers find in the first weeks. If your scanner coverage has gaps (and it does), you're paying bounties instead of running a free scan. Budget for a higher first-quarter spend and treat it as an audit.
Your triage process is untested with external input. Internal security workflows and external researcher workflows are different. Researchers submit reports in different formats, with different severity interpretations, and with different expectations around response time. If your team has never handled external reports before, the first wave of a paid program is where you learn. That learning costs money.
Scope disputes are more expensive. When a researcher finds something in a gray area on a VDP, the cost of a scope dispute is reputation. When they find it on a paid program, the cost is reputation plus the bounty conversation. Getting your scope tight before money is on the table is cheaper.
If your organisation has the maturity to handle these trade-offs, going straight to a private BBP is a legitimate path. Most of the programs that do this successfully are technology companies with existing security teams of five or more people.

When You're Ready for a Paid Program
The signal that you're ready to move from VDP to a paid bug bounty program isn't a date on a calendar. It's a set of conditions.
Your VDP pipeline works. Reports come in, get triaged within your SLA, get routed to engineering, get fixed, and get closed. Researchers hear back. Average time-to-fix is something you can measure and defend.
Low-hanging fruit is gone. You've addressed the findings from your VDP. Your scanners run regularly. Known vulnerabilities in your external surface are patched. You're not going to pay $500 for a finding that Nuclei would have caught.
Engineering has capacity. Your development teams know that security reports exist, have a process for handling them, and have allocated capacity. If every bounty report becomes an emergency that derails a sprint, your engineering org isn't ready.
You have budget and executive support. Someone with authority has approved a bounty table and a quarterly budget. The security team isn't going to have to fight for every payout. Leadership understands this is an ongoing cost, not a one-time expense.
You can define scope clearly. You know what's in scope, what's not, what vuln classes you care about, and what you'll pay for each severity level. Ambiguous scope generates disputes. Disputes burn researcher goodwill. See Scoping a Program for detailed guidance.

Private Before Public
Start with a private program. Every platform supports this. A private program means you invite specific researchers rather than opening to everyone.
Why:

Controlled volume. You pick how many researchers have access. Start with 10-20. Scale up as your triage capacity allows.
Higher signal-to-noise. Invited researchers on platforms like HackerOne, Bugcrowd, and Intigriti are vetted. They submit better reports with fewer duplicates and invalid findings.
You can iterate. Your scope document, bounty table, and rules will have problems. Better to discover them with 15 experienced researchers than 1,500 people of varying skill levels.
Reputation building. Researchers talk. If your first 20 researchers have a good experience (fast triage, fair payouts, respectful communication), they'll tell others. That reputation matters when you go public.

Most programs stay private for 3-12 months before going public. Some stay private permanently. There's no shame in it.
Launching public on day one is the most common mistake new programs make. You get 200 reports in the first week, 180 of them are noise, your triage team burns out, and the 20 valid findings sit in a queue for months. Start private.

Next Steps
Once you've decided on VDP or BBP and whether to start private, the next decisions are:

Scoping a Program -- Define what researchers can test and how.
Choosing a Platform -- Pick where to host your program.
Setting Bounty Tables -- Get your pricing right.
Researcher Relationships -- Build the relationships that make your program work.
The Business Case -- Sell it internally if you haven't already.

Related

Running a Bug Bounty Program
Responsible Disclosure
Reading Scope
