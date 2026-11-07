# Second identity: harvest, harness, and the cross-tenant BOLA matrix

Measured 2026-10-25 (Proton, multi-app E2E suite). Covers what happens **after** you finally have a
second account, which is where the real BOLA work starts — and where two rounds were lost.

## 1. Getting the second identity (operator-assisted, then harvest)

Automation was genuinely impossible on Proton signup (off-screen decoy + cross-origin HV challenge
iframe; full diagnostic in skill `signup-block-ops` §8/§9). The operator created it manually in a
headed browser we opened. The handoff and the harvest are separate steps:

```python
# open for the human — background=true + notify_on_complete=true, NEVER foreground
ctx = pw.chromium.launch_persistent_context(
    r"/home/agentuser/<target>-manual-profile", headless=False,
    args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
    no_viewport=True, locale="en-US")
```

Harvest after they say it's done:
```python
ctx = pw.chromium.launch_persistent_context(PROFILE, headless=False, no_viewport=True)
pg  = ctx.pages[0]; pg.goto("https://account.proton.me/apps", wait_until="domcontentloaded")
# identity proof FIRST — do not trust that a cookie exists
print(pg.evaluate("()=>document.body.innerText")[:300])   # "RESEARCHER_USERNAME | RESEARCHER_EMAIL | ..."
ctx.storage_state(path=".../manual-state.json")
```

**One profile = one process.** A profile held by the still-open handout browser refuses a second
launch: `Opening in existing browser session. This usually means that the profile is already in use`.
Either kill only the PIDs whose command line contains that profile
(`wmic process where "name='chrome.exe'" get ProcessId,CommandLine` → filter → `taskkill /F /PID`),
or read cookies from the process that is already running. Do **not** open a second instance.

Record in the ledger: "account B created manually by operator, <date>" — a report must never imply
self-provisioning that did not happen.

## 2. You cannot replay these cookies with `requests` — and the failure looks like authz

Two different auth shapes existed side by side on the same target:

| account | shape | how to call it |
|---|---|---|
| A (Proton address, SRP login) | real bearer token from `POST /api/auth/v4/sessions` | plain `requests` with `Authorization: Bearer <token>` |
| B (external-address, browser session) | `AUTH-<uid>` cookie whose value is an **encrypted envelope** (`eyJpdiI6…`, sometimes URL-encoded JSON `%7B%22Resp…`) | **in-page `fetch()` only** |

Sending an encrypted-envelope cookie as a bearer token yields `401 Invalid access token` (or
`403 9106 MissingScopes`). Both read exactly like an authorization failure and will make you write
"account B cannot access its own data" — a phantom finding. Check the cookie's *shape* before
concluding anything: ciphertext (`eyJpdiI`, `%7B%22`) ⇒ it is not a token.

## 3. In-page fetch harness (the reusable part)

`api2.py` pattern: navigate to the target origin, then `evaluate` a fetch shim. Both details are
mandatory, each one alone still 401s.

```python
JS = """async ({method, path, uid, apv, body, base}) => {
  const h = {'Accept':'application/vnd.protonmail.v1+json','x-pm-uid':uid,'x-pm-appversion':apv};
  const opt = {method, credentials:'include', headers:h};
  if (body != null) { h['Content-Type']='application/json'; opt.body = JSON.stringify(body); }
  const r = await fetch(base + path, opt);
  return {status:r.status, body:(await r.text()).slice(0,4000)};
}"""

def req(self, method, path, body=None, base=None):
    target = base or self.base
    if not self.pg.url.startswith(target):          # (a) CORS: hop to the target ORIGIN first
        for cand in (target + "/u/0/", target):     #     per-app landing creates that app's session
            try:
                self.pg.goto(cand, wait_until="domcontentloaded", timeout=45000)
                self.pg.wait_for_timeout(6000)
                if self.pg.url.startswith(target): break
            except Exception: continue
    return self.pg.evaluate(JS, {"method":method,"path":path,"uid":UID,
                                 "apv":APV,"body":body,"base":target})
```

- **(a) origin hop** — a cross-subdomain `fetch()` dies as `TypeError: Failed to fetch`, which reads
  like a network outage. Navigating to the app first is what makes the call legal.
- **(b) per-host UID** — the `x-pm-uid` is **per subdomain**, not one global value. Read the live
  `AUTH-<uid>` cookie names from `ctx.cookies()` per host; five UIDs existed at once on one account
  and only one had the scopes `/users` needs. Wrong UID ⇒ `403 9106 MissingScopes:["user","settings"]`.
- Landing on `/u/0/` (the app), not just the bare host, is what mints that product's fork session.
  A bare-host visit leaves you 401 on `/api/`.

## 4. External-address accounts have a smaller product footprint

Account B was created with a gmail address (Proton `Type: 3`, address `Type: 5`). Consequences worth
knowing **before** planning the matrix:

- **Drive, Docs**: fully usable.
- **Calendar**: refused — `/u/1/setup-address?to=proton-calendar`. An external-address account has no
  `@proton.me` address, so Calendar cannot be provisioned. Calendar BOLA is *untestable* with this
  identity, not "negative".
- **Pass**: forced `/reauth` (extra password step) before the vault unlocks.

Plan the matrix around what each identity can actually open, and write the untestable rows down as
untestable with the reason.

## 5. Cross-tenant BOLA matrix — Drive (verified negative, worth recording)

Account B's own session probing Account A's objects:

| request | result | reading |
|---|---|---|
| `GET /drive/volumes/{A_vol}` | `422 Code 2011 "Insufficient permissions"` | denied |
| `GET /drive/shares/{A_share}` | `422 "You don't have permission to perform this action"` | denied |
| `GET /drive/v2/volumes/{A_vol}/links/{A_link}` ×3 | `404 Path not found` | denied |
| `GET /drive/v2/volumes/{A_vol}/folders/{A_link}` | `404 Path not found` | denied |
| `GET /drive/v2/shares/my-files` (control) | `200` → B's own volume | control OK |

The **422 vs 404 split is the design being correct**: known-but-unauthorised ⇒ 422, unknown path ⇒
404. It also means a foreign user learns nothing about object existence at the routing layer. Record
this as a negative with the exact codes — it is what makes the eventual positive credible.

## 6. Dead ends to recognise fast (so you don't burn a round)

- **The root my-files share cannot take invitations.** `POST /drive/v2/shares/{rootShareID}/invitations`
  answers `422 Share not found`. A shareable unit must first be created from a link:
  `POST /drive/v2/volumes/{vol}/shares` with `{AddressID, ShareKey, SharePassphrase,
  SharePassphraseSignature, RootLinkID, Name}` — server-computable parts are the blocker, not the route.
- **UI-first Drive sharing is hostile to automation.** A persistent upsell modal intercepts pointer
  events (`... intercepts pointer events`), `Escape` does not dismiss it, and the row's "More options"
  button has no stable `aria-label` after dismissal. Prefer the API path or accept "UNTESTED".
- **Permission-escalation route, for when you do get a share:**
  `PUT /drive/shares/{shareId}/members/{memberId} {Permissions}` — that is the endpoint to point at a
  viewer→editor attempt. Do not report anything from it until a real A→B share exists.

## 7. Reporting discipline that came out of this round

- An anti-automation gate that holds is a **working control** ⇒ coverage limit with a named unlock,
  never "target is clean" and never a bug.
- Anything you could not reach because the identity lacks the product is **UNTESTED**, not negative.
  The two words are not interchangeable and a reviewer will check.
