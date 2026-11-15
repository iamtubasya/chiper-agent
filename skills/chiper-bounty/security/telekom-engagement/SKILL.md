---
name: telekom-engagement
description: "Deutsche Telekom bug bounty: scope, RoE, estate map."
metadata:
  hermes:
    tags: [security, bug-bounty, telekom, engagement, scope, roe, t-systems, otc]
version: 1.0.0
---

# Deutsche Telekom bug bounty engagement

Vendor-run program (no HackerOne/Bugcrowd engagement for DTAG itself). Submission is **email only**:
`bugbounty@telekom.de`. T-Mobile US is a *separate* program on Bugcrowd — different scope, different
rules; do not mix.

Public page: `https://www.telekom.com/bug-bounty-program`
(also `/en/about-us/data-privacy-and-security/hacking-and-testing/bug-bounty`)

## Scope (public program)

In scope — wildcards, both the apex and the wildcard must be written for any scope gate:

```
*.telekom.de            *.telekom.net           *.telekom.com
*.t-systems.com         *.open-telekom-cloud.com
auth.otc.t-systems.com  *.otc-service.com
```

Out of scope:

```
*.reverse.open-telekom-cloud.com
*.lila.dih.telekom.com
all customer systems not owned by Deutsche Telekom AG
PHP RCE CVEs (CVE-2026-109618 / CVE-2026-109619) — explicitly excluded
```

Rewards: **P1 €5,000 · P2 €2,000 · P3 €1,000**. Private program is 2× (€10k / €4k / €2k) and wider.
Scoring uses Bugcrowd VRT or CVSS 4.0. *"If a reported vulnerability affects multiple systems, we pay
the reward only once."* No reward for third-party software/services.

## Rules of Engagement — the clause that shapes every PoC

Beyond the usual (confidential until fixed, no availability impact, no social engineering, no
physical access, no third-party systems):

> **"Do not access data. Do not modify, upload, delete, or share data."**
> **"If you discover personal data while testing, stop the attack immediately, delete the transferred
> personal data, and contact the Bug Bounty Team."**

Operational consequence: **every PoC must prove reachability without retrieving a record.** For an
unauthenticated-read finding, the proof is the *layer* the anonymous request reaches (a named DAO /
datasource error) plus a 403 on the write sibling — never a dumped row. Design the PoC around
"the filter is absent" rather than "here is the data". See
`api-authz-probe-ordering` §1b for the technique this forces.

## Estate shape (measured 2026-10-29)

93,423 subfinder names → 5,140 resolving → 2,345 live HTTP services. Concentrations:

| cluster | notes |
|---|---|
| `*.tap.telekom.de` (~49k) | CI/CD preview app farms, one host per build (`trap-*`, `*-<uuid>`); mostly dead, near-zero value |
| `*.aws.telekom.de`, `*.caas-t*`, `*.caas-p*` | k8s ingress farms; many `403` |
| `*.dih.telekom.com` | "Connect & Integrate" per-customer tenants — **customer systems, mostly OOS**; only DTAG-owned platform hosts are fair game |
| `*.obs.eu-de.otc.t-systems.com` | OTC object storage buckets; several anonymous-`LIST` buckets (see negatives) |
| `*.otc-service.com`, `*.otc.t-systems.com` | T Cloud Public control plane |
| `*.p5x.telekom.net`, `*.p5x2/p5x4` | the `idm`/`account` identity platform |

Core-business surfaces worth the hours: **Telekom Login / account-manager** (`account.idm.telekom.com`,
`idm.telekom.com`), **MagentaBusiness APIs** (`developer.telekom.com`, `docs.developer.telekom.com` —
docs are Vonage-hosted), **5G slicing** (`5g-slicing.telekom.net`), **IoT/M2M**
(`*.scs.iot.telekom.com`, `*.iotplatform.telekom.net`), **wholesale/carrier**
(`*.wholesale.telekom.com`), **shop** (`shop.telekom.de`, Nuxt + `api/shop/*`), **devops**
(`*.devops.telekom.de`).

## Verified negatives — do not re-run blind

- **No self-registration anywhere on the identity surface.** Telekom Login, every Keycloak realm
  (`keycloak.iotplatform.telekom.net` realm `iot`/`master`, `iam.dih.telekom.com` realm `dih`,
  `auth.ms.otc.t-systems.com`), Bitwarden (`bitwarden.telekom.de`,
  `disableUserRegistration: true`), iMSA, `qc-tool`/`wats` are all invite/employee gated. **This is
  the single biggest coverage blocker**: IDOR/BOLA/priv-esc lanes need an account you cannot
  self-provision. State it as a coverage gap, not as "no findings".
- Keycloak dynamic client registration: blocked by the `Trusted Hosts` policy on both realms
  (`403 insufficient_scope … Host not trusted`). Self-registration page returns `pageId: error`
  for `account-console` / `keycloak-proxy-admin` / `security-admin-console`. Correctly configured.
- `5g-slicing.telekom.net` `/backend/api/*`: all `401`; JWT `alg:none` and HS256-forgery
  (`secret`, empty) × 3 payloads → all `401`. Keycloak client `five-g-slice-ui` is PKCE-only with
  strict `redirect_uri` (evil host and `host.evil.example` suffix both `400`). Dead end unless an
  account appears.
- ArgoCD (`argocd.tcloudlz.telekom.net`, `argocd-rwth.commx.bo.dih.telekom.com`) v3.1.1:
  `/api/v1/settings` public but contains only url/label/overrides/analytics — **no clientSecret**;
  `/applications`, `/clusters`, `/repositories` all `401`. Not a finding.
- `shop.telekom.de` bundle endpoints (`/api/shop/order`, `/items`, `/coupon`, `/dcb_vouchers`) all
  `404` unauthenticated — session-gated upstream; unreachable without a real cart session.
- `developer.telekom.com` `/api/account/*` and `/api/dashboard/*` → `feature-guard` `404` by design.
- `adminapi.dih.telekom.com/api-docs` is public (OpenAPI, "Admin Approval API") but every
  `/api/v1/*` route answers `401`. Schema disclosure only.
- Portainer `schiff.roaming.telekom.net` 2.45.3: `/api/status` public, `/api/users/admin/check`
  `204`, `/api/endpoints` `401`. Correct.
- No claimable subdomain takeover found across the dangling-looking CNAMEs
  (`boc.cgs.telekom.net`→azurestaticapps, `romcloud.telekom.net`→azurewebsites,
  `business.telekom.com`→Netlify, `uke.cgs`→SWA, `tnm.telekom.net`→Azure) — all live, verified.
- Anonymous-`LIST` OTC buckets (`brodos-external`, `bgr-geoldg-public`, `apig-demo`) are
  **public-by-name** marketing/SDK content (`Bedienungsanleitung/*.pdf`, `java/SdkDemo.zip`).
  `apig-demo` ACL shows `AllUsers: READ`. Low; only report if real internal data appears.

## Open lead

`customer-rest-services.api-docs.iot.telekom.com` — unauthenticated read path reaching the
persistence layer (500 `HikariDatasource` init) vs `403` on the write siblings, plus a public 498 KB
`/v3/api-docs` for the 46-endpoint M2M SIM API. Medium as it stands; BOLA escalation over
`partnerId` is **conditional** on the datasource recovering.
Full evidence and reproduction: `api-authz-probe-ordering/references/telekom-iot-m2m-authz-2026-10-29.md`.

## Reporting notes

- Email the report to `bugbounty@telekom.de`; ask for PGP before sending anything sensitive.
- Include: vuln type, severity assessment, reproduction detail (PoC), suggested remediation —
  all three are named on the program page as expected.
- Never attach retrieved personal data (RoE). Redact host identifiers if they map to a customer.
