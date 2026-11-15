# Reverse Index — SSRF

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| parameter URL / webhook / avatar / fetch | ganti ke http://localhost dan Collaborator | Basic SSRF against another back-end system · Basic SSRF against the  |
| import/export dari URL | SSRF ke 169.254.169.254 (cloud metadata) | Basic SSRF against another back-end system · Basic SSRF against the  |
| PDF/screenshot generator | SSRF lewat URL yang dirender | Basic SSRF against another back-end system · Basic SSRF against the  |
| integrasi third-party (Slack, GitHub, Jira) | webhook URL → internal | Basic SSRF against another back-end system · Basic SSRF against the  |
| GraphQL resolver yang fetch URL | SSRF via mutation argument | Accessing private GraphQL posts · Accidental exposure of private Gra |

## PoC corpus terkait (2 repo)

- `Ch4os1_CVE-2024-4157-SSRF-RCE-Reverse-Shell`
- `George0Papasotiriou_CVE-2026-2020-SSRF-via-URL-Parser-Differential`

## Lab PortSwigger: ssrf (5 lab)

- Basic SSRF against another back-end system (`lab-basic-ssrf-against-backend-system`)
- Basic SSRF against the local server (`lab-basic-ssrf-against-localhost`)
- SSRF with filter bypass via open redirection vulnerability (`lab-ssrf-filter-bypass-via-open-redirection`)
- SSRF with blacklist-based input filter (`lab-ssrf-with-blacklist-filter`)
- SSRF with whitelist-based input filter (`lab-ssrf-with-whitelist-filter`)
