# Insecure Deserialization

_Gadget chains (Java/PHP/Python/Node/.NET) to RCE._

Techniques: 23  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | 🚨 CVE-2026-25769 - Wazuh Insecure Deserialization RCE | `0xBlackash_CVE-2026-25769` |
| 2 | CVE-2026-68771 — ComfyUI Unauthenticated Pickle Deserialization RCE | `0xdak_CVE-2026-68771_exploit` |
| 3 | CVE-2026-69098 — kotaemon unauthenticated deserialization RCE | `0xdak_CVE-2026-69098_exploit` |
| 4 | An unsafe deserialization vulnerability in Wazuh servers allows remote code execution through unsanitized dictionary injection in DAPI requests/responses. This issue arises from th | `0xjessie21_CVE-2025-24016` |
| 5 | CVE-2025-53770 SharePoint Deserialization RCE PoC | `0xray5c68616e37_cve-2025-53770` |
| 6 | CVE-2026-50522 Poc : SharePoint Deserialization RCE | `4minx_CVE-2026-50522` |
| 7 | React2Shell (CVE-2025-55182): The Deserialization Bug That Broke the Web ⚡ | `AdityaBhatt3010_React2Shell-CVE-2025-55182-The-Deserialization-Bug-Tha` |
| 8 | CVE-2025-53770 – Microsoft SharePoint Server 2019 Unauthenticated RCE via Deserialization | `Agampreet-Singh_CVE-2025-53770` |
| 9 | <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,2,5,30&height=200&section=header&text=CVE-2025-68664&fontSize=60&fontAlignY=35&desc=L | `Ak-cybe_CVE-2025-68664-LangGrinch-PoC` |
| 10 | Incomplete fix in Apache MINA AbstractIoBuffer.getObject() method. The classname allowlist validation that restricts which classes can be deserialized is applied too late, after st | `Akinfue_CVE-2026-42778-POC` |
| 11 | CVE-2026-53435 — Jenkins Deserialization → Arbitrary File Read (PoC) | `AmesianX_CVE-2026-53435` |
| 12 | CVE-2025-50460: Remote Code Execution in modelscope/ms-swift via unsafe PyYAML deserialization | `Anchor0221_CVE-2025-50460` |
| 13 | CVE-2025-50461: Remote Code Execution via Unsafe Model Deserialization in Verl | `Anchor0221_CVE-2025-50461` |
| 14 | ModelScope Ms-Swift ModelFileSystemCache Deserialization of Untrusted Data Remote Code Execution Vulnerability | `Before-Rain_CVE-2025-50472` |
| 15 | CVE-2026-56121 — Feast Unauthenticated RCE via gRPC Registry Deserialization | `BiiTts_CVE-2026-56121-Feast-Unauth-RCE` |
| 16 | CVE-2026-24009 — docling-core Unsafe YAML Deserialization (PoC + Notes) | `BiranPeretz_docling-core-CVE-2026-24009` |
| 17 | EncryptInterceptor fail-open bypass in Apache Tomcat Tribes clustering leading to unauthenticated RCE via Java deserialization. | `CypherHippie_CVE-2026-34486---unauthenticated-RCE-via-Java-deserializa` |
| 18 | CVE-2025-24813 - Apache Tomcat Partial PUT + Deserialization RCE | `Dhananjayasj_CVE-2025-24813-Apache-Tomcat-Partial-PUT-Deserialization-` |
| 19 | Sitecore Critical Deserialization (RCE) CVE-2025-53690 POC and Nuclei Template | `ErikLearningSec_CVE-2025-53690-POC` |
| 20 | WSUS CVE-2025-59287 – XML Deserialization RCE (Reverse Shell) | `FurkanKAYAPINAR_CVE-2025-59287` |
| 21 | ModbusMechanic V3.0 Insecure Deserialization & RCE | `Gelcon_PoC-ModbusMechanic-3.0-Insecure-Deserialization-and-RCE` |
| 22 | VisiCut V2.1 Stack Overflow due to Insecure Deserialization | `Gelcon_PoC-of-VisiCut2_1-Stack-Overflow-Vul` |
| 23 | CVE-2025-64512 — pdfminer.six Insecure Deserialization (Pickle) via Crafted PDF | `BardLaudian_CVE-2025-64512` |
