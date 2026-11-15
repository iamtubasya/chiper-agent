# Cross-Site Scripting

_Execute JS in victim context: reflected, stored, DOM, mXSS, CSP bypass._

Techniques: 61  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | boid CMS 2.1.1 - reflected Cross-Site Scripting (XSS) | `0x4M3R_CVE-2024-53255` |
| 2 | (https://www.cve.org/CVERecord?id=CVE-2025-5721) - Multiple stored cross site scripting vulnerabilities in SourceCodester Student Result Management System v1.0 | `0xEricTee_CVE` |
| 3 | CVE-2026-30048 - Stored Cross-Site Scripting (XSS) in NotChatbot WebChat <= 1.5.0 | `0xN4no_CVE-2026-30048` |
| 4 | Cross-Site Scripting (XSS) vulnerability was discovered in the meal | `0xZeroSec_CVE-2025-55887` |
| 5 | Cross-Site Scripting (XSS) vulnerability was discovered in the Ajax | `0xZeroSec_CVE-2025-55888` |
| 6 | HelpDeskZ-v2.0.2 Stored Cross Site Scripting XSS | `0xashfaq_-HelpDeskZ-v2.0.2---Stored-Cross-Site-Scripting-XSS-` |
| 7 | XSS Exploit for Roundcube Webmail 1.6.7 (CVE-2024-42009) | `0xbassiouny1337_CVE-2024-42009` |
| 8 | Bloomberg Memray’s Stored XSS via Unescaped Command-Line Metadata | `0xmrma_CVE-2026-32722` |
| 9 | A Cross-site Scripting (XSS) vulnerability exists in version v2024-01-05 of the indexmenu plugin when is used and enabled in Dokuwiki (Open Source Wiki Engine). A malicious attacke | `1s1ldur_CVE-2024-42758` |
| 10 | A vulnerability in the web-based management interface of Cisco Finesse could allow an unauthenticated, remote attacker to conduct a stored XSS attack by exploiting an RFI vulnerabi | `3zz4t_CVE-2024-20405` |
| 11 | Simple Python PoC to check Citrix NetScaler ADC / Gateway instances for CVE-2025-12101 (reflected XSS on /cgi/logout) using a crafted SAMLResponse + RelayState payload. | `6h4ack_CVE-2025-12101-checker` |
| 12 | CVE-2025-26202: Cross-Site Scripting (XSS) in DZS Router Web Interface | `A17-ba_CVE-2025-26202-Details` |
| 13 | Todoist App v8484 Stored XSS | `ASencerK_TodoistStoredXSS` |
| 14 | CVE-2024-57175: Stored Cross-Site Scripting (XSS) in PHPGURUKUL Online Birth Certificate System v1.0 | `Ajmal101_CVE-2024-57175` |
| 15 | A Reflected cross-site scripting (XSS) vulnerability in browse.php of Code-projects Jonnys Liquor 1.0 allows remote attackers to inject arbitrary web scripts or HTML via the search | `Akhlak2511_CVE-2024-50969` |
| 16 | This script is designed to exploit vulnerabilities in a Mailcow instance using Cross-Site Scripting (XSS) and Remote Code Execution (RCE). The script aims to: | `Alchemist3dot14_CVE-2024-30270-PoC` |
| 17 | Monica-Stored-XSS-Vulnerability | `Allevon412_CVE-2024-54951` |
| 18 | Open WebUI vulnerable to Stored DOM XSS via prompts when 'Insert Prompt as Rich Text' is enabled resulting in ATO/RCE | `AlphabugX_CVE-2025-64495-POC` |
| 19 | CVE-2025-61319: Stored XSS in ReNgine <= 2.2.0 | `AmalJafarzade_CVE-2025-61319` |
| 20 | CVE-2026-48849 - Stored XSS, HTML Injection & CSS Injection in Roundcube Webmail | `AnandJogawade_CVE-2026-48849-Roundcube-Webmail-Stored-XSS` |
| 21 | Multiple vuylnerabilities including SQL injectiona nd CRoss Site Scripting were found in Hospital management system (HMS) 4.0 | `Ant1sec-ops_HMS4.0-Avdisories` |
| 22 | Hospital-management-Systemv4.0-Stored-XSS | `Ant1sec-ops_Hospital-management-Systemv4.0-Stored-XSS` |
| 23 | CVE-2026-40487 - Postiz <= 2.21.5 - Arbitrary File Upload via MIME-Type Spoofing to Stored XSS to Account Takeover | `Astaruf_CVE-2026-40487` |
| 24 | PoC for CVE-2025-26529 – Moodle XSS to RCE Exploit | `Astroo18_PoC-CVE-2025-26529` |
| 25 | Cross-Site Scripting (XSS) | `BLACK-SCORP10_CVE-2024-51430` |
| 26 | CVE-2024-52794 – Stored Cross-Site Scripting (XSS) in Discourse | `Beesco00_CVE-2024-52794-Discourse-Stored-XSS` |
| 27 | CVE-2024-42009 PoC: Email Capture Listener & XSS Exploit | `Bhanunamikaze_CVE-2024-42009` |
| 28 | CVE-2025-65754 : Stored XSS in Algernon 1.17.4 | `Bnyt7_CVE-2025-65754` |
| 29 | XSS2Shell — WordPress Pre-Auth XSS → RCE Chain PoC | `Boreas37_CVE-2026-64638-PoC-XSS2Shell-` |
| 30 | CVE-2024-31214 - WordPress XSS to RCE | `BouroubaAmine_WordPress-Poc` |
| 31 | CVE-2024-51026 - Vulnerabilidade de Cross Site Scripting (XSS) no NetAdmin IAM | `BrotherOfJhonny_CVE-2024-51026_Overview` |
| 32 | CVE-2024-24136 : Math Game Cross-Site-Scripting | `BurakSevben_2024_Math_Game_XSS` |
| 33 | CVE-2024-24134 : Online Food Menu - Cross-Site-Scripting | `BurakSevben_2024_Online_Food_Menu_XSS` |
| 34 | CVE-2024-24135: Product Inventory with Export to Excel - Cross-Site-Scripting | `BurakSevben_2024_Product_Inventory_with_Export_to_Excel_XSS` |
| 35 | CVE-2024-22890: My e-Diary App - Cross-Site-Scripting | `BurakSevben_CVEs` |
| 36 | CVE-2024-28784 — Stored XSS in IBM QRadar SIEM Rule Wizard | `CainSoulless_CVE-2024-28784` |
| 37 | CVE-2026-9271 — WordPress KeepInMind Stored XSS Assessment | `CerberusMrXi_WordPress-KeepInMind-CVE-2026-9271-Exploit` |
| 38 | Live Helper Chat PHP-Resque XSS Vulnerability - CVE POC | `CodeBrics_lhc-php-resque-exploit` |
| 39 | CVE-2024-46878 - Tiki CMS Reflected Cross-Site Scripting (XSS) Vulnerability | `ColdFusionX_CVE-2024-46878-TikiCMS-XSS` |
| 40 | CVE-2024-46879 - Tiki CMS Reflected Cross-Site Scripting (XSS) Vulnerability | `ColdFusionX_CVE-2024-46879-TikiCMS-XSS` |
| 41 | Stored Cross-site Scripting (XSS) vulnerabilities in the Edit feature of the Software Package List page of IngEstate Server | `Cr0wld3r_CVE-2026-30082` |
| 42 | Stored Cross-Site Scripting (XSS) in Projectworlds Online Attendance System | `CyberShailendra1_Online-Attendance-System-Projectworlds` |
| 43 | ProjectWorlds Online Examination System - Stored XSS in feedback.php | `CyberShailendra1_Online-Examination-System-Project` |
| 44 | A CRLF vulnerability (%0D%0A) exists in TinyWeb Server creating a potential risk for redirection, XSS and other cool tricks depending on how the client interprets the HTTP Response | `DMCERTCE_CRLF_Tiny` |
| 45 | CVE-2024-42009 PoC: Email Capture Listener & XSS Exploit in Roundcube Webmail | `DaniTheHack3r_CVE-2024-42009-PoC` |
| 46 | XSS to Admin account takeover (CVE-2025-14340) | `DeepSecurityResearch_CVE-2025-14340` |
| 47 | CVE-2025-67730 – Stored Cross-Site Scripting (XSS) | `Dharan10_CVE-2025-67730` |
| 48 | Reflected XSS on Login Screen Leading to PHP Code Execution — WordPress Core | `Dungsocool_CVE-2026-64638` |
| 49 | Problem Type: CWE-79 (Cross-Site Scripting) | `DylanDavis1_CVE-2025-63708` |
| 50 | Title The SIL 3.1 is vulnerable to Cross Site Scripting (XSS) in the "hmessage" parameter. | `ELIZEUOPAIN_CVE-2024-24035` |
| 51 | > Vulnerability type : Cross Site Scripting (XSS) <br> | `EQSTLab_CVE-2024-25503` |
| 52 | Authenticated Stored Cross-Site Scripting (XSS) in Genealogy app prior to 4.4.0 allows arbitrary JavaScript execution and privilege escalation from Editor+ role to Administrator. | `Eternalvalhalla_CVE-2025-55287-POC` |
| 53 | phpAbook 9.0i - Cross-Site Scripting (XSS) Vulnerability (CVE-2024-48589) | `Exek1el_CVE-2024-48589` |
| 54 | Stored XSS in Coolify delete flow (CVE-2025-34157) | `Eyodav_CVE-2025-34157` |
| 55 | ElementsKit Elementor Addons <= 3.7.9 — Authenticated (Contributor+) Stored Cross-Site Scripting | `FOLKS-iwd_CVE-2026-2600-POC` |
| 56 | D-Link DIR-845L routers version 1.01KRb03 and below are vulnerable to Cross Site Scripting (XSS) via /htdocs/webinc/js/bscsmsinbox.php. | `FaLLenSKiLL1_CVE-2024-33111` |
| 57 | CVE-2025-29094-Multiple-Stored-Cross-Site-Scripting-XSS | `FraMarcuccio_CVE-2025-29094-Multiple-Stored-Cross-Site-Scripting-XSS` |
| 58 | Vulnerability Disclosure: XSS in Inflectra SpiraTeam 7.2.00 | `GCatt-AS_CVE-2024-48591` |
| 59 | 🛡️ CVE-2024-28623 – XSS Vulnerability in RiteCMS v3.0.0 | `GURJOTEXPERT_ritecms` |
| 60 | CVE-2026-41653: BentoPDF ≤ 2.8.2 - Stored XSS → File Exfiltration | `Astaruf_CVE-2026-41653` |
| 61 | <img width="1448" height="1086" alt="ChatGPT Image 13 set 2026, 160906" src="https://github.com/user-attachments/assets/f3a6fc2c-8e25-4710-b6cd-9e241d3088c2" /> | `FUNFACTOR1_pocket-android-xss-0click-cve` |

## Corpus pass 2 (6 teknik)

- **(no-CVE)** (`Emm448_vulnerability-research`) — an unauthenticated remote attacker can connect to port `23` (telnet) and gain fu
- **(no-CVE)** (`0xashfaq_-HelpDeskZ-v2.0.2---Stored-Cros`) — in helpdeskz v2.0.2, an attacker can exploit an xss vulnerability by injecting m
- **(no-CVE)** (`0xPThree_next.js_cve-2025-29927`) — middleware may be used to restrict content by geographic location. bypass geogra
- **(no-CVE)** (`0xPThree_next.js_cve-2025-29927`) — middleware may be used to set csp headers to prevent xss. bypass csp to xss:
- **(no-CVE)** (`GURJOTEXPERT_ritecms`) — the xss vulnerability allows an attacker to execute arbitrary javascript in the 
- **(no-CVE)** (`ASencerK_TodoistStoredXSS`) — this allows an attacker to upload a png file that executes arbitrary javascript

## Corpus deep pass 2 3 teknik)
- `G33l0_Cve-2026-64638` — a missing plugin file makes wordpress 301 to a canonical url and then
- `G33l0_Cve-2026-64638` — a opens b (same-origin with a on the attacker origin), then navigates
- `G33l0_Cve-2026-64638` — full chain - host the attacker origin and wait for an admin to visit
