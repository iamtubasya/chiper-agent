# Auth0 Universal Login provisioning (classic / new UL, DB connection)

Recipe for standing up a verified test account on any Auth0-fronted SaaS
(`<tenant>.eu.auth0.com` / `<tenant>.auth0.com`), driving the hosted login page with Playwright and
capturing the API token for the authed plane. Verified on console.hivecompute.ai (2026-10-26).

## Shape of the flow

```
console.<target>/            -> 302 to <tenant>.auth0.com/authorize?client_id=…&screen_hint=login
                               -> <tenant>.auth0.com/u/login?state=…        (LOGIN form)
click "Sign up"              -> <tenant>.auth0.com/u/signup?state=…        (SIGNUP form)
submit                       -> "Check your inbox" (verification link)
click link in mail           -> <tenant>.auth0.com/u/email-verification?ticket=<T>
                               -> back on the app, now showing the LOGIN form
login + submit               -> <tenant>.auth0.com/u/consent?state=…       (Accept / Decline)
click Accept                 -> app callback with ?code=…                  -> authenticated SPA
```

## The four traps (each cost a cycle)

1. **The two forms use different field names.** The **login** page renders
   `input[name=username]` + `input[name=password]`; the **signup** page renders
   `input[name=email]` + `input[name=password]`. Filling `input[name=username]` on the signup page
   (or vice-versa) times out. Branch on which page you are on.
2. **`wait_for_selector("input")` hangs.** The Auth0 page carries several hidden
   `input[name=state]` / `input[name=connection]` fields; the locator resolves to the first one,
   which is never visible, so the wait times out even though the form is on screen. Always wait for
   the *named* field (`input[name=username]` or `input[name=email]`).
3. **The consent screen is a second gate.** After a successful password submit the browser lands on
   `/u/consent` ("Authorize App … Accept / Decline"). Nothing proceeds until `Accept` is clicked.
   Poll `pg.url` for `consent` and click `button:has-text('Accept')`.
4. **"Something went wrong, please try again later" on the signup form does NOT mean registration
   failed.** Observed live: the form showed that error, yet the verification e-mail arrived, the
   ticket verified, and login succeeded. Treat the *verification e-mail* as the source of truth, not
   the form's error text.

## Capturing the API token

Do not fight the SPA's in-memory auth0 client (`window.auth0Client` is not exposed and
`getAccessToken()` is not reachable from `evaluate`). Read the token from the network instead:

```python
caps = []
def on_resp(r):
    if "auth0" in r.url and "oauth/token" in r.url:
        try: caps.append(r.text())
        except Exception: pass
pg.on("response", on_resp)
# ... drive login + consent ...
for body in caps:
    d = json.loads(body)
    if d.get("access_token"):
        save({"access_token": d["access_token"],
              "expires_at": time.time() + d.get("expires_in", 3600)})
        break
```

The response carries `access_token` (audience `https://<tenant>.auth0.com/api/v2/`),
`id_token`, `refresh_token`, `expires_in` (86400 observed). Decode the JWT to confirm `sub`
(`auth0|<24 hex>`), `azp` (the console client id) and `scope` before using it.

## Verification-link extraction (and the stale-ticket trap)

The mail is from `support@<vendor>.com` with subject "Verify your email" and a link of the shape
`https://auth.<vendor>.com/u/email-verification?ticket=<T>` (sometimes wrapped in a
`mandrillapp.com/track/click/...` redirect — unwrap it).

**Match the ticket to the account you just registered.** A naive "newest mail containing
`Verify your email`" grabs a *previous* account's ticket when you provision several in one session,
and the verification then silently does nothing for the new one. Filter on the recipient address or
on a marker in the body, and assert the ticket is fresh.

## After the browser: the API plane usually needs one more call

A verified Auth0 identity is not the same as a provisioned product account. On Hivenet Compute the
user row existed (`GET /users/self` → 200 with `id`, `org_id`, `org_role`) but
`GET /users/self/compute-profile` → 404 "no compute profile for this user", and
`POST /users/self/compute-profile/chat` → 503 "Could not verify the share record contents" until a
profile existed. Generalise: after login, call the app's own "ensure profile" endpoint (or repeat
whatever the SPA does on first load) before assuming a 503 is an authorization failure.

## Minimal working skeleton

```python
from playwright.sync_api import sync_playwright

def wait_field(pg, name, timeout=40000):
    pg.wait_for_selector(f"input[name={name}]", timeout=timeout)

with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    ctx = br.new_context(viewport={"width": 1300, "height": 1000})
    pg = ctx.new_page()
    pg.goto("https://console.<target>/", wait_until="load", timeout=60000)
    wait_field(pg, "username")                 # LOGIN page
    pg.click("text=Sign up"); time.sleep(6)
    wait_field(pg, "email")                    # SIGNUP page  <-- different name
    pg.fill("input[name=email]", EMAIL)
    pg.fill("input[name=password]", PWD)
    pg.click("button[type=submit]"); time.sleep(10)
    # -> "Check your inbox"; verify via the ticket link, then come back and log in
    pg.goto("https://console.<target>/", wait_until="load", timeout=60000)
    wait_field(pg, "username")
    pg.fill("input[name=username]", EMAIL)
    pg.fill("input[name=password]", PWD)
    pg.click("button[type=submit]"); time.sleep(8)
    if "consent" in pg.url:
        pg.click("button:has-text('Accept')"); time.sleep(10)
```

## Hygiene

- One account per `+alias` of the operator mailbox; log every account (including the incidental
  ones) in `ENGAGEMENT_LOG.md` with the org id / user id the API returns.
- Record the org id and user id from `GET /users/self` — they are the objects every later
  cross-tenant probe needs.
- If the product bills per resource (GPU, VM), never deploy: a €0 balance is the entitlement and
  probing authorization does not require spending.
