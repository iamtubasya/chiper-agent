# Turnstile-gated and App-Check-gated form submission

Measured on an authorized VDP target (NGRAVE, `www.ngrave.io` data-deletion portal, 2026-10-29).
Two gates stacked: a Cloudflare Turnstile widget on the form, and Firebase App Check + Firebase Auth
(Google-SSO-only) on the API behind it. This file covers what each failure mode actually means and
which conclusions are legitimate.

---

## 1. The widget renders but never yields a token

Console shows:

```
[Cloudflare Turnstile] Error: 400020.
Failed to load resource: the server responded with a status of 400 ()
```

**400020 is "invalid widget size" — NOT "invalid sitekey".** The usual cause is the container element
being collapsed or detached when `turnstile.render()` runs (React re-render, `display:none` parent,
0×0 host div, widget mounted inside a hidden tab). The sitekey can be perfectly valid.

Quick reference for the codes you will actually meet:

| code | meaning | what to change |
|---|---|---|
| `400020` | invalid widget size / container collapsed | give the host element explicit width+height before render |
| `110100` | invalid sitekey | key is wrong or from another account |
| `110200` | domain not allowed | your test host is not in the widget's domain list |
| `110500` | missing or invalid session | token issued for a different browser session |
| `1106xx` | timeout-or-duplicate | token already redeemed — tokens are **single-use** |

Force a render yourself instead of relying on the page's React lifecycle:

```js
// in the live page context, after the widget script has loaded
window.turnstile.remove();                       // drop the broken instance
const el = document.querySelector('[data-testid="the-widget-host"]');
el.style.cssText = 'width:320px;height:80px;display:block';
window.turnstile.render(el, {
  sitekey: '0x4AAAAAAA…',                        // from the SSR payload / chunk
  theme: 'dark',
  callback: t => { window.__tok = t; },
  'error-callback': e => { window.__err = String(e); },
});
```

Read `window.__err` — it is the code above, printed instead of guessed at. Sitekeys are recoverable
from the server-rendered RSC payload (`"siteKey":"0x4AAA…"`) or the chunk that calls
`turnstile.render`.

If it still errors with `400020` after a forced render with explicit dimensions, the block is on
Cloudflare's side (widget misconfiguration on the target). That is a **target-side finding about
their form being unusable**, not a wall you can climb — note it and move on.

---

## 2. The honeypot short-circuits the bot check

The form had a hidden field (`name="company"`, `tabindex="-1"`, `autocomplete="off"`) — a classic
honeypot. Submitting with that field **non-empty** produced:

```
{"ok":true,"requestId":"CDD-7MGX-2026-1029"}
```

with an invalid/absent Turnstile token. Submitting with it empty produced `{"reason":"robot"}`.

Read the ordering carefully before you celebrate. Probing the field set one at a time gave:

| payload | result |
|---|---|
| valid email/order, honeypot empty, junk token | `{"ok":false,"reason":"robot"}` |
| bad email, honeypot empty | `{"ok":false,"reason":"invalid"}` |
| bad email, honeypot **filled** | `{"ok":false,"reason":"invalid"}` |
| valid email/order, honeypot **filled** | `{"ok":true,"requestId":"CDD-…"}` |
| valid email/order, honeypot filled, wrong confirm word | `{"ok":false,"reason":"invalid"}` |

That ordering says the handler validates input **first**, then checks the honeypot, and treats a
filled honeypot as "bot confirmed → return a plausible success and discard". A honeypot that answers
`ok:true` is a **deception response**, not a bypass — the write is deliberately dropped.

Doctrine:

- **`ok:true` from a honeypot field is never proof of a write.** Neither is a `requestId` string; it
  can be generated client-side or server-side without persisting anything.
- **Verify the side effect out-of-band**, on a channel you control: the confirmation email that
  should arrive at your own address, a record visible via an authenticated read, a webhook to your
  own listener. In this session the confirmation email never arrived → the write was **not** claimed.
- Never report "unauthenticated write / record injection" on the strength of a success body alone.
  Same rule as `bb-methodology` → Body-Diff Rule, specialised to forms.

---

## 3. The real wall is behind the form: App Check + SSO-only auth

For the API the form talks to, the useful probe set is small and decisive:

1. Call the API with no credentials → note the exact envelope.
2. Call it again adding `X-Firebase-AppCheck: <junk>`:
   - response changes from `MISSING_HEADERS` to `UNAUTHORIZED` → **the header is validated
     server-side** (real `verifyToken()` call, not a presence check).
3. Fingerprint Firebase Auth with Identity Toolkit (see `mobile-pentest` §2h-i): if
   `accounts:signUp` → `OPERATION_NOT_ALLOWED` and anonymous → `ADMIN_ONLY_OPERATION`, and
   `createAuthUri(providerId=google.com)` returns an `authUri`, then the only way in is a real Google
   account plus a Play-Integrity-passing client.

That combination is a **coverage gap, not a failure**. Write it as:

> "Authenticated surface not reachable: API requires a Firebase App Check token (junk token →
> `UNAUTHORIZED`, proving server-side verification) and Firebase Auth is Google-SSO only
> (`OPERATION_NOT_ALLOWED` for email/password, `ADMIN_ONLY_OPERATION` for anonymous). Reaching it
> requires a device passing Play Integrity plus a real Google identity."

It carries two reproducible probes, it is honest, and it stops the next session re-deriving the wall.

---

## 4. Browser-harness notes

- A Turnstile widget **cannot be solved** by clicking blind when the widget itself is in error — fix
  the render first, then the interactive checkbox appears and can be clicked through
  `frame_locator('iframe[src*="challenges.cloudflare.com"]').locator("body").click()`.
- Rendering the widget in a fresh Playwright context with the page's own sitekey is legitimate for
  an authorized test and is the fastest way to distinguish "sitekey invalid" from "my harness is
  being detected".
- Managed-challenge tokens are tied to the browser session/UA that solved them. Harvest the token in
  the same context that will submit it; moving a token between HTTP clients fails with `110500`.
