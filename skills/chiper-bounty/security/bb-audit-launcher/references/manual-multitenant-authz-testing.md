# Manual multi-tenant / authz testing (no-scanner engagements)

Companion to the **VENDOR-FORBIDS-SCANNERS BRANCH** in SKILL.md. Use when the program forbids
automated tools, so cross-tenant and access-control questions must be answered by hand.
Proven end-to-end on freeagent.com (0 exploitable findings, 20 verified negatives).

## 1. Build the test assets (operator-owned, required by most programs)

| asset | how |
|---|---|
| tenant A | sign up a trial with the operator's real address |
| tenant B (disposable) | sign up again with a **plus-address** (`user+fa2@…`) — lands in the same inbox, is a separate account |
| low-privilege user | create a user in tenant A with the lowest role/permission and **send invitation** |
| OAuth app | register on the program's in-scope developer portal, redirect to `https://localhost:8443/callback` |

Getting a **token per identity** (needed to test authz, not just the web UI): OAuth
authorize → approve → exchange `code` at the token endpoint with HTTP Basic
`client_id:client_secret`. Registering 2 redirect URIs makes the "second registered URI" case testable.
The client secret is usually shown **once** at creation / on "generate new secret" — capture it then.

## 2. Intercept the OAuth code without a reachable callback host

The callback points at a local port you may not be serving, and the browser lands on
`chrome-error://chromewebdata/`. Don't fight it — observe instead:

```python
pg.on("request",  lambda r: caught.update(url=r.url) if "localhost:8443" in r.url and "code=" in r.url else None)
pg.on("response", lambda r: caught.update(url=r.headers.get("location","")) if "localhost:8443" in (r.headers.get("location","") or "") else None)
ctx.route("https://localhost:8443/**", lambda route: (caught.update(url=route.request.url), route.fulfill(status=200, body="ok")))
```

The approve POST returns a **302 whose `Location`** already carries `?code=…` — the response
listener catches it even when the route stub doesn't.

## 3. `redirect_uri` validation: test at the real decision point

Testing `/v2/approve_app` while **logged out** returns a redirect to the login page for *every*
candidate URI → looks like "no validation" or produces pure noise. The decision is made on the
**post-login approval page** (tenant subdomain `/app_approvals/new`). Log in first, then loop the
variants and read whether the page offers **Approve** or shows `redirect URI is invalid for this app`:

exact · second-registered · `+ ".evil.example"` · `+ "/../../evil"` · `+ "?next=evil"` ·
`+ "#@evil"` · `localhost:8443.evil.example` · `localhost:8443@evil.example` · evil host ·
`http://` downgrade · port swap · backslash · no `redirect_uri` (defaults to first registered).

Note the login cookie is often **host-only on the login host**, so every app-approval walk
re-triggers a full login + OTP. Budget for that; don't conclude "unauthenticated = vulnerable".

## 4. BOLA/IDOR matrix (API **and** web session)

Create in tenant B, read from tenant A, expect 404 everywhere:

contacts · invoices · credit_notes · estimates · bills · expenses · projects · tasks ·
timeslips · price_list_items · capital_assets · users · attachments

Repeat through the **web session**: open tenant A's UI, learn the real URL pattern from an object
you own (`/contacts/<own_id>` → `/invoices/<own_id>`), then substitute B's id. UI and API are
separate authorization surfaces and both must be checked.

Attachments are worth their own pass: attach a receipt in B, then fetch
`/v2/attachments/<B_id>` with A's token (expect 404) and with no token (expect
`Authorization HTTP header required`). The S3 `content_src` is a **presigned URL** —
anonymous 200 on it is by design, not a finding.

## 5. BFLA / permission levels

Give the low-privilege identity its **own token** and probe collections outside its role
(invoices, bills, expenses, bank, journal, VAT, users) — expect 403, plus a control set it *should*
reach (timeslips/tasks/projects). Also probe `GET/PUT /v2/users/<owner_id>` from the low-priv token.

### ⛔ The false-positive trap (cost this engagement a full re-check)
A low-priv identity getting **HTTP 200** on a collection is *not* automatically broken authz.
Re-run the **same** request with the **owner** token and diff the bodies:

```
owner   -> {"contact":{…,"email":"…","phone_number":"…","address1":"…","account_balance":"…"}}
low-priv-> {"contact":{…}}   # name/org only
```

If the owner sees more fields, the API is **permission-aware and field-filtering** → by design,
NOT a finding. Always compare against the owner's view *before* writing it up, even when the web UI
denies the page the API allows.

## 6. Invitation / activation token binding

`/activate/<token>?user=<id>` (also `/reset_password`, hidden `code=<token>`).

- **Render-only is not proof.** The page shows the "choose a new password" form even for a
  non-existent `user` id — the parameter is validated at submit time, not on GET.
- **Decisive test:** submit with `user=<id of a disposable own account>`, then try logging in as
  *that* account **and** as the token's real owner with the new password. Whichever accepts shows
  the binding. Expect the `user` param to be ignored (token bound to the invited user) → no finding.
- Disposable accounts only; never point this at an account you still need.

## 7. Quick supplementary checks

- **Env isolation:** production token against the sandbox host → expect `401 Access token not recognised`.
- **Subdomain takeover triage:** resolve a random name first. Wildcard DNS means every enumerated
  host is noise; only NXDOMAIN-then-real pairs are evidence.
- **Headers/cookies as one-shot observations:** CSP nonce + `frame-ancestors 'self'`,
  `X-Frame-Options`, HSTS, `nosniff`, `Set-Cookie: …; Secure; HttpOnly; SameSite=Lax`.
  Hardening notes are usually out of scope — record, don't report.

## 8. Pitfalls that wasted time

- **git-bash/MSYS path conversion (Windows):** a CLI argument starting with `/` is rewritten into a
  Windows path before Python sees it — `python fa_api.py GET /v2/company` becomes
  `https://api.freeagent.comC:/v2/company`, so the host parses as `api.freeagent.comc` and the
  request dies with a bogus `socket.gaierror: [Errno 11001] getaddrinfo failed`. Fix:
  `MSYS_NO_PATHCONV=1 <cmd>`, or pass the path inside the script instead of on the command line.
  Do **not** misdiagnose this as a DNS outage or a broken `requests`.
- **Playwright:** `ctx.storage_state(path=…)` called after `b.close()` raises
  `Error: Event loop is closed!` — save state inside the `with sync_playwright()` block.
- **All-NUL (0x00) files** (`PHASE_LOG.md`, a script, a JSON result) are silent write failures.
  Treat as *missing evidence*, never as "empty output" or a clean result.
- **Windows DNS flake:** the first `getaddrinfo` in a fresh process can fail; a warm-up
  `socket.getaddrinfo(host, 443)` with retries before the request makes API helpers reliable.
  (Verify the *host string* is what you think it is before blaming DNS — see MSYS above.)
- **Login field IDs drift from the vendor docs** — always dump
  `[...document.querySelectorAll('input,button')]` and use the real `#id`/`name` rather than
  guessing `#email`/`#password`. On FreeAgent: `#login_email`, `#login_password`, `#login_submit`,
  OTP `#two_factor_code` submitted via `input[name=commit]`.

## 9. Evidence & closing

- One JSON per vector under `evidence/<vector>/`, each storing the **exact request, status and body**
  (plus `findings.json` even when it has zero entries).
- The 0F report carries: scope + assets, method, a **per-vector table with result + evidence path**,
  the disproven candidate **with the reason it was disproven**, an informational-only notes section,
  and the **Residual coverage (honest gaps)** list.
- Zero findings is a valid outcome — say "0 exploitable findings, N verified negatives", never
  "all tools / all vectors tested" unless the artifacts on disk actually show that.
