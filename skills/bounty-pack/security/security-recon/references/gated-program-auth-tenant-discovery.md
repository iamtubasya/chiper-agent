# Discovering a gated developer-program's separate Auth0 tenant (open self-registration)

Trigger: a SaaS has a "developer program" / "integration platform" / "build your own X" that is visibly
gated behind "Request access" (a Typeform / contact-sales form, "preview access", manual approval), and you
need an API key (Bearer token) to reach the juicy internal API (encryption oracle, proxy, user/admin CRUD).

## Technique

1. **Read the dev portal login page's Sign-in / Request-access `<a href>`.** It hands you the OAuth entry
   point verbatim:
   ```
   <a href="https://<tenant>/authorize?client_id=<id>&response_type=code&scope=openid+profile+email&redirect_uri=<uri>">
     Sign in</a>
   ```
   This yields the **tenant**, **client_id**, **scope**, and **redirect_uri** in one fetch — never guess.
   The developer/partner program very often uses a **SEPARATE tenant from production**
   (prod = custom domain `login.<apex>`, dev = `<org>-dev.us.auth0.com` or `<org>.us.auth0.com`).

2. **Test open self-registration on that tenant** (often left open while production enforces captcha/bot
   detection):
   ```bash
   curl -s -X POST https://<tenant>/dbconnections/signup \
     -H 'Content-Type: application/json' \
     -d '{"client_id":"<id>","connection":"Username-Password-Authentication","email":"<you>","password":"<pw>"}'
   # 200 {email, email_verified:false, _id, ...}  = OPEN signup, no bot detection
   # 401 {"name":"requires_verification"}          = bot detection ON (this tenant is protected)
   ```
   Prod tenants answer `connection not found` for the default name (their connection is custom, e.g.
   `unito`); the dev tenant typically keeps the default.

3. **Complete the login via the authorize code flow** (NOT ROPC — ROPC's `/usernamepassword/login` and
   `/oauth/token` grant_type=password often return 403 `AnomalyDetected` / `Invalid state` on these
   tenants). Sequence with a `requests.Session`:
   1. `GET <authorize_url>` → follows to `/u/login/identifier?state=...`; grab `name="state" value="..."`.
   2. `POST /u/login/identifier` with `{state, username, action:default}` (form-urlencoded) → `/u/login/password`.
   3. re-grab `state`, `POST /u/login/password` with `{state, username, password, action:default}` →
      redirect to `redirect_uri?code=...` (or an error).

## Pitfalls

- **The redirect_uri admin panel may be decommissioned** — after a successful login you may land on
  `redirect_uri` returning 404 or `?error=server_error&error_description=...something went wrong...`.
  Open signup on the dev tenant then grants *nothing* → the finding is Low/Info, and often OOS as
  "third party / no impact". Confirm what the self-registered account actually grants BEFORE rating it
  above Low/Info.
- **Open signup ≠ open login.** Signup can be open (`/dbconnections/signup` = 200) while login still hits
  anomaly detection. Use the signed-`state` code flow, not ROPC.
- **The prod API key is a separate artifact.** A dev-tenant account is not automatically an
  integrations-platform "user" with an `apiKey`. Those are issued manually; `POST /users` and
  `/users/{id}/apiKey` on the platform both require an existing valid Bearer token (circular — no
  self-serve path).