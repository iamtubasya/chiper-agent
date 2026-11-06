# Laravel Livewire Auth-Flow Testing (magic-link / QR components)

Livewire 3 apps expose their auth state machines as components on the login page. When the
primary door (QR, OAuth, password) is walled, enumerate ALL components on the page — a
magic-link component is a second door that often needs only an email.

## Step 1 — enumerate components from the login page HTML
```python
import re, html, json
c = requests.get(TARGET + "/login", headers=UA).text
snaps = re.findall(r'wire:snapshot="([^"]+)"', c)
for sn in snaps:
    d = json.loads(html.unescape(sn))
    print(d["memo"]["name"], d["memo"]["id"], list(d["data"].keys()))
```
Component `data` keys reveal the auth machine (e.g. `{email, sent, error}` = magic-link;
`{sid, qrCode, qrCodeImage}` = QR login). Actions are in `wire:click`/`wire:keydown.enter.prevent`
attributes (e.g. `sendMagicLink`).

## Step 2 — drive the component IN THE BROWSER (not scripted)
Scripted `/livewire/update` replay with the page's initial snapshot fails (404/419) because
Livewire validates the snapshot checksum against live component state. The browser handles
CSRF + snapshot mutation automatically:
- Playwright: `pg.query_selector("input[placeholder='name@example.com']")` → `.click()` →
  `pg.keyboard.type(email, delay=50)` (real keystrokes — `fill()` does NOT always sync wire:model)
  → `inp.press("Enter")` or click the `wire:click` button.
- Capture the response: listen for POSTs to `/livewire/update` whose post_data contains the
  component name; the JSON response contains the NEW snapshot — read `data.sent` / `data.error`
  for the server verdict (this doubles as a user-enumeration oracle if errors differ).

## Step 3 — read the Livewire wire format (for reference / later scripted use)
```
POST /livewire/update
{"_token": "<plain csrf-token from meta tag>",
 "components":[{"snapshot":"<raw wire:snapshot string, HTML-escaped>",
                "updates":{"email":"..."},
                "calls":[{"path":"","method":"sendMagicLink","params":[]}]}]}
```
X-CSRF-TOKEN must carry the PLAIN token (meta tag); X-XSRF-TOKEN carries the encrypted cookie.
A stale snapshot → 404 "Not Found" (Livewire checksum mismatch), not a 419.

## What to test once a session exists
- **Rate limiting**: magic-link sends are typically per-email throttled (observed: "Too many
  requests. Please try again in 57 minutes") — proper defense; note the cooldown before re-testing.
- **Link entropy + single-use + expiry**: links are the bearer token; check reuse and TTL.
- **Post-login session handling**: does the app call `session()->regenerate()` after
  `Auth::login()`? The byteauth-laravel package does NOT (session-fixation shaped, needs a
  cookie-planting vector for impact — usually P4 max, verify the deployed app, not the package).
- **Authenticated surface**: IDOR/BOLA on user-scoped endpoints, business logic on money moves.

## Email-side dependency
Magic links land in the mailbox — Gmail API token (hermes/google_token.json) must be live or
the flow stalls. Google OAuth apps in "testing" publishing status have refresh tokens that
expire after 7 days (invalid_grant) — re-auth proactively at engagement start when any
email-delivered credential (magic link, OTP, verification mail) is in scope.
