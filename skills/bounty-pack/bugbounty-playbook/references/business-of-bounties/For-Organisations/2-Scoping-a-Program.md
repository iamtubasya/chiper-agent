# Scoping a Program

> tags: business, programs

> related: Business-of-Bounties/For-Organisations/Starting-a-Program, Business-of-Bounties/For-Organisations/Researcher-Relationships, Programs/Selection/Reading-Scope

Scoping a Program
Scope is the single most important document in your program. It determines what researchers test, what you pay for, and where the arguments happen. Most programs get it wrong on the first try. That's fine, as long as you iterate.

Domains and Subdomains
Start by mapping what you actually own. This sounds obvious, but most organisations don't have a complete inventory of their external-facing assets until someone forces them to build one. Before you write a scope document, run your own recon.
# Discover what's actually out there
subfinder -d yourcompany.com -all -silent | sort -u
amass enum -passive -d yourcompany.com
You'll find things you forgot about. Old marketing sites, staging environments that never got decommissioned, acquisitions still running on their original domains. Decide what to include before researchers find them for you.
Wildcard scope (*.yourcompany.com) is appropriate when you want broad coverage and your team can handle reports against any subdomain. Researchers who like doing recon will gravitate towards it. But it means you need to be able to triage findings against systems you may not be intimately familiar with.
Explicit domain lists are appropriate when you want focused testing on specific applications. List exactly which domains are in scope. This reduces noise but also reduces the chance of researchers finding issues on assets you didn't know about.
Most mature programs do both: a wildcard for general coverage, plus a list of high-value targets with higher bounty multipliers. That way you get focused effort on the important stuff and still catch surprises on the things you forgot about.

IP Ranges and Infrastructure
If you include IP ranges, be precise. CIDR notation, not vague descriptions. Researchers need to know exactly what they can and can't scan.
In scope:
  203.0.113.0/24
  198.51.100.0/24

Out of scope:
  All other IP ranges not explicitly listed

Consider whether you want researchers doing port scanning against your infrastructure. Some programs allow it with rate limits. Others restrict testing to web applications only. Be explicit about this. A researcher running nmap against your /24 isn't being aggressive if your scope doesn't say otherwise.
Cloud infrastructure adds complexity. If you're running on AWS, GCP, or Azure, your IP ranges change. Scope by domain name rather than IP where possible. If you do include cloud IPs, keep the scope document updated when ranges change.

Third-Party Services
Most scope documents handle this badly. Modern organisations run on third-party services. Your login page might be Auth0, your email is Google Workspace, your CDN is Cloudflare, your support portal is Zendesk. Researchers will encounter these. Your scope needs to address them clearly.
General rule: vulnerabilities in the third-party product itself are out of scope. If a researcher finds an XSS in Zendesk's core platform, that belongs to Zendesk's own bug bounty program, not yours.
Misconfigurations in how you use third-party services are typically in scope. An overly permissive S3 bucket policy, a misconfigured OAuth integration, an exposed Firebase database with weak rules -- these are your responsibility, not the vendor's.
Be explicit about this in your policy:

Vulnerabilities in third-party software or services (e.g., Cloudflare, AWS, Zendesk) are out of scope. Misconfigurations in our use of third-party services that expose our data or users are in scope.

Common third-party considerations:

CDN/WAF providers (Cloudflare, Akamai, AWS CloudFront): Bypasses of WAF rules that expose vulnerabilities in your application are in scope. Vulnerabilities in the WAF product itself are not.
Authentication providers (Auth0, Okta, Azure AD): Misconfigurations in your SSO setup are in scope. Bugs in the provider's platform are not.
Cloud storage (S3, GCS, Azure Blob): Exposed buckets and misconfigured access policies on your accounts are in scope.
SaaS tools (Jira, Slack, Confluence): Generally out of scope unless a misconfiguration in your instance exposes sensitive data. A public Jira board with internal tickets is your problem, not Atlassian's.


Mobile Applications
If you have mobile apps, decide whether they're in scope and specify which versions. Testing should generally be limited to the current production release. Researchers who decompile APKs from three versions ago and report fixed issues waste everyone's time.
Specify the platform: iOS, Android, or both. If you have different features on each, note that. API endpoints discovered through mobile app analysis should be in scope if the API itself is in scope.

Vulnerability Classes
Not all vulnerability types are worth paying for. Define which classes are in scope and which aren't. Every program excludes some things.
Standard exclusions that almost every program should include:

Missing security headers without demonstrated impact
Self-XSS (only affects the researcher's own session)
CSRF on logout
Rate limiting on non-critical endpoints
SPF/DKIM/DMARC configuration issues
Clickjacking on pages with no sensitive actions
Software version disclosure without a known exploit

Be careful with blanket exclusions. "All denial of service is out of scope" might cause you to miss a critical ReDoS or application-level DoS that crashes your service with a single request. Consider scoping to "DoS requiring significant traffic volume is out of scope; application-level DoS achievable with minimal requests is in scope."
Similarly, "open redirects are out of scope" as a blanket rule means you might miss an open redirect that chains into an OAuth token theft. Consider scoping to "open redirects are out of scope as standalone findings; open redirects that enable exploitation of another vulnerability are in scope."

Rules of Engagement
Scope isn't just what to test, it's how to test. Define:

Rate limits on scanning. If you don't want researchers running aggressive scanners, say so. "Automated scanning is permitted at reasonable rates that do not impact service availability" gives you room to push back on abuse without banning tools entirely.
Data access boundaries. "Do not access, modify, or exfiltrate data belonging to other users. Use only accounts you own or control." This protects your users and protects the researcher.
Production vs. staging. If you have a staging environment, tell researchers to use it. If you don't, acknowledge that testing happens on production and set expectations accordingly.
Reporting timeline. "Report vulnerabilities within 24 hours of discovery" is reasonable. It prevents researchers from sitting on critical findings while they look for more.


Keeping Scope Current
Scope documents go stale. Infrastructure changes, acquisitions happen, products get deprecated. Review your scope quarterly at minimum. When you add new assets, update the scope proactively rather than waiting for a researcher to ask whether the new subdomain is fair game.
Announce scope changes to your researcher community. If you're running a private program, a message in your shared channel is enough. If you're public, platform announcements work. Researchers who invest time in your program deserve to know when the rules change.

Related

Starting a Program
Researcher Relationships
Reading Scope
