---
name: hunt-session
description: "Hunt Session Management vulnerabilities — session fixation (no regeneration on login), insufficient invalidation on logout / password-change / email-change, predictable or low-entropy session IDs, JWT-as-session with no exp/revocation, refresh-token rotation/reuse-detection gaps, OAuth/SSO session linkage, device-bound-session (DBSC) downgrade, and cookie attribute issues (Secure/HttpOnly/SameSite/__Host-). Validate with TWO real sessions (attacker A + victim B), body-diff every 200, and OOB confirmation for theft chains. Medium to Critical (fixation→admin hijack, no-invalidation→persistent ATO)."
sources: hackerone_public, portswigger_research, owasp_wstg
report_count: 18
---

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §F): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`


## Autonomous Testing Priority

**Missing HttpOnly on cookies is auto-detected — focus your active testing on lifecycle invalidation (higher impact).**

**Pattern 1 — Session survives logout (most common high-value finding):**
1. Login and note the session token/cookie value
2. Call the logout endpoint (`/logout`, `POST /api/logout`, etc.)
3. Try to use the OLD session token to access a protected resource (`/api/me`, `/dashboard`, `/account`)
4. If 200 with user data → session not invalidated on logout = ATO persistence

**Pattern 2 — Session not regenerated on login (session fixation):**
1. GET any page to receive a pre-authentication session token/cookie
2. POST valid credentials to the login endpoint
3. Compare the session token BEFORE and AFTER login
4. If the token is unchanged → session fixation vulnerability

**Pattern 3 — Session survives password change:**
1. Login → record session A value
2. Change the password via the account settings endpoint
3. Replay session A on a protected endpoint
4. If 200 → token not rotated on credential change = persistent ATO (critical chain when combined with XSS/cookie theft)

**Content-type:** Login and session endpoints vary — use `application/json` for REST APIs, `application/x-www-form-urlencoded` for traditional web forms. Try both if the first returns an unexpected response.

**Proof:** A protected-resource 200 response (with user data) using a session token that should have been invalidated confirms the finding.

---

# HUNT-SESSION — Session Management

## Crown Jewel Targets

Session fixation leading to admin hijack = Critical. Session surviving a password change = High-to-Critical (persistent ATO from a stolen cookie that the victim believes they revoked by resetting their password).

**Highest-value chains:**
- **Session fixation** — server accepts a session ID set by the client and does NOT regenerate it on login → attacker pre-plants an ID, victim authenticates, attacker rides the now-authenticated session → persistent ATO.
- **No invalidation on logout** — old token still works after `/logout` → theft window never closes.
- **No invalidation on password / email change** — a stolen session survives the victim's "I think I was hacked, let me reset" → persistent ATO. This is the single highest-paid session bug class.
- **Refresh-token reuse without rotation-detection** — a leaked refresh token mints fresh access tokens forever; no reuse-detection means the legitimate user's later refresh does NOT revoke the attacker's branch.
- **Predictable / low-entropy session ID** — sequential, timestamp- or userId-derived IDs → brute-force or compute other users' sessions.
- **JWT-as-session with no `exp` / no revocation list** — stolen JWT = permanent access; logout is cosmetic.

---

## Grounding — patterns that shaped each phase

No invented CVE/report IDs below. These are the *named, publicly-documented* patterns this skill encodes:

- **Session fixation, login-CSRF, no-regeneration-on-auth** — OWASP WSTG-SESS-03 / WSTG-SESS-01; the classic ACROS / Mitja Kolšek session-fixation paper. Highest-impact variant: fixing the session of an SSO/admin user.
- **SameSite=Lax sibling-subdomain CSRF reaching session state** — Argo CD **CVE-2024-22424** (Lax cookies sent on top-level cross-site navigations from a sibling subdomain). Use this when a session cookie relies on `SameSite=Lax` as its only CSRF defence.
- **Refresh-token rotation & automatic reuse-detection** — the Auth0/IETF OAuth-Security-BCP model: a rotated refresh token, if replayed, must invalidate the *entire token family*. Absence = the core bug to prove.
- **Device Bound Session Credentials (DBSC)** — the W3C/Chrome DBSC draft binds a session to a TPM/device key. Test the *downgrade*: does the server still accept a non-bound cookie when the DBSC challenge is stripped?
- **Cookie attribute hardening** — OWASP WSTG-SESS-02; `__Host-`/`__Secure-` prefixes per RFC 6265bis. Missing `HttpOnly` is only a finding when a real XSS/DOM sink exists (chain with `hunt-xss`/`hunt-dom`).
- **Entropy** — NIST SP 800-63B requires ≥64 bits of entropy in a session identifier. Treat anything decodable to a counter/timestamp/userId as a finding regardless of length.

Cross-refs: ATO chaining → `hunt-ato`; JWT alg/kid tampering → `hunt-api-misconfig`; OAuth code/state flaws → `hunt-oauth`; CSRF mechanics → `hunt-csrf`; cookie-theft sinks → `hunt-xss` / `hunt-dom`.

---

## Attack Surface Signals

```
Set-Cookie: session=...            # name varies: sid, JSESSIONID, connect.sid,
                                   # PHPSESSID, ASP.NET_SessionId, laravel_session, _csrf
/login /logout /api/login /oauth/token
/auth/refresh /api/token/refresh   # refresh-token rotation surface
/account/change-password /settings/email
?sid= ?session= in URL             # session-in-URL → leaks via Referer/logs (finding)
```
```
# Header signals worth flagging immediately:
Set-Cookie: session=abc; Path=/                 # no HttpOnly/Secure/SameSite
Set-Cookie: session=abc; SameSite=None          # None without Secure = rejected by modern browsers, but flag
Set-Cookie: __Host-sess=...; Secure; Path=/     # GOOD — hard to fixate
Sec-Session-Registration: ...                   # DBSC in play → test downgrade
Set-Cookie: <sess>=127.0.0.<X-Forwarded-For value><rand>   # client IP BAKED INTO the token (or into a
                                                          # hop/session cookie) → references/client-ip-header-session-token.md
```

---

## Step-by-Step Hunting Methodology

> **Two-session rule.** Every invalidation/fixation claim is proven with TWO concrete sessions captured by a real flow — attacker **A** and victim **B** — never with hardcoded placeholder strings. Helpers below capture real cookies from `curl`'s Netscape jar.

```bash
TARGET=target.com
JAR_A=$(mktemp); JAR_B=$(mktemp)

# Robust session-cookie extractor: handles #HttpOnly_ prefix lines and any
# cookie name (sid/JSESSIONID/connect.sid/PHPSESSID/...). Prints name=value.
get_cookie () {  # $1=jar  $2=name-regex (default: common session names)
  local jar="$1" re="${2:-session|sid|sess|JSESSIONID|connect\.sid|PHPSESSID|laravel_session}"
  awk -v re="$re" '
    /^#HttpOnly_/ { sub(/^#HttpOnly_/,""); }   # strip jar HttpOnly marker
    /^#/ { next }                              # skip remaining comments
    NF>=7 && $6 ~ re { print $6"="$7 }         # field6=name field7=value
  ' "$jar" | tail -1
}
```

### Phase 1 — Session Fixation (regeneration-on-login)
```bash
# Step 1: grab a pre-auth session the SERVER hands an anonymous client.
curl -s -L -c "$JAR_A" "https://$TARGET/login" -o /dev/null
PRE=$(get_cookie "$JAR_A"); echo "pre-auth: $PRE"

# Step 1b (stronger): can we FORCE an arbitrary ID? attacker-chosen value.
FIX="session=AAAAdeadbeefAAAA"

# Step 2: authenticate while CARRYING the pre-auth/forced cookie (reuse same jar).
curl -s -L -c "$JAR_A" -b "$JAR_A" -X POST "https://$TARGET/login" \
  -d "username=attacker@example.com&password=CorrectHorse1" -o /dev/null
POST=$(get_cookie "$JAR_A"); echo "post-auth: $POST"

# DECISION:
#  - If $POST == $PRE (value unchanged across the auth boundary) AND that value
#    now returns authenticated data → FIXATION. The server reused the anon ID.
#  - If the forced $FIX value is accepted and authenticates → CRITICAL fixation
#    (attacker controls the ID; no email/XSS needed to plant it).
AUTH=$(curl -s -L -b "$JAR_A" "https://$TARGET/api/me")
echo "$AUTH" | head -c 200
```
**FP guard:** a value *change* is not automatically safe — some apps rotate the readable cookie but keep a stable server-side session keyed by a second cookie. Diff the FULL `Set-Cookie` set and confirm the *old* value is genuinely dead (Phase 2). Also confirm `/api/me` returns *your* identity, not a generic 200/landing page.

### Phase 2 — Invalidation on Logout
```bash
# A logs in for real (fresh jar), capture A's live session.
curl -s -L -c "$JAR_A" -X POST "https://$TARGET/api/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"attacker@example.com","password":"CorrectHorse1"}' -o /dev/null
A=$(get_cookie "$JAR_A"); echo "A=$A"

# Baseline: what does an authenticated /api/me look like for A? (capture body, not just code)
BEFORE=$(curl -s -L -b "$JAR_A" "https://$TARGET/api/me")

# Logout A.
curl -s -L -b "$JAR_A" -X POST "https://$TARGET/api/logout" -o /dev/null

# Replay A's OLD cookie value explicitly (do NOT reuse the jar — logout may have
# overwritten it). Compare body + code against the authenticated baseline.
AFTER=$(curl -s -L -H "Cookie: $A" "https://$TARGET/api/me" -w '\n[%{http_code}]')
echo "AFTER: $AFTER"
```
**FP discipline (mandatory):**
- Don't trust the status code. A cached/edge 200 or a generic SPA shell returns 200 for everyone. **Body-diff** `AFTER` against `BEFORE` — the finding is only real if `AFTER` still contains A's *unique identity marker* (email, user-id, CSRF token, account name).
- Confirm with a **negative control**: a random/garbage cookie value must NOT return the same authenticated body. If garbage also yields 200 with user data, the endpoint isn't session-gated and there's no finding here.
- Re-test after a **short delay** and from a **different IP** — some servers lazily expire on next access or pin sessions to IP.

### Phase 3 — Invalidation on Password / Email Change (persistent-ATO core)
```bash
# This is the real two-session flow. A = attacker holding a stolen/old session.
# B = the victim who changes their password believing it revokes access.
# (In a real engagement A is a session you legitimately captured for a TEST account
#  that you also control as B — never use a real third party.)

# 1) Log the TEST account in as session A, capture it.
curl -s -L -c "$JAR_A" -X POST "https://$TARGET/api/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"victim@example.com","password":"OldPass!1"}' -o /dev/null
SESSION_A=$(get_cookie "$JAR_A"); echo "SESSION_A=$SESSION_A"
BEFORE=$(curl -s -L -H "Cookie: $SESSION_A" "https://$TARGET/api/profile")

# 2) Log the SAME account in as session B (separate jar = "the victim's browser").
curl -s -L -c "$JAR_B" -X POST "https://$TARGET/api/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"victim@example.com","password":"OldPass!1"}' -o /dev/null

# 3) Victim (session B) changes the password.
curl -s -L -b "$JAR_B" -X POST "https://$TARGET/api/change-password" \
  -H 'Content-Type: application/json' \
  -d '{"old_password":"OldPass!1","new_password":"BrandNew!2"}' -o /dev/null

# 4) THE TEST: replay the OLD SESSION_A captured in step 1.
AFTER=$(curl -s -L -H "Cookie: $SESSION_A" "https://$TARGET/api/profile" -w '\n[%{http_code}]')
echo "AFTER pw-change: $AFTER"
```
**Decision + FP discipline:**
- Finding is confirmed only if `AFTER` returns 200 **and** the body still carries the account's unique data (body-diff vs `BEFORE`). A bare 200 on a public/SPA route is not proof.
- Run the **garbage-cookie negative control** again to prove the endpoint is session-gated.
- Repeat the identical flow for **email-change** (`/settings/email`) and for **logout-all-devices** — apps frequently invalidate the *acting* session (B) but not *sibling* sessions (A). That sibling-survival is the exact persistent-ATO primitive `hunt-ato` chains.
- **Severity gate:** if the change-password endpoint also lacks a current-password / MFA step-up (per `hunt-mfa-bypass`), A can pivot from read-only to full takeover → escalate.

### Phase 4 — Cookie Attribute Analysis
```bash
curl -sI -L "https://$TARGET/" | grep -i '^set-cookie'
```
- **HttpOnly** missing → cookie reachable via `document.cookie`. Only a finding **chained to a real XSS/DOM sink** (`hunt-xss`/`hunt-dom`) — note it, don't report standalone as High.
- **Secure** missing → cookie sent over cleartext HTTP; pair with `hunt-tls-network` (downgrade/HSTS-gap) for a network-attacker chain.
- **SameSite** missing/`None` → CSRF reachability; `SameSite=Lax` is bypassable via sibling-subdomain top-level navigation (Argo CD **CVE-2024-22424** class) → hand to `hunt-csrf`.
- **`__Host-` / `__Secure-` prefix absent** → the session can be overwritten/fixated from a subdomain or non-secure context; its presence largely kills cookie-fixation, so flag the *absence* as the precondition for Phase 1.

### Phase 5 — Session-ID Entropy
```bash
# Collect a LARGE sample (200+) of freshly-issued IDs. -L is required: a 302
# /login often sets the cookie on the redirect target, not the first response.
N=200; SAMP=$(mktemp)
for i in $(seq 1 $N); do
  J=$(mktemp)
  curl -s -L -c "$J" "https://$TARGET/login" -o /dev/null
  get_cookie "$J" | cut -d= -f2- >> "$SAMP"
  rm -f "$J"
done
sort "$SAMP" | uniq -d | head            # duplicates = catastrophic (re-use)
awk '{print length($0)}' "$SAMP" | sort -n | uniq -c   # length distribution
```
Then analyse, don't eyeball:
- **Sequential / monotonic** — `sort -n` the decoded values; a steady +1/+N delta = predictable.
- **Decodable structure** — `base64 -d` / hex-decode each ID and look for embedded `userId`, unix timestamps, or PIDs.
- **Bit entropy** — feed the raw bytes to `ent` or `dieharder`; NIST SP 800-63B wants ≥64 bits. 10 samples is far too few to claim anything — gather hundreds.
- **FP guard:** a long random-*looking* token is not proof of strength; only structural decode + a large-sample entropy estimate is. Conversely a short token with high per-char entropy may still be fine — measure, don't count characters.

### Phase 6 — JWT-as-Session
```bash
JWT="eyJ..."        # captured from Authorization: Bearer or a cookie
# Decode header + payload safely (base64url padding fix).
b64url(){ local s="${1//-/+}"; s="${s//_//}"; printf '%s' "$s===" | base64 -d 2>/dev/null; }
b64url "$(cut -d. -f1 <<<"$JWT")" | jq .   # header: alg, kid
b64url "$(cut -d. -f2 <<<"$JWT")" | jq .   # claims: exp, iat, sub, jti
```
- **`exp` missing or years out** → no expiry. **`jti` missing** → server cannot maintain a revocation list → logout can't truly revoke.
- **Revocation test:** logout, then replay the *same* JWT against `/api/me`. If it still returns the user → tokens are not server-revocable; this is the JWT-session persistence finding. Body-diff to avoid a cached 200.
- **Tampering (alg/kid/key-confusion) is owned by `hunt-api-misconfig`** — hand off `jwt_tool $JWT -T` / `-X a` there rather than duplicating it.

### Phase 7 — Refresh-Token Rotation & Reuse-Detection
```bash
# 1) Obtain a refresh token (login or /oauth/token), then rotate it once.
RT1=$(curl -s -L -X POST "https://$TARGET/api/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"victim@example.com","password":"OldPass!1"}' | jq -r '.refresh_token')

# 2) Use RT1 to mint a new access token — server SHOULD return a rotated RT2.
R2=$(curl -s -L -X POST "https://$TARGET/auth/refresh" \
  -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$RT1\"}")
RT2=$(jq -r '.refresh_token' <<<"$R2"); echo "rotated? RT1!=RT2 -> $([ "$RT1" != "$RT2" ] && echo yes || echo NO-ROTATION)"

# 3) REUSE-DETECTION test: replay the OLD RT1 again (simulating the leaked token).
REPLAY=$(curl -s -L -X POST "https://$TARGET/auth/refresh" \
  -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$RT1\"}" -w '\n[%{http_code}]')
echo "RT1 replay: $REPLAY"

# 4) Then confirm RT2 was KILLED by the replay (correct BCP behaviour invalidates
#    the whole family). If RT2 still works after RT1 was replayed → no family-revocation.
curl -s -L -X POST "https://$TARGET/auth/refresh" \
  -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$RT2\"}" -w '\n[%{http_code}]'
```
**Findings:** no rotation (RT1==RT2) = a long-lived stealable credential; rotation **without** reuse-detection (RT1 replay still mints tokens, or RT2 survives the replay) = the leaked-token-persistence bug per the OAuth Security BCP. **OOB note:** if you suspect a leaked RT via SSRF/log/JS-bundle, confirm the token's reach with `hunt-ssrf`/`hunt-source-leak`, not by guessing.

### Phase 8 — OAuth/SSO Session Linkage & DBSC Downgrade
```bash
# SSO linkage: after IdP callback, is the app session bound to the IdP session?
#  - Log out at the IdP only; replay the app session cookie. Still 200 with user
#    data → app session outlives the IdP session (single-logout gap).
# DBSC downgrade: if responses carry Sec-Session-Registration / Sec-Session-Id,
#  strip the device-bound proof header and replay the plain cookie:
curl -s -L -H "Cookie: $A" "https://$TARGET/api/me" -w '\n[%{http_code}]'
#  If the plain (non-bound) cookie is still accepted → device-binding is advisory,
#  not enforced → a stolen cookie defeats DBSC entirely.
```
Hand OAuth `state`/`redirect_uri`/code-injection to `hunt-oauth`; this phase only covers the *session-layer* binding.

---

## Chain Table

| Session finding | Chain to | Impact |
|----------------|----------|--------|
| Session fixation (forced `__Host-`-less cookie) | Trick admin/SSO user into authenticating on planted ID | Admin session takeover (Critical) |
| No logout/password-change invalidation | `hunt-xss`/`hunt-dom` cookie theft → replay surviving session | Persistent ATO past victim's reset |
| Refresh token, no reuse-detection | Leaked RT (SSRF/log/bundle) → infinite access-token minting | Persistent ATO, survives password change |
| `SameSite=Lax` only | Sibling-subdomain top-level nav (CVE-2024-22424 class) → CSRF | State change / login-CSRF → fixation |
| JWT no `exp`/`jti` | Stolen token, no server revocation | Permanent access |
| DBSC downgrade accepted | Steal plain cookie despite device-binding | Defeats the only theft mitigation |
| Predictable ID | Compute/brute another user's session | Cross-user ATO |

---

## Client-IP header trust (cookie value encodes an IP, or changes with X-Forwarded-For)

Kalau value cookie kelihatan meng-encode IP (`Vietnam2Session=127.0.0.<ip>…`, `HopSession=127.0.0.<ip>…`)
atau berubah bentuk saat header IP dikirim, baca `references/client-ip-header-trust-testing.md`.
Ringkas:

- Tentukan header mana yang dihormati (real estate: `X-Forwarded-For` + `Client-IP` iya,
  `X-Real-IP` / `True-Client-IP` / `Forwarded` tidak).
- Kalau value-nya masuk ke `Set-Cookie`, uji refleksi atribut (`; Domain=…`). **Hanya payload yang lolos
  3x** yang boleh masuk laporan — di run nyata cuma `Domain=` yang lolos, `Path=`/`Max-Age=`/`SameSite=`
  dipotong. Atribut legitik ditulis paling akhir, jadi per RFC 6265 dia yang menang; bilang itu terus
  terang daripada overclaim.
- Sebelum nyimpulin severity, jalankan tiga uji penentu: CRLF/response-splitting (raw socket),
  caching (`X-Cache: HIT` pada respons ber-`Set-Cookie` = High), dan **diff otorisasi** —
  fetch tiap path dua kali (clean vs `X-Forwarded-For: 127.0.0.1`) lalu bandingkan status + hash body
  di seluruh host in-scope. **Ini satu-satunya jalur Low→High.** Hasil kosong tetap hasil: tulis sebagai
  "tested and ruled out", bukan dihapus.
- Session fixation: kirim cookie pilihan penyerang; kalau server selalu mencetak token baru, tidak ada
  fixation — catat sebagai negatif.

## Is the token *supposed* to be unauthenticated? Read the vendor's own client first

An endpoint that hands out a full session token to an unauthenticated caller looks like the best
finding of the engagement. It is also the single easiest thing to mis-report, because hand-off
tokens are a legitimate design. **Grep the vendor's own JS bundle for the call site before you score
it.** If their client calls it unauthenticated, the token is the credential by design and there is no
bug.

Measured on **Proton** (`/api/auth/v4/sessions/forks/{selector}`), 2026-10-25 — a prior round had
already drafted this as a High "session-fork tokens issued without the secret key". The client bundle
settled it in one grep:

```js
// pass-index.js — the vendor's own code
pullFork ?? (e => { let {selector:t} = e,
  a = {method:"get", url:`auth/v4/sessions/forks/${t}`};
  return a.url = n ? `${n}/${a.url}` : a.url, r({...a, unauthenticated:!0}) })
```

`unauthenticated:!0` on the fork claim is the design: the app holds only a selector, so the selector
*is* the bearer credential for the hand-off. Dropped, correctly.

### The check, in order

1. **Find the call site.** `grep -o '.\{120\}sessions/forks.\{140\}' *.js` and read whether the
   request is issued with `unauthenticated:true`, with no `Authorization`, or from a pre-login page.
2. **Read the scope difference.** A hand-off token is usually *narrower* than a login session.
   Measured fork scope: `full self payments keys parent user loggedin nondelinquent mail calendar
   drive pass verified settings wallet meet` — note what is **absent** vs the SRP-login session
   (`password`, `locked`, `vpn`, `docs`, `lumo`). A narrow by-design token that cannot escalate is not
   a finding; a *wide* one that can is.
3. **Attack the scope boundary instead of the issuance.** The reportable question becomes "can this
   token do something its scope says it cannot?" Enumerate one privileged write per missing scope and
   confirm the server refuses (`403 Access token does not have sufficient scope` +
   `MissingScopes:["password"]` / `["locked"]` is the *correct* answer, and it is a negative you
   should record, not a dead end).
4. **Check revocation coverage.** Revoke-all, then replay the hand-off token AND its refresh token.
   Both dead (`401` access, `422 Invalid refresh token`) = revocation is wired correctly. That
   negative is worth writing down — it is what tells the vendor you tested the whole lifecycle.

### Related by-design shapes that read as findings

- **Recovery material returned to any token.** `GET /core/v4/users` returns per-key
  `RecoverySecret` + `RecoverySecretSignature` to *every* session token including the narrow one.
  It looks like key exfiltration. It is not: the recovery *file* (a local blob the client writes) is
  encrypted **with** that secret, so the secret alone decrypts nothing. Confirm by reading the client's
  export/import code (`exportPrivateKey` → `encryptMessage({passwords:[recoverySecret]})`) before
  writing anything. Verify with a real key: `gpg --batch --pinentry-mode loopback --passphrase <s>
  --import key.asc` succeeds for *any* passphrase when the key is loaded that way, so use a
  **signing** test (`--clearsign` + grep for `BEGIN PGP SIGNED MESSAGE` **and** absence of
  `Bad passphrase`) to tell a real passphrase from a no-op import.
- **Availability/enumeration oracle that is just the feature.** `users/available` returning
  `409 Username already used` for a taken name is the documented availability check. Before reporting
  enumeration, verify the `Suggestions` array is not derived from real accounts — on Proton the
  suggested names were themselves **free** (`200`), i.e. synthetic. One request per suggestion settles it.

**Rule:** an unauthenticated token endpoint is a finding only when the token grants something the
caller should not have. Locate the design intent in the vendor's own client, then attack the
boundary the design claims to enforce.

## Validation (house FP discipline)

Before claiming ANY session finding:
- **Two real sessions, not placeholders** — every fixation/invalidation claim uses A and B captured by the `curl` flows above.
- **Body-diff, never status-only** — a 200 means nothing without the account's unique identity marker present in the body, diffed against the authenticated baseline.
- **Negative control** — a garbage/random cookie must FAIL where your "surviving" cookie succeeds; otherwise the endpoint isn't session-gated and it's a non-finding.
- **Cache/edge check** — re-request with a cache-buster and from a second IP; rule out an edge-cached or IP-pinned 200.
- **OOB for theft chains** — when the impact depends on exfiltrating a cookie/token (XSS, SSRF, log leak), confirm receipt out-of-band (Collaborator) rather than asserting it.
- **Static-vs-state** — `HttpOnly`/`Secure`/`SameSite` absence is a *policy* observation; only report as High once paired with a real exploit primitive (XSS, network-MITM, CSRF). Standalone attribute gaps are Low/Informational.

**Severity:**
- Session fixation → admin/SSO takeover: **Critical**
- No invalidation on password/email change, or refresh-token reuse without detection: **High → Critical** (escalate if MFA/step-up also absent)
- Predictable/duplicate session ID: **High**
- No invalidation on logout: **Medium → High** (depends on theft vector)
- Missing `HttpOnly`/`SameSite` standalone: **Low/Informational** until chained


## 2026 sweep 7 (dork pass 2026-10-18 — 1 repo)

- email2sms (IEEE S&P 2026) — **text-message spoofing via carrier email-to-SMS gateways**: messages injected toward a carrier gateway (e.g. with `telnetlib3`) are displayed with a sender of the attacker's choosing. Relevant to OTP/SMS flows: an attacker who can reach the gateway can forge the 'bank' message that phishes the victim's own credentials.
  - smartphone messaging systems that allows attackers to easily spoof the identity
  - then be displayed as the sender of the attacker’s choosing (e.g., arbitrary

## OWASP Top 10:2025 anchor + ASVS V7 test plan (added 2026-10-30)

Session-management failures sit in **A07:2025 Authentication Failures** (36 CWEs, highest
exploitability 7.69 and highest impact 4.44 in the Top 10). ASVS 5.0 V7 gives the requirement-level
checklist — cite the ID in the report:

| ASVS | Lvl | Requirement | Our phase |
|---|---|---|---|
| **7.2.1** | **1** | all session token verification via a **trusted backend** | Phase 6 |
| **7.2.2** | **1** | dynamically generated tokens, not static | Phase 5 |
| **7.2.4** | **1** | **new session token on authentication (incl. re-auth)** | Phase 1 — fixation |
| **7.4.1** | **1** | **session unusable after logout/expiry** | Phase 2 |
| **7.4.2** | **1** | **all sessions terminated when account disabled/deleted** | Phase 3 |
| 7.3.1 | 2 | inactivity timeout | Phase 2 |
| 7.3.2 | 2 | absolute maximum lifetime | Phase 6 |
| 7.4.3 | 2 | option to terminate other sessions after factor change | Phase 3 |
| **7.5.1** | **2** | **full re-auth before modifying sensitive auth attributes** | Phase 3 |
| 7.5.3 | 3 | step-up auth before highly sensitive transactions | Phase 8 |
| **7.6.1** | **2** | RP↔IdP session lifetime behaves as documented (SLO) | Phase 8 |
| **7.6.2** | **2** | **session creation requires consent or explicit action** | Phase 8 — silent session creation |

Full map + score tables: `security/exploit-cookbook/references/owasp-top10-2025-asvs5-access-auth.md`

## Naikkan severity — komposisi K/A/B/X (wajib sebelum lapor, added 2026-10-30)

Session yang tidak diinvalidasi adalah **B (Bypass)** — ia menghapus cek yang memblokir hop berikutnya. Fixation adalah **B** juga. Yang membuatnya Critical: session lama + perubahan email tanpa re-auth = ATO persisten.

Klasifikasikan temuan lo dengan apa yang ia **supply**, lalu cari tepi yang menyambung:

| Part | Yang ia beri penyerang |
|---|---|
| **K — Knowledge** | identifier / versi / schema |
| **A — Action** | server melakukan sesuatu atas nama lo |
| **B — Bypass** | menghapus cek yang memblokir hop berikutnya |
| **X — Amplifier** | primitif kecil → banyak / tampilan aktor lain |

Pola yang **terbukti** mencapai High/Critical:

```
B + X   missing rate limit (B) + account enumeration (B) + spray (A)  =  credential-stuffing ATO
K + B + A + X   error-leak (K) → unthrottled enumeration (B) → unverified email change (A)
                → IDOR/export amplification (X)                          =  mass ATO
K + A   version/stack leak (K) → CVE pada versi itu persis (A)          =  RCE
```

Prosedur (di **0E**, sebelum lapor ditulis): INVENTORY → LABEL → EDGES → SINK → PROVE → REPORT.
**Satu laporan rantai**, judul = impact terminal, severity = impact terminal.

Skill lengkap: `security/chain-to-impact` · `exploit-depth` (L0→L5) · `lead-to-critical`.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Session fixation: set cookie sebelum login, cek berubah setelah login | Rotasi wajib |
| 2 | Cookie scope: `Domain` terlalu luas, `Path` terlalu longgar | Pencurian lintas subdomain |
| 3 | Predictability: bandingkan beberapa session ID | Entropi rendah |
| 4 | Tidak invalidasi saat logout/ganti password | Sesi bertahan |
| 5 | Concurrent session: batasi perangkat? | Kebijakan sesi |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa memakai session ID korban yang tidak berubah setelah login" — tunjukkan akses yang didapat.
2. **Apa yang hilang dari korban?** Kontrol sesi/akun. Sebutkan data atau aksi yang bisa diambil.
3. **Bisa direproduksi 10 menit dari nol?** Gunakan dua browser/sesi; sertakan cookie (disedit) dan langkah.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** kuasai/hiasi sesi

**Teknik pengembangan:** fixation; no rotation post-login; cross-subdomain cookie

**Eskalasi ke:** `hunt-ato` · `hunt-idor`

**Depth target:** L3 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.



## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Session fixation; token tidak dirotasi setelah login; token masih valid setelah logout; cookie tanpa `HttpOnly`/`Secure`/`SameSite`; session di URL. Kalibrasi: token yang di-rotasi + invalidate di logout = correct; cookie flag hilang tapi token tidak bisa dicuri tanpa XSS = Medium.
