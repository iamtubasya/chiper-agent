# Payment / Plan-Entitlement Bypass Testing (SAFE boundary + recipe)

Source: quarterwise.co.uk audit, 2026-09-28. User asked: *"sudah kamu coba dari sisi payment utk
upgrade ke pro? apakah bisa bypass tanpa perlu bayar spt fake payment atau ad celah lain?"*

This file exists because that question has a **hard line** through it, and because the
*legitimate* half (entitlement bypass) is a real, high-value bug class worth testing properly.

---

## 1. The line (state it, then test only the allowed half)

| Allowed — real bug-bounty class | NOT allowed — fraud, refuse |
|---|---|
| Can the Pro/paid entitlement be obtained **without a verified payment**? | Completing a **fake payment** |
| Is plan/price/interval **client-supplied and trusted**? | Forging a **valid-looking** payment-provider webhook to actually grant entitlement |
| Does a fabricated "success" return URL flip the plan? | Any action that takes real goods/service without paying the merchant |
| Are webhook signatures **verified**? (test with invalid sig — must 4xx) | Replaying a *captured real* webhook to steal entitlement |

Fraud is not security research and is not covered by an engagement — a security team cannot
"approve" a fake payment to a live account. **Do the entitlement analysis; never execute the
fraud.** Say so plainly when pushed, then continue with the allowed tests.

## 2. Map the entitlement path first

```bash
# a) find the billing action + its ONLY client field
grep -oE '\$ACTION_ID_[a-f0-9]+' billing.html
grep -oE '<input[^>]*name="[^"]+"[^>]*value="[^"]*"' billing.html     # e.g. name="interval" value="annual"
# b) confirm there is NO client-facing setPlan action
grep -rhoE 'createServerReference\("[a-f0-9]{40,}"[^)]*"[A-Za-z0-9_]*(Plan|Billing|Subscription|Checkout)[A-Za-z0-9_]*"' js/
# c) find the webhook
for p in /api/stripe/webhook /api/webhooks/stripe /api/billing/webhook /api/checkout/webhook; do
  printf '%s ' "$p"; curl -s -o /dev/null -w 'GET:%{http_code} ' "$P"; \
  curl -s -o /dev/null -w 'POST:%{http_code}\n' -X POST -H 'Stripe-Signature: t=1,v1=deadbeef' -d '{}' "$P"
done
```
A `GET 405 / POST 400 "missing signature"` = webhook exists and gates on signature. `404` on
the alternates = only one real endpoint.

## 3. The tests (all read-only w.r.t. money)

```bash
# 1) click upgrade, do NOT pay → redirects to checkout.<provider>.com; plan must stay free
# 2) fabricate success return-URLs → plan must NOT change
for u in "/app/billing?success=1" "/app/billing/session_id=cs_live_FAKE" \
         "/app/billing/success" "/api/stripe/success?session_id=cs_live_FAKE" \
         "/app?upgraded=1" "/app/account?plan=pro"; do
  curl -s -H "Cookie: $CK" "https://$T$u" | grep -oE "on the <strong>[a-z]+" ; done   # expect: free, every time
# 3) forged webhook, well-formed signature, random secret → must be 400 invalid signature
SIG=$(printf '%s%s' "$PAYLOAD" "$TS" | openssl dgst -sha256 -hmac 'whsec_fake' | sed 's/.*= //')
curl -s -X POST -H "Content-Type: application/json" \
     -H "Stripe-Signature: t=$TS,v1=$SIG" -d "$PAYLOAD" "https://$T/api/stripe/webhook"
# expect: {"error":"invalid signature"}   (HMAC verified against the real secret)
# 4) submit the billing action with tampered interval (lifetime_free/pro/0/'') → no entitlement path
```

## 4. Verdict + severity

- **All negative (typical for a competent build):** entitlement is granted only by a
  **signature-verified webhook**; client flags, return-URLs, and field tampering have no
  effect. Report as *verified secure design*, no finding.
- **Finding only if:** a client flag/return-URL/field actually changes the plan, OR the
  webhook accepts an unsigned/forged event, OR plan state is readable-but-not-writable while
  the entitlement check reads a client value. Then: Free→Pro without payment = High, and the
  proof is the plan-diff with a *non-paid* account (never a completed fake payment).

## 5. Related: free-plan feature gating (why entitlement tests also matter)

When probing plan boundaries, confirm the *gate is server-side* for each paid feature — the UI
hiding a button is not a gate:
- expected messages that prove enforcement: `"…is a Pro feature"`, `"Your free plan includes 1
  income source"`, `"Two-factor authentication is required before …"`.
- A gate that returns a plain `200` with rendered content may still be UI-only — test the
  **action/API** under the paid feature path with a free session before calling it enforced.
