---
name: attack-surface-index
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  Reverse index: target FEATURE -> first probe -> lab -> PoC repo. Use during 0B/0C
  when recon has just told you what the target HAS, and you need to know what to try
  before marking a class N/A. Covers RCE, IDOR/BOLA and ATO first.
metadata:
  hermes:
    tags: [security, recon, index, rce, idor, bola, ato, bug-bounty]
---

# Attack-Surface Index — dari fitur target ke probe pertama

**Masalah yang dipecahkan:** recon bilang "target punya fitur X", lalu kelas vuln
ditandai N/A karena tidak ada yang memetakan X → teknik. Index ini memutus pola itu.

**Cara pakai:** buka file kelas yang relevan, cari baris yang cocok dengan fitur yang
**benar-benar ada** di target, jalankan probe-nya SEBELUM menulis N/A.

## Kelas tersedia (33 kelas)

| Kelas | File | Fitur | PoC repo | Lab |
|---|---|---:|---:|---:|
| Account Takeover | `references/ato.md` | 8 | 20 | 0 |
| Auth Bypass | `references/auth-bypass.md` | 4 | 8 | 13 |
| Data Exposure (DB leak) | `references/data-exposure.md` | 8 | — | — |
| Web Cache Poisoning | `references/cache-poison.md` | 3 | 1 | 0 |
| Clickjacking | `references/clickjacking.md` | 3 | 0 | 5 |
| Cloud / Infrastructure | `references/cloud.md` | 5 | 11 | 0 |
| CORS Misconfiguration | `references/cors.md` | 3 | 1 | 3 |
| CRLF Injection | `references/crlf-injection.md` | 4 | 1 | 0 |
| Crypto / JWT | `references/crypto.md` | 4 | 7 | 6 |
| CSRF | `references/csrf.md` | 3 | 2 | 1 |
| Insecure Deserialization | `references/deserialization.md` | 4 | 4 | 0 |
| File Upload | `references/file-upload.md` | 4 | 3 | 6 |
| GraphQL | `references/graphql.md` | 4 | 1 | 5 |
| Host Header Injection | `references/host-header.md` | 3 | 0 | 0 |
| IDOR / BOLA / Broken Access Control | `references/idor-bola.md` | 6 | 6 | 13 |
| Information Disclosure | `references/info-disclosure.md` | 4 | 1 | 0 |
| LDAP Injection | `references/ldap.md` | 3 | 0 | 0 |
| LFI / Path Traversal | `references/lfi.md` | 4 | 4 | 6 |
| LLM / AI Attacks | `references/llm-ai.md` | 5 | 2 | 4 |
| NoSQL Injection | `references/nosql.md` | 4 | 5 | 3 |
| Open Redirect | `references/open-redirect.md` | 4 | 0 | 0 |
| Prototype Pollution | `references/prototype-pollution.md` | 3 | 1 | 0 |
| Race Conditions | `references/race-condition.md` | 4 | 4 | 6 |
| RCE & Command Injection | `references/rce.md` | 7 | 20 | 5 |
| HTTP Request Smuggling | `references/request-smuggling.md` | 3 | 1 | 3 |
| SQL Injection | `references/sqli.md` | 5 | 15 | 3 |
| SSRF | `references/ssrf.md` | 5 | 2 | 5 |
| Server-Side Template Injection | `references/ssti.md` | 4 | 4 | 0 |
| Supply Chain | `references/supply-chain.md` | 4 | 0 | 0 |
| Web Cache Deception | `references/web-cache-deception.md` | 3 | 0 | 5 |
| WebSockets | `references/websocket.md` | 3 | 1 | 2 |
| Cross-Site Scripting | `references/xss.md` | 5 | 8 | 0 |
| XXE | `references/xxe.md` | 4 | 3 | 4 |

**Total: 132 pemetaan fitur · 136 referensi PoC repo · 98 lab PortSwigger**

Kelas dengan 0 lab: PortSwigger tidak punya topik publik untuk kelas itu, atau lab-nya tidak dirender di `all-labs` (terverifikasi untuk authentication). Batas nyata, bukan kelalaian — probe-nya tetap berlaku, cuma tanpa contoh lab.

## Aturan pakai (mengikat)

1. **Satu baris cocok = probe wajib.** Bukan opsional. Kalau fiturnya ada dan probe
   belum dijalankan, kelas itu belum boleh N/A.
2. **Probe = differential.** Setiap probe membandingkan dua state (auth vs anon,
   user A vs user B, valid vs invalid). Satu response bukan temuan.
3. **Tiga kali sebelum "terblokir".** Ganti encoding, method, content-type, casing,
   nama parameter — baru boleh menyerah.
4. **N/A harus menyebut apa yang sudah dicoba**, bukan cuma "tidak ada".

## Kelas tambahan (path terverifikasi 2026-10-28)

| Kelas | Detail | Kapan |
|---|---|---|
| Reverse Engineering | `hunt-aa-modular/SKILL.md` (web3) · `poc-technique-atlas/references/reverse-engineering.md` | binary/source apa pun |
| Mobile / APK / iOS | `mobile-pentest/SKILL.md` | target punya app Android/iOS |
| Firmware / IoT | `poc-technique-atlas/references/firmware-pentest.md` | router/appliance/IoT |
| Binary Exploitation / Pwn | `poc-technique-atlas/references/pwn-chain.md` | ada vuln memory-corruption |
| Windows / AD | `poc-technique-atlas/references/windows-ad.md` | target enterprise Windows |
| Smart account / modular | `hunt-aa-modular/SKILL.md` | ERC-7579 / 4337 / 7702 surface |
| Signed approvals | `hunt-permit2-signature/SKILL.md` | Permit2 / ERC-3009 / EIP-712 |
| AMM hooks / pools | `hunt-amm-hooks/SKILL.md` | v4 / Balancer v3 / singleton |
| Restaking / LRT | `hunt-restaking-lrt/SKILL.md` | operator registry / withdrawal queue |
| Intent / settlement | `hunt-intent-settlement/SKILL.md` | solver / filler / attestor |
| Oracle / L2 | `hunt-oracle-l2/SKILL.md` | sequencer feed / Chainlink / Pyth |
| Vault inflation | `hunt-vault-inflation/SKILL.md` | ERC-4626 / share price |
| Upgradeability | `hunt-diamond-proxy/SKILL.md` | proxy / diamond / beacon |

## Master map — variasi attack exhaustif per kelas (2026)

Satu baris = satu kelas → referensi varian lengkap yang sudah disuntik ke skill `hunt-*`.
Kalau fitur ketemu, buka **dua** hal: (a) baris di tabel 33-kelas di atas (probe pertama), lalu
(b) referensi varian di bawah (semua payload/bypass/ladder). Ini yang bikin coverage exhaustif,
bukan cuma probe-detect.

| Kelas | Referensi varian exhaustif (path relatif ke skill) |
|---|---|
| SSRF | `hunt-ssrf/references/ssrf-vector-variants.md` — 10 katalog: IMDS semua provider, protocol matrix, IP-encoding, parser-differential, DNS-rebinding, gopher→RCE ladder, k8s hostname, file-format carrier, CRLF, escalation rungs |
| RCE / Command Injection | `hunt-rce/references/rce-vector-variants.md` — operator+filter-bypass, SSTI engine matrix, gadget per bahasa, LFI→RCE ladder, upload→RCE, config sinks, supply-chain, proof rungs |
| SQL Injection | `hunt-sqli/references/sqli-vector-variants.md` — fingerprint DBMS, dump/file/OS per DBMS, blind-exfil ladder (boolean/time/DNS/HTTP/error), second-order, WAF-bypass, RCE per DBMS |
| Insecure Deserialization | `hunt-deserialization/references/deser-gadget-catalog.md` — byte-format fingerprint, ysoserial chain list (`URLDNS` detection), phpggc, ysoserial.net, pickle/Marshal/Node/SnakeYAML, escalation rungs |
| SSTI | `hunt-ssti/references/ssti-sandbox-escape-matrix.md` — class-walker per engine (Jinja2/Twig/Freemarker/Velocity/SpEL/Smarty/Mako), blind OOB, sandbox-vs-RCE-vs-CSTI disambiguation |
| XXE | `hunt-xxe/references/xxe-variant-matrix.md` — XInclude, XSLT/Xalan→RCE, SSRF wrapper, exfil HTTP/DNS/error, port-scan oracle, hidden parsers, escalation rungs |
| XSS | `hunt-xss/references/xss-payload-atlas.md` — context→payload, event-handler/tag atlas, mXSS, CSP bypass, filter-evasion, AngularJS CSTI, stored carrier, escalation rungs |
| Kernel-layer RCE | `hunt-rce` → `exploit-cookbook/references/cve-2026-98432-ireq-opt-uaf.md` — remote pre-auth Linux TCP UAF (MPTCP listener) |
| JWT / Crypto forgery | `hunt-jwt-crypto/references/jwt-header-attack-matrix.md` — header field × attack, full alg set, kid sink, offline recovery |
| NoSQL Injection | `hunt-nosqli/references/nosqli-vector-matrix.md` — 16 operator catalog, string-breakout, type-juggling, store flavours |
| Cache Poisoning / WCD | `hunt-cache-poison/references/cache-poison-matrix.md` — unkeyed-input atlas, WCD ext list, CDN quirks, cache-key oracle |
| GraphQL abuse | `hunt-graphql/references/graphql-abuse-matrix.md` — introspection-bypass ladder, depth/cost/batching, resolver race table |
| IDOR / BOLA | `hunt-idor` (SKILL.md sendiri) — method-override + null-byte/array injection disuntik inline; APQ/GraphQL caller-supplied-id, harvest-opaque-id chain |
| Business Logic (SaaS) | `hunt-business-logic/references/vpn-service-logic-matrix.md` (VPN) + `fintech-tax-logic-matrix.md` (fintech/tax) |
| LLM / AI | `hunt-llm-ai` (SKILL.md) — LLM-to-SQL/shell + cost/DoS abuse inline; lihat juga `references/ai-tool-schema-ref-ssrf.md` |
| Unauth surface (web2) | `unauth-surface-discovery/references/unauth-vector-battery.md` — Tier 0–7 ordered checklist |
| Authed surface (web2) | `authed-webapp-audit/references/authed-vector-battery.md` — Tier 0–7 ordered checklist |
| Web3 (semua kelas) | `web3-audit/references/web3-hunt-dispatcher.md` — fingerprint→skill→kill-signal→first-probe routing (8 kelas hunt-* web3) |
| ATO (12 path → battery) | `hunt-ato/references/ato-path-battery.md` — Tier 0→7 ordered battery: reset-poisoning, email-change, JWT, password-step-up, recovery, subdomain-takeover, multi-tenant token |
| API Misconfig (matrix) | `hunt-api-misconfig/references/misconfig-variant-matrix.md` — mass-assignment, verb/param pollution, prototype pollution, OData bypass, OpenAPI exposure |
| RAG / Vector (fingerprint) | `hunt-rag-vector/references/vector-db-fingerprint-matrix.md` — 15 vector-DB default port + unauth endpoint + API-key leak location |
| OAuth / OIDC (battery) | `hunt-oauth/references/oauth-attack-battery.md` — Tier 0→7: OIDC discovery, redirect_uri (8 shape), state CSRF, DCR, consent/scope, token-endpoint |
| CORS (variant matrix) | `hunt-cors/references/cors-variant-matrix.md` — 10 ACAO reflection shape + preflight gating + postMessage weakness |
| CSRF (defense→bypass) | `hunt-csrf/references/csrf-bypass-matrix.md` — 11 defense→bypass rows (SameSite/CT/token/custom-header/Duende-BFF) |
| Host Header (battery) | `hunt-host-header/references/host-header-battery.md` — Tier 0→5: triage, reset-poisoning (6 shape), cache-poison, SSRF (2 mekanisme), OAuth |
| WebSocket (battery) | `hunt-websocket/references/websocket-attack-battery.md` — Tier 0→6 CSWSH/message-authz/tampering/namespace + fingerprint per framework |
| Rate Limit / Brute (matrix) | `hunt-brute-force/references/rate-limit-bypass-matrix.md` — 4-state classify + edge-throttle + seed-test + bypass + token-entropy |
| MFA Bypass (battery) | `hunt-mfa-bypass/references/mfa-bypass-battery.md` — Tier 0→6 response-manip/skip/OTP/reuse/race/device-trust/enrollment + prefix-oracle |
| DOM (battery) | `hunt-dom/references/dom-attack-battery.md` — Tier 0→5 clobbering/postMessage/SW/CSS-exfil/CSTI |
| Node.js (battery + gadget) | `hunt-nodejs/references/nodejs-attack-battery.md` — Tier 0→6 pollution→gadget-table→RCE/trust-proxy/SSTI/command-injection |
| Subdomain Takeover (5 chain) | `hunt-subdomain/SKILL.md` — OAuth redirect_uri + cookie-domain + CSP + CORS + DKIM/SPF eskalasi; sister-class dangling social link → `hunt-subdomain/references/dangling-social-link.md` |
| **appsec-fyi (second opinion, source-cited 2026)** | `appsec-fyi/references/<class>.md` — 25 kelas practical-guide dari appsec.fyi; sudah di-inject sebagai `references/appsec-fyi-techniques.md` ke 19 hunt skill (RCE/SSRF/SQLi/XSS/XXE/IDOR/JWT/CSRF/SSTI/deser/GraphQL/API/authn/LLM/mobile/OSINT/recon/secrets/supply-chain). Buka ketika butuh second opinion source-cited; owner skill tetap menang. WEB2-only. |

**Tambahan kelas 2026 (baru, belum masuk tabel 33-kelas di atas):** buka `bb-2026-attack-surface`
untuk 4 kelas bayar-gede (race/TOCTOU, GraphQL batching, RAG/LLM injection, cache/host-header).

**Alur spine (urutan wajib per target):** `attack-flows` Alur 9 — recon 0B → unauth battery →
provision 2 akun → authed battery → chain ≥3x → 0F report gate.

## Sumber data

- **PortSwigger labs** — 93 lab dengan solusi lengkap di
  `security/poc-technique-atlas/references/portswigger/`
- **PoC corpus** — 2.223 repo di `D:/data hermes/poc-compact/` (nama = produk/CVE)
- **hunt-\* skills** — 67 skill, masing-masing dengan metodologi & payload
  (termasuk 8 kelas web3 modern: `hunt-aa-modular`, `hunt-permit2-signature`,
  `hunt-amm-hooks`, `hunt-restaking-lrt`, `hunt-intent-settlement`, `hunt-oracle-l2`,
  `hunt-vault-inflation`, `hunt-diamond-proxy`)
- **appsec-fyi mirror** — `appsec-fyi/references/<class>.md` — 25 kelas practical-guide
  source-cited (RCE, SSRF, SQLi, XSS, XXE, IDOR/BOLA, JWT, CSRF, SSTI, deser, GraphQL,
  API-sec, authn/authz, AI/LLM, mobile, OSINT, recon, secrets, supply-chain, fuzzing,
  Burp, Python, talks). Second opinion source-cited per kelas → gandakan dengan baris
  master map / `hunt-*` saat kelas di-fingerprint. WEB2-only (see web3 note in
  `appsec-fyi/references/00-INDEX.md`).

## Memperluas index

Tambah baris ke file kelas saat menemukan pemetaan baru. Format:

```
| <fitur yang terlihat saat recon> | <probe pertama, satu kalimat> | <lab bila ada> |
```

Baris terbaik adalah yang **spesifik pada produk** ("admin panel dengan template
editor"), bukan generik ("ada halaman web").

## Kelas tambahan (reverse-skill package, 2026-10-21)

| Kelas | File | Kapan |
|---|---|---|
| Reverse Engineering | `security/poc-technique-atlas/references/reverse-engineering.md` | binary/source apa pun |
| Mobile / APK / iOS | `security/poc-technique-atlas/references/mobile-reverse.md` | target punya app Android/iOS |
| Firmware / IoT | `security/poc-technique-atlas/references/firmware-pentest.md` | router/appliance/IoT |
| Binary Exploitation / Pwn | `security/poc-technique-atlas/references/pwn-chain.md` | ada vuln memory-corruption |
| Windows / AD | `security/poc-technique-atlas/references/windows-ad.md` | target enterprise Windows |
| Web Cache Poisoning | `references/cache-poison.md` | CDN/proxy di depan app |
| Protocol RE | `security/poc-technique-atlas/references/protocol-reverse.md` | protokol binary custom |
| API Misconfig | `security/poc-technique-atlas/references/api-misconfig.md` | REST/GraphQL surface |

Detail teknik di `security/poc-technique-atlas/references/<kelas>.md` dan
`security/poc-technique-atlas/references/reverse-skill.md` (12 skill + fase mapping).