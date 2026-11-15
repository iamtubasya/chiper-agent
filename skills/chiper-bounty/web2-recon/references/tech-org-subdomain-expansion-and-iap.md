# Tech-org subdomain expansion + IAP-protected internal tooling

Class: the product runs on an **internal tech-org domain** (e.g. `nntech.io`, registrant verified via
RDAP as the parent bank). The highest-yield recon is expanding that zone and mapping which internal
tools are internet-facing. Companion to `internal-infra-disclosure.md`.

## 1. CT-only undershoots badly; `subfinder -all` is the gap

- certspotter/crt.sh alone gave **85** names across the estate; `subfinder -d <zone> -all` over the
  same 7 zones gave **14,410** (492 resolved, 378 answered HTTPS). Never conclude the surface from CT
  alone.
- `subfinder -all` is slow (minutes). Run it in the background and keep working on other hosts.
- Chain: `subfinder -all` → `dnsx -a -resp` → `httpx -sc -title -td -server -json`.

## 2. Read redirects on infra hosts — sibling zones hide behind them

`argocd.cd-test.<zone>` answered `302 Location: https://argo.test.cd.<OTHER-DOMAIN>/` — that single
header revealed a **sibling corporate domain** (`nordnettech.se`) that was not in the target's
`security.txt` canonical list. Always resolve and follow 301/302 on CI/CD/admin hosts; a redirect is
a free map to an unlisted zone (which may or may not be in scope — check ownership before probing).

## 3. Naming schemes leak architecture (this *is* the finding material)

Observed scheme, reusable as a wordlist/mental model:
```
{api,hantera,ops,iap,link,mcp,experimentation}.<project>.dev.<zone>
{argocd,atlantis,apps,backstage,openmetadata-api,mobile-ota}.cd[-test].<zone>
{account-register,company-data,sso,webid-signature-gateway,insurance-*}.b2b.<prod|test>.<zone>
{looker,nettie,nettie-mcp,dataland-file-upload-admin,incident-admin}.bi-apps.{analytics,analytics-test}
{lh,kiosk,wifi-user-admin,servicedesk-dashboard}.dcc.<zone>
```
Per-project dev names leaked the roadmap (trade-stock, flat-crypto, paper-broker, langfuse, …).

## 4. Access-control fingerprint (so you can prove you did NOT bypass)

| Control | Tell |
|---|---|
| Google Cloud IAP | `302` to `accounts.google.com/o/oauth2/v2/auth?client_id=…`; header `x-goog-iap-generated-response: true`; cookie `GCP_IAP_XSRF_NONCE_*` |
| Cloud Armor / GCP LB | uniform `403`, 134-byte Google 403 page, on every path |
| Network ACL | host resolves but **TCP times out** (`curl` code 000) |
| GCS bucket | `<Error><Code>AccessDenied` + `X-GUploader-UploadId`, `Server: UploadServer` |

Probe a few bypass paths anyway (`/healthz /api /static /_next /actuator/health /.well-known/…`): a
consistent 302/403 across all of them is the *proven* statement that the control holds.

## 5. Reporting shape

- Class **CWE-200, Low/Informational**; impact = reconnaissance only. Never claim compromise when
  the controls held — state plainly what did NOT work.
- Verify domain ownership before writing it up. RDAP for `.io`:
  `curl -s https://rdap.identitydigital.services/rdap/domain/<name>` → registrant org.
  `.se` RDAP was unreachable from the test host; fall back to in-band evidence (same infra/branding).
- Many programs **exclude** "internal IP / internal hostname disclosure" — say so to the operator
  rather than padding a submission.

## 6. PITFALL — empty resolver output is NOT a negative

`dig` silently returned **empty** (not `NXDOMAIN`) for names that curl and python resolved fine.
That produced a false "all dev hosts are NXDOMAIN / historical" conclusion and nearly closed the
whole zone. Before declaring a name dead, **cross-check with a second method**:

```bash
nslookup <host> 8.8.8.8
python3 -c "import socket; print(socket.gethostbyname('<host>'))"
```
Any tool that returns `0 rows` / `1 resolved` from a large list is a **suspect run, not a result** —
re-run it with corrected flags before believing the negative (see the abort-vs-negative rule in
`security/bug-bounty → references/wordpress-user-enum-and-version-precondition.md`).
