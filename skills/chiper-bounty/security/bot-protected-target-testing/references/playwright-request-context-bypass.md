# Playwright `context.request` — browser-TLS bypass for Cloudflare bot management

## When to use
`curl` returns `000`/empty and even `httpx` can only GET (or gets empty bodies for POST) against a
Cloudflare bot-managed host — but you still need to POST JSON and READ the response body. This is the
exact case for Bloom (api.bloomcredit.io, api.bloomplus.com, satori.bloomcredit.io): curl = `000`,
httpx GET = works (401/405/404), but no clean POST body read.

## The unlock: `context.request` (Playwright APIRequestContext)
`ctx.request` is Playwright's **APIRequestContext** — it sends real HTTP through the browser's
networking stack (real Chrome TLS/JA3 fingerprint, real cookies) and it is **NOT subject to CORS**.
It can GET/POST/DELETE and returns the raw body. This is the reliable POST path through bot mgmt.

```python
from playwright.async_api import async_playwright
ctx = await p.chromium.launch_persistent_context(
    PROFILE, headless=False,
    executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    args=["--disable-blink-features=AutomationControlled"],
    user_agent="... Chrome/120 ...",
)
req = ctx.request                      # <-- APIRequestContext, NOT page.evaluate(fetch)
r = await req.post("https://host/v2/endpoint",
                   data={"k":"v"}, headers={"Content-Type":"application/json"})
body = await r.text()                  # <-- MUST await; it is a coroutine, not bytes
```

## Gotchas that cost time (all hit this session)
1. `ctx.request` has methods `.get()` / `.post()` / `.fetch()` — there is NO `.request()` method.
   Calling `req.request(...)` raises `AttributeError: 'APIRequestContext' object has no attribute 'request'`.
2. `resp.text()` is a coroutine — `resp.text()[:N]` raises `coroutine is not subscriptable`. Always
   `await resp.text()` (or `.json()`).
3. Do NOT try `page.goto("<api-host>/")` then `page.evaluate(fetch(...))`. If the root is 4xx/empty,
   the page lands on `chrome-error://chromewebdata/`, the origin is never established, and every
   same-origin `fetch()` throws `TypeError: Failed to fetch`. Use `ctx.request` instead — it does not
   need a loaded page.
4. `page.goto` raises on 4xx by default (`wait_until="domcontentloaded"`); use `wait_until="commit"`
   and wrap in try/except if you genuinely need to land on an origin.
5. Cross-origin fetch from a sibling subdomain is CORS-blocked (opaque) — same reason to prefer
   `ctx.request` for reading bodies from the API host.

## Reading error differentials
Because `ctx.request` returns real bodies, you can finally see the 401 body an Envoy/KrakenD/FastAPI
gateway emits for a bearer endpoint (e.g. `{"detail":"bearer token required"}` vs
`{"detail":"token missing kid header"}` vs `{"detail":"token signing key not found"}`). That
differential is exactly what tells you the auth is JWT+JWKS and how far down the validation chain
each crafted token gets.