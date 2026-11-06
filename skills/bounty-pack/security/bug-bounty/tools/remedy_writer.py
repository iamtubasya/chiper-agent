#!/usr/bin/env python3
"""
remedy_writer.py — Write remediation recommendations for findings.
Usage:
  python3 remedy_writer.py --title "SQLi in login" --severity P1 --type sqli --output remedy.md
"""
import sys, os, argparse
from datetime import datetime

REMEDIATION_TEMPLATES = {
    "sqli": {
        "title": "SQL Injection",
        "remediation": [
            "Use parameterized queries (prepared statements) for all database interactions.",
            "Implement input validation and sanitization for all user-supplied data.",
            "Apply least-privilege database permissions — application DB user should only have necessary access.",
            "Deploy a Web Application Firewall (WAF) with SQL injection rules.",
            "Enable database query logging for monitoring.",
        ],
        "references": [
            "https://owasp.org/www-community/attacks/SQL_Injection",
            "https://cwe.mitre.org/data/definitions/89.html",
        ]
    },
    "xss": {
        "title": "Cross-Site Scripting (XSS)",
        "remediation": [
            "Encode all output context-appropriately (HTML, JS, URL, CSS).",
            "Implement Content Security Policy (CSP) headers.",
            "Use frameworks that auto-escape by default (React, Vue, Angular).",
            "Validate and sanitize all user input on both client and server side.",
            "Use HttpOnly and Secure flags on session cookies.",
        ],
        "references": [
            "https://owasp.org/www-community/attacks/xss/",
            "https://cwe.mitre.org/data/definitions/79.html",
        ]
    },
    "idor": {
        "title": "Insecure Direct Object Reference (IDOR)",
        "remediation": [
            "Implement authorization checks for every object access.",
            "Use indirect references (e.g., UUIDs instead of sequential IDs).",
            "Enforce ownership verification — user can only access their own resources.",
            "Implement rate limiting on object access patterns.",
            "Log and monitor for bulk object enumeration attempts.",
        ],
        "references": [
            "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References",
            "https://cwe.mitre.org/data/definitions/639.html",
        ]
    },
    "ssrf": {
        "title": "Server-Side Request Forgery (SSRF)",
        "remediation": [
            "Validate and sanitize all user-supplied URLs.",
            "Whitelist allowed domains/IPs for server-side requests.",
            "Block requests to internal/private IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).",
            "Use a dedicated network segment for server-side request handling.",
            "Disable unnecessary URL schemes (file://, gopher://, dict://).",
        ],
        "references": [
            "https://owasp.org/www-community/attacks/Server_Side_Request_Forgery",
            "https://cwe.mitre.org/data/definitions/918.html",
        ]
    },
    "rce": {
        "title": "Remote Code Execution (RCE)",
        "remediation": [
            "Never pass user input to system commands or code execution functions.",
            "Use language-specific sandboxing or containerization for dynamic code.",
            "Implement strict input validation and output encoding.",
            "Apply principle of least privilege — application should run with minimal permissions.",
            "Enable code signing and integrity verification.",
        ],
        "references": [
            "https://owasp.org/www-community/attacks/Command_Injection",
            "https://cwe.mitre.org/data/definitions/78.html",
        ]
    },
    "auth_bypass": {
        "title": "Authentication Bypass",
        "remediation": [
            "Enforce authentication checks on all protected endpoints.",
            "Use established authentication frameworks (OAuth 2.0, OpenID Connect).",
            "Implement multi-factor authentication (MFA).",
            "Validate tokens server-side on every request.",
            "Implement account lockout and brute-force protection.",
        ],
        "references": [
            "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/03-Authentication_Testing/",
            "https://cwe.mitre.org/data/definitions/287.html",
        ]
    },
    "privilege_escalation": {
        "title": "Privilege Escalation",
        "remediation": [
            "Enforce role-based access control (RBAC) on all endpoints.",
            "Validate user roles server-side, not just in the UI.",
            "Implement principle of least privilege.",
            "Audit all permission checks regularly.",
            "Use parameterized queries to prevent unauthorized data access.",
        ],
        "references": [
            "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/",
            "https://cwe.mitre.org/data/definitions/269.html",
        ]
    },
    "default": {
        "title": "Security Vulnerability",
        "remediation": [
            "Follow OWASP Top 10 guidelines for this vulnerability class.",
            "Implement input validation and output encoding.",
            "Apply defense-in-depth strategy.",
            "Conduct regular security audits and penetration testing.",
            "Implement security monitoring and incident response.",
        ],
        "references": [
            "https://owasp.org/www-project-top-ten/",
        ]
    }
}

def get_remediation(vuln_type):
    return REMEDIATION_TEMPLATES.get(vuln_type.lower(), REMEDIATION_TEMPLATES["default"])

def write_remediation(title, severity, vuln_type, output):
    rem = get_remediation(vuln_type)

    content = f"""# Remediation: {title}

**Severity:** {severity}
**Vulnerability Type:** {rem['title']}
**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}

## Recommended Fixes

"""
    for i, fix in enumerate(rem["remediation"], 1):
        content += f"{i}. {fix}\n"

    content += f"""
## References

"""
    for ref in rem["references"]:
        content += f"- {ref}\n"

    content += f"""
## Testing the Fix

After implementing the remediation:
1. Re-run the same exploit chain that found this vulnerability
2. Verify the vulnerability is no longer exploitable
3. Check for regression in related functionality
4. Document the fix in your security changelog
"""
    with open(output, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[REMEDY] Generated: {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate remediation recommendations")
    parser.add_argument("--title", required=True)
    parser.add_argument("--severity", default="P2")
    parser.add_argument("--type", default="default", help="Vuln type: sqli, xss, idor, ssrf, rce, auth_bypass, privilege_escalation")
    parser.add_argument("--output", default="remedy.md")
    args = parser.parse_args()
    write_remediation(args.title, args.severity, args.type, args.output)
