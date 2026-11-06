# Akamai / bot-manager challenge playbook

Symptom → cause → fix. Symptoms are from real engagements, not documentation.

## Symptom table

| What you see | Actual cause | What works |
|---|---|---|
| `403` HTML "Access Denied … errors.edgesuite.net" on `curl` | Akamai; TLS/header fingerprint, not UA | visible real Chrome (`channel="chrome"`, `headless=False`) |
| Same 403 after adding full browser headers | headers are not the signal | as above; do not keep tweaking headers |
| `403` on headless Chromium but the site "works for users" | headless detected | `headless=False` |
| `200` in Chrome, but `curl`/`ctx.request` for the *same URL* → 403 | `ctx.request` has its own fingerprint | `pg.evaluate("async u => (await fetch(u)).text()", url)` |
| `429 {"cpr_chlge":"true","t":"…"}` from an XHR endpoint, including the site's own | Akamai CPR challenge on the API host | often not solvable; treat as a coverage gap and say so |
| Everything worked, then mass 403 after ~50–150 requests | IP reputation / rate | back off, batch, slow down |
| `page.goto(url)` returns a page whose title is "Access Denied" | you are parsing the challenge | assert on title/status before parsing anything |
| JS bundle is 400 bytes of `<HEAD><TITLE>Access Denied` | bundle fetch blocked; you saved the error page | fetch bundles via `pg.evaluate`, and assert size > 1 KB |

## Harness

    from playwright.sync_api import sync_playwright
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/139.0.0.0 Safari/537.36")

    def harness(pw=None, state=None):
        pw = pw or sync_playwright().start()
        br = pw.chromium.launch(headless=False, channel="chrome",
                                args=["--disable-blink-features=AutomationControlled",
                                      "--no-sandbox", "--start-maximized"])
        ctx = br.new_context(viewport={"width": 1440, "height": 900}, user_agent=UA,
                             locale="en-AU", timezone_id="Australia/Sydney",
                             extra_http_headers={"Accept-Language": "en-AU,en;q=0.9"})
        if state:
            ctx = br.new_context(**{**kw, "storage_state": state})
        return pw, br, ctx, ctx.new_page()

Match the target's market in `locale` + `timezone_id`. Keep one long-lived browser and open
pages/tabs in it rather than relaunching per step.

## Stability: the browser fights back

Challenges trigger client-side navigation, so an in-flight `evaluate` dies with
"Execution context was destroyed, most likely because of a navigation". Do not treat this as
a tool failure — wrap every page-evaluate in a retry that re-navigates and settles first:

    def settle(pg, url="https://<host>/", tries=6):
        for _ in range(tries):
            pg.goto(url, wait_until="domcontentloaded", timeout=90000)
            for _ in range(6):
                pg.wait_for_timeout(2500)
                if pg.url.startswith(url) and "Access Denied" not in (pg.title() or ""):
                    return True
        return False

    def do(pg, js, arg):
        for _ in range(3):
            try:
                return pg.evaluate(js, arg)
            except Exception:
                settle(pg)
        return {"err": "unstable"}

Also attach listeners defensively: a bare `pg.on("response", lambda ...)` that throws inside
the handler tears down the CDP pipe (EPIPE, `Node.js` stack spew). Guard handler bodies, or
push onto a list and process afterwards.

## Security headers

`response.headers` is filtered. To claim a header is missing, use `response.all_headers()`:

    r = pg.goto(url, wait_until="domcontentloaded", timeout=90000)
    h = r.all_headers()

Then report the pattern, not the single fact: "storefront sends no CSP / X-Frame-Options /
Referrer-Policy / Permissions-Policy, HSTS is `max-age=86400` with no `includeSubDomains`,
and cookies are set without Secure/HttpOnly/SameSite — while the API sibling host *does* send
a full CSP set". That inconsistency is the actionable line.

## Cookies worth diffing on a protected site
Anonymous-visit identifiers (GA4 id, a `server_visitor_id`, a session cookie) are often stable
per browser. If a token/broker endpoint accepts a client-supplied identifier header and returns
the *same* token for the same identifier, the interesting question is not "can I make one"
(anyone can, by design, on a public storefront) but "is that identifier guessable". Trace it
in the bundle: `crypto.randomUUID()` / a GA4 client id is high entropy; a hash of IP+UA, a
timestamp, or a counter is not. Without a real artefact to test, report it as an observation.

## Language for the coverage gap
    "The GraphQL endpoint at <host> returns HTTP 429 with {"cpr_chlge":"true"} to this
     environment, including to the storefront's own XHR calls. I extracted the query documents
     and operation names from the client bundle (see attachments) but could not execute them,
     so I make no claim about that API in either direction."
