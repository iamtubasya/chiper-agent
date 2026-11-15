# Relying-party (client) checks — the app IS the OIDC client

Most web targets are **Relying Parties (RPs)**: the app itself holds the `client_id` (public) and
302s to Keycloak/Auth0/Entra. The IdP is frequently a **different host** (often out of scope), so the
testable surface is the RP plus the RP's *client registration* at the IdP. The classic IdP-side
checks (redirect_uri validation, PKCE, state) are covered in the SKILL; these are the RP-side checks
that get missed. Field-validated on a Swiss media SPA (`sunshine.ch`, Keycloak realm behind a BFF
pattern, 2026-10).

## 0. Recognise the pattern (10 seconds)

```bash
curl -s -D - -o /dev/null "https://$TARGET/auth/login" | grep -iE '^HTTP|^location|^set-cookie'
# -> 302 location: https://<idp>/realms/<realm>/protocol/openid-connect/auth?client_id=<rp>...&redirect_uri=https%3A%2F%2F<TARGET>%2Fauth%2Fredirected...
```
The `redirect_uri` is fixed server-side and the `client_id` is the brand's client. Note the realm and
`client_id` — you will reuse both. `/auth/logout` 302s to the IdP `end_session_endpoint`.

## 1. Enumerate the client's enabled flows, then test ROPC

`grant_types_supported` in the realm discovery doc tells you which flows the *realm* advertises, not
which the *client* allows — so test the client directly:

```bash
curl -s "https://<idp>/realms/<realm>/.well-known/openid-configuration" \
  | grep -oE '"grant_types_supported":\[[^]]*\]'

# ROPC (direct access grant) against the RP's own client_id, NO secret:
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  "https://<idp>/realms/<realm>/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=<rp-id>&username=probe@example.invalid&password=x&scope=openid"

# and the built-in Keycloak client:
#   client_id=account  -> often "Client not allowed for direct access grants"
```
Interpretation:
- `401 unauthorized_client` / "Invalid client or Invalid client credentials" → the client is
  **confidential** (needs a secret) and/or ROPC is off → safe.
- `400` "Client not allowed for direct access grants" → the client EXISTS but ROPC is disabled → safe.
- **HTTP 200 with an `access_token`** → ROPC is live for a public client: credential-stuffing and
  **MFA-bypass without any rate-limit friction** (Medium+, and it sidesteps the browser flow entirely).

Send only 1–2 probes. This is a config check, not a credential brute-force.

## 2. Does the RP honour a user-supplied redirect / return param?

Nearly every RP sets `redirect_uri` server-side and ignores attacker-supplied overrides — but *verify*,
because when one does honour it, it is auth-code theft → ATO.

```bash
BASE=$(curl -s -D - -o /dev/null "https://$TARGET/auth/login"            | grep -i location)
for q in redirect_uri redirect return_to next url continue; do
  LOC=$(curl -s -D - -o /dev/null "https://$TARGET/auth/login?$q=https://evil.test/cb" | grep -i location)
  echo "$q -> $(printf '%s' "$LOC" | sed -n 's/.*redirect_uri=\([^&]*\).*/\1/p')"
done
# If every line shows the SAME server-set redirect_uri -> not honoured -> safe.
```

## 3. Probe the RP callback for graceful error handling

```bash
curl -s -D - -o /dev/null "https://$TARGET/auth/redirected"                       # no code/state
curl -s -D - -o /dev/null "https://$TARGET/auth/redirected?code=AAA&state=BBB"    # bogus code
```
- Raw **HTTP 500** with a message like `request to the redirect_uri path but there's no session state
  found` = a robustness gap (app-specific, Low/Info) **and** useful negative evidence that `state` IS
  bound to a session — i.e. login-CSRF/code-injection is *not* trivially open. Do not escalate to ATO
  without proof the code/token actually moves to an attacker host.
- A clean redirect to `/` or the login page = better handling.

## 4. Scope discipline

The IdP host (`login.<vendor>.ch`, `*.auth0.com`, `*.okta.com`) is usually **not** in the target's
scope even when the RP security.txt routes reports to a bug-bounty program. Record it as
authorization context, but every *finding* must land on the RP asset. Do not fire test traffic at the
IdP until scope is explicitly clear — and if the program is a third-party managed one, check the
program's published scope list actually contains the brand before treating it as open (a security.txt
can point at a managed program whose public program list does not include the host).

## 5. Other RP-side observations worth recording

- The RP's `window.app` / SSR config often exposes the SSO entry (`triggerAuthFlow`, `userAccountsEnabled`)
  and the API path list — pair this with `hunt-spa-api` §2b.
- Crash-on-missing-param callbacks (500s) are a recurring Low/Info hardening finding on these stacks.
