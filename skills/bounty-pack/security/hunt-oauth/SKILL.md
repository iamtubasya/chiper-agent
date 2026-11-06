---
name: hunt-oauth-gateway
description: "Use when auditing OAuth/OIDC endpoints for bug bounty."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [oauth, oidc, sso, jwt, auth, bug-bounty]
---

# Hunt — OAuth / OIDC

Audit OAuth/OIDC/SAML/SSO endpoints untuk bug bounty: token handling,
authorization code flow, redirect_uri validation, PKCE, state leakage,
account linking, session fixation via OAuth.

## Load reference (wajib)

Baca file berikut sebelum mulai — berisi playbook lengkap OAuth/OIDC attack:

```
references/skill-oauth-oidc-audit.md
```

## Golden rules

1. Selalu uji `redirect_uri` validation: open redirect → token leak.
2. Cek PKCE enforcement: apakah `code_challenge` opsional?
3. Cek state parameter: apakah dipakai & divalidasi (CSRF).
4. Cek implicit flow (token in URL) vs PKCE flow yang seharusnya.
5. Cek account linking: apakah bisa link akun attacker ke korban.
6. Jangan report by-design — butuh bukti akses data/dana/user.

## Output yang diharapkan

- Endpoint OAuth/OIDC yang ditemukan (/.well-known/openid-configuration, /authorize, /token, /userinfo)
- Setiap finding: evidence on-disk + step-by-step + impact (data/user/dana/sistem)
- Temuan masuk candidate → review 3x cek → report HANYA yang lolos