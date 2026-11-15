# Reverse Index — IDOR / BOLA / Broken Access Control

**Cara pakai:** saat recon menemukan *fitur* di kolom kiri, jalankan probe di
kolom tengah SEBELUM menandai kelas ini N/A. Lab & PoC di kolom kanan adalah
contoh nyata yang bisa dibaca/dijalankan.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| any endpoint with a numeric/uuid id in path or body | swap id A->B, compare response bodies | Insecure direct object references · Method-based access control can be |
| collection endpoint (/api/users, /api/orders) | fetch UNAUTHENTICATED first — cheapest primitive | Insecure direct object references · Method-based access control can be |
| GraphQL API | introspection -> mutations accepting id: -> BOLA-by-resolver | Accessing private GraphQL posts · Accidental exposure of private Graph |
| multi-tenant / org / workspace switch | cross-tenant read/write via tenantId tamper | Insecure direct object references · Method-based access control can be |
| file/download/export by name or id | sequential filename harvest (transcript 1.txt) | Insecure direct object references · Method-based access control can be |
| admin action reachable by non-admin role | method tampering POST->GET + Referer-based check bypass | Insecure direct object references · Method-based access control can be |

## PoC corpus terkait (6 repo)

- `AdityaBhatt3010_Sudo-Privilege-Escalation-Linux-CVE-2025-32463-and-CVE-2025-32462`
- `Asim-QAZi_BrokenAccessControl-News-Portal-Project-in-PHP-and-MySQL-in-PHPGurukul`
- `Asim-QAZi_Improper-Access-Control---in-Pet-Grooming-Management-Software`
- `Asim-QAZi_Improper-Access-Control-in-SourceCodester-Gas-Agency-Management-System`
- `BiiTts_CVE-2026-56423-MISP-deleteSelection-BrokenAccessControl`
- `George0Papasotiriou_CVE-2026-11107-Insecure-Direct-Object-Reference-with-Predictable-UUIDv1`

## Lab PortSwigger: access-control (13 lab)

- Insecure direct object references (`lab-insecure-direct-object-references`)
- Method-based access control can be circumvented (`lab-method-based-access-control-can-be-circumvented`)
- Multi-step process with no access control on one step (`lab-multi-step-process-with-no-access-control-on-one-step`)
- Referer-based access control (`lab-referer-based-access-control`)
- Unprotected admin functionality (`lab-unprotected-admin-functionality`)
- Unprotected admin functionality with unpredictable URL (`lab-unprotected-admin-functionality-with-unpredictable-url`)
- URL-based access control can be circumvented (`lab-url-based-access-control-can-be-circumvented`)
- User ID controlled by request parameter (`lab-user-id-controlled-by-request-parameter`)
- User ID controlled by request parameter with data leakage in redirect (`lab-user-id-controlled-by-request-parameter-with-data-leakage-in-redirect`)
- User ID controlled by request parameter with password disclosure (`lab-user-id-controlled-by-request-parameter-with-password-disclosure`)
- User ID controlled by request parameter, with unpredictable user IDs (`lab-user-id-controlled-by-request-parameter-with-unpredictable-user-ids`)
- User role can be modified in user profile (`lab-user-role-can-be-modified-in-user-profile`)
- User role controlled by request parameter (`lab-user-role-controlled-by-request-parameter`)
