## Two-factor / TOTP surface — the full matrix worth running

Once you enrol an authenticator app on your own test account (self-enrol from
`/app/account/security` style pages; keep the base32 secret in a helper module so you can
generate codes on demand — do NOT hardcode the secret or a tool wrapper may mangle it),
run all of these. On Quarterwise every one held; the *method* is what's reusable:

1. **Half-authenticated session.** After the password step but before the code, hit
   `/app`, `/app/account` → expect 307 to login. One route usually answers 200 with the
   marketing/SPA-404 shell instead of redirecting — that is the catch-all, not access;
   confirm by checking the body, not the status.
2. **Server-side enforcement on sensitive actions, not just login.** Wrong code on
   "turn off 2FA" and on "save NINO/SSN" must be refused with the control still on. This is
   the highest-value check: many apps validate TOTP only at login and treat the code field
   on later forms as decoration.
3. **Attempt cap + whether it is account-level.** Submit wrong codes until lockout
   (observed: 5 → "Too many attempts. Please wait about 15 minutes"). Then a FRESH login
   with the CORRECT code must also be refused → account-level counter. **Then verify it
   expires** by logging in ~15 min later: "resistant to brute force" and "permanently
   locked out" are different findings.
4. **Replay — one code, two logins.** Wait for the start of a 30s window so both logins fit,
   complete login #1 with the code, then start a second login and submit the SAME code
   (assert `current_code() == code` so you know the window did not roll). Accepted on #2 =
   replayable. Quarterwise: #1 in, #2 "That code is not correct" → replay prevented.
5. **Recovery flow.** `Forgot MFA?` → read the stated design before pressing anything. A
   24-hour delay plus a warning email is a *control*; an instant code-only reset is a bypass.
   Do not start a 24h disable timer on an account you do not own — report the copy as read.
6. **What MFA does NOT cover.** Credentials that bypass it (API keys, personal access
   tokens, machine users) keep working while the account is MFA-locked. Verified: during
   lockout `/api/v1/me` still returned 200 with the API key. Not a bug — but say it plainly
   so "2FA is on" is not oversold, and note that MFA protects interactive login only.

**Pitfall that produced a false conclusion.** The first replay test reused a code for a
"save NINO" action with a different value and concluded "replay prevented" — the real
rejection was the *NINO validator* (check suffix must be A–D; `AB123456E` is invalid). When
an action "fails" during an MFA test, read the raw server error (for RSC:
`page.on("response")` → the `1:{"error":"..."}` flight segment) before attributing it to
MFA. And always validate your test *value* with a fresh code first — that is the control
that separates "code rejected" from "value rejected".


