# GraphQL

_Introspection, batching, alias/IDOR, injection, DoS._

Techniques: 3  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | CVE-2026-19478 GitLab GraphQL unauthenticated project deletion | `EQSTLab_CVE-2026-19478` |
| 2 | 3. CVE-2026-11103 – GraphQL Batching Alias Rate Limit Bypass | `George0Papasotiriou_CVE-2026-11103-GraphQL-Batching-Alias-Rate-Limit-B` |
| 3 | CVE-2026-24136 - Saleor GraphQL IDOR / Unauthenticated PII Exfiltration | `BlankBire_CVE-2026-24136-Lab` |
