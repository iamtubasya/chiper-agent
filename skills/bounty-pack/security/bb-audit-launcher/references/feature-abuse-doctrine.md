# Feature-Abuse Doctrine — operational checklist (operator, 2026-10-29)

Companion to `redteam-mindset` **Part 3**. Run this at Phase 0C before any vuln-class sweep,
and re-run it at 0E on every candidate before the report gate.

Core shift: **stop reading the app like its developer. Read it like someone who wants a state
the developer believed impossible.**

---

## Gate 1 — Feature as weapon (not vuln-class list)

For each feature in the product, fill this in the findings file *before* touching it:

```
FEATURE     : invite / export / reset / coupon / webhook / ...
INVARIANT   : what the feature is supposed to protect
TRUST       : what the dev assumes is checked elsewhere (UI, role, previous step, another service)
ABUSE       : the closest *legitimate* use that bends the invariant
TARGET STATE: the impossible state you want (member→owner, tenant A reads tenant B, trial→paid,
              quota exhausted but still usable, deleted object still alive, refund keeps entitlement)
```

### Abuse table — the highest-yield features

| Feature (works as designed) | Impossible state to chase |
|---|---|
| invite / referral / share link | self-invite into a privileged role; link still valid after role downgrade or removal; link re-usable after accept |
| email change / password reset / 2FA enroll | change email with no verification → reset → ATO; enroll attacker 2FA before victim's first login; reset token bound to email not user |
| export / import / bulk / CSV upload | export ignores tenant or field filters; import writes fields the UI never exposes (role, owner, tenant_id, verified) |
| draft → publish / moderation / version history | publish an unmoderated older revision; restore overwrites current state; moderation flag cleared by re-save |
| coupon / trial / proration / refund / credit | stacking, re-apply after cancel, refund without revoking entitlement, negative quantity, currency rounding |
| seat / limit / quota / rate | raise limit via downgrade→upgrade; invite that isn't counted; delete-then-recreate resets counter |
| soft-delete / restore / transfer ownership / merge account | restore an object after it moved tenant; merge absorbs another account's credentials or roles |
| support-view / impersonation / "login as" | obtain another user's session via the support path; impersonation token outlives the grant |
| webhook / API key / OAuth scope / device trust | webhook URL = outbound SSRF; old key valid after rotation; scope not enforced per endpoint |
| pagination / cursor / sort / filter / search | cursor carries server-side filter; search index returns objects the list API hides |
| upload avatar / document | SVG/HTML → XSS; path traversal in filename; file re-used across tenants |
| notification / email template / invite message | HTML/link injection into someone else's inbox |

**Hard rule: the UI is not a security control.** Disabled button, hidden field, "step you can't
skip" — send it anyway. That is the target.

---

## Gate 2 — Cross-feature matrix (bugs live in the interaction)

Build the matrix, then test the diagonals:

```
feature A × feature B    state created by A, changed/consumed by B
endpoint × role          low-role session calls the high-role endpoint via another path
object × tenant          identifier from tenant X used inside tenant Y's flow
state × state            pending+active, draft+published, deleted+restored, invited+existing
request × request        two parallel requests, different features, same object
```

Four mandatory triangles:

1. **Create in A, change in B** — created through the strict door, mutated through the loose one
   (or the reverse). Validation usually exists at exactly one door.
2. **Low role, high-role feature** — take the high-role action, call its endpoint with a low-role
   session, including "internal" endpoints only the admin UI calls.
3. **Cross-tenant identifier** — one ID/slug/cursor/filename/job-id/invoice-no replayed in another
   tenant's context. This is where BOLA/IDOR actually lives.
4. **Inter-feature race** — claim quota/coupon/seat/role through two different features in
   parallel; both read the old state and both commit.

### Killer combinations

`invite + role change` · `reset password + email change` · `share link + permission downgrade` ·
`draft/publish + moderation` · `coupon + refund` · `trial + plan change` · `soft-delete + restore` ·
`ownership transfer + pending invite` · `API key + scope` · `webhook + SSRF` · `export + filter` ·
`impersonation + session` · `2FA enroll + login` · `merge account + password reset`.

**Gate:** every candidate must be re-tested against **≥2 other features sharing the same object or
state**. A single point is a signal, not a finding.

---

## Gate 3 — Symptom → root cause → all twins

```
1. SYMPTOM : exact request/response + unique marker (not memory)
2. LOCATE  : find the handler — JS bundle / sourcemap / OpenAPI / source repo / binary
3. ROOT    : which guard/middleware/validator did NOT run, or ran in the wrong order?
             (validation missing, role checked client-side, tenant taken from body,
              write-before-validate, auth on read but not write, allow-list vs deny-list)
4. TWINS   : grep that root across the WHOLE estate — function name, decorator, middleware,
             model field, route pattern. List every endpoint that shares the root.
5. TEST    : run the same hypothesis on EVERY candidate, not a sample.
6. REPORT  : one root = one class = one report with N endpoint proofs.
```

Closed box? Infer the root from behaviour — **which parameter is ignored**, **which header changes
the outcome**, **which order matters** — then fire that hypothesis at every similar endpoint.

**Gate:** a report without a stated root cause plus its twin list is not mature.

---

## Gate 4 — State-diff, not status code

```
200 with no state change     → NOT a bug (echo / no-op / dry-run)
4xx-5xx WITH a state change  → serious bug (partial write, write-before-validate, TOCTOU)
403 leaking stack/path       → finding (info disclosure / path discovery)
```

Five layers of proof — check all, not just layer 1:

```
L1 RESPONSE   body, headers, timing, cookies that changed
L2 RE-READ    GET the object again — did state actually change?
L3 SIDE FX    new record, counter/quota, notification, email sent, webhook fired,
              audit-log entry, job queued, cache/search index updated
L4 OTHER      log in as user B / admin — what do THEY see now?
L5 DOWNSTREAM list/search/export/dashboard/report changed? downstream job ran?
```

After-request checklist (run in order, record results): re-GET object → list & search index →
counter/quota/seat → notification/email/webhook → audit log → other actor's view → idempotency
(send twice: does the effect double?) → rollback (cancel/delete: what state remains?).

**Gate:** an impact claim without an L2–L5 state diff is UNPROVEN. Evidence = a before/after pair
with a unique marker, never a status code.

---

## Gate 5 — Compose the Low pool (operator, 2026-10-29)

Standing rule: **chain multiple Low-severity findings into one higher-severity finding.** A single
Low stays Low because it supplies only ONE of the four parts a chain needs. Label every signal:

| Part | Supplies | Typical Lows |
|---|---|---|
| **K** Knowledge | identifier / version / schema you can't otherwise get | info-leak, verbose error, `.env`, introspection, bucket/dir listing, header leak, cursor leaking a server-side filter |
| **A** Action | the server does something on your behalf | CSRF (no impact alone), open redirect, HTML/email-template injection, benign mass-assignment, blind SSRF, webhook config |
| **B** Bypass | removes the check blocking the next hop | no rate limit, account enumeration, unthrottled OTP, CORS reflect on a cookie endpoint, host-header trust, `redirect_uri` wildcard, unverified email change, captcha bypass |
| **X** Amplifier | turns small into many, or into another actor's view | public-object IDOR (→ enumerate to private), share-link reuse, impersonation, export ignoring filters, vendor email/webhook relay, cross-tenant id |

Unlabelled signal = noise (missing headers, clickjacking with no target, `Server:` banner). Drop it.

### Composition procedure — run at 0E, before any report is written

```
1. INVENTORY  LOW_LEDGER.md: id | endpoint | observed | part | what it unlocks | verified?
2. LABEL      one primary part per row; unlabelled → drop
3. EDGES      for each pair: does A's output feed B's requirement?
4. SINK       name the terminal impact (ATO / cross-tenant data / fund movement / RCE / mass PII /
              privesc). No sink reachable → the pool is honestly negative; record the missing edge
5. PROVE      walk the composite end-to-end from a CLEAN session, 3x, one artifact per hop (Gate 4)
6. REPORT     ONE chain report. Title = terminal impact. Severity = terminal impact.
              Individual Lows become numbered steps, never separate submissions
```

Reliable patterns: `K+B+A+X` info-leak → unthrottled enumeration → unverified email change →
export amplification = mass ATO · `A+B` CSRF on a form whose only guard is a skippable captcha ·
`K+A` version leak → CVE on that version = RCE · `A+X` open redirect + share-link reuse = token
exfil · `B+X` no rate limit + enumeration + spray = credential stuffing ATO · `K+K+A` two leaks
that together reconstruct one secret.

### Hard rules

1. **Severity = terminal impact, never the sum.** Three Lows do not add up to Critical. If the chain
   reaches Medium, it is Medium. Inflation costs the program's trust in every later report.
2. **Every hop needs an artifact.** A "probably possible" hop makes the whole chain UNPROVEN — name
   it as the single unproven hop plus the credential that would settle it.
3. **One dead hop kills that chain, not the pool.** Re-route through another part; only then record
   the negative, quoting the server string that killed it.
4. **Do not ship the parts as filler while the composition is unfinished** — Low spam buries the
   High you were about to assemble.
5. **The composition must survive the vendor's rubric.** If the terminal class is N/A or out of
   scope (e.g. DeFi "no fund-loss path"), composition does not change that. Check eligibility first.
6. **Same-root Lows collapse into one finding** (Gate 3): five Lows sharing one missing guard = one
   root cause with five proofs, not five submissions.
