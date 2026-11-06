<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/apisec.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Core Mechanics: Attack Vectors and Vulnerabilities

Core Mechanics: Attack Vectors and Vulnerabilities
API security is fundamentally about managing access control, data exposure, and the integrity of business logic implemented through API endpoints. Common vulnerabilities span several categories, often mirroring traditional web application risks but with API-specific nuances.

Authentication and Authorization Weaknesses
Authentication and authorization failures remain the most prevalent and impactful API vulnerabilities. This includes:

• Broken Object Level Authorization (BOLA): Attackers manipulate object identifiers in requests to access or modify resources belonging to other users. This is frequently exploited through predictable IDs in API calls .
• Broken Function Level Authorization (BFLA): Users can execute functions or access administrative actions that are beyond their assigned privileges. This often arises from insufficient checks on user roles or permissions .
• Authentication Bypass: Flaws in authentication mechanisms, such as weak credential validation, insecure token handling, or misconfigured authorization services, allow unauthorized access .
• Mass Assignment: Backend systems fail to filter user-supplied data, allowing attackers to inject unexpected parameters and modify unintended object properties. This can lead to privilege escalation or unauthorized state changes .
• Insecure Direct Object References (IDOR): While similar to BOLA, IDOR often refers to predictable identifiers that allow access to unauthorized resources.
Data Exposure and Leakage
APIs frequently handle sensitive data, making their protection critical.

• Excessive Data Exposure: APIs return more data than necessary, potentially exposing sensitive fields or PII (Personally Identifiable Information) that the client application does not require. This can be a consequence of poorly defined API responses or ORM (Object-Relational Mapper) configurations .
• Secrets Exposure: API keys, OAuth secrets, database credentials, and other sensitive tokens are often leaked. Common vectors include hardcoding in source code, public repositories, container images, environment variables, and application logs . Fake API keys stored insecurely have also been observed .
• Clear Text Logging: Sensitive information logged in plain text can be intercepted or accessed if log files are compromised .
• Cross-Tenant Data Exposure: In multi-tenant environments, residual data blocks or misconfigurations can inadvertently expose data from one tenant to another .
Injection and Input Validation Flaws
Traditional injection attacks remain relevant in the API context.

• SQL Injection: Malicious SQL code injected into API parameters can compromise database integrity and confidentiality .
• Cross-Site Scripting (XSS): While less direct than in web applications, APIs can still be vectors for XSS, particularly if they render user-supplied content without proper sanitization or if data is reflected back to the client in an unsafe manner . SVG sanitizer bypasses can lead to XSS by manipulating namespaces, using foreignObject, or employing nested SVGs .
• Command Injection: Malicious commands can be injected through API parameters, leading to arbitrary code execution on the server .
• Improper Input Validation: Insufficient validation of user-supplied data in API requests can lead to various vulnerabilities, including buffer overflows, business logic flaws, and injection attacks .
Business Logic and Flow Vulnerabilities
Exploiting the intended functionality of an application through its API can be a potent attack vector.

• Unrestricted Access to Sensitive Business Flows: Legitimate business processes, like payment processing or reservation systems, can be abused if APIs do not sufficiently validate actions or states. Examples include payment bypasses  or AI agents autonomously canceling reservations due to authorization vulnerabilities .
• Client-Provided User\_Id Abuse: Password reset features that accept a client-provided User_Id can be abused for account takeover .
• Protocol Handler Attacks: Exploiting custom URL schemes and Progressive Web Apps (PWAs) for protocol handler attacks can bypass origin validation .
Server-Side Request Forgery (SSRF)
SSRF vulnerabilities occur when an API can be tricked into making requests to unintended internal or external resources. This can be used to scan internal networks, access sensitive cloud metadata, or interact with internal services .

HTTP Smuggling and Desync Attacks
These attacks exploit discrepancies in how different network intermediaries (e.g., load balancers, WAFs, backend servers) parse HTTP requests, particularly when dealing with Content-Length and Transfer-Encoding headers. This can lead to request splitting, response queue poisoning, and session cookie theft . HTTP/2 desync attacks are also a growing concern .

AI-Specific Vulnerabilities
The integration of AI introduces novel attack surfaces.

• Insecure Handling of Model Context Protocol (MCP) Configurations: Exploiting insecure MCP servers in AI platforms can lead to Remote Code Execution (RCE) .
• Vulnerabilities in AI Frameworks: Platforms like Flowise, PraisonAI, and Ollama have exhibited vulnerabilities, including RCE, memory leaks exposing API keys and prompts, and authentication bypasses .
• Prompt Injection: While often discussed, the focus is shifting towards AI agents performing actions they are authorized to do, rather than direct prompt manipulation .
• AI-Generated Code Risks: Code generated by AI models has a higher vulnerability density, often containing critical security gaps .
• API Key Exfiltration via AI Artifacts: For example, API keys can be exfiltrated through Hugging Face download counters or within ChatGPT's hidden reasoning logs .

## Notable Techniques

Notable Techniques
Several specific techniques are frequently employed by attackers and are critical for practitioners to understand.

SVG Sanitizer Bypasses
Attackers can bypass SVG sanitizers using various techniques to achieve Cross-Site Scripting (XSS). These include:

• Namespace Tricks: Manipulating XML namespaces to inject executable content.
• foreignObject Element: Embedding SVG content within HTML contexts.
• Nested SVGs: Embedding SVGs within SVGs to confound parsers.
• animate and animateTransform Tags: Using these for scripting within SVGs.
• XSLT Stylesheets via Data URLs or Link Headers: Injecting malicious XSLT to process SVG content.
• USE Element with Image Polyglots: Leveraging image polyglots to render malicious code.
These bypasses can be effective against multiple libraries designed to sanitize SVG input .

Weak JWT Signature Validation
JSON Web Tokens (JWTs) are commonly used for stateless authentication. Weaknesses arise when:

• JWT None-Algorithm Attack: Attackers can tamper with tokens to set the algorithm to "none," effectively removing signature validation, allowing them to forge tokens with arbitrary claims .
• JWT Missing Signature Validation: Developers may skip signature validation entirely, allowing for forged tokens to be accepted .
• JWT Algorithm Confusion: Exploiting implementations that incorrectly handle algorithm negotiation, potentially allowing public keys to be used as secrets.
Loopjacking
This attack class targets applications that involve user interaction and state changes, particularly in API-driven workflows.

• Representation-based Attacks: Manipulating the representation of an action to trick the user into approving an unintended state change.
• Post-approval State-Substitution Attacks: Modifying the state of an operation after the user has already approved it.
Loopjacking vulnerabilities have been identified in agent operating systems .

Exploiting Custom URL Schemes and PWAs
Progressive Web Apps (PWAs) and custom URL schemes can be exploited to bypass origin validation. An "Evil PWA" attack can leverage these mechanisms to trick the user into granting permissions or executing actions that violate usual browser security policies .

CRLF Injection for HTTP Desync Attacks
Carriage Return Line Feed (CRLF) injection is a potent technique for inducing HTTP desynchronization. This can be used for:

• Request Splitting: Creating two distinct requests from what appears to be a single one.
• Response Queue Poisoning: Forcing a backend server to prepend crafted data to a legitimate user's response.
• Session Cookie Theft: Using poisoned responses to steal session cookies.
Tools like Hackvertor can assist in crafting these payloads .

Arbitrary File Read (Path Traversal)
This classic vulnerability allows attackers to read sensitive files from the server by manipulating path components in API requests. Notable instances include vulnerabilities in Atlassian products  and AWS AgentCore infrastructure .

Insecure Deserialization
Deserializing untrusted data without proper validation can lead to Remote Code Execution (RCE). This is a common risk when dealing with serialized objects, particularly in languages like Python (e.g., pd.read_pickle()) .

Uncontrolled Resource Consumption (Denial of Service)
APIs can be targeted with requests designed to exhaust server resources, leading to Denial of Service (DoS). This includes:

• HTTP/3 Request Read Timeout Not Applied: Exploiting scenarios where specific timeouts are not enforced, leading to resource exhaustion .
• GraphQL Deeply Nested Queries: Crafting complex, deeply nested GraphQL queries that overload the server's processing capacity .
• GraphQL Batching Exploits: Amplifying DoS attacks by sending multiple queries within a single batch request .
API Key Theft and Credit Consumption
API keys, once compromised, can be used for unauthorized access, data exfiltration, and malicious actions, often leading to unexpected credit consumption for the service provider. This has been observed in contexts ranging from cloud services to AI model platforms .

Exposure of OTPs in API Responses
One-Time Passwords (OTPs) are critical for multi-factor authentication. Exposing these in API responses, even temporarily, can enable account takeover attacks .

Unauthenticated API Endpoint Exposing Sensitive Data
A common and critical issue is the existence of API endpoints that should be protected but are publicly accessible without authentication, leading to the exposure of user records, PII, or other sensitive information .

Exploiting Agent Harnesses for Forged Instructions
In environments utilizing agent frameworks, vulnerabilities in agent harnesses can allow attackers to inject forged instructions, leading to unauthorized tool execution or command execution .