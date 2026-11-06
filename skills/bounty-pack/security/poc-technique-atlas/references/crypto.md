# Crypto Flaws

_Weak algos, padding oracles, key recovery, IV/nonce misuse._

Techniques: 76  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | CVE-2025-43919: Directory Traversal in GNU Mailman 2.1.39 (cPanel/WHM Bundle) | `0NYX-MY7H_CVE-2025-43919` |
| 2 | CVE-2025-24071: NTLM Hash Leak via RAR/ZIP Extraction and .library-ms File | `0x6rss_CVE-2025-24071_PoC` |
| 3 | CVE-2025-8088 WinRAR Path Traversal Exploit (PoC) | `0xAbolfazl_CVE-2025-8088-WinRAR-PathTraversal-PoC` |
| 4 | 🛡️ CVE-2025-64446 - FortiWeb Critical Authentication Bypass & Path Traversal | `0xBlackash_CVE-2025-64446` |
| 5 | 🛡️ CVE-2026-22557 - Critical Path Traversal Vulnerability in Ubiquiti UniFi Network Application | `0xBlackash_CVE-2026-22557` |
| 6 | 🩸 CVE-2026-31635 – DirtyDecrypt | `0xBlackash_CVE-2026-31635` |
| 7 | 🛡️ CVE-2026-39813 - Fortinet FortiSandbox Path Traversal Vulnerability | `0xBlackash_CVE-2026-39813` |
| 8 | 🔥 CVE-2026-5027 - Langflow Path Traversal | `0xBlackash_CVE-2026-5027` |
| 9 | A path-traversal vulnerability that allows an attacker to read files from the system. | `0xFZin_CVE-2024-36991` |
| 10 | Apport apport-unpack Path Traversal (CVE-2026-77113) | `0xROI_CVE-2026-77113` |
| 11 | CVE-2026-81780 — Hash Form RCE | `0xTerror_CVE-2026-81780-Hash-Form` |
| 12 | Collection of the signed UEFI Secure Boot shim binaries affected by CVE-2026-8863, with the embedded shim version, Authenticode signer and revocation hashes of each image. | `0xbekoo_CVE-2026-8863` |
| 13 | deco-cx apps Parameter analyticsScript.ts AnalyticsScript server-side request forgery | `0xcucumbersalad_CVE-2025-13796-PoC` |
| 14 | 2. add x-middleware-subrequest: src/middleware:src/middleware:src/middleware:src/middleware:src/middleware as header | `0xcucumbersalad_cve-2025-29927` |
| 15 | CVE-2026-44024 — Fluentd outfile ${tag} Path-Traversal Arbitrary File Write | `0xdak_CVE-2026-44024_exploit` |
| 16 | CVE-2026-52680 — Apache Kyuubi REST Batch Path-Traversal Arbitrary File Write | `0xdak_CVE-2026-52680_exploit` |
| 17 | CVE-2025-31125 Exploit - Vite WASM Import Path Traversal 🛡️ | `0xgh057r3c0n_CVE-2025-31125` |
| 18 | CVE-2025-10951 - checkmlloggertraversal.py | `1amUnvalid_CVE-2025-10951` |
| 19 | CVE-2025-8110 — Gogs <= 0.13.3 Arbitrary File Write via Symlink Traversal | `3jee_CVE-2025-8110` |
| 20 | CVE-2026-34486 — Apache Tomcat EncryptInterceptor RCE | `404-src_CVE-2026-34486` |
| 21 | A PoC of the exploit script for the Arbitrary File Read vulnerability of Vite /@fs/ Path Traversal in transformMiddleware (CVE-2025-30208). Detailed analysis can be refer to this [ | `4xura_CVE-2025-30208` |
| 22 | PHPVibevulnerabilityDirectory-Traversal | `751897386_PHPVibe_vulnerability_Directory-Traversal` |
| 23 | Whistle 2.9.98 contains an unpatched path traversal vulnerability because the /cgi-bin/sessions/get-temp-file endpoint fails to adequately sanitize user input in the filename param | `AC8999_CVE-2025-5880` |
| 24 | CVE-2025-64446 Fortinet FortiWeb Path Traversal RCE Exploit | `AN5I_cve-2025-64446-fortiweb-exploit` |
| 25 | CVE-2025-24071 - Windows File Explorer NTLM Hash Leak | `Abdelrahman0Sayed_CVE-2025-24071` |
| 26 | 🔥 CVE-2025-25279 — Mattermost 10.4.1 | `AbokorMAHAMMADMOUSSE_CVE-2025-25279-Mattermost-Path-Traversal` |
| 27 | How We Stopped a Crypto-mining Attack in Kubernetes Caused by a Next.js RCE | `Achanandhi-M_Kubecon-India-2026-Demo` |
| 28 | CVE-2025-8088: WinRAR’s Zero-Day Path Traversal — From Zero to Pwn 🗿 | `AdityaBhatt3010_CVE-2025-8088-WinRAR-Zero-Day-Path-Traversal` |
| 29 | CVE-2026-34486 Apache Tomcat EncryptInterceptor 绕过漏洞复现 | `AirSkye_CVE-2026-34486-poc` |
| 30 | 🔥 CVE-2025-6389 — Critical WordPress Zero-Day (RCE) | `AivarSaar_blackash-cve-2025-6389` |
| 31 | CVE-2024-29050 is a security vulnerability in Windows' cryptographic services, particularly in how certificates are processed during cryptographic operations. The issue stems from  | `Akrachli_CVE-2024-29050` |
| 32 | setuptools Path Traversal CVE-2025-47273 | `AliElKhatteb_CVE-2025-47273-POC` |
| 33 | Slides and tooling from the DEF CON 34 talk "Thin Client? Thin Crypto: Bypassing | `AmberWolfCyber_DEFCON34-ThinClientThinCrypto` |
| 34 | > Simple hash cracker for [Apache Shiro](https://github.com/apache/shiro) hashes written in Golang. Useful for exploiting [CVE-2024-4956](https://github.com/erickfernandox/CVE-2024 | `An00bRektn_shirocrack` |
| 35 | CVE-2026-47627 — NVIDIA Triton Inference Server Path Traversal → DoS (Zip-Slip) | `AneKazek_cve-2026-47627` |
| 36 | Path Traversal PoC (CVE-2024-23334) | `Arc4he_CVE-2024-23334-PoC` |
| 37 | The project was created to demonstrate the use of various tools for capturing NTLM hashes from users on a network and for executing phishing attacks using email. This showcases how | `ArtemCyberLab_Project-NTLM-Hash-Capture-and-Phishing-Email-Exploitatio` |
| 38 | CVE-2024-46987 — Camaleon CMS Arbitrary Path Traversal | `BLUEBERRYP1LL_CVE-2024-46987` |
| 39 | CVE-2025-24071 — Windows File Explorer Spoofing / NTLM Hash Disclosure via .library-ms | `BardLaudian_CVE-2025-24071` |
| 40 | A proof of concept of the path traversal vulnerability in the python AioHTTP library =&lt; 3.9.1 | `BestDevOfc_CVE-2024-23334-PoC` |
| 41 | Path traversal in Ollama with rogue registry server | `Bi0x_CVE-2024-37032` |
| 42 | CVE-2026-49230 — Apache APISIX jwe-decrypt Authentication Bypass | `BiiTts_CVE-2026-49230-APISIX-jwe-decrypt-Auth-Bypass` |
| 43 | CVE-2026-54917 — SeaweedFS S3 gateway cross-bucket path traversal | `BiiTts_CVE-2026-54917-SeaweedFS-Cross-Bucket-Traversal` |
| 44 | CVE-2026-74239: Windows path traversal in style archive import | `BomboBombone_CVE-2026-74239` |
| 45 | CVE-2026-64824 — Home Assistant Core Backup-Restore Symlink Path Traversal → RCE | `Boreas37_CVE-2026-64824-PoC` |
| 46 | CVE-2026-73034 — DB-GPT v0.8.1 Unauthenticated Path Traversal → Arbitrary File Write | `Boreas37_CVE-2026-73034-PoC` |
| 47 | unifi os 5.0.6 pass traversal to admin &amp; code exec scripts | `BoredHackerBlog_unifi_5.0.6_exploitation` |
| 48 | CVE-2024-42007 - php-spx Path Traversal Exploit | `BubblyCola_CVE_2024_42007` |
| 49 | DJI Enhanced WiFi Weak Cryptography (CVE-2025-10250) | `ByteMe1001_DJI-Enhanced-WiFi-Weak-Cryptography` |
| 50 | Universal local privilege escalation Proof-of-Concept exploit for [CVE-2024-1086](https://nvd.nist.gov/vuln/detail/CVE-2024-1086), working on most Linux kernels between v5.14 and v | `CCIEVoice2009_CVE-2024-1086` |
| 51 | CVE-2026-5203 — CMS Made Simple ≤ 2.2.22 RCE (Path Traversal + Arbitrary File Upload) | `CaginKyr_CVE-2026-5203` |
| 52 | Path traversal vulnerability in Splunk Enterprise on Windows versions below 9.2.2, 9.1.5, and 9.0.10 that allows reading sensitive files. | `Cappricio-Securities_CVE-2024-36991` |
| 53 | 🚀 HashForm Exploit Script | `Chocapikk_CVE-2024-5084` |
| 54 | CVE-2026-41651 - Pack2TheRoot Vulnerability | `CipherCloak_CVE-2026-41651` |
| 55 | CVE-2026-31280-Insecure-Bluetooth-RFCOMM-Leading-to-Device-Crash-in-Parani-M10-Intercom | `CipherX1802_CVE-2026-31280-Insecure-Bluetooth-RFCOMM-Leading-to-Device` |
| 56 | Pre-authentication remote code execution for WordPress 6.9.0–6.9.4 and 7.0.0–7.0.1. | `Crypto-Cat_wp2shell` |
| 57 | Estudio técnico de la vulnerabilidad CVE-2025-5548 | `CryptoMachio_CVE-2025-5548` |
| 58 | FortiOS and FortiProxy Password Hashing Vulnerability to RCE (CVE-2024-21754) | `CyberSecuritist_CVE-2024-21754-Forti-RCE` |
| 59 | EncryptInterceptor fail-open bypass in Apache Tomcat Tribes clustering leading to unauthenticated RCE via Java deserialization. | `CypherHippie_CVE-2026-34486---unauthenticated-RCE-via-Java-deserializa` |
| 60 | Basically below tool allow for universal modification on its log file which lead to privilege escalation as root. | `Cythonic1_CVE-2025-27591` |
| 61 | sloof — iOS 26.1 Kernel Exploit | `D3CRYPTORDE_GuentherJB` |
| 62 | FortiWeb Unauthenticated RCE via Path Traversal &amp; CGI Auth Bypass | `D3crypT0r_CVE-2025-64446` |
| 63 | CVE-2024-29868: Use of Cryptographically Weak PRNG in Recovery Token Generation | `DEVisions_CVE-2024-29868` |
| 64 | CVE-2025-24071-POC-NTLMHashDisclosure | `DeshanFer94_CVE-2025-24071-POC-NTLMHashDisclosure-` |
| 65 | CVE-2026-26012 — Vaultwarden Cipher Enumeration PoC | `Dulieno_CVE-2026-26012` |
| 66 | CVE-2026-42048 Langflow Path Traversal / Arbitrary Directory Deletion PoC | `EQSTLab_CVE-2026-42048` |
| 67 | CVE-2025-24071: NTLM Hash Leak via .library-ms File (Metasploit Module) | `FOLKS-iwd_CVE-2025-24071-msfvenom` |
| 68 | CVE-2026-75604 - Next.js path traversal → RCE (Windows) · research lab | `FORTBRIDGE-UK_cve-2026-75604` |
| 69 | CVE-2026-89013 — Dolibarr hashp=shared Authorization Bypass | `Faceless0x7_CVE-2026-89013` |
| 70 | CVE-2025-24054 and CVE-2025-24071 - NTLM Hash Leak via .library-ms Exploit | `Fomovet_cve-2025-24071` |
| 71 | CVE-CVE-2024-0582 latest kernel bypass root updated POC just run python file with root | `Forsaken0129_UltimateLinuxPrivilage` |
| 72 | Autonomous AI agent with its own cryptographic identity. It hunts CVEs, | `Freire007-byte_sentric-core` |
| 73 | Dirty Frag: Universal Linux LPE | `FrosterDL_CVE-2026-43284` |
| 74 | This is a POC and a hashcat module for FortiOS CVE 2024-21754 we found. | `GDATAAdvancedAnalytics_fortigategate` |
| 75 | CVE-2026-11119 – Padding Oracle Attack on CBC Mode Encryption | `George0Papasotiriou_CVE-2026-11119-Padding-Oracle-Attack-on-CBC-Mode-E` |
| 76 | Sliver is an open source cross-platform adversary emulation/red team framework, it can be used by organizations of all sizes to perform security testing. Sliver's implants support  | `BishopFox_sliver` |
