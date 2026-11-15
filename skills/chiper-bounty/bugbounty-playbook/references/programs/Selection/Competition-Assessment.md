# Competition Assessment

> tags: programs, methodology

> related: Programs/Selection/New-Programs, Programs/Selection/Payout-Analysis, Programs/Platforms/HackerOne, Programs/Platforms/Intigriti

Competition Assessment
Finding a vulnerability is only half the battle. If someone else finds it first, you get a duplicate and nothing else. Competition assessment is how you estimate the odds of that happening before you commit your time.

Why Competition Matters More Than Bounty Size
I've skipped programs with $50,000 critical bounties because they had 300+ active researchers and every logical attack surface had been tested. I've spent real time on programs paying $500 for high severity because they had 15 reported researchers and a complex application that required domain expertise most people don't have.
The ratio of expected finding rate to researcher density is what determines your actual return. High bounties plus high competition equals low expected value per hour.

Signals for Researcher Count
No platform gives you a real-time researcher count per program, but you can triangulate:
Disclosed report volume: Programs that have disclosed hundreds of reports publicly have been researched heavily. Programs with 10-20 disclosed reports are either new, private with limited invites, or less popular. All three can be good for you.
Researcher thank count (H1): The "Hackers Thanked" number on H1 program pages counts unique researchers who received bounties or recognition. It's a floor estimate of researchers who've been active. Programs with 500+ researchers thanked have significant coverage already.
Age of program: Older programs have more historical coverage. A program launched 3 months ago has had far less time to accumulate researcher attention than one launched 5 years ago.
Program popularity signals: Being featured in platform newsletters, tweeted about by prominent researchers, or referenced in write-ups drives traffic. Programs that have had public write-ups appear for their findings attract more researchers.

Duplicate Rate as a Signal
If a program's disclosed reports show lots of N/A decisions with "duplicate" language in comments, the program is overworked. High duplicate rates indicate:

Active researcher population is large
The obvious bugs are being found simultaneously
You need to work the non-obvious surface to have unique findings

Some programs publish their duplicate rate directly. H1 doesn't surface this cleanly, but you can often infer it from researcher comments in disclosed reports.

The Sweet Spot
You're looking for programs that have:

Enough scope to be interesting (complex app, wide subdomain space, rich API surface)
Not so much competition that everything obvious is gone
A history of paying valid findings (disclosed reports confirm this)
Bounty table that justifies the time investment

flowchart TD
    Q{Bounty vs Competition?}
    Q --> HB_LC["High Bounty + Low Competition<br/>= Best ROI"]
    Q --> HB_HC["High Bounty + High Competition<br/>= High risk, high reward"]
    Q --> LB_LC["Low Bounty + Low Competition<br/>= Volume grind only"]
    Q --> LB_HC["Low Bounty + High Competition<br/>= Not worth your time"]

    HB_LC --> Ex1["New private programs,<br/>mid-size SaaS fresh launches"]
    HB_HC --> Ex2["Established big tech<br/>(Google, Meta)"]
    LB_LC --> Ex3["Small programs<br/>nobody has looked at"]
    LB_HC --> Ex4["Old public programs,<br/>overworked startup VDPs"]

    style HB_LC fill:#2d6a2e,color:#fff
    style LB_HC fill:#8b2020,color:#fff

The upper-left quadrant is where you want to spend your time. Low competition plus reasonable bounty.

Finding Programs in the Sweet Spot
New programs: Just launched programs are the best opportunity. See New Programs for first-blood tactics.
Niche vertical expertise: If you understand healthcare, fintech, or automotive systems better than the average researcher, programs in those verticals have fewer qualified competitors. Domain expertise reduces effective competition.
Non-English programs: Programs with primarily non-English documentation or interfaces attract fewer researchers who don't speak those languages. Intigriti EU programs have this characteristic to some degree.
Complex authentication flows: Programs built on complex multi-tenant architectures, complex authorization models, or specific technology stacks (SAP, Oracle, custom enterprise software) attract fewer researchers because they require more ramp-up time. That ramp-up time is a moat once you have it.
Private programs with limited invites: By definition, capped invitation counts limit competition. The invite filter already reduces your field.

Using Resolved Report Counts Intelligently
Total resolved reports tells you how much historical coverage a program has received. But it doesn't tell you the current rate of activity.
A program with 2,000 resolved reports over 5 years might be getting 5 new reports per month now. A program with 200 resolved reports in 6 months might be getting 50 per month. The second is more competitive despite having fewer total reports.
Look for: total resolved count plus the date range if visible. If you can see recent activity rates from public reports with dates, even better.

When Duplicate Risk Is Acceptable
Sometimes a high-competition program is worth it anyway:

The bounty ceiling is high enough that even a low hit rate pays well
You have a specific technique or approach you're confident is novel
You're using the program primarily to build skills on a well-scoped target
The program has a fast payout cycle and you're running volume on medium/low severity

Know why you're there. "Everyone's on this program and the bounties are huge" is not a strategy. "I know this tech stack better than most researchers and I have a specific angle to test" is.

Related

Payout Analysis
New Programs
HackerOne
Intigriti
