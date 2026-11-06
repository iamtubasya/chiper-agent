# Target Selection

> tags: methodology, beginner, intermediate

> related: Methodology/Scoping, Programs/, Recon/

Target Selection
The single biggest factor in whether you find bugs isn't your skill level. It's your target.
A great hunter on a hardened target with 200 active researchers finds nothing. An average hunter on a fresh program with a wide scope and messy codebase finds a P1 in their first session. That's not luck, that's selection.
The Target Selection Matrix
flowchart TD
    Q{Payout vs Competition?}
    Q --> HP_LC["High Payout + Low Competition<br/>= Sweet Spot"]
    Q --> HP_HC["High Payout + High Competition<br/>= Established Goldmines"]
    Q --> LP_LC["Low Payout + Low Competition<br/>= Skill Sharpeners"]
    Q --> LP_HC["Low Payout + High Competition<br/>= Not Worth It"]

    HP_LC --> Ex1["New programs, mid-tier SaaS,<br/>fintech with wide scope"]
    HP_HC --> Ex2["Big tech: Google, Meta<br/>Mature programs, tight scope"]
    LP_LC --> Ex3["Gov/DoD VDP,<br/>VDP with no payout"]
    LP_HC --> Ex4["Picked-over programs<br/>with low rewards"]

    style HP_LC fill:#2d6a2e,color:#fff
    style LP_HC fill:#8b2020,color:#fff

You want to be in that top-left quadrant as much as possible. New programs with decent payouts and wide scope. The window closes fast though. Within a few weeks every recon bro with an automated pipeline has already grabbed the low-hanging fruit. But those first few weeks are gold.
Signals of a Good Target
Wide scope. *.example.com is infinitely better than "only test app.example.com/dashboard." Wide scope means more attack surface, more forgotten assets, more interesting chains across subdomains.
Complex application. SaaS products with user roles, payment flows, file uploads, integrations, API endpoints. More features means more places things break. A brochure site with a contact form isn't worth your time.
Active development. Check their changelog, blog, or GitHub. Frequent deploys mean new code, new features, new bugs. Stale apps have already been picked over.
Reasonable response times. Check platform stats. Programs where average first response is 30+ days will drain your motivation. You want feedback loops.
No weasel clauses. Read the policy. Some programs have language that lets them acknowledge your bug and pay nothing. Walk away.
Signals to Avoid
Tiny scope with high payouts. If the scope is a single endpoint and the bounty table goes up to $50k, they're either confident it's hardened or they'll find a reason to downgrade your findings. Either way, poor ROI.
500+ resolved reports and 50+ active hackers. The obvious stuff is gone. You can still find things but you'll spend 10x the time for findings that are more likely to be duped.
Shady duplicate handling. Check the reviews on the platform. Researchers talk. If three different people mention dodgy duplicate handling, believe them.
My Approach
I keep a rotation of 3-5 active targets at any time. When I sit down to hunt I pick based on energy level:

High focus day - Deep dive on a complex target. Business logic, auth flows, chain development.
Medium focus - New recon on a target I haven't mapped yet. Content discovery, JS analysis.
Low energy - Run automation against my target list, review nuclei output, check for new subdomains.

This keeps things from getting stale. If I'm stuck on one target I switch to another. Come back in a week with fresh eyes and you'll often see things you missed.
First Blood Strategy
New programs are gold. Here's my first 48 hours:

Immediately - read the full scope doc, understand the product, sign up for an account
Hour 1-2 - subdomain enumeration, port scan top ports, screenshot everything with gowitness
Hour 2-4 - tech stack profiling, identify interesting assets, deprioritize static content
Hour 4-8 - deep dive on the most promising 2-3 assets, focus on auth and IDOR first
Day 2 - JS analysis on the main app, API endpoint discovery, parameter fuzzing

The goal is a valid submission within 48 hours. Doesn't have to be critical. An early valid report establishes you on the program, gives you signal/reputation, and usually means faster triage on subsequent reports.
See Also

Scoping & Rules of Engagement
Program Strategy
Recon
