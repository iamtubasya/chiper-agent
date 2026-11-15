# Worked case 2 — deep-dive round on the same email-platform config endpoint (2026-09-30)

Follow-up engagement to `atmail-2026-09-example.md`, on the same product (`/api/settings`).
Kept because it is the round where the *method* got fixed, not just the finding.

## What the deep dive changed

| Axis | Prior round | Deep-dive round |
|---|---|---|
| Hosts returning config | 63 | **121 of 155 probed** (the earlier count was hosts-yielding-secrets, not hosts-yielding-config) |
| Paths | `/api/settings` | plus **`/api/.well-known/jmap-settings` → `301` → `/api/settings`** (alias discovered by grepping the pre-auth SPA bundle) |
| Credentials | Google key + OAuth client ID + Dropbox app ID | plus **an Azure/OneDrive application (client) ID + redirectUrl** |
| Internal topology | SSO endpoints | plus **non-production IdP hostnames** (`onepass.uat3.test.aws.singtel.com`, `web-uat.csso.app.vic`) |
| Cross-tenant | asserted untestable | **tested three ways, all negative** |

## The reusable probes

**Bundle mining finds the aliases.** `/api/.well-known/jmap-settings` was not guessed — it appeared
as a string literal in the pre-auth webmail bundle, next to `/api/settings`. Grep every JS bundle
the login page loads for `"/[a-z.0-9/_-]{4,60}"` and diff against your known paths; JMAP/SPA
products alias their config endpoint in several places.

**Cross-tenant ruling-out battery** (all three are cheap; run all three so the negative is strong):

1. *Parameter selection* — 6 caller hosts × 5 other-tenant hostnames × 24 names
   (`webdomain, webDomain, domain, tenant, tenantId, host, hostname, realm, defaultRealm, server,
   id, account, accountId, user, email, site, vhost, webmail, customer, org, organisation, groupId,
   sid`) = 720 requests. Hash each body; compare against the caller's own baseline. Result: 0 changes.
2. *Path suffix/traversal* — `/api/settings/<tenant>`, `/api/<tenant>/settings`, `//`, `/./`, `%2f`,
   `..;/`, case variants, `.json`.
3. *Host-header selection on a shared front end* — resolve one host to its IP, then replay with a
   different `Host:` per request.

The Host-override matrix is where the real answer lives. Resolve the front end first
(`socket.gethostbyname`), then send `Host: X` to that IP:

```
Host: <a webdomain registered on that node>  -> that tenant's own config   (try every known host)
Host: <a real tenant NOT on that node>       -> NEUTRAL DEFAULT config
Host: zz-nonexistent-9912.<domain>           -> NEUTRAL DEFAULT config  (same MD5 as the row above)
Host: attacker.example                       -> NEUTRAL DEFAULT config  (same MD5)
```

Dump the fallback config in full before calling it neutral: the one here had `theme: "default"`,
three stock vendor-authored themes, zero credentials and zero foreign hostnames — genuinely
neutral. Two real conclusions fall out of the identical MD5: **no cross-tenant read** and
**no tenant-existence oracle**. Report it as per-tenant exposure replicated fleet-wide.

Note the asymmetry that looks like a finding and is not: a caller *can* fetch any tenant's config
by naming that tenant's public hostname — the same data that hostname serves directly. No
privilege gained. Say that out loud in the report before a triager says it for you.

## The redaction trap (cost a full false conclusion)

The endpoint returned full-length 39-char `AIza…` keys. The runtime's output-layer secret redactor
rendered them in tool output as `AIzaSy...PRgQ` — indistinguishable from a product-side mask.
Re-testing that redacted string gave `400 API key not valid` for every probe, which produced a
brief "the keys are inert, withdraw the credential claim" correction. It was wrong.

Fix, and the only reliable one: read the value **from the saved file** and print `len()` +
`sha256` prefix. `len == 39` means the key was disclosed in full. A redacted *display* never
changes the response's byte count either — cross-check `len(response.content)`.

Corollary for the report: a key whose length does **not** match the provider's format should be
described as "malformed or masked", never as live, and a key whose referer allowlist you could not
satisfy must be reported as **restriction not bypassed** rather than quietly folded into the
"bypassable" claim.

## Negative-control result that survived review

```
KEY                                  no Referer                                   Referer: <tenant host>
pc3  AIzaSyDn… (39)                  403 PERMISSION_DENIED: referer <empty> blocked   403: user does not have
                                                                                     sufficient permissions  <- GATE PASSED
orchid AIzaSyDe… (39)                403 referer <empty> blocked                     403 referer … blocked    <- NOT satisfied
eu-west D9K5nA… (24)                 400 INVALID_ARGUMENT: API key not valid         400 API key not valid
CONTROL (AIzaSy + 33×A)              400 INVALID_ARGUMENT: API key not valid         400 API key not valid
```

`drive/v3/files` answering at the project layer (`The user does not have sufficient permissions…`)
means the Drive API is enabled on project `463053038625`; `books|youtube|translate|customsearch`
answering `has not been used in project 463053038625 before or it is disabled` means they are not.
That is the honest ceiling: key accepted, API enabled, **no data returned to an API-key-only
caller** → CVSS `C:L`, not `C:H`.

## Other negatives worth reusing (so you do not re-run them blindly)

- **Methods** on a config endpoint: only GET. No write path ⇒ no stored-XSS chain via the tenant's
  `advertisingConfig` / `maintenance` HTML.
- **CORS**: ACAO reflecting an arbitrary `Origin` (and `null`) on 4 hosts, but
  `Access-Control-Allow-Credentials` never sent and no session cookie involved ⇒ not exploitable.
  Do not report origin reflection alone.
- **Auth-bypass headers** against 17 sibling protected endpoints (`X-Original-URL`, `X-Rewrite-URL`,
  `X-Forwarded-For: 127.0.0.1`, `X-Real-IP`, `X-Client-IP`, `X-Originating-IP`,
  `X-Custom-IP-Authorization`, `X-HTTP-Method-Override`) plus path manipulation
  (`//api/x`, `/api/./x`, `/API/x`, `/api/%61dmin`, `..;/`, trailing `?`/`#`, `.json`): 0 changes.
- **Query flags** (`debug, full, raw, all, admin, expand, pretty, internal, verbose,
  includeSecrets, version, format, include, detailed, showHidden`): byte-identical, no "expanded" mode.
- **JMAP** `POST /api/jmap` with `getSettings`/`Core/echo`/`Session/get`/`Mailbox/get`/`Account/get`
  + `X-JMAP-Extensions`: 401 each. `/api/.well-known/jmap`: 200 with a **0-byte** body.
- `/auth/password-policy`: 401. `/auth/spa/config?app=`: `app` is whitelisted and the hostname
  reflection is JSON-escaped, 404, `no-cache` ⇒ not exploitable.
- **Edge WAF**: 40 concurrent connections ⇒ uniform `403 Forbidden` (nginx, 118-byte body),
  transient and per-source. That is why the first ffuf run reported 5152/5152 × 403 — block pages,
  not results. See `bot-protected-target-testing` §3a. Sequential/`curl` traffic was never affected.
