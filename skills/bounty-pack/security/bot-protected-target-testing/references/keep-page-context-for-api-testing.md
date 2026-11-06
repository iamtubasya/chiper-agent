# Keep the page context alive: browser-driven API testing when the app evicts you

## The failure mode

SPA wizard / registration / recovery apps frequently **evict the tester**: after N
attempts, on an anti-automation trigger, or mid-flow, the client redirects to a help /
bail-out page (`hilfe.<brand>.net/kundenservice/...`, "Registrierung fehlgeschlagen",
"We're sorry we can't sign you up"). In Playwright/Camoufox this kills the execution
context, so every follow-up `page.evaluate(fetch(...))` dies with:

```
playwright._impl._errors.Error: Page.evaluate: Execution context was destroyed,
most likely because of a navigation.
```
or, one call later, `NetworkError when attempting to fetch resource.`

The trap: **the UI bails but the API often still answers.** In the worked case the
wizard redirected to the help page, yet `POST /captcha-verification` and
`POST /personal-info` still returned `204` — only the specific endpoint under abuse
watch (`/aliases`) returned a `denial-error`. Giving up on the UI redirect throws away
a live API surface.

## The fix: block the bail-out navigation

Route-abort the eviction target so the SPA never leaves its origin and the JS context
survives:

```python
await page.route('**hilfe.gmx.net**', lambda route: asyncio.ensure_future(route.abort()))
```

Then drive the flow as usual (fill form, solve captcha) and call the API directly with
`page.evaluate` — cookies set by earlier steps are still attached to the context.

## Pitfall: `credentials:'include'` or your cookies never leave

A `fetch()` from `page.evaluate` does **not** send cookies by default. Without it the
server sees an anonymous request and answers `cookie-validation-error` (401), which
reads exactly like "your session is invalid" and sends you debugging the wrong thing:

```javascript
const res = await fetch('https://api.example/endpoint', {
    method: 'POST',
    credentials: 'include',          // <-- mandatory
    headers: {'content-type': 'application/vnd...', 'x-ui-app': 'flexreg/2.14.1'},
    body: JSON.stringify({...})
});
```

## Pitfall: capture flow identifiers BEFORE the eviction

Flow ids / nonces minted by `/config` (or an early XHR) must be scraped from the
network stream as they happen — attach the response listener before `goto`, because
the bail-out can happen before you can read the DOM.

## Diagnose UI-block vs API-block before concluding "blocked"

Log every XHR/fetch response during the flow. If auth-ish endpoints still return
2xx while the page redirects, the block is UI-level (or endpoint-specific) and the API
remains testable. Only when the API itself denies (per-IP `denial-error`, 403 at the
edge) is the surface actually closed — and even then it is usually a cooldown
(observed: ~1 registration flow per 30–60 min per IP), not a permanent flag.

## Bonus: walking Apache Wicket wizard flows (United Internet stack)

Wicket apps (password recovery, account/ciss) expose a numbered-page state machine in
the URL. The recipe:

1. `GET /passwordrecovery/` → `302` with a fresh `srttkn` (UUID) + `JSESSIONID`
   (path-scoped, HttpOnly).
2. `GET /passwordrecovery/wicket/page?1&srttkn=<T>` → form whose **action** carries
   the live token: `action="./page?1-1.-recoveryAuthorizeForm&srttkn=<T>"`.
3. POST the form (`srttkn` hidden field + inputs) → `302 ./page?2&srttkn=<T2>` →
   fetch `page?2&srttkn=<T2>` for the next step.

Two parsing traps: Wicket emits attributes **without spaces**
(`id="srttkn"type="hidden"name="srttkn"value="..."`) so `name="srttkn" value=` regexes
miss — extract the UUID from the form `action` instead. And the token is
**session-bound**: reusing it from another cookie jar returns 401 (good security —
record it as a negative result, not a bug).

A page-2 response that lacks the step's error text while a control address shows it is
an enumeration oracle — but verify the submit actually processed (a stale/mismatched
token renders a clean page without processing, a false positive that will not
reproduce once you fix the token handling).
