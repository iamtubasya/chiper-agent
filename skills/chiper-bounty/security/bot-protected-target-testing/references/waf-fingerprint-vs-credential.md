# WAF blocks by client fingerprint, not by credential

Measured 2026-10-27 (cleanshot.com, AWS-WAF behind CloudFront).

## The shape of the failure

A Bearer JWT that returns `200` from a real browser returns
`401 {"message":"Unauthenticated."}` from Python `urllib`/`requests`.

- the token is **byte-identical** to the one the browser holds (verified by reading
  `localStorage` and diffing the JWT `sub` claim)
- the headers were copied from the browser: `Origin`, `Referer`, `Sec-Fetch-Dest/Mode/Site`,
  `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`, `Accept-Language`, `Accept`
- re-logging-in through `POST /api/auth/login` from Python also returns 429/401

Conclusion: the block is on the **client shape** (TLS/JA3 fingerprint + header ordering), not on
the credential. No amount of header copying fixes it, and the fix is not "get a better token".

## Working method — probe from inside the browser context

1. Log in once in a real browser (SeleniumBase Pure CDP, headed, works for Turnstile-gated
   signup when the widget auto-solves on page load).
2. Harvest the token: `localStorage.getItem('state.token')` (SPA convention — confirm the key
   name by dumping `Object.keys(localStorage)` first).
3. Run every authenticated probe through the page's own `fetch`:

```js
(async () => {
  const t = localStorage.getItem('state.token');
  const H = (b) => b
    ? {'Authorization':'Bearer '+t,'Accept':'application/json','Content-Type':'application/json'}
    : {'Authorization':'Bearer '+t,'Accept':'application/json'};
  const call = async (m,p,b) => {
    const r = await fetch('/api/'+p, {method:m, headers:H(!!b),
                                      body: b?JSON.stringify(b):undefined,
                                      credentials:'include'});
    return m+' '+p+' -> '+r.status+' '+(await r.text()).slice(0,150);
  };
  window.__probe = (await Promise.all([
    call('GET','user'), call('GET','team'), call('GET','media'),
  ])).join('\n');
  return 'ok';
})()
```

4. **Read `window.__probe` in a SEPARATE tool call.** The MCP `run_javascript` bridge serialises
   a large returned object to `{}` — a string on `window` survives the round-trip, a big inline
   return value does not. Two calls per batch, not one.

## Operational notes

- **Expect the WAF to start 429-ing the SPA login page itself** after a few dozen API calls.
  Body: `We detected unusual traffic from your network… Error ID: AWS-WAF-CLOUDFRONT`.
  That is a cooldown, not a permanent block — wait it out (15–30 min) rather than switching
  egress or concluding "signup blocked".
- The same 429 can hit a *content-dependent scanner* mid-run (linkfinder printed its usage
  banner while reporting `HTTP Error 429`). See `audit-pipeline-operations` §E2 — a usage banner
  on an error path is not a CLI fault.
- `401` from Python while the browser gets `200` is the diagnostic signature. If you see it,
  stop re-authenticating and move the probe into the browser.

## What this does NOT mean

This is not "browser tools work and Python does not" as a standing rule — it is "this vendor's
WAF fingerprints the client, so the client must be a browser for authenticated probes".
Unauthenticated recon (subfinder, httpx, katana, gau, nuclei at low rate) still works fine from
Python against the same host.
