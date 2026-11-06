# Social Deal — dual-stack auth mechanics and modal state reading

Measured 2026-10-29 against `www.socialdeal.nl`. This file exists because a whole session was lost to
misreading session state; the mechanics below are what actually govern login here.

## 1. Two auth stacks, one host

| | Legacy storefront | Checkout / Nuxt app |
|---|---|---|
| Login | `POST /login/` | `POST /_app/api/account/login` |
| Cookie | `Socialdeal` (PHP session) | `tokens` (RS256 JWT) + `guest_identity` + `__Host-csrf` |
| Body fields | `email,password,remember,redirect` | `email,password,register,remember_me` |
| Header needed | `X-Requested-With: XMLHttpRequest` | `x-product-origin: socialdeal` |
| Turnstile | yes (blocks pure-HTTP login) | **no** |
| 200 shape | `{"redirectUrl":"…","alert":[]}` | `{"token":"<JWT>"}` |

The checkout login **also authenticates the legacy app** — after it, `/account/` (with the XHR header)
contains the member's email and `/my-vouchers/` opens. That is the only reliable way in when the legacy
`/register/` is walled.

`tokens` JWT payload:
```json
{"iss":"api.socialdeal.nl","iat":…,"group":"responsive","aud":"website","sub":"api",
 "exp":…,"shadow":false,"member":{"id":"240sng054q"}}
```

## 2. The session-destroying gotcha

```
api-login  ->  tokens cookie set, session good
legacy POST /login/  ->  200 {"redirectUrl": ...}   <-- looks fine
        ->  `tokens` cookie is DELETED
        ->  every subsequent legacy call answers as anonymous
```

Symptom set (all of it is the wipe, not a bug):
* `/cart/pay/` → `<script>closeCart();</script>`
* `/cart/overview/` (XHR) → `{"success":false,"shouldLogin":true,…}` (151–153 bytes)
* `/gift-card/` → `{"success":false,"shouldLogin":true}`
* `/account/` XHR no longer contains the member email

Rule: **choose one stack per jar.** If the legacy stack is needed, log in legacy once and never run the
API login afterwards in the same session.

## 3. Login is rate-limited and misreports

After ~6 login POSTs inside a few minutes:
```
HTTP 429
{"error":true,"statusCode":429,"statusMessage":"Invalid credentials","message":"Invalid credentials"}
```
No `Retry-After`, no `Ratelimit-*` headers. It persisted past 100 s and 240 s of waiting. The password
is correct — 429 here means "backed off", not "wrong password". Retrying the login to debug is what
extends the outage; if you see 429, stop touching the endpoint for the rest of the session.

## 4. Modal state reading — `X-Requested-With` is mandatory

Without the header, these routes render the whole storefront (~5 MB) instead of the fragment:

```
XHR /my-vouchers/  -> ~150-3000 B modal   (real state)
GET /my-vouchers/  -> 5,133,652 B homepage (useless, and greps clean for "Activeer eerst")
```

That size inversion produced a false "the activation gate is gone" conclusion. Always:
1. send `X-Requested-With: XMLHttpRequest`;
2. assert the body length is fragment-sized before deriving state;
3. cross-check with `/account/` (XHR) containing the member email.

Account activation: the code in the mail
(`/account/activeren/?code=<digits>&ref=<token>`) is **single-use-ish and stale-safe** — re-running it
prints "Je account is al geactiveerd" in a JS block, and an old code silently does nothing. If the
activation is needed, fetch the newest mail and use that link, then re-check the modals.

`/modal/account/resend-activationmail/` needs `email` in the body; without it → `{"success":false}`
("Geef een geldig e-mailadres op").

## 5. Browser-side capture pattern (what worked)

Driver: Camoufox (`headless=False, humanize=True, locale="nl-NL"`), page kept alive across steps.

```python
def on_resp(r):
    if "/_app/api/" in r.url or "/cart/" in r.url:
        print(r.request.method, r.status, r.url[-60:], r.text()[:120])
page.on("response", on_resp)
```

In-page login + action, to keep cookies consistent with the browser:
```python
page.evaluate("""async (cred) => {
  const r = await fetch('/_app/api/account/login', {method:'POST', credentials:'include',
    headers:{'Content-Type':'application/json','x-product-origin':'socialdeal'},
    body: JSON.stringify({email:cred.email, password:cred.password,
                          register:false, remember_me:false})});
  return JSON.stringify({s:r.status, t:(await r.text()).slice(0,160)});
}""", {"email": addr, "password": pwd})
```

**Pitfall that cost a cycle:** never build that JS by string substitution
(`script.replace("P", json.dumps(pwd))`) — `"P"` also matches the `P` in `POST`, producing
`Invalid request method "Passw0rd!2026xOST"`. Pass a dict as `evaluate`'s second argument instead.

Also: the page-level `showLogin()` helper is not defined on `/login/` (it is a storefront-page global),
and clicking the modal's "Registreren"/"Inloggen" anchors can hang on `waiting for scheduled
navigations`. Driving the form via `document.getElementById(...).click()` / `requestSubmit()` inside
`evaluate` is more reliable than `locator.click()`.

## 6. Cart / checkout separation

* Legacy cart: `/cart/add/{deal_unique}/{n}/` → `19cpn767fv6`-style item unique → `/cart/overview/`,
  `/cart/method/?forceFlow=required`, `/cart/save/`, `/cart/pay/`.
* Checkout store: `/_app/api/platform/cart` — GET `204` when empty; PATCH body is
  `{"deal_groups":[{"items":[{"unique":…,"amount":…}]}]}` but returns `404 MultiCart.NotFound` without
  a UI-minted cart. POST/PUT/DELETE on the collection → `404 Page not found`.
* They are not the same cart. A legacy add never shows up at `/checkout` ("Je winkelmandje is
  momenteel leeg" is correct behaviour, and `/checkout` is the travel product anyway).
