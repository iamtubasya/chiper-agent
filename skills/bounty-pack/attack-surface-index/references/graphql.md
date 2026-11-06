# Reverse Index — GraphQL

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| endpoint /graphql atau /api/graphql | introspection query → dump schema | Accessing private GraphQL posts · Accidental exposure of private Gra |
| query dengan variabel id | BOLA-by-resolver: substitute victim id | Accessing private GraphQL posts · Accidental exposure of private Gra |
| mutation yang ambil keputusan authz | tes tanpa auth directive | Accessing private GraphQL posts · Accidental exposure of private Gra |
| batch/alias dalam satu request | rate-limit bypass + brute via alias | Accessing private GraphQL posts · Accidental exposure of private Gra |

## PoC corpus terkait (1 repo)

- `George0Papasotiriou_CVE-2026-11103-GraphQL-Batching-Alias-Rate-Limit-Bypass`

## Lab PortSwigger: graphql (5 lab)

- Accessing private GraphQL posts (`lab-graphql-reading-private-posts`)
- Accidental exposure of private GraphQL fields (`lab-graphql-accidental-field-exposure`)
- Finding a hidden GraphQL endpoint (`lab-graphql-find-the-endpoint`)
- Bypassing GraphQL brute force protections (`lab-graphql-brute-force-protection-bypass`)
- Performing CSRF exploits over GraphQL (`lab-graphql-csrf-via-graphql-api`)
