# Bugcrowd

> tags: programs

> related: Programs/Platforms/HackerOne, Programs/Platforms/Intigriti, Programs/Selection/Reading-Scope, Programs/Selection/Payout-Analysis

Bugcrowd
Bugcrowd is H1's main competitor for enterprise programs. The platform feels different in practice: different severity taxonomy, different triage model, different community culture. Worth understanding both if you're serious about this.

The VRT (Vulnerability Rating Taxonomy)
Bugcrowd doesn't use CVSS scores the way most other platforms do. They use their own Vulnerability Rating Taxonomy, which maps vulnerability types and contexts to a P1-P5 priority rating. This is both its strength and its frustration.
The VRT is public at github.com/bugcrowd/vulnerability-rating-taxonomy. Read it. Seriously, read it before submitting to Bugcrowd programs. The taxonomy tells you exactly how Bugcrowd's triage team will classify your finding, which tells you what priority (and therefore what bounty band) to expect.
graph TD
    A[Your Finding] --> B{VRT Classification}
    B --> C[P1: Critical]
    B --> D[P2: High]
    B --> E[P3: Medium]
    B --> F[P4: Low]
    B --> G[P5: Informational]
    C --> H[Top of bounty table]
    D --> I[High band]
    E --> J[Mid band]
    F --> K[Low band / $0]
    G --> L[$0, usually no fix required]

Where the VRT helps: consistency. A self-XSS is always P5 across all Bugcrowd programs. You won't waste time on it. An unauthenticated RCE is always P1. The categories are well-defined.
Where it frustrates: context matters, and the VRT is coarse. An XSS that's technically P3 but enables admin account takeover might still pay P3 rates even when the business impact warrants more. Push back in these cases with a strong impact statement, but know the taxonomy is what triage will anchor to.

VRT vs CVSS






























FactorCVSSBugcrowd VRTBasisBase, temporal, environmental vectorsVulnerability type + contextFlexibilityHigh, researcher-definedLow, taxonomy-definedConsistencyVaries by reporterHigh across programLearning curveSteep for new researchersLower, just read the taxonomy
CVSS knowledge still matters because it's what H1 programs and direct programs tend to use. But on Bugcrowd, the VRT is the language. Speak it.

Priority Queue Mechanics
Bugcrowd uses a priority queue for report routing. Higher priority (P1/P2) reports route to more experienced triage staff and get faster attention. P4/P5 reports can sit for a while.
Programs set their "minimum payout priority" in their bounty table. If a program only pays P3 and above, a P4 finding gets triaged but doesn't earn a bounty. Check this before submitting low-severity items.

Kudos System
Bugcrowd has a Kudos system separate from bounties. Kudos are points awarded for valid findings, with multipliers for higher severity. Your Kudos score feeds into your researcher ranking and affects which programs you can access.
Unlike H1's signal, Kudos are additive. Submitting and receiving a valid P4 adds Kudos without penalizing you for the lower severity. This makes Bugcrowd's reputation system slightly more forgiving for researchers building up from lower-severity finds.

Triage Model
Bugcrowd uses a centralized triage model for many of their managed programs. A Bugcrowd triage analyst reviews your report first, then escalates to the program's security team if it validates. This has tradeoffs:
Good: Triage analysts know the VRT cold. Decisions are usually consistent with the taxonomy. You get faster first responses on many programs.
Bad: The triage layer adds distance between you and the program's engineers. Nuanced vulnerabilities that need context sometimes get misclassified. Follow-up conversations can feel like you're talking to a middleman.
For straightforward vulns that map cleanly to the VRT, Bugcrowd's triage is fine. For complex chains or logic flaws that need explanation, be extra thorough in your initial report because revision cycles through managed triage are slow.

Bugcrowd vs H1: The Practical Difference

H1 has more total programs and more name-brand targets
Bugcrowd has a stronger enterprise/corporate program presence
H1's private program ecosystem is larger and harder to break into initially
Bugcrowd's VRT gives clearer expectations upfront
Both have highly variable triage quality depending on the specific program

Run both. Some programs are exclusive to one platform.

Related

HackerOne
Intigriti
Reading Scope
Payout Analysis
