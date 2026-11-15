# reCAPTCHA v3 score threshold + minified-SPA API reconstruction (CEX)

Two techniques from a crypto-exchange bug bounty (Citronus, 2026-11) that generalise to any
hardened SPA with server-side bot scoring.

## 1. reCAPTCHA v3 is score-based, and the error leaks the threshold

reCAPTCHA v3 is NOT the v2 checkbox. It runs invisible and returns a `token` + a `score`
(0.0–1.0). The server rejects low-scoring tokens and — on many targets — **tells you the exact
threshold and your current score**:

```
POST /sso/registration/email/  {email,password,token:""}
   -> 422 {"code":"blank","detail":{"token":["This field cannot be empty."]}}
POST ...  {token:"fake"}
   -> 400 {"detail":"Invalid reCaptcha token","code":"recaptcha_invalid_token"}
POST ...  {token:<real v3 token from an automated browser>}
   -> 400 {"detail":"Invalid token score. 0.1 < 0.5","code":"recaptcha_invalid_token_score"}
```

That last response is the whole tell: score threshold = **0.5**, and your automated browser got
**0.1**. So the field is present and server-enforced (not client-trusted), and the score decays
below threshold once your IP/session is flagged as bot-like.

Practical consequences for account minting:
- The score **drops after repeated automated logins** from the same profile/IP. Fresh automation
  gets a passing score; the 3rd–4th login attempt starts failing `score … < 0.5` even though the
  token flow is identical. That is IP/device reputation, not a target property, and it recovers
  with a fresh profile dir / a cool-down — treat it as REWORK, never as "signup blocked".
- **Blank vs fake vs low-score** errors are three different gates (presence → validity → score).
  Log all three; they map exactly where the bot check sits.
- Password-reset is often the side-channel: here `POST /sso/reset/password/email/` returned 204
  with an empty/fake/absent token (no reCAPTCHA at all), while register + login enforce score
  >= 0.5. That asymmetry is itself a (Low) finding, and it is also the only un-throttled auth
  surface when the score has decayed.
- Drive the real form in headed Chrome; `grecaptcha.execute(sitekey, {action})` returns a token
  without any challenge, but its *score* still belongs to the browser/IP.

## 2. Reconstruct a minified SPA's whole API surface before probing

No OpenAPI on a minified React/Vite bundle — these five greps rebuild the endpoint map in minutes
(axios-class pattern):

```
# all API base URLs (axios instance constructors)
grep -oE 'super\("https://[^"]+"\)' bundle.js | sort -u
#  -> https://api.citronus.com/sso/  /wallets/ /crypto/ /futures/ /spot/api/ /referrals/ /admin/api/ ...

# every literal method call (endpoint paths)
grep -oE '\.(get|post|put|delete|patch)\("([^"]{1,120})"' bundle.js | sort -u

# map class -> base -> FIRST method to see which base each class owns
grep -oE 'class [A-Za-z$_]+ extends or\{constructor\(\)\{super\("[^"]+"\)\}[a-zA-Z$_=]{0,60}' bundle.js
```

Then resolve **inherited bases** — the trap that silently sends you to the wrong host:

```
class Wd extends or{constructor(){super("https://api.citronus.com/sso/")}}   # base = /sso/
class SJ extends Wd{getUser=()=>this.get("user/info/"); ...}                  # inherits /sso/
```

`SJ` extends `Wd`, so `user/info/` lives at `/sso/user/info/`, NOT `/wallets/user/info/` — even
though a sibling `class xJ … super("…/wallets/")` suggests otherwise. When an endpoint 404s, walk
the `extends` chain to find its real base. The auth*namespace in particular is frequently a
different prefix than the wallet/trading namespaces.

Reading the bundle: it is a single multi-MB minified line — use windowed Python, never `grep`
with a heavy regex (see the Pitfalls note):
```python
i = data.find("validateWalletAddress"); print(data[max(0,i-400):i+300])
```

## 3. OAuth-PKCE CEX auth flow (register → 2FA → code → callback)

The full money-account chain on this target, so the next CEX audit starts already oriented:

1. register `POST /sso/registration/email/` {email,password,marketing_consent,token,referrer_code,language_code} → `{code_uid, expire_after}`
2. confirm `POST /sso/registration/email/confirm/` {code_uid, code} → `{token}` (40-hex SSO token)
3. login `POST /sso/authentication/login/email/` {email,password,token} → `{code_uid, resend_after:60}`
4. login-code `POST /sso/authentication/login/code/` {code_uid, code} → `{token}`
5. authorize `GET /sso/oauth/authorize/?response_type=code&code_challenge=<PKCE>&client_id=…&redirect_uri=…` with `Authorization: Bearer *** token>` → `{redirect_uri?code=<code>}`
6. callback `…/web/sso/login/callback/?code=<code>` → `{access_token, refresh_token}`

Notes:
- `redirect_uri` is whitelisted (arbitrary `evil.com` is rewritten to the app + a fresh PKCE
  challenge) — so no open-redirect/token-theft there.
- Access token is a **RS256 JWT with `kid`**; payload carries `uid` (UUID), `sub` (numeric id),
  `roles`, `permissions`. Decode it first — it tells you the IDOR target (numeric id) and the
  role model to test for mass-assignment.
- OTP codes are **6 digits, single-use, 10 min valid** for login (registration confirm says
  "1 hour"); password-reset uses a **link token** (~43 base64url chars, 1 hour), not a code.
- The codes are also **stored in the notifications table** and visible through
  `GET /notifications/v1/` in your own account — a reminder that "your own OTP" is self-scoped,
  not an IDOR, unless you can cross the user boundary.

## 4. The split 6-box OTP input (Playwright)

The email OTP field is NOT one `<input>` — it is six `<input maxlength=1 inputmode=numeric>` with
no testid, and the Verify button (`[data-testid=otpFormVerifyButton]`) stays `disabled` until all
six are filled. `page.fill()` on a `code`-named selector silently matches the *button*, not the
input, and `fill()` on a disabled button times out. Fill each box per digit:

```python
boxes = page.locator("input[inputmode='numeric'][maxlength='1']")
for i, ch in enumerate(code):
    await boxes.nth(i).fill(ch)
```