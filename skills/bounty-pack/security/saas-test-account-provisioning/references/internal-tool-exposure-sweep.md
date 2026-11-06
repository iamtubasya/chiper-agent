# Internal-tool exposure sweep — the estate pass that follows a self-registration hit

Companion to `self-registration-impact-proof.md`. Once one publicly-reachable **internal** tool is found
(Mattermost, Git, chat, BI, multisig UI), the same company almost always runs siblings that are reachable
too. Sweep them before writing the report — the sweep either finds more findings or produces the honest
"controls held" table that keeps the one real finding credible.

Verified on the Blink estate (2026-10-13), `blink.sv` + `blinkbtc.com`: 10 previously-unknown hosts found
in one pass, each classified in <10 requests.

## 1. Enumerate — certspotter, not crt.sh

`crt.sh` returned `502` repeatedly; the certspotter API did not:

```bash
curl -s "https://api.certspotter.com/v1/issuances?domain=<corp-domain>&include_subdomains=true&expand=dns_names"
# -> JSON list; collect every e.dns_names[], strip "*." and lowercase
```

Do it for **every** corporate domain (the product domain and the corporate domain are different
estates — `blink.sv` had 67 names, `blinkbtc.com` had 26, and the juicy ones were in the second).
A host inventory you already built for one domain tells you nothing about the other; check that your
"live hosts" file actually contains the second domain before assuming the estate is covered.

## 2. Fingerprint, then classify by service class

Probe `https://<host>/` once (status + `<title>` + `Server`) and group by what the title says. The
per-class verdict probes that actually decided it:

| class | probe (unauthenticated) | "held" signal | "finding" signal |
|---|---|---|---|
| Mattermost | `GET /api/v4/config/client?format=old` | `EnableOpenServer:false` | `true` + `EnableUserCreation:true` |
| Forgejo / Gitea | `GET /user/sign_up`, then `GET /explore/repos`, `GET /api/v1/version` | page text **"Registration is disabled"**; `/api/v1/*` → `403 {"message":"Only signed in user is allowed to call APIs."}`; `/explore/repos` redirects to login | real signup form; public repo list |
| Matrix | `POST /_matrix/client/v3/register {}` (GET → `405`) | `M_FORBIDDEN "Registration has been disabled. Only m.login.application_service registrations are allowed."` | `m.login.dummy` / registration_token flow returned |
| Grafana | `GET /api/health`, `GET /api/dashboards/home` | health `200` (version only) + dashboards `401` | anonymous dashboards / org list |
| Specter Desktop | `GET /` | a **password form** (`/auth/login`, `csrf_token`) | app UI with no auth (Bitcoin wallet management — would be critical) |
| Concourse | `GET /api/v1/info`, `/api/v1/workers`, `/api/v1/pipelines` | `401` on workers/user, `[]` on pipelines | populated pipelines/teams |
| Next.js product app | `GET /api/user/*`, `/api/auth/*`, then method-probe the rest | `401 {"error":"Authentication required - no session token"}` | user data, unauth invoice/create endpoints |

Rules for this pass:
- **Never brute-force, guess or spray credentials at an exposed admin login.** A login form is a "held"
  verdict; report the exposure as attack surface only (version + endpoint), never as access.
- **Read what a brand-new account could see before claiming impact** — on Git that is "public repos"
  (`/explore/repos`), on chat it is the open-invite team. If nothing is visible to a fresh account, the
  finding is the account itself, not data.
- **A page that renders "registration is disabled" is a HELD control** and belongs in the coverage
  table, not in the findings list. Saying so explicitly is what steers triage away from a downgrade.
- Fingerprint duplicates: two hosts serving the **same `buildId`** (Next.js) are the same build; test one.

## 3. Brand-name collisions — do not attribute a resource without evidence

Bucket/CDN enumeration by brand name (`blink-web`, `blink-staging`, `blink-files`, …) returned
publicly-listable buckets — none of which belonged to the target. Evidence required before any claim:

1. object keys referencing the target's domain/paths (`blink.sv`, `/var/www/...`),
2. a reference from the target's own web app or mobile source (`assets.*`, `storage.googleapis.com/<name>`,
   `*.r2.dev`),
3. **or** nothing — in which case it is a collision: record it as a checked-and-cleared negative.

Read **listing metadata only** while deciding; never download objects from a third party's bucket, and
say in the notes that you did not (a PHP app's `driving_licence_user/*` uploads in an unrelated bucket is
someone else's incident, not evidence).

## 4. Cover the whole companion surface in the same pass

Also cheap and worth the requests on the same host list: public `*.js.map` (Next.js source maps → `404`
on all five apps here = held), `robots.txt`/`.well-known/*`, and the OIDC discovery document
(`/.well-known/openid-configuration` shows `grant_types_supported` + `scopes_supported` — the fastest
read of an OAuth server's scope model before touching `/oauth2/auth`).

## 5. Evidence shape

One `host_inventory_<domain>.json` (status, server, title per host) + one probe-verdict JSON per class
(the raw response body is the proof), plus a coverage table in the report:

```
tested: <hosts> — registration disabled (Forgejo/Matrix), auth-gated (Grafana/Specter/Concourse),
        hardened API (terminal app) ; untested: <what you did not reach>
```
