# Reconstructing a login/auth state machine from the public front end

Goal: turn "the login is a JS SPA, I can only see the first screen" into a list of real
endpoints with **exact request bodies**, so the auth surface can be probed methodically.

Why this beats guessing: the SPA's API client is shipped to every anonymous visitor. It

- names the first-step endpoint (the one the SPA calls before you even type a password),
- gives the **exact field names** for every stage (this is where most time is lost),
- enumerates sibling endpoints the UI only reaches on rare paths (OTP, 2FA, refresh, revoke),
- and tells you the response contract (`methods[]`, `continuationToken`, `action.type`) so you
  can reason about the state machine instead of poking at it.

## Step 1 — Capture the first step from the UI (30 seconds)

Filling the login form with a junk username is enough. You want the first XHR the page fires.

```python
page.on("request",  lambda r: rec(r.method, r.url, r.post_data) if "/auth" in r.url else None)
page.on("response", lambda r: rec(r.request.method, r.url, r.status,
                                  r.text()[:2000]) if "/auth" in r.url else None)
page.goto(signin_url, wait_until="networkidle", timeout=45000)
page.fill("input[type=email]", "doesnotexist@example.com")
page.press("input[type=email]", "Enter")
page.wait_for_timeout(5000)
```

Then repeat with the password field visible to capture **stage 2** (the second POST), which is
the one carrying the credential — it is a different request and often a different field name.

## Step 2 — Pull the route chunks, not just the shell

The landing HTML usually preloads only the shell. React Router ships its full route table in an
inline manifest, and each route is its own chunk:

```bash
curl -s "$BASE/ui/auth/signin" -o signin.html
grep -oE '/ui/auth/assets/[A-Za-z0-9_.-]+\.js' signin.html | sort -u    # preloaded shell
grep -oE 'assets/[A-Za-z0-9_.-]+\.js' *.js | sort -u                   # ALL chunks incl. routes
```

`window.__reactRouterManifest` lists every route module; names like `signin._index-*`,
`signin.otp-*`, `reset-*`, `AuthProvider-*`, `useIdentifierFirstFlow-*` tell you which files
carry the auth logic. Download those and grep the **API client class** (the class with
`async authenticate(...)` / `postAbortStale(...)`), not the view components.

```bash
grep -l "initIdentifier\|postAbortStale\|continuationToken" *.js   # the client module
```

On a minified single-line bundle, `grep -E '.{0,25}/api/...'` will time out. Use Python:

```python
import re, glob, collections
pat = re.compile(r'/(?:api|auth|jmap|v[0-9]|opt-in|accountapi|signupapi|billing)[A-Za-z0-9/_.{}$:+-]{2,70}')
c = collections.Counter()
for f in glob.glob("*.js"): c.update(pat.findall(open(f, encoding="utf-8", errors="replace").read()))
```

Also beware of **false positives from source-module paths**: an unminified/bundled file lists
`/api/utils/adminapi.js`, `/api/client.js`, `/api/2FA/index.js` — those are module specifiers,
not HTTP routes. Cross-check every candidate with a real request before believing it.

## Step 3 — Worked case (Atmail auth SPA, 2026-09-30)

Captured by the two calls above, all on `login.junara.com`:

| Endpoint | Shape | Notes |
|---|---|---|
| `POST /auth/init` | `{"username":"<any>"}` | returns `{"continuationToken":"<JWE>","methods":[{"type":"password"}]}` for ANY well-formed address, existing or not |
| `POST /auth` | `{"method":"password","token":"<continuationToken>","password":"..."}` | the field is **`token`**, not `continuationToken` |
| `POST /auth` | `{"method":"otp","token":"...","password":"<6-digit code>"}` | the OTP code goes in **`password`**, there is no `code` field |
| `POST /auth` | `{"method":"require2FA","token":"...","password":"<totp>","remember":30}` | 2FA step |
| `POST /auth` | `{"method":"reissue","token":"<fresh>","accessToken":"<old>"}` | the refresh path |
| `POST /auth/otp` | `{"username":"...","intent":"totp-login"\|"password-reset"}` | returns `{"result":"otp scheduled"}` for any address |
| `GET /auth/me`, `/auth/password-policy` | bearer | 401 unauthenticated |
| `POST /auth/token`, `POST /auth/revoke` | OAuth 2.0 | public-client aware |
| `GET /auth/.well-known/jwks.json` | JWKS | public signing key |
| `GET /auth/authorize` | OAuth authorize | PKCE required |

## Field-name traps — the symptom → cause table

This is the single highest-value table in this file. Every row cost real time.

| Symptom | Cause |
|---|---|
| `500 {"error":"server_error","details":["internal server error #<id>"]}` on every input | **wrong field name** — the handler dereferenced a missing/renamed key. Re-read the client source and use its literal key names |
| `400` with an **empty body** on every input | a required field is absent entirely (e.g. `token`), or the token expired |
| `400 {"error":"invalid_request","error_description":"...POST body can not be empty."}` **while you are sending a body** | the endpoint is form-encoded, not JSON — switch `Content-Type: application/x-www-form-urlencoded` (`&`-joined pairs) |
| `400 "Query argument <x> is required, but not found"` | you are one parameter short; the message names it (this is how `code_challenge` was found to be mandatory) |
| `403 Forbidden` with a short fixed-length body | edge/WAF block, not the app — see `bot-protected-target-testing` §3a |
| `400 API key not valid` for a key you know is real | you are re-testing a **redacted display string**; re-read from the file |

## Step 4 — Interpret the results honestly

- **Uniform responses across existing and non-existent accounts = no enumeration oracle.** Test
  it: 4-6 usernames (2 random, 4 real-shaped) through `/auth/init` **and** stage 2, then compare
  `(status, len, sha256(body))`. Record the negative; do not hand-wave "probably enumerable".
- **A capability endpoint that answers identically on every host is not a finding.** `GET /auth`
  returning the same `{"methods":[...]}` on 143 hosts is product capability.
- **A server error is not a finding either.** An unhandled 500 that discloses only a random
  request id discloses nothing — say so and move on.
- **A refresh endpoint (`method: "reissue"`) is the highest-value thing to poke**, because it
  takes a caller-supplied `accessToken`. Feed it `""`, a random string, and a well-formed fake
  JWT, and compare. On this target every variant returned the same generic 500 — no bypass, and
  the uniform answer is itself the evidence that the token is actually validated.
- **OAuth surfaces:** check `client_credentials` and other grants against `/auth/token`. A public
  client is correctly refused (`invalid_grant ... client is marked as public`). Note that
  requiring PKCE **even for `response_type=token`/`none`** is unusual and worth recording as a
  control that works.

## Boundary — what NOT to do on this surface (policy, not capability)

- **Do not trigger password-reset / OTP mail to addresses you do not control.** Most programs
  list "spamming notification systems" as prohibited activity. If you want to prove the mail
  actually goes out, use a **disposable inbox you own** and poll it; one or two requests, not a
  burst.
- **"otp scheduled" is not proof of delivery.** On this target a disposable inbox received
  nothing in four minutes across 25 polls, so the honest verdict was *inconclusive* — not
  "unthrottled mail bomb". Never promote an unverified delivery claim into a finding.
- **Do not brute force codes.** Measure whether throttling exists; that is the reportable fact,
  and on many programs even that lands as Informative.
- **Same for signup verification dead-ends.** If a signup flow's verification mail never arrives,
  the blocker is external, not a vulnerability. Record it as a coverage gap and stop.
