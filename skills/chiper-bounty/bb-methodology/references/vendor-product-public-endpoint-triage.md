# Vendor-product public endpoint triage — is this a finding, or is it how the product ships?

Large enterprises run dozens of self-hosted copies of well-known products (ArgoCD, Bitwarden, JFrog,
Keycloak, Portainer, Dependency-Track, RabbitMQ, SonarQube, Roundcube, Matomo, Open WebUI). Each one
has a handful of endpoints that answer `200` without credentials **by design**. Reporting those burns
credibility and eats a triage slot that a real bug needed.

This is the decision table, built from a 2,345-live-host sweep of Deutsche Telekom (2026-10-29).
Every row was probed live; the verdict column is what the probe actually returned.

## The rule

> **A public endpoint on a vendor product is a finding only when it discloses something the product's
> own documentation says requires authentication.** Otherwise it is the product working as designed.
> Your bug is in the *configuration*, not the software — so the question is always "did this deploy
> change the default in a way that leaks?", not "does this route exist?".

## Triage table

| Product | Public route | Verdict | Why |
|---|---|---|---|
| ArgoCD | `GET /api/version` | **not a finding** | Version string. Useful for CVE mapping only. |
| ArgoCD | `GET /api/v1/settings` | **not a finding** | Returns `url`, `appLabelKey`, `oidcConfig` (`issuer`, `clientID`, `scopes`), `googleAnalytics`. **No `clientSecret`.** Azure tenant IDs + OIDC clientIDs are in every discovery doc — public by design. |
| ArgoCD | `GET /api/v1/session/userinfo` → `{}` | **not a finding** | Empty object = anonymous. |
| ArgoCD | `GET /api/v1/applications` → `401 no session information` | **negative** | Correctly gated. |
| Keycloak | `GET /auth/realms/<r>/.well-known/openid-configuration` | **not a finding** | Required by the OIDC spec to be public. |
| Keycloak | `POST /clients-registrations/openid-connect` → `403 Trusted Hosts` | **negative** | Dynamic client reg enabled but host-restricted. Correctly configured. |
| Keycloak | `/protocol/openid-connect/registrations` → `pageId: error` | **negative** | Self-registration disabled. |
| Bitwarden | `GET /api/config` | **not a finding** | Public bootstrap config: version, `disableUserRegistration`, environment URLs. |
| Bitwarden | `/admin` → `302` | **not a finding** | Admin portal exists, login-gated. |
| Bitwarden | identity discovery returns internal hostnames (`bitwarden-self-host-identity:5000`) | **info-leak, Low** | Internal DNS name + `http://` in a TLS service. Real but low. |
| JFrog | `GET /artifactory/api/system/ping` → `OK` | **not a finding** | Liveness probe, documented as anonymous. |
| JFrog | `GET /artifactory/api/repositories` → `401` | **negative** | Gated. |
| Portainer | `GET /api/status` | **not a finding** | `{Version, InstanceID}` — public by design. |
| Portainer | `GET /api/users/admin/check` → `204` | **not a finding** | `204` = admin exists. This is the init-detection endpoint the setup wizard uses. |
| Portainer | `GET /api/endpoints` → `401` | **negative** | Gated. |
| Dependency-Track | `GET /api/version` | **not a finding** | Version + system UUID. |
| Dependency-Track | `POST /api/v1/user/login` enumeration (GHSA-9w3m-hm36-w32w) | **test, usually negative** | Probed with n=3 users on 4.8.0 and 4.13.6 → uniform `500` / `415`. No differential, so no oracle. |
| RabbitMQ | `GET /api/overview` → `401`; `guest:guest` → `401 not_authorized` | **negative** | Default creds disabled. |
| SonarQube | `GET /api/system/status` → `403` | **negative** | Gated. |
| SonarQube | `GET /api/projects/search` → `401` | **negative** | Gated. |
| Roundcube | `/program/js/app.min.js` → `200` | **not a finding** | Static asset. |
| Roundcube | `/installer/` → `404`, `/CHANGELOG.md` → `404` | **negative** | Installer removed (good). |
| Roundcube | `rcversion` in page source | **not a finding** | Version disclosure for CVE mapping only. |
| Matomo | `index.php?module=API&method=API.getMatomoVersion` → `401` | **negative** | Requires view access. |
| Open WebUI | `GET /api/config` | **not a finding** | Public bootstrap: version, `enable_signup`, oauth providers. |
| Open WebUI | `GET /api/v1/auths/` → `401` | **negative** | Gated. |
| Elasticsearch / MinIO / Grafana | `/` returns product banner | **not a finding** | Version banner. Only a finding if `/metrics`, `/_cat/indices` or `/api/datasources` answer. |
| yopass / PrivateBin / secret-sharing | `GET /config` | **not a finding** | Public bootstrap: `DISABLE_UPLOAD`, `FORCE_ONETIME_SECRETS`. Every instance serves it. |
| yopass | `POST /secret`, `POST /file` reachable anonymously | **not a finding** — see §4 | The product's entire purpose is anonymous upload. Validates before storing. |
| Workspace ONE / MDM consoles | `302 → /AirWatch/Login` | **not a finding** | Login page. Internet-facing MDM is attack surface, not a vuln. |

## 4. Anonymous-write endpoints: validate-before-store is the whole answer

The near-miss worth internalising. A publicly reachable **write** endpoint feels like a finding and
almost never is — because the product validates the payload *before* persisting it.

Measured on `yopass.dih.telekom.com` (Telekom, 2026-10-29) — a self-hosted yopass secret-sharing
instance. API is at **root**, not `/api` (that 404s):

```
POST /secret  {}                                   -> 400 {"message":"Message must be PGP encrypted"}
POST /secret  {"message":"","expiration":3600}     -> 400 {"message":"Message must be PGP encrypted"}
POST /secret  {"message":"notbase64!!!", ...}      -> 400 {"message":"Message must be PGP encrypted"}
POST /file    {}                                   -> 400 {"message":"Message must be PGP encrypted"}
GET  /secret/zzzznotarealidzzzz                    -> 404
GET  /config  -> {"DISABLE_UPLOAD":false,"FORCE_ONETIME_SECRETS":false,"PREFETCH_SECRET":true}
```

Read it correctly: the endpoint **is** anonymously reachable, and **nothing can be stored** without
valid PGP ciphertext. That is server-side-PGP mode working as designed. The temptation is to write
"unauthenticated file upload on a Telekom secret-sharing service — Medium". It would be rejected,
and the rejection would be correct.

**The rule:**

> An anonymous write endpoint is a finding only when you can demonstrate a **state change you were
> not supposed to cause**. Validation-rejects-everything is a negative, not a Low.

**What to actually test, and what each outcome means:**

| probe | outcome | verdict |
|---|---|---|
| `POST` empty / malformed body | `400` naming the required format | negative — validated before store |
| `POST` a **valid** payload of the accepted format | `200` + retrievable id | still not a finding *if the product's purpose is anonymous upload* |
| `POST` valid payload, then `GET` the id **as a third party** | content returned | that is the product working. Only a finding if the store was meant to be private |
| unbounded upload (size / count / no rate limit) | accepted | storage-abuse DoS — **report as Low at most, and only with a rate measured**, not assumed |
| id enumeration (`/secret/1`, `/secret/2`) | sequential hits | **real finding** — secrets behind guessable ids |
| config shows `FORCE_ONETIME_SECRETS:false` + `PREFETCH_SECRET:true` | — | weakens confidentiality by design; informational |

**And the discipline that matters more than any of the above:** when you probe a *write* endpoint on
someone's production secret store, use **empty or invalid bodies only**. Every probe above was
rejected pre-storage — nothing was written to their database. Sending a valid payload "just to
confirm" puts your test ciphertext in a stranger's production store and, on this product class,
creates a real retrievable secret with a Telekom-branded URL. That is the line between testing and
polluting.

## The three ways this triage goes wrong

**1. Version banner ≠ vulnerable.** `SonarQube`, `Roundcube rcversion 10617`, `Dependency-Track 4.8.0`
are all version disclosures. They become findings only when you can name a CVE **and** demonstrate the
exploit path on that exact version. A version string plus a CVE database is a hypothesis, not a bug.

**2. Public-by-design vs misconfigured is decided by the *default*, not by the response.** ArgoCD
`/api/v1/settings` returning `oidcConfig.clientID` looks juicy. It is not — the field ships in the
product's own API and the OIDC spec requires the client ID to be public. The finding would be a
`clientSecret` in that response. It wasn't there. Read the product's API docs for the endpoint before
you score it.

**3. "Admin panel exists" is not a finding.** `/admin` → `302` on Bitwarden, `403` on Keycloak's
`/auth/admin/`, login form on Portainer. Presence of an admin surface is attack surface, not a
vulnerability. It only becomes reportable when you get past it.

## What IS worth reporting from this sweep

- **A gated sibling proving the ungated one is a mistake.** If `/api/v1/applications` is `401` but
  `/api/v1/settings` is `200` with a secret in it, that contrast is the finding. Without the contrast
  you cannot prove intent.
- **Internal hostnames / plaintext `http://` in a TLS service.** Bitwarden's identity container leaking
  `bitwarden-self-host-identity:5000` is a genuine (low) info-leak that maps internal topology.
- **A default credential that works.** `guest:guest` on RabbitMQ, `admin:admin` on Portainer. Test
  once, never brute-force — programme rules forbid it and one probe settles it.
- **An install-wizard / setup route left reachable.** Portainer `/api/users/admin/check` returning
  `204` on a *fresh* instance is the takeover path. On an initialised instance it is noise.
- **Schema disclosure that converts an opaque error into a map.** A public `/v3/api-docs` on a host
  whose API otherwise returns bare `500`s is the amplifier that turns a Medium into an actionable
  report — see the Auth-Differential Rule in the parent skill.

## Probe list (cheap, one pass, per host)

```
/api/version                  /api/v1/settings            /api/v1/session/userinfo
/api/v1/applications          /api/config                 /api/status
/api/users/admin/check        /api/overview               /api/system/status
/api/projects/search          /api/repositories           /artifactory/api/system/ping
/auth/realms/master/.well-known/openid-configuration
/.well-known/openid-configuration
/installer/                   /program/js/app.min.js      /CHANGELOG.md
```

Score each hit against the table above **before** writing it down. A sweep that produces 40 "200 OK"
and 0 findings is a successful sweep, not a failed one — provided you can say *why* each one is
by-design.
