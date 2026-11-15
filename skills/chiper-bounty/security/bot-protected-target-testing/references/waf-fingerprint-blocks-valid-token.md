# WAF fingerprint blocks: a valid token still gets 401

Measured 2026-10-27 (cleanshot.com, AWS WAF / CloudFront). Companion to SKILL.md §2f/§2g — those
cover "the WAF blocks curl". This one covers the harder case: **the WAF blocks your client, not your
credential**, so a perfectly valid Bearer token fails from a script while the identical token works
in the browser.

---

## 1. The symptom

| client | call | result |
|---|---|---|
| browser (logged in) | `GET /api/user` | `200` + full profile |
| Python `urllib`, **same token, byte-identical** | `GET /api/user` | `401 {"message":"Unauthenticated."}` |
| Python `urllib` | `POST /api/auth/login` (correct creds) | `429 … Error ID: AWS-WAF-CLOUDFRONT` |
| browser `fetch` | `POST /api/auth/login` (same creds) | `200` + token |

The tell is the **error string**: `Unauthenticated.` (generic, Laravel-style auth middleware) rather
than anything about the token being invalid, plus a WAF `429` carrying an `Error ID`. The token was
never evaluated — the request never reached the app.

**Why this matters beyond convenience:** every "negative" a scripted client produced on this target
is unverified until re-run from the browser. A 403/401 from Python here is a *blocked run*, and a
blocked run is neither a finding nor a negative (see `audit-pipeline-operations` §5a row 3).

## 2. Fix — run authenticated probes inside the page

The browser's origin, TLS stack and cookies are already trusted. Drive the app's own API from there:

```javascript
// SeleniumBase run_javascript, on any page of the app's origin
(async () => {
  const t = localStorage.getItem('state.token');   // this app mirrors the JWT here
  const H = {Authorization:'Bearer '+t, Accept:'application/json',
             'Content-Type':'application/json'};
  const call = async (m,p,b) => {
    const r = await fetch('/api/'+p, {method:m, headers:H,
                       body: b?JSON.stringify(b):undefined, credentials:'include'});
    return m+' '+p+' -> '+r.status+' '+(await r.text()).slice(0,150);
  };
  window.__probe = [
    await call('GET','user'),
    await call('GET','media/185794'),            // another tenant's id
    await call('DELETE','team/members/185794?delete_mode=transfer_and_delete'),
  ].join('\n');
  return 'ok';
})()
```

Then **read it back in a second call**: `window.__probe`.

### 2.1 Three traps in that snippet (all cost real time)

1. **The MCP `run_javascript` return value is unreliable for async or large results.** Every object
   came back `{}`; a promise came back `[object Promise]`; top-level `await` threw
   `ReferenceError: await is not defined`. Stash the joined string on `window.__probe` inside the
   async IIFE, return a trivial `'ok'`, and read `window.__probe` in a follow-up call.
2. **`credentials:'include'` is mandatory** on same-origin fetches when the app also uses cookies —
   without it you get a 401 that looks like an auth bug.
3. **Batch related probes into one IIFE.** Each `run_javascript` round-trip is a separate call; a
   13-probe matrix is one IIFE returning one string, not 13 calls.

## 3. If you must use Python — the header set

```python
HDRS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://<app-host>",
    "Referer": "https://<app-host>/<app-path>/",
    "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
}
```
Even with all of that the JA3/TLS fingerprint may still be blocked — so **treat Python as the
fallback and the browser as the primary** for authenticated work on a WAF'd target.

## 4. Login by clicking can silently no-op

Clicking `Log in` produced no navigation and no error; the page still showed the form. Cause: the
SPA re-rendered between the `fill_input` calls and the click, so the fields were empty at click
time. Verify before concluding anything:

```javascript
JSON.stringify({email:document.querySelector('#email')?.value,
                pw:document.querySelector('#password')?.value?.length,
                remember:document.querySelector('#remember')?.checked})
```
If the fields are empty, re-fill and re-click — or skip the UI entirely and drive the API from
inside the page, then seed the token yourself:

```javascript
(async () => {
  const r = await fetch('/api/auth/login', {method:'POST', credentials:'include',
    headers:{'Content-Type':'application/json','Accept':'application/json'},
    body: JSON.stringify({email:'<acct>', password:'<pw>', remember:true})});
  const t = await r.text();
  if (r.status === 200) localStorage.setItem('state.token', JSON.parse(t).data.token);
  return r.status + '|' + t.slice(0,180);
})()
```

## 5. Harvesting tokens for two accounts

For a cross-account matrix you need both tokens. Sequence that worked:
1. Log in as A in the browser → read `localStorage` → save the token.
2. `POST /api/auth/logout` from inside the page **and** `localStorage.removeItem('state.token')` —
   the SPA's session is persistent, so navigating to `/login` alone still lands you in the app.
3. Log in as B (UI or the in-page API call above) → read `localStorage` → save.
4. Decode both JWTs (`base64` the middle segment) and **print the `sub` claim** to confirm which
   account each token belongs to before running the matrix — a silent mix-up invalidates the whole
   differential.

## 6. Cooldown is real; do not treat it as a permanent block

The same host that 429'd Python answered `200` again from the browser ~20 minutes later. A WAF
throttle is operational state: wait it out, keep working on unauth surface, and re-verify from the
browser rather than concluding "the API is closed".
