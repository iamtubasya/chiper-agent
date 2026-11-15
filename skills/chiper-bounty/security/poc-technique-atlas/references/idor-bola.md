# IDOR / BOLA / Access Control

_Missing/weak object & function-level authorization._

Techniques: 89  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | CVE-2024-0044, identified in the createSessionInternal function of the PackageInstallerService.java file, is a high-severity vulnerability affecting Android versions 12 and 13. Thi | `007CRIPTOGRAFIA_c-CVE-2024-0044` |
| 2 | CVE-2025-27591 – Privilege Escalation via Symlink Abuse in below | `00xCanelo_CVE-2025-27591` |
| 3 | CVE-2025-32462 – sudo -h Privilege Escalation PoC | `0p5cur_CVE-2025-32462-POC` |
| 4 | CVE-2025-32463 - sudo Local Privilege Escalation (PoC) | `0p5cur_CVE-2025-32463-POC` |
| 5 | This exploit chains CVE-2025-6018 and CVE-2025-6019 to achieve local privilege escalation from an unprivileged user to root on vulnerable SUSE/openSUSE systems. CVE-2025-6018 is a  | `0rionCollector_Exploit-Chain-CVE-2025-6018-6019` |
| 6 | below versions < v0.9.0 are vulnerable to a local privilege escalation vulnerability duo to the fact that the program creates a world-writable log file, an a world writable log fil | `0x00Jeff_CVE-2025-27591` |
| 7 | CVE-2026-12400 — FlowForms IDOR: Unauthorized Form Modification | `0x00phantom-hat_CVE-2026-12400-Exploit` |
| 8 | 🚨 CVE-2026-20245 - Cisco Catalyst SD-WAN Manager Privilege Escalation | `0xBlackash_CVE-2026-20245` |
| 9 | 🦊 CVE-2026-5173: GitLab WebSocket Unauthorized Method Execution PoC | `0xBlackash_CVE-2026-5173` |
| 10 | DATAGERRY Broken Access Control | `0xByteHunter_CVE-2024-50967` |
| 11 | CVE-2026-19598 — Pods WordPress Plugin Unauthenticated Privilege Escalation | `0xCyp1337_CVE-2026-19598-` |
| 12 | Beacon Object File implementation of CVE-2024-26229 — Windows CSC driver local privilege escalation via DKOM token theft. | `0xGunrunner_CVE-2024-26229-BOF` |
| 13 | CVE-2024-25830 and CVE-2024-25832 - DataCube3 Improper Access Control and Unrestricted File Upload. | `0xNslabs_CVE-2024-25832-PoC` |
| 14 | 🛡️ CVE-2025-6934 - Unauthenticated Privilege Escalation in Opal Estate Pro | `0xTerror_CVE-2025-6934` |
| 15 | An Insecure Direct Object Reference (IDOR) vulnerability was discovered | `0xZeroSec_CVE-2025-55886` |
| 16 | PoC for CVE-2024-45058 Broken Access Control, allowing any user with view permission in the user configuration section to become an administrator changing their own user type. | `0xbhsu_CVE-2024-45058` |
| 17 | CVE-2025-32463 — sudo "chwoot" chroot Local Privilege Escalation | `0xdak_CVE-2025-32463_exploit` |
| 18 | CVE-2026-64564: SCTPhantom - Local Privilege Escalation (LPE) PoC | `0xdeadroot_SCTPhantom-CVE-2026-64564` |
| 19 | CVE-2026-46331 – pedit COW Local Privilege Escalation Proof-of-Concept (PoC) | `0xdeadroot_pedit-cow-exploit` |
| 20 | SureTriggers <= 1.0.78 - Authorization Bypass Exploit | `0xgh057r3c0n_CVE-2025-3102` |
| 21 | Camaleon CMS (>v2.9.1) - Mass Assignment leads to Privilege Escalation Exploit Tool - PoC | `0xk4rth1_CVE-2025-2304` |
| 22 | CVE-2026-31266 - Craft CMS Missing Authorization | `0xrixet_Craftcms-PoC-CVE-2026-31266` |
| 23 | (r"\blocal privilege escalation\b", "leo thang \\u0111\\u1eb7c quy\\u1ec1n c\\u1ee5c b\\u1ed9"), | `12121211aaaaa_CVE_2024_30085` |
| 24 | CVE-2025-32463 - Sudo Privilege Escalation PoC | `12bijaya_CVE-2025-32463` |
| 25 | print(f"[INFO] Attempting privilege escalation for user: {self.username}") | `1atakan1_CVE-2025-6934` |
| 26 | This repository provides a Go-based exploit tool for CVE-2025-32463, a critical local privilege escalation vulnerability (CVSS 9.3) in sudo versions 1.9.14 to 1.9.17. It allows una | `1xPwn_CVE-2025-32463` |
| 27 | PoC: CVE-2025-2304 - Camaleon CMS Privilege Escalation | `7acini_CVE-2025-2304-CamaleonCMS-PoC` |
| 28 | Bash script for Privilege Escalation via "ndsudo" (Netdata Local Exploit) | `80Ottanta80_CVE-2024-32019-PoC` |
| 29 | CVE-2026-49083 LatePoint Calendar Booking Plugin Privilege Escalation Exploit 🎲🎲🎲 | `87achrafg-stack_CVE-2026-49083` |
| 30 | CVE-2026-51119 - Privilege Escalation in Invixium IXM WEB v2.3.85.25 | `A17-ba_CVE-2026-51119` |
| 31 | Broken Access Control in Inseri Core (WordPress Plugin) | `AC8999_CVE-2026-27344` |
| 32 | SimplCommerce is affected by a Broken Access Control vulnerability in the review system, allowing unauthorized users to post reviews for products they have not purchased. | `AbdullahAlmutawa_CVE-2024-50945` |
| 33 | To create a Metasploit module to exploit the RCE vulnerability in the User Profile Builder WordPress plugin before version 3.11.8, we need to take advantage of the lack of proper a | `Abdurahmon3236_CVE-2024-6366` |
| 34 | Next.js Middleware Authorization Bypass | `Ademking_CVE-2025-29927` |
| 35 | ⚠️ CVE‑2025‑32463 & CVE‑2025‑32462 – Sudo Privilege Escalation Flaws in Linux | `AdityaBhatt3010_Sudo-Privilege-Escalation-Linux-CVE-2025-32463-and-CVE` |
| 36 | Wondershare Filmora v.13.0.51 - Insecure Permissions Privilege Escalation | `Alaatk_CVE-2024-26574` |
| 37 | Macro Expert &lt;= 4.9.4 - Insecure Permissions Privilege Escalation | `Alaatk_CVE-2024-27674` |
| 38 | A vulnerability has been discovered in Axigen Mail Server for Windows, affecting all versions up to 10.5.18, which allows for local privilege escalation. | `Alaatk_CVE-2024-28589` |
| 39 | Camaleon CMS 2.9.0 – Authenticated Privilege Escalation (Role Change) + Optional S3 Config Leak | `Alien0ne_CVE-2025-2304` |
| 40 | Unauthenticated Privilege Escalation | `Alixploit22_CVE-2025-11740` |
| 41 | The Frontend Admin by DynamiApps plugin for WordPress is vulnerable to unauthorized modification of arbitrary WordPress options in all versions up to, and including, 3.28.20. This  | `Altelus1_CVE-2025-13342` |
| 42 | LiteSpeed Cache Privilege Escalation PoC - CVE-2024-28000 | `Alucard0x1_CVE-2024-28000` |
| 43 | CVE-2025-6019: Privilege Escalation Exploit via UDisks2 Filesystem Resize | `And-oss_CVE-2025-6019-exploit` |
| 44 | GouGuOA Mass Assignment Privilege Escalation Vulnerability | `Angoddess_CVE` |
| 45 | eventin &lt;= 4.0.34 - privilege escalation via user email change / account takeover for authenticated contributor+ | `AnotherSec_CVE-2025-4796` |
| 46 | Sensitive Data Exposure via Object Level Access Control in esp-idf | `Ant1sec-ops_CVE-2024-33453` |
| 47 | CVE-2026-4255 Thermalright TR-VISION HOME DLL Side-Loading Privilege Escalation | `Ard33_CVE-2026-4255` |
| 48 | POC for Unauthorized access to documents. CVE-2025-64516 | `ArdNoir_CVE-2025-64516-POC` |
| 49 | CVE-2022-0944: Privilege Escalation Vulnerability in OverlayFS 🛡️ | `Artemisxxx37_cve-2024-0944` |
| 50 | Broken Access Control – Privilege Escalation in News Portal Project in PHP and MySql in PHPGurukul | `Asim-QAZi_BrokenAccessControl-News-Portal-Project-in-PHP-and-MySQL-in-` |
| 51 | CVE-2026-1702 - Improper Access Control – allows admin creation from user account in Sourcecodester Pet Grooming Management Software | `Asim-QAZi_Improper-Access-Control---in-Pet-Grooming-Management-Softwar` |
| 52 | Improper Access Control – allows unauthorized creation of users, bookings, consumers, and cylinders in SourceCodester Gas Agency Management System | `Asim-QAZi_Improper-Access-Control-in-SourceCodester-Gas-Agency-Managem` |
| 53 | Privilege Escalation via ndsudo (Netdata Local Exploit) | `AzureADTrent_CVE-2024-32019-POC` |
| 54 | CVE-2024-48990 — needrestart Local Privilege Escalation | `BLUEBERRYP1LL_CVE-2024-48990` |
| 55 | Linux Kernel nftables Use-After-Free (Local Privilege Escalation) | `Baba01hacker666_CVE-2026-23111` |
| 56 | CVE-2026-46490 — samlify SAML AttributeValue XML Injection → Privilege Escalation | `BiiTts_CVE-2026-46490-samlify-SAML-Attribute-Injection` |
| 57 | CVE-2026-56423 — MISP deleteSelection Broken Access Control | `BiiTts_CVE-2026-56423-MISP-deleteSelection-BrokenAccessControl` |
| 58 | CVE-2026-73310: OAuth2 redirect URI not bound to authorization code | `BomboBombone_CVE-2026-73310` |
| 59 | CVE-2026-73311: OAuth2 authorization code replay | `BomboBombone_CVE-2026-73311` |
| 60 | CVE-2026-73317: Approval job authorization bypass | `BomboBombone_CVE-2026-73317` |
| 61 | CVE-2026-73318: Missing authorization on force-agreement actions | `BomboBombone_CVE-2026-73318` |
| 62 | CVE-2026-44848 — Portainer: Missing Authorization on Docker Plugin Endpoints → Host RCE | `Boreas37_CVE-2026-44848-PoC` |
| 63 | OZ Forensics Exploit - IDOR Vulnerability Exploit | `Brakerciti_OZForensics_exploit` |
| 64 | Universal local privilege escalation Proof-of-Concept exploit for [CVE-2024-1086](https://nvd.nist.gov/vuln/detail/CVE-2024-1086), working on most Linux kernels between v5.14 and v | `CCIEVoice2009_CVE-2024-1086` |
| 65 | Vulnerability Title:LuDaShi Incorrect Access Control | `CDipper_CVE-2025-67246` |
| 66 | CVE-2025-45422: Proximus b-box UPnP Persistence & Access Control Bypass | `Cedrico03_CVE-2025-45422---Bbox` |
| 67 | Penetration Testing Writeup: Next.js RCE & Node.js Inspector Privilege Escalation | `ChrisBarack_cve-2025-55182` |
| 68 | CVE-2025-2304 - Camaleon CMS 2.9.0 - Privilege Escalation Exploit | `CsuriBird_CVE-2025-2304` |
| 69 | Basically below tool allow for universal modification on its log file which lead to privilege escalation as root. | `Cythonic1_CVE-2025-27591` |
| 70 | CVE-2025-66954 – Buffalo LinkStation Username Enumeration via IDOR | `DBmonster19_CVE-2025-66954` |
| 71 | privilege escalation for linux (all versions) | `Darabium_Gombruc` |
| 72 | CVE-2026-58635: Windows Narrator Braille Local Privilege Escalation | `DavidCarliez_CVE-2026-58635-PoC` |
| 73 | Privilege Escalation Case - SOC335-CVE-2024-49138-Exploitation-Detected | `DeividasTerechovas_SOC335-CVE-2024-49138-Exploitation-Detected` |
| 74 | CVE-2025-7771 – ThrottleStop.sys Privilege Escalation | `Demoo1337_ThrottleStop` |
| 75 | Below Privilege Escalation Exploit (CVE-2025-27519) | `Diabl0xE_CVE-2025-27519` |
| 76 | CVE-2026-9055 — Amelia Booking Plugin Unauthenticated Privilege Escalation | `EXEcution-py_CVE-2026-9055` |
| 77 | Authenticated Stored Cross-Site Scripting (XSS) in Genealogy app prior to 4.4.0 allows arbitrary JavaScript execution and privilege escalation from Editor+ role to Administrator. | `Eternalvalhalla_CVE-2025-55287-POC` |
| 78 | This tool is provided strictly for authorized security research, penetration testing, and educational purposes. Only run it against systems you own or have explicit, written permis | `Ethicalgrey_phpBB-CVE-2026-48611` |
| 79 | Arbitrary Command Injection Vulnerability in Netcore Routers and Wireless APs After Authorization | `Exploo0Osion_netcore_command_injection_2` |
| 80 | Arbitrary Command Injection Vulnerability in Netcore Routers Including NBR1005GPE, B6, and NBR200 After Authorization | `Exploo0Osion_netcore_command_injection_3` |
| 81 | Azure Front Door Privilege Escalation – CVE-2026-24306 PoC | `ExploreUnknowed_CVE-2026-24306` |
| 82 | CVE-2026-89013 — Dolibarr hashp=shared Authorization Bypass | `Faceless0x7_CVE-2026-89013` |
| 83 | This repository contains the Proof of Concept (PoC) for CVE-2026-24134, a Broken Object Level Authorization (BOLA) vulnerability in StudioCMS. | `FilipeGaudard_CVE-2026-24134-PoC` |
| 84 | CVE-2026-35045 — Broken Object-Level Authorization in Tandoor Recipes | `FilipeGaudard_CVE-2026-35045-PoC` |
| 85 | CVE-2025-32463 – Privilege Escalation via Sudo chroot | `FreeDurok_CVE-2025-32463-PoC` |
| 86 | Multiple Local Privilege Escalation Vulnerabilities in Little Orbit GFAC Driver (GFACSysx64.sys) | `FzRsLLaSheR_CVE-2026-12166_CVE-2026-12167_CVE-2026-12168` |
| 87 | Privilege Escalation Vulnerabilities in Pegatron TdeIo64 Driver (tdeio64.sys) | `FzRsLLaSheR_CVE-2026-14960-CVE-2026-14961` |
| 88 | CVE-2025-2304 POC - Camaleon CMS Privilege Escalation | `AzureADTrent_CVE-2025-2304_POC` |
| 89 | CVE-2026-24136 - Saleor GraphQL IDOR / Unauthenticated PII Exfiltration | `BlankBire_CVE-2026-24136-Lab` |


## Corpus deep pass 2 1 teknik)
- `12121211aaaaa_CVE_2024_30085` — four extra zero bytes are kept after structsize because cldflt computes
