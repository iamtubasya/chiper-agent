---
name: flexreg-anti-automation-bypass
description: Test United Internet flexreg registration APIs (mail.com/GMX/WEB.DE register-service) when the wizard bails out client-side. Block the hilfe.* bail-out navigation with page.route to keep the JS context alive for direct API calls.
metadata:
  hermes:
    tags: [security, bug-bounty, registration, anti-automation, united-internet, playwright]
---

# Flexreg Anti-Automation Bypass (United Internet: mail.com / GMX / WEB.DE)

## When to use
- Testing register-service.{gmx.net,web.de,mail.com} (flexreg 2.14.1) and the wizard
  redirects to `hilfe.<brand>/kundenservice/flexreg.html` ("Registrierung fehlgeschlagen")
- `/aliases` starts returning `urn:problem:mam:flexreg:denial-error` after probing
- Any target where a client-side JS bail-out destroys the page context mid-flow

## The technique (verified 2026-10-25, mail.com engagement)

The bail-out is a **client-side navigation** triggered after an API response. It kills
the Playwright/Camoufox execution context, so `page.evaluate(fetch(...))` fails with
"Execution context was destroyed" / NetworkError. Fix: **block the navigation** so the
context survives and the flow cookies stay usable:

```python
await page.route('**hilfe.gmx.net**', lambda route: asyncio.ensure_future(route.abort()))
```

Then: load wizard → fill step-1 form → solve captcha → wait for the
captcha-verification + personal-info POSTs to actually fire → call the API directly
with `page.evaluate` (do NOT wait for the next UI step — it will never come).

### Captcha click: use a REAL click, and poll for the API call (corrected 2026-10-25)

Earlier note said `dispatch_event('click')` is more reliable — **that is wrong**; a
later session hit runs where dispatch_event never fired the API calls at all (only
`GET /config` appeared, alias input stayed disabled). The reliable pattern:

```python
await page.wait_for_selector('.cf-checkbox', timeout=30000)
await page.wait_for_timeout(4000)          # let the widget stabilise
await page.locator('.cf-checkbox').first.click(timeout=10000)   # REAL click
# then POLL for the API calls, retrying the click up to 4x:
for attempt in range(4):
    for _ in range(6):
        await page.wait_for_timeout(2500)
        if any('captcha' in p for _, _, p, _ in reqs) and any('personal-info' in p for _, _, p, _ in reqs):
            break
    else:
        await page.locator('.cf-checkbox').first.click(timeout=8000)  # or dispatch_event as fallback
```

### Response mocking when the API denies you (route.fulfill)

If `/aliases` answers `401 denial-error` the wizard disables the alias input and shows
"Your email address or account cannot be created right now". To keep a registration
flow alive for API testing, intercept and mock the denied response:

```python
FAKE = json.dumps({"available": True, "suggestions": [
    {"name": "RESEARCHER_NAME.susanto@gmx.de", "product": "gmxnetFree", "gid": "1"}],
    "productType": "gmxnetFree"})
async def mock(route):
    if route.request.method == 'POST' and 'aliases' in route.request.url:
        await route.fulfill(status=200, content_type='application/json', body=FAKE)
    else:
        await route.continue_()
await page.route('**register-service.gmx.net/**', mock)
```

Note: mocking only fixes the CLIENT side — the server-side alias check on final
submission may still deny. The block is per-IP and time-based; it lifts after a
cooldown (observed ~30–60 min, sometimes longer after heavy probing).

## Flexreg API map (register-service.gmx.net)

Headers on every call: `x-ui-app: flexreg/2.14.1`, `credentials: 'include'`.
Flow id comes from `GET /config?product=gmxnetFree&defaultCountryCode=DE`
(`registrationFlowId`); cookies `reg-flow-data0/1`, `chunks-flow-data` are
**encrypted and bound to the flow id** (random flow id → 401 cookie-validation-error).

| Step | Path | Content-Type | Notes |
|---|---|---|---|
| captcha | POST /captcha-verification | application/json | body {captchaFox:{userSolution},registrationFlowId} → 204, sets binding cookies |
| identity | POST /personal-info | ...flexreg.user.personalinfo-v1+json | {registrationFlowId,firstName,lastName,birthDate} → 204 |
| alias check | POST /aliases | ...flexreg.alias.suggestioninput-v2+json | {registrationFlowId,amount,wishAlias,mode:"alias"} → **available:true/false = account-existence oracle** |
| alias pick | POST /alias-selection | json | → 204 |
| address | POST /address-details | json | → 204 (country list is EU-only; validation is lenient) |
| password | POST /password-check | json | → 204 |
| phone | mTan step | — | SMS required; config: codeLength 6, maxVerificationAttempts 3, requestCooldownS 60 |

## Pitfalls
- **Do not bail early on `hilfe` in page.url** — the API calls still succeed; only the
  UI redirects. Waiting for the next form (`input[name="alias"]`) times out.
- `/aliases` gets denial-error'd after sustained probing from one IP; the block lifts
  after a cooldown (tens of minutes). captcha-verification/personal-info keep working.
- Registration is limited to ~1 successful flow per cooldown window per IP.
- mail.com signup itself is geo-blocked at the platform-mesh edge (403 all paths from
  non-allowed countries, e.g. Indonesia); GMX/WEB.DE wizards load but share the block.
- `password.gmx.net` / `password.web.de` do not exist (NXDOMAIN) — password recovery
  is mail.com-branded only (`password.mail.com/passwordrecovery/`, Wicket app,
  session-bound `srttkn`).

## Related
- geo-block-proxy-ops (proxy/fingerprint discipline for registration gates)
- bug-report-delivery (draft staging: Gmail REST token dead, use IMAP App-Pw path)
