## Second-factor (MFA) surface — the matrix that mostly finds controls

When the account has 2FA (or you just enabled it to reach a gated area), test it as its own
class. On Quarterwise the whole matrix came back as working controls — expect that, and say so:

| Test | How | Expected/observed |
|---|---|---|
| Half-auth session | finish the password step, then `goto` `/app`, `/app/account` | 307 → `/login` (app pages unreachable). A route that returns 200 with the marketing/404 SPA shell is NOT a bypass — read the body |
| Sensitive-action enforcement | submit the 2FA-guarded action (`save NINO`, `turn off authenticator`) with `000000` | refused, state unchanged → the check is server-side, not just UI |
| Attempt cap | submit wrong codes until it breaks | observed: 5th attempt → "Too many attempts. Please wait about 15 minutes" |
| Counter scope | after lockout, fresh login + CORRECT code | still refused → **account-level**, so TOTP brute force is impractical |
| Replay | use one code for login, then reuse the SAME code for a sensitive action | rejected — but to prove it, change the target VALUE too, otherwise "rejected" is indistinguishable from "no change" |
| Recovery | follow "Forgot MFA?" | observed: disable 2FA after a 24h delay + email notice you can act on. Verify the copy; do NOT trigger it on a vendor account (starts a real 24h timer) |
| API keys | call `/api/v1/me` while the account is MFA-locked | still 200 → **MFA protects interactive login only; an API key grants read/write with no TOTP.** Not a bug, but report it as a threat-model clarification |

Locking yourself out is part of the test: after the attempt-cap run, the saved session is
half-authenticated and unusable until the window closes. Kick off a background timer and
finish verification when it fires — do not keep retrying, each attempt can extend the window.

