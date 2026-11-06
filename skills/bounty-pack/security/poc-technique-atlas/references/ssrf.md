# SSRF

_Make the server issue requests; hit metadata, loopback, internal services, DNS-gap bypasses._

Techniques: 20  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | Critical Unauthenticated SSRF in SonicWall SMA1000 Series | `0xBlackash_CVE-2026-15409` |
| 2 | 🚨 CVE-2026-44578 — Next.js SSRF Vulnerability | `0xBlackash_CVE-2026-44578` |
| 3 | deco-cx apps Parameter analyticsScript.ts AnalyticsScript server-side request forgery | `0xcucumbersalad_CVE-2025-13796-PoC` |
| 4 | The SSRF filter checked hostname text, but the actual destination was decided later by DNS. That gap let attacker-controlled Webhook URLs reach loopback, metadata, and private netw | `0xmrma_CVE-2026-34207` |
| 5 | Penpot's remote image import let an authenticated file editor turn a normal media convenience feature into backend-origin SSRF because attacker-controlled URLs crossed into a redir | `0xmrma_CVE-2026-45806` |
| 6 | A vulnerability in the web-based management interface of Cisco Finesse could allow an unauthenticated, remote attacker to conduct an SSRF attack on an affected system. | `3zz4t_CVE-2024-20404` |
| 7 | Creating a Remote Code Execution (RCE) Metasploit module for the SSRF vulnerability (CVE-2024-38472) in Apache HTTP Server on Windows is challenging because SSRF itself doesn't dir | `Abdurahmon3236_CVE-2024-38472` |
| 8 | MrDoc <=0.95 is vulnerable to Server-Side Request Forgery (SSRF) in the validateurl function of the appdoc/utils.py file. | `Anike-x_CVE-2025-45250` |
| 9 | CVE-2026-42281: MagicMirror² ≤ 2.35.0 - Unauthenticated SSRF via /cors endpoint | `Astaruf_CVE-2026-42281` |
| 10 | Detects Oracle E-Business Suite (CVE-2025-61882). Detection: multi-tier checks — fingerprinting, version checks, endpoint &amp; SSRF tests, timing analysis &amp; controlled exploit | `BattalionX_http-oracle-ebs-cve-2025-61882.nse` |
| 11 | CVE-2026-73315: SSRF through PayPal certificate URL | `BomboBombone_CVE-2026-73315` |
| 12 | This repository contains a Python script designed to exploit the SSRF vulnerability (CVE-2024-21893) and command injection vulnerability (CVE-2024-21887) in Ivanti Connect Secure a | `Chocapikk_CVE-2024-21893-to-CVE-2024-21887` |
| 13 | ZITADEL SSRF Exploit - CVE-2025-67494 | `Chocapikk_CVE-2025-67494` |
| 14 | echo "=== CVE-2026-34753 SSRF Exploit === | `Dhiaelhak-Rached_CVE-2026-34753` |
| 15 | CVE-2026-22874 — Gitea SSRF PoC | `Eliot-code_CVE-2026-22874-PoC` |
| 16 | CVE-2026-33534 - EspoCRM 9.3.3 Authenticated SSRF | `EntroVyx_CVE-2026-33534` |
| 17 | Blind SSRF to RCE Exploit - PrestaShop 8.1.7 | `Fckroun_CVE-2024-41651` |
| 18 | Vulnerability Disclosure: SSRF in Inflectra SpiraTeam 7.2.00 | `GCatt-AS_CVE-2024-48590` |
| 19 | CVE-2026-2020 – SSRF via URL Parser Differential | `George0Papasotiriou_CVE-2026-2020-SSRF-via-URL-Parser-Differential` |
| 20 | CVE-2024-4157: Getting Reverse Shell on Havoc C2 - Chaining SSRF with RCE | `Ch4os1_CVE-2024-4157-SSRF-RCE-Reverse-Shell` |


## Corpus deep pass 2 4 teknik)
- `G33l0_Cve-2026-64638` — a missing plugin file makes wordpress 301 to a canonical url and then
- `G33l0_Cve-2026-64638` — a opens b (same-origin with a on the attacker origin), then navigates
- `12121211aaaaa_CVE_2024_30085` — four extra zero bytes are kept after structsize because cldflt computes
- `G33l0_Cve-2026-64638` — full chain - host the attacker origin and wait for an admin to visit


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **seed-006_ssrf-cloud-metadata**
  - [2026-02] SSRF → 云元数据 → AK/SK → OSS 全量数据
  - 通过 Web 应用的 SSRF 漏洞访问云元数据服务，获取临时凭据，最终导出 OSS 存储桶全部数据。
  - → AccessKeyId, SecretAccessKey, Token
  - | SSRF 被 WAF 拦截 169.254 | IP 黑名单 | 用 IPv6 地址 `[::ffff:169.254.169.254]` 绕过 | 15min |
