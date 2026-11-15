# Custom Protocol Reverse Engineering

_Source: reverse-skill package (zhaoxuya520/reverse-skill) + field-journal (43 real cases). Extracted 2026-10-21._

## Technique headings
- (see reverse-skill package section below)


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **seed-011_pcap-protocol-reverse**
  - | TLS 抓到但解不了 | 客户端不留 SSLKEYLOGFILE | 在客户端进程层 hook（Frida 抓 ssl_read/ssl_write）抓明文 | 1.5h |
  - StrLenField("payload", "", length_from=lambda p: p.length - 8),
  - if TCP in p and p[TCP].dport == 9527 and p.payload:
