# Reverse Index — LFI / Path Traversal

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| parameter file / path / download / template | ../../../etc/passwd + variasi encoding | File path traversal, traversal sequences blocked with absolute path  |
| upload yang bisa ditulis ke path | LFI → log poisoning → RCE | File path traversal, traversal sequences blocked with absolute path  |
| parameter include / page / view | path traversal + null byte / superfluous decode | File path traversal, traversal sequences blocked with absolute path  |
| API yang baca file by name | absolute-path bypass + extension validation bypass | File path traversal, traversal sequences blocked with absolute path  |

## PoC corpus terkait (4 repo)

- `0xAbolfazl_CVE-2025-8088-WinRAR-PathTraversal-PoC`
- `751897386_PHPVibe_vulnerability_Directory-Traversal`
- `AbokorMAHAMMADMOUSSE_CVE-2025-25279-Mattermost-Path-Traversal`
- `AdityaBhatt3010_CVE-2025-8088-WinRAR-Zero-Day-Path-Traversal`

## Lab PortSwigger: file-path-traversal (6 lab)

- File path traversal, traversal sequences blocked with absolute path bypass (`lab-absolute-path-bypass`)
- File path traversal, traversal sequences stripped non-recursively (`lab-sequences-stripped-non-recursively`)
- File path traversal, simple case (`lab-simple`)
- File path traversal, traversal sequences stripped with superfluous URL-decode (`lab-superfluous-url-decode`)
- File path traversal, validation of file extension with null byte bypass (`lab-validate-file-extension-null-byte-bypass`)
- File path traversal, validation of start of path (`lab-validate-start-of-path`)
