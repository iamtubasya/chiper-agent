# Reverse Index — Race Conditions

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| transfer / withdraw / redeem / claim | single-packet attack (Turbo Intruder) | Limit overrun race conditions · Bypassing rate limits via race condi |
| voucher/kupon sekali-pakai | 2 request bersamaan lolos cek 'sudah dipakai' | Limit overrun race conditions · Bypassing rate limits via race condi |
| endpoint dengan limit kuota | limit overrun via concurrency | Limit overrun race conditions · Bypassing rate limits via race condi |
| follow/unfollow/vote | race pada counter | Limit overrun race conditions · Bypassing rate limits via race condi |

## PoC corpus terkait (4 repo)

- `0xjohnnydev_CVE-2026-28992-IOHIDFamily-FastPathUserClient-Race-Conditions`
- `C9Y57_TOTOLINK_setTracerouteCfg`
- `DaddyBigFish_CVE-2025-59287-hawktrace`
- `George0Papasotiriou_CVE-2026-21007-GPU-Driver-ioctl-Race-Condition-Kernel-Memory-Mapping-`

## Lab PortSwigger: race-conditions (6 lab)

- Limit overrun race conditions (`lab-race-conditions-limit-overrun`)
- Bypassing rate limits via race conditions (`lab-race-conditions-bypassing-rate-limits`)
- Multi-endpoint race conditions (`lab-race-conditions-multi-endpoint`)
- Single-endpoint race conditions (`lab-race-conditions-single-endpoint`)
- Exploiting time-sensitive vulnerabilities (`lab-race-conditions-exploiting-time-sensitive-vulnerabilities`)
- Partial construction race conditions (`lab-race-conditions-partial-construction`)
