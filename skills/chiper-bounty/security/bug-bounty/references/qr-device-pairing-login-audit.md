# QR / device-pairing login audit (banks, PSD2, any "scan to log in")

Any flow shaped `generate token → render QR → phone app confirms → desktop polls for status` is an
authentication primitive with its own bug classes: token guessability, cross-session polling oracle,
scope bypass, and confirm-without-bind. This is the checklist that produces a defensible verdict
either way — and the "all controls hold" verdict is a legitimate deliverable.

Worked case: an EU bank's Internet Banka. Endpoints were fully unauthenticated (no cookie needed):

```
POST /openapi/unsecured/cbl-idm/ib-login/generate-qr   {"scopeType":"IB"}
 -> 200 {"authenticationId":"<40 hex>-<sequential counter>",
         "qrCode":"<scheme>://open?ACTION=APPPAGE&URL=QRLOGIN&authenticationId=<same>"}
POST /openapi/unsecured/cbl-idm/ib-login/login/commit  {"authenticationId":"..."}
 -> 200 {"authorizationStatus":"WRONG_AUTHORIZATION"|"CONFIRMED"|"EXPIRED"|"REJECTED"}
```

## Tests, in order

**1. Entropy.** Split the token: `<hex part>-<numeric part>`. Count real entropy of the hex part
(40 hex = 160 bits ⇒ not brute-forceable) and note the numeric part is a **timestamp/counter**, not
secret material. Roughly `now - <n>` mapping to the current epoch reveals it is a monotonic counter —
useful to know, not a finding by itself.

**2. Derivation.** Try to reconstruct the hex part from everything the server already handed you, and
label the result either way:

```python
cands = {
 "sha1(counter)":            sha1(counter),
 "sha1(session cookie)":     sha1(sess_cookie),
 "sha1(decoded session uuid)": sha1(base64decode(sess_cookie)),   # many gateways b64 a uuid
 "sha1(uuid+counter)":       sha1(uuid+counter),
 "sha1(session+counter)":    sha1(sess+counter),
 "sha1(now)":                sha1(str(int(time.time()))),
}
```
All-miss = the token is server-random (a *control*, say so). Any hit = predictable session token,
immediate High.

**3. Cross-session polling oracle.** The highest-yield check. In two independent sessions:
A generates a QR, **B** polls A's `authenticationId`. Compare B's response to A's own poll.
- Identical (`WRONG_AUTHORIZATION` for both) ⇒ no oracle, no hijack primitive without app-side confirm.
- B gets a *richer* answer (user identity, `CONFIRMED`, partial profile) ⇒ session binding failure → report.

**4. Scope parameter tampering.** Send every plausible `scopeType`/`channel` value
(`IB`, `SB`, `PSD2`, `PAYMENT`, `CARD`, junk). An unwhitelisted enum that still issues a valid token is
**not** a finding unless the resulting token's authorization is observably different — verify by
comparing the poll outcome, and say so if not.

**5. Confirm-without-bind (needs the mobile app).** Does `login/commit` require the same device/session
that generated the token, and does the phone app sign the *pending transaction payload* rather than a
bare "confirm"? With a paired test device:
`{login A's QR on B's phone}` must fail, and `{approve A's payment from B's QR}` must fail. Without a
device this stays a **coverage gap**, stated as such.

**6. Post-auth session quality.** After CONFIRMED, check whether a *different* session ID is issued
(session fixation), and whether `login/commit` can be replayed against an already-used
`authenticationId` (replay/reuse). Both are testable with two throwaway polls, no account.

## Reporting frame

Two of the six (1,3) are fully provable without an account and are what a triager will accept as evidence
that you actually attacked the flow. Put them in the coverage ledger explicitly:
`QR token 160-bit, no derivation from session/counter/timestamp; cross-session poll returns the same
WRONG_AUTHORIZATION ⇒ no oracle`. Then name the one unlock needed for 5/6 (a paired test device).
