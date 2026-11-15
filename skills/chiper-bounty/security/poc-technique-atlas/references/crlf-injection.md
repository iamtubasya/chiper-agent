# CRLF / Request Smuggling

_Header injection, response splitting, HTTP desync._

Techniques: 4  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | A CRLF vulnerability (%0D%0A) exists in TinyWeb Server creating a potential risk for redirection, XSS and other cool tricks depending on how the client interprets the HTTP Response | `DMCERTCE_CRLF_Tiny` |
| 2 | CVE-2026-33149 — Host Header Injection in Tandoor Recipes | `FilipeGaudard_CVE-2026-33149-PoC` |
| 3 | CVE-2026-1010 – WebSocket Connection Smuggling | `George0Papasotiriou_CVE-2026-1010-WebSocket-Connection-Smuggling-via-M` |
| 4 | CVE-2026-11113 – SMTP Header Injection in Contact Form | `George0Papasotiriou_CVE-2026-11113-SMTP-Header-Injection-in-Contact-Fo` |

## 2026 sweep 3 (dork pass 2026-10-18 — 2 repo)

- **CVE-2026-24061** — GNU inetutils-telnetd: CRLF injection in the login/negotiation path
  leads to **authentication bypass and an instant root shell**. Lesson: CRLF reaching an
  auth or protocol-negotiation path is an auth bypass, not just response splitting.
- **CVE-2026-22777** — ComfyUI-Manager CRLF injection → RCE, chained with CVE-2025-67303
  (arbitrary git install → code execution). Lesson: a CRLF that reaches an installer or
  package-manager argument is code execution.
- **CVE-2026-34975** — CRLF **email header** injection in Plunk's raw MIME construction:
  SES silently BCCs every outgoing email to an attacker address via the compromised API key.
  Lesson: test CRLF against mail-sending paths, not only HTTP responses.

## 2026 sweep 5 (dork pass 2026-10-18 — 3 repo)

- **CVE-2026-73570 (Zimbra ZCS, CVSS 8.9, CISA KEV)** — SMTP log poisoning → swatchdog →
  OS command injection. The attack needs **no SNMP exposure**: malicious input arrives over
  standard SMTP, and a custom low-level SMTP client bypasses `smtplib`'s address validation
  to send non-RFC-compliant payloads. Fix was string-form → list-form `system()`.
- **CVE-2026-46584 (Apache Camel camel-mail)** — `mail.smtp.*` headers settable by an
  unauthenticated HTTP client because the `HttpHeaderFilterStrategy` strips only `Camel*`
  prefixes. Lesson: header allow-lists that filter by **prefix** are bypassable by any header
  outside the prefix.
- **CVE-2026-23829 (Mailpit)** — CRLF injection from a flawed regex: the character class
  allows `\r` because `\v` inside brackets matches only vertical tab, not CR/LF.
- **CVE-2026-11113 (contact form)** — user-supplied email address inserted into the mail
  header without sanitisation. The simplest and most common mail-header bug.
