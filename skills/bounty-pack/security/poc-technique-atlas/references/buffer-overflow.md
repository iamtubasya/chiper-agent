# Memory Corruption

_Stack/heap overflow, UAF — binary targets / native parsers._

Techniques: 36  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | CVE-2026-9256 Nginx heap buffer overflow POC | `06-ux_CVE-2026-9256-POC` |
| 2 | Stack-Based Buffer Overflow in Tenda HG7 / HG9 / HG10 Routers | `0xBlackash_CVE-2026-11499` |
| 3 | 🐧 CVE-2026-23111 - Linux Kernel nftables Use-After-Free Vulnerability | `0xBlackash_CVE-2026-23111` |
| 4 | 🛡️ CVE-2026-31402 – NFSv4 LOCK Replay Cache Heap Overflow | `0xBlackash_CVE-2026-31402` |
| 5 | 🛡️ CVE-2026-42530 - NGINX HTTP/3 (QUIC) Use-After-Free Vulnerability | `0xBlackash_CVE-2026-42530` |
| 6 | 🚨 CVE-2026-45447 - Critical OpenSSL Use-After-Free Vulnerability | `0xBlackash_CVE-2026-45447` |
| 7 | 🔐 CVE-2026-63072 — OpenSSL CMS Heap Buffer Overflow | `0xBlackash_CVE-2026-63072` |
| 8 | Pre-auth heap buffer overflow and heap information leak in nginx, caused by | `0xCyberstan_CVE-2026-42533-POC` |
| 9 | CVE-2026-46215: DRM GEM changehandle Use-After-Free (unprivileged LPE) | `0xCyberstan_CVE-2026-46215-POC` |
| 10 | CVE-2025-4517 / CVE-2025-4330 — Python tarfile Data Filter Bypass via PATHMAX Overflow | `0xDTC_CVE-2025-4517-tarfile-PATH_MAX-bypass` |
| 11 | Title: D-Link DCS-935L HNAP Service SetDeviceSettings Stack Buffer Overflow Vulnerability (RCE) | `0xcc12138_DCS-935L-HNAP-Service-CVE` |
| 12 | CVE-2026-20637: AppleSEPKeyStore Use-After-Free | `0xjohnnydev_CVE-2026-20637-AppleSEPKeyStore-UAF` |
| 13 | CVE-2026-20687: AppleJPEGDriver startDecoder() Timeout UAF (deferred panic) | `0xjohnnydev_CVE-2026-20687-AppleJPEGDriver-UAF` |
| 14 | nginx ngxhttprewritemodule Heap Buffer Overflow | `3nou9h_CVE-2026-9256-Poc` |
| 15 | CVE-2026-14266 Poc: 7-Zip XZ Heap Buffer Overflow PoC Generator | `4minx_CVE-2026-14266` |
| 16 | H3C routers have been found to have a buffer overflow vulnerability. Magic B0 model have a serious buffer overflow vulnerability. This vulnerability can cause a buffer overflow by  | `666324_H3C-Magic-B0-vuln` |
| 17 | A critical buffer overflow vulnerability has been identified in D-Link's DI-7001MINI-8G device. This flaw exists within the handling of HTTP POST requests to the httpddebug.asp end | `666324_dlink-DI-7001MINI-8G-vuln` |
| 18 | SimplCommerce is affected by an integer overflow vulnerability in the cart logic, allowing manipulation of product quantities and total prices via crafted quantity parameters. | `AbdullahAlmutawa_CVE-2024-50944` |
| 19 | CVE-2024-29050 is a security vulnerability in Windows' cryptographic services, particularly in how certificates are processed during cryptographic operations. The issue stems from  | `Akrachli_CVE-2024-29050` |
| 20 | CVE-2026-64788 — IOGPUFamily Use-After-Free | `AmorCool_iOS26.6-CVE-2026-64788` |
| 21 | SceNKFastMalloc (Reuse/uaf?) | `BUSHIGAN_PS4-POC` |
| 22 | Linux Kernel nftables Use-After-Free (Local Privilege Escalation) | `Baba01hacker666_CVE-2026-23111` |
| 23 | PoC for an integer overflow vulnerability in ImageIO patched in iOS/macOS 26.5 (CVE-2026-28990) | `Billy-Ellis_exr-imageio-poc` |
| 24 | CVE-2026-73321: PHP worker stack overflow through nested BBCode | `BomboBombone_CVE-2026-73321` |
| 25 | Android app that detects the kernel vulnerability CVE-2026-43499 — a use-after-free in rtmutex triggered via futexrequeue. | `CakesTwix_Android-CVE-2026-43499` |
| 26 | CVE-2026-2441 — Chrome CSSFontFeatureValuesMap Use-After-Free | `D3b0j33t_CVE-2026-2441-PoC` |
| 27 | Proof-of-concept for a heap overflow and memory leak in TinyWeb 1.94 - All versions most likely affected. | `DMCERTCE_PoC_Tiny_Overflow` |
| 28 | . CVE-2026-52924: SCTP Use-After-Free in Stale Cookie Handling | `Eliot-code_CVE-2026-52924` |
| 29 | Vulnerability description: LBT-T300-T310 v2.2.3.6 of Shenzhen Rio Tinto Technology Co., Ltd. was found to have a buffer overflow at/appy.cgi through multiple parameters. | `FLY200503_IoT-vul` |
| 30 | CVE-2026-42533 — NGINX Pre-Auth Heap Overflow: Analysis & RCE | `FranklinF25_cve-2026-42533` |
| 31 | CVE-2026-42945 — NGINX Rewrite Heap Overrun: Analysis, DoS & Credited RCE Port | `FranklinF25_cve-2026-42945` |
| 32 | A stack-based buffer overflow vulnerability exists in the depackpha() function of libxmp, a library for module music playback. The vulnerability is triggered when parsing malformed | `GCatt-AS_CVE-2025-47256` |
| 33 | VisiCut V2.1 Stack Overflow due to Insecure Deserialization | `Gelcon_PoC-of-VisiCut2_1-Stack-Overflow-Vul` |
| 34 | CVE-2026-11105 – Stack Buffer Overflow in Custom Base64 Decoder | `George0Papasotiriou_CVE-2026-11105-Stack-Buffer-Overflow-in-Custom-Bas` |
| 35 | CVE-2026-11108 – Integer Overflow in Memory Allocator (kmalloc Sim) | `George0Papasotiriou_CVE-2026-11108-Integer-Overflow-in-Memory-Allocato` |
| 36 | CVE-2025-38676 — Linux Kernel ≤ 6.17-rc2 (AMD IOMMU) stack buffer overflow | `14mb1v45h_CVE-2025-38676` |


## Corpus deep pass (correction 2026-10-17 — system-level PoC, 1 teknik)

- `Geal_trailer` — minimal Rust PoC for a type/buffer placed in contiguous memory (heap-layout primitive). Technique only; no CVE, no impact on its own.
