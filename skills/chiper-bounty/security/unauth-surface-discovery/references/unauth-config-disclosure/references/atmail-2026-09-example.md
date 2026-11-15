# Worked example — email-platform tenant config endpoint (2026-09)

Engagement: authorised bug-bounty program on a cloud email/webmail platform.
Endpoint class: `GET /api/settings` on every webmail and API-gateway host.

## What was found

- `GET https://<host>/api/settings` → **HTTP 200, JSON, no auth, no cookie**.
- Reachable on **121 of 155** probed in-scope hosts including **production** tenancies plus
  staging (the first pass under-counted at ~60; re-measure before writing the number).
- A second path reaches the identical payload: `GET /api/.well-known/jmap-settings` → **301** →
  `/api/settings`. `/api/settings/` (trailing slash) and `/api/setting` (singular) are 404.
- The login page genuinely needs this data pre-auth (theme, locale, password rules), so the
  *endpoint being public is intended*. The bug is what else is in the payload.

Leaked, per tenant:

| Value | Meaning |
|---|---|
| `googleDrivePickerConfig.devKey` — 39-char `AIza…` on two tenants, 24-char malformed on a third | Google API key |
| `googleDrivePickerConfig.appId` | OAuth client ID (`…apps.googleusercontent.com`) |
| `dropboxPickerConfig.appId` | Dropbox app key |
| `onedrivePickerConfig.appId` + `redirectUrl` | Azure/OneDrive application (client) ID |
| `authUrl` / `logoutUrl` | Customer SSO endpoints (partner IdP) — **including UAT / pre-production IdP hostnames** |
| `blockDuration` = **0** on 118 of 121 hosts (60 on 2, 3000 on 1) | vendor's own lockout setting — disabled by default |
| `metaSettings.passwordResetSettings.*` | reset-step copy, OTP resend text, throttle text |
| `endpoints.{uploadUrl,downloadUrl,eventSourceUrl,registerUrl}` | internal API map |
| `extensions.*`, `licenseValid`, `sessionExpirySeconds`, `defaultRealm`, `spamReportEmail`, full theme definitions | posture |

## Secret usability test (the honest part) — CORRECTED 2026-09-30

**The method originally written here was wrong and produced a false negative.** It probed the key
against Maps with the key in the `X-Goog-Api-Key` **header**:

```
GET https://maps.googleapis.com/maps/api/geocode/json?address=zzzz
X-Goog-Api-Key: <key>
→ 200 {"status":"REQUEST_DENIED","error_message":"You must use an API key to authenticate each
       request to Google Maps Platform APIs..."}
```

That reply is returned for **every** value — a real key, a malformed string, and even an empty
key all give the identical `REQUEST_DENIED`. It discriminates nothing, so the conclusion drawn
from it ("the key is real but restricted to a different API family") was unsupported.

**Correct procedure** — use the `key=` **query** form against an endpoint that actually validates
keys, and probe a negative control in the same run:

```
GET https://www.googleapis.com/drive/v3/files?key=<value>&pageSize=1
GET https://www.googleapis.com/drive/v3/files?key=<invented AIzaSy…>   # control
```

| Reply | Meaning |
|---|---|
| `400 INVALID_ARGUMENT — API key not valid.` | not a key at all (or masked/truncated) |
| `403 PERMISSION_DENIED — Requests from referer <X> are blocked.` | **key is REAL** — Google resolved it and applied its restriction |
| `403 — The user does not have sufficient permissions for this file.` | key accepted AND the Referer gate was satisfied |
| `403 — <API> has not been used in project <N> …` | key accepted; the response names the GCP project number |

The control is what makes the claim sound: only a real key can produce the *referer* error,
because an unknown key never gets that far. Measured result for this endpoint's three values:
pc3 `AIzaSyDn…` (39) = real, referer gate satisfiable with `Referer: https://pc3.atmailcloud.com/`,
Drive API enabled on project 463053038625; orchid `AIzaSyDe…` (39) = real but its referer
allowlist was **not** satisfiable with any value tried → reported as *not bypassed*; eu-west
`D9K5nA…` (24) = malformed. Correct report sentence:

> the key was probed once and returned a referer-restriction error that an invented control value
> did not, indicating it is a live Google API key for the tenant's Drive integration; the
> restriction is satisfiable by a caller-supplied `Referer` header. This is unauthorised
> disclosure of a live credential with a bypassable protection, **not** account takeover: no API
> enabled on the project returned data to an API-key-only caller.

**⚠️ Trap that made this hard to see:** the agent runtime's output-layer secret redactor renders a
39-char `AIzaSy…` key as an abbreviated string (`AIzaSy...PRgQ`) that looks exactly like a
product-side placeholder. Re-testing *that* string returns `400 API key not valid` for everything
and yields a confident, wrong "the keys are masked/inert" conclusion. Read the value from the
saved evidence file and print only `len()` + a hash — `len == 39` proves it was disclosed in full.

## How it was used as ground truth

The same response carried `"blockDuration": 0` on 118 of the 121 hosts that expose it (60 on two,
3000 on one; the admin-panel hosts do not expose the endpoint at all — they answer 502). That
converted a behavioural rate-limit observation (60 burst logins, no lockout) from "the control did
not fire during my test" into "the vendor's own configuration shows the control is **disabled
deployment-wide**". The behavioural burst alone is arguable; the leaked config value is not — but
state the distribution, not "every host".

## Two false-positive classes that looked like findings

### 1. Reflected hostname in a config error string
`/auth/spa/config?app=webmail` with `X-Forwarded-Host: <marker>.evil.example` echoed the marker
back inside a JSON error: `{"error":"web domain not found","details":["web domain
'<marker>.evil.example' not found in webmail settings"]}`. Frequently mis-reported as cache
poisoning or host-header injection. Killed by four checks:

- the attacker must set the header themselves (no upstream proxy sets it from user input);
- `Cache-Control: no-cache, no-store, must-revalidate` → nothing is cacheable;
- no `Location`, no `Set-Cookie` → no redirect, no session impact;
- the value is JSON-escaped → no XSS.

Verdict: documented negative, not a bug.

### 2. `/vendor/*.php` returning HTTP 200
Directory brute force reported `/vendor/autoload.php`, `/vendor/composer/*.php` as 200, which
looks like Composer dependency/source disclosure. It was **HTTP 200 with a 0-byte body** — PHP
was executing the files and producing empty output, not serving source. `/vendor/composer/installed.json`
and `/composer.lock` (the actually-interesting files) returned **403**. Always check the body
size and content-type before calling a 200 a disclosure.

## Cross-tenant and fleet-wide variants — see the deep-dive reference

The follow-up round tested the cross-tenant question three ways (parameter selection, path
suffix/traversal, and a Host-override matrix against a shared front end) and all three came back
negative, and it ran the methods/CORS/auth-bypass-header/query-flag/JMAP/endpoint-discovery
variants that also failed. That material lives in **`references/fleet-config-endpoint-deepdive.md`**
so this file stays the worked case and that one stays the method. Headline result: no cross-tenant
read, no tenant-existence oracle, no privilege gained — report it as per-tenant exposure
replicated fleet-wide, not as an isolation break.

## Reporting decision

- Filed as **CWE-200**, Medium (`AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` ≈ 5.3).
- One finding, listing the additional affected hosts inside it (same root cause, so separate
  reports would be closed as duplicates).
- Pre-empted the program's "informative" clauses by naming the concrete secret and stating it is
  not a version string or bare enumeration.
- Duplicate risk acknowledged: the settings endpoint itself had been seen in an earlier session
  on the same product, so the *new* value offered was the third-party credential leak, not the
  endpoint's existence.

## Transferable lessons

1. Count hosts and report the number — per-tenant leak means fleet-wide impact. Re-count on a
   later pass; this engagement's first figure (~60) was less than half the real one (121).
2. Always test the secret once and state the result honestly — but make sure the probe can
   actually discriminate (negative control in the same run), and never re-test a value you read
   off rendered output, because the runtime's own secret redaction will feed you a fake.
3. A config endpoint is also evidence for unrelated findings; scan it for lockout/throttle/MFA
   keys and use them as ground truth. Refine the distribution before quoting it
   (`blockDuration` was "0 on every host" in the first draft; it is 0 on 118/121, 60 on 2,
   3000 on 1, and not exposed at all on the admin-panel hosts which 502 the endpoint).
4. Rule out cross-tenant access explicitly before claiming it, and record the negatives — a
   triager who suspects you stretched will ask for exactly that evidence.
5. Watch for an **alias path** to the same payload (`.well-known` redirect, trailing slash,
   `.json`): the remediation has to cover every route, and it is a cheap way to strengthen a
   duplicate-risky finding.
6. Two of the three strongest-looking candidates here were false positives. Check body size,
   cache headers, and who controls the input before writing anything up.
