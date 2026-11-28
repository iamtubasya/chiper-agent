# Payload Shelf — chiper-bb-methodology

Skill ini metodologi, bukan kelas: **payload per kelas ada di sub-skill pemiliknya**.
Ambil dari sini per fase/decision flow:

| Kelas | Payload |
|---|---|
| SQLi | `../chiper-web-sqli/payloads.md` (+ `../chiper-web-sqli/sqli-cross-db-guide.md`, `sqli-double-query-guide.md`) |
| XSS | `../chiper-web-xss/payloads.md` |
| SSRF | `../chiper-web-ssrf/payloads.md` |
| XXE | `../chiper-web-xxe/payloads.md` |
| IDOR/BOLA | `../chiper-web-access-control/payloads.md` |
| Auth bypass | `../chiper-web-auth-bypass/payloads.md` |
| Deserialization | `../chiper-web-deserialization/payloads.md` |
| File inclusion | `../chiper-file-inclusion/payloads.md` |
| Cmd/SSTI/LDAP/NoSQL | `../chiper-command-injection-advanced/payloads.md` |
| API (REST/GraphQL) | `../chiper-api-security/payloads.md` |
| Race | `../chiper-concurrency-exploitation/payloads.md` |
| Lintas kelas / encoder | `../chiper-payload-generation/payloads.md` |

Pre-flight tetap: `command -v` → `../chiper-bootstrap/`.
