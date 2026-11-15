# Chain Thinking

> tags: methodology, intermediate, advanced

> related: Chains/Open-Redirect-to-ATO, Chains/SSRF-to-Cloud-RCE, Chains/XSS-to-Privilege-Escalation, Chains/IDOR-to-ATO, Chains/Subdomain-Takeover-to-Session, Chains/, Reporting/Severity-Escalation, Reporting/Impact-Statements

Chain Thinking
Every bug you find should trigger one question: what does this give me access to next?
An open redirect on its own is a low. An open redirect on an OAuth callback is an account takeover. Same vulnerability, completely different payout. The difference is whether you stopped at "I found a thing" or kept pulling the thread.
The Chain Decision Tree
When you find something, run through this:
flowchart TD
    A["You found a vulnerability"] --> B{"Gives you a new position?"}
    B -->|Yes| C["Map what's reachable"]
    B -->|No| D{"Combinable with another finding?"}

    C --> E{"Can you escalate further?"}
    E -->|Yes| F["Keep chaining"]
    E -->|No| G["Report the chain as-is"]

    D -->|"Have a complementary finding"| H["Build the chain end-to-end"]
    D -->|"Know what would chain"| I["Hunt for the missing link"]
    D -->|"Stands alone"| J["Report solo, note chain potential"]

    H --> E
    I --> K{"Found it?"}
    K -->|Yes| H
    K -->|No| J
    F --> G

Common Chain Patterns
These are the combinations I see most often. Each one has its own page with detailed methodology.
Open Redirect → OAuth Account Takeover
The classic. Find an open redirect, check if the app uses OAuth, see if the redirect_uri validation is loose enough to accept your redirect. If yes, you're stealing authorization codes.
User clicks crafted link
    → OAuth flow starts with redirect_uri=target.com/callback://evil.com
    → User authenticates (or is already authenticated)
    → Authorization code sent to target.com/callback
    → /callback redirects to evil.com WITH the auth code in the URL
    → Attacker exchanges code for access token
    → Full account takeover
Severity jump: Low → Critical
SSRF → Cloud Metadata → RCE
Find SSRF (even blind) and the app is on AWS/GCP/Azure. Hit the metadata endpoint, grab IAM credentials, see what those creds can do. Sometimes it's read-only on one S3 bucket. Sometimes it's admin on the entire account.
SSRF in PDF generator / URL preview / webhook
    → Fetch http://169.254.169.254/latest/meta-data/iam/security-credentials/
    → Returns IAM role name
    → Fetch .../security-credentials/{role-name}
    → Returns AccessKeyId, SecretAccessKey, Token
    → Enumerate permissions: S3? EC2? Lambda? SSM?
    → Worst case: ssm:SendCommand → RCE on any EC2 instance
Severity jump: Medium → Critical
XSS → Admin Action → Privilege Escalation
Stored XSS that fires in an admin panel is already high on its own. But if you can craft a payload that performs admin actions (creating a new admin account, changing permissions, exfiltrating data) that's a critical with demonstrated impact.
Stored XSS in user-controllable field (display name, bio, support ticket)
    → Payload triggers when admin views the content
    → XSS executes in admin's browser context
    → Fetch admin API endpoints with admin's session
    → Create new admin account / export all user data / modify billing
Severity jump: Medium → Critical
IDOR → PII Leak → Account Takeover
IDOR gives you access to another user's data. That data includes their email and the answer to their security question. Or their phone number, and the app uses SMS-based password reset. Or their API key, and that key has full account permissions.
Severity jump: Medium → Critical
Subdomain Takeover → Cookie Theft
Dangling CNAME on a subdomain. You claim it. If cookies are scoped to .example.com (and they often are), you can now read session cookies for the main application from any user who visits your controlled subdomain.
Severity jump: Medium → High/Critical
Hunting for Missing Links
Sometimes you find one half of a chain and need to hunt specifically for the other half. This is targeted hunting and it's extremely efficient because you know exactly what you're looking for.
You have an open redirect. You need:

OAuth implementation with loose redirect_uri validation
Referer-based token leakage
Any flow that appends sensitive data to a URL before redirecting

You have XSS (self-only or reflected). You need:

A CSRF-protected action you want to forge (the XSS bypasses CSRF tokens)
An admin panel that renders user-controlled content
A postMessage listener that trusts the origin

You have SSRF (blind). You need:

Cloud metadata endpoint reachability
Internal services on predictable ports (6379 Redis, 9200 Elasticsearch, etc.)
DNS rebinding setup to bypass allowlist filters

You have an IDOR. You need:

Sensitive data in the leaked object (PII, tokens, keys)
A user action you can perform with the leaked data (password reset, API access)
Scale. Can you enumerate all users, or just one?

The Chain Report
When reporting a chain, structure matters. Don't just list two bugs and hope the triager connects the dots.
## Summary
[One sentence: what an attacker achieves by combining these findings]
 
## Attack Flow
[Numbered steps, end-to-end, that a non-technical PM could follow]
 
## Step 1: [First vulnerability]
[Technical details, request/response, proof]
 
## Step 2: [How Step 1 enables Step 2]
[This is the critical paragraph. Explain the bridge between findings.]
 
## Step 3: [Second vulnerability / escalated access]
[Technical details, request/response, proof]
 
## Impact
[What does the attacker now have? How many users affected?
 Frame in business terms, not just technical severity.]
That "how Step 1 enables Step 2" section is where most chain reports fail. Triagers are busy. If they have to figure out the connection themselves, they'll evaluate each finding independently and you'll get two mediums instead of one critical.
See Also

Chain Patterns
Severity Escalation
Impact Statements That Pay
