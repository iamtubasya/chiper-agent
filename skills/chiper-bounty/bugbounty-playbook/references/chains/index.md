# Chains

> tags: chains, methodology

> related: Chains/Open-Redirect-to-ATO, Chains/SSRF-to-Cloud-RCE, Chains/XSS-to-Privilege-Escalation, Chains/IDOR-to-ATO, Chains/Subdomain-Takeover-to-Session, Chains/Race-Condition-to-Financial, Chains/Info-Disclosure-to-Full-Exploit, Chains/XSS-to-Account-Takeover, Chains/CSRF-to-ATO, Chains/OAuth-Misconfig-to-ATO, Chains/File-Upload-to-RCE, Chains/Prototype-Pollution-to-Exploit, Chains/SSTI-to-RCE, Chains/Subdomain-Takeover-to-OAuth, Chains/IDOR-and-Mass-Assignment, Chains/XXE-to-SSRF-to-RCE, Chains/GraphQL-BFLA-to-Extraction, Chains/Self-XSS-to-Exploitable, Chains/Prompt-Injection-to-Data-Exfil, Methodology/Chain-Thinking, Reporting/Severity-Escalation

Chains
This is where the money is.
A standalone medium-severity bug earns you $500-$2,000 depending on the program. That same medium, chained with one or two other findings into a complete attack scenario, earns $5,000-$50,000. Those numbers aren't made up. The delta between "I found an open redirect" and "I found an open redirect that enables account takeover of any user via OAuth token theft" is often a 10-20x multiplier.
Every chain starts with understanding what position each vulnerability gives you and what's reachable from that position.
Chain Pattern Map
flowchart TD
    subgraph Position["Initial Finding"]
        P1["Open Redirect"]
        P2["SSRF"]
        P3["XSS"]
        P4["IDOR"]
        P5["Info Disclosure"]
        P6["Subdomain Takeover"]
    end

    subgraph Bridge["Bridge / Enabler"]
        B1["OAuth redirect_uri"]
        B2["Cloud metadata"]
        B3["Admin renders user content"]
        B4["PII in response"]
        B5["Referer leaks token"]
        B6["Cookies on *.domain.com"]
    end

    subgraph Impact["Final Impact"]
        I1["Account Takeover"]
        I2["RCE / Infra Compromise"]
        I3["Privilege Escalation"]
    end

    P1 --> B1 --> I1
    P1 --> B5 --> I1
    P2 --> B2 --> I2
    P3 --> B3 --> I3
    P3 --> B1
    P4 --> B4 --> I1
    P5 --> B4
    P6 --> B6 --> I1

Chain Patterns
Open Redirect → OAuth Account Takeover
Low → Critical. The classic chain. Requires an OAuth implementation with a redirect_uri that can be manipulated to include your open redirect.
SSRF → Cloud Metadata → RCE
Medium → Critical. Any SSRF on a cloud-hosted app. Hit the metadata endpoint, grab IAM creds, enumerate permissions, escalate.
XSS → Admin Action → Privilege Escalation
Medium → Critical. Stored XSS that fires in a privileged context. Use the admin's session to perform admin actions programmatically.
IDOR → PII Leak → Account Takeover
Medium → Critical. IDOR leaks enough user data to enable password reset, security question bypass, or API key theft.
Subdomain Takeover → Cookie Theft
Medium → High/Critical. Take over an abandoned subdomain, use it to read cookies scoped to the parent domain.
Race Condition → Financial Impact
Medium → High. Race condition on a payment, transfer, or reward redemption flow. Demonstrate actual monetary loss.
Info Disclosure → Full Exploitation
Low → Varies. The finding the triager wants to close as informational, until you show what an attacker does with the disclosed data.
XSS → Account Takeover
Medium → Critical. Stored XSS fires in the victim's browser, steals the session cookie or storage-based bearer token, and replays it. When HttpOnly blocks cookies, the payload acts as the victim directly via CSRF-adjacent requests.
CSRF → Account Takeover
Medium → Critical. CSRF on the email-change endpoint silently swaps the victim's recovery address. Attacker triggers a password reset to their own inbox and completes the login.
OAuth Misconfiguration → Account Takeover
Medium → Critical. Three variants: weak redirect_uri validation ships the authorisation code to an attacker server, missing state enables CSRF on the OAuth flow, and implicit-flow tokens leak through Referer headers.
File Upload → RCE
High → Critical. Upload bypass - extension blacklist, MIME check, magic byte, .htaccess overwrite, nginx/php-fpm path confusion - lands a webshell in an executable path.
Prototype Pollution → DOM XSS or RCE
Medium → Critical. Client-side: polluted property reaches a DOM sink. Server-side: Node.js gadget in Handlebars or EJS turns prototype write into OS command execution.
SSTI → RCE
High → Critical. Server-side template injection across Jinja2, Twig, Freemarker, and Handlebars. Each engine has a documented path to os.popen or equivalent.
Subdomain Takeover → OAuth Account Takeover
Medium → Critical. Claim an abandoned subdomain registered as an OAuth redirect_uri. Every user who authenticates via that OAuth flow sends their authorisation code to the attacker.
IDOR + Mass Assignment → Privilege Escalation
Medium → Critical. Write IDOR on a user-update endpoint combined with mass assignment on role fields - attacker elevates any account to admin without knowing the target's credentials.
XXE → SSRF → Cloud RCE
High → Critical. XXE in a SOAP or XML endpoint fetches the cloud metadata URL via entity resolution. IAM credentials from the metadata response chain directly into the SSRF-to-Cloud-RCE pattern.
GraphQL BFLA → Mass Data Extraction
High → Critical. Introspection reveals privileged mutations and queries. Broken function-level authorisation lets a low-privilege user run them. Query aliasing bypasses per-request rate limits for bulk exfiltration.
Self-XSS → Exploitable via Login CSRF or Clickjacking
Low → High. Self-XSS only fires in the attacker's session. Login CSRF forces the victim into that session, then navigates them to the XSS page. The payload fires in the victim's browser.
Prompt Injection → Data Exfiltration
High → Critical. Indirect prompt injection in a document read by an AI agent. The agent uses the victim's OAuth-connected tools to exfiltrate emails, files, or messages to an attacker-controlled endpoint.
Building Your Own Chains
The patterns above are documented because they're common. But the most valuable chains are the ones specific to the application you're testing. Methodology for discovering them is in Chain Thinking.
Short version: every time you find something, stop and map what new position it gives you. Look at what's accessible from that position. If you can't escalate right now, note it and come back when you find the missing link.
See Also

Chain Thinking
Severity Escalation
