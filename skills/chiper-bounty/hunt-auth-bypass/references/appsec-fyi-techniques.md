<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/authn.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques and Attack Patterns

Notable Techniques and Attack Patterns
Beyond core protocol weaknesses, attackers employ a variety of sophisticated techniques.

Authentication Bypass

• Host Header Authentication Bypass: Manipulating the Host header to trick applications into treating requests as internal or trusted, bypassing security checks .
• CSRF Header Bypass for Account Takeover: Exploiting vulnerabilities where CSRF protection is bypassed through header manipulation, leading to account takeover .
• Unauthenticated Administrative Access: Direct access to administrative functions without any authentication, often due to misconfigurations .
• Empty Cluster Join Key: A specific misconfiguration in distributed systems (like JFrog Artifactory) where an empty cluster join key allows unauthenticated administrative access .
• XML Signature Wrapping (XSW): As detailed above, a powerful technique for forging SAML assertions .
• Weak JWT Signature Validation: Overlooking alg: none or allowing algorithm confusion allows attackers to forge JWTs .
• Exploiting Password Reset Mechanisms: Bypassing verification steps or manipulating reset tokens to take over accounts .
• SMTP Header Smuggling: Can be used to spoof identities, potentially aiding in phishing or bypassing email-based authentication checks .
• Protocol Interpretation Differences: Exploiting inconsistencies in how protocols are parsed by different components .
• SSO Redirection Hijacking: Manipulating the redirection process in SSO flows to trick users or steal tokens .
• API Endpoint Exploitation: Directly attacking API endpoints that lack proper authentication or authorization checks .
• Broken Access Control: Even if authentication succeeds, broken access control can allow users to access unauthorized resources or perform unauthorized actions .
Account Takeover (ATO) and Credential Compromise

• POST-based XSS for Account Takeover: Using Cross-Site Scripting in POST requests to steal session cookies or credentials .
• Credential Stuffing/Phishing: Brute-forcing accounts with leaked credentials or using phishing to acquire them .
• Session Hijack/Leak: Stealing active session tokens or cookies to impersonate users .
• Privilege Escalation: After gaining initial access, attackers escalate privileges to gain higher levels of control .
• Infostealers: Malware specifically designed to steal credentials, API keys, and session tokens from various cloud and AI environments .
• AI Agent Exfiltration: AI agents used maliciously to exfiltrate credentials from internal services .
• Exploiting Chained Misconfigurations: Combining multiple minor misconfigurations to achieve a significant security breach .
• Using LLMs for Vulnerability Discovery/Exploitation: AI models are being used by attackers to find and exploit vulnerabilities more efficiently .
• Exploiting WebAuthn/Passkey Workflows: Vulnerabilities in the implementation or user interaction with passkeys can lead to compromise .
Token Abuse

• OAuth Token Hijacking/Stealing: Obtaining valid OAuth tokens through various means (phishing, XSS, insecure storage) .
• Cross-User OAuth Session Fixation (COSF): Forcing a user to use a session identifier that is also known to another user or attacker .
• Cross-Tenant Client ID Confusion: Exploiting shared client IDs across different tenants or organizations within a multi-tenant system .
• Cross-Connector OAuth Account Takeover: Abusing integrations between different OAuth providers or connectors .
• Stolen OAuth Tokens Bypassing MFA: Tokens that represent an authenticated and authorized session can often bypass subsequent MFA checks .
• Long-Lived OAuth Tokens Bypassing MFA: Tokens that remain valid for extended periods increase the risk window for theft and bypass .
• Refresh Token Exploitation: Refresh tokens, if compromised, can be used to obtain new access tokens, even if the original access token has expired or been revoked .
Cloud and API Security

• API Endpoint Exploitation: Direct attacks on APIs that lack robust authentication and authorization .
• Cross-Tenant Client ID Confusion: In cloud environments, misconfigured client IDs can lead to cross-tenant data access .
• Exploitation of GCP Billing Accounts for AI Usage (LLMjacking): Malicious use of compromised cloud accounts to incur AI service costs [S0 (implied)].
• Infostealers targeting AWS, GCP, GitHub, and OpenAI API Keys: Dedicated malware to compromise cloud and AI service credentials .
• Abuse of AWS IAM Role Assumption and SourceIdentity: For obfuscation or privilege escalation by manipulating role assumptions [S0 (implied)].
• Misconfigured Cluster Join Keys: Leading to unauthenticated administrative access in distributed systems .
AI Agent Security

• AI Agent Using Stolen Credentials and Zero-Day Exploits: Advanced persistent threats leveraging AI for sophisticated attacks .
• AI Agent Exfiltrating Credentials: Malicious AI agents actively searching for and stealing sensitive information .
• Using LLMs for Vulnerability Discovery/Exploitation: AI models assisting attackers in identifying and weaponizing vulnerabilities .
• AI-Driven Phishing-as-a-Service Kits: Automating the creation and deployment of highly convincing phishing campaigns .