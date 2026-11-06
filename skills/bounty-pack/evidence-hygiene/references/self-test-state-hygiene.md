# Self-test state hygiene — mutating your OWN identity during an audit

Learnings from an engagement where testing a bug required changing our own account's display name,
then a password-reset probe locked us out of it for ~40 minutes.

## 1. Every mutation of your test identity gets logged at the moment it happens

Testing email/invite/RBAC surfaces frequently means you must *mutate* the account you are testing
with:

| Mutation | Why you'd do it | Cost if forgotten |
|---|---|---|
| Display name → payload (`<b>INJ2</b>`, `{{7*7}}`) | prove the value reaches an email/UI sink | account looks corrupted; payload re-fires into other people's inboxes |
| Role of a member → grant/deny | prove privilege delta | leaves an over-privileged test member in the org |
| Phone number / email | phone-reuse and enumeration tests | breaks SMS MFA path for the real owner |
| Password (via reset flow) | recovering from a self-lockout | **the old credential is dead** — anyone reading the old log entry wastes time |

Rule: write the change, the revert, and the *new* credential into the engagement log in the same
turn you make it. `ENGAGEMENT_LOG.md` next to the evidence is the right place — not a task tracker,
not memory. Revert before ending the session and note that the revert succeeded.

## 2. Clean up test identities, and say which one you kept

Delete throwaway members/invites with the same API the UI calls (e.g.
`DELETE /users/user {email}`), then list the resource again to prove the deletion. Keep at most the
one low-privileged identity the rest of the engagement still needs, and record its password, TOTP
secret, browser profile path and CDP port. A future session should not have to re-provision it.

## 3. Redaction is display-side — do not chase phantom corruption

After passing a phone number through a tool call, the echoed value can come back masked
(`+628****4807`) because output-layer secret/PII redaction rewrites the *display*, while the file on
disk and the value actually sent are intact. Verify against the artifact (read the file, re-read the
API response) before concluding "I corrupted the data" — chasing this cost real time and produced a
false alarm in the log that then had to be corrected.

Corollary: when a stored value *does* look wrong, check the wire format too — the app may mask the
field in its own responses (`+628****4807`) while the full value round-trips fine.

## 4. Distinguish "my probe broke the account" from "the creds changed"

A failed login after your own reset/invite/RBAC probing is usually *your* probe, not account
corruption. Order of investigation: (1) read the field value back — automation silently drops
characters; (2) check `localStorage.error_requests` / response bodies for the precise error code
(`…_ERROR_LOGIN` vs `…_CAPTCHA_VALIDATION_FAILED` vs `…_MAX_LOGIN_ATTEMPTS`); (3) only then consider a
credential change. Document the resolution, because the next session will hit the same sequence.
