# Authorized session recovery — getting an authenticated session for an engagement

Use when the engagement needs the operator's authenticated session and you do not have the password
in hand. **Only for the operator's own accounts, on an engagement with a verified authorization
artifact (security.txt / published policy / SOW).** Recovering credentials from the operator's own
machine for the operator's own account is the sanctioned path; doing it to anyone else is not.

Verified end-to-end 2026-10-08 on quarterwise.co.uk (VDP, safe harbour) — the operator said
"lanjut pakai akun pro saya".

## 0. Cheapest source first: the operator's own mailbox

If the app has an e-mail code / magic-link login, and you already have IMAP access to the
operator's mailbox (the engagement's mail helper, e.g. `~/check_basabasi_email.py`), read the code
straight out of the inbox. Values are read from the file on disk — the displayed `***` is only a
secret-tripwire in the transcript, not the file content. Never ask the operator to relay codes.

## 1. Inventory local browser profiles

Look for purpose-built profiles left by earlier engagements — they usually sit in the home dir with
an obvious name (`qw_chrome_cdp*`, `*-cdp`, `eng-*`). For each, check whether it holds a session for
the target:

```python
sqlite3 → <profile>/Default/Network/Cookies
  SELECT host_key, name, length(encrypted_value), expires_utc
  WHERE host_key LIKE '%<target>%'
```

A `qw_session`-style row (encrypted length ~120-130) means an authenticated cookie exists.

## 2. Probe each profile without mutating it

Copy the profile, delete `Default/Network/Cookies-journal`, `lockfile`, `SingletonLock`, then launch
a throwaway Chrome:

```
chrome.exe --user-data-dir="/home/agentuser/qw_probe_0" --remote-debugging-port=9340 \
           --remote-allow-origins=* --no-first-run --no-default-browser-check --headless=new
```

Navigate a page to `/app` (or the authed root) and read `document.body.innerText`. The plan badge /
"Upgrade to Pro" copy tells you which tenant you landed in. **Never launch a real profile directly** —
you will corrupt or lock it, and you may lose the only working session.

Launch Chrome from **Python `subprocess.Popen`** inside the probe script, not from bash with `&` —
background `&` in a `terminal` call is rejected, and Popen lets you `.terminate()` deterministically.

## 3. Get the cookie in cleartext over CDP websocket

There is **no HTTP `/<json>/evaluate` endpoint** on raw CDP (that shape is Camofox's REST API). Use
the websocket: read `<port>/json/list`, take the page target's `webSocketDebuggerUrl`, then
`Network.getAllCookies` / `Runtime.evaluate` over it. `websocket-client` and `websockets` are both
installed; a ~40-line helper (`cdp.py list|eval|goto`, honouring a `QW_CDP_PORT` env var) pays for
itself immediately. Note the built-in `browser_cdp` tool may be pointed at a *different* browser
instance and refuse with WinError 1225 — the raw websocket is the reliable path.

Keep the cleartext cookie for `requests`-driven testing: a captured `qw_session` plus curl/requests
gives you an authenticated leg without driving the UI for every probe.

## 4. Recover a saved password from Chrome's `Login Data`

Local State lives in the **profile root**, not `Default/`. Chrome 80+ uses AES-GCM with the prefix
`v10`:

```python
key = win32crypt.CryptUnprotectData(
        base64.b64decode(json.loads(LocalState)["os_crypt"]["encrypted_key"])[5:], ...)[1]
# v10/v11: nonce = blob[3:15]; ct = blob[15:]; AESGCM(key).decrypt(nonce, ct, None)
# older : win32crypt.CryptUnprotectData(blob)
```

`win32crypt` + `cryptography` are already installed. Query `logins` for `origin_url LIKE
'%<target>%'` and read `username_value` / decrypt `password_value`.

**Sanity note:** the same recipe applied to `Cookies` can appear to "decrypt" to binary garbage
while GCM auth still passes — if the value is not printable ASCII it is not the cookie the browser
sends. Do not chase it; take the cookie from the live browser via CDP (step 3) instead.

## 5. MFA

MFA code = `pyotp.TOTP(<secret>).now()`; fill the field with the React-safe setter (native value
descriptor + `input`/`change` events) and click the verify button. A stored secret per engagement is
worth recording next to the target's scope note.

## 6. Post-login hygiene

- A landing page like `/app/clients` with a client list = a firm/multi-client plan, i.e. the widest
  surface the account has. Confirm the plan on `/app/account`.
- Create the engagement's own API key from `/app/account/api` (TOTP-gated), store it under the
  workspace, and **revoke it at the end**.
- Cleanup that needs two clicks: `Remove` on an adviser fires an **in-page confirm dialog**, not a
  native JS dialog — click the row's `Remove`, then the `Confirm` button that appears. Clicking
  only `Remove` looks like it did nothing.

## Case study — quarterwise.co.uk v5 (2026-10-08)

- Five profiles (`qw_chrome_cdp`, `_b`, `_b2`, `_b3`) all held a **free throwaway** session
  (`qwab12042@uberip.com`). The Pro account lived in the operator's main Chrome `Profile 1`
  (`Login Data`): `Mr Fz` + a stored password.
- Login = e-mail + password, then `/login/mfa` (TOTP). Landing = `/app/clients`, plan **pro**.
- Result of the pass: no Medium+ finding. Every probed control enforced (BOLA -> 404, pre-MFA
  cookie cannot reach `/app`, e-mail payloads tag-stripped, ledger descriptions escaped, server
  actions reject foreign `Origin`, alert e-mail IP is the real Cloudflare value).
- Residue with **no UI delete path**: ledger entries written through `/api/v1` — register them in
  the report for the vendor rather than hunting for a delete button.
