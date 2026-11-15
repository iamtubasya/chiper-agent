# SQL Injection

_Extract/modify DB data via query injection; incl. blind, UNION, second-order._

Techniques: 84  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | CVE-2024-51060: SQL Injection in Projectworlds Online Admission System v1 | `0x1c1ph3r_CVEs` |
| 2 | <h1>And exploited SQL injection vulnerabilities in Mura/Masa CMS. | `0x3f3c_CVE-2024-32640-SQLI-MuraCMS` |
| 3 | 🚨 CVE-2026-21643 "FortiGhost" : Pre-Auth SQLi RCE in FortiClientEMS | `0xBlackash_CVE-2026-21643` |
| 4 | 🚨 CVE-2026-27876 - Grafana Critical RCE via SQL Expressions | `0xBlackash_CVE-2026-27876` |
| 5 | 🚨 CVE-2026-41462 - ProjeQtor Unauthenticated SQL Injection | `0xBlackash_CVE-2026-41462` |
| 6 | ✦ CVE-2026-42208 - Critical SQL Injection in LiteLLM | `0xBlackash_CVE-2026-42208` |
| 7 | 🔴 CVE-2026-72898 - Unauthenticated SQL Injection | `0xBlackash_CVE-2026-72898` |
| 8 | 🚨 CVE-2026-9082 : SQL Injection Vulnerability in Drupal Core | `0xBlackash_CVE-2026-9082` |
| 9 | CVE-2025-64459: Django ORM SQL Injection PoC | `0xCyberstan_CVE-2025-64459-Poc` |
| 10 | ZoneMinder Authenticated Time Based SQLi POC - CVE-2024-51482 | `0xDaeras_CVE-2024-51482-POC` |
| 11 | FreePBX 16 — Unauthenticated SQLi to RCE | `0xEhab_FreePBX-CVE-2025-57819-RCE` |
| 12 | WordPress REST batch route-confusion blind SQL injection — automated exploit chain. | `0xWhoknows_wp2shell` |
| 13 | SQL Injection vulnerability in Alpes Recherche et Developpement ARD GEC | `0xZeroSec_CVE-2025-55885` |
| 14 | CVE-2026-69083 — SiYuan Unauthenticated SQL Injection | `0xdak_CVE-2026-69083_exploit` |
| 15 | CVE-2024-2876 - SQL Injection Vulnerability in Email Subscribers by Icegram Express | `0xlf_CVE-2024-2876` |
| 16 | CVE-2025-28009 - SQL Injection in Dietiqa App v1.0.20 | `0xs4h4_CVE-2025-28009` |
| 17 | CVE-2024-34327 SQL Injection Vulnerability Checker | `0xsu3ks_CVE-2024-34327` |
| 18 | CVE-2025-45346 – Bacula-Web Time-Based SQL Injection (PostgreSQL Version Extraction) | `0xsu3ks_CVE-2025-45346` |
| 19 | Unauthenticated SQL injection in Drupal Core on PostgreSQL via POST /user/login, escalated to remote code execution through PostgreSQL sessionpreloadlibraries. | `11romain_CVE-2026-9082` |
| 20 | CVE-2024-9264-RCE-Exploit in Grafana via SQL Expressions | `14mb1v45h_cyberspace061` |
| 21 | CVE-2024-8465 – SQL Injection Proof of Concept | `19melek19_TheMisfits-CVE-2024-8465-SQLi` |
| 22 | patient-record-management-system-in-php has sql injection in birthingform.php | `2364490073_cve1` |
| 23 | Metabase SQL Injection RCE | `34zY_CVE-2026-72898` |
| 24 | WordPress Batch API Desynchronization SQL Injection Exploit | `4minx_CVE-2026-63030` |
| 25 | CVE-2026-72898 PoC : Metabase Unauthenticated SQL Injection | `4minx_CVE-2026-72898` |
| 26 | Some simple scripts to help exploit SQLi using both bash and Node.js based on CVE-2024-7456 (https://nvd.nist.gov/vuln/detail/CVE-2024-7456). | `77Philly_CVE-2024-7456scripts` |
| 27 | <h1 align="center">CVE-2026-9082 - Drupal Core PostgreSQL SQL Injection PoC</h1> | `7h30th3r0n3_CVE-2026-9082-Drupal-PoC` |
| 28 | Phpgurukul RTBS Project PHP V2.1 /aboutus.php SQL injection | `81a2in9_cve` |
| 29 | 🛡️ Zabbix 7.0.0 SQL Injection Exploit Script | `874anthony_CVE-2024-42327_Zabbix_SQLi` |
| 30 | A low-privileged authenticated user can exploit this vulnerability by sending a crafted HTTP POST request with a malicious orderby parameter (e.g., orderby=IF(1=1,SLEEP(5),1)). Thi | `Abdullah4eb_CVE-2025-50383` |
| 31 | CVE-2026-60137 — WordPress Core SQL Injection PoC | `AbdullahMaqbool22_CVE-2026-60137-WordPress-Core-SQL-Injection-PoC` |
| 32 | wpsqli - WordPress SQLi Extractor (CVE-2026-60137) | `AdarshThakur14777-cyber_CVE-2026-60137` |
| 33 | smm-panel-sqli(CVE-2025-55575) | `Aether-0_CVE-2025-55575` |
| 34 | A SQL injection vulnerability in orderview1.php of Itsourcecode Online Furniture Shopping Project 1.0 allows remote attackers to execute arbitrary SQL commands via the id parameter | `Akhlak2511_CVE-2024-50970` |
| 35 | A SQL injection vulnerability in print.php of Itsourcecode Construction Management System 1.0 allows remote attackers to execute arbitrary SQL commands via the mapid parameter. | `Akhlak2511_CVE-2024-50971` |
| 36 | A SQL injection vulnerability in printtool.php of Itsourcecode Construction Management System 1.0 allows remote attackers to execute arbitrary SQL commands via the borrowid paramet | `Akhlak2511_CVE-2024-50972` |
| 37 | Multiple vuylnerabilities including SQL injectiona nd CRoss Site Scripting were found in Hospital management system (HMS) 4.0 | `Ant1sec-ops_HMS4.0-Avdisories` |
| 38 | Wordpress SQLI-2-RCE Exploit | `Ap0dexMe0_CVE-2024-27956` |
| 39 | MachForm up to version 19 is affected by an authenticated Blind SQL injection in the user account settings page. | `Atreb92_cve-2024-37765` |
| 40 | LearnPress – WordPress LMS Plugin &lt;= 4.2.7 - Unauthenticated SQL Injection via 'conlyfields' | `Avento_CVE-2024-8522` |
| 41 | CVE-2026-1337 - Apache WebPortal SQL Injection PoC | `Bangkah_apache-auth-bypass-poc` |
| 42 | The WP Directory Kit plugin for WordPress is vulnerable to SQL Injection via the 'attributevalue' and 'attributeid' parameters in all versions up to, and including, 1.3.0 due to in | `BassamAssiri_CVE-2024-3217-POC` |
| 43 | open-video-cms has sql injection vulnerability in video/list | `Bemcliu_cve` |
| 44 | CVE-2026-52887 — NocoBase SQL Injection → PostgreSQL-superuser RCE | `BiiTts_CVE-2026-52887-NocoBase-SQLi-RCE` |
| 45 | CVE-2026-54350 — Budibase Unauthenticated NoSQL Operator Injection | `BiiTts_CVE-2026-54350-Budibase-NoSQL-Injection` |
| 46 | cve patient-record-management-system-in-php has sql injection in /dentalform.php | `BinBall_cve` |
| 47 | CVE-2026-69084 / CVE-2026-69085 — SiYuan Arbitrary SQL Execution & SQLi | `Boreas37_CVE-2026-69084-PoC` |
| 48 | CVE-2024-51482 - ZoneMinder Blind SQL Injection | `BridgerAlderson_CVE-2024-51482` |
| 49 | OpenSTAManager <= 2.9.8 — Error-Based SQL Injection in Scadenzario Bulk Operations Module | `BridgerAlderson_CVE-2026-24418` |
| 50 | Zabbix-CVE-2024-42327 RCE PoC | `BridgerAlderson_Zabbix-CVE-2024-42327-SQL-Injection-RCE` |
| 51 | CVE-2024-24140: Daily Habit Tracker App SQL Injection | `BurakSevben_Daily_Habit_Tracker_App_SQL_Injection` |
| 52 | CVE-2024-24142: School-Task-Manager-System-SQL-Injection-2 | `BurakSevben_School-Task-Manager-SQL-Injection-2` |
| 53 | CVE-2024-24141: School-Task-Manager-System-SQLInjection-1 | `BurakSevben_School-Task-Manager-System-SQLi-1` |
| 54 | CVE-2024-9796 WP-Advanced-Search < 3.3.9.2 - Unauthenticated SQL Injection | `BwithE_CVE-2024-9796` |
| 55 | Python script that exploits CVE-2024-27956, a vulnerability in Wordpress that allows SQL Injection leading to Remote Code Execution. | `CERTologists_EXPLOITING-CVE-2024-27956` |
| 56 | During the security assessment of "STUDENT WEB PORTAL", I detected a critical SQL injection vulnerability in the "signup.php" file. This vulnerability is attributed to the insuffic | `CH0ico_CVE_choco_2` |
| 57 | CVE-2026-44680 - MikroORM SQL Injection Exploit Framework | `CerberusMrXi_CVE-2026-44680-MikroORM-SQL-Injection-Exploit-Framework` |
| 58 | 🛡️ CVE-2026-57588 - Nessus SQL Injection Exploitation Framework | `CerberusMrXi_CVE-2026-57588-Nessus-XML-Import-SQL-Injection-PoC` |
| 59 | CVE-2026-23723 PoC - WeGIA Authenticated SQL Injection Exploit Helper | `Ch35h1r3c47_CVE-2026-23723-POC` |
| 60 | > WordPress REST Batch Route-Confusion SQL Injection (CVE-2026-63030) Proof of Concept | `Ch4120N_CVE-2026-63030` |
| 61 | ⚡️ Exploit for CVE-2024-8504 & CVE-2024-8503: SQLi and RCE ⚡️ | `Chocapikk_CVE-2024-8504` |
| 62 | openDCIM - SQLi to RCE via Config Poisoning | `Chocapikk_opendcim-exploit` |
| 63 | CVE-2026-25746 - SQL Injection Vulnerability in OpenEMR <8.0.0 | `ChrisSub08_CVE-2026-25746_SqlInjectionVulnerabilityOpenEMR7.0.4` |
| 64 | CVE-2026-32127 - SQL Injection Vulnerability in OpenEMR 8.0.0 | `ChrisSub08_CVE-2026-32127_SqlInjectionVulnerabilityOpenEMR8.0.0` |
| 65 | CVE-2026-33917 - SQL Injection Vulnerability in OpenEMR < 8.0.0.3 | `ChrisSub08_CVE-2026-33917_SqlInjectionVulnerabilityOpenEMR8.0.0` |
| 66 | 🚨 CVE-2024-9264 - Grafana SQL injection leading to Remote Code Execution (RCE) and file Read | `Cythonic1_CVE-2024-9264` |
| 67 | CVE-2024-51428 - ZoneMinder Blind SQL Injection PoC | `D1se0_CVE-2024-51428-PoC` |
| 68 | CVE-2026-35194 — Apache Flink SQL Code Injection | `DexSemon_CVE-2026-25194` |
| 69 | CVE-2024-1698 – NotificationX WordPress Plugin SQL Injection (Time‑Based Blind) | `Dhananjayasj_CVE-2024-1698-NotificationX-WordPress-Plugin-SQL-Injectio` |
| 70 | WordPress CVE 2024-1071 SQL Exploit | `Dogu589_WordPress-Exploit-CVE-2024-1071` |
| 71 | CVE-2026-0603 Hibernate ORM Injection / Second-Order SQL Injection | `EQSTLab_CVE-2026-0603` |
| 72 | ★ CVE-2026-26980 TryGhost Ghost CMS Content API SQL Injection PoC ★ | `EQSTLab_CVE-2026-26980` |
| 73 | CVE-2026-30951 Sequelize JSON Cast SQL Injection | `EQSTLab_CVE-2026-30951` |
| 74 | CVE-2026-43220 MikroORM SQL Injection | `EQSTLab_CVE-2026-34220` |
| 75 | CVE-2026-72898 Metabase password-reset unauthenticated SQL injection | `EQSTLab_CVE-2026-72898` |
| 76 | CVE-2026-79483-FastGPT-NoSQL-Injection | `ExploreIO_CVE-2026-79483-FastGPT-NoSQL-Injection` |
| 77 | CVE-2026-59550 - AWP Classifieds ≤ 4.4.7 unauthenticated SQL injection | `FLX-0x00_CVE-2026-59550` |
| 78 | Happy Addons for Elementor &lt;= 3.20.4 — Authenticated (Contributor+) Second-Order SQL Injection | `FOLKS-iwd_CVE-2025-68999-POC` |
| 79 | CVE-2026-89012 — Dolibarr SQL Filter Denylist Bypass | `Faceless0x7_CVE-2026-89012` |
| 80 | 🚨POC RELEASED🚨PoC for SQL Injection leads to RCE in Wordpress released (CVE-2024-27956). WordPress Admin Account Creation and Reverse Shell (cve-2024-27956) | `FoxyProxys_CVE-2024-27956` |
| 81 | BIG-IP Next Central Manager API UNAUTHENTICATED SQL INJECTION | `GRTMALDET_Big-IP-Next-CVE-2024-26026` |
| 82 | A time-based blind SQL injection exploit for the OpenSIPS Control Panel. | `Gabriel-Lacorte_CVE-2026-36670` |
| 83 | CVE-2026-21004 – SQLite FTS3 Match Infoleak via Query Crafting | `George0Papasotiriou_CVE-2026-21004-SQLite-FTS3-Match-Infoleak-via-Quer` |
| 84 | CVE-2026-72898 — Metabase Unauthenticated SQL Injection PoC | `BlackHatExploitation_metabase-sql-poc` |

## Corpus pass 2 (1 teknik)

- **(no-CVE)** (`Bangkah_apache-auth-bypass-poc`) — proof of concept (poc) script to demonstrate an authentication bypass vulnerabil

## Corpus deep pass ( 1 teknik)
- `12121211aaaaa_CVE_2024_30085` — four extra zero bytes are kept after structsize because cldflt computes


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **2026-08-01_pentest-encryption-oracle-public-template-sql-admin-takeover**
  - 2. 从所有 `Encrypt/Decrypt/Sign/Verify` 入口建立生产者—消费者矩阵，记录权限、用途绑定、调用者可控字段和密文格式。
  - 10. 使用官方管理员仓储的口令验证方法做业务层正负对照：指定新口令成功、旧口令失败；到此立即停止进一步 SQL/RCE 扩展。
  - consumer: unauthenticated ciphertext -> decrypt -> full parser
  - 在 API Security 与 SRC Hunter 中增加固定检查：“通用 Encrypt/Sign/JWT 生成器是否能为另一个公开 Verify/Decrypt/Parse 消费者生成 capability”。
