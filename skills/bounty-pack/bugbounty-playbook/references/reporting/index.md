# Reporting

> tags: reporting, methodology

> related: Reporting/Report-Writing, Reporting/Severity-Escalation, Reporting/Impact-Statements, Reporting/Report-Templates, Reporting/Responsible-Disclosure

Reporting
The report is the product. Not the bug. The report.
You don't get paid for finding vulnerabilities. You get paid for convincing a triage team (often a junior analyst working through a queue of 50 submissions) that what you found is real, reproducible, and impactful. If your report is two sentences and a screenshot of an alert box, you're leaving money on the table even when you find legit issues.
I've been on both sides of this. Submitted over a hundred reports as a researcher, and also built and run a bug bounty program for a multinational bank. The difference in quality between reports that get paid quickly at full severity versus reports that sit in triage limbo is almost always in the writing, not the finding.
The Reporting Funnel
flowchart TD
    A["You find something"] --> B{"Actually a vulnerability?"}
    B -->|"Maybe"| C["Test deeper first"]
    B -->|"Yes, can demonstrate impact"| D["Write the report"]

    D --> E["Title: specific, descriptive"]
    E --> F["Summary: what + impact"]
    F --> G["Repro steps: exact, copy-paste ready"]
    G --> H["Impact: business language"]
    H --> I["Evidence: screenshots, HTTP requests"]
    I --> J["Suggested fix: optional but appreciated"]

    C -->|"Confirmed"| D
    C -->|"Not exploitable"| K["Don't report it"]

Sections
Report Writing
Anatomy of a report that gets triaged quickly, rated accurately, and paid at the top of the range.
Severity Escalation
How to argue for higher severity when triage undervalues your finding. Frameworks, language, and when to push versus when to accept.
Impact Statements That Pay
Translating technical findings into business risk. The same XSS is worth different amounts depending on how you frame it.
Report Templates
Copy-paste-customise templates by vulnerability class. A starting point, not a crutch.
Responsible Disclosure
90-day timelines, coordinated disclosure, and what to do when programs ghost you.
Common Reporting Mistakes
Writing for other hackers instead of triagers. Your report will likely be read by someone less technical than you. If they can't understand it they can't assess it correctly. Write for a competent developer who doesn't specialise in security.
Skipping reproduction steps because "it's obvious." It isn't obvious. Write the steps as if you're leaving instructions for someone who has never seen the application. Include exact URLs, payloads, and expected responses.
Submitting too early. If you suspect there's a chain but haven't confirmed it, keep testing. A complete chain report is worth dramatically more than a single finding with a note saying "I think this might be chainable." Explore the full impact before you submit.
Submitting too late. Counterpoint to the above: don't sit on a valid finding for weeks trying to chain it. If you've spent a day trying to escalate and can't, submit what you have. Mention the chain potential in your impact section, but get the report in. Someone else might find the same base bug while you're chasing the chain.
Not including raw HTTP requests. Screenshots of Burp are fine. But also include the actual request and response as text that the triager can copy, paste, and replay. Make their job easy.