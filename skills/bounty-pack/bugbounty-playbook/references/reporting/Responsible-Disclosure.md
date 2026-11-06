# Responsible Disclosure

> tags: reporting, methodology

> related: Reporting/Report-Writing, Programs/Selection/Reading-Scope, Programs/Platforms/Direct-Programs

Responsible Disclosure
Responsible disclosure is the agreement, implicit or explicit, between you and the program: you give them time to fix it, they give you credit (and hopefully a bounty) without pursuing legal action. When it works, it works well. When it breaks down, you need to know your options.

The Standard Timeline
The industry standard is 90 days from first contact before public disclosure. Google Project Zero popularized this. Most organizations and researchers treat it as the norm.
flowchart LR
    A["Day 0: Report submitted"] --> B["Day 1-7: Triage"]
    B --> C["Day 8-67: Patch development"]
    C --> D["Day 68-75: Researcher review"]
    D --> E["Day 90: Disclosure deadline"]
    E --> F["Coordinated publication"]
    E --> G["Extension if justified"]

90 days is a starting point, not a hard rule. If the program is making genuine progress and asks for a short extension, it's reasonable to grant it. If they're stalling, it isn't. I've given programs up to 120 days when the fix required infrastructure changes. I've held to 90 when a program went silent for weeks.

What "Coordinated" Actually Means
Coordinated disclosure means you and the program agree on timing and content before anything goes public. In practice:

You notify them before publishing
You give them a chance to push a fix first
You don't include working exploit code that would make exploitation trivial for others
You do publish eventually, timeline or not

Full disclosure (publishing immediately with no notice) is rarely justified and will likely end your relationship with that program and others. Coordinated disclosure is the default.

When Programs Ghost You
It happens. You submit a report through the right channel, wait a week, hear nothing. Here's my escalation sequence:

Day 7: Follow up once in the same ticket/thread. One message, not three.
Day 14: If still no response, try an alternative channel. security@company.com, their security.txt contact, a LinkedIn message to their security team lead if you can find one.
Day 30: Send a formal notice stating your disclosure intent and your intended date (90 days from original submission).
Day 90: Follow through on your stated timeline if there's been no engagement.

Documenting every step matters. If this ever turns into a legal issue, your paper trail is your defense. Keep timestamps on every message.

CERTs and Third-Party Coordination
If you've found a vulnerability affecting a vendor whose product is used widely (not just one company's deployment), coordinating through a CERT makes sense:

CERT/CC (Carnegie Mellon): certcc.cert.org, handles complex multi-vendor cases
CISA (US government systems): cisa.gov/coordinated-vulnerability-disclosure
NCSC (UK): ncsc.gov.uk
BSI (Germany): bsi.bund.de

CERTs are most useful when: the vendor is unresponsive, the vulnerability affects multiple products, or there's a CVE assignment question. For typical bug bounty programs on platforms like HackerOne or Bugcrowd, you won't need them.

Legal Considerations and Safe Harbor
Safe harbor language in a program's policy is your protection. It typically says the company won't pursue legal action against researchers acting in good faith within the defined scope. Read it before testing. If there's no safe harbor clause, that's a risk factor.
What "good faith" usually means in practice:

You didn't exfiltrate real user data beyond what was needed to demonstrate the bug
You didn't access systems outside the defined scope
You reported promptly and didn't exploit the bug for personal gain
You didn't publicly disclose before giving reasonable time to fix

Laws that matter (US context):

CFAA (Computer Fraud and Abuse Act): Still vague, still used to prosecute. Staying in scope is your main protection.
DMCA Section 1201: Relevant if you're reversing software as part of research. Most programs won't care, but it exists.
State laws: Some states have their own computer crime statutes. They largely mirror CFAA.

Outside the US, the legal landscape varies. EU, UK, and Australian laws differ. If you're testing programs based in jurisdictions with aggressive computer crime laws and no clear safe harbor, understand your risk exposure.

When Public Disclosure Is Appropriate
Public disclosure serves a purpose: it warns users, it incentivizes fixes, and it builds collective knowledge. But timing matters.
Disclose publicly when:

The 90-day timeline has passed with no patch and no substantive engagement
The vulnerability is already being exploited in the wild
The program has patched it and you have agreement to publish
You've received explicit written permission

Don't disclose publicly when:

You haven't given the program reasonable time
The fix is in progress and they're communicating actively
You're angry about the bounty amount (bad reason, bad look)
The disclosure would primarily enable mass exploitation of unpatched systems

If you do disclose after a failed timeline, write it up professionally. Document your timeline, your attempts to contact, and their responses (or lack thereof). Don't editorialize about the company being irresponsible unless the facts make the case themselves.

Related

Report Writing
Reading Scope
Direct Programs
