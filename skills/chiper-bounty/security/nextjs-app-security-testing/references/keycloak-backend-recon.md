# Keycloak-backed Next.js target — probe battery

Worked example: **Mamentis**, 2026-10. `app.mamentis.ai` = Next.js App Router + Auth.js (next-auth);
`auth.mamentis.ai` = Keycloak (≥25, asset paths `/resources/q8tw0/...`); realm `mamentis`; OIDC client
`mamentis-app`. Everything below is unauthenticated and non-destructive. Carry the exact commands into the
report — a "hardened" verdict is only worth anything if the probes are reproducible.

## 0. Detect the pattern

| signal | meaning |
|---|---|
| `/api/auth/providers` returns `{ "<idp>": { id, name, type: "oidc", signinUrl, callbackUrl } }` | Auth.js in front; `callbackUrl` names the IdP |
| `/api/auth/session` → literal `null` unauthenticated | Auth.js session endpoint |
| `/api/login` → `307` to `<auth-host>/realms/<realm>/protocol/openid-connect/auth?...` | Keycloak, PKCE S256, signed-JWT `state` |
| `__Host-*` cookie with a `hex|hex` value | Rails-ish CSRF convention, but on Next.js apps it is app-issued; not a framework tell on its own |
| app-level `/api/*` routes all `307 → /login` | edge middleware auth; re-test with all verbs |

## 1. OIDC discovery — read it as a configuration statement, not a formality

```bash
curl -s "https://<auth-host>/realms/<realm>/.well-known/openid-configuration"
```

Extract and *interpret*:

- `grant_types_supported` — advertised does **not** mean allowed for *your* client. Mamentis advertised
  `password`, `client_credentials`, `implicit`, `device_code`, `token-exchange`, `uma-ticket`, `ciba`; the
  client itself allowed none of them.
- `scopes_supported` — custom scopes leak domain modelling. Mamentis exposed `governance:read` /
  `governance:write`, i.e. an authorization model worth probing once you have a token.
- `code_challenge_methods_supported` — if `plain` is present, PKCE downgrade is worth a look.
- `registration_endpoint` — presence ⇒ consider Dynamic Client Registration (below).
- `/.well-known/uma2-configuration` → `200` ⇒ Keycloak authorization services are enabled on the realm
  (permission/resource APIs exist behind auth).

## 2. Grant allow-list (the highest-signal cheap probe)

One request per grant, using the public `client_id` from the authorize URL and **no secret**:

```bash
T=https://<auth-host>/realms/<realm>/protocol/openid-connect/token
curl -s -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'grant_type=client_credentials&client_id=<client>' "$T"
curl -s -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'grant_type=password&client_id=<client>&username=<clearly-fake>@example.invalid&password=<fake>' "$T"
curl -s -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'grant_type=refresh_token&client_id=<client>&refresh_token=x' "$T"
curl -s -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'grant_type=urn:ietf:params:oauth:grant-type:device_code&client_id=<client>&device_code=x' "$T"
```

Reading the result:

- `401 {"error":"unauthorized_client","error_description":"Invalid client or Invalid client credentials"}`
  on **all** grants ⇒ the client is **confidential** and ROPC/device/refresh are off. Clean negative; say so.
- `400 {"error":"invalid_grant"}` instead ⇒ the grant IS enabled and you have reached credential validation
  (a materially different posture — ROPC enabled means credential stuffing is a live path).
- `200` with an `access_token` ⇒ public client with a service account: authentication bypass. Escalate.

The fake-username probe is **one** request: it discriminates `unauthorized_client` (grant off) from
`invalid_grant` (grant on) without any brute-force behaviour. Do not loop it.

Also: `GET /protocol/openid-connect/userinfo` without a token must be `401`.

## 3. Anonymous Dynamic Client Registration + the `Trusted Hosts` policy

A `registration_endpoint` in discovery is worth one probe, because open DCR (register a client with an
attacker `redirect_uri`) is a direct path to authorization-code theft → account takeover.

```bash
U=https://<auth-host>/realms/<realm>/clients-registrations/openid-connect
curl -s -X POST -H 'Content-Type: application/json' -d '{}' "$U"
```

Discriminator: a body of `{}` cannot create anything, so the status tells you the gate.

| result | meaning |
|---|---|
| `401` / `403 insufficient_scope … Policy 'Trusted Hosts' rejected request … Host not trusted.` | anonymous DCR denied — good |
| `400` + `invalid_client_metadata`-style body | **the request reached validation without credentials ⇒ DCR is OPEN.** Escalate: register a client with an attacker redirect_uri, then (RFC 7592) delete it via the returned `registration_access_token` and record the client_id as evidence |

**The Host-header sweep is usually a dead end — prove it instead of assuming it.** Keycloak's Trusted Hosts
policy evaluates the request `Host`, which invites spoofing the internal trusted name. Whether that works
depends entirely on the front proxy:

```bash
for H in localhost 127.0.0.1 <auth-host> <apex> app.<apex> api.<apex> keycloak internal <lb-ip>; do
  printf '%-22s ' "$H"
  curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' \
    -H "Host: $H" -d '{}' "$U"
done
```

- If only `<auth-host>` returns the policy response (`403`) and every other Host returns a proxy `404`, the
  load balancer **routes by Host**, so only `<auth-host>` ever reaches Keycloak and the trusted-host list
  cannot be spoofed from outside. That is a clean, reportable negative — and it cost nine requests.
- If a *different* Host returns `400`/`403`-with-the-realm-reachable, you just found the bypass.

## 4. redirect_uri strictness matrix

Drive the authorize endpoint directly and compare against an exact-match control (the control should `302`;
anything else must be `400`, not a redirect to the attacker):

```bash
CZ="https://<auth-host>/realms/<realm>/protocol/openid-connect/auth?response_type=code&scope=openid&client_id=<client>"
# attacker domain | suffix trick app.host.evil.tld | userinfo app.host@evil.tld
# path traversal appended to the real path | query append ?next=https://evil | omitted entirely
```

Mamentis: every variant `400`, only the registered URI `302`. Register the *omitted* case too — it is the
classic sloppy-config tell.

## 5. Remaining unauthenticated state checks

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<auth-host>/admin/master/console/            # expect 404
curl -s -o /dev/null -w '%{http_code}\n' https://<auth-host>/realms/<realm>/login-actions/registration
curl -s https://<auth-host>/realms/<realm>/account/                                            # 200 = account console live
```

- registration returning the **sign-in page** (400) ⇒ self-registration disabled. Record it: it is what
  makes the authenticated surface unreachable, which is a reportable coverage fact.
- admin console 404 ⇒ the management UI is not exposed on the public host.
- the login page itself lists the configured social IdPs as `/realms/<realm>/broker/<alias>/login` links
  (`kc-social-provider-name` / `social-<alias>` ids). Enumerate them — they are the provisioning path.

## 6. The provisioning decision gate (do not skip this)

If registration is disabled and the marketing CTAs are dead, the only way in is a social IdP. Before touching
it, weigh:

1. Signing in **creates a real account** on the target and sends the target a real identity.
2. Which mailbox/provider you use is the operator's identity. Do not spend it unilaterally.
3. The finding class you are chasing is real (IdP auto-provisioning ⇒ registration bypass; IdP
   auto-link-by-unverified-email ⇒ account takeover), and it is often the highest-value item on such a target.

Default action: **stop, report the blocked surface explicitly in the deliverable, and ask** — offering a
throwaway IdP account (fresh GitHub/Google) as the proposed method. A blocked surface documented with the full
negative matrix is a legitimate round outcome.
