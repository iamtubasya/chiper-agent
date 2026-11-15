## Complete Report Structure (Standard Sections)

Every bug bounty PDF should include these sections in order:
1. **Cover/Header** — Title, meta table (Platform, Program, Severity, CVSS, Endpoint, Researcher, Date)
2. **Executive Summary** — 2-3 paragraphs: what, why it matters, severity
3. **Severity Justification** — CVSS vector breakdown table + arguments for classification
4. **Technical Details** — Authentication flow, affected endpoints, how things work normally
5. **Proof of Concept — Step-by-Step** — Each step with: description, HTTP request/response, screenshot
6. **Negative Tests** — Table of what you tried and couldn't break (shows thoroughness)
7. **Impact Analysis** — Direct impact, attack vectors table, business impact
8. **Remediation** — Immediate actions, defensive measures, code-level fix
9. **Full HTTP Exchange** — Complete raw POC copy-pasteable by triager
10. **Disclosure Statement** — Authorization, scope, compliance

