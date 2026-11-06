# Auth Bypass / AuthN flaws

_Bypass login, MFA, JWT, OAuth, SAML, session trust._

Techniques: 70  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | CVE-2025-58434 Flowiseai Auth Bypass PoC | `00lucasm_CVE-2025-58434-Flowiseai-Auth-Bypass-PoC` |
| 2 | CVE-2024-47533 – Cobbler XMLRPC Authentication Bypass → Reverse Shell (Unauthenticated RCE) | `00xCanelo_CVE-2024-47533-PoC` |
| 3 | CVE-2026-24061 - telnetd Authentication Bypass PoC | `0p5cur_CVE-2026-24061-POC` |
| 4 | CVE-2025-32433 Erlang/OTP SSH RCE EXP | `0x7556_CVE-2025-32433` |
| 5 | 🛡️ CVE-2025-13315 - Critical Authentication Bypass in Twonky Server 8.5.2 | `0xBlackash_CVE-2025-13315` |
| 6 | 🚨 CVE-2025-31161 - Critical Authentication Bypass in CrushFTP | `0xBlackash_CVE-2025-31161` |
| 7 | 🚨 CVE-2025-32433: Unauthenticated RCE in Erlang/OTP SSH Server | `0xBlackash_CVE-2025-32433` |
| 8 | 🛡️ CVE-2025-64446 - FortiWeb Critical Authentication Bypass & Path Traversal | `0xBlackash_CVE-2025-64446` |
| 9 | 🤖 CVE-2026-0073 - Wireless ADB Authentication Bypass | `0xBlackash_CVE-2026-0073` |
| 10 | 🚨 CVE-2026-0257 - Authentication Bypass Vulnerabilities | `0xBlackash_CVE-2026-0257` |
| 11 | 🛡️ CVE-2026-20127 — Cisco Catalyst SD-WAN Authentication Bypass | `0xBlackash_CVE-2026-20127` |
| 12 | 🚨 CVE-2026-21962 - Critical Authentication Bypass Vulnerability | `0xBlackash_CVE-2026-21962` |
| 13 | CVE-2026-2699 — Progress ShareFile Storage Zones Controller Authentication Bypass | `0xBlackash_CVE-2026-2699` |
| 14 | 🚨 CVE-2026-35616 - FortiClient EMS Authentication Bypass 🚨 | `0xBlackash_CVE-2026-35616` |
| 15 | ⚠️ CVE-2026-41940 - cPanel & WHM Authentication Bypass | `0xBlackash_CVE-2026-41940` |
| 16 | 🚨 CVE-2026-50751 - Authentication Bypass in Check Point VPN (IKEv1) | `0xBlackash_CVE-2026-50751` |
| 17 | 🚨 CVE-2026-60206 — WebLogic SAML Takeover | `0xBlackash_CVE-2026-60206` |
| 18 | 🚨 CVE-2026-8451 - NetScaler SAML IdP Memory Overread Vulnerability | `0xBlackash_CVE-2026-8451` |
| 19 | CVE-2026-82329 — JFrog Artifactory Unauthenticated Authentication Bypass (Mass Exploit) | `0xCyp1337_CVE-2026-82329` |
| 20 | CrushFTP Authentication Bypass - CVE-2025-31161 | `0xDTC_CrushFTP-auth-bypass-CVE-2025-31161` |
| 21 | Exploit for Mitel MiCollab Authentication Bypass and Arbitrary File Read Vulnerability (CVE-2024-41713) | `0xNehru_mitel-micollab-exploit` |
| 22 | This repository contains a condensed and optimized proof-of-concept (PoC) exploit for CVE-2024-35250. The code is based on Varwara's original release PoC. | `0xROOTPLS_GiveMeKernel` |
| 23 | CVE-2026-41940: cPanel/WHM Authentication Bypass (Single & Multi-Target) | `0xYuR1_CVE-2026-41940` |
| 24 | ADB TLS Auth Bypass Exploit (CVE-2026-0073) | `0xbinder_CVE-2026-0073` |
| 25 | WAVLINK WiFi Router — CSRF Authentication Bypass Chained with Stored Command Injection | `0xcc12138_wavlink-nu516u1-csrf-command-injection-` |
| 26 | CVE-2026-32136exploit - AdGuard Home h2c Upgrade Auth Bypass | `0xdak_CVE-2026-32136_exploit` |
| 27 | CVE-2026-59243 — Apache Airflow FAB Provider OAuth Auth Bypass → DAG RCE | `0xdak_CVE-2026-59243_exploit` |
| 28 | CVE-2025-31161 - CrushFTP User Creation Authentication Bypass Exploit | `0xgh057r3c0n_CVE-2025-31161` |
| 29 | 🔥 CVE-2026-41940 – cPanel & WHM Auth Bypass | `0xgh057r3c0n_CVE-2026-41940` |
| 30 | CVE-2024-0012 an authentication bypass in Palo Alto Networks PAN-OS software enables an unauthenticated attacker with network access to the management web interface to gain PAN-OS  | `0xjessie21_CVE-2024-0012` |
| 31 | FortiWeb Authentication Bypass to Remote Code Execution Exploit | `34zY_CVE-2025-52970` |
| 32 | Simple Python PoC to check Citrix NetScaler ADC / Gateway instances for CVE-2025-12101 (reflected XSS on /cgi/logout) using a crafted SAMLResponse + RelayState payload. | `6h4ack_CVE-2025-12101-checker` |
| 33 | CVE-2025-3639 PoC - Liferay Portal/DXP Login Bypass | `6lj_CVE-2025-3639` |
| 34 | A Nuclei template to detect CVE-2025-29927 the Next.js authentication bypass vulnerability. If you want to understand exactly how this vulnerability works, you can read the origina | `6mile_nextjs-CVE-2025-29927` |
| 35 | KiviCare-authentication-bypass-script-for-wordpress | `AkAi3_KiviCare-authentication-bypass-script-for-wordpress` |
| 36 | CVE-2026-35616 — FortiClient EMS Pre-Auth Bypass | `Alaatk_CVE-2026-35616` |
| 37 | Erlang/OTP SSH Pre-Authentication Channel Confusion | `AntonieSoga_Erlang-OTP-PoC_CVE-2025-32433` |
| 38 | bypass github | `Arian91_CVE-2025-23369_SAML_bypass` |
| 39 | CVE-2026-1337 - Apache WebPortal SQL Injection PoC | `Bangkah_apache-auth-bypass-poc` |
| 40 | Ni8mare: n8n Authentication Bypass & Remote Code Execution | `Bannt08_Research-CVE-2026-21858` |
| 41 | CVE-2026-46490 — samlify SAML AttributeValue XML Injection → Privilege Escalation | `BiiTts_CVE-2026-46490-samlify-SAML-Attribute-Injection` |
| 42 | CVE-2026-49230 — Apache APISIX jwe-decrypt Authentication Bypass | `BiiTts_CVE-2026-49230-APISIX-jwe-decrypt-Auth-Bypass` |
| 43 | CVE-2026-49468 — LiteLLM Unauthenticated Auth Bypass via Host-Header Route Confusion | `BiiTts_CVE-2026-49468-LiteLLM-Auth-Bypass` |
| 44 | CVE-2026-56782 — Gorse Unauthenticated Database Dump / Restore (Auth Bypass) | `BiiTts_CVE-2026-56782-Gorse-Auth-Bypass` |
| 45 | (https://trap.biu.life/search?q=%28request%3D%5EPOST+%2Fapi%2F2.0%2Fmlflow%2Fwebhooks+%26%26+request%3DCREATED%29+%7C%7C+%28request%3D%5EPOST+%2Fapi%2F2.0%2Fmlflow%2Fwebhooks%2F+%2 | `BiuTrap_CVE-2026-64849` |
| 46 | CVE-2026-67276 - MikroTrik SSH Authentication Bypass Exploit | `BlackHatExploitation_exploit-mikrotik-2026` |
| 47 | CVE-2026-48060 - Litestar HTML Injection Through CSRF Token | `Blinky-Keys_CVE-2026-48060` |
| 48 | CVE-2026-73309: Empty OAuth2 credentials bypass | `BomboBombone_CVE-2026-73309` |
| 49 | CVE-2026-73310: OAuth2 redirect URI not bound to authorization code | `BomboBombone_CVE-2026-73310` |
| 50 | CVE-2026-73311: OAuth2 authorization code replay | `BomboBombone_CVE-2026-73311` |
| 51 | CVE-2026-41452 — Krayin CRM Installer Auth Bypass → Admin Takeover | `Boreas37_CVE-2026-41452-PoC` |
| 52 | CVE-2026-43914 — Vaultwarden Email-2FA Brute-Force Protection Bypass | `Boreas37_CVE-2026-43914-PoC` |
| 53 | CVE-2026-58455 — Dockwatch Unauthenticated RCE (auth bypass + command injection) | `Boreas37_CVE-2026-58455-PoC` |
| 54 | A web app to manage your Two-Factor Authentication (2FA) accounts and generate their security codes | `Bubka_2FAuth` |
| 55 | CVE-2026-7671 - Tornet Scooter OTP Brute Force | `CaginKyr_CVE-2026-7671` |
| 56 | Deep Sea Electronics DSE855 - Authentication Bypass | `Cappricio-Securities_CVE-2024-5947` |
| 57 | CVE-2026-41940 - cPanel/WHM Authentication Bypass Exploit v1.0 | `CerberusMrXi_cPanel-WHM-CVE-2026-41940-auth-bypass-exploit` |
| 58 | <img src="https://img.shields.io/badge/CVE--2026--9830-AUTHBYPASS-red?style=for-the-badge" alt="CVE-2026-9830 Badge"/> | `ChPratik_CVE-2026-9830` |
| 59 | GNU Inetutils telnetd Remote Authentication Bypass | `Chocapikk_CVE-2026-24061` |
| 60 | CVE-2026-29000 — pac4j-jwt JWE Authentication Bypass | `ClayOfGilgamesh_CVE-2026-29000` |
| 61 | COMFAST CF-XR11 V2.7.2 has a command injection vulnerability in function sub424CB4. | `CurryRaid_iot_vul` |
| 62 | FortiWeb Unauthenticated RCE via Path Traversal &amp; CGI Auth Bypass | `D3crypT0r_CVE-2025-64446` |
| 63 | CVE-2024-27198 - Authentication Bypass Using an Alternate Path vulnerability in JetBrains TeamCity Server | `Donata64_tc_test01` |
| 64 | CVE-2026-20896: Gitea Docker Image Authentication Bypass PoC | `EQSTLab_CVE-2026-20896` |
| 65 | CVE-2024-27198 – JetBrains TeamCity Authentication Bypass & RCE PoC | `EynaExp_CVE-2024-27198-POC` |
| 66 | CVE-2026-29000 — pac4j-jwt PlainJWT-in-JWE Authentication Bypass | `FranzAlvis_Cve_2026_29000_exploit` |
| 67 | CVE-2026-11116 – SNMPv3 Authentication Bypass via Default EngineID | `George0Papasotiriou_CVE-2026-11116-SNMPv3-Authentication-Bypass-via-De` |
| 68 | CVE-2026-21003 – JWT "none" Algorithm Bypass via kid Header Omission | `George0Papasotiriou_CVE-2026-21003-JWT-none-Algorithm-Bypass-via-kid-H` |
| 69 | CVE-2026-48611 – phpBB OAuth Account Hijacking Exploit | `Diznev_CVE-2026-48611-EXPLOIT` |
| 70 | CVE-2026-11102 – OAuth2 Implicit Grant Fragment Hijacking | `George0Papasotiriou_CVE-2026-11102-OAuth2-Implicit-Grant-Fragment-Hija` |

## Corpus pass 2 (4 teknik)

- **(no-CVE)** (`0xNehru_mitel-micollab-exploit`) — a successful exploit allows unauthenticated access to sensitive system files on 
- **(no-CVE)** (`Donata64_tc_test01`) — cve-2024-27198 - authentication bypass using an alternate path vulnerability in 
- **(no-CVE)** (`0xNehru_mitel-micollab-exploit`) — exploit for mitel micollab authentication bypass and arbitrary file read vulnera
- **(no-CVE)** (`BlackHatExploitation_exploit-mikrotik-20`) — mikrotik routeros ssh public key authentication bypass - no private key required


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **seed-003_web-api-auth-bypass**
  - 对某 Web 应用的 REST API 进行黑盒测试，发现未授权访问和 IDOR 漏洞。
  - 5. 测试 IDOR：用账号 A 的 token 访问账号 B 的资源 → 成功（水平越权）
  - | IDOR 测试不确定是否成功 | 返回的数据没有明显的用户标识 | 对比两个账号的响应，找到 user_id 字段差异 | 15min |
  - curl -H "Authorization: Bearer <token_A>" https://target.example.com/api/v1/users/USER_B_ID
