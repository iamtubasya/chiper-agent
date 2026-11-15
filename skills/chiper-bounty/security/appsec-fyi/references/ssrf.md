## Notable Techniques

Notable Techniques
SSRF exploitation techniques are diverse and continuously evolving. Attackers exploit various misconfigurations and application logic flaws:

Cloud Metadata Services Abuse
Accessing cloud provider metadata services is a common and high-impact SSRF technique. These services, typically accessible via a special link-local IP address (e.g., 169.254.169.254 for AWS IMDS), expose temporary credentials, security tokens, and instance information. Stealing these credentials can grant attackers broad access to cloud resources like S3 buckets, RDS databases, and IAM roles .

Attackers often bypass IMDSv2's PUT-only requirement for credential requests by exploiting redirect logic or other HTTP manipulations to achieve credential exfiltration .

Bypassing IP Address and Host Restrictions
Many applications attempt to mitigate SSRF by blocking requests to internal IP addresses or specific hostnames. Attackers employ various techniques to circumvent these restrictions:

• DNS Rebinding: An attacker controls a domain that initially resolves to a safe, public IP address. After the application validates the hostname, the DNS record is rapidly changed to point to a malicious internal IP address, allowing the forged request to proceed .

• Alternative IP Representations: Using decimal, octal, hexadecimal, or IPv6-mapped IPv4 addresses can bypass naive IP address filters. For example, 127.0.0.1 can be represented as 017700000001 (octal) or ::ffff:127.0.0.1 (IPv6) .

• Domain Redirects: Exploiting HTTP redirect mechanisms (e.g., 302, 307, 308) can be used to forward requests to an internal target after initial validation. This is particularly effective when the validation is performed on the initial URL, but the actual fetch follows the redirect without re-validation .

• URL Parsing Discrepancies: Different libraries or components may parse URLs differently. Exploiting these discrepancies, such as handling of fragments (#), encoded characters, or specific delimiters, can lead to bypasses .

• Unicode and Special Characters: Manipulating URLs with Unicode characters or special characters can sometimes confuse parsers and bypass filters .

• Null Byte Truncation: Appending a null byte (%00 or \x00) can truncate string processing, allowing a malicious suffix to be appended to a seemingly safe URL .

Exploiting Specific Application Features
Many common application features can become SSRF vectors if they process user-supplied URLs without adequate validation:

• Webhooks: Applications that send webhooks to user-configured endpoints are prime targets. Validation might occur at configuration time but not during delivery, allowing redirects to internal or metadata endpoints .

• PDF Generators: Applications that convert HTML to PDF can be tricked into fetching external resources via CSS stylesheets or embedded HTML/JavaScript. This can be used to target cloud metadata services .

• Image Fetching/Uploads: Features that fetch images from a user-supplied URL (e.g., profile pictures, remote image previews) or handle image uploads with URL parameters can be exploited .

• XML Parsers (XXE): XML External Entity (XXE) vulnerabilities can be chained with SSRF by referencing an external HTTP URL in an entity declaration, forcing the XML parser to act as an HTTP client .

• AI Agents and LLM Pipelines: AI agents that fetch data from external sources, particularly in Retrieval Augmented Generation (RAG) pipelines, can be manipulated. If granted excessive network access without proper runtime validation, they can become SSRF vectors .

• Screenshot/Rendering Services: Features that generate screenshots or render web pages can be abused to trigger SSRF and capture internal data .

• Package Repositories: Features like VCS remote download requests in artifact repositories can be exploited .

• API Endpoints: Unauthenticated access to API endpoints that directly pass caller-controlled endpoints to HTTP request methods is a common vulnerability .

SSRF Chaining for RCE
SSRF alone can provide significant access, but it's often chained with other vulnerabilities to achieve Remote Code Execution (RCE). This can involve:

• Targeting Services with RCE Vulnerabilities: Using SSRF to send crafted requests to internal services that have known RCE vulnerabilities (e.g., Redis, Elasticsearch, specific administrative interfaces) .

• Exploiting File Write Vulnerabilities: If SSRF can lead to writing a malicious file to the server, combined with an arbitrary file write vulnerability, RCE can be achieved .

• Exploiting Deserialization Vulnerabilities: SSRF can be used to deliver malicious payloads to deserialization sinks.

• HTTP Request Smuggling: Techniques like HTTP/2 request smuggling can be combined with SSRF to poison request queues or bypass security controls, potentially leading to RCE .

Blind SSRF Exploitation
When direct responses are not visible, attackers use creative methods to confirm SSRF and extract information:

• Out-of-Band (OAST) Channels: Using tools like Burp Collaborator or Interactsh to monitor DNS lookups or HTTP callbacks to attacker-controlled domains .

• Timing-Based Attacks: Measuring the time it takes for a request to complete can reveal information about the target, especially when combined with sequential probing of internal IPs or ports .

• Error Messages and Status Codes: Partial responses can provide clues about the success of a request or the internal network structure.

## Notable Techniques in Detail

Notable Techniques in Detail
Cloud Metadata Exfiltration Beyond IMDSv1
While IMDSv1 is widely understood as a target, attackers continue to find ways to access cloud metadata, even when IMDSv2 is in place. Techniques include exploiting redirect logic that might bypass IMDSv2's PUT-only requirement for token acquisition , or chaining SSRF vulnerabilities with other misconfigurations to bypass security controls . The core principle remains: tricking the server into making a request to the metadata endpoint (169.254.169.254 for AWS) to retrieve temporary IAM credentials or other sensitive information .

HTTP/2 Request Smuggling
HTTP/2 introduced new complexities that can lead to request smuggling vulnerabilities. Exploiting HTTP/2 frame multiplexing or misconfigurations in H2C (HTTP/2 Cleartext) support can allow attackers to send SSRF payloads to internal services, bypassing perimeter defenses . This can be combined with response queue poisoning to achieve RCE or bypass authentication.

PDF Generation and HTML/JavaScript Injection
The functionality of generating PDFs from HTML input is a recurring SSRF vector. By injecting HTML with external stylesheet references or JavaScript code that makes server-side requests, attackers can target internal resources or cloud metadata endpoints. The underlying rendering engine (e.g., headless Chromium) can be tricked into making these requests, with OOB callbacks often used for confirmation . If the PDF generator runs in an un-sandboxed environment with root privileges, this can lead to RCE .

AI Agent and LLM Pipeline Exploitation
The increasing integration of AI agents and LLMs into applications presents new SSRF attack surfaces. When these agents require fetching data from various sources, if the underlying fetching mechanisms are not rigorously validated, they can be tricked into accessing internal networks or sensitive metadata. This pattern is observed in AI agents with excessive network access granted without runtime validation, or in LLM applications like RAG pipelines where user-provided prompts can influence data fetching . ChatGPT's custom GPT actions have also been a target, allowing redirection to Azure IMDS or other internal endpoints .

XXE Beyond Basic XML Parsing
While XXE is a well-known vulnerability, its application in SSRF is still potent. Beyond standard XML documents, XXE can be found in Office Open XML parsers, SVG files, and other structured data formats. Leveraging XXE to trigger SSRF allows attackers to access internal services, read local files, and even exfiltrate cloud credentials .

Leveraging URL Parsing and Protocol Handlers
Attackers exploit the inherent complexity and potential inconsistencies in how different components parse URLs. This includes manipulating the order of operations, using different encodings, or exploiting parser differences between edge infrastructure (like load balancers or WAFs) and the application logic itself . The abuse of less common protocol handlers like gopher:// is particularly powerful for interacting with arbitrary TCP services and often leads to RCE .

## Notable Techniques in Practice

Notable Techniques in Practice
Portainer SSRF via URL Validation Bypass
In Portainer, a Docker management UI, an SSRF vulnerability (GHSA-wqqf-pwjh-2hm6) allowed signed-in users to fetch internal addresses or cloud metadata. The vulnerability exploited improper validation of user-supplied URLs, where the application might check for well-formedness but not adequately validate the destination, allowing it to reach internal services or metadata endpoints .

MLflow Webhook SSRF Leading to Cloud Credential Theft
MLflow's model registry webhook functionality was found to be vulnerable to SSRF (CVE-2026-64849). The issue stemmed from inadequate validation of webhook target URLs. While the configuration might impose some restrictions, the delivery mechanism did not re-validate the destination, allowing redirects to cloud metadata services like 169.254.169.254. This led to the retrieval of cloud tokens, actively exploited by ransomware gangs .

SonicWall SMA1000 SSRF Chains
SonicWall SMA1000 devices have been targeted by sophisticated SSRF exploitation chains. CVE-2026-15409 involved an unauthenticated SSRF that could be chained with other vulnerabilities to achieve Erlang RCE and subsequently steal credentials for Active Directory attacks . A subsequent zero-day chain exploited similar architectural weaknesses, combining SSRF with command injection .

Next.js Middleware SSRF
Vulnerabilities in Next.js, such as CVE-2025-57822, have demonstrated SSRF stemming from improperly sanitized input in middleware, allowing attackers to forge requests. These issues can impact self-hosted Next.js applications and require specific version upgrades for remediation .

Axios Vulnerabilities (Header Injection, NO_PROXY Bypass)
The widely used Axios HTTP client library has had multiple SSRF-related vulnerabilities. CVE-2026-40175 involved header injection leading to SSRF and RCE through prototype pollution. CVE-2025-62718 exploited a NO_PROXY bypass, allowing SSRF to occur under specific network configurations . These highlight the importance of securing dependencies and understanding their network behavior.

Craft CMS GraphQL SSRF Bypass
Craft CMS has seen SSRF vulnerabilities where GraphQL mutations could be manipulated. In one instance, CVE-2026-27127 involved bypassing SSRF protections by leveraging IPv6 resolution, allowing attackers to steal cloud metadata credentials. These exploits often hinge on subtle bypasses of validation logic .