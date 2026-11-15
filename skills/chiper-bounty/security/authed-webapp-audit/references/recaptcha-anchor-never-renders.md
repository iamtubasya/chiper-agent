# reCAPTCHA v2 checkbox that never renders its anchor (and the 5-attempt cutoff)

Measured 2026-10-31 on `apps.clever.com` (dev signup SPA). Five attempts across two egress IPs.

## The failure shape

The reCAPTCHA v2 checkbox widget is present and looks healthy from the outside, but its
internals never initialise:

```python
# OUTSIDE — looks fine:
#   iframe[src*='recaptcha/api2/anchor']  present, 256x60, class 'grecaptcha-logo'
#   iframe[src*='recaptcha/api2/bframe']  present
#   typeof grecaptcha !== 'undefined'     true

# INSIDE — dead:
fr = pg.frame_locator("iframe[src*='recaptcha/api2/anchor']")
fr.locator("#recaptcha-anchor").count()          # -> 0  (never becomes 1, 20-poll)
await pg.evaluate("()=>{const t=document.querySelector('textarea[name=g-recaptcha-response]');"
                  "return t?t.value.length:-1}")  # -> 0
await pg.evaluate("()=>grecaptcha.execute()")     # -> EXEC RESULT: timeout
```

`count() == 0` on `#recaptcha-anchor` is the decisive signal. **There is nothing to click** —
so the two techniques that normally rescue a stuck captcha do not apply:
- clicking the anchor checkbox (works when the node exists)
- `grecaptcha.execute()` / `executeAsync()` (times out here)

## Rule out the usual causes first, then stop

| Cause | Test | Verdict here |
|---|---|---|
| IP/egress reputation | re-run on a fresh egress (`warp-cli --accept-tos connect`, confirm via `api.ipify.org`) | identical `len=0` on both IPs → **not** reputation |
| ad-blocker / script block | check `typeof grecaptcha`, whether `api.js` loaded | loaded, defined |
| wrong sitekey | read the `k=` param off the anchor iframe | matched the bundle's `recaptchaPublicKey` |
| client-side gate only | POST the endpoint without the token | `400` — server genuinely requires it |

**Do not rotate egress further once two IPs fail identically.** It is not reputation; each extra
rotation is wasted time and additional noise on the target.

## Capture the server-side requirement as evidence

Before giving up, confirm the token is actually required — this turns "couldn't sign up" into a
documented gate rather than a guess:

```bash
POST /signup/self-serve/verify-email  {"fullName":"x","workEmail":"x@y.z","honeypot":""}
# -> 400 Bad request
```
and grep the bundle for the client contract:
```python
# main.js showed: executeAsync() -> on null token throws
#   {"error":"We couldn't verify you're human. Please disable any ad blockers and try again."}
# then posts {...fields, captchaToken: token}
```
So the field is `captchaToken`, sourced from reCAPTCHA, and the endpoint rejects its absence.
That is the evidence to record.

## The 5-attempt cutoff (operator rule)

Standing instruction for account-provisioning work: **if 5 consecutive attempts to create an
account fail, stop and move to the next target.** Do not keep iterating variants — different
email domain, different profile, different egress — past that budget.

- Count attempts honestly. Three signup runs + two egress variants = five.
- When reporting the block, state the attempt count and the egresses tested, so the next session
  does not restart the same ladder from zero.
- The engagement loses more from an hour burned on one captcha than from one unreached authed
  plane; the unauthenticated surface is still fully testable and is where the next lead comes from.

## Related

- Invisible-reCAPTCHA that fires anchor+bframe but no app XHR (a *different* failure — the widget
  initialises, the app never sends) → `saas-test-account-provisioning` §3e.
- Cloudflare Turnstile whose widget needs a real click at the checkbox offset → same skill, Step 3j.
- Note: `saas-test-account-provisioning` is user-owned; this file lives here because that skill
  cannot be patched by autonomous curation. If it is adopted
  (`hermes curator adopt saas-test-account-provisioning`), consider relocating this section there.
