# HackerOne

> tags: programs

> related: Programs/Platforms/Direct-Programs, Programs/Platforms/Bugcrowd, Programs/Platforms/Intigriti, Programs/Selection/Competition-Assessment, Programs/Selection/Payout-Analysis

HackerOne
HackerOne is the biggest platform in the space. More programs, more researchers, more competition. Your experience on H1 depends heavily on which tier of programs you're working.

Signal and Reputation
H1's reputation system is built around Signal. Signal is a rolling average of your accepted reports versus your total reports, with low-severity and informational reports dragging it down. It's designed to measure report quality, not quantity.
Key thresholds:

Signal above 1.0 is the baseline to look credible
Most private programs filter invites by signal score
A flood of N/A reports early in your career is hard to recover from quickly
Duplicate reports don't hurt signal, but informational reports do

Don't chase volume early. Five well-researched reports that all resolve valid beat twenty spam reports every time on this platform. The signal mechanics punish the spray-and-pray approach.

Reputation Points
Reputation is a separate number from signal. It accumulates based on bounty amounts and severity ratings you receive. It's mostly cosmetic in terms of platform mechanics, but it's a visible proxy for seniority that programs look at when deciding who to invite.
High reputation + high signal = invitation to better private programs. That's the flywheel.

Getting Invited to Private Programs
Private programs on H1 are where the best payout-to-competition ratios live. The invite mechanics:

H1 periodically runs automated invitation batches based on signal, reputation, and domain specialty
Some programs manually review researcher profiles and invite directly
A few programs use "managed" invites through H1 staff

Things that speed up private invites:

A public portfolio with validated findings (even small ones)
Signal above 2.0 consistently
Finding valid bugs on public programs in the same industry vertical the private program is in
H1 CTFs, when they run, can boost profile visibility

Don't ask programs to invite you. It looks desperate and doesn't work. Build the profile and wait.

Triage Quality Varies Wildly
This is the honest reality of H1: the triage experience depends almost entirely on which program you're dealing with. Some programs have excellent in-house security teams who triage quickly, communicate clearly, and pay fast. Others outsource triage to H1's managed triage service or third-party vendors, and the quality varies from "pretty good" to "actively hostile."
Signs of a well-run program:

Median time to first response under 2 days
Median time to bounty under 30 days
Response rate above 90%
Public disclosed reports show consistent, clear communication

Signs of a poorly-run program:

First response takes 2+ weeks
Reports sitting "triaged" for months with no update
Lots of N/A decisions on borderline findings that are clearly valid
Disclosed reports where researchers are visibly frustrated in comments

Check the program's stats on their H1 page before spending serious time on it. The stats are public and they tell you a lot.

Program Stats Worth Checking
On any H1 program page, look at:

Response efficiency: % responded, % resolved, median times
Bounty table: Maximum and minimum payouts by severity
Reports resolved (all time): Higher number means more researched attack surface. Could mean fewer easy wins or a mature security team.
Thank you researcher count: Rough gauge of active researcher population


Platform Fees
H1 takes a fee from programs on top of the bounty they pay you. As a researcher, this doesn't directly affect your payout, but it affects how programs price their bounty tables. Some programs on H1 have lower bounty tables specifically because of platform overhead. Direct programs sometimes pay more for this reason. See Direct Programs.

Disclosures
H1 has a disclosure system where you can request public disclosure after a report is closed/resolved. Programs can approve or deny. Approved disclosures are valuable for your portfolio. Request them on significant findings once the program has patched.

Related

Bugcrowd
Intigriti
Direct Programs
Competition Assessment
Payout Analysis
