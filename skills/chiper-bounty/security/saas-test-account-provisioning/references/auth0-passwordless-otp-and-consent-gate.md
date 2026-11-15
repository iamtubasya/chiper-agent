# Auth0 passwordless email-code login + the post-login consent gate

Verified on `dashboard.aghanim.com` (Aghanim), 2026-10-27. Tenant: Auth0 **Universal Login classic**,
custom domain `auth0.<target>` (CNAME to the IdP), passwordless **email code only** — no password field
exists anywhere in the flow.

Companion to `auth0-universal-login-provisioning.md`, which covers the **DB-connection** variant
(username/password). Read this one when the login page has no password step.

---

## 1. Field names that actually work (and the ones that time out)

| step | URL | input | trap |
|---|---|---|---|
| identifier | `/u/signup/identifier`, `/u/login/identifier` | `input[name="email"]` | **`type="text"`**, not `type="email"` — `pg.fill('input[type="email"]', …)` hangs 30 s |
| challenge | `/u/login/passwordless-email-challenge` | `input[name="code"]` | rendered *after* a client-side transition; fill too early → "element not found" |

Both pages also carry 9+ hidden inputs (`state`, `js-available`, `webauthn-available`, `webauthn-platform-available`, `is-brave`,
`connection` ×2) — so:
- `wait_for_selector("input")` returns instantly on a *hidden* `state` field and then everything else races;
- `input[type="text"]` matches the hidden ones too. **Always select by `name`.**

```python
await pg.get_by_role("link", name="Sign up").first.click()      # /u/signup/identifier
await pg.fill('input[name="email"]', EMAIL)                     # type=text, NOT type=email
await pg.click('button[type="submit"]')                         # -> passwordless-email-challenge
await pg.fill('input[name="code"]', code)
await pg.click('button[type="submit"]')
```

Dump the truth in one call instead of guessing:

```python
await pg.eval_on_selector_all("input",
  "e=>e.map(x=>({n:x.name,t:x.type,id:x.id,ph:x.placeholder}))")
```

## 2. Reading the OTP (Gmail API, refresh-token flow)

Mail arrives from `notifications@<target>.com` within ~4 s, subject `"<6 digits> is your <Product>
verification code"`. Reuse the operator's token at `%LOCALAPPDATA%\hermes\google_token.json`:

```python
d = json.load(open(TOKEN))
tok = requests.post(d["token_uri"], data={
    "client_id": d["client_id"], "client_secret": d["client_secret"],
    "refresh_token": d["refresh_token"], "grant_type": "refresh_token"}).json()["access_token"]
q = "newer_than:2m from:%s" % sender          # search by SENDER, not "last 5 messages"
```

Two traps, both hit live:
1. **Search by sender + window, never "the newest N messages."** A shared mailbox returns another
   engagement's code (a Genians trial code was the first hit in one poll) and you paste the wrong OTP.
2. **Extract by subject, not by "first 6-digit run in the body."** HTML bodies are full of sizes and
   colours; the subject line is the reliable channel here.
3. The IdP invalidates the previous code when you request a new one — if the flow is stuck, request
   again and re-read rather than retrying the stale code.

## 3. Where the session ends up

After the code is accepted you land on the app (`/onboarding`), and the credential is **not** a cookie:

- cookies: `auth0`, `auth0_compat`, `did`, `did_compat`, `_legacy_auth0.<client>.is.authenticated`,
  `csrf_token`, `__cf_bm`, posthog;
- `localStorage['@@auth0spajs@@::<client_id>::https://<audience>::openid profile email offline_access']`
  = `{"body": {"access_token": …, "refresh_token": …, "scope": …, "audience": …}, "expiresAt": …}`
- a second key holds `id_token` + `decodedToken`.

Harvest it without guessing key names — `storage_state()` then walk every origin's localStorage and
`json.loads` each value, keeping the one with a `body.access_token`:

```python
for o in state["origins"]:
    for i in o["localStorage"]:
        try: v = json.loads(i["value"])
        except Exception: continue
        if isinstance(v, dict) and isinstance(v.get("body"), dict) and "access_token" in v["body"]:
            TOKEN = v["body"]["access_token"]
```

(One value in that origin is not JSON at all — bare `json.loads` over `i["value"]` raises
`JSONDecodeError: Expecting value: line 1 column 1`. Skip, don't abort.)

Decode the JWT before you use it: `aud` is the vendor audience (`https://<target>`), `azp` is the SPA
client id, `scope` is `openid profile email offline_access` with **no `permissions` claim** — so
authorization is server-side role lookup, not token scopes. That means a forged/`alg:none` token gets you
nothing even if signature validation were weak.

## 4. The 451 consent wall (the actual blocker)

`GET /profiles/me` → `451 {"detail":"Terms of service has changed"}`, and nearly every other admin
endpoint inherits the gate. A few stay open, which is the tell that the session is fine:

```
200  GET /companies/games                  # [{name:"Demo Corp", games:[…]}]  <- auto-provisioned tenant
200  GET /invites/me                       # None
200  GET /customers/outdated_agreements    # {"terms":true,"privacy":true,...}
451  GET /profiles/me
```

Unblock by calling the SPA's own endpoint (grep the bundle for `accept_agreements`):

```python
POST /dashboard/v1/customers/accept_agreements {}                      -> 204   # company-less customer
POST /dashboard/v1/companies/{company_id}/profiles/accept_agreements   -> 204   # invited member
```

Then `/profiles/me` returns the customer object and the whole plane opens.

The UI path is unreliable and not worth debugging: the visible "Accept" button was the **cookie banner**,
and checking `input[name=privacy]` / `input[name=terms]` set `checked=true` without firing React's
`onChange` (the §3f/§3f-label tell) — the form never submitted. One API call replaced ten minutes of DOM
work; this is the same "when the page won't drive, call the endpoint" rule as Step 6b.

## 5. What a fresh passwordless signup actually gets you

Worth knowing before you plan the authed suite — on this vendor, self-signup provisions a **read-only**
identity:

```
GET /v1/companies/{id}/profiles/me
 -> {"type":"regular","role":"user","mode":0,
     "permissions":["campaign:read","store:read","transaction:read","refund:read","dispute:read", …]}
```

Every write (`items`, `coupons`, `api_keys`, `customer_roles`, `games`, `checkout_links`,
`game_settings`) answered **403**. So the account buys you: a real tenant id pair for cross-tenant
sweeps, a real read plane, and a differential by role — and it explicitly does **not** buy the write
plane. Say that as a coverage bound with the exact 403 evidence; do not report "no findings" on a plane
you could not reach, and do not burn time re-trying the same 403s.

## 6. Checklist

- [ ] `input[name="email"]` (type=text) filled, submit → `passwordless-email-challenge`
- [ ] OTP read by sender + subject from the operator mailbox — not "newest message"
- [ ] `input[name="code"]` filled, submit → app URL (not the IdP)
- [ ] `storage_state()` saved; `body.access_token` extracted from `@@auth0spajs@@…`
- [ ] JWT decoded (`aud`, `azp`, `scope`, presence of `permissions`)
- [ ] `/profiles/me` (or `/me`) hit FIRST — any 451/blanket-403 → consent gate, not broken auth
- [ ] `customers/accept_agreements` (and `companies/{id}/profiles/accept_agreements`) called
- [ ] own role + permission list recorded before planning the write-plane tests
