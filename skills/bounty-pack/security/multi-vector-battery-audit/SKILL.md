---
name: multi-vector-battery-audit
description: Run a 100+ vector adversarial battery per vulnerability class (RCE, ATO, data leak) against a codebase-backed target, with strict false-positive discipline. Use when asked for exhaustive coverage or deep-dive per class, and when you must distinguish real findings from test artifacts.
category: security
---

# Multi-Vector Battery Audit

Exhaustive per-class probing with **honest triage**. The value is not the vector list (anyone can write 100 curl commands) — it is the discipline that keeps a flaky artifact out of the report.

## When to use
- Operator says "deep dive", "minimum N vectors per class", "exhaustive coverage"
- Target has source available (GitHub repo, self-hostable) so you can stand up a local instance
- You need to prove a **negative** credibly (SSRF absent, no data leak) rather than assert it

## Core discipline (the part that matters)

### 1. Flaky ≠ finding
A race or timing result that appears 1 of 3 runs is **not** a vulnerability. Validate every race 3× with fresh state. If it does not reproduce all 3, discard it and say so explicitly.

```
bad:  "refresh rotation race: 4 tokens issued"        <- one lucky run
good: "refresh rotation race: 4 tokens in 1 run, 1 token in 3 validation runs -> NOT reproducible, not reported"
```

### 2. Delta vs spread for timing oracles
Never claim a timing oracle from a median difference alone. Compare the delta against the measured range/spread.

```
existing 796.9ms (spread 2825) vs ghost 1192.3ms (spread 4739)
delta 395ms  <<<  spread 4739ms  -> distributions overlap, NOT an oracle
```

### 3. Your own test harness lies — verify the flag before reporting
Several "findings" turn out to be bugs in the probe script, not the target. Before escalating any flagged vector, re-read the assertion and confirm the setup was actually the attack scenario.

Real examples from use:
- `/auth/me IDOR` flagged because the test passed `?user_id=` — but the endpoint ignored the param entirely and returned own account. Not a bug.
- `device lock NOT BLOCKED` flagged because the account was never bound before testing a second PC. Setup bug.
- `CSRF accepted` flagged because the request carried a `Bearer` header in the same call, so it was never a browser-CSRF scenario.
- `email 2FA enabled without TOTP` — actually correct behaviour when no TOTP is enrolled.

### 4. Mutation testing reads are static analysis, not proof
Regex-scanning source for `subprocess`/`eval`/`exec` finds *primitives*, not *reachable sinks*. Label those results as "surface found", never as "RCE".

### 5. Report the negative with the same rigor as the positive
A negative is only credible with the payload list and the observed rejection. "No SSRF" is worthless; "24 payloads, all rejected with the exact error" is evidence.

## Workflow

### Phase 0 — get a runnable instance
```bash
git clone --depth 1 <repo> && cd <repo>
python -c "import fastapi, sqlalchemy, argon2, jwt, cryptography"  # check what's missing
pip install -q <only-missing-packages>          # don't rebuild a full venv, it times out
```
Prefer the project's own test client (`fastapi.testclient.TestClient`) — no port, no network, deterministic, and it exercises the real route stack.

### Phase 1 — map sinks first
```bash
grep -rn "urlopen\|requests\.\|httpx\.\|subprocess\|os\.system\|eval(\|exec(\|pickle\|yaml\.load" <src>
```
For each outbound sink record: **is the host fixed? is the user-controlled part validated?** That decides whether SSRF is even reachable before you write 24 payloads.

### Phase 2 — wave structure
Run in waves so a slow class does not block the others, and so you can amend the list after seeing wave-1 results:

| Wave | Purpose |
|---|---|
| 1 | ~50 vectors, breadth, all obvious classes |
| 2 | ~45 vectors, depth on whatever wave 1 flagged + second-order paths |
| validation | 3× on every positive, fresh state each run |
| top-up | push each class past the required count |

### Phase 3 — the vector taxonomy

**RCE / injection (~100)**
- Archive extraction: zip-slip (absolute unix/windows, drive-relative `C:x`, UNC `\\host\share`, `..`, nested `..`, backslash `..\..`, NTFS ADS `f.txt:hidden`, trailing dot/space, device names `CON`/`NUL`/`AUX`, 8.3 `EVIL~1`, NUL byte, unicode `∕` U+2215, fullwidth `．` U+FF0E, double-encode `%2f`, 40-deep traversal, case-varied `STREAMS/`), symlink entries, duplicate entries, empty/corrupt zip, zip bomb ratio, entry-count flood, preserve-dir bypass
- Exec boundary: launch target outside allowed dir, interpreter override via argv, env var passthrough
- SQLi/NoSQL: `' OR '1'='1`, `'; DROP TABLE--`, UNION, time-based `SLEEP`/`WAITFOR`, `$gt`/`$ne`/`$where`
- Template: `{{7*7}}`, `${7*7}`, `<%= 7*7 %>`
- Header/log injection: CRLF in UA/XFF, ANSI escapes
- JWT: alg none/HS384/HS512/RS256 confusion, `kid` traversal+sqli, `jku`/`x5u` remote keys, `crit`, duplicate JSON keys
- Client sinks: subprocess/eval/exec/pickle/yaml, URL passed to a media player without option sanitisation

**ATO (~100)**
- Email normalisation: case, plus-address, dots, whitespace, trailing dot, unicode homoglyph
- Lockout: brute 5×, then try case-variant / XFF-rotated to bypass
- Device/HWID: bind then second PC, body vs header precedence, regex boundaries (31/32/33/64/65 chars), refresh from other device, bind race
- Refresh tokens: reuse after rotation, rotation race, access-as-refresh, refresh-as-access, expired, logout-all invalidation, cross-user logout
- 2FA: TOTP replay, drift windows (+/-1, +/-5 steps), setup overwrite, re-setup when enabled, expired challenge, attempt cap, resend cap, method precedence, enable/disable email-2FA without code
- Reset: code reuse, cross-user code, attempt-limit race, CSRF without Origin, Host poisoning, old password death, session kill on reset
- IDOR/authz: `?user_id=`, mass assignment, cross-user preferences
- Enumeration: login, register, forgot, unsubscribe — compare **byte-identical** bodies
- Inactive user: login, refresh, existing access token
- Challenge tokens: entropy, forge, cross-device use

**Data leak (~100)**
- Endpoint sweep: `/docs`, `/redoc`, `/openapi.json`, `/actuator`, `/actuator/env`, `/swagger`, `/graphiql`, `/.env`, `/auth.db`, `/.git/HEAD`, `/.svn/entries`, `/backup.db`, `/server/.env`, `/metrics`, `/debug`, `/console`, `/shell`, `/.well-known/security.txt`, `/package.json`, `/requirements.txt`
- Response headers: `Server`, `X-Powered-By`, HSTS, nosniff, frame-options, CSP, referrer-policy, cache-control
- Field whitelist on identity endpoints: password hash, TOTP secret, HWID hash, token_version, otp hashes
- Error handling: malformed JSON, type confusion (bool/int/list/dict/float), oversized body, wrong content-type → check for traceback/sqlalchemy/site-packages
- Timing: login, verify-code, refresh (apply delta-vs-spread rule)
- Token hygiene: reset link entropy, cookie flags (httponly/secure/samesite/scope), referrer-policy on token pages, cache-control
- Storage at rest: hash algorithm, encrypted blobs, UUID vs sequential IDs
- CORS, XFH poisoning, cache-key variance, 404 uniformity, 405 Allow header

## Execution notes (Windows / MSYS host)

- **Never build scripts with a heredoc** — the parser rejects long heredocs. Write via `execute_code` + `open(path,'w')` to an **absolute** `C:\...` path.
- `execute_code` and `terminal` have **different cwd**. Write with an absolute Windows path, run with the MSYS path (`/tmp/X`).
- Long batteries exceed the 60s foreground limit → `terminal(background=True, notify_on_complete=True)` then poll the output file.
- Argon2 at ~250ms/hash makes seeding 1000 users take 4 minutes. For amplification proofs, **seed the DB directly** with the app's own models and `hash_verify_code()`, then hammer the real endpoint. Same validity, 20× faster.
- Passwords containing the email local-part get rejected by most policies — use `Zx9!qwErTy-Uiop`.
- Print results as a table at the end (`tested: N   flagged: M`) so the coverage claim is auditable.

## Deliverable template

```
CLASS       : <name>
VECTORS     : N
FINDINGS    : M reproducible
NEGATIVE    : <what was tested, with the rejection evidence>
FLAKY       : <what appeared once, and why it was discarded>
HARDENING   : <real observations below the reporting bar>
```

Report findings separately from hardening notes. A 500 on a race is hardening; a brute-forceable verification code is a finding.

## Pitfalls

- Do not count a vector twice across waves; keep an explicit tally.
- Do not escalate a flag before re-reading your own assertion (see discipline #3).
- Do not claim "no findings" without the printed vector count and the rejection evidence for each class.
- If a wave script throws, the traceback is not a target bug — read it as your own harness defect before rewriting.
