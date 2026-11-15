# Report Templates

> tags: reporting, intermediate

> related: Reporting/Report-Writing, Reporting/Impact-Statements, Reporting/Responsible-Disclosure

Report Templates
Copy, paste, fill in the brackets. These aren't magic, but they get you to a solid first draft in 10 minutes instead of staring at a blank page. The templates follow the structure from Report Writing. Impact language is adapted from Impact Statements.

XSS (Stored)
Title: Stored XSS in [location] allows arbitrary script execution in [victim context] sessions
Summary: The [field/feature] at [URL] stores and renders unsanitized HTML input. Any [user type] who [views/visits] the affected [page/profile/object] will execute attacker-controlled JavaScript in their authenticated session.
Impact: An attacker can hijack sessions, exfiltrate cookies, perform actions on behalf of victims, or display phishing content under the legitimate domain. Because [location] is visible to [victim scope], the attack can be delivered passively without requiring victim interaction beyond normal platform use. This enables scalable account takeover targeting [admin accounts / all users / specific roles].

XSS (Reflected)
Title: Reflected XSS in [parameter] at [endpoint] allows session hijacking via crafted link
Summary: The [parameter] parameter at [endpoint] reflects user input into the HTML response without sanitization. An attacker who delivers a crafted URL to a victim can execute arbitrary JavaScript in the victim's browser session.
Impact: An attacker can steal session tokens, perform CSRF attacks from the victim's context, or present phishing overlays on the legitimate domain. The attack requires only a single click from the victim and can be delivered via email, social engineering, or any channel that allows URL sharing.

IDOR
Title: IDOR on [endpoint] exposes [object type] belonging to arbitrary users
Summary: The [id/uuid/reference] parameter at [endpoint] is not validated against the authenticated user's ownership. Any authenticated user can access [object type] belonging to any other account by supplying a different identifier.
Impact: An attacker with any valid account can enumerate and access [describe data: private messages / billing records / PII / documents] for every user on the platform. The identifiers are [sequential integers / UUIDs exposed elsewhere / predictable], making enumeration [trivial / feasible]. This constitutes unauthorized access to user data and [may trigger breach notification requirements under GDPR/CCPA if applicable].

SSRF
Title: SSRF via [parameter/feature] allows internal network access and cloud metadata retrieval
Summary: The [parameter] parameter at [endpoint] causes the server to fetch attacker-controlled URLs without restriction. The server's response (or timing/error behavior) confirms successful requests to internal addresses.
Impact: An attacker can probe internal network services, access cloud provider metadata endpoints to retrieve IAM credentials, and pivot to internal infrastructure not exposed to the internet. In cloud-hosted environments, successful exploitation of http://169.254.169.254/ or http://169.254.169.254/latest/meta-data/iam/security-credentials/ can yield persistent credentials granting broad access to the cloud account. Demonstrated: [what you actually retrieved].

SQLi
Title: SQL injection in [parameter] at [endpoint] allows [read/write/auth bypass] on the database
Summary: The [parameter] parameter at [endpoint] is interpolated into a SQL query without parameterization. The injection is [error-based / boolean-based / time-based blind / UNION-based] and allows [what's achievable].
Impact: An attacker can [read arbitrary tables including user credentials and PII / bypass authentication entirely / write to the database]. The database user context is [root/app user/unknown], which [does/may] allow escalation to [file system access / OS command execution]. Authentication bypass alone allows full access to the application as any user including administrators.

Auth Bypass
Title: Authentication bypass on [endpoint/feature] allows [unauthenticated/unprivileged] access to [protected resource]
Summary: [Specific mechanism, e.g., "The JWT signature is not verified on the /api/admin route" or "The role parameter in the session cookie is not validated server-side"]. This allows [attacker context] to access resources restricted to [required role/auth state].
Impact: An attacker can access [all admin functionality / any user's account / privileged API endpoints] without valid credentials or the required role. This completely removes the access control boundary protecting [describe what's behind it]. [If unauthenticated bypass]: no account is required, the attack is available to any internet user.

Race Condition
Title: Race condition in [feature] allows [duplicate redemption / balance manipulation / quota bypass]
Summary: The [feature] endpoint at [URL] processes requests without adequate locking. Sending [N] concurrent requests within the same transaction window allows an attacker to [specific outcome] multiple times before the system registers the first operation.
Impact: An attacker can [redeem a single-use code N times / withdraw more than their available balance / consume N times their allotted quota] by sending parallel requests. In testing, I achieved [specific result, e.g., "redeemed a single $25 voucher 6 times, netting $125 in fraudulent credit"]. Direct financial impact per successful exploit: [estimate]. The attack requires an authenticated account but no elevated privileges.

Information Disclosure
Title: [Type] disclosure at [endpoint] exposes [specific data] to [attacker context]
Summary: The endpoint [URL] returns [describe what's leaked] to [unauthenticated requests / any authenticated user / users without the required role]. This data was not intended to be accessible to this audience.
Impact: The exposed data includes [PII / credentials / internal infrastructure details / API keys / session tokens]. [For credentials/keys]: these can be used directly to [authenticate as other users / access additional systems / escalate privileges]. [For PII]: this affects [estimated scope] users and [may constitute a reportable breach under applicable regulations].

CSRF
Title: CSRF on [endpoint] allows attacker to [action] on behalf of any authenticated user
Summary: The [endpoint] endpoint accepts state-changing requests without CSRF token validation. An attacker can host a page that submits a forged request when an authenticated user visits it, performing [action] without the user's knowledge or consent.
Impact: Any authenticated user who visits an attacker-controlled page will unknowingly [change their email address / transfer funds / modify account settings / delete data]. The attack requires no user interaction beyond visiting a link. Combined with [stored XSS / email delivery / social engineering], this can target [specific user groups / all users / administrators]. [If admin-targeted]: this enables privilege escalation via forced account modification.

Subdomain Takeover
Title: Subdomain takeover on [subdomain] via unclaimed [service] resource
Summary: The subdomain [subdomain.target.com] has a DNS [CNAME / A] record pointing to [service, e.g., "an S3 bucket / Heroku app / Azure endpoint"] that no longer exists or has been deprovisioned. An attacker can claim the underlying resource and serve arbitrary content under the target's domain.
Impact: An attacker controlling this subdomain can serve phishing pages under the trusted domain, steal cookies scoped to *.target.com or .target.com, bypass CORS policies that whitelist *.target.com, and host malicious content with the reputation of the target domain. [If cookies are scoped to parent domain]: this enables session hijacking for any user of the main application.

Open Redirect (Chained)
Title: Open redirect at [endpoint] enables [OAuth token theft / phishing under trusted domain]
Summary: The [parameter] parameter at [endpoint] redirects users to arbitrary external URLs without validation. This redirect is within the OAuth-trusted domain, allowing it to be used as a redirect_uri value to intercept authorization codes.
Impact: An attacker can construct a URL that starts an OAuth flow with redirect_uri set to the vulnerable redirect endpoint, chaining through to an attacker-controlled server. The victim authenticates normally, but their authorization code is delivered to the attacker, enabling full account takeover. [If no OAuth]: the redirect serves as a trusted phishing vector, sending victims from a legitimate domain to an attacker-controlled login page.

Path Traversal / LFI
Title: Path traversal in [parameter] at [endpoint] allows reading arbitrary server files
Summary: The [parameter] parameter at [endpoint] is used to construct a file path on the server without adequate sanitization. By injecting traversal sequences (../), an attacker can read files outside the intended directory.
Impact: Demonstrated file read of [/etc/passwd / application config / .env / database credentials]. [If credentials found]: these credentials grant [database access / admin login / API access to internal services]. [If source code]: the leaked source reveals [additional vulnerabilities / hardcoded secrets / internal API endpoints]. The server runs as [user/root], which [limits/does not limit] the scope of readable files.

XXE
Title: XXE injection via [upload/endpoint] allows [file read / SSRF / denial of service]
Summary: The [feature, e.g., "DOCX upload / SAML authentication / XML API endpoint"] at [endpoint] processes XML input with external entity resolution enabled. An attacker can inject a crafted DTD to read local files, make server-side requests, or cause denial of service.
Impact: Demonstrated retrieval of [/etc/passwd / application.properties / internal config] via file:// protocol handler. [If SSRF]: the XXE can be escalated to reach cloud metadata endpoints and internal services, equivalent to full SSRF. [If blind]: data is exfiltrated via out-of-band DNS/HTTP requests to [collaborator domain], confirmed by [evidence].

Business Logic
Title: Business logic flaw in [feature] allows [financial gain / quota bypass / access control circumvention]
Summary: The [feature] at [endpoint] [describe the logic flaw: "does not validate that the coupon has already been applied" / "allows negative quantities in the cart" / "trusts client-side price calculations"]. An attacker can exploit this to [specific outcome].
Impact: Demonstrated [specific result, e.g., "purchasing a $500 item for $0.01 by modifying the price parameter" / "applying the same referral code 47 times, generating $470 in credit" / "accessing premium features by replaying a trial activation request"]. Direct financial impact: [amount per exploit]. The flaw requires only [a standard user account / no authentication] and can be repeated [indefinitely / N times before detection].

Privilege Escalation
Title: [Horizontal/Vertical] privilege escalation via [mechanism] allows [attacker role] to access [target role] functionality
Summary: [Describe mechanism, e.g., "Changing the role parameter in the PUT /api/user/profile request from user to admin is accepted by the server" / "Replacing the user ID in the JWT payload without invalidating the signature grants access to other accounts"]. The server does not [validate role changes server-side / verify JWT signature / check authorization on the target endpoint].
Impact: [Vertical]: Any standard user can escalate to [admin/superadmin] privileges, gaining access to [user management / billing / system configuration / all customer data]. [Horizontal]: Any authenticated user can access any other user's [account / data / session] by [manipulating the identifier]. This bypasses the entire authorization model of the application.

Account Takeover (Chain)
Title: Account takeover of any user via [chain description, e.g., "open redirect + OAuth flow manipulation"]
Summary: This report chains [N] findings into a complete account takeover:

[Step 1: e.g., "Open redirect at /callback allows redirect_uri manipulation"]
[Step 2: e.g., "OAuth flow sends authorization code to attacker-controlled URL"]
[Step 3: e.g., "Attacker exchanges code for access token and takes over victim account"]

Each step is described with reproduction details below.
Impact: An attacker can take over any user account on the platform, including administrators, without knowing the victim's credentials. The attack requires only that the victim clicks a single crafted link. [If no interaction needed]: the attack can be delivered passively via [stored XSS / email / embedded content]. This grants the attacker full access to the victim's [data / payment methods / connected services / administrative functions].

Cache Poisoning
Title: Web cache poisoning via [unkeyed header] delivers [XSS / malicious content] to all users
Summary: The [header, e.g., X-Forwarded-Host] header is excluded from the cache key but reflected in the response [in a script src / in a meta tag / in inline JavaScript]. An attacker can send a request with a malicious header value, poison the cache, and serve the poisoned response to all subsequent visitors.
Impact: Every user requesting [cached URL] receives the attacker's payload until the cache entry expires (TTL: [duration]). Demonstrated delivery of [JavaScript execution / redirect to phishing page / content defacement] to unauthenticated visitors. The attack persists without the attacker maintaining any infrastructure after the initial poisoning request. Cache scope: [single page / wildcard path / entire domain].

Chain Report (General Template)
Title: [Final impact] via [brief chain description]
Summary: This report demonstrates a chain of [N] findings that individually range from [low/medium] severity but together achieve [critical impact]:

[Finding 1 title] ([severity alone]) - [one sentence]
[Finding 2 title] ([severity alone]) - [one sentence]
[Finding N title] ([severity alone]) - [one sentence]

Combined severity: [Critical/High] - the chain achieves [account takeover / RCE / mass data access / financial impact] which none of the individual findings achieve alone.
Full reproduction: [Detailed numbered steps showing the complete attack from start to finish, with exact URLs, payloads, and expected responses at each stage]
Impact: [Describe the final impact in business terms. What can the attacker do? How many users are affected? Is it repeatable? What data is at risk?]

Notes on Using These Templates
Don't just fill in brackets and ship it. Read what you've written out loud. If it sounds like a form letter, it reads like one. Add specifics: your actual payloads, the actual data you accessed, the actual behavior you observed. These templates give you structure. You supply the substance.
The impact section especially needs customization. Generic impact language gets generic severity ratings.

Related

Report Writing
Impact Statements
Responsible Disclosure
