# Public config-file key triage + reCAPTCHA-Enterprise signup order mapping

Worked from the PubNub engagement (2026-10-31), where the authenticated area was unreachable
because signup validated a reCAPTCHA Enterprise token server-side. Both techniques below came out
of that blocked session — the second one is what turned the blocker into a High finding.

---

## Part 1 — `/config.json` key triage

### Probe the config-file names on every host

```
/config.json   /app-config.json   /env.json   /settings.json   /assets/config.json
/runtime-config.json   /appsettings.json   /configuration.json
```

One GET each, no auth. PubNub's `admin.pubnub.com/config.json` returned HTTP 200 with:

```json
{
  "sentryEnvironment": "prd",
  "demo": {
    "627651": {"demoUrl": "https://www.pubnub.com/demos/transport-logistics/?show=demo",
               "githubUrl": "https://github.com/PubNubDevelopers/transport-logistics-javascript-demo",
               "label": "Transport & Logistics"},
    "632313": {"demoUrl": "https://www.pubnub.com/demos/live-streaming-showcase",
               "githubUrl": "https://github.com/PubNubDevelopers/pn-solution-live-events",
               "label": "Sports Media Entertainment"}
  },
  "inkeep": {
    "integrationId": "cm2lp5c3l00kvrt8yaczi5m3z",
    "organizationId": "org_AoQMtSJNmMqt8U4m",
    "apiKey": "9d228670aadc10e93eb3f88314a894952a70fc26bec34f49"
  },
  "segment": {"writeKey": "RSzooYXYta360AkLvST610aA6zlGPwER"}
}
```

### The triage table — this is what decides reportability

| credential class | ships in client bundle by design? | verdict |
|---|---|---|
| Segment / Amplitude / GA **write** key | **Yes** — documented public | weak alone; reportable when a server-side key sits beside it |
| Sentry DSN | Yes | informational |
| reCAPTCHA **site** key | Yes | informational |
| Stripe/Paddle **publishable** id | Yes | informational |
| **Any API key without a `publishable`/`site`/`write` prefix** (Inkeep, OpenAI, SendGrid, Twilio, internal service tokens) | **No** | **reportable — this is the finding** |
| Secret key (`sk_…`, `secret_key`, `seckey`) | No | critical if present |

The rule: **score the finding on the server-side credential, not the client-side one.** Leading
with a Segment write key invites a by-design close, because Segment documents those as public.

### Verify liveness — with a mandatory negative control

```python
import base64
AUTH = "Basic " + base64.b64encode((SEG_WRITE_KEY + ":").encode()).decode()

# NEGATIVE CONTROL FIRST — no auth must fail
st, b = req("https://api.segment.io/v1/track", {"userId": "x", "event": "y"})
# -> 400 {"success": false, "message": "An invalid write key was provided",
#         "code": "invalid_request"}

# THEN the real key
st, b = req("https://api.segment.io/v1/track",
            {"userId": "probe", "event": "probe_event"}, hdr={"Authorization": AUTH})
# -> 200 {"success": true}
```

Without the negative control you cannot distinguish "this key works" from "this endpoint accepts
anything". Run it in the same session and quote both in the report.

### Blast radius — sweep all seven Segment ingest endpoints

All seven accepted the key on PubNub:

```
/v1/track    -> 200      /v1/identify -> 200      /v1/page    -> 200
/v1/screen   -> 200      /v1/group    -> 200      /v1/alias   -> 200
/v1/batch    -> 200
```

That list is the blast-radius sentence: an anonymous caller can fabricate arbitrary events under
arbitrary `userId` values.

### Liveness proof for a non-Segment key

One authenticated request that fails *past* the auth layer is sufficient:

```
POST https://api.inkeep.com/v1/chat/completions
Authorization: Bearer <key>     X-Integration-Id: <id>
-> 400 {"error":{"message":"Invalid model"}}
```

An invalid key returns 401/403 before the model layer is reached, so reaching "Invalid model"
proves the key authenticated. Do not go further — you would burn the vendor's quota.

### Three free extras the file handed over

1. **Environment name** — `sentryEnvironment: "prd"` confirms production.
2. **A demo-account map** — `627651` and `632313` labelled "Transport & Logistics" and
   "Sports Media Entertainment". This is the provenance evidence the demo-keyset rule (§1n)
   demands, delivered for free: any account ID in that map is a demo account and its data is not
   a finding.
3. **Third-party integration IDs** — scopes what else the vendor's stack touches.

### Report framing that got it paid

- **Lead with the Inkeep key** (server-side credential, must never reach a browser).
- **Cite the Segment key as demonstrated impact** of the same exposure, with the negative control.
- **Add one sentence inviting reassessment** on the Segment portion if the triager considers
  client-side write keys by-design. That pre-empts the obvious close without conceding the
  server-side half.
- CVSS 3.1 `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:H/A:N` = **8.2 High**. Not Critical, because a Segment
  write key is write-only by design — integrity, not confidentiality, and no customer data access.

---

## Part 2 — reCAPTCHA-Enterprise signup validation order

### Find the endpoint from the bundle's request helper, not by guessing paths

The base URL is usually a variable. On PubNub:

```js
fm = "";  QP = {baseUrl: `${fm}/api`, credentials: "same-origin"};
aa = (e, n) => fetch(`${QP.baseUrl}${e}`, {...n, credentials: QP.credentials});
```

So the signup endpoint is **`POST /api/users`**, not `/users` — and `POST /users` returns
`405 Not Allowed` from nginx, which reads as "endpoint does not exist" if you guess paths.

### Read the exact body shape from the submit handler

```json
{
  "email": "...", "first": "...", "last": "...", "password": "...",
  "contextData": {
    "pageTitle": "...", "pagePath": "/register", "pageUrl": "...",
    "pageReferrer": "", "pageSearch": "", "userAgent": "...",
    "signupSource": "register"
  },
  "g-recaptcha-response": "<token>",
  "enterprise": true
}
```

Plus a **honeypot field** `contact-email` that the client strips before sending
(`const {"contact-email": f, ...x} = p`). Sending it filled is harmless — the server ignores it.

Signup routes in the bundle: `/register`, `/register-starter`, `/register-illuminate`.
Site keys: production `6LdxhW8pAAAAAArRGDvcAZBXwP5rJfx0zwRGzbCi`, non-production
`6Lcdrm4pAAAAAPRGVkU3FHWvVgQ3h-Q2ul_HN3S9` (selected by hostname check in the bundle).

### The validation order — map it by removing one field at a time

| request | response | captcha checked? |
|---|---|---|
| bad email + bad pw | `400 {"error":"Email is not valid."}` | no |
| good email + bad pw | `400 {"error":"Your password must be between 8 and 72 characters…"}` | **no** |
| good email + no pw | `400 {"error":"Please fill out your password."}` | **no** |
| good email + good pw | `400 {"error":"Invalid response from Google reCAPTCHA","error_code":"BAD_CAPTCHA_RESPONSE"}` | **yes — here** |
| captcha field absent | `400 {"error":"Please retry your registration and provide a captcha response.","error_code":"BAD_CAPTCHA"}` | n/a |
| junk captcha string | `400 {"error":"MALFORMED","error_code":"BAD_CAPTCHA_RESPONSE"}` | yes |

**Order is email → password → captcha.**

### What the weak-password skip is, and is not

A weak password makes the server answer with the password policy *without* checking the captcha.
That is an **error-message oracle**, not an account-creation bypass — no account is created, and
with a valid password the captcha holds. Report it as such or not at all. Do not dress it up.

### Confirm the block is real before spending the session

Mint a genuine token in a real browser (the app passes **no action string**, so
`executeRecaptcha(undefined)`):

```js
await new Promise(r => window.grecaptcha.enterprise.ready(r));
const t = await window.grecaptcha.enterprise.execute('6LdxhW8pAAAAAArRGDvcAZBXwP5rJfx0zwRGzbCi',
                                                     {action: undefined});
// -> 2425-char token
```

Submitting that token from a **headed** Chrome with a warmed-up profile still returned:

```json
{"code":400,"error":"Score too low","error_code":"BAD_CAPTCHA_RESPONSE"}
```

reCAPTCHA Enterprise v3 is score-based and invisible — there is no puzzle, only a reputation
score, and a datacenter/low-reputation IP scores low. **Once you have confirmed this, stop.** Record
the blocker with the specific gate named, and do not write the attempts up as a workflow.

### The pivot that paid

While mapping signup I swept the bundle for never-tested routes and found `/config.json` (Part 1)
plus three routes the session-token bypass newly opened. **A blocked signup is a reason to widen the
unauth sweep, not to grind the captcha.** The blocker session produced a High finding on a
different surface.

### Also checked and closed (record as negatives)

- `/api/services/google/auth` → 200 but serves a proxied Google **sign-in** page
  (`accounts.google.com/v3/signin/`), no `client_id`/`redirect_uri` — not an account-creation path.
- All other provider paths (`github`, `microsoft`, `azure`, `okta`, `saml`, `apple`, `linkedin`,
  `sso`, `oidc`) → 404.
- Webhook signature verification on `/api/subscription/payment/webhook/invoice-payment` and
  `/api/subscription/payment-method/webhook/set-default` held against 18 bypass shapes (see §1q).
