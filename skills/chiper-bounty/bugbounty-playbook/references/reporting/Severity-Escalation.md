# Severity Escalation

> tags: reporting, intermediate, advanced, polished

> related: Methodology/Chain-Thinking, Reporting/Impact-Statements, Reporting/Report-Writing

Severity Escalation
Your finding is worth what you can convince the triage team it's worth. CVSS is a guideline, not a law. Bounty tables have ranges, not fixed amounts. The report that clearly articulates real-world impact gets the higher payout.
This isn't about inflating severity dishonestly. It's about doing the work to demonstrate the actual impact, because triagers defaulting to the lowest plausible severity is a well-documented pattern.
The Severity Assessment Flow
flowchart TD
    A["Found a vulnerability"] --> B["What can an attacker do with this?"]
    B --> C{"Concrete impact?"}
    C -->|"Yes"| D["Document full exploitation scenario"]
    C -->|"Leads to something"| E["Build the chain"]
    C -->|"Theoretical only"| F["Be honest about limitations"]

    D --> G{"Maps to bounty table?"}
    G -->|"Yes"| H["Reference their category"]
    G -->|"Falls between categories"| I["Argue for higher with justification"]
    G -->|"Class they haven't considered"| J["Educate on business impact"]

    E --> D
    F --> K["Submit at accurate severity"]

Escalation Strategies by Severity Tier
Informational → Low
Triager marked it informational because they don't see exploitability. You need to prove the finding has security relevance.
What works:

Show the disclosed information helps an attacker. Stack traces leak framework versions, version-specific CVEs exist. Internal paths leak, directory structure aids further enumeration.
Demonstrate the behaviour violates their own security headers/policy. If they set X-Content-Type-Options but you found a path where it's missing, that's a control failure, not just a curiosity.
Reference compliance requirements if applicable. PCI-DSS scoped targets treat information disclosure findings more seriously because auditors flag them.

What doesn't work:

"This could be used in a phishing attack" with no concrete scenario.
Pointing to OWASP as if it's legislation.

Low → Medium
The gap between low and medium is usually about who is affected and what they lose.
What works:

Demonstrate user impact, not just theoretical exploitation. "An attacker can leak any user's email via IDOR on /api/user/{id}/profile" is medium. "The endpoint exposes user data" is low.
Show scale. One user affected = low. All users enumerable = medium or higher.
If the finding requires authentication, prove any authenticated user can exploit it (not just users with special roles). Broad attacker pool means higher severity.

Medium → High
This is where most severity arguments happen. The difference usually comes down to one of these:
Demonstrate impact on confidentiality at scale. Medium: "I can read another user's profile." High: "I can enumerate all 500,000 user profiles including email, phone, and billing addresses using sequential IDs."
Demonstrate impact on integrity of sensitive actions. Medium: "I can modify my own profile fields that should be read-only." High: "I can modify another user's account settings including their email address, enabling account takeover via password reset."
Prove the attack is practical. Medium findings often get that rating because the triager thinks exploitation is unrealistic. Walk them through the attack scenario step by step. If it requires user interaction, explain how a realistic phishing scenario would deliver the payload. If it requires specific timing, demonstrate it works reliably.
High → Critical
Critical is reserved for findings that compromise the entire system, all user accounts, or core business functions. Getting a finding rated critical usually requires at least one of:

Remote code execution on the server, in a privileged context. Demonstrated, not theoretical.
Full account takeover of any user. Not "I can see their email." You can log in as them.
Access to all user data. Database-level access, or an IDOR/API flaw that allows complete enumeration.
Infrastructure compromise. SSRF to cloud credentials, internal network access, secrets that unlock further access.
Financial impact. Ability to manipulate payments, transfer funds, bypass billing.

The Regulatory Angle
If the target is in a regulated industry (finance, healthcare, government), you have additional leverage for severity arguments. Not every triager will know this, so spell it out.
flowchart LR
    A["Your Finding"] --> B{"Affected data type?"}
    B -->|"PII"| C["GDPR, CCPA"]
    B -->|"Payment cards"| D["PCI-DSS"]
    B -->|"Health info"| E["HIPAA"]
    B -->|"Auth credentials"| F["NIST 800-63, SOC2"]
    B -->|"Financial records"| G["SOX, GLBA"]

    C --> H["Cite regulatory obligations in impact section"]
    D --> H
    E --> H
    F --> H
    G --> H

You're not threatening them with compliance consequences. You're helping them understand the full risk picture. A triager who realises your finding could trigger PCI audit scrutiny is going to escalate it internally, which usually means a higher severity rating and faster resolution.
Example:

The exposed endpoint returns full payment card data (PAN, expiry, cardholder name) for any customer order. Beyond the direct confidentiality impact, this exposure likely constitutes a PCI-DSS Requirement 6.5 violation and may trigger breach notification obligations under applicable state and federal laws.

vs.

This endpoint leaks credit card data.

Same finding. Wildly different response from triage.
When to Push Back
If your report is downgraded and you disagree:

Wait 24 hours. Your initial reaction is emotional. Sleep on it.
Re-read their rationale. Sometimes they're right. If you missed something, accept it.
If you still disagree, respond with evidence, not frustration. Quote their bounty table, reference their own scope document, provide additional PoC that addresses their specific concern.
Escalate via platform mediation if the response is unreasonable. HackerOne and Bugcrowd both have mediation processes. Use them sparingly. Only for clear miscalls, not minor disagreements.
Know when to walk away. If a program consistently undervalues findings, stop testing for them. Your time has a dollar value. Spend it on programs that pay fairly.

Language That Works

























Instead ofTry"This is critical because XSS is in the OWASP Top 10""This stored XSS executes in admin sessions when reviewing user-submitted content, giving an attacker full administrative access""An attacker could steal sensitive data""An attacker can retrieve full name, email, phone, and billing address for any of the platform's ~2M users by iterating the sequential user ID parameter""This could lead to account takeover""I confirmed full account takeover: changed the victim's email, triggered a password reset to my email, and logged in with new credentials. Video attached.""This should be high severity""Per [Program Name]'s bounty table, this falls under 'Access to other users' PII at scale,' which maps to the High tier ($X - $Y)"
The Golden Rule
Demonstrate, don't claim. Every severity argument should be backed by something you can show: a screenshot, a request/response pair, a video, or a PoC script. If you're writing the word "could" more than once in your impact section, you haven't gone far enough in proving exploitability.
See Also

Chain Thinking
Impact Statements That Pay
Report Writing
