# QuarterWise VDP Audit Case Study (2026-09-26) — hardened target, verified-negatives

Full multi-day Next.js App Router SaaS (UK MTD tax software, explicit VDP + safe harbor,
scope = apex domain + signed-in app + API; subdomains/Stripe/Postmark/Cloudflare/HMRC out).
End result: **zero rewardable findings** — every boundary survived server-side. This file
records what was tested, the reusable verification tricks, and the false-positive that
nearly shipped. The class-level playbook lives in SKILL.md §9; this is the fleshed detail.

## What was attacked (the full matrix)

- **API** `/api/v1/*` (me, sources, categories, transactions): all 401 without key.
  `/api/account/export` ignores tampered accountId/userId/email — always returns own data.
- **IDOR/BOLA** across 3 accounts + server-action replay:
  - page-level: other-user property → "We can't find that page"
  - evil-origin replay → 500 digest error; transaction count unchanged (CSRF safe)
  - propertyId swap in own form → "That property could not be found."
  - owner settings action replayed with co-owner cookie → `{"error":"Only the owner can
    change these settings."}` (200-with-error = authz confirmed, NOT a vuln)
- **XSS**: 162-URL dalfox sweep (0); property-name stored (escaped in RSC payload); notes
  stored (`<img src=x onerror>` rendered as `&lt;img...&gt;` in a `<p>`, no DOM img,
  persisted-safe after reload); reset-page param reflection (flight-JSON escaped, not a sink).
- **CSV/XLSX formula injection**: `=SUM(A1:C1)` property name → export: stored in
  sharedStrings (`<si><t>`), NOT a `<f>` cell → inert. Display name `=2+2` in clients CSV
  → server prepends `'` → `'=2+2` → safe.
- **Import-path injection**: CSV with `=SUM`, `<img onerror>`, `@@cmd`, `{{7*7}}`, `${7*7}`
  parses into preview as plain text; never committed (free-plan gate); entries page +
  XLSX/CSV exports stayed clean.
- **Business logic**: sharePercent >100/-10/0 → server reverts to 100; over-allocation via
  replay (60 on top of 60) → `"That would take the property over 100% owned."`
- **Invite / role**: role radio tampered viewer→owner → server falls back to viewer;
  invite token bound to recipient email (different user sees "sign in with the invited
  address"); viewer→contributor write attempt blocked; co-owner→owner settings blocked.
- **Auth**: change email needs current password; change password needs current password +
  TOTP; NINO save needs valid TOTP (see reload-oracle below); login brute 500s = broken
  replay, account never locked (rate limit is per-IP/CF, not a lock-out finding).

## Reload-oracle example (NINO + MFA)

- Baseline: valid NINO + correct TOTP → field persists, `saved` marker.
- Test: valid NINO + wrong code `000000` → after fresh `Page.navigate` reload the field is
  EMPTY and the page re-shows the form → server rejected the wrong code. DOM-input value
  immediately after submit is optimistic UI; the reload is the truth. Cross-checked via
  `/api/account/export` (`clients[].nino = null`).

## TOTP self-enrollment (own account) — code that worked

```python
import base64, hmac, hashlib, struct, time
def totp(secret, period=30, digits=6):
    key = base64.b32decode(secret + '=' * ((8 - len(secret) % 8) % 8))
    counter = int(time.time() // period)
    h = hmac.new(key, struct.pack('>Q', counter), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    val = struct.unpack('>I', h[o:o+4])[0] & 0x7FFFFFFF
    return str(val % 10 ** digits).zfill(digits)
```
Pitfalls: base32 secret regex on the page `[A-Z2-7]{20,}`; the secret ROTATES on each page
render — generate the code in the SAME render you submit (do not navigate between read and
submit); enroll via the authenticator-app option (SMS option isn't scriptable).

## The false positive that nearly shipped (role-confound)

Acc2 was BOTH adviser-contributor AND 50% co-owner. As the combined role, acc2 deleted an
owner-added entry (£1,250.00) — looked like "contributor can delete owner entries" (P2).
Disambiguation: owner removed the co-owner share → as PURE contributor, `[aria-label=
Delete entry]` count dropped to 0 on owner entries, and after the contributor added their
own entry the delete button appeared only on that row (server conditionally renders per-row
actions). Lesson: co-owner grants legitimately include shared-book write in this product;
multi-grant test accounts must be reduced to the single role under test before claiming a
role-boundary violation. Per-row action-button rendering is itself the object-level authz
signal — document it as verified rather than filing it.

## Other hard-won details

- `Network.requestWillBeSent` `postData` is TRUNCATED; use `Network.getRequestPostData`
  with the requestId for the exact multipart body. Hand-built multipart server-action replay
  returns generic 500 for both valid and invalid bodies when the wire format is wrong
  (missing router-state-tree / wrong `_N_` prefix / stale `$ACTION_KEY`) — a single 500 is
  not a server signal; run the valid control first, else test via browser DOM.
- `browser_exec` harness can time out on heavy app pages; a raw `websocket` CDP driver with
  `Network.enable` + `Runtime.evaluate` is more reliable for authenticated flows. Chrome
  must be started with `--remote-allow-origins=*` for off-harness websocket control; kill
  stale chrome holding the debug port with PowerShell `Stop-Process -Force` (taskkill //F
  fails under MSYS).
- Adviser flows: inviting any adviser requires a current TOTP code; role changes too. This
  is deliberate MFA anti-session-hijack — not a bug.
- Hardened-target reporting: the deliverable is the verified-negative matrix (each surface,
  each request, each control result) — never a blanket "no bugs found".