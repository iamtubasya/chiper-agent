# LFI / Path Traversal

_Read/include local files, escape upload dirs, wrapper abuse._

Techniques: 47  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | CVE-2025-43919: Directory Traversal in GNU Mailman 2.1.39 (cPanel/WHM Bundle) | `0NYX-MY7H_CVE-2025-43919` |
| 2 | CVE-2025-8088 WinRAR Path Traversal Exploit (PoC) | `0xAbolfazl_CVE-2025-8088-WinRAR-PathTraversal-PoC` |
| 3 | 🛡️ CVE-2025-64446 - FortiWeb Critical Authentication Bypass & Path Traversal | `0xBlackash_CVE-2025-64446` |
| 4 | 🛡️ CVE-2025-68645 - Zimbra Local File Inclusion (LFI) Analysis | `0xBlackash_CVE-2025-68645` |
| 5 | 🛡️ CVE-2026-22557 - Critical Path Traversal Vulnerability in Ubiquiti UniFi Network Application | `0xBlackash_CVE-2026-22557` |
| 6 | 🛡️ CVE-2026-39813 - Fortinet FortiSandbox Path Traversal Vulnerability | `0xBlackash_CVE-2026-39813` |
| 7 | 🔥 CVE-2026-5027 - Langflow Path Traversal | `0xBlackash_CVE-2026-5027` |
| 8 | A path-traversal vulnerability that allows an attacker to read files from the system. | `0xFZin_CVE-2024-36991` |
| 9 | Apport apport-unpack Path Traversal (CVE-2026-77113) | `0xROI_CVE-2026-77113` |
| 10 | 🚨 CVE-2025-2294 - Local File Inclusion (LFI) Vulnerability in Kubio AI Page Builder for WordPress 🧱 | `0xWhoami35_CVE-2025-2294` |
| 11 | CVE-2026-44024 — Fluentd outfile ${tag} Path-Traversal Arbitrary File Write | `0xdak_CVE-2026-44024_exploit` |
| 12 | CVE-2026-52680 — Apache Kyuubi REST Batch Path-Traversal Arbitrary File Write | `0xdak_CVE-2026-52680_exploit` |
| 13 | CVE-2025-24963 - Vitest Browser Mode - Local File Read | `0xdeviner_CVE-2025-24963` |
| 14 | CVE-2025-31125 Exploit - Vite WASM Import Path Traversal 🛡️ | `0xgh057r3c0n_CVE-2025-31125` |
| 15 | Unauthenticated arbitrary local file read in GitLab CE/EE. Affects 18.7–19.1.7, 19.2.0–19.2.5, 19.3.0–19.3.1. Fixed in 19.1.8 / 19.2.6 / 19.3.2 (2026-09-10). CVSS 10.0, reportedly  | `0xlyvio_cve-2026-85706-poc-exploit-gitlab` |
| 16 | A vulnerability in the web-based management interface of Cisco Finesse could allow an unauthenticated, remote attacker to conduct a stored XSS attack by exploiting an RFI vulnerabi | `3zz4t_CVE-2024-20405` |
| 17 | A PoC of the exploit script for the Arbitrary File Read vulnerability of Vite /@fs/ Path Traversal in transformMiddleware (CVE-2025-30208). Detailed analysis can be refer to this [ | `4xura_CVE-2025-30208` |
| 18 | PHPVibevulnerabilityDirectory-Traversal | `751897386_PHPVibe_vulnerability_Directory-Traversal` |
| 19 | Whistle 2.9.98 contains an unpatched path traversal vulnerability because the /cgi-bin/sessions/get-temp-file endpoint fails to adequately sanitize user input in the filename param | `AC8999_CVE-2025-5880` |
| 20 | CVE-2025-63888 ThinkPHP 5.0.24 File Inclusion RCE Exploit | `AN5I_cve-2025-63888-exploit` |
| 21 | CVE-2025-64446 Fortinet FortiWeb Path Traversal RCE Exploit | `AN5I_cve-2025-64446-fortiweb-exploit` |
| 22 | 🔥 CVE-2025-25279 — Mattermost 10.4.1 | `AbokorMAHAMMADMOUSSE_CVE-2025-25279-Mattermost-Path-Traversal` |
| 23 | CVE-2025-8088: WinRAR’s Zero-Day Path Traversal — From Zero to Pwn 🗿 | `AdityaBhatt3010_CVE-2025-8088-WinRAR-Zero-Day-Path-Traversal` |
| 24 | setuptools Path Traversal CVE-2025-47273 | `AliElKhatteb_CVE-2025-47273-POC` |
| 25 | Gecko Theme LFI Exploit (CVE-2025-69080) | `AndrielSec_CVE-2025-69080` |
| 26 | CVE-2026-47627 — NVIDIA Triton Inference Server Path Traversal → DoS (Zip-Slip) | `AneKazek_cve-2026-47627` |
| 27 | Path Traversal PoC (CVE-2024-23334) | `Arc4he_CVE-2024-23334-PoC` |
| 28 | CVE-2024-46987 — Camaleon CMS Arbitrary Path Traversal | `BLUEBERRYP1LL_CVE-2024-46987` |
| 29 | A proof of concept of the path traversal vulnerability in the python AioHTTP library =&lt; 3.9.1 | `BestDevOfc_CVE-2024-23334-PoC` |
| 30 | This repository is a proof of concept (POC) for CVE-2024-23334, demonstrating an attempt to replicate the bug in aiohttp that leads to Local File Inclusion (LFI). | `Betan423_CVE-2024-23334-PoC` |
| 31 | Path traversal in Ollama with rogue registry server | `Bi0x_CVE-2024-37032` |
| 32 | CVE-2026-54917 — SeaweedFS S3 gateway cross-bucket path traversal | `BiiTts_CVE-2026-54917-SeaweedFS-Cross-Bucket-Traversal` |
| 33 | CVE-2026-74239: Windows path traversal in style archive import | `BomboBombone_CVE-2026-74239` |
| 34 | CVE-2026-64824 — Home Assistant Core Backup-Restore Symlink Path Traversal → RCE | `Boreas37_CVE-2026-64824-PoC` |
| 35 | CVE-2026-73034 — DB-GPT v0.8.1 Unauthenticated Path Traversal → Arbitrary File Write | `Boreas37_CVE-2026-73034-PoC` |
| 36 | CVE-2024-42007 - php-spx Path Traversal Exploit | `BubblyCola_CVE_2024_42007` |
| 37 | Quick and easy exploitation of CVE-2024-4956 for LFI based on original PoC from: VeryLazyTech, https://github.com/verylazytech/CVE-2024-4956. | `Buff3st-0v3rfl0w_CVE-2024-4956` |
| 38 | CVE-2026-5203 — CMS Made Simple ≤ 2.2.22 RCE (Path Traversal + Arbitrary File Upload) | `CaginKyr_CVE-2026-5203` |
| 39 | HSC Mailinspector 5.2.17-3 through 5.2.18 - Local File Inclusion | `Cappricio-Securities_CVE-2024-34470` |
| 40 | Path traversal vulnerability in Splunk Enterprise on Windows versions below 9.2.2, 9.1.5, and 9.0.10 that allows reading sensitive files. | `Cappricio-Securities_CVE-2024-36991` |
| 41 | Jenkins 2.441 - Local File Inclusion | `Cheepsss_SPS_POC` |
| 42 | A kind old vulnerability that effect Apache Struts leading to LFI, and remote exection. | `Cythonic1_CVE-2024-53677-POC` |
| 43 | FortiWeb Unauthenticated RCE via Path Traversal &amp; CGI Auth Bypass | `D3crypT0r_CVE-2025-64446` |
| 44 | Grow by Tradedoubler < 2.0.22 - Unauthenticated LFI | `E1-Bot141_CVE-2024-6460` |
| 45 | CVE-2026-42048 Langflow Path Traversal / Arbitrary Directory Deletion PoC | `EQSTLab_CVE-2026-42048` |
| 46 | CVE-2026-75604 - Next.js path traversal → RCE (Windows) · research lab | `FORTBRIDGE-UK_cve-2026-75604` |
| 47 | CVE-2025-32395 vite LFI add windows | `FlowerWitch_my_poc-exp` |

## Corpus pass 2 (4 teknik)

- **(no-CVE)** (`An00bRektn_shirocrack`) — and now for why this exists: turns out hashcat doesn't support the format, and t
- **(no-CVE)** (`DavidCarliez_Windows-AppResolver-LPE-PoC`) — deletion. it demonstrates a missing appresolver capability check in the same
- **(no-CVE)** (`Emirhan-C4Z_exploit-poc1`) — successfully exploiting this chain allows an **unauthenticated attacker** to rea
- **(no-CVE)** (`Emirhan-C4Z_exploit-poc1`) — 🔓 **authentication bypass** via path traversal using `..;/` url parsing bypass.
