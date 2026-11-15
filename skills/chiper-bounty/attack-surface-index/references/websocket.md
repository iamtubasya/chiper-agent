# Reverse Index — WebSockets

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| fitur realtime (chat, notifikasi, live) | cross-site WebSocket dari origin lain | Manipulating the WebSocket handshake to exploit vulnerabilities · Ma |
| WS handshake tanpa validasi Origin | manipulasi handshake → akses | Manipulating the WebSocket handshake to exploit vulnerabilities · Ma |
| message yang diteruskan ke user lain | inject payload ke user lain | Manipulating the WebSocket handshake to exploit vulnerabilities · Ma |

## PoC corpus terkait (1 repo)

- `George0Papasotiriou_CVE-2026-1010-WebSocket-Connection-Smuggling-via-Malformed-Upgrade-Header`

## Lab PortSwigger: websockets (2 lab)

- Manipulating the WebSocket handshake to exploit vulnerabilities (`lab-manipulating-handshake-to-exploit-vulnerabilities`)
- Manipulating WebSocket messages to exploit vulnerabilities (`lab-manipulating-messages-to-exploit-vulnerabilities`)
