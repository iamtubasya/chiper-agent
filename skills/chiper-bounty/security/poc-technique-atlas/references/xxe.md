# XXE Injection

_XML external entity: file read, SSRF, OOB exfil, blind XXE._

Techniques: 5  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | POC for CVE-2024-34102 : Unauthenticated Magento XXE and bypassing WAF , You will get http connection on ur webhook | `11whoami99_CVE-2024-34102` |
| 2 | CVE-2024-50848: XXE in the WorldServer v11.8.2 | `1mhr4b_CVE-2024-50848` |
| 3 | XML External Entity Injection (XXE) in XDocReport | `AT190510-Cuong_CVE-2025-65482-XXE-` |
| 4 | Jinhe OA XXE Vulnerability | `BigMancer_Jinhe-OA-XXE-Vulnerability` |
| 5 | CVE-2026-11112 – XXE via SVG Image Upload | `George0Papasotiriou_CVE-2026-11112-XXE-via-SVG-Image-Upload` |


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **seed-017_xxe-oob-exfil**
  - | OOB 服务器 80 端口收到回连但 payload 没拼接好 | DTD 嵌套层数搞错 | 严格对照 OOB 模板（外层 + 内层） | 1h |
  - | 文件读取了但只读到一半 | XML 限制实体长度（XML_MAX_TOKEN_BYTES） | 分段读取 + 偏移 | 1h |
  - | 内网 SSRF 全是 connection refused | 应用所在网段没开内部服务 | 改 localhost / 127.0.0.1 / 内部 service 名（K8s） | 30min |
  - | Java 应用打不通 | Java 默认 XML 解析器禁了 SYSTEM | 试 `jar:` 协议 / 或换 SOAP 接口可能用的是 Apache Xerces 老版本 | 数小时 |
