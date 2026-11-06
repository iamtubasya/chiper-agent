# Deal / voucher / daily-deal marketplace — measured logic matrix

Source: Social Deal (Intigriti, NL/BE/DE daily-deal platform), 2026-10-29. Every row below was
EXECUTED against production with an authenticated account; none was inferred from the bundle.
Use this as the probe order for any "buy a deal → get a voucher → redeem at partner" product
(Groupon-shaped: daily deal, gift card, loyalty stamps, lottery promotions).

The product model that drives the test list:

```
deal page → /cart/add/<unique>/<amount>/ → cart (items[][unique], items[][amount])
         → /cart/method/ (payment method select) → /cart/save/ → /cart/pay/
         → PSP redirect → /cart/complete/ → voucher issued → /my-vouchers/
side rails: gift-box (PDF), gift-card redeem (code+PIN), spaarkaart (stamps), /loyalty/ (lottery)
```

## Results matrix

| Probe | Request | Observed | Verdict |
|---|---|---|---|
| amount 0 | `items[][amount]=0` on cart/save | total unchanged 34,95 | clamped |
| amount −1 | `items[][amount]=-1` | total unchanged | clamped |
| amount 0.5 / 1.5 | fractional | `1.5` accepted but total unchanged; `0.5` reset the cart | clamped (no half-voucher) |
| amount 10000 | huge | total unchanged | cap server-side |
| param shape | `items[0][amount]` vs `items[][amount]` | **both accepted**, recomputed | no shape confusion |
| item substitution | add cheap item, then `cart/save items[][unique]=<expensive>` | cart keeps its OWN internal unique; server ignores supplied unique | **no price confusion** |
| reverse substitution | add expensive, save cheap unique | unchanged 34,95 | control holds |
| payment method outside allowlist | `method[type]=tegoed` | pay → `closeCart()` (silent reject) | validated |
| payment method legit | `method[type]=ideal` | pay returns div with `data-payment-url=https://pay.ideal.nl/transactions/...` | live PSP mint |
| skip payment | `GET/POST /cart/complete/` with cart+method set | **307 → /** | needs a real PSP session |
| stamp minting | `POST /spaarkaart/add-stamp/ {index:1..5, unique:<card>}` | `{"success":false}` ×5 | server checks earned allowance |
| lottery tickets | `POST /loyalty/tickets/ {promotion:66}` | `{"success":false,"shouldLogin":true}` (see auth note) | member-scoped |
| promo code | `GET /deal-details/promo-code/?deal_unique=X&quantity=1` | `{"promoCode":null}` | read-only quote |
| gift-card claim | `POST /gift-card/ code=<code>` | renders `Mijn vouchers` modal, NOT a claim result | wrong route — see below |

### The one that matters for the report

`items[][unique]` is a **decoy**. The cart stores its own server-issued item unique
(e.g. `19cpn767fv6`) that is unrelated to the deal unique you passed to `/cart/add/`.
Any amount or unique you send to `/cart/save/` is re-resolved from that server-side row.
So the classic "swap the unique after add" test is a guaranteed negative here — do not spend
a second pass on it. The real lever would be the row the server issued, which you cannot forge.

## Payment-method allowlist is the actual gate

`/cart/method/?forceFlow=required` returns the full list inline in `setCartValue(...)` calls:

```
setCartValue( event, ['paymentMethodType','paymentMethodReference'], ['ideal',''],       '/cart/save/?forceFlow=payment' )
... google_pay, apple_pay, klarna, creditcard, paypal, mrcash, cartebancaire
```

- Every option has an **empty reference** — no stored-mandate injection surface.
- A value outside the list does not 400; it makes `/cart/pay/` return `closeCart()` (99 bytes).
  **Distinguish by body length**: real PSP mint = ~485 bytes with `data-payment-url`;
  reject = 99 bytes `closeCart()`. That length diff is the fastest oracle on this flow.
- There is no `tegoed`/credit/gift-balance method here, so "pay with own credit" is not a route
  to a free order. Tested, not assumed.

## Gift card: the code is a claim, not a render

`POST /gift-card/ code=...` on a session that is not fully activated just re-renders the
vouchers modal — that is **not** an oracle. The real claim path lives in the vouchers modal form
(`#giftCardModalForm`, `input[name=code]`) and answers with a structured object the JS then
branches on:

```js
data.success === false
  data.link === 'transfer'      -> voucher already owned by someone else, transfer prompt
  data.link === 'requires_pin'  -> open the PIN drawer  (#pin_code / #pin)
  data.errors[0] === 'pin'      -> PIN wrong, refocus pin
  data.alert                    -> generic alert array
data.success === true           -> creditsText + expireText shown, credits landed
```

`requires_pin` is the interesting state: a gift-card code is protected by a **second short
factor**. On a numeric short PIN with no lockout that is a monetary-impact bug — but proving it
by spraying PINs is brute force, which the usual policy excludes. The defensible test is
structural: does the PIN have a server-side attempt counter? Send 2–3 wrong PINs on one code and
watch whether the response changes (lockout text / different error) — that is 3 requests, not
brute force. If there is no counter, report the DESIGN (unlimited PIN attempts on a bearer-value
code) with the 3-request evidence and let triage set severity.

## Loyalty stamps: `index` is client-supplied and properly ignored

The stamp card renders `data-index="1..20"`, `data-stamps-needed="20"`,
`data-add-stamp="/spaarkaart/add-stamp/"`, `data-unique="<card>"`. The client sends
`{index, unique}`. Posting index 1..5 with zero earned stamps returns `{"success":false}`
every time — the server checks the earned-stamp allowance, so `index` only chooses WHICH slot
to fill, not HOW MANY you get. Same for the lottery: `/loyalty/tickets/` refuses when the member
has no spend-derived tickets.

## Session architecture pitfall that will waste your whole session

The estate ran **two independent auth stacks on the same host** and they interfere:

| stack | cookie | minted by |
|---|---|---|
| legacy PHP storefront (`/cart/*`, `/my-vouchers/`, `/loyalty/`, `/spaarkaart/`) | `Socialdeal` | legacy login, or the activation link |
| Next.js `/checkout` app (`/_app/api/platform/*`) | `tokens` (RS256 JWT, `member.id` in payload) | `POST /_app/api/account/login` |
| whitelabel Nuxt (`spontaan.nl`, `whynot.com`) | `wl_tokens` (RS256 JWT, `data.identifier`) | their own login |

**Calling the legacy `POST /login/` after the modern login WIPES the `tokens` cookie and does not
authenticate the legacy app.** Symptom: `/cart/*`, `/gift-card/`, `/loyalty/*` all answer
`{"success":false,"shouldLogin":true,"message":"Je bent niet bevoegd..."}` (the "not authorised"
JSON) even though `/account/` looks logged in.

Rules:
1. Log in **once** per stack and record which cookie you got.
2. Never call the other stack's login "to be safe" — it destroys the first.
3. When every member endpoint returns the not-authorised JSON, suspect a wiped cookie, not a missing route.
4. The modern login returns the JWT in the **response body** (`{"token": "..."}`), and the client
   must store it as the `tokens` cookie itself — a bare `requests.Session` will not persist it.
   Set it explicitly: `S.cookies.set("tokens", tok, domain="www.socialdeal.nl", path="/")`.
5. Repeated login attempts trip `429` whose `statusMessage` literally reads **"Invalid credentials"**
   — that is a rate limiter wearing a credential error's clothes. Do not conclude the password is
   wrong; back off. Test accounts supplied by the program can be locked this way.

## Registration wall vs. the newer app

Legacy `/register/` rejected **every** email domain (gmail, outlook, mailinator, the program's own
`@intigriti.me`, the vendor's `@socialdeal.nl`) from both headless and a real stealth browser, with
Cloudflare Turnstile on the form. The Next `/checkout` app accepted a one-request registration with
no Turnstile:

```
POST /_app/api/account/login {"email":..., "password":..., "register":true, "remember_me":false}
-> 200 {"token": "..."} + Set-Cookie guest_identity, tokens, __Host-csrf
```

Lesson: when a policy says "self-register", a wall on the old signup form does not mean the target
is untestable — enumerate the estate for a **second, newer auth entry point** before declaring a
blocker. Also: activation from the checkout-registered account did not clear the legacy
`/my-vouchers/` gate ("Activeer eerst"), so per-stack activation state is separate too.

## Where the money actually was, in the end

Not in the cart. The payable finding came from the **routing layer** — a 301 whose `Location` was
`http://<service>.socialdeal.internal/...` (see
`security-recon/references/app-link-association-and-internal-host-disclosure.md`).
On a hardened daily-deal target, the commerce logic was well built (every one of the 5 mandatory
probes came back a clean, defensible negative) and the edge config was not.
