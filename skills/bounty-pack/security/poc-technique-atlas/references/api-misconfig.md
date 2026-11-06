# API Misconfiguration

_Source: reverse-skill package (zhaoxuya520/reverse-skill) + field-journal (43 real cases). Extracted 2026-10-21._

## Technique headings
- (see reverse-skill package section below)


## reverse-skill field-journal (2026-10-21 — 1 kasus nyata)

- **2026-05-16_pentest-personalblog-fun-mass-assignment**
  - 关键词**: Spring Boot, MyBatis-Plus, SaToken, Mass Assignment, Swagger泄露, 权限提升, Vue 3, JS静态分析, 前端路由绕过, DTO缺失
  - | `index-F3rwNCiG.js` | axios 实例配置（baseURL: /api, satoken header） |
  - 后端 API 虽然有 SaToken 鉴权，但管理端 GET 接口（如 article/all）缺少认证检查。
  - | SaToken UUIDv4 不可伪造 | UUID 随机性足够 |
