# YesWeHack

> tags: programs

> related: Programs/Platforms/Intigriti, Programs/Platforms/HackerOne, Programs/Platforms/Bugcrowd, Programs/Selection/Competition-Assessment, Programs/Selection/Payout-Analysis

YesWeHack
YesWeHack is France's answer to HackerOne and it's grown into the dominant bug bounty platform for European companies outside the Intigriti footprint. If you're already on Intigriti and ignoring YesWeHack, you're leaving a meaningful slice of the European market untouched.

Geographic Reach
YesWeHack is headquartered in Paris and its program list reflects that. Strong presence in:

France (domestic market, heavily represented)
Germany and the DACH region
Benelux
Singapore and Southeast Asia - the platform expanded into APAC earlier than its European competitors

The researcher base is similarly concentrated. US and UK researchers who work exclusively on H1 and Bugcrowd rarely touch YesWeHack. That gap in researcher density is an opportunity, same as Intigriti used to be a few years ago. The window where YesWeHack programs are underworked is real but won't stay open indefinitely.

Researcher Dashboard
The platform's researcher-facing interface has improved consistently. Current features worth knowing:

Mission feed: YesWeHack surfaces active programs and engagement opportunities. The framing as "missions" gives the dashboard a different feel from H1's program list.
Hunter radar: A visualisation of your activity and standing relative to your peers. More gamified than useful, but it gives you a quick read on where you rank.
Report tracking: Reasonable view of open and closed reports across programs. Less cluttered than H1's equivalent in my experience.
Public programmes: YesWeHack's public program list is browsable without an account at yeswehack.com/programs.


Reputation and Ranking
YesWeHack uses a points-based reputation system. Points accumulate from valid findings, weighted by severity. Your score determines your visible rank on the platform and affects invitation priority for private programs.
A few things worth knowing about how it works in practice:

Lower-severity valid finds still contribute, so building rank from the ground up is possible without waiting for critical bugs
Private program invitations use both rank and reported domain specialisation to match researchers to programs
The ranking resets or decays on some metrics - read the platform documentation on decay mechanics so you understand how inactivity affects your standing


GDPR and European Scope
YesWeHack programs skew toward European companies that are GDPR-compliant by necessity. This matters for scope interpretation. Data exposure findings - user PII leakage, unprotected exports, misconfigured data access - tend to get elevated treatment on European programs because the regulatory consequences are real to the companies involved.
Frame your data-related findings with GDPR impact language when relevant. "This endpoint exposes user email addresses without authentication, creating potential exposure under GDPR Article 5" lands differently than a generic description of information disclosure.
The same applies to scope exclusions: European companies are often more conservative about what they allow researchers to access, particularly around real user data. Read the exclusions carefully.

Dojo Training Labs
YesWeHack maintains a training environment called Dojo - a set of intentionally vulnerable practice targets. It's useful for:

New researchers getting familiar with the platform before hunting live programs
Practising specific vulnerability classes in a legal environment
Demonstrating skill to the platform for access to better programs

Dojo is not a substitute for real hunting, but it's a reasonable warm-up resource. Some platforms charge for training labs; YesWeHack's Dojo is free to registered researchers.

Triage Quality
Triage on YesWeHack varies by program, same as every platform. A few patterns worth noting:

French enterprise programs tend to have faster triage than the platform average, possibly because the company headquarters and security teams are more accessible to YesWeHack's customer success team
Programs from smaller companies, particularly those new to running a bounty program, can be slow on first response
The platform does have a managed triage option for programs that opt into it, which adds a layer between you and the company's security team

Check the program's stats for median response times before investing serious effort.

YesWeHack vs. Intigriti
Both platforms target European company programs. The practical differences:

Intigriti has stronger Belgian, Dutch, and UK program presence; YesWeHack's French program list is deeper
Intigriti's live hacking events have higher visibility in the European researcher community
YesWeHack's APAC expansion gives it programs that Intigriti doesn't have
Researcher density on both platforms is lower than H1, but both are growing

Running both is the right call. Their program lists don't overlap heavily.

Related

Intigriti
HackerOne
Bugcrowd
Competition Assessment
Payout Analysis
