---
name: hunt-session-gateway
description: "Use for IP spoofing, session hijack, subdomain takeover, session management flaws."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [session, hijack, ip-spoofing, subdomain-takeover, auth]
---

# Hunt — IP / Session Hijacking

Audit session management: cookie flags, session fixation, session
concurrency, IP-based auth bypass, subdomain takeover yang bisa
mem-bypass cookie scoping.

## Load reference (wajib)

Baca file berikut sebelum mulai — playbook IP spoofing & session hijack:

```
references/skill-ip-and-session-hijacking.md
```

## Golden rules

1. Uji session fixation: login ganti session id? bisa dipaksa set?
2. Uji cookie flags: Secure / HttpOnly / SameSite / Domain scope.
3. Uji IP-based auth: X-Forwarded-For / X-Real-IP bypass.
4. Uji subdomain takeover → cookie domain scoping exploit.
5. Jangan report by-design — butuh bukti bisa ambil session/data user.

## Output yang diharapkan

- Endpoint/behavior session yang vulnerable + evidence on-disk
- Setiap finding: step-by-step + impact (account takeover / data access)
- Temuan masuk candidate → review 3x cek → report HANYA yang lolos