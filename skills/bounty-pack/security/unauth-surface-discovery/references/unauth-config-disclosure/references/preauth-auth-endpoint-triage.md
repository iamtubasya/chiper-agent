# Triaging auth/SSO endpoints found on the unauthenticated surface

Companion to Step 1b of this skill. Once the pre-auth SPA capture hands you the login/auth
surface, most of what it exposes is **not** reportable — but two shapes are easy to get wrong in
opposite directions. This is how to classify each one without overclaiming or missing a real bug.

## 1. Capability endpoints — NOT reportable

```
GET /auth
 -> 200 {"methods":[{"type":"password"},{"type":"require2FA"},{"type":"forgottenPassword"},
                     {"type":"otp"},{"type":"passcode"},{"type":"reissue"}],"prompt":null}
```

Reachable without credentials on 143/176 hosts in the worked case, but the body was
**byte-identical on every host** — verified by hashing the response across the census. It discloses
product capability, not tenant data. There is no "across tenant" angle because there is nothing
tenant-specific in it. Record it, list it under coverage, and do not file it.

Give it one line in the report anyway when it contradicts something else you found, e.g. the same
response advertising `require2FA` on hosts whose `/api/settings` says `"allow2FA": false`. That is
a posture inconsistency worth a sentence, not a finding.

**Test for the tell:** if the body is identical on all hosts, it is capability. If it varies per
host, it is configuration — and then it belongs with the main config finding.

## 2. Per-app config endpoints — same CWE as the main finding

```
GET /auth/spa/config?app=webmail          (or ?app=account-portal)
 -> 200 {"authorizeUrl":"https://login.junara.com/auth/authorize",
         "clientId":"webmail-junara","enable":true}
```

On 52/176 hosts unauthenticated, with genuinely per-tenant values (three distinct
`authorizeUrl`/`clientId` pairs plus a `{"authorizeUrl":"","clientId":"","enable":false}` default).

This is the **same class and the same data family** as the main `/api/settings` finding — that
payload already leaked `authUrl` / `logoutUrl` for the same tenants. Filing it separately invites a
duplicate closure; folding it in as "additional affected endpoint" strengthens the main finding and
widens the remediation. Rule of thumb: different endpoint, same root cause and same leak class →
one finding, several endpoints.

Note the per-app parameter: `?app=webmail` and `?app=account-portal` return different values, and
`?app=<anything else>` returns a whitelist rejection (`app must be webmail or account-portal`).
Enumerate the app values from the SPA's own calls rather than guessing, and check the 404/500
variants too — a host can answer `404 web domain not found` while a sibling answers
`500 web domain does not have a valid tenant id`, which is an internal-state differential only (no
data disclosed, not a finding).

## 3. `/authorize` — the open-redirect false positive

Driving `/auth/authorize` with 23 redirect_uri shapes (exact, `http://` downgrade, foreign domain,
`host.evil.example`, `hostevil.example`, `@`-userinfo both orders, subdomain injection, path
extension, `../`, `%2e%2e`, backslash, protocol-relative, triple-slash, CRLF, `data:`,
`javascript:`, port change, query/fragment injection, upper-case host, trailing dot, IDN) produced:

```
302  Location: /ui/auth/signin?client_id=webmail-junara&response_type=code
              &redirect_uri=https%3A%2F%2Fevil.example%2F&scope=openid+offline&state=…
403  (data:, javascript:, ../, %2e%2e)
```

**This is not an open redirect.** Two independent reasons, and you must check both before writing a
word:

1. The `Location` is a **relative path on the same host** — the browser never leaves the origin.
2. The attacker's value appears only as a **URL-encoded query parameter** being echoed to the
   signin page, not as the redirect destination.

A naive matcher that greps the `Location` for the attacker's domain fires on both and reports an
open redirect. Decode the query string before believing it. (Contrast with a real one: an absolute
`Location: https://evil.example/...` with the value *not* URL-encoded inside another parameter.)

## 4. What is genuinely testable pre-auth, and what is not

| Test | Meaningful result |
|---|---|
| drop `code_challenge` | `400 code_challenge is required` = PKCE enforced (good); `302` = PKCE optional (finding) |
| empty `response_type` | `400 response_type is required` = validated |
| `response_type=token` / `id_token token` | still `302` with no error = implicit flow not rejected (note it; not automatically reportable) |
| bogus `client_id` | still `302` = client_id not validated pre-login (not a finding on its own) |
| `redirect_uri` = `data:` / `javascript:` / `../` | `403` = coarse edge filter present |
| does the signin page SSR-reflect `redirect_uri`/`state`/`scope`? | marker absent in the shell = no reflection/XSS, dead end |
| `POST /auth/token`, `/auth/otp`, `/auth/revoke`, `/auth/reset-password` | `401`/`400`/`405` = correct; `200` with no session = finding |
| `GET /auth/sso?url=…` | constant `400` (1-byte body) for every parameter tried = no SSRF handle here |

**The hard boundary:** `redirect_uri` validation happens **after** authentication. If `/authorize`
only echoes parameters into the signin page, you cannot test the real match rule from the outside.
Write that as an honest limit — "validation occurs post-auth, untestable externally" — and claim
neither a pass nor a fail. Do not convert an untestable area into a finding.

## 5. Use the REAL client_id and redirect_uri

Harvest them from the pre-auth SPA's own `authorize` call (Playwright network capture) or from path
literals in the bundle. Testing with an invented `client_id` only proves the endpoint ignores
client_id; it does not exercise the `redirect_uri` allowlist for any real client. In the worked case
the two real pairs were `myaccount-junara → https://account.junara.com/` and
`webmail-junara → https://webmail.stg.junara.com/login/oauth` — each with its own IdP host, so both
had to be tested separately.

## 6. OOB check before you call an auth parameter an SSRF

Put the correlation domain into the parameters that could plausibly cause a server-side fetch —
`redirect_uri`, `url`, `returnUrl`, `webdomain`, `*` in autodiscover XML — and watch for callbacks.
88 probes across 8 hosts produced **0 callbacks** in the worked case, which is what lets you write
"tested for SSRF/OOB, negative" instead of leaving the area silently uncovered.

## 7. Scope check on anything an archive hands you

`gau`/Wayback output routinely mixes in historical URLs and unrelated registrants. In the worked
case it surfaced `zboard/*.php` paths on the **apex** domain of a brand that the program scoped as
`*.brand.com` — the apex was not covered, its registrar and name servers belonged to someone else,
and the URLs were years old. That is a third-party target: do not send a single request at it, and
say in the report that you saw it and left it alone. Same for `*.internal.<host>` names recovered
from archives — check DNS; NXDOMAIN today means no live surface, only an archive artefact.
