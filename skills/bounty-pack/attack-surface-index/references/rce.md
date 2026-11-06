# Reverse Index — RCE & Command Injection

**Cara pakai:** saat recon menemukan *fitur* di kolom kiri, jalankan probe di
kolom tengah SEBELUM menandai kelas ini N/A. Lab & PoC di kolom kanan adalah
contoh nyata yang bisa dibaca/dijalankan.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| file upload / avatar / import | upload handler -> extension/MIME/content bypass -> webshell | Remote code execution via web shell upload · Web shell upload via Cont |
| admin panel / template editor / CMS theme | SSTI or eval sink -> RCE | — |
| API docs (swagger/openapi) or debug toolbar | dev-facing package reaches prod -> unauth RCE | — |
| deserialization endpoint (Java/.NET/pickle) | gadget chain -> RCE | — |
| search / filter / sort parameter | command/SQL/template injection -> RCE | SQL injection vulnerability allowing login bypass · SQL injection vuln |
| image/PDF/CSV export or OG-image generator | rendering sink -> RCE (next/og SVG) | — |
| CI runner / build hook / webhook executor | agent acts on model/input -> RCE | — |

## PoC corpus terkait (120 repo)

- `0-d3y_langflow-rce-exploit`
- `0XFFFF-XD_CVE-2024-4577-PHP-CGI-RCE`
- `0dayan0n_RCE_CVE-2024-7954-`
- `0x00phantom-hat_Hoverfly-1.11.3-RCE-CVE-2025-54123-Exploit`
- `0xAbolfazl_CVE-2025-8088-WinRAR-PathTraversal-PoC`
- `0xCZR1_PoC-Cups-RCE-CVE-exploit-chain`
- `0xDTC_XWiki-Platform-RCE-CVE-2025-24893`
- `0xDTC_js2py-Sandbox-Escape-CVE-2024-28397-RCE`
- `0xEhab_FreePBX-CVE-2025-57819-RCE`
- `0xWhoknows_wp2shell`
- `0xcc12138_wavlink-nu516u1-csrf-command-injection-`
- `0xdeadroot_CVE-2026-39987-marimo-rce`
- `0xgh057r3c0n_SysAid-PreAuth-RCE-Chain`
- `0xr2r_CVE-2024-3400-Palo-Alto-OS-Command-Injection`
- `0xsha_wp2shell`
- `10T4_PoC-Fix-jenkins-rce_CVE-2024-23897`
- `1Altruist_CVE-2025-46271-Reverse-Shell-PoC`
- `3v1lC0d3_RCE-QloApps-CVE-2024-40318`
- `431m_rcetest`
- `686f6c61_POC-WP-XSS2Shell-CVE-2026-64638`
- … +100 repo lagi di `D:/data hermes/poc-compact/`

## Lab PortSwigger: os-command-injection (5 lab)

- Blind OS command injection with out-of-band interaction (`lab-blind-out-of-band`)
- Blind OS command injection with output redirection (`lab-blind-output-redirection`)
- Blind OS command injection with time delays (`lab-blind-time-delays`)
- OS command injection, simple case (`lab-simple`)
- Blind OS command injection with out-of-band data exfiltration (`lab-blind-out-of-band-data-exfiltration`)
