# Cloud / Metadata

_IMDS, bucket, IAM, container escape, SSRF-to-cloud._

Techniques: 15  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | Bloomberg Memray’s Stored XSS via Unescaped Command-Line Metadata | `0xmrma_CVE-2026-32722` |
| 2 | The SSRF filter checked hostname text, but the actual destination was decided later by DNS. That gap let attacker-controlled Webhook URLs reach loopback, metadata, and private netw | `0xmrma_CVE-2026-34207` |
| 3 | A local package installation helper trusted caller-supplied package names too much. In yeoman-environment, missing generators could be installed without user confirmation, turning  | `0xmrma_CVE-2026-42089` |
| 4 | Camaleon CMS 2.9.0 – Authenticated Privilege Escalation (Role Change) + Optional S3 Config Leak | `Alien0ne_CVE-2025-2304` |
| 5 | CVE-2025-54914 Azure Route Exploit | `Ash1996x_CVE-2025-54914-PoC` |
| 6 | Privilege Escalation via ndsudo (Netdata Local Exploit) | `AzureADTrent_CVE-2024-32019-POC` |
| 7 | CVE-2025-24893 - XWiki Remote Code Execution Exploit | `AzureADTrent_CVE-2025-24893-Reverse-Shell` |
| 8 | This exploit and description are written by AI. If you find a mistake or issue, please let me know! This exploit was tested and confirmed working. Thank you! | `AzureADTrent_CVE-2025-4517-POC` |
| 9 | CVE-2025-58434 + CVE-2025-59528 | `AzureADTrent_CVE-2025-58434-59528` |
| 10 | This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://op | `Azure_azure-c-shared-utility` |
| 11 | description: "IPAM - Azure IP Address Management made easy!" | `Azure_ipam` |
| 12 | CVE-2026-54917 — SeaweedFS S3 gateway cross-bucket path traversal | `BiiTts_CVE-2026-54917-SeaweedFS-Cross-Bucket-Traversal` |
| 13 | CVE-2026-33267 — Apache Traffic Server untrusted @ header → internal metadata spoof | `Boreas37_CVE-2026-33267-PoC` |
| 14 | Azure Front Door Privilege Escalation – CVE-2026-24306 PoC | `ExploreUnknowed_CVE-2026-24306` |
| 15 | CVE-2025-2304 POC - Camaleon CMS Privilege Escalation | `AzureADTrent_CVE-2025-2304_POC` |


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **seed-016_k8s-container-escape**
  - 拿到一个容器内的 shell（通过应用漏洞 / 暴露的 Jenkins / 或 K8s 上的 RCE），需要从容器逃逸到宿主机，进而横向控制整个 K8s 集群。
  - env | grep -i 'kube\|docker\|aws\|az' # 服务账号 / 元数据 token
  - ls /var/run/secrets/kubernetes.io/serviceaccount/  # K8s SA token
  - TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
