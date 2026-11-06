# Web Cache Poisoning

_Source: reverse-skill package (zhaoxuya520/reverse-skill) + field-journal (43 real cases). Extracted 2026-10-21._

## Technique headings
- (see reverse-skill package section below)


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **2026-05-25_pentest-cf-access-sibling-subdomain-cookie-poisoning**
  - 2026-05-25 CF Access 兄弟子域配置错误 → 跨子域 Cookie 投毒 + Session Fixation
  - 5. **`.well-known/cloudflare-access-protected-resource/` 元数据** → 公开端点,泄露 team_domain
  - 6. **CT 日志查兄弟子域**(crt.sh 502,改用 certspotter):
  - curl 'https://api.certspotter.com/v1/issuances?domain={target_proxy_root}&include_subdomains=true&expand=dns_names'
