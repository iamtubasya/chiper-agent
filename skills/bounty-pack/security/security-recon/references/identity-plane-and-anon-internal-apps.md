# Identity plane + anonymous internal apps — the surface passive enum never finds

Source engagement: Genians bug bounty (2026-10). Lesson that produced this file: **crt.sh-only
enumeration returned 45 hosts and missed the entire identity/infrastructure plane.** Everything below
was found only after a DNS wordlist brute (Step 1b).

---

## 1. What the brute found that CT never would

| Host | What it was | Why CT missed it |
|---|---|---|
| `tech.<apex>` | **Jira Server 9.12.4**, directly exposed, no gateway | no unique publicly-logged cert |
| `sso.<apex>` | Atlassian **Crowd SSO** behind AWS API Gateway | shares a wildcard/CDN cert |
| `auth.my.<apex>` | **second Keycloak**, 3 live realms | found only via a leaked `redirect_uri`, not enum at all |
| `partner.<apex>` | partner portal with its own OIDC client | wildcard cert |
| `api.<apex>` / `dashboard.my.<apex>` / `sase.my.<apex>` | additional app origins | wildcard cert |
| `logs` / `monitor` / `pi` / `dl` / `download` | 403 Apache originals | — |

Brute cost: 836 candidates, 30 threads, ~6 seconds. There is no reason to skip this.

---

## 2. Discovery patterns worth reusing

### 2a. An IdP realm you didn't know existed leaks out of a downstream app's redirect

The `auth.my.<apex>` Keycloak was never enumerated. It surfaced because the partner portal's OIDC login
leg 302'd and the `Location` header named it in full:

```
GET https://partner.<apex>/public/keycloak/<product>/oidc/login
  -> 302 Location: https://auth.my.<apex>/realms/ztna-sase/protocol/openid-connect/auth
       ?response_type=code
       &redirect_uri=https%3A%2F%2Fpartner.<apex>%2Fpublic%2Fkeycloak%2Fztna-sase%2Foidc%2Fcallback
       &client_id=client-partnerportal-oidc
       &nonce=...&state=...&scope=openid
```

That single 302 gives you: **IdP host, realm name, `client_id`, and the exact registered
`redirect_uri`** — the three inputs every authorize-endpoint test needs. Always drive the first auth hop
and read `Location` (same technique as Step 5c for NextAuth apps).

Then probe realms by name — Keycloak returns 200 with a `public_key` JSON body on a live realm and
404 on a dead one, so realm existence is enumerable:

```bash
for r in <product> partner master csm sase ztna genians admin; do
  printf '%-12s ' "$r"
  curl -sk -o /dev/null -w '%{http_code}\n' "https://<idp>/realms/$r"
done
```
Measured: `ztna-sase` 200, `partner` 200, **`master` 200** (realm-admin), everything else 404.
`master` being reachable is worth flagging but is *not* a finding by itself — you still need creds.

Realm config is public: `/realms/<r>/.well-known/openid-configuration` gives `grant_types_supported`
(watch for `password`, `device_code`, `token-exchange`, `uma-ticket`), `code_challenge_methods_supported`
(watch for `plain`), `registration_endpoint` (DCR present?), and `scopes_supported` (watch for
`delegation:client` / `delegation:user` = impersonation surface).

### 2b. `redirect_uri` — run the full 14-variant set before believing it's loose

Naive testing passes on the happy path and proves nothing. The set that actually separates a strict
validator from a loose one:

```
legit-exact                    trailing-slash
evil-host                      query-append
suffix-dot  (<legit>.evil.tld) fragment-append
at-sign     (<legit>@evil.tld) case-variant (Https://)
path-traversal (/../../..)     null-byte (%00.evil.tld)
non-standard-port              scheme-relative (//evil.tld)
localhost                      wildcard-sub (sub.<legit>)
```
Measured on the Keycloak above: **all 13 non-exact variants → HTTP 400**, exact → 200. Clean negative.
Write that negative down; it is what stops a later session re-testing.

### 2c. DCR endpoint can be *present* and still unusable

`registration_endpoint` appeared in discovery and the endpoint parsed a malformed body with a genuine
Keycloak schema error (`Unrecognized field "directAccessGrantsEnabled"`), i.e. it is live — but every
well-formed registration came back **403 with the target's own branded error page**, which is the WAF,
not Keycloak. Distinguish the two by the response body: a Keycloak JSON schema error means you reached
the app; a branded `<!doctype html>…Not Found` page means the edge dropped you. Don't record "DCR open"
on the strength of the schema error alone.

---

## 3. Jira Server — one-request anonymous exposure checks

`GET /rest/api/2/serverInfo` is unauthenticated by design on Jira Server and returns
`version` / `versionNumbers` / `buildNumber` / `buildDate` / `deploymentType`. Use it as the version gate
*before* spending time on CVEs.

What answered **200 unauthenticated** on a real Jira Server 9.12.4:

| Endpoint | Result |
|---|---|
| `/rest/api/2/dashboard` | **200 — total=18, full internal dashboard names** |
| `/rest/api/2/serverInfo` | 200 — version + build |
| `/rest/applinks/1.0/manifest` | 200 — app id, versions, inbound/outbound auth providers incl. `TwoLeggedOAuthWithImpersonation` |
| `/rest/api/2/statuscategory` | 200 |
| `/secure/QueryComponent!Default.jspa` | 200 — ~33 KB field metadata |
| `/secure/ContactAdministrators!default.jspa` | 200 — contact-admin form |

What correctly returned **401/empty** (record these as negatives):
`/rest/api/2/user/search`, `/rest/api/2/user`, `/rest/api/2/field`, `/priority`, `/resolution`,
`/configuration`, `/auditing/record`, `/projectCategory`, `/permissionscheme`,
`/rest/api/latest/issue/<KEY>-1`, `/rest/api/2/filter`.
`/rest/api/2/project` → `[]` and `/rest/api/2/search?jql=…` → `total:0` for anonymous: a Jira with no
anonymous-browsable projects still leaks **dashboard names**, which name teams and processes
(SLA / TS-Partner / Weekly-NAC / CAM-OG …).

### Reporting ring-fence for this finding
Dashboard-name disclosure is **real, reproducible (3/3, `--no-sessionid`, no Authorization header) but
Low**. Many programs' exclusion lists explicitly bar "server application information exposure" and
"version disclosure", so a report that leads with `serverInfo` gets closed. Lead instead with the
*business* artefact — internal dashboard/project/process names — and state the absence of PII/issues
honestly. Do not inflate to Medium on the strength of `applinks` auth-provider names.

---

## 4. Gateway-fronted SSO (AWS API Gateway + Lambda)

Signature: every path returns `{"message":"Missing Authentication Token"}` (API Gateway's own 403) while
one or two paths resolve. Sweep paths and keep only the non-403s — here `/login` (200, the SSO UI) and
`/ping` (`healthy`).

Notes that generalise:
- Rate-limit kicks in after ~30 rapid requests and the whole host starts returning `{"message":"Forbidden"}`.
  Back off ~20 s, or drive it through a real browser context, before concluding a path is gone.
- The login response can carry a **framework `DEBUG` block** naming the backend
  (`version_server":"bp_lambda_<svc>_<build>","WORKING_ENV":false,"__type":"login"`). That fingerprint
  recurs across the vendor's products — the same `__type`/`__action`/`memory_usage` shape appeared on
  their public PI API. It confirms a shared internal framework, which is worth noting for a later
  dispatcher test, but the `DEBUG` object reflects **server constants only**: injecting
  `__type=`/`__action=` in the request had zero effect. Test it once, don't dwell.
- Crowd SSO login form fields are an attack-surface map in themselves:
  `loginid, password, step=1, redirectTo` · `authcode, step=2, cookie, client_ip` ·
  `step=pwd_chg` (+cookie) · `step=pwd_reset` (loginid+name+email+phone).
  `cookie` being **client-supplied and required** at `step=2` ("Login failed! No cookie!") is a genuine
  lead for 2FA-token forgery/replay — but proving it needs one valid step-1 cookie, so it stays a lead,
  never a report.

### What turned out clean here (don't re-test, cite this)
- `redirectTo` reflected into HTML → correctly entity-encoded; `</script>` closed properly as `<\/script>`;
  11 XSS payloads all inert; **no open redirect** (server never uses it for redirect, only echoes it).
- `loginid` echoed into the JSON error message → tags **stripped**, no XSS.
- Non-existent `step=<anything>` values → JSON with `DEBUG` only, no behaviour change. Unknown steps are
  inert; only 1 / 2 / pwd_chg / pwd_reset do anything.

---

## 5. Cross-product auth chain to look for

The high-value observation from this engagement was **not** any single bug — it was the topology:

```
partner.<apex>  --OIDC-->  auth.my.<apex>/realms/<product>     (Keycloak)
sso.<apex>      (Crowd + Lambda) --> tech.<apex>/jira           (internal SLA/TS/partner data)
```

One identity plane gates both the partner-facing portal and the internal ticketing system. That makes
the IdP — not the product instance — the right place to spend the next session, and it reframes a
"Low" info leak into "this is the perimeter that protects SLA/partner data".
