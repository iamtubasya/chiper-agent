# Registration / verification ATO — checklist + runtime harness

Companion to Path 10 (pre-account takeover) and Path 11 (optional identifier on a verification
endpoint). Validated 2026-10-30 against DedSec CCTV (open-source FastAPI auth server, v1.0.3);
two reports filed — `GHSA-v5pf-gxfc-7cq3` (registration pre-hijack) and
`GHSA-2223-mv52-4wvq` (verify-code branch).

## 1. Source-read checklist (do this before touching the app)

Grep the registration and verification handlers, then answer in writing:

| # | Question | Why it decides the finding |
|---|---|---|
| 1 | Does the 2nd registration of an **unverified** email update `password_hash`? | If not → pre-hijack primitive |
| 2 | Does the 2nd registration of a **verified** email leave the password alone? | If it *does* update → different, worse bug (silent override) |
| 3 | Is the identifier field on the verify endpoint `Optional`/nullable/defaulted? | An optional identifier = an untested branch |
| 4 | On that branch: per-account rate limit? attempt counter? token scoping? | Any one missing weakens it; all three missing = exploitable |
| 5 | Does the login handler increment the failure counter on a **correct** password? | If not → polling oracle, no lockout |
| 6 | Does password reset clear `totp_enabled` / device binding? | Decides whether lockout is permanent or cosmetic |
| 7 | Is there a TOTP-disable endpoint at all? | No disable = victim cannot self-recover |

## 2. Runtime harness (source-available targets)

Run the app locally and exercise the **real endpoints**. Do not reimplement the logic — that only
proves your reimplementation.

```python
import os, sys, secrets, base64, tempfile
_tmp = tempfile.mkdtemp()
os.environ.update({
    "ENVIRONMENT": "test",                       # bypasses production CHANGE_ME refusal
    "DATABASE_URL": f"sqlite:///{_tmp}/run.db",  # isolated per run — critical for repeatability
    "JWT_SECRET": secrets.token_urlsafe(64),
    "TOTP_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    "EMAIL_BACKEND": "memory",                   # codes readable in-process, no SMTP
    "RATE_LIMIT_IP_PER_MINUTE": "100000",        # keep the demo off the limiter
    "RATE_LIMIT_ACCOUNT_PER_15MIN": "100000",
})
sys.path.insert(0, os.path.abspath("."))
from fastapi.testclient import TestClient
from app.main import app
from app.emailer import get_sender

outbox = get_sender()          # MemorySender: .outbox = [(to, subject, body), ...]
```

Reading a code out of the in-memory outbox:

```python
import re
def code_for(email, word=None):
    msgs = [m for m in outbox.outbox
            if m[0] == email and (word is None or word in m[1].lower())]
    return re.search(r"Your code: (\d{6})", msgs[-1][2]).group(1)
```

### Seeding large N without paying the password-hash cost

Argon2 at OWASP parameters costs ~250 ms/hash. Registering 1000 users through `/auth/register`
therefore takes ~4 minutes and makes amplification experiments unfinishable. Seed the DB directly,
using the app's **own models and its own hash helpers**, then drive the real endpoint:

```python
from app.db import SessionLocal, init_db
from app.models import User, EmailVerificationToken
from app.security import hash_verify_code, utcnow
import datetime, uuid

init_db()
with SessionLocal() as db:
    for i in range(3000):
        uid = str(uuid.uuid4())
        db.add(User(id=uid, email=f"seed{i:05d}@example.com",
                    password_hash=DUMMY_ARGON2_STRING, email_verified=False, is_active=True))
        db.flush()
        db.add(EmailVerificationToken(user_id=uid,
                                      token_hash=hash_verify_code(uid, f"{i:06d}"),
                                      attempts=0,
                                      expires_at=utcnow() + datetime.timedelta(hours=24)))
    db.commit()
```

3000 rows seed in ~21 s versus ~12 min through the HTTP path. The endpoint under test is untouched,
which is the point — only account *creation* is short-circuited.

### Two-pass rule for the amplification claim

Measuring hit rate at N=1000 with blind guesses is a binomial coin flip — one run proves nothing.
Report the **rate**, not a lucky hit:

```
P(hit per guess) = N / 1_000_000          # one guess tested against all pending rows
expected hits    = guesses * P
```

State the ceiling honestly: with a 300/h global cap that is ~7,200 guesses/day, so ~0.7 %/day
against a single target and ~7 accounts/day at N=1000. A targeted single account is **not**
practical; the mass case is. Writing "brute-forceable" without the number invites a downgrade.

## 3. The poll loop (no race required)

The pre-hijack chain looks like it needs timing. It does not, because of how login handles a
*correct* password on an unverified account:

```
attacker registers victim@x with attacker password   -> 202
poll: login(victim@x, attacker_pw)   x6             -> 403 "Email address not verified."
victim registers normally + verifies                 -> (their own ordinary action)
poll: login(victim@x, attacker_pw)                  -> 200 + access_token + refresh_token
```

`_register_failure()` is only called on a **wrong** password, and a correct password *resets*
`failed_login_count`. So polling with the attacker's own (correct) password never trips lockout —
only the per-account rate limit, which a slow poll sits under.

## 4. Proving permanent lockout (don't infer it)

Enabling TOTP only strands the victim if reset does not clear 2FA. Prove it end to end and read the
DB afterwards, rather than inferring from a `200 "Password changed"` page.

```
[1] attacker enables TOTP on the victim account
[2] victim runs the FULL reset: forgot -> code -> link -> new password -> 200 "Password changed"
[3] victim logs in with the NEW password -> 200 status=totp_required
[4] DB after reset: totp_enabled=True, totp_secret_enc set, token_version bumped
```

Result: reset rotated the password and killed sessions but left the second factor. Combined with
"no TOTP-disable endpoint", the victim has no self-service path. That is the sentence worth writing.

## 5. Severity honesty — this class is High, not Critical

Both findings above shipped as **high**, deliberately:

- Verified accounts are untouched — the `else` branch handles them safely.
- The victim can register with a **different email address**; nothing bans it. It is identity
  *squatting*, not takeover of an existing account.
- For the verify-code path, a single targeted account is ~0.7 %/day; only mass squatting scales.

What makes the verify-code path the stronger report is not the rate — it is that it needs **zero
victim action** (the attacker verifies the account themselves), whereas the pre-hijack needs the
victim to complete their own signup.

## 6. Fix to lead with

Make the identifier mandatory; the legacy branch disappears:

```python
class VerifyEmailIn(_Strict):
    token: str = Field(min_length=6, max_length=200)
    email: EmailStr          # required, not Optional
```

For the registration side: in the `elif not existing.email_verified:` branch, also set
`existing.password_hash = pw_hash` — the "overwrite" worry only applies to verified accounts.
