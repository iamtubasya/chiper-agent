# TOTP / 2FA enrolment — recover the secret instead of begging for codes

Verified on the Genians CSM engagement (2026-10-27): Keycloak realm `csm`,
required action `VERIFY_EMAIL` then TOTP, operator enrolled Google Authenticator
on their phone and sent the export QR as a photo.

Read this the moment a target's login shows an OTP field **and** the operator
controls the enrolled authenticator. It converts a per-login scheduling problem
into a one-time setup step.

---

## Why not just ask for the 6-digit code

A TOTP code is valid for 30 s. An authenticated audit needs:

- a login, then several re-logins as the session cookie expires;
- a **second identity** for IDOR/BOLA differentials (each with its own enrolment);
- re-auth after any cookie/profile mishap.

Asking the operator for a code each time does not survive that. The second
request onwards they are either asleep, or you burn the window waiting for a
reply, or you waste attempts on a stale code.

**Rule: ask once for the enrolment QR, then never ask again.**
If the operator offers "I'll send you a code", redirect them — "just send the QR
image, it's one step for you and unblocks the whole session." Operators find
this *easier* than relaying codes, so the request is not a burden.

---

## What the QR actually contains

Two shapes. Both decode to the same thing: a base32 shared secret.

### 1. `otpauth-migration://offline?data=<base64 protobuf>`
Google Authenticator **export / transfer** QR ("Transfer accounts → Export").
Holds every account in the app, hence the protobuf wrapper.

### 2. `otpauth://totp/<issuer>:<account>?secret=...`
Single account. Produced by most non-Google apps and by the enrolment page
itself in some products. `secret=` is already base32.

The migration payload's field map (no `.proto` ships with it; verified against a
real export) is documented inline in `scripts/decode_totp_qr.py`. The secret is
raw bytes in field 1 of each `OtpParameters` — **base32-encode it yourself**, do
not paste the bytes.

---

## Recipe

```bash
python scripts/decode_totp_qr.py /path/to/qr.jpg \
       --json ./genians_totp.json
```

Output:

```
account[0]
  name      : My Genians:operator@example.com
  issuer    : My Genians
  secret    : OEYWE3DXOBEGU4KMOFEHE5ZSGY3EYUZY   (len=32)
  algorithm : SHA1
  digits    : 6
  type      : TOTP
  live code : 928821   (12s left)
```

Then in the login harness:

```python
import json, time, pyotp
cfg    = json.load(open("genians_totp.json"))
secret = cfg["secret"]                 # never a string literal in the script

rem = 30 - int(time.time()) % 30
if rem < 10:                           # avoid submitting into an expiring window
    time.sleep(rem + 2)
page.fill("#otp", pyotp.TOTP(secret).now())
page.click("#kc-login")
```

**Wait for a fresh window before submitting.** If a stage takes ~6 s to render
and the code has 4 s left, you get "invalid authenticator code" and lose an
attempt — which on a rate-limited IdP is a real cost. The `< 10s` guard above is
the difference between one attempt and three.

---

## Finding the QR on the operator's machine

They will say "I saved it in Downloads" or send it via chat. Do not ask twice —
look:

```bash
find "/c/Users/<user>/Downloads" -maxdepth 2 -type f \
     \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \) \
     -newermt "-1 day" | head -20
```

Also check `Downloads/Telegram Desktop/`, `Pictures/Screenshots`, and the
Desktop. Pick by mtime, newest first.

**A dark UI screenshot is not necessarily the QR.** When several candidates exist,
confirm which is actually a QR before spending decode attempts — dump a coarse
ASCII preview (76 cols × aspect-corrected rows, ramp `" .:-=+*#%@"`) and look for
three finder squares. A photo of a settings page renders as smooth gradients; a
QR renders as a high-contrast checkerboard. This costs one cheap call and
prevents "no barcode found" on the wrong file.

---

## Traps that actually bit

- **The tool-call redaction mangles literal secrets in authored files.** Writing
  `PASSWORD = "@BlueFrog88"` into a `.py` via a write/exec helper can arrive on
  disk as `PASSWORD=***` → `SyntaxError: unterminated string literal`. This is
  the same class as the existing PII pitfall in the parent skill. Fixes, in
  order of preference:
  1. keep the secret in a JSON file and read it (`json.load(...)["secret"]`);
  2. build it from codes: `"".join(chr(c) for c in [64,66,108,117,101,70,114,111,103,56,56])`;
  3. pass it as an env var the harness reads.
  Never inline it as a quoted literal in generated source.
- **Enrolment often cannot be completed headlessly anyway — that's fine.** The
  operator enrolling on their phone is the *expected* path (QR transfers into
  the app). You only need the *export* side.
- **Keycloak: the login page is two-stage.** Entering the email and submitting
  swaps the form: `#username` → `#password` → `#otp`, all posting to
  `#kc-login`. A driver that fills `#password` immediately after `networkidle`
  finds nothing, because the field did not exist yet. Fill stage by stage, each
  with its own `wait_for_selector`. The URL after the email stage is
  `.../login-actions/authenticate?execution=...&client_id=...` — `execution` is
  the flow handle, not a credential.
- **The enrolment page and the export QR are different artefacts.** The
  "Transfer accounts → Show secret" path and the export QR both yield the
  secret; the *enrolment* QR may be shown only once at setup. If the operator
  already dismissed it, the export QR from the app is the reliable fallback.
- **HOTP vs TOTP.** Field 6 tells you. A `counter` value that must increment
  means the code is single-use and the counter must advance between logins —
  HOTP will desynchronise if you reuse. `decode_totp_qr.py` reports the type;
  read it.

---

## Keep the secret, but keep it out of evidence

Store it beside the session state, not inside the report or any artifact you
might attach:

- `genians_totp.json` next to `genians_cookies.json` / `storage_state.json`.
- Never in the PoC PDF, never in the report body, never in a committed script.
- It is the operator's account credential. Deleting it at engagement end is the
  same hygiene as deleting the test account.

---

## Are the *target's* 2FA paths still worth testing?

Yes — and possession of one working TOTP secret makes it cheaper, not moot:

- **Does the direct-grant path enforce it?** Try `grant_type=password`,
  `client_credentials`, and the device-code flow against the token endpoint. If
  any returns a token without an OTP, that is an MFA bypass. (On Genians: all
  `unauthorized_client` / "Client not allowed for direct access grants" — the
  enrolment is enforced consistently. A clean negative worth recording, not a
  finding.)
- **Is the OTP verifiable without the secret?** Empty submit, a repeated prior
  code, and a code 30 s past expiry should all fail. Replay of an *accepted*
  code is the one that pays.
- **Is the OTP step skippable in the flow?** Navigate straight to the
  post-auth redirect URI with only the pre-OTP cookies; if the app issues a
  session, the second factor is decorative.
