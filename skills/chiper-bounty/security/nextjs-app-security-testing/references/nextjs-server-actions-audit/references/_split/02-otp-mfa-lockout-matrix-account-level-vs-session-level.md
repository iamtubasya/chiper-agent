## OTP / MFA lockout matrix (account-level vs session-level)

Attack: wrong OTP on login MFA and on recovery-code flows; then fresh login (session
rotation) to see if the counter resets.

- Record the attempt count where lockout fires (observed: 6 for OTP, 6 for recovery
  code, 11 for wrong password).
- If a FRESH login is immediately blocked (or "Too many attempts. Request a new code."
  persists on a new page load), the counter is **account-level** → session rotation won't
  beat it → brute-force resistant. Report as solid, don't keep hammering.
- Lockout cooldown can be minutes ("wait about 15 minutes", "wait about 6 minutes") —
  plan tests across accounts, and remember you may lock YOUR OWN account mid-session.

