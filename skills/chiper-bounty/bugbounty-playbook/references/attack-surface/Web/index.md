# Web Applications

> tags: web, attack-surface

> related: Attack-Surface/Web/Authentication/Login-Bypass, Attack-Surface/Web/Authentication/Password-Reset, Attack-Surface/Web/Authentication/OAuth, Attack-Surface/Web/Authentication/SSO, Attack-Surface/Web/Authentication/MFA-Bypass, Attack-Surface/Web/Authentication/Session-Management, Attack-Surface/Web/Authentication/JWT, Attack-Surface/Web/Authorization/IDOR, Attack-Surface/Web/Authorization/BOLA, Attack-Surface/Web/Authorization/Privilege-Escalation, Attack-Surface/Web/Authorization/Multi-Tenancy, Attack-Surface/Web/Injection/XSS/, Attack-Surface/Web/Injection/SQLi/, Attack-Surface/Web/Injection/SSTI, Attack-Surface/Web/Injection/Host-Header, Attack-Surface/Web/Injection/NoSQLi, Attack-Surface/Web/Injection/Deserialization, Attack-Surface/Web/Injection/Command-Injection, Attack-Surface/Web/SSRF/, Attack-Surface/Web/Client-Side/CSRF, Attack-Surface/Web/Client-Side/postMessage-Vulnerabilities, Attack-Surface/Web/Client-Side/CORS, Attack-Surface/Web/Client-Side/WebSocket, Attack-Surface/Web/Client-Side/Subdomain-Takeover, Attack-Surface/Web/Client-Side/Clickjacking, Attack-Surface/Web/Client-Side/Prototype-Pollution, Attack-Surface/Web/Business-Logic/Race-Conditions, Attack-Surface/Web/Business-Logic/Price-Manipulation, Attack-Surface/Web/Business-Logic/State-Machine, Attack-Surface/Web/Business-Logic/Mass-Assignment, Attack-Surface/Web/Infrastructure/Cache-Poisoning, Attack-Surface/Web/Infrastructure/Request-Smuggling, Attack-Surface/Web/Infrastructure/Open-Redirect, Attack-Surface/Web/Infrastructure/Web-Cache-Deception, Attack-Surface/Web/Infrastructure/HTTP2-Attacks

Web Applications
Widest attack surface and deepest section of this playbook. Organized by category rather than alphabetically because the categories reflect how you actually think about testing. You test authentication as a system, not individual bugs in isolation.
Authentication
How users prove who they are. Every auth implementation is custom in ways that matter.

Login Bypass Patterns- Password Reset Flows- OAuth Misconfigurations- SSO & SAML Attacks- MFA Bypass- Session Management- JWT Attacks

Authorization
How the app decides what you're allowed to do. Most consistently rewarded bug class in my experience.

IDOR Patterns- BOLA & BFLA- Privilege Escalation- Multi-Tenancy Bugs

Injection
Putting data where the application expects instructions.

XSS - Reflected, stored, DOM, mXSS, framework-specific, WAF bypass
SQL Injection - Error-based, blind, second-order, ORM-specific- Server-Side Template Injection- Host Header Injection- NoSQL Injection- Deserialization- Command Injection

SSRF
Making the server send requests on your behalf. Gateway to cloud metadata and internal networks.

SSRF - Full methodology, bypass techniques, blind SSRF, cloud exploitation

Client-Side
Bugs that execute in the user's browser.

CSRF- postMessage Vulnerabilities - Full methodology, origin bypass, widget exploitation
CORS Misconfigurations- WebSocket Security- Subdomain Takeover- Clickjacking- Prototype Pollution

Business Logic
The bugs no scanner will ever find.

Race Conditions- Price & Quantity Manipulation- State Machine Bugs- Mass Assignment

Infrastructure
Server and proxy layer misconfigurations.

Cache Poisoning- HTTP Request Smuggling- Open Redirect- Web Cache Deception- 2 Attacks
