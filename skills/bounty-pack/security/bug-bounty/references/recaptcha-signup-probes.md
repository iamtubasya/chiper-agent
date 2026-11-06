# Captcha-Gated Signup/Registration Flows on Bug Bounty Targets (reCAPTCHA v3 case study)

Field notes from probing `staging.luno.com` signup (Sep 2026). Class of problem: a target's signup/login form silently does nothing when automated — the cause is a captcha integration mismatch, not a bot-block. Diagnose before reaching for a solver.

## Why "button does nothing" is usually NOT WAF/bot-blocking

Silent-dead submit buttons on captcha-gated forms come from JS errors inside the app's own captcha handler, which is caught and swallowed. Distinguish via evidence:

- **App-side integration error** (captcha fires but page JS throws): network log shows ZERO POST to the signup endpoint on click. Analytics beacons (e.g. gtag `form_submit`) still fire. This is a target-side weakness — potentially a finding angle (captcha enforcement can be bypassed on the API if the endpoint itself doesn't validate).
- **Server-side enforcement** (captcha required by API): direct curl POST without token → `ErrCaptchaRetryRequired`-style error. Confirms the API validates tokens; UI automation must produce a real token.

**Error-oracle tip:** POSTing the raw endpoint directly with a dummy/absent token is a cheap, low-noise probe that tells you exactly which failure mode you're in before any browser automation.

## Diagnosis path that worked (in order)

1. `performance.getEntriesByType('resource')` from the browser → did a request to the signup endpoint ever fire? (transferSize 0 + no entry = never sent)
2. Probe the captcha global in the **page main world** (see camoufox skill: isolated-world evaluate can't see `grecaptcha`): check `typeof grecaptcha`, `grecaptcha.enterprise` present or not, sitekey.
3. Walk `___grecaptcha_cfg.clients` to find rendered widgets. Gotchas: `clients` may be an object (not array — `.forEach` throws); walking hits **cross-origin objects** (the widget iframe handle) → wrap every property read in try/catch and only recurse into plain `[object Object]`; the sitekey lives a few levels down (e.g. `root.i.i.sitekey`).
4. Decide the mismatch:
   - `render=explicit` in the api.js URL → `grecaptcha.execute()` takes a **widget id (number, usually 0)**, NOT the sitekey string. Passing the sitekey makes `execute()` hang forever.
   - App code calls `grecaptcha.enterprise.*` but page loaded standard api.js → `grecaptcha.enterprise` is `undefined` → app handler throws on every click. Token via standard API may still work if the backend accepts it.

## Getting a token via main-world injection (browser automation)

From isolated-world evaluate, inject: `<script> (async () => { const t = await new Promise((res,rej)=>{ grecaptcha.ready(()=> grecaptcha.execute(0, {action:'signup'}).then(res).catch(rej)); setTimeout(()=>rej(new Error('timeout')), 25000); }); ... document.documentElement.setAttribute('data-out', JSON.stringify(out)); })(); </script>` — then poll the attribute. Full worked scripts: `D:\data hermes\bug-bounty\_progress\luno\` (rc_cfg3.py, mainworld_signup.py, signup_widgetid.py).

Then POST the signup endpoint **from page context** (same injected script, `credentials:'include'`, URLSearchParams body) so cookies/origin are right.

## Solver fallback

If a genuine token can't be produced in-browser (enterprise enforcement, score requirements): Boterdrop solver `POST localhost:8000/recaptchaV3` `{sitekey, pageurl, action}` → poll `GET /result?id=`. v3 tokens are single-use and expire in ~2 minutes — fetch and submit immediately.

## Finding-angle reminders

- If the UI flow is broken by the target's own captcha mis-integration but the API endpoint accepts a standard-v3 token where enterprise is intended — that's an auth-flow weakness worth documenting (enforcement mismatch).
- Always capture: endpoint, required params, error strings for missing/invalid tokens, and proof of which integration the page loads (api.js URL, sitekey, enterprise flag).
