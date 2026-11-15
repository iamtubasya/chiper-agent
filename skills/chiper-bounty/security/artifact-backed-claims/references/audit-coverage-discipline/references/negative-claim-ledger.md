# The negative-claim ledger — worked example

Source: Moneta (2026-10-28) and Deeper Network (2026-10-28). Both are cases where "nothing
reportable" was written before the coverage justified it, and what the corrected pass produced.

---

## Case A — Moneta `ib.moneta.cz`: the 5-of-18 failure

### What was claimed
"All unauth endpoints hold. Nothing payable." (written twice, in two rounds)

### What the ledger should have shown

| Column | Content |
|---|---|
| TESTED | 5 of the 18 unsecured paths extracted from the SPA bundle |
| BLOCKED | authenticated namespace (~360 endpoints) behind PowerAuth; programme provides no test account, KYC/BankID gated |
| **SHORTCUT** | **13 paths never probed. 392 service×method JSONWS combinations never tried. A surface I named myself (`/documents/`) never touched.** |

The third column was non-empty. The conclusion was unsupported.

### The corrected pass — what the remaining 13 paths yielded

Re-running all 18 with the correct request contract (recovered from the bundle, not guessed):

```
/openapi/unsecured/publicregistry/company/search   {companyNamePart, maxResultCount}  -> 10 results
/openapi/unsecured/publicregistry/address/search   {streetAndNumber, editedField, recordCountLimit} -> 9
/openapi/unsecured/ib/payment/payu/check-url       -> payu.decryptionError (uniform, fail-closed)
/openapi/unsecured/cbl-idm/ib-login/generate-qr    -> authenticationId + qrCode
/openapi/unsecured/cbl-idm/ib-login/login/commit   -> NOTCONFIRMED / WRONG_AUTHORIZATION
/openapi/session/ib/password/change-and-send       -> 401 POWER_AUTH_SIGNATURE_INVALID
/openapi/fraud/panic-button/clear-cache            -> 400 No static resource (absent here)
```

Result: still nothing payable — **but now a defensible negative**, because the coverage is complete
and each dead end carries the control that killed it.

### The two oracle hypotheses that the extra coverage produced and then killed

Both are worth recording because both looked like findings:

**1. `/session/nib/login-by-token/{token}` — 200 with a backend error while siblings 404.**
Seven tokens (short / numeric / nil-UUID / 32-hex / "admin") all returned an identical
`cbl.access.denied.exception`. A sibling path `login-by-tokenXXX` returned `400 No static resource`,
which proved the real route exists and the uniform denial is the *token* check, not the route.
No oracle. Dead.

**2. PayU `check-url` — unauthenticated `payu.decryptionError`.** Classic padding-oracle shape.
Seven payload shapes (empty, 32-hex, nested, base64, 256-byte) produced an identical error with no
length or timing divergence. Fail-closed uniformly. No oracle. Dead.

### Reusable technique that made the extra coverage cheap
The SPA marks its own unauthenticated calls:

```python
re.findall(r'hD\)\(?\s*["\'`](/[^"\'`]{2,90})["\'`]\s*\)([^;]{0,260}?)unsecured\(\)', js, re.S)
```

28 call sites → 18 unique paths, with zero guessing. This is what turned "5 probed" into "18/18
probed" in a single pass. Look for the app's own auth marker before writing any wordlist.

---

## Case B — Deeper Network web surface: the false-positive that survived one round

### The signal
`POST /auth/pin/request {email}` returned **204** for an unregistered address but **429** for the
researcher's own address. Textbook user-enumeration oracle shape.

### The control that killed it
Send the same 10 requests to **one** never-registered address:

```
control: 10x SAME ghost email -> {204: 1, 429: 9}
```

Identical behaviour. The limiter counts **requests per email**, not account existence. Ten
*distinct* ghost addresses produced 10× `204` and never a 429 — the expected shape of a per-key
counter.

**Lesson:** a differential only counts when a control with a *known* answer fails to reproduce it.
This is the same reflex as the control-address rule for RPC sweeps, applied to auth oracles.

---

## The ledger template to copy

```markdown
## Coverage ledger — <host or class>

### Tested (artefact on disk)
- <path/class> — <probe> → <result>, evidence: <file>

### Not tested — blocked
- <path/class> — blocked by: <specific gate>

### Not tested — my own shortcut
- (must be empty)
```

If the last section is non-empty, close this file and go run it. Then come back.
