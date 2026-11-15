# Impact Statements

> tags: reporting, intermediate, advanced

> related: Reporting/Report-Writing, Reporting/Report-Templates

Impact Statements That Pay
The technical finding gets you in the door. The impact statement determines the payout. I've watched the same XSS get rated P4 on one report and P1 on another, from different researchers, same vulnerability, because one person explained what you could actually do with it and the other just described the mechanics.
Programs are not paying you for technical knowledge. They're paying you for risk reduction. Frame your findings in terms of risk.

The Core Translation
Technical fact: "JavaScript executes in a victim's browser."
Business risk: "An attacker can hijack authenticated sessions and take over any user account, including admin accounts, without the victim's knowledge."
The second version triggers a meeting. The first one gets triaged by a junior analyst who checks a severity matrix.

What Programs Actually Care About
In rough order of what moves severity ratings:

Data exposure (PII, financial, credentials, health data)
Account takeover (especially admin/privileged accounts)
Financial impact (unauthorized transactions, billing manipulation)
Lateral movement (one user's compromise enabling others)
Reputational damage (attacker-controlled content on their domain)
Service disruption (but only if severe and realistic)


Templates by Vulnerability Class
XSS (Reflected)
Weak: "An attacker can execute JavaScript in a victim's browser."
Strong: "An attacker who convinces a target to click a crafted link can execute arbitrary JavaScript in the victim's authenticated session, enabling cookie theft, credential harvesting via fake login overlays, or DOM-based account takeover. No prior access is required. The attack requires only a single click from the victim."

XSS (Stored)
Weak: "Stored XSS allows script injection."
Strong: "Any user who views the affected [page/profile/comment] will execute attacker-controlled JavaScript in their session. This enables mass account takeover without requiring any interaction beyond normal browsing. Because [location] is displayed to [all users / admins / high-value targets], the blast radius includes [specific high-value user class]."

IDOR
Weak: "I can access other users' data by changing the ID parameter."
Strong: "Any authenticated user can enumerate and exfiltrate all [object type] for every account on the platform by incrementing a sequential ID parameter. No privilege escalation is required. This exposes [describe data: PII, financial records, private messages] for all [user count estimate if known] customers. Depending on regulatory context, this may constitute a breach requiring notification under GDPR/CCPA."

SSRF
Weak: "The server makes requests to attacker-controlled URLs."
Strong: "The server-side request forgery allows an attacker to probe internal network infrastructure, access cloud metadata endpoints (e.g., http://169.254.169.254/latest/meta-data/), and potentially retrieve IAM credentials that grant persistent access to the cloud environment. In a typical AWS deployment, this can escalate to full account compromise."

SQLi
Weak: "SQL injection allows database queries."
Strong: "Exploiting this SQL injection gives an unauthenticated attacker read access to the entire database, including [users table with credentials / payment data / PII]. If stacked queries are supported, this extends to arbitrary file read/write and potentially operating system command execution. The database user context determines the ceiling, but authentication bypass alone is achievable without further escalation."

Auth Bypass
Weak: "Authentication can be bypassed."
Strong: "An unauthenticated attacker can access any endpoint in the application without valid credentials by [specific mechanism]. This completely eliminates the security boundary protecting [user data / admin functionality / paid features]. Every protected resource is effectively publicly accessible."

Race Condition
Weak: "A race condition exists in the payment flow."
Strong: "By sending [N] concurrent requests during the [checkout/transfer/redemption] operation, an attacker can [redeem a single-use coupon multiple times / withdraw funds exceeding their balance / consume a resource quota far beyond their limit]. In testing, I successfully [specific outcome, e.g., redeemed a $50 coupon 8 times in a single second], resulting in [$X] in fraudulent value. Direct financial loss to the company is the primary impact."

Before/After: The Same Bug, Two Framings
Bug: IDOR on /api/messages/{id} exposes private user messages.
Before (weak):

"By changing the message ID in the URL, I can read messages belonging to other users."

After (strong):

"Any authenticated user can read private messages belonging to any other user on the platform by incrementing the id parameter in the /api/messages/{id} endpoint. The IDs are sequential integers starting from 1, making full enumeration trivial. Private messages on this platform include [per scope: medical consultations / financial discussions / personal communications]. This is a direct violation of user privacy expectations and likely triggers breach notification obligations in jurisdictions where users reside."

The second version tells the program exactly why this is a P2 or higher, what data is at risk, and what their legal exposure is. The first version reads like a student lab exercise.

Notes on Regulatory Hooks
When the data involved triggers a regulatory framework, say so. You don't need to be a lawyer. Just naming it puts the ball in their court.

GDPR: any PII affecting EU users
CCPA: California residents, consumer data
HIPAA: health-related data, US context
PCI-DSS: payment card data
SOC2: if the company is SOC2 certified and this violates a control

Don't overuse this. If it genuinely applies, it belongs in your impact section.

Related

Report Writing
Report Templates
