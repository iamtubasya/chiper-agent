# Django REST Framework target recon and auth-flow testing (djangoeurope, 2026-10)

DRF hosting-panel/API targets have a recognizable shape. This is the unauthenticated sweep that
maps one fast, in the order that pays off.

## 1. The root endpoint is a free map

`GET https://api.<target>/` on a DRF deployment returns the full endpoint index as JSON
(`{"user": ".../user/", "token": ".../token/", ...}`). djangoeurope exposed 55 endpoints this way,
including the sensitive names (token, otpdevice, sshkey, stripe/*, invoice). Save it as the
attack-surface list before probing anything.

## 2. Unauthenticated sweep — classify every endpoint

GET each path with no credentials and bucket by status:

- **200** → open. Usually reference data (language, country, timezone, plan, doc, faq) — but check
  each body for infra detail. `/server/` on djangoeurope returned server hostnames, CPU/RAM/disk,
  OS and package versions, hosting provider and locations: a real (Low) info disclosure.
- **401/403 `{"detail":"Authentication credentials were not provided."}`** → auth-gated. Note that
  OPTIONS is gated too, so you cannot read the serializer metadata unauthenticated.
- **422 with a serde/validation message** → reachable without auth; the error names required
  fields, which is free schema enumeration.

## 3. Write-method check on the open endpoints (the DRF misconfig hunt)

For every GET-open endpoint, POST a minimal JSON body. Correct DRF config answers 401 on POST
(per-method permissions, e.g. IsAuthenticatedOrReadOnly). A 200/201/400-business-error instead
means the write path is missing its permission class — that is the finding. djangoeurope: all 7
tested endpoints correctly 401'd on POST.

## 4. Auth-flow enumeration tests (run all three, compare bodies verbatim)

| Flow | Endpoint shape | Enumeration signal |
|---|---|---|
| Login | POST `/login/` | different error for existing vs nonexistent user |
| Password reset request | POST `/password_reset/` | different response/timing for existing vs nonexistent |
| Registration | POST `/user/` | "email already registered" vs generic |

djangoeurope was clean on all three (uniform `Unable to log in with provided credentials.` and
uniform `{"status":"OK"}`). Also inspect every response FIELD, not just the error: the contact-form
response carried `"is_registered": false` — a potential enumeration oracle. If you cannot
demonstrate the flip (no known-registered address), log it as UNCONFIRMED, do not claim it.

## 5. Payment webhooks — test verification, not just reachability

An imprint/config endpoint often leaks the payment webhook path (djangoeurope: `/imprint/` exposed
`https://api.djangoeurope.com/payment/paypal/notify/` plus bank details and the Stripe pk_live key
— imprint data is public by design in CH/EU, the webhook path is the useful part). Then:

1. POST an empty body → the validator's field errors reveal the expected IPN fields
   (`txn_id is not set` → `wrong destination email: None` → `wrong destination email: <value>`).
2. Set the destination to the value the error names (the PayPal account email from the imprint).
3. Send a complete forged IPN. `{"non_field_errors":["paypal VERIFIED failed: INVALID"]}` means the
   handler DOES call back to PayPal with `cmd=_notify-validate` — working control, record the
   negative. A 200/201 on a forged IPN is the finding.

## 6. Throttling and anti-fraud are separate layers

djangoeurope registration sat behind an ALTCHA PoW (see `client-reverse` →
`references/altcha-pow-captcha-reversal.md`). Solving the PoW still produced
`{"non_field_errors":["Detected as spam."]}`, then `429 Request was throttled ... Retry-After: 86399`
— a 24h IP throttle. Budget for it: when registration closes, pivot to the unauthenticated surface
and record the throttle as the reason the authenticated surface is untested (a coverage limit, not
a clean bill of health).

## 7. Subdomain sweep via DoH (not CT — CT times out)

Resolve a candidate list (api, panel, mail, webmail, staging, dev, docs, admin, monitor, git, ws,
cdn, static, assets, billing, account) against `https://dns.google/resolve?name=X&type=A`. Live
hosts that fail HTTPS may serve plain HTTP — always retry with `http://` and `-k`:

- `staging.` → HTTP 200, production copy
- `dev.` → Django app, SSH(22)+443 open, self-signed cert; test `/nonexistent` for a Django DEBUG
  traceback (Page not found + URLconf) — its absence is a verified control
- `docs.` → default Sphinx install; probe `_sources/` (listable?), `objects.inv`, `_downloads/`
- `mail./webmail.` → often 301s to a catch-all

## 8. WebSocket endpoints

Panel bundles construct WS URLs as `wss://api.<target>/ws/<id>?token=<JWT>` with a
`Sec-WebSocket-Protocol: token.<JWT>` subprotocol. Test the handshake with a raw socket
(Upgrade headers, no lib needed): no-token / garbage-token / garbage-token+subprotocol should all
fail identically at the HTTP layer (400). A 101 Switching Protocols without a valid token is the
finding; uniform 400s are a verified control.

## Pitfalls

- MSYS `/tmp` paths are invisible to the Windows Python interpreter — write probe outputs to a
  file inside the workspace, not `/tmp/x.json`, or your parse step eats a FileNotFoundError.
- A 500 on a probe is usually YOUR input, not the target: an invalid base58/identifier gets a
  generic 500 from strict validators. Re-test with a known-valid value before recording it.
- DRF "Not Found" pages are the framework default 404 HTML, not a SPA fallback — useful for
  distinguishing real routes from catch-alls.
