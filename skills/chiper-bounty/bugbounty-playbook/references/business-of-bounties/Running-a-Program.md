# Running a Program

> tags: business, programs

> related: Reporting/, Methodology/Scoping, Business-of-Bounties/Career-Strategy, Business-of-Bounties/Mental-Health

Running a Bug Bounty Program
I've been on both sides of the table. I've submitted over a hundred reports and triaged over five hundred. The two experiences give you a picture that neither side alone can see. This page is about what the inside of a program actually looks like, because understanding it will make you a measurably better researcher.
Why Companies Run Bug Bounty Programs
The honest answer is usually a mix of things, and the mix matters for how a program operates.
Some companies run programs because they genuinely believe in the model. Security leadership pushed for it, they've seen the data on researcher-found vulns versus internal teams, and they treat it as a real investment. These programs have healthy bounty tables, responsive triage, and researchers remember them.
Some companies run programs because a CISO needed something to show the board. "We have a bug bounty program" is a checkbox on a security posture slide. These programs have tiny bounty tables, long triage queues, and the security team is the only person who cares about it.
Most programs are somewhere in between. The security team wants it to work. Finance controls the budget. Legal controls the scope. The result is a compromise that frustrates everyone, researchers included.
Knowing which type of program you're dealing with changes how you should invest your time.
How Programs Are Structured Internally
A typical mid-size corporate BBP looks something like this:
graph TD
    A[Researcher Submits Report] --> B[Platform Triage]
    B --> C{Valid / Not Valid?}
    C -->|Valid| D[Internal Security Team Review]
    C -->|Not Valid| E[Closed: N/A or Informational]
    D --> F{Severity Assessment}
    F --> G[Engineering Team Notified]
    G --> H[Fix Developed]
    H --> I[Fix Verified]
    I --> J[Bounty Paid + Report Resolved]
    F --> K[Disputed or Scope Question]
    K --> D

The piece researchers rarely see is the gap between "Internal Security Team Review" and "Bounty Paid." That gap is often filled with: getting an engineering team to acknowledge the issue, getting it prioritized against other work, getting a fix reviewed, and then getting finance to cut a payment. On a slow report, that entire chain can take months. It's not always that the program doesn't care. It's often that the security team has no control over engineering velocity.
How Triage Actually Works
Platform triage (on HackerOne, Bugcrowd, etc.) is the first filter. These are often full-time triagers who are reviewing hundreds of reports a week across many programs. They're looking for: is this in scope, is this a real vulnerability, is this a duplicate, is the impact clearly stated.
They are not doing deep technical analysis on every report. They don't have time. If your report requires significant effort to understand whether it's valid, it will often be closed or deprioritized ahead of reports that make the case clearly.
The reports that move fast: clear reproduction steps, clear impact statement, obvious scope, severity that matches the finding. The reports that sit: vague impact, requires the triager to extrapolate, missing reproduction steps, or theoretical vulnerabilities with no concrete proof.
What triagers are actually penalized for: approving invalid reports. A false positive that gets to an engineering team wastes their time and reflects badly on triage. This is why borderline reports sometimes get conservative assessments. If you want a finding taken seriously, remove any reason to doubt it.
How Bounty Tables Get Set
This is the part that explains why some programs feel cheap.
Bounty amounts are almost never set by the security team alone. The process usually involves: security proposing a table, finance pushing back, legal adjusting based on liability concerns, and a compromise landing somewhere that everyone is slightly unhappy with.
The security team knows the market rate. They've seen what HackerOne publishes, they know what researchers expect. They often can't get the budget approved to match it.
The programs that underpay relative to their asset value are usually not doing it out of bad faith. They're doing it because nobody with budget authority has been shown a researcher finding a critical vulnerability and saying "this is what we paid for it." Until that happens, bug bounty is an abstract line item.
What changes bounty tables: evidence. A critical payout on a report that clearly explains business impact gets the security team ammunition to go back to finance and say "this is what good bounty tables produce." Every time a researcher clearly articulates impact in business terms, they're making the case for better bounties, not just for their report but for the ones after it.
What Makes a Researcher Programs Love
I've triaged over five hundred reports. Here is what I remember about the researchers who made my job better:
Clear writing. Not long, clear. A three-paragraph report that includes: what you found, how you reproduced it, what an attacker could do with it. That's it. That's the whole report. Attachments for screenshots and proof-of-concept. Researchers who write well get their reports triaged faster because triagers are humans who appreciate not having to decode a wall of text.
Honest severity. If you found a stored XSS that requires a very specific victim interaction and limited blast radius, submit it as a medium, not a critical. Programs remember researchers who consistently assess severity accurately. Researchers who consistently oversell get their reports scrutinized harder because triage has learned they need to discount the claimed severity.
Good faith on edge cases. Scope is imperfect. Sometimes a great find is in a gray area. The researchers who handle this well: acknowledge the ambiguity in the report, explain why they think it's worth reviewing, and let the program decide. The researchers who handle it poorly: submit aggressively and argue about scope in every comment.
No ultimatums. "I will publish in 48 hours" messages, threats to report to regulators, public pressure tactics: these end working relationships and sometimes legal ones. Legitimate disclosure concerns are worth raising. There's a professional way to raise them that doesn't involve threats.
Understanding This Makes You a Better Researcher
When you know that triage is working a queue and clear reports move faster, you write clearer reports.
When you know that bounty tables are set by people who need business justification, you write better impact statements.
When you know that the triager's job is pattern matching under time pressure, you write reports that match the pattern of valid findings, not reports that require creative interpretation.
The researchers who treat programs as adversaries to be beaten get worse results than the researchers who treat them as organizations with internal constraints and humans trying to do their jobs. Both sides are trying to get to the same place: found bug, fixed bug, paid researcher. The path there is smoother when you understand what the path looks like from the other end.
See also: Reporting, Scoping, Career Strategy, Mental Health