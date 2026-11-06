# Reading Scope

> tags: programs, methodology

> related: Reporting/Impact-Statements, Programs/Platforms/Direct-Programs, Reporting/Responsible-Disclosure, Programs/Selection/New-Programs, Programs/Selection/Competition-Assessment

Reading Scope Documents
The scope document is a contract. It defines what you're allowed to test, what you're not allowed to test, and what the program will pay for. Getting this wrong costs you bounties at best and legal exposure at worst. Read it before you do anything else.

What Scope Docs Cover
A typical scope document has:

In-scope targets: Domains, IP ranges, mobile apps, APIs
Out-of-scope targets: Explicit exclusions
Out-of-scope vulnerability classes: Common exclusions like rate limiting, missing headers, self-XSS
Rules of engagement: What testing methods are allowed
Reward criteria: What severity levels pay what, sometimes with specific conditions
Safe harbor language: Their commitment not to pursue legal action

Read all of it. The exclusions matter as much as the inclusions.

Wildcard Notation
*.example.com means all subdomains of example.com. It does not mean example.com itself (the apex domain). If the apex isn't listed separately, it may not be in scope.
What's included by *.example.com:

app.example.com
api.example.com
mail.example.com
dev.internal.example.com (yes, third-level subdomains are included)

What's NOT included:

example.com (apex)
example.co.uk (different TLD)
notexample.com (different domain)

Some programs write *.example.com and actually mean "the main app." When in doubt, ask. Out-of-scope findings don't get paid and can get you flagged.

Common Exclusions and What They Mean
"Third-party services are out of scope": If the company uses Salesforce, Zendesk, AWS, Cloudflare, etc., vulnerabilities in those products belong to the vendor's program, not this one. Misconfigurations in how the company uses those services may still be in scope.
"Social engineering and phishing are out of scope": You can't pretend to be IT support to phish credentials. You can test technical phishing vectors like open redirects if the rest of the scope allows it. (Note: open redirects as standalone findings are usually also out of scope - see Impact Statements.)
"Denial of service is out of scope": Don't run stress tests, brute force at scale, or anything that could impact availability. Some programs carve out a specific exception for "proof of concept DoS without production impact."
"Automated scanning is prohibited": Means don't point Burp Scanner, Nikto, or similar tools at their production systems. Some programs mean this, some list it and then don't care about light enumeration. Err on the side of caution.
"Self-XSS is out of scope": XSS that only affects your own session (you have to paste something into your own browser console to trigger it) doesn't qualify. XSS that affects other users does.

Ambiguous Language and How to Interpret It
Programs are written by humans and sometimes have ambiguity. Common situations:
*"All .example.com properties" combined with a specific list of exclusions: The exclusion list is authoritative. If something isn't on the exclusion list, it's probably in scope, but the phrase "all properties" might have been written to be permissive without the author thinking through every subdomain.
"Mobile apps" without version specifics: Test the current production version. Don't dig up ancient versions unless the program specifically mentions them.
"APIs" without specific endpoints: Generally means the APIs served by the in-scope domains. Doesn't mean every internal API you can enumerate.
No mention of authenticated vs unauthenticated testing: You can test as an authenticated user with an account you control. You can test for privilege escalation between account types. You typically can't test without an account on a platform that requires one.
When something is genuinely ambiguous and you've spent significant time on a potential finding, ask before submitting. A one-sentence question to the program inbox protects you from a wasted report.

Rules of Engagement
Take these seriously. Common rules:

Don't test on production if a staging environment is provided
Don't access, modify, or exfiltrate real user data
Use only accounts you own or have permission to use
Report findings promptly after discovery (some programs have a specific window)
Don't discuss unresolved findings publicly

Breaking rules of engagement voids your safe harbor. If the program offers a test environment and you test production instead, you're on your own legally if something goes wrong.

When to Ask for Clarification
Ask when:

A subdomain or asset is logically connected to the in-scope targets but isn't explicitly listed
An exclusion seems to conflict with an in-scope target
You've found something that only partially overlaps with the stated scope
The policy hasn't been updated in over a year and the company's infrastructure has clearly changed

Ask once, ask specifically. "Is api-v2.example.com in scope?" is a good question. "Can you clarify your scope?" is not.
Keep the response. If they say it's in scope via email and then try to reject your report for being out of scope, you have the exchange.

Scope as Attack Surface Prioritization
Reading scope also tells you where to focus. If a program has a large wildcard scope but explicitly excludes their marketing site and their internal HR tools, they're telling you where the interesting stuff is: the product. Start there.
Programs that list specific high-value assets explicitly (main app, admin portal, payment API) are signaling where they expect the most research.
graph LR
    A[Read scope doc] --> B{In-scope targets}
    B --> C[Wildcard domains]
    B --> D[Specific apps]
    B --> E[APIs]
    A --> F{Exclusions}
    F --> G[Reduce surface]
    C --> H[Enumerate subdomains]
    D --> I[Deep test specific features]
    E --> J[Auth, IDOR, injection]
    H & I & J --> K[Prioritized test plan]


Related

Direct Programs
Responsible Disclosure
New Programs
Competition Assessment
