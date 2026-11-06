---
name: hunt-auth-bypass
description: Hunting skill for auth bypass vulnerabilities. Built from 12 public bug bounty reports across SAML XSW / parser-differential (GitHub Enterprise CVE-2025-25291/25292), SAML signature stripping (Uber, Rocket.Chat, samlify CVE-2025-47949), SAML domain enforcement bypass via control characters (HackerOne 2024), partner-portal cross-IdP assertion reuse (Slack), WordPress XMLRPC bypassing SSO (Uber), JWT alg-confusion HS256/RS256 (Jitsi), JWT signature-validation skip (Linktree, Newspack), and token-audience confusion (Argo CD CVE-2023-22482). For standalone JWT signature/crypto forging (alg:none, key confusion, kid/jku) see hunt-jwt-crypto; this skill covers JWT only inside SSO/SAML/token-trust bypass chains. SAML assertion-layer attacks (XSW, comment injection, signature stripping, XXE-in-assertion) are owned by hunt-saml; this skill owns the broader cross-protocol auth-bypass taxonomy. Use when hunting auth bypass — see the Legacy-Protocol Matrix for branded-UI vs legacy-endpoint patterns.
sources: github, hackerone_public, github_security_lab, projectdiscovery_research
report_count: 12
---
> **appsec-fyi supplement (source-cited, 2026 CVEs):** `references/appsec-fyi-techniques.md` —
> additive per-class technique list from https://appsec.fyi. Owner methodology below still wins.

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §E/§F): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`

> **Home-grown token schemes (app ships an open-source client) + fail-open IPC auth (CWE-636):**
> `references/custom-token-auth-testing.md` — recover the token/registration scheme from the client
> source, self-provision an account, then matrix-test the trust model (is `pubkey` caller-supplied
> and unbound?), the authz binding (path id vs token subject = BOLA), and entitlement/mass-assignment.
> Also: diagnosing a **canned** static error (identical `codeReferenceId` across inputs *and* hosts)
> vs edge caching, and the client-side "auth skipped when self-signature can't be verified" pattern.

> **Wallet-signed API requests (EIP-712 / Web3Signed / EIP-3009) — attack the BINDING, not the crypto:**
> `references/eip712-signed-request-binding-tests.md` — recover the typed-data scheme from the shipping client
> (each feature has its OWN `verifyingContract`), mint signatures locally with `eth_account` from a throwaway key,
> then walk the binding matrix: declared-owner vs recovered-signer, body-swap, delegate/server authority scoped to
> one owner, publicKey↔address, monotonic `grantVersion` nonce, capability-secret entropy, unauthenticated status
> reads. Includes the canonical-body-hash trap (bare hex vs `sha256:` prefix, sorted-keys JSON) and the list of
> signed-request behaviours that are NOT findings so they get written down as verified negatives instead.


## Crown Jewel Targets

Auth bypass is consistently one of the highest-paying vulnerability classes in bug bounty because it directly violates the most fundamental security control. High-value targets include:

- **SSO/SAML implementations** at enterprise SaaS companies (Slack, Okta, OneLogin integrations) — payouts regularly in the $5K–$25K+ range
- **Admin panels and partner/internal portals** — subdomain-separated admin surfaces like `partners.shopify.com`, `admin.company.com`
- **Third-party auth plugin integrations** — WordPress plugins (OneLogin, WP-SAML-Auth), Drupal SSO modules, any CMS with pluggable auth
- **XMLRPC endpoints** on WordPress — often forgotten, bypasses standard WP auth flows entirely
- **OAuth callback flows** — state parameter mishandling, redirect_uri mismatches
- **API authentication layers** — especially where auth was bolted on after the fact

**Asset priority:** Targets with federated identity (SAML, OAuth, OIDC) connected to large user populations. Partner/reseller portals are particularly juicy because they often have elevated permissions and less security scrutiny than the main product.

---

### SSH certificate-authority trust forgery (Git-hosting / enterprise platforms)
When an org or instance registers an SSH certificate authority, cert `principals` may not be bound server-side to the requesting identity — a member can mint a cert asserting another user's principal and authenticate as them (e.g. modify another user's resource given only its URL). Add SSH-CA trust to the auth-surface list on Git-hosting targets; niche/platform-specific. Disclosed: reports/1901040.

## Attack Surface Signals

**URL patterns to hunt:**
```
/xmlrpc.php
/wp-login.php
/saml/
/sso/
/auth/saml/callback
/oauth/callback
/partners.*
/admin.*
/?wc-api=
/api/v*/auth
/login?redirect=
/accounts/login
```

**Response headers signaling SSO:**
```
X-Frame-Options: SAMEORIGIN (common on SSO portals)
Set-Cookie: SAMLResponse=
Location: https://idp.company.com/saml
WWW-Authenticate: Bearer realm="partners"
```

**JS patterns indicating federated auth:**
```javascript
// Look for in page source
samlRequest
RelayState
SAMLResponse
onelogin
shibboleth
okta
passport.js authenticate
```

**Tech stack signals:**
- WordPress + any SSO plugin → check XMLRPC separately
- Shopify Partner API exposure → cross-tenant privilege escalation risk
- Any app advertising "SSO enabled" or "Login with [Enterprise IdP]"
- Separate subdomains for admin/partner that share session cookies with main domain
- Applications using `SimpleSAMLphp`, `ruby-saml`, `python-saml`

**Burp passive scan triggers:**
- `SAMLResponse` in any POST body
- `openid_connect` or `id_token` in responses
- Cookie domains set to `.company.com` (wildcard)

---

## Step-by-Step Hunting Methodology

1. **Map all authentication entry points**
   - spider the target for every login surface: main login, admin login, API login, partner portal, mobile API endpoints
   - check `robots.txt`, JS files, and the wayback machine for forgotten endpoints like `/xmlrpc.php`

2. **Identify the auth mechanism per entry point**
   - Is it forms-based, SAML, OAuth, API key, session token?
   - For WordPress: always probe `/xmlrpc.php` even if the main login is SSO-protected

3. **Test XMLRPC independently of SSO**
   - If site uses SSO (e.g., OneLogin), manually POST to `/xmlrpc.php`
   - XMLRPC uses WordPress-native credentials, not SSO — test with `system.listMethods` first, then `wp.getUsersBlogs`

4. **Enumerate SAML implementation**
   - Capture a valid SAMLResponse via Burp
   - Decode the Base64 payload, inspect the XML
   - Test signature stripping, comment injection, and XML wrapping attacks
   - Test if SP validates the signature at all (send unsigned assertion)

5. **Test cross-portal session/token reuse**
   - Log into `partners.shopify.com` type portals
   - Attempt to use the issued token/cookie against the main admin portal
   - Look for shared cookie domains, shared JWT secrets, or API tokens that work across contexts

6. **Fuzz auth parameters**
   - Null/empty passwords, `password[]=array`, SQL in username field
   - Try `admin`/`admin`, `test`/`test` on staging subdomains
   - Modify `role`, `is_admin`, `user_type` in JWTs (none algorithm, weak secret)

7. **Check redirect and state parameters**
   - Does removing `state` from OAuth break anything?
   - Can you change `redirect_uri` to an open redirect target?
   - Does the `RelayState` in SAML get validated?

8. **Verify impact by escalating privileges**
   - Don't stop at login — prove you can access admin functions, other users' data, or sensitive configuration
   - Screenshot the highest-privilege action you can perform

---

## Legacy-Protocol Matrix (Probe These First on Any Custom-Branded Login)

When a target has a custom, branded login UI (e.g. `customlogin.aspx`, `/auth/signin`, `/account/login`), **always probe the platform's legacy protocol endpoints with native credentials** in parallel. These endpoints frequently outlive the custom UI's protections and accept native credentials with NO rate limit, NO MFA challenge, NO CAPTCHA, NO anti-automation. This is the WordPress XMLRPC pattern generalised across CMS / portal / framework stacks.

| Target tech | Legacy endpoint(s) to probe | Native-cred bypass surface |
|---|---|---|
| **WordPress** | `/xmlrpc.php` (`system.listMethods`, `wp.getUsersBlogs`, `system.multicall`) | Native WP user/pass; bypasses SSO, MFA, IP-allow rules on `/wp-login.php` |
| **WordPress (REST)** | `/?rest_route=/wp/v2/users`, `/wp-json/wp/v2/users` | User enumeration anonymously even when login page is hardened |
| **SharePoint (any version)** | `/_vti_bin/Authentication.asmx` (`Mode` + `Login` SOAP ops) | Native Forms-auth credential; FedAuth cookie returned; no rate limit on this endpoint observed on SP2013 farms — **this is the canonical SP equivalent of the WP XMLRPC bypass** |
| **SharePoint legacy** | `/_vti_bin/_vti_aut/author.dll`, `/_vti_bin/_vti_adm/admin.dll`, `/_vti_bin/owssvr.dll` | FrontPage RPC; sometimes still wired to credential validators |
| **SharePoint REST** | `/_api/contextinfo` (POST), `/_api/$metadata` | Anonymous FormDigest issuance; full API surface enumeration |
| **Atlassian (Jira / Confluence)** | `/rest/auth/1/session` (basic-auth), `/rest/api/2/myself`, legacy `/rest/api/1.0/` | Native credentials accepted on `/rest/auth/1/session` even when Atlassian Crowd / Atlassian Access SSO is enforced on the UI |
| **Drupal** | `/jsonapi/`, `/user/login?_format=json` | JSON POST endpoint that accepts native passwords; separate from SSO middleware |
| **Drupal (D7 legacy)** | `/?q=user/login`, `/services/`, `/rest/` | Older REST modules with independent auth |
| **Joomla** | `/administrator/index.php?option=com_login`, `/api/index.php/v1/users` | Native Joomla credentials accepted on admin entry independent of any front-site SSO |
| **Exchange / OWA** | `/EWS/Exchange.asmx`, `/Autodiscover/Autodiscover.xml`, `/Microsoft-Server-ActiveSync` | NTLM / Basic; bypasses OWA UI restrictions (MFA, IP-allow). The classic CVE-2020-0688 / CVE-2021-26855 surface |
| **Citrix NetScaler** | `/vpn/index.html`, `/cgi/login`, `/nf/auth/doAuthentication.do` | Native AD credentials; independent of MFA wrappers |
| **F5 BIG-IP** | `/mgmt/tm/util/bash`, `/tmui/login.jsp` | Native admin credentials |
| **Generic ASP.NET app** | `*.asmx?WSDL`, `*.svc?WSDL`, `trace.axd`, `elmah.axd`, `.disco` | Find every web service; many take credentials independently of the WebForms login |
| **Spring Boot** | `/actuator/*`, `/management/*`, `/api/v1/auth/login`, `/api/v1/swagger-ui` | Actuator endpoints sometimes anonymously enumerable |
| **Jenkins** | `/jnlpJars/jenkins-cli.jar`, `/script`, `/manage`, `/computer/(master)/script` | API tokens + native auth |
| **GitLab** | `/api/v3/*` (deprecated but still on old installs), `/api/v4/users`, `/api/v4/projects` | Personal Access Tokens with looser scoping than UI session |
| **TeamCity** | `/app/rest/users`, `/login.html?username=&password=` (GET-form-login) | Native admin credentials |
| **Apache Tomcat** | `/manager/html`, `/host-manager/html`, `/manager/text/list` | Native Tomcat realm credentials independent of any front auth |
| **WebLogic** | `/console/login/LoginForm.jsp`, `/wls-wsat/*` | Native admin |
| **Oracle EBS / PeopleSoft** | `/OA_HTML/AppsLogin`, `/psp/*/?cmd=login` | Native ERP credentials |

**How to use:**
1. Identify the tech stack from headers + paths (use `hunt-misc` Attack Surface Signals).
2. Find the row above that matches.
3. Probe the legacy endpoint anonymously to confirm it's reachable and not 403/404.
4. Test with synthetic credentials to confirm it accepts native credential format and returns differential responses (success vs failure).
5. Verify there is no rate limit, no lockout, no CAPTCHA — burst 10 requests at the same user, confirm uniform timing.
6. Report as **Critical / High** depending on chain to ATO: an anonymous + unlimited credential brute-force endpoint is consistently Critical on bug-bounty programs.

**Lesson from a authorized engagement:** A an enterprise dealer portal on SharePoint 2013 had a custom branded `customlogin.aspx`. The hunt-auth-bypass skill was loaded but the matrix above did not exist in this document — and the WordPress XMLRPC pattern was not connected to the SharePoint equivalent. `/_vti_bin/Authentication.asmx` was reachable anonymously, accepted unlimited credential attempts with no rate limit and no lockout, and was the highest-impact finding in the engagement. Walking this matrix on the first pass would have surfaced it immediately.

---

## Payload & Detection Patterns

**XMLRPC auth probe (bypasses SSO):**
```bash
curl -s -X POST https://target.com/xmlrpc.php \
  -H "Content-Type: text/xml" \
  -d '<?xml version="1.0"?>
<methodCall>
  <methodName>system.listMethods</methodName>
  <params></params>
</methodCall>'

# If 200 with method list → XMLRPC is enabled, test auth:
curl -s -X POST https://target.com/xmlrpc.php \
  -H "Content-Type: text/xml" \
  -d '<?xml version="1.0"?>
<methodCall>
  <methodName>wp.getUsersBlogs</methodName>
  <params>
    <param><value><string>admin</string></value></param>
    <param><value><string>password</string></value></param>
  </params>
</methodCall>'
```

**SAML signature stripping (send unsigned assertion):**
```python
import base64, re

# Decode captured SAMLResponse
saml_b64 = "BASE64_FROM_BURP"
saml_xml = base64.b64decode(saml_b64).decode()

# Strip the Signature element entirely
stripped = re.sub(r'<ds:Signature.*?</ds:Signature>', '', saml_xml, flags=re.DOTALL)

# Re-encode and submit
print(base64.b64encode(stripped.encode()).decode())
```

**SAML XML comment injection (username confusion):**
```xml
<!-- Original NameID -->
<NameID>attacker@evil.com</NameID>

<!-- Injected to confuse parser -->
<NameID>attacker@evil.com<!---->.victim@company.com</NameID>

<!-- Or namespace confusion -->
<NameID xmlns:evil="http://evil.com">victim@company.com</NameID>
```

**Partner/cross-portal token reuse test:**
```bash
# Get token from partner portal
TOKEN=$(curl -s -X POST https://partners.target.com/login \
  -d 'email=attacker@test.com&password=pass' \
  -c cookies.txt | grep -o 'token=[^;]*')

# Replay against admin portal
curl -s https://admin.target.com/dashboard \
  -H "Authorization: Bearer $TOKEN" \
  -H "Cookie: $TOKEN"
```

**JWT none algorithm attack:**
```python
import base64, json

header = base64.b64encode(json.dumps({"alg":"none","typ":"JWT"}).encode()).decode().rstrip('=')
payload = base64.b64encode(json.dumps({"user_id":1,"role":"admin","email":"victim@company.com"}).encode()).decode().rstrip('=')
token = f"{header}.{payload}."
print(token)
```

**Grep patterns for auth bypass surface:**
```bash
# Find XMLRPC in scope
grep -r "xmlrpc" scope_urls.txt

# Find SSO indicators in JS
grep -rE "(SAMLResponse|samlRequest|RelayState|onelogin|shibboleth)" *.js

# Find partner/admin subdomains
subfinder -d target.com | grep -E "(admin|partner|internal|sso|auth|login)"
```

---

## Common Root Causes

1. **SSO bypasses local auth entirely at the UI layer, but not at the API layer** — developers disable the login form but forget that API endpoints (`/xmlrpc.php`, REST API, mobile API) have their own auth handlers that still accept native credentials.

2. **SAML signature validation is skipped or optional** — library defaults often don't enforce signature checking; developers use `wantAssertionsSigned: false` or fail to configure the IdP certificate correctly.

3. **Shared session infrastructure across different trust levels** — partner portals and admin portals reuse the same session cookie or JWT secret because they're built on the same internal framework, assuming access control at the application layer is sufficient.

4. **Trust inheritance in multi-tenant architectures** — a token issued in a lower-privilege context (partner, reseller) is accepted in a higher-privilege context because the verification only checks signature validity, not the issuance context.

5. **Plugin/module auth is independent of application auth** — every WordPress plugin that handles auth (contact forms, REST API extensions, WooCommerce) may implement its own auth handler inconsistently with the main site's SSO.

6. **XML parsing inconsistencies** — different XML parsers (used by SP vs. IdP) handle comments, namespaces, and whitespace differently, enabling confusion attacks where the signed content differs from the evaluated content.

7. **The auth guard and the router canonicalize the path differently** — middleware tests `req.path` as a raw string, the framework resolves it as a route, and the framework's defaults (case-insensitive matching, trailing-slash normalisation, `..` and `%2e` decoding, proxy rewrite headers) make those two views diverge. One capital letter can remove auth from an entire API surface. See the Canonicalization Mismatch section — this is the highest-yield class in hand-written middleware because the guard *looks* correct and its `401` branch is what a reviewer reads.

---

## Bypass Techniques

| Defense | Bypass |
|---|---|
| SSO enforced on login page | Probe alternate entry points: XMLRPC, REST API, mobile API, legacy endpoints |
| SAML signature validation | XML comment injection, namespace wrapping, signature wrapping (XSW), remove signature entirely |
| IP allowlisting on admin portal | Use partner portal token if it shares auth backend |
| Rate limiting on login | XMLRPC allows credential stuffing via `system.multicall` — batches hundreds of auth attempts in one request |
| CSRF token on login form | SAML flow is POST-based cross-origin by design; no CSRF token needed on `/saml/callback` |
| JWT signature validation | `alg: none`, key confusion (RS256 → HS256 with public key as secret), brute-force weak secrets |
| Separate session stores per portal | Check if cookie domain is `.target.com` (wildcard) — cookie bleeds between subdomains |
| MFA on primary login | If SAML SP doesn't enforce MFA at the assertion level and accepts pre-auth assertions, MFA can be skipped |
| API-key middleware that prefix-tests `req.path` | Canonicalization mismatch: `/API/`, `/api/../api/`, `//api/`, `/%61pi/`, `X-Original-URL` — the guard's string test misses what the router still resolves. §Canonicalization Mismatch |
| Path-based authz on a proxied/CDN-fronted app | `X-Original-URL` / `X-Rewrite-URL` / `X-Forwarded-Prefix` — the guard sees the outer path, the origin honours the override |
| Guard that returns `true` when the key env var is unset | Not a bypass but a posture bug: a misconfiguration turns into a public API. Report it alongside, and check the config for an `ALLOW_UNAUTHENTICATED_*` flag before claiming the bypass matters |

**XMLRPC multicall for mass auth bypass:**
```xml
<methodCall>
  <methodName>system.multicall</methodName>
  <params><param><value><array><data>
    <value><struct>
      <member><name>methodName</name><value><string>wp.getUsersBlogs</string></value></member>
      <member><name>params</name><value><array><data>
        <value><string>admin</string></value>
        <value><string>password1</string></value>
      </data></array></value></member>
    </struct></value>
    <!-- repeat for each credential pair -->
  </data></array></value></param></params>
</methodCall>
```

---

## Differential-error testing hygiene — the stale-CSRF false positive (verified 2026-10, FIRST.org portal)

When hunting **user enumeration** via differential login errors (existing user says
"incorrect", unknown user says "invalid"), the single most common false positive is a
**consumed CSRF/anti-replay token**, not an auth oracle. Frameworks with single-use hidden
tokens (FIRST's in-house portal uses `__req`; Rails `authenticity_token`; Laravel `_token`;
Django `csrfmiddlewaretoken`) reject the SECOND submission of the same token with a generic
"invalid request" error that looks exactly like an account-state difference.

What it looks like in practice: attempt 1 (existing account) returns "incorrect" in 0.4 s;
attempt 2 (unknown account, same page token) returns "invalid" in 1.1 s. The timing gap and
the different word scream enumeration. Re-run with a **freshly fetched token per attempt**
and both return the identical "incorrect" — the differential was the token, full stop.

Rules that prevent the false positive:

1. **Fresh token per attempt** — GET the form page again before every POST; never reuse a
   hidden token across attempts, even within one session.
2. **Fresh session per attempt** when the framework binds tokens to the session cookie.
3. **Three controls minimum** — one known-existing identity, one known-nonexistent identity,
   and one repeat of each; all four must agree before you claim an oracle.
4. **Timing is not an oracle by itself** — sub-second differences on a single pair are noise;
   the error TEXT (or the next stage of the flow running) is the signal.
5. If the differential survives fresh tokens, verify it is account-state and not, e.g., a
   rate-limit warning that appears after N requests to the same page (also seen live: a
   "You're sending a lot of requests" warning that only triggered for the address probed
   repeatedly).

Related: `triage-validation` — enumeration alone is usually N/A/Informational; it only becomes
a finding when chained to lockout-amplification or credential attacks.

## Gate 0 Validation

Before writing any report, answer these three questions:

1. **What can the attacker DO right now?**
   Must be: authenticate as another user OR authenticate without valid credentials OR elevate to admin/privileged role. "Partial information disclosure" is not auth bypass.

2. **What does the victim LOSE?**
   Must identify a concrete asset: account takeover of specific user, access to all admin functions, ability to read/modify other tenants' data, or access to privileged APIs. Abstract "security control bypass" without impact is not sufficient.

3. **Can it be reproduced in 10 minutes from scratch?**
   You must be able to: (a) start from a fresh browser/session, (b) follow your exact steps, and (c) arrive at authenticated access to a protected resource. If reproduction requires special preconditions you can't re-create (a specific victim's active session, timing windows), the report needs more work.

---

## Real Impact Examples

**Scenario 1 — SSO Enforcement Bypassed via Forgotten Protocol Endpoint**
A large ride-sharing company enforced SSO (via OneLogin) on all WordPress-based internal/public properties. The XMLRPC endpoint (`/xmlrpc.php`) remained active and accepted WordPress-native credentials entirely independent of the SSO flow. An attacker with any valid WP-native credentials (obtained via credential stuffing or from a previous breach) could authenticate directly through XMLRPC, bypassing MFA, SSO policies, and IP restrictions enforced on the main login form. Impact: Full authenticated access to all WordPress functions available to that user role, including content management and potentially admin functions.

**Scenario 2 — SAML Assertion Forgery via Signature Validation Failure**
A major enterprise communication platform's SAML SP implementation failed to properly validate assertion signatures in specific edge cases. By manipulating the XML structure of a captured SAMLResponse (specifically through comment injection or namespace prefix attacks), an attacker could modify the `NameID` value to impersonate any user in an organization — including workspace administrators — without possessing that user's credentials or private key material. Impact: Complete account takeover of any user within a SAML-enabled organization; attacker gains access to all messages, files, and integrations in the workspace.

**Scenario 3 — Cross-Portal Privilege Escalation via Shared Auth Backend**
An e-commerce platform's partner/reseller portal issued authentication tokens that were validated by the same backend service as the merchant admin portal. A partner-level account (lower trust, external-facing) could use its issued credentials or tokens to authenticate directly against admin-tier API endpoints, bypassing the merchant onboarding and permission assignment flow. Impact: A malicious partner could access any merchant's admin panel, modify store configurations, exfiltrate customer PII and payment data, or install malicious scripts — affecting thousands of merchant storefronts.

---

## Disclosed Report Citations (Backfill +8 — 2016-2025)

The following real, verified bug-bounty / coordinated-disclosure cases extend this skill. Spans 4 SAML subclasses, 4 JWT subclasses, 1 legacy-protocol (XMLRPC), and 2 partner-portal cross-domain reuse patterns.

5. **GitHub Enterprise Server — SAML XSW via parser differential (CVE-2025-25291/25292)** ([H1 #2579939](https://hackerone.com/reports/2579939) · [Blog](https://github.blog/security/sign-in-as-anyone-bypassing-saml-sso-authentication-with-parser-differentials/))
    - Subclass: SAML signature stripping / XSW (parser-differential variant)
    - Payload: signed SAML response; inject a sibling `<Assertion>` so REXML (signature-checker) and Nokogiri (business-logic reader) resolve different nodes via the same XPath. Signature validates against benign node; SP consumes attacker-controlled `<NameID>admin@target</NameID>`
    - Root cause: two XML parsers used for verification vs consumption return different elements for the same XPath
    - Year: 2025 — GitHub Security Lab bounty (program max class, internally rated Critical)

6. **GitHub Enterprise — SAML signature bypass on encrypted assertions (CVE-2024-4985)** ([H1 #2475347](https://hackerone.com/reports/2475347) · [ProjectDiscovery advisory](https://projectdiscovery.io/blog/github-enterprise-saml-authentication-bypass))
    - Subclass: SAML signature stripping (XSW family) when encrypted-assertions feature enabled
    - Payload: forge SAML response with attacker-controlled assertion; exploit improper signature verification on the encrypted-assertion code branch; provision arbitrary user including `site_admin`
    - Root cause: improper cryptographic signature verification on the encrypted-assertion code branch
    - Year: 2024 — bounty undisclosed, CVSS 10.0

7. **Uber — SAML auth bypass on `uchat.uberinternal.com`** ([H1 #223014](https://hackerone.com/reports/223014))
    - Subclass: SAML signature stripping / improper assertion verification (OneLogin SP-side)
    - Payload: replay/modify SAML assertion with forged `NameID`; SP did not strictly validate signature scope, so attacker-controlled assertion accepted, granting OneLogin SSO session to internal chat
    - Root cause: improper SAML signature verification on SP implementation
    - Year: 2017 — **$8,500**

8. **Uber — OneLogin SSO bypass via WordPress XMLRPC** ([H1 #138869](https://hackerone.com/reports/138869))
    - Subclass: WordPress XMLRPC bypassing SSO (legacy-auth path not gated) — canonical Legacy-Protocol Matrix case
    - Payload: OneLogin plugin auto-created WP users with literal password `@@@nopass@@@`. SSO plugin blocked `wp-login.php` only. POST `xmlrpc.php` with `wp.getUsersBlogs` + known shared password → authenticated as any previously-SSO'd user
    - Root cause: SSO enforcement applied at one auth surface (wp-login) but legacy XML-RPC path retained password auth with a guessable shared password
    - Year: 2016 — **$7,000**

9. **Slack — SAML "confused-deputy" assertion reuse** ([Writeup](http://blog.intothesymmetry.com/2017/10/slack-saml-authentication-bypass.html))
    - Subclass: partner-portal / cross-IdP assertion reuse (audience-restriction not validated)
    - Payload: take an old expired GitHub-signed SAML assertion (different audience, different subject) → present to Slack ACS → Slack logs attacker in as the asserted username
    - Root cause: no audience-restriction nor freshness check; trust extended across IdPs
    - Year: 2017 — **$3,000**

10. **HackerOne — SAML signup domain enforcement bypass via control characters** ([H1 #2101076](https://hackerone.com/reports/2101076))
    - Subclass: partner-portal / SAML domain-binding bypass via unicode control characters
    - Payload: new user sign-up at SAML-enforced org; append trailing control character (e.g., `\r`, ` `) to email → domain comparison normalises away, signup proceeds → unauthorised access to the org
    - Root cause: inconsistent unicode/control-char normalisation between domain check and identity write
    - Year: 2024 — bounty awarded (amount undisclosed)

11. **8x8 / Jitsi-Meet — JWT alg-confusion (asymmetric verifier accepts symmetric alg)** ([H1 #1210502](https://hackerone.com/reports/1210502))
    - Subclass: JWT alg-confusion (RS256 → HS256 using public key as HMAC secret)
    - Payload: server publishes RS256 verification public key. Send a token with header `{"alg":"HS256"}` signed with that public key as the HMAC secret → Prosody module validates and admits attacker into authenticated/moderator room
    - Root cause: verifier did not enforce `alg=RS256`; allowed symmetric algorithm using the public key as shared secret
    - Year: 2021 — bounty undisclosed

12. **Argo CD (Internet Bug Bounty) — JWT audience claim not validated (CVE-2023-22482)** ([H1 #1889161](https://hackerone.com/reports/1889161))
    - Subclass: token-scope / audience check at issuance not at use (cross-audience token confusion)
    - Payload: obtain any RS256-signed token signed by the cluster's OIDC issuer but minted for a different `aud` (e.g., `kubernetes`) → present it as bearer to Argo CD API → API treats it as valid because it accepted the issuer's signature and skipped `aud` enforcement
    - Root cause: `aud` claim not enforced; signature-trust extended across audiences
    - Year: 2023 — **$2,400** via IBB

---

## Duende BFF — Token-Confusion & Session-Fixation (2024-2026 surface)

Duende BFF deployments expose two distinct auth-bypass families beyond the CSRF angle covered in `hunt-csrf`. Both are documented architectural realities, not unicorn CVEs.

### Attack class 1 — YARP `UserOrClient` / `UserOrNone` privilege escalation

`Duende.BFF.Yarp` attaches access tokens to proxied routes via `WithAccessToken(TokenType.X)` metadata. The **misconfig pattern**: developer marks a route `UserOrClient` (use user token if logged in, else fall back to *client-credentials* token) intending it for a "public catalog" endpoint. The client-credentials (M2M) token frequently has broader scope (`api.admin`, `internal.read`) than any user token. An **unauthenticated** attacker hitting that route gets the request proxied with the **service-account token attached** to the downstream API — privilege escalation by design when the downstream trusts the bearer.

**Payload shape:** identify a BFF route marked `TokenType.UserOrClient` (visible via 401-vs-200 differential when no session, or via leaked OpenAPI/NSwag spec). Hit it with no cookies → BFF forwards with M2M token granting admin-scope downstream. ([docs.duendesoftware.com/bff/fundamentals/apis/yarp](https://docs.duendesoftware.com/bff/fundamentals/apis/yarp/))

**Adjacent confirmed CVE:** **CVE-2024-51987** in `Duende.AccessTokenManagement.OpenIdConnect` — *"HTTP client uses incorrect token after refresh"* — materially the same family of token-confusion at the proxy layer. Moderate severity, fixed 2024. ([GHSA-...51987](https://github.com/advisories?query=duende))

### Attack class 2 — Cookie-domain wildcard + sliding expiration = persistent ATO

When BFF session cookie has `Domain=.example.com` (devs do this to share login across `app.` and `admin.`), the `__Host-` prefix protection is dropped. Any sibling subdomain — including a **taken-over** one (`legacy.example.com` CNAMEd to deprovisioned Heroku/S3) — can write `Set-Cookie: .AspNetCore.Cookies=<attacker_session>; Domain=.example.com`. Victim hits `app.example.com` carrying the attacker's session = **session-fixation ATO**.

If `SlidingExpiration=true` (default) and `ExpireTimeSpan` is large (e.g. 8h), an exfiltrated cookie remains valid and keeps sliding forward as long as the attacker periodically calls `/bff/user`. There is no server-side refresh-token rotation check on the cookie itself — only the OIDC token (server-side) rotates. Persistent ATO window per stolen cookie.

**Payload shape:** subdomain takeover → write the BFF session cookie with `Domain=.example.com` → victim's next visit to `app.example.com` adopts attacker's session. Cron-curl `GET /bff/user -H 'X-CSRF: 1' -b '.AspNetCore.Cookies=...'` every 6h indefinitely to keep the session alive.

**Hardening reference:** [docs.duendesoftware.com/bff/fundamentals/session/handlers](https://docs.duendesoftware.com/bff/fundamentals/session/handlers/), [nestenius.se BFF cookie guide](https://nestenius.se/net/bff-in-asp-net-core-3-the-bff-pattern-explained/), [Langkemper on `__Host-` prefix](https://www.sjoerdlangkemper.nl/2017/02/09/cookie-prefixes/).

### Attack class 3 — `/bff/user` claim disclosure

`GET /bff/user` returns the **full claim set** of the active session as a JSON array — `sub`, `sid`, `email`, `bff:session_expires_in`, `bff:session_state`, `bff:logout_url`, plus every custom claim the OP issued (department, role, internal employee ID, tenant ID). The endpoint is gated only by session cookie + `X-CSRF: 1`. If `AnonymousSessionResponse=Response200` is set, the endpoint also acts as a session probe (200 + claims vs 200 + `null`) usable as an auth-state oracle. Low/Medium info-disclosure on its own; valuable as recon for the YARP token-confusion class above. ([docs.duendesoftware.com/bff/fundamentals/session/management/user](https://docs.duendesoftware.com/bff/fundamentals/session/management/user/))

### Evidence strength + reporting tip

No Duende.BFF-direct CVE exists. The three classes are exploitable via real-world misconfigurations; CVE-2024-51987 and CVE-2025-26620 in the adjacent `Duende.AccessTokenManagement` packages make token-confusion a confirmed family. **Report by chain impact** (e.g., "low-priv session reaches admin-scope downstream API via UserOrClient route" → Critical) rather than by CVE citation, since the issue is design-level.

Cross-references for the chain:
- `hunt-csrf` — the role-partitioned antiforgery class (the CSRF angle on the same BFF surface).
- `hunt-subdomain-takeover` / `hunt-subdomain` — required primitive for the cookie-domain attack.

---

## Function-Level Access Control (Broken Authorization)

Authentication bypass gets you *in*; **function-level access control** failures let an already-authenticated low-privilege user reach privileged *functions* the UI never offered them. This is the authorization sibling of `hunt-idor` (object-level access) — test both whenever you hold any authenticated session.

**The sibling-function rule:** if 9 endpoints under a path enforce auth/role middleware, the 10th that doesn't is your bug. Admin route families are the highest-yield place to look:

```
/api/admin/users   → has auth middleware
/api/admin/export  → often MISSING it
/api/admin/delete  → often MISSING it
/api/admin/reset   → often MISSING it
```

**Anti-patterns to grep for:**
```javascript
// Missing middleware on a sibling route
router.get('/admin/users',  authenticate, authorize('admin'), getUsers);
router.get('/admin/export', getExport);            // No middleware!

// Client-side role check only — server never re-checks
if (user.role === 'admin') showAdminButton();      // frontend gate
app.post('/api/admin/delete', deleteUser);         // no server-side check
```

**How to hunt:** enumerate every privileged endpoint (admin/export/delete/reset/impersonate, GraphQL admin queries), then replay each from a *regular* authenticated session — and again with no session. A 200 (or a differential vs the 403 its siblings return) is broken function-level access control.

**Real paid example — HackerOne TrustHub:** `POST /graphql` with the `TrustHubQuery` operation had no authorization check — a regular user could read all vendors' data (CVSS 8.7, High). The object-level variant (e.g. a WebSocket `get_history` accepting an arbitrary UUID with no ownership check) belongs to `hunt-idor`.

---

## OWASP Top 10:2025 anchor + ASVS V6/V7 test plan (added 2026-10-30)

This class is **A07:2025 Authentication Failures** — and A07 has the **highest exploitability (7.69)
AND highest impact (4.44) scores in the entire Top 10**, 36 CWEs, 7,147 CVEs. When a program's scope
is thin, auth is where the money is.

ASVS 5.0 requirements this class must satisfy (cite the ID in the report):

| ASVS | Lvl | Requirement | Our probe |
|---|---|---|---|
| **6.3.4** | **2** | **no undocumented auth pathways** | enumerate ALL login routes (Legacy-Protocol Matrix) |
| **6.3.8** | **3** | valid users not deducible from failed challenges | differential-error test — **fresh token per attempt** |
| **6.4.2** | **1** | no password hints / KBA | registration form |
| **6.5.1** | **2** | lookup secrets / OOB codes / TOTP usable **only once** | replay the code |
| **6.6.2** | **2** | OOB codes **bound to the original request** | cross-session code reuse |
| **6.8.2** | **2** | signature presence + integrity **always** validated | strip/alter assertion |
| **7.2.4** | **1** | new session token on authentication (incl. re-auth) | **session fixation** |
| **7.4.1** | **1** | session unusable after logout/expiry | replay post-logout |
| **7.5.1** | **2** | full re-auth before modifying sensitive auth attributes | change email without re-auth |

**2026 technique refresh — parser differential.** The canonicalization section below is the general
form; 2026 produced four verified, version-specific instances of the *same* bug (two parsers, one
request, two different answers):

- **CVE-2026-88009 Traefik < 2.11.57 / < 3.7.13** — rootless HTTP/1 request target stored in
  `URL.Opaque` with `URL.Path` empty → path-scoped authz bypass + **access-log evasion** +
  cross-vhost routing bypass, unauthenticated, stock defaults.
- **CVE-2026-50559 Quarkus < 3.37.0** — encoded reserved chars (`%3B`, `%2F`, `%5C`) defeat the
  security-policy path match while the router decodes and executes.
- **CVE-2026-0707 Keycloak** — `Authorization` header parser accepts non-standard `Bearer`
  separators (tabs), case variants, multiple spaces → gateway/IdP disagreement.
- **CVE-2026-52747 ModSecurity < 3.0.16** — multipart parser silently strips embedded line breaks
  from non-file fields → WAF-vs-backend differential on `ARGS`.

Probe set + the "check the access log" rule:
`security/exploit-cookbook/references/owasp-top10-2025-asvs5-access-auth.md` §5.

## Canonicalization Mismatch — the guard and the router disagree about what the path IS

The single highest-yield auth-bypass class in hand-written middleware, and the one most often
missed because the code *looks* protective. The guard inspects the path as a **string**; the
router resolves the path as a **route**. If those two disagree about what a request is, the guard
does not fire and the route still serves.

**The anti-pattern:**

```javascript
// auth.ts — a prefix test on the raw path
if (!req.path.startsWith(pathPrefix)) {
  return next()                      // <-- no key check at all on this branch
}
```

```javascript
// server.ts
app.use(createApiKeyMiddleware(expectedApiKey))   // intended: guard everything under /api/
app.get("/api/tokens", handler)                   // Express default: caseSensitive = FALSE
```

Express matches routes case-**insensitively** by default. `req.path` preserves the case the
client sent. So `/API/tokens` fails `startsWith("/api/")` (so the guard defers **without
authenticating**) and then matches the `/api/tokens` route. One capital letter removes auth from
the whole surface. Note the failure mode: the check is not merely weak, it is **never executed**.

### The variants — walk all of them, they are the same bug

| Variant | Probe | Guard sees | Router sees |
|---|---|---|---|
| **Case folding** | `/API/tokens`, `/Api/Tokens` | not `/api/…` | `/api/tokens` (caseSensitive:false) |
| **Missing/extra trailing slash** | `/api` vs prefix `/api/`, or `/api//tokens` | prefix mismatch | normalised / matched |
| **Dot-segment traversal** | `/api/../api/admin/x` | literally starts with `/api/` ✔ | normalised to `/api/admin/x` |
| **Encoded characters** | `/%61pi/tokens`, `/api%2ftokens` | not `/api/` | decoded before routing |
| **Duplicate slash** | `//api/tokens` | not `/api/` | collapses to `/api/tokens` |
| **Path parameters** | `/api;foo/tokens`, `/api%00/tokens` | mismatch | stripped by the framework |
| **Unicode normalisation** | full-width `／`, homoglyphs | mismatch | normalised |
| **Proxy/CDN prefix strip** | `X-Original-URL`, `X-Rewrite-URL`, `X-Forwarded-Prefix` | sees the outer path | honours the override header |

The traversal row is the inverse failure and equally real: a guard that *does* match can still be
walked past if the router normalises `..` afterwards. **Test both directions** — paths that fail
to match a prefix they should, and paths that match a prefix they shouldn't.

### Reproduce it against the real framework, with controls

Do not argue from reading — the framework's default decides the outcome. Transcribe the
middleware and route table verbatim, pin the framework version the project declares, and run both
directions:

```
401  GET  /api/tokens            no key    <- CONTROL: guard works when the prefix matches
200  GET  /api/tokens            with key  <- CONTROL: guard allows the legitimate caller
200  GET  /API/tokens            no key    <- bypass
202  POST /API/admin/replay/...  no key    <- admin action without a key
```

**The two controls are what make it conclusive** and non-arguable in a report: the same path in
lowercase is blocked without a key and allowed with one, so the guard is configured correctly and
simply does not run for a case-varied path. Without them a reviewer can claim you mis-set the key.

Watch for `pathPrefix` defaults that differ per route family: an app may build one middleware for
`/api/` and another for `/api/admin/`, and a single normalisation bug defeats **both** at once.

### Before calling it a finding, check the deployment posture

Grepping the config for an escape hatch saves you from reporting an intended open API:

- an **`ALLOW_UNAUTHENTICATED_API`-style flag** — if it is on, the API is open by design and the
  bypass is moot;
- **`resolveEnableApi(requested, apiKey, allowUnauthenticated)`**-style helpers — read what
  combination actually enables the guarded mode, and quote the `.env.example` default in the report;
- **whether the service is reachable externally at all.** An internal-only indexer/worker makes
  this a code-level defect, not an external exploit path — many programs (including Relay's) pay
  only when an *unprivileged party can reach* the bug. Say so plainly rather than implying reach
  you did not prove.

### Remediation to recommend

1. **Normalise before comparing** — `req.path.toLowerCase().startsWith(prefix.toLowerCase())`.
2. **Let the router be authoritative** — mount the guard in front of the routes it protects
   (`app.use("/api", guard)`) instead of re-deriving the prefix from the path by hand. Middleware
   ordering cannot be defeated by path shape; a string test can.
3. **Fail closed** on a missing key — a guard that returns `true` when unconfigured turns a
   misconfiguration into a public API.
4. Consider case-sensitive routing as defence in depth, but do not rely on it alone: the other
   rows in the table above survive it.

`references/path-canonicalization-auth-bypass.md` carries the full repro harness, the framework
defaults that cause it per stack, and the report skeleton.

---

## Naikkan severity — komposisi K/A/B/X (wajib sebelum lapor, added 2026-10-30)

Sebuah temuan auth **hampir tidak pernah High sendirian**. Yang membuatnya High adalah komposisi.
`security/chain-to-impact` memberi empat label — klasifikasikan SETIAP sinyal auth lo dengan apa yang
ia **supply**, lalu cari tepi yang menyambung:

| Part | Yang ia beri penyerang | Sinyal auth yang biasa supply ini |
|---|---|---|
| **K — Knowledge** | identifier / versi / schema | error differential (enumerasi user), version leak di halaman login, `iss`/`aud` di JWT, error yang menyebut framework |
| **A — Action** | server melakukan sesuatu atas nama lo | reset-password yang menulis ke email tak terverifikasi, alternate-path login, SSO callback yang menerima assertion tak ditandatangani |
| **B — Bypass** | menghapus cek yang memblokir hop berikutnya | **missing rate limit** (unlocks spray), **OTP throttle lemah**, CORS reflect di endpoint ber-cookie, `redirect_uri` wildcard, captcha bypass, path canonicalization |
| **X — Amplifier** | primitif kecil → banyak, atau jadi tampilan aktor lain | IDOR di objek publik, share-link reuse, support-view/impersonation, export yang abaikan filter |

Pola komposisi yang **terbukti** mencapai High/Critical dan relevan untuk kelas ini:

```
B + X   missing rate limit (B) + account enumeration (B) + spray (A)  =  credential-stuffing ATO
K + B + A + X   error-leak (K) → unthrottled enumeration (B) → unverified email change (A)
                → IDOR/export amplification (X)                          =  mass ATO
A + X   open redirect (A) + share-link identifier reuse (X)             =  token exfil ke origin penyerang
K + A   version/stack leak (K) → CVE pada versi itu persis (A)          =  RCE
```

Prosedur (jalanin di **0E**, sebelum laporan ditulis): INVENTORY → LABEL → EDGES → SINK → PROVE →
REPORT. **Satu laporan rantai**, judul = impact terminal, severity = impact terminal. Low individual
muncul sebagai langkah bernomor, bukan submission terpisah.

Aturan jujur: **Low tanpa label part bukan Low — itu noise.** Jangan padding ledger dengan missing
header atau clickjacking tanpa target state-changing.

Skill lengkap: `security/chain-to-impact` · tangga kedalaman `exploit-depth` (L0→L5) ·
`lead-to-critical` (skor ceiling sebelum menghabiskan waktu).

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Endpoint sensitif tanpa sesi sama sekali (bukan cuma halaman — **API call**-nya) | SPA shell ≠ bypass; data API yang menentukan |
| 2 | Turunkan versi: `/api/v1/` vs `/api/v2/` pada endpoint sama | Legacy route authz lebih lemah |
| 3 | Header auth internal: `X-Forwarded-User`, `X-Remote-User`, `X-Original-URL` | Parser confusion di proxy/gateway |
| 4 | Path normalisasi: `..;`, `%2e%2e`, `//`, `/.`, trailing dot — cek ke MANA path mendarat | Normalisasi ≠ bypass; landing target harus protected |
| 5 | Parameter role/tenant: ubah `org_id`/`tenant`/`account` di body & query | Vertical privesc lewat client-supplied scope |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** lewati verifikasi identitas

**Teknik pengembangan:** akses admin panel -> upload webshell; jadi user lain -> ATO; endpoint internal -> RCE

**Eskalasi ke:** `hunt-ato` · `hunt-rce` · `hunt-idor`

**Depth target:** L3 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **`hunt-idor`** — Auth bypass without object-level access is half a finding; pair them. Chain primitive: legacy `/v1/users/{id}` route missing both auth middleware AND ownership check = unauthenticated cross-tenant data read via direct ID substitution → full PII dump from "I am nobody" starting position.
- **`hunt-ato`** — Auth-bypass primitives feed the ATO funnel. Chain primitive: XMLRPC native-cred acceptance + no rate limit on `wp.getUsersBlogs` → credential-stuff with breach corpus from `hunt-misc` recon → `system.multicall` batches 1000 cred pairs per request → one valid pair = ATO bypassing the SSO + MFA the UI enforces.
- **`hunt-sharepoint`** — The SP equivalent of the WordPress XMLRPC pattern lives here. Chain primitive: `/_vti_bin/Authentication.asmx` anonymous reachable + native Forms-auth credential accepted + zero rate limit = unlimited credential brute-force endpoint bypassing custom-branded `customlogin.aspx` protections → FedAuth cookie → full SharePoint farm access.
- **`security-arsenal`** — Pull the JWT-attack payloads section (alg=none, kid path-traversal, JWK injection, RS256→HS256 key confusion) when JWT validation is the auth wall; pull the SAML signature-stripping section when the SP accepts unsigned assertions.
- **`triage-validation`** — Run the Pre-Severity Gate before claiming Critical on an "auth bypass" that only enumerates usernames or only reveals a 401-vs-403 differential. Username enumeration alone without lockout-amplification is consistently N/A or Informational on H1.


## 2026 sweep (dork pass 2026-10-18 — 3 repo)

- **CVE-2026-18963 — Keycloak forgot-password flow authentication bypass** (`orevim/CVE-2026-18963-PoC` ★0)
  - flow bypass, with an optional browser component that renders the resulting
  - CVE-2026-18963 is an authentication bypass in Keycloak's forgot-password flow.
- **CVE-2026-97657 — WooCommerce Abandoned Cart Pro auth bypass via local token forgery** (`murrez/CVE-2026-97657` ★1)
  - CVE-2026-97657 — Abandoned Cart Pro for WooCommerce authentication bypass
  - Performs **local token forgery** then a **single unauthenticated HTTP GET** (plus redirect follows). No WordPress credentials are sent.
- **CVE-2026-54415 — Azuriom CMS broken access control → ATO (<1.2.11)** (`abdugafforov-bobur/CVE-2026-54415-PoC` ★2)
  - CVE-2026-54415 — Azuriom CMS Broken Access Control → Account Takeover
  - Missing authorization on the admin server-management routes in Azuriom CMS `< 1.2.11` lets any low-privileged admin (holding only `admin.access`) mint an AzLink server token a


## 2026 sweep 3 (dork pass 2026-10-18 — web2, 2 repo)

- CVE-2026-41940 — **cPanel/WHM root auth bypass via session-file CRLF injection** (cpsrvd daemon). The forged session fields include `tfa_verified=1` and `hasroot=1`, so the bypass also defeats 2FA. **Confirmed in-the-wild exploitation** — patch immediately.
  - cPanel & WHM Edition** - CRLF Injection to Authentication Bypass & Full Session Hijacking
- CVE-2026-24061 — GNU inetutils-telnetd **CRLF injection → authentication bypass → instant root shell**. Lesson: CRLF in a login/negotiation path is an auth bypass, not just a response-splitting nuisance.
  - GNU inetutils-telnetd Edition** - CRLF Injection to Authentication Bypass & Instant Root Shell


## 2026 sweep 4 (dork pass 2026-10-18 — 3 repo)

- CVE-2026-18963 — **Keycloak reset-credentials bypass → unauthenticated account takeover**. Knowing only a username or e-mail, an attacker completes the password reset for any user. The mail step runs for real before the bypass, so the victim still receives a (legitimate-looking) mail — do not rely on 'user got an email' as evidence the flow was safe.
  - CVE-2026-18963 — Keycloak reset-credentials bypass → unauthenticated account takeover
  - Knowing only a **username or e-mail address**, an unauthenticated attacker sets an
- CVE-2026-1529 — Keycloak **unauthorized organization registration via improper invitation-token validation**. Lesson: invitation tokens are authorization objects; test reuse, cross-tenant replay and missing expiry.
  - Keycloak: Unauthorized organization registration via improper invitation token validation**
- My-Exploits — Metasploit modules + Docker labs for four platforms, including the Keycloak takeover and a **Vault metadata slash-injection** module. Useful as a ready-made lab to reproduce IdP takeover patterns safely.
  - `~/.msf4`). Three modules: the Keycloak takeover, the Vault metadata slash injection, and


## 2026 sweep 5 (dork pass 2026-10-18 — 1 repo)

- CVE-2026-14378 — WordPress DevKit Pro ≤2.3.0 **pre-auth admin takeover** via a forged `original_user_id` cookie plus a `wp_footer` `revert_switch` nonce. Lesson: impersonation features that trust a client-supplied 'original user' identifier are an auth bypass; look for any cookie/header naming a user the server then acts as.
  - Proof-of-concept scanner and exploit helper for **CVE-2026-14378**: unauthenticated **administrator session takeover** in the WordPress plugin **DevKit Pro** (d
  - PoC for CVE-2026-14378: DevKit Pro ≤2.3.0 pre-auth admin takeover via forged original_user_id cookie + wp_footer revert_switch nonce. check/admin + mass scan.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Canonicalization mismatch (guard vs router tidak sepakat path itu apa) → akses handler tertutup; legacy protocol matrix (XMLRPC, SAML strip, partner-portal token replay); cookie-domain wildcard + sliding expiration = persistent ATO. Kalibrasi: 401/403 konsisten di semua varian = kontrol bekerja; differential-error tanpa akses = Info.
