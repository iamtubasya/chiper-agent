# Race Conditions / TOCTOU

_Concurrent abuse of check-then-act: limit/coupon/stock/double-spend._

Techniques: 6  |  Source corpus: poc-compact (GitHub PoC repos)

Format: technique = the **method** (what the bug/exploit does). Repo = exemplar to read for detail.
Never paste payload bodies verbatim into a client; use the method + adapt.

| # | Technique (method) | Exemplar repo |
|---|---|---|
| 1 | CVE-2026-28992: IOHIDFamily FastPathUserClient Race Conditions | `0xjohnnydev_CVE-2026-28992-IOHIDFamily-FastPathUserClient-Race-Conditi` |
| 2 | > a signal handler race condition in OpenSSH's server (sshd) | `7etsuo_cve-2024-6387-poc` |
| 3 | SimplCommerce is affected by a race condition vulnerability in the checkout logic, allowing multiple users to purchase more products than are in stock via simultaneous checkout req | `AbdullahAlmutawa_CVE-2024-53476` |
| 4 | A Time-of-Check to Time-of-Use (TOCTOU) vulnerability was identified in Balena Etcher for Windows in versions prior to 2.1.4. | `B1tBreaker_CVE-2026-30332` |
| 5 | CVE-2026-21007 – GPU Driver ioctl Race Condition (Kernel Memory Mapping) | `George0Papasotiriou_CVE-2026-21007-GPU-Driver-ioctl-Race-Condition-Ker` |
| 6 | a signal handler race condition in OpenSSH's server (sshd) | `FerasAlrimali_CVE-2024-6387-POC` |
