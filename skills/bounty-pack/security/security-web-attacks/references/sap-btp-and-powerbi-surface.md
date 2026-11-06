# SAP BTP approuter + Power BI embedded portal — recon & testing recipe

Observed live 2026-10-14 (gasunie.nl VDP): `gewasschademelden.<target>` = SAP BTP approuter + XSUAA +
SAP IAS; `dataport.<target>` = ASP.NET Razor app ("PowerBiReports") that brokers Power BI embed tokens.
Both shapes are common across EU energy / utility / logistics estates, so treat them as a reusable class.

## 1. Fingerprint: SAP BTP approuter

- `/` → 302 to `/site`; `/site` returns an ~880-byte shell served by the approuter itself.
- The shell's inline JS sets a cookie trio derived from the current URL:
  `fragmentAfterLogin` (location.hash), `locationAfterLogin` (path), `signature` (HMAC-ish tag).
- **The signature is value-bound — it changes per path** (`/site` ≠ `/site/xyz` ≠ `/site?a=1`), which
  kills the obvious post-login open redirect: you cannot pair a forged `locationAfterLogin` with a
  lifted `signature`. Confirmed: `locationAfterLogin=https://evil.example` + a lifted signature against
  `/login/callback?code=x&authType=xsuaa&state=x` returned **401** for every value tried.
- Login chain: approuter → `<tenant>.authentication.<region>.hana.ondemand.com/oauth/authorize?...`
  (SAP IAS) → the IAS login page offers the configured IdPs (in this case an employee SAML button plus a
  `sap_idp=sap.custom` path into an SAP-managed B2C/SAML tenant).
- Other approuter tells: `/logout` → 500 with a near-empty body (normal, not a finding), `/login` → 404,
  `X-Vcap-Request-Id` response header, and `frame-ancestors *` in the shell page's CSP.
- `sap_idp=` is an IdP **selector**, not a redirect target: supplying an external URL returned 200/404,
  never a redirect to it. Do not report it as an open redirect without a real 30x.

## 2. "Is self-registration open?" — decide BEFORE touching accounts

Walk the chain end-to-end instead of guessing from the login page:
approuter `/site` → IAS login page → any signup path → the IdP policy that backs it.

- If the IAS page renders only sign-in buttons and no register link, self-registration is probably closed.
- The B2C policy name leaks intent (`B2C_1A_signup_signin_saml` implies a signup policy exists), but the
  flow still has to be walked. A manual SAML replay that ends at the IdP with *"Identity provider cannot
  process the response due to wrong configuration"* is **not** a usable self-service path.
- For critical-infrastructure operators and other regulated entities: **do not fabricate a business /
  farmer / operator identity to register.** Offer a sandbox, or ask the vendor to provision a test
  account. Record "registration closed" as a coverage boundary — not as a failed engagement.

## 3. Power BI embed-token broker (the interesting surface on a "public data" portal)

- Page markup carries the pair needed to drive it: `getPowerBiReport('<workspaceId>', '<reportId>', ...)`.
- The broker is a Razor handler: `GET /index?handler=EmbedInfo&workspaceId=<GUID>&reportId=<GUID>`
  (it also answers on any path prefix, e.g. `/<AnyReportSlug>/index?handler=EmbedInfo`).
- Response JSON: `{Type, EmbedReport:[{ReportId, ReportName, EmbedUrl}], EmbedToken:{Token, TokenId, Expiration}}`.
- **The token is not a JWT.** It is base64url with a `.` separator and gzip per part:
  ```python
  a, b = tok.split(".")
  part = base64.urlsafe_b64decode(a + "=" * (-len(a) % 4))
  if part[:2] == b"\x1f\x8b": part = gzip.decompress(part)
  # -> {"clusterUrl":"https://WABI-...analysis.windows.net","exp":...,"allowAccessOverPublicInternet":true}
  ```
  The other part is an encrypted payload + CryptoKey blob and is not readable.
- **The token is scoped, not over-privileged:** it returns 403 against
  `api.powerbi.com/v1.0/myorg/groups/<ws>/reports` and `.../datasets`, so it cannot be used to enumerate
  the workspace. Verify this before claiming an over-scoped token.
- **The handler does no allowlist check.** It forwards whatever GUID pair it is given to Power BI using
  the app's own credentials; unknown workspace/report produce a downstream error
  (`Operation returned an invalid status code 'NotFound'`) instead of a local rejection. That is a real
  hardening gap — but with no known non-public workspace/report GUID the impact is **unprovable**. Stop
  at the boundary, state it as an unproven gap, and offer to test with an identifier list the vendor
  provides. Do not upgrade it to "cross-tenant data access".
- Enumerate the public report set by scraping the sidebar slugs, then mapping each slug to its
  `(workspaceId, reportId)` pair from the page's inline script — that is the app's own public list, and
  it gives you the legit reference token to compare against.

## 4. ASP.NET Razor handler parameter abuse → verbose stack trace (CWE-209)

`?handler=<Name>` routes to `OnGet<Name>(...)`. Break the parameters and the unhandled exception comes
back verbatim in the body of an HTTP 500:

| trigger | leaked message |
| --- | --- |
| omit every parameter | `Value cannot be null. (Parameter 'g')` |
| non-GUID value | `Unrecognized Guid format.` |
| valid id + unknown id | downstream SDK error, e.g. `Operation returned an invalid status code 'NotFound'` |

Each body also carries `at <Namespace>.<Page>.OnGet<Handler>(...) in D:\a\1\s\src\...\<File>.cs:line NN`,
i.e. the CI build path, the internal class/method names, and the offending line — plus the third-party
SDK in use. Try this trigger list first on any handler you find: missing param, malformed type,
valid-id-but-unknown-id, oversized value, extra/unknown query params. Confirm **3×** with different
inputs and hash each body (sha256 of the response body, first 16 hex chars, is a clean artefact for the
report).

## 5. When the engagement trips the WAF mid-run

Heavy scanning can flip the apex site to a flat `403` (nginx / Cloudflare) for *later* requests —
including policy fetches and `/.well-known/security.txt`. Pull them from Wayback with the raw-content
modifier so you get the file, not the archive's HTML wrapper:

```bash
curl -sL 'https://web.archive.org/web/2025id_/https://<host>/.well-known/security.txt'
curl -sL 'https://web.archive.org/web/2025/<policy-url>'
```

Do this **before** concluding that a contact channel or policy is unavailable. Also note the trade-off in
the coverage section: the block is why the unauth surface could not be re-probed afterwards.
