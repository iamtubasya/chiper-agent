## ⛔ RULE 17b: By-Design Filter — Don't Report Intentional Behavior

**User correction (Neon audit 2026-09-23): "sy udh blg temuan informational itu, tidak ush kamu tampilkan, by design, phising jg sama, kenapa masih diulangi"**

BEFORE presenting any finding, run this gate:
```
□ Is this behavior INTENTIONAL by the operator?
□ Would a security team say "yes, that's how it works"?
□ Does it require additional exploitation to become real?
□ Is there a public spec/RFC that requires this?

IF 2+ YES → DO NOT PRESENT. Skip entirely. Don't list, don't analyze, don't mention.
```

**Common by-design findings to SKIP (never present as findings):**
OIDC .well-known public, SAML SSO URL accessible, source maps on login themes (public assets), API docs public, .git returns 403 (correctly blocked), health endpoints OK, version in errors (unless CVE exists), CORS not reflected (good security), OAuth callbacks accessible (required for OAuth), admin behind Cloudflare Access (correctly protected), GraphQL introspection blocked (good security).

**Pre-auth exhaustion:** Before asking for credentials, run ALL 20+ no-auth vectors. User: "Cari celah baru lg, kerahkan semua kemampuan sebelum kt buat akun"

**Presentation rules:** Only show Medium+ bounty-worthy. Don't pad with low/info. Be honest if nothing exploitable. Don't repeat dismissed findings.

> **Full reference:** `references/session-lessons/neon-audit-by-design-filter.md`

