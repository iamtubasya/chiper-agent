# Reverse Index — Cloud / Infrastructure

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| bucket/storage publik | list & baca tanpa auth, cek ownership | — |
| IAM role / policy longgar | privilege escalation lewat role assumption | — |
| metadata service (169.254.169.254) | SSRF → kredensial sementara | — |
| Kubernetes API / etcd exposed | anonymous access → cluster takeover | — |
| serverless function URL | invocation tanpa auth + env leak | — |

## PoC corpus terkait (11 repo)

- `Alicey0719_docker-POC_CVE-2024-1086`
- `CloudRoam7_CVE`
- `CloudWise-OpenSource_FlyFish`
- `DavCloudz_cve`
- `ELIZEUOPAIN_Exploit-CVE-2024-9513-NetAdmin-IAM-Allows-User-Enumeration-In-Active-Directory`
- `EagleTube_CloudPanel`
- `Fc04dB_novel-cloud-vul`
- `FlowerWitch_CVE-2025-61686_docker`
- `Flux159_mcp-server-kubernetes`
- `George0Papasotiriou_CVE-2026-21005-Docker-Registry-V2-Schema-1-Image-Poisoning`
- `George0Papasotiriou_CVE-2026-21008-Kubernetes-Service-Account-Token-Mounted-in-HostPath`
