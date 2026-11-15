# SSTI / CSTI

_Template injection to RCE or client-side code exec._

Techniques: 7  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | 🚨 CVE-2026-34724 - Zammad < 7.0.1 - Server-Side Template Injection (SSTI) to Remote Code Execution (RCE) via AI Agent | `0xBlackash_CVE-2026-34724` |
| 2 | Client-side template injection (CSTI) in Azuriom CMS admin dashboard allows a low-privilege user to execute arbitrary template code in the context of an administrator's session. Th | `1337Skid_CVE-2025-65271` |
| 3 | Server Side Template Injection | `A3h1nt_CVEs` |
| 4 | CVE-2025-64087 (SSTI FreeMarker) | `AT190510-Cuong_CVE-2025-64087-SSTI-` |
| 5 | CVE-2026-38165 (SSTI Velocity) | `AT190510-Cuong_CVE-2026-38165-SSTI-` |
| 6 | SelectCours-Sever-side-Template-injection | `Andriesces_SelectCours-_Sever-side-Template-injection` |
| 7 | CVE-2026-11104 – Python SSTI via Jinja2 /attr Filter Bypass | `George0Papasotiriou_CVE-2026-11104-Python-SSTI-via-Jinja2-attr-Filter-` |
