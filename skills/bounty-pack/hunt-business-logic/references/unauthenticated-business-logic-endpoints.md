# Unauthenticated Business Logic Endpoints — Hunting Pattern

> Session: DuoCircle bug bounty (2026-10-26). Found user enumeration + no rate limiting on
> `POST /appsumo_tokens` at app.dmarcreport.com. This reference captures the reusable pattern.

## The Pattern

SaaS products often expose business-logic endpoints WITHOUT authentication because they sit
outside the main app's auth guard. Common candidates:

| Endpoint pattern | What it does | Risk |
|---|---|---|
| `/appsumo_tokens`, `/promo_codes`, `/vouchers` | License/promo redemption | User enum, code brute force, arbitrary email association |
| `/redeem`, `/claim`, `/gift` | Reward claiming | Same as above |
| `/invitations/accept?token=` | Invite acceptance | Token brute force, email enum |
| `/unsubscribe?token=` | Email unsubscribe | Token enum, email enum |
| `/verify-email?token=` | Email verification | Token brute force |
| `/webhooks/stripe`, `/webhooks/*` | Payment webhooks | Forgery if no signature check |
| `/password/reset` (no rate limit) | Password reset | Email enum, reset flood |
| `/newsletter/subscribe` | Newsletter signup | Email enum |

## How to Find Them

1. **gau / Wayback Machine** — historical URLs reveal endpoints that were once public.
   `echo "target.com" | gau --subs | grep -iE '(appsumo|promo|redeem|claim|voucher|invite|unsubscribe)'`
2. **Crawl with katana** — `-jc` (JS crawl) + `-kf all` catches form actions in JS bundles.
3. **Check sitemap.xml and robots.txt** — sometimes list non-app routes.
4. **Look at the CSP `form-action` directive** — reveals allowed form submission targets
   that may include unauthenticated endpoints.

## Testing Methodology

### 1. Confirm no auth required

```bash
curl -s -o /dev/null -w "%{http_code}\n" "https://target.com/appsumo_tokens/new"
# 200 = accessible without auth (finding candidate)
# 302 to /login = auth-gated (skip)
```

### 2. Test for user enumeration oracle

Submit with a KNOWN-existing email vs a RANDOM non-existing email. Compare responses:

```bash
# Get CSRF (Rails)
CSRF=$(curl -s -c cookies.txt "https://target.com/endpoint/new" | grep -oP 'name="authenticity_token" value="\K[^"]+')

# Submit with existing email
curl -s -b cookies.txt -c cookies.txt -X POST "https://target.com/endpoint" \
  -d "authenticity_token=$CSRF&endpoint[email]=admin@target.com&endpoint[token]=TEST"

# Read flash message (Rails pattern: POST → 302 → GET → flash in session)
curl -s -b cookies.txt "https://target.com/endpoint/new" | grep -oP '<p class="mb-0">\s*\K[^<]+'
```

**Rails flash message extraction:** After a POST that returns 302, the flash is stored in
the session cookie. Do a GET on the same page WITH the cookie jar to render it. The message
is inside `<div class="alert alert-danger">` → `<p class="mb-0">`. The flash is consumed
after one view, so capture it on the first GET after the POST.

### 3. Test for rate limiting absence

```bash
for i in $(seq 1 10); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -b cookies.txt -X POST \
    "https://target.com/endpoint" \
    -d "authenticity_token=$CSRF&endpoint[email]=test$i@x.com&endpoint[token]=RL$i")
  echo "Request $i -> $code"
done
# All 302/200 = no rate limiting (finding)
# Any 429 = rate limited (note it)
```

### 4. Test claim_field / hidden field manipulation

Rails forms often have hidden fields like `claim_field=true`. Try:
- Setting to `false` — may skip validation
- Omitting entirely — may bypass required-field checks
- Setting to array/object — may cause type confusion

## Impact Framing for Reports

When writing up the finding, frame impact as:

1. **Enumeration**: "An attacker can determine which email addresses are registered on
   the platform without authentication."
2. **Scale**: "The absence of rate limiting enables mass harvesting at thousands of
   requests per minute."
3. **Downstream**: "The harvested list enables targeted phishing campaigns against
   [product-type] customers who are likely security-conscious."
4. **Business logic**: "Without rate limiting, an attacker could brute force valid
   [license/promo/invite] codes."

## CVSS Guidance

User enumeration + no rate limiting on an unauthenticated endpoint typically scores:
`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` = **5.3 Medium**

- C:L because only email existence is leaked (not full PII)
- I:N and A:N because no data modification or availability impact demonstrated
- If the endpoint also allows code brute-forcing with economic impact, argue for C:H

## Pitfalls

- **Flash message timing**: The Rails flash is consumed on first render. If you POST then
  GET twice, the second GET shows nothing. Capture on the first GET after POST.
- **Session cookie handling**: Must use `-c cookies.txt -b cookies.txt` on BOTH the GET
  (for CSRF) and the POST (to maintain session). Without the cookie, the CSRF token is
  invalid and Rails returns 422.
- **Rate limit false negatives**: A 503 from the origin is not rate limiting — check if
  it's a WAF block (look at response body for block-page signatures) vs a genuine 429.
- **Turnstile/CAPTCHA on the form does not mean the endpoint is protected**: Some apps
  render Turnstile client-side but don't validate the token server-side. Always test the
  POST directly without a Turnstile token.
