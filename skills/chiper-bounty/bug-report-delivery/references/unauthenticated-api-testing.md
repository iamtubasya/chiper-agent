# Unauthenticated API Testing Techniques (when signup is CAPTCHA-blocked)

When Turnstile/reCAPTCHA blocks every account-creation channel (direct form, OAuth/SSO, WHMCS register,
headless browser), pivot to unauthenticated vectors. These techniques found real issues on DuoCircle
(2026-10-26) without any account.

## 1. API Auth Mechanism Discovery (header fuzzing)

Before testing injection or bypass, find WHICH header the API actually checks. Send the same request with
different auth header names and compare responses:

```
X-API-Key: test       -> 401 "Authentication Required"   (header ignored)
X-Auth-Token: test    -> 401 "Key test not found."        (header IS checked!)
Authorization: Bearer test -> 401 "Authentication Required"
```

The response body difference ("Key X not found" vs "Authentication Required") reveals the real auth header.
Once found, all subsequent injection/bypass tests target that header.

## 2. Type Juggling in Auth Tokens (PHP/Symfony APIs)

PHP falsy values in auth headers can crash or bypass middleware. Test these exact strings:

| Value | Expected | What it means |
|---|---|---|
| `0` | 500 = type juggling crash | Falsy string not handled in key lookup |
| ` 0` / `0 ` | 500 = trim-then-compare | Whitespace trimmed before falsy check |
| `00` | 401 normal | Not falsy |
| `0.0` | 401 normal | Not falsy |
| `false` | 401 normal | String "false" is truthy in PHP |
| `null` | 401 normal | String "null" is truthy in PHP |
| `%30` | 401 normal | URL-encoded "0" decoded after check |

Only the exact string `0` (with optional surrounding whitespace) triggers the crash. This is a genuine
bug — unauthenticated 500 on all endpoints — even if low severity alone.

**Escalation path:** if the auth code uses loose equality (`==`) anywhere, type juggling can potentially
bypass auth entirely. Test with values like `0`, `false`, `null` in JSON bodies and query params too,
not just headers.

## 3. Version-Changelog CVE Hunting

When you fingerprint an outdated software version (via swagger, docs, or headers), check the upstream
changelog for security fixes between the deployed version and latest:

```bash
# Get the changelog
curl -s https://raw.githubusercontent.com/<org>/<repo>/master/CHANGELOG.md

# Or the releases API (rate-limited without auth)
curl -s "https://api.github.com/repos/<org>/<repo>/releases?per_page=10"
```

Look for commits with `security`, `fix: close`, `harden`, `auth bypass`, `cross-account`, `IDOR`, `SSRF`
in the message. Each security fix between the deployed version and latest is a candidate vulnerability.

**Live example (EmailEngine):** target ran v2.81.2, latest was v2.86.0. Changelog revealed security fixes
in 2.82-2.84:
- "close the paths a bound or narrowed API token could use to reach other accounts" (cross-account access)
- "keep account ids apart in Redis keys and URLs" (IDOR)
- "harden the IMAP proxy and the SMTP listener against unauthenticated clients" (auth bypass)
- "keep the global webhook headers off account-level targets" (credential leak)
- "route API account HTTP traffic through the account proxy" (SSRF)

All required auth to exploit, but the version gap itself is worth reporting as a secondary observation.

## 4. Falsy-Value Probing on Any Parameter

The type juggling technique generalizes beyond auth headers. Test `0`, `false`, `null`, `[]`, `{}` on:
- Path parameters (`/v1/services/0`)
- Query parameters (`?id=0`)
- JSON body fields (`{"id": 0}`)
- Array-style params (`?id[]=0`)

A 500 on any of these indicates unhandled type coercion. A 200 with unexpected data indicates a potential
auth bypass or logic flaw.

## 5. Health/Status Endpoint Recon

Health endpoints are often unauthenticated and leak infrastructure details:

```
/health  -> {"status":"ok","checks":{"database":true,"redis":true}}
/status  -> {"status":"up"}
/up      -> Rails health check
```

Not payable alone (info disclosure of framework metadata is excluded by most programs), but useful for:
- Confirming the tech stack (database type, cache layer)
- Finding endpoints that skip auth middleware (test if `/doc` or `/health` crashes with type juggling —
  if it doesn't, the auth middleware is route-scoped, not global)
