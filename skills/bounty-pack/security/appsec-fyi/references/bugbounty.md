## Notable Techniques

Notable Techniques
The following techniques represent a cross-section of impactful vulnerabilities and exploitation methods that continue to be relevant in bug bounty hunting:

Vulnerability Classes and Exploitation Chains

• Server-Side Request Forgery (SSRF): Exploiting applications that mishandle user-supplied URLs to make requests on behalf of the server, potentially accessing internal resources, cloud metadata, or performing port scanning . This can be chained with other vulnerabilities for RCE .

• HTTP Request Smuggling: Exploiting discrepancies in how front-end and back-end servers process HTTP requests, leading to desynchronization and cache poisoning or bypassing security controls .

• XML External Entity (XXE) Injection: Exploiting vulnerable XML parsers to access local files, perform SSRF, or conduct denial-of-service attacks. This includes crafting payloads for Office Open XML (OOXML) files .

• Cross-Site Scripting (XSS): Still a prevalent vulnerability, with advanced techniques including blind XSS, SVG-based XSS, DOM-based XSS, and chaining XSS with other flaws like CSRF for account takeover .

• Insecure Direct Object Reference (IDOR): Gaining unauthorized access to resources by manipulating identifiers in requests, often found through reconnaissance or by targeting application logic flaws .

• Prototype Pollution: Modifying JavaScript object prototypes to alter application behavior, potentially leading to denial-of-service, XSS, or RCE .

• Authentication and Authorization Bypass: This encompasses a broad range of techniques, including OAuth misconfigurations, SAML exploitation, broken access control logic, and exploiting password reset mechanisms .

• Vulnerable and Outdated Components: Exploiting known vulnerabilities (N-days) in libraries, frameworks, or applications .

• Hardcoded Credentials: Discovering embedded API keys, passwords, or other secrets in code or configuration files, often through static analysis or reconnaissance .

• PHP2Shell (CVE-2026-109618 & CVE-2026-109619): A specific vulnerability involving PHP deserialization leading to code execution.

• Spring4Shell (CVE 2022 22965): Data binding vulnerability allowing RCE via file overwrite.

• Next.js Server Action Denial of Service (CVE-2026-23870): Exploiting form data rebuilding with nested pointers to crash Next.js applications .

• Vulnerability in NVIDIA DCGM Exporter (CVE-2026-47483): Unauthenticated resource consumption, DoS, and information disclosure impacting thousands of GPUs .

• Flask session pickle deserialization: Leading to RCE, demonstrated by a $90K Google bounty.

• Integer overflow vulnerability: For free purchases (\u20b90).

• PHP2Shell (CVE-2026-109618 & CVE-2026-109619): Four confirmed attack chains and potential impact.

• Microsoft Edge exploit chain: Using only logic bugs, bypassing memory corruption exploits.

• 1-click RCE in Discord: Via Twitch embed.

• XSS in Cloudflare's image endpoint: Via SVG sanitizer bypass.

• Sub-user can delete a company: Demonstrated in Munshi.

• Arbitrary file read: In an AWS open-source tool with AI agents.

• Shodan to real-world impact chain: From weak credentials to delivery manipulation.

• Iframe sandwich technique: To escalate XSS to Account Takeover.

• Path traversal in cohttp (OCaml).

• Jailbreak for Claude Sonnet 4.6: Convincing AI it's an Anthropic-verified researcher.

• Mass password reset code sending vulnerability: Awarded $30,000 bounty.

• Exploiting lengthy registration forms: To find neglected vulnerabilities.

• Nginx CVEs requiring uncommon configurations: nginx-rift, nginx-poolslip, nginx-quicburst, CVE-2026-42533.

AI-Assisted Techniques
AI models are increasingly integrated into bug bounty workflows, not just for discovery but for validation, exploit generation, and reporting.

• Autonomous Reconnaissance: AI agents can perform extensive information gathering, fingerprinting, and initial vulnerability identification . Tools like HexStrike AI and Claude-OSINT exemplify this.

• Vulnerability Discovery and Validation: AI models can analyze code for logic flaws, identify potential entry points, and even assist in verifying reported bugs by attempting to reproduce steps .

• Prompt Engineering for Security: Crafting specific prompts for LLMs to uncover vulnerabilities or generate exploit code, including bypassing AI security controls (e.g., jailbreaks) .

• Exploit Chain Building: AI can assist in chaining multiple low-severity findings into a high-impact exploit .

• Report Writing: LLMs can help structure and draft vulnerability reports, improving clarity and efficiency.