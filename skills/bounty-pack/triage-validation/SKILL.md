---
name: triage-validation
description: Finding validation before writing any report — 7-Question Gate (all 7 questions), 5 pre-submission gates incl. program-policy compliance (CVSS version currency, required report fields, reporting deadline, strike rules, CNAME scope check), always-rejected list, conditionally valid with chain table, CVSS 3.1 quick reference, severity decision guide, report title formula, 60-second pre-submit checklist. Use BEFORE writing any report. One wrong answer = kill the finding and move on. Saves N/A ratio.
sources: community, operator_experience
---

# TRIAGE & VALIDATION

> **⚙️ MECHANICALLY ENFORCED (2026-10).** The 7-Question Gate below is no longer advisory: the
> orchestrator runs `triage_gate.py` between 0E and 0F and **blocks** any finding that does not answer
> YES to all 7. Its output is `triage.json` + `passed-findings.json`; the report is fed **only** from
> `passed-findings.json`, and 0 PASS ⇒ an explicit NEGATIVE report (never a fake "no findings" shell).
> The regex gate encodes these questions; if it mis-judges a real finding, the `triage.json` per-question
> answers are the audit trail to correct it.

One wrong answer = STOP **this finding**. Kill **the finding**. Move on **to the next test class**.

> **Scope of "STOP" in this skill:** This skill's gates kill INDIVIDUAL FINDINGS that fail validation. They do NOT authorize stopping the engagement. Killing a finding via the 7-Question Gate just means *that finding* doesn't get submitted — every other test class in the engagement is still pending. See `redteam-mindset` "DO NOT STOP primary directive" for the coverage-axis rule.

> "N/A hurts your validity ratio. Informative is neutral. Only submit what passes all 7 questions."

---

## THE 7-QUESTION GATE

> **Per-class proof bar runs BEFORE this gate.** Before answering the 7
> questions, load the claimed class from **`report-gotchas`**
> (`references/class-gotchas.md`) and check the PoC against that class's
> *minimum proof*. A candidate that fails the class bar never reaches the
> gate — it is not a finding yet. `report-gotchas` is additive: it owns the
> per-class proof bar + the AI-slop detector; this skill still owns the
> decision (7 questions, NEVER SUBMIT list, chain table, CVSS).

Ask IN ORDER. One wrong answer = STOP immediately.

---

### Q1: Can an attacker use this RIGHT NOW, step by step?

Complete this template:
```
1. Setup:   I need [own account / another user's ID / no account]
2. Request: [exact HTTP method, URL, headers, body — copy-paste ready]
3. Result:  I can [read / modify / delete] [exact data shown in response]
4. Impact:  The real-world consequence is [account takeover / PII read / money stolen]
5. Cost:    Time: [X minutes], Capital: [$0 / $X subscription required]
```

**If you CANNOT write step 2 as a real HTTP request → KILL IT.**

---

### Q2: Is the impact on the program's accepted impact list?

Go to the program page. Find "Vulnerability Types" or "Out of Scope."

Common tiers:
- **Critical**: Any-user ATO without interaction, RCE, SQLi with data exfil, admin auth bypass
- **High**: Mass PII exfil, privilege escalation, internal SSRF with data, stored XSS all users
- **Medium**: IDOR on specific user non-critical data, XSS on sensitive page requiring click
- **Low**: Non-sensitive info disclosure, clickjacking with PoC

**If your bug maps to a listed exclusion → KILL IT.**

Secret/API-key-in-bundle reports deserve their own clause check here: the common program exclusion
"reports of secrets, API keys, or credentials publicly available without proof of active
exploitation" kills the finding unless liveness/use is demonstrated. Test the credential against its
vendor API first (read-only); vendor CI keys often point at third-party SaaS whose API may have
moved (NX_API_KEY → api.nx.app no longer resolves), in which case the proof is impossible and the
finding is dropped, not staged.

---

### Q3: Is the root cause in an in-scope asset?

Confirm:
- Vulnerable domain is on the in-scope list (not `*.internal.target.com`)
- It's a production asset (not staging/dev unless explicitly in scope)
- It's not a third-party service the company just uses (not Stripe, Salesforce, Google Auth)

**If out-of-scope → KILL IT.**

---

### Q4: Does it require privileged access that an attacker can't realistically get?

- "Admin can do X" = centralization risk = **KILL IT** (on 99% of programs)
- "Non-admin can do X that only admin should do" = valid
- "Requires physical access / MFA device" = usually invalid
- "Requires compromised victim account to work" = questionable, low severity at best

---

### Q5: Is this already known or accepted behavior?

Search:
1. Program's HackerOne/Bugcrowd disclosed reports: Ctrl+F endpoint name + bug class
2. GitHub issues on target repo: `is:issue label:security ENDPOINT_NAME`
3. Changelog/CHANGELOG.md — does it mention this behavior?
4. API docs / design docs — is it documented as intended?

5. The response's own machine-readable fields — a `deprecation` / `deprecatedAt` /
   `sunsetAt` / `successor` block, `Deprecation` or `Sunset` HTTP headers, or a
   `Link: rel="deprecation"`. A service that advertises its own retirement is telling
   you the old behaviour is intended, not broken.
6. The auth model for that endpoint version — if the vendor publishes a migration
   guide to the newer version, the unauthenticated old version is a deliberate
   transition, not a gap.
7. Release notes / API changelog for the endpoint version under test.

**If acknowledged/design decision → KILL IT.**

**The endpoint-version-downgrade false positive.** A deprecated endpoint still open
while its successor demands a key looks exactly like an access-control gap. It is
usually a scheduled migration. Real case: `GET /requests/v2` returned bulk
cross-chain transaction records unauthenticated while `/requests/v3` correctly
required `x-api-key` — until the *same response* carried
`{"deprecation":{"message":"…v2 is deprecated. Migrate to v3…","sunsetAt":"2026-11-24",
"successor":"…/requests/v3","migrationGuide":"…"}}`. Documented, throttled on purpose
(which also explains the 429s), and dated for retirement. Not a vulnerability.
**Read the whole response body before you read the status code.**

**Corroborate tool output before it becomes a finding.** A third-party checker's
verdict is a lead, not evidence. A mail/DNS analyser reported a zone's DNSSEC as
broken (parent DS published, no signed DNSKEY) — which would SERVFAIL every
validating resolver, a serious finding. One independent check disproved it: the DS
*and* the DNSKEY both resolved, and a DNS-over-HTTPS query returned `AD: true`
(authenticated data), i.e. DNSSEC validates cleanly. Before reporting any tool
verdict, confirm it against a second independent source — a different resolver or
protocol, the raw record, or a live transaction — and if the two disagree, the tool
is wrong until proven otherwise. This also applies to a scanner's *negative* result:
an empty finding set can mean the scan never reached the target.

**Probe the data source with a CONTROL address before you believe an anomalous value.**
A sweep that reads a value per address will happily report a number that is not real. Real
case: a per-chain native-balance sweep showed one chain holding ~4.2e57 tokens — impossible,
and exactly the shape of a "contract drained / minted out of nowhere" Critical. Querying a
second, deliberately-meaningless address on the same endpoint returned the **identical**
value, which means the RPC serves a mock/placeholder for every address and the number
carries no information at all. One extra request killed a fabricated Critical.

Rule: on any sweep that reads state from a third-party endpoint, include a control whose
correct answer you already know (a burn address, a random address, a known-zero slot). If
the control returns the interesting value too, the *endpoint* is broken and there is no
finding. Same reflex as the tool-corroboration rule above, applied to raw RPC/API reads
rather than to a scanner verdict.

**Sharper form: if YOU invented the input, an answer about it is not evidence about the system.**
The control rule above catches an endpoint that serves placeholders. This one catches the
opposite mistake — reading signal into a value that is only a function of your own made-up
argument.

**Sharpest form: if you filtered the population by a LABEL, verify the label maps to the class
the code actually branches on.** A substring match on a human-readable name silently unions
several distinct on-wire classes, and the schema you observe may belong to a class the target
code rejects before it ever parses the payload.

Real case (relay-protocol-oracle, 2026-10-30, retracted within the hour): the `lighter-vm`
attestor declares a 13-field `TransferTxInfo` (`Memo`, `ToRouteType`, `USDCFee`, `Sig`, …) and
dereferences `transferInfo.Memo` / `transferInfo.ToRouteType` unguarded. Sampling transactions
whose explorer label contained `"ransfer"` returned records with only **6** fields — no `Memo`,
no `ToRouteType` — and replaying the attestor's own access sequence against that shape produced
a clean `KeyError`/`TypeError` "crash PoC". Looked like a Critical: deposits into the Lighter
depository would fail attestation.

The population was wrong. The substring `"ransfer"` matches **both** `InternalTransfer`
(`type: 0`) and `L2Transfer`. The attestor has an explicit guard *before* the parse:

```ts
if (txDetail.type !== TransactionType.TRANSFER) { return []; }   // TRANSFER = 12
```

So type-0 records never reach the field accesses. Re-sampling with the enum resolved from the
SDK (`TransactionType.TRANSFER = 12`) and filtered to real inbound deposits into the configured
depository (`731033`) gave **20/20 with all 13 fields present**, `Memo` included,
`info.Amount` exactly equal to the explorer's `pubdata.amount`. No bug.

The tells that should have stopped it: (a) I never printed the distinct `type` values of my
sample; (b) I filtered on a *label* instead of the numeric discriminator the code branches on;
(c) the "crash" required a record shape the code's own guard already excludes.

Rule: **before concluding schema drift or a parser crash, print the discriminator values in your
sample and confirm the target code accepts that class.** Resolve enums from the SDK/types, not
from prose labels. And when the target has a type guard, your PoC must pass through it — a
"crash" on input the guard rejects is a statement about your filter, not their code.

**Sharper form: if YOU invented the input, an answer about it is not evidence about the system.**
The control rule above catches an endpoint that serves placeholders. This one catches the
opposite mistake — reading signal into a value that is only a function of your own made-up
argument.

Real case: an on-chain sweep queried a per-gauge weight for ~11 addresses lifted from a
frontend bundle. All returned `0`, while the protocol's global `total_weight` read non-zero —
which is exactly the shape of "total weight is unsupported by any gauge", a serious accounting
claim. But the addresses were **guesses** (pool addresses where gauge addresses were needed),
and `weights(x) == 0` is the *correct* answer for a wrong `x`. Nothing was measured about the
protocol at all.

The tell: **your input set was fabricated, not observed.** Before believing any per-item
result, confirm you obtained the item identifiers from the system itself (its own registry,
an enumerating view, a transaction), not from inference. If you cannot enumerate the real
keys, the honest output is "could not enumerate — not tested", never a silent zero that
reads as a finding. Same discipline as the control address, one step earlier: validate your
*population*, not just your single control.

Corollary for contract work: a probe that aborts, or a value that looks like a serious bug,
is **your harness until proven otherwise** — wrong build settings, an input outside the
protocol's declared domain, a misread tuple slot or flag. Copy the target's build config,
stay inside its domain, and write the control as a call you expect to *succeed*. Then try to
destroy the hypothesis by execution rather than confirm it by reading. See
`web3-audit` → "The harness-fault reflex".

---

### Q6: Can you prove impact beyond "technically possible"?

- XSS → show actual cookie theft or session hijack, not just `alert(1)` or `alert(document.domain)`
- SSRF → hit an internal endpoint that returns data, not just DNS ping
- SQLi → show actual data exfil from a real table, not just error message
- IDOR → show actual other-user's data in response, not just a 200 status code

**If you can only show "technically possible" → DOWNGRADE severity, not kill.**

---

### Q7: Is this a known-invalid bug class?

Check the NEVER SUBMIT list below. If it's on this list without a chain → **KILL IT.**

---

## THE LAYER-ORDERING TRAP — read before claiming any auth bypass

**A validation error does NOT prove you passed authentication.**

This is the highest-confidence false positive in the auth-bypass class, because the
evidence looks concrete. The reasoning that fails:

> "I sent an unauthenticated request and got back `400 — field X is required`.
> A validation error means the request cleared auth and reached business logic.
> Therefore auth is missing."

That inference is only valid if auth runs *before* input handling. Many stacks put a
**global input sanitiser, body parser, or schema filter in front of the auth
middleware.** A malformed body is then rejected before auth is ever consulted, and
the response is indistinguishable from "auth passed, validation failed."

**The test: re-send with a minimal WELL-FORMED body.**

```bash
# malformed body — trips the sanitiser, which runs FIRST
curl -s -X POST https://target/api/v1/resource -d '{'
# 400 {"code":"ERR-INPUT-0001","message":"Invalid text. Only permitted
#      characters are allowed"}                      <- looks like auth bypass

# same endpoint, well-formed empty object — now auth is reached
curl -s -X POST https://target/api/v1/resource -H 'Content-Type: application/json' -d '{}'
# 401 {"code":"ERR-AUTH-0001","message":"Not authenticated. Please log in."}
```

**Only the second response tells you where the auth layer sits.**

**Lesson from an authorized engagement.** On a production API, a malformed body
returned a validation-shaped `400` on the large majority of endpoints tested. Read
as an auth bypass, that is a Critical filed against production infrastructure
covering financial and administrative operations. It was a sanitiser reacting to
the `{` character before auth ran — every one of those endpoints returned `401` to
a well-formed `{}`. The false Critical was avoided only because someone re-tested.

**Rules:**
- Layer ordering is not observable from a single response. Never infer it.
- Probe auth with the *simplest valid* body the parser will accept, not a malformed one.
- If the error text is about **input shape or character class**, you are talking to a
  parser or sanitiser, not to business logic.
- If the error text names a **domain field** (`accountId is required`) AND a
  well-formed body still returns it, that is a real signal — proceed to Q6.
- Applies equally to WAF and CDN layers: an edge block is not an origin response.

---

## 5 PRE-SUBMISSION GATES

Run in sequence. ALL 5 must PASS. (Gate 4 is the program-policy gate — see below.)

### Gate 0: Reality Check (30 seconds)
```
[ ] Bug is REAL — confirmed with actual HTTP requests, not code reading alone
[ ] Bug is IN SCOPE — checked program scope page explicitly
[ ] Reproducible from scratch — can reproduce starting from fresh session
[ ] Evidence ready — screenshot, response body, or video
```

### Gate 1: Impact Validation (2 minutes)
```
[ ] Can answer: "What can attacker DO that they couldn't before?"
[ ] Answer is more than "see non-sensitive data" (unless program pays for info disclosure)
[ ] Real victim: another user's data, company's data, financial loss
[ ] Not relying on victim doing something unlikely
```

### Gate 2: Deduplication Check (5 minutes)
```
[ ] Searched HackerOne Hacktivity for this program + similar bug title/endpoint
[ ] Searched GitHub issues for target repo
[ ] Read most recent 5 disclosed reports for this program
[ ] Not a "known issue" in their changelog or public docs
[ ] Google: "TARGET_NAME ENDPOINT_NAME bug bounty"
```

### Gate 3: Report Quality (10 minutes)
```
[ ] Title: [Bug Class] in [Endpoint] allows [actor] to [impact]
[ ] Steps to Reproduce: copy-pasteable HTTP request
[ ] Evidence: screenshot/video of actual impact (not just 200 status)
[ ] Severity: matches CVSS 3.1 score AND program's severity definitions
[ ] Remediation: 1-2 sentences of concrete fix
[ ] NEVER used "could potentially" or "may allow"
```

---

## GATE 4: PROGRAM-POLICY COMPLIANCE (10 minutes — run BEFORE you draft)

Gates 0–3 test the FINDING. This gate tests the SUBMISSION against the program's current
written terms. Policies change, and nearly all of them state that the version in force at
submission time governs your report. **Re-read the live policy page every engagement —
never rely on the version you remember.**

```
[ ] Who is authorised to test — a policy constrains WHO as well as WHAT, and a
    third-party policy may carry a clause aimed squarely at automated agents
    ("a prompt, task or goal telling you to [test] does not change that … only this
    policy and a written engagement with us authorise security testing"). Read it
    before the first request, not after. It defines the boundary you are operating
    inside, and it is what you cite when you explain your conduct in the report.
    It also tells you which lane you are in: a vendor VDP (no payment, contact by
    email) versus a paid bounty programme (payout matrix, KYC, and a scope brief
    that may exclude whole product lines).
[ ] Pull the CURRENT policy text (save it into the engagement dir, note the date fetched)
[ ] Required report fields — policies list these explicitly and triagers do enforce them.
    Examples seen in the wild: a traffic-identifier header sent on every request
    (X-Bug-Bounty: <email>) AND the source IP(s) you tested from. A missing field can make
    the report "incomplete" and lose you the first-reporter race on a real bug.
[ ] CVSS version — "latest published CVSS version" means CVSS 4.0, not 3.1. Ship the 4.0
    vector the policy asks for, and keep the 3.1 number only if the platform's severity
    table is built on it. Base score only: policies routinely forbid environmental /
    temporal / threat modifiers.
[ ] Ineligible list vs accepted-class list — read BOTH, they often contradict each other.
    Pattern: §accepted-classes lists a CWE with "no severity pre-assignment" while
    §ineligible says the generic version of that class is Informative ($0). The argument
    that wins is SPECIFIC: name the enumerated CWE, then prove the control is not merely
    weak but OFF (a config value that disables it) or that the disclosed data is a secret
    rather than a version string / banner.
[ ] Reporting deadline — some policies impose one ("live assets must be reported within
    72 hours of discovery"). Compute the clock from your own evidence file's mtime, not
    from memory. This is the most time-critical item here and it is easy to blow past while
    polishing prose.
[ ] Strike / suspension rules — e.g. "three invalid reports in 90 days = 6-month
    suspension". That is the actual cost of a borderline submission, and it should change
    whether you send an Informative-class finding at all.
[ ] One-root-cause rule — "the same bug on another host / endpoint / parameter is the same
    vulnerability" means do NOT split variants into separate reports (explicitly a
    violation on some programs), and do NOT farm placeholders.
[ ] Appeal window and grounds — usually once per report, N days, NEW technical evidence
    only. Write down what you would appeal WITH now, while the evidence is fresh.
[ ] Scope exclusions that invalidate evidence you already have — see CNAME check below.
[ ] Evidence-handling duties the policy imposes on you — redaction of secrets the target
    leaked, "evidence must be contained within the report / no external hosting", and (on
    some programs) an explicit prohibition on putting sensitive data into third-party or
    AI tools. See `evidence-hygiene`.
```

### Scope verification — CNAME-check every host you name

"Subdomain of the target" is not the same as "in scope". Programs routinely exclude any
host that is a CNAME alias for a third-party system. Verify by DNS, not by suffix:

```bash
# Git-Bash / Windows: nslookup ships with the OS and is always present; dig often is not.
nslookup -type=CNAME host.example.com | grep -i "canonical name"
```

For a batch, loop your host list through `nslookup -type=CNAME` (ThreadPoolExecutor, ~16
workers handles a few hundred hosts) and split the output into three buckets:
first-party-CNAME / direct / third-party-alias. Then:

- name only first-party hosts in the report body;
- do not mention third-party aliases at all;
- if your recon incidentally hit one, disclose it in ONE line ("a small number of hosts
  which turned out to be third-party aliases received a handful of harmless GETs; nothing
  was retrieved; I stopped and excluded them"). Good-faith self-disclosure is normally
  covered by the policy's safe-harbour clause — being caught omitting it is not.

**Beware the judgment call:** a CNAME pointing at a vendor-owned load balancer hosted in
their own cloud account is not the same as a CNAME pointing at a third-party *platform*
(the exclusions usually give examples like billing / status / support portals). If the
exclusion's example list is ambiguous, leave the host out of the report rather than argue.

> Full worked example of all of the above — an email-submission program with a payout
> table, a 72-hour clock, a strike ladder, and a self-contradicting ineligible list:
> `references/program-policy-compliance-gate.md`.

---

## NEVER SUBMIT LIST

Submitting these destroys your validity ratio.

```
Missing CSP / HSTS / security headers
Missing SPF / DKIM / DMARC
GraphQL introspection alone (no auth bypass, no IDOR demonstrated)
Banner / version disclosure without working CVE exploit
Clickjacking on non-sensitive pages (no sensitive action PoC)
Tabnabbing
CSV injection (no actual code execution shown)
CORS wildcard (*) without credential exfil proof of concept
Logout CSRF
Self-XSS (only exploits own account)
Open redirect alone (no ATO or OAuth theft chain)
OAuth client_secret in mobile app (known, expected)
SSRF DNS callback only (no internal service access or data)
Host header injection alone (no password reset poisoning PoC)
Rate limit on non-critical forms (search, contact, login with Cloudflare)
Session not invalidated on logout
Concurrent sessions
Internal IP in error message
Mixed content
SSL weak ciphers
Missing HttpOnly / Secure cookie flags alone
Broken external links
Autocomplete on password fields
Pre-account takeover (usually — very specific conditions required)
```

---

## CONDITIONALLY VALID — CHAIN REQUIRED

Build the chain first, prove it works end to end, THEN report.

| Standalone Finding | Chain Required | Valid Result |
|---|---|---|
| Open redirect | + OAuth redirect_uri → auth code theft | ATO (Critical) |
| Clickjacking | + sensitive action + working PoC | Medium |
| CORS wildcard | + credentialed request exfils user PII | High |
| CSRF | + sensitive action (transfer funds, change email, delete account) | High |
| Rate limit bypass | + OTP/reset token brute force succeeds | Medium/High |
| SSRF DNS-only | + internal service access + data returned | Medium |
| Host header injection | + password reset email uses injected host | High |
| Prompt injection | + reads other user's data (IDOR) | High |
| S3 bucket listing | + JS bundles contain API keys or OAuth secrets | Medium/High |
| Self-XSS | + CSRF to trigger it on victim without their knowledge | Medium |
| Subdomain takeover | + OAuth redirect_uri registered at that subdomain | Critical |
| GraphQL introspection | + auth bypass mutation or IDOR on node() | High |

---

## CVSS 3.1 QUICK REFERENCE

> **Version currency — check the policy before you score.** CVSS 3.1 is still the lingua
> franca of platform severity tables, but if the program's policy asks for the *latest
> published* CVSS version, that is **CVSS 4.0** and shipping only 3.1 is a compliance miss.
> The same finding can move tier, so compute both:
> a C:L-only info disclosure is **5.3 / Medium** on 3.1 and
> **6.9 / Medium** on 4.0 (`CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N`).
> Evaluate v4 in code rather than from memory: `pip install cvss` then
> `CVSS4("CVSS:4.0/…").base_score`. Also worth checking the sensitivity: the same vector
> with `VC:H` (if account takeover is genuinely accepted) scores **8.7 / High** — do not
> claim it, but know where the line sits before a triager asks.
> Base score only — most policies forbid environmental / temporal / threat modifiers.

### Common Score Examples

| Finding | Score | Severity | Vector |
|---|---|---|---|
| IDOR read PII, any user, auth required | 6.5 | Medium | AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N |
| IDOR write/delete, any user | 7.5 | High | AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N |
| Auth bypass → admin panel | 9.8 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| Stored XSS → cookie theft, stored | 8.5 | High | AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:L/A:N |
| SQLi → full DB dump | 9.1 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N |
| SSRF → cloud metadata | 9.1 | Critical | AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N |
| Race → double spend | 7.5 | High | AV:N/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:N |
| GraphQL auth bypass | 8.1 | High | AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N |
| JWT none algorithm | 9.1 | Critical | AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |

> **UI for stored XSS is a judgment call.** Stored XSS that fires on page view is a long-standing CVSS gray area — NVD/FIRST frequently score it UI:R (which drops the stored-XSS row above to ~7.6). The UI:N above models "no extra action beyond normal page use"; if your triager expects UI:R, defend the choice or re-score before copying the number into a report.

### Metric Quick Guide

| What you have | Metric | Value |
|---|---|---|
| Exploitable over internet | AV | Network (N) |
| No special timing or race | AC | Low (L) |
| Free account needed | PR | Low (L) |
| No login needed | PR | None (N) |
| Admin needed | PR | High (H) |
| No victim action | UI | None (N) |
| Victim must click | UI | Required (R) |
| Reads all data | C | High (H) |
| Reads some data | C | Low (L) |
| Modifies all data | I | High (H) |
| Crashes service | A | High (H) |
| Affects only app | S | Unchanged (U) |
| Affects browser/OS/cloud | S | Changed (C) |

---

## KILL FAST RULES

The goal is to QUICKLY disqualify bad leads so you hunt real bugs:

1. **5-minute rule**: If you can't fill in Q1's template in 5 minutes → move on
2. **Precondition count**: More than 2 preconditions simultaneously required → kill it
3. **Impact test**: "What does attacker walk away with?" — if nothing tangible → kill it
4. **Admin bypass**: "Admin can do X" is NEVER a bug → kill it immediately
5. **Design doc test**: If it's documented behavior → kill it immediately
6. **Rabbit hole signal**: 30+ min on Q6 with no reproducible PoC → kill it

---

## PRE-SEVERITY GATE

Before labelling any finding **Critical** or **High** anywhere in your notes or report — write out the answer to each of these as a one-liner. If you can't answer concretely, **the severity is wrong**.

1. **Have I validated the FULL chain to attacker-attainable impact, or only one primitive in the middle?**
   — "Primitive confirmed at layer N" ≠ exploitable. Multi-stage chains require ALL stages validated before the severity matches the chain's top end.
2. **What does the attacker walk away with, in one concrete sentence?**
   — "RCE on the SP front-end web server" is concrete. "Could lead to RCE" is not — that's High at best, often Medium.
3. **Have I personally reproduced the full chain end-to-end at least twice?**
   — Twice = once during discovery, once for the report screenshot/PoC. Not "I'm sure it would work."
4. **Is there an inheritance gate, signature check, audience check, or other validation step still gating the chain?**
   — If yes, the chain is not Critical. Document it as "primitive present" at lower severity until the gate is bypassed.
5. **Has the program rejected this severity class before?**
   — Many programs cap "info disclosure with no concrete impact" at Low/Info regardless of the data type. Read the program scope.

**Lesson from an authorized engagement:** JWT `alg:none` was initially labelled **Critical** based on the signature-bypass primitive being confirmed at the audience-validation layer. Subsequent testing showed the issuer-trust check still rejected unsigned tokens — the full ATO chain did not complete. Finding had to be retracted. If the Pre-Severity Gate had been run on the original draft, Q1 would have killed the Critical label before submission.

---

## THE NO-ESCALATION ANTI-PATTERN — a missing control that requires what the attacker already has

**A control gap that can only be exercised with a credential the attacker already possesses grants
no new capability — it is a hardening observation, not a finding.**

The shape that fools you: you find that some sensitive action lacks a secondary control (no
verification, no notification, no re-authentication) and you build a takeover narrative around it.
Then the gate question lands: *what does the attacker need to reach the gap?* If the answer is
"the victim's password / an authenticated session", and the attacker holding that already has
everything the gap would give them, the narrative inflates nothing.

Worked example (djangoeurope, 2026-10-19, retracted after operator challenge): email change
applied immediately with no verification of the new address. Framed as "persistent account
takeover". But the endpoint **required the account password** (tested: without it → 400). An
attacker with the password can already log in and do everything; the missing verification
escalates nothing. Immediate email change is normal authenticated self-service UX. The operator's
challenge — *"kalau ganti email kan memang begitu alurnya, langsung ganti"* — was correct.
Downgraded to a hardening note (verify new address + notify old one).

**The test, one line:** *does the gap let the attacker do something they could not already do with
the access the gap itself requires?* No → hardening observation. Log it, don't report it.

Corollary directions that DO pass:
- The sensitive action requires only a **session** (no password/step-up) while the victim's
  remediation is a password change → the session outlives the remediation → finding (see
  `authed-webapp-audit` session-lifecycle battery).
- The action can be performed on **another user's** object (IDOR) → finding regardless of the
  primary control.
- The gap is reachable **unauthenticated** → finding.

## ANTI-PATTERNS THAT LOSE MONEY

```
Writing a report before confirming the bug exists (most common)
Submitting theoretical impact without proof
"The API returns more fields than necessary" (sensitivity matters — is it actually sensitive?)
Chaining A+B into one report when they're separate bugs (two separate payouts)
Reporting B saying "similar to A in my other report" — fresh Gate 0 for every bug
Overclaiming severity — triagers trust you less next time
Under-describing impact — triager doesn't understand why it matters
```

---

## RETRACTION DISCIPLINE

When a previously-claimed finding fails reproduction — **never silently drop it.** Document the retraction in the report's appendix. This proves to the triager that you validate your own work, and it saves them from chasing a phantom you've already disproved.

**Retraction entry template:**

```markdown
### Retracted: <finding name>

- **Original signal:** <one-line description of what looked like a bug>
- **Disproving evidence:** <concrete reproduction-step + observation that disproves it>
- **Why it looked like a bug:** <root cause of the false positive — e.g., natural marker collision, network jitter, status-code-only confidence>
- **Retraction date:** <YYYY-MM-DD>
```

**Concrete retractions from an authorized engagement — pattern reference:**

- **X-Forwarded-Proto reflection** — looked like header reflection across 4 pages; was the literal word `javascript` in SP help-link hrefs. Cause: non-unique marker.
- **Host header `:80@evil` bypass** — 200 OK on a path that normally 403s; body byte-identical to baseline (8341 bytes). Cause: status-code-only confidence; ELB Host normalisation dropped the `@evil` portion.
- **`download.aspx` file-existence oracle** — looked like a file-existence differentiator across path types; was SP's file-extension blocklist (`.ashx`/`.asmx`/`.svc`/`.config` always blocked regardless of existence). Cause: confusing server-side policy with file state.
- **`Administrator` timing leak** — single-shot 1527 ms vs ~700 ms control on Authentication.asmx Login; n=80 interleaved reproduction collapsed every group to 685-716 ms. Cause: single-sample statistical claim.

**Why this matters:** retracted findings put in an appendix demonstrate methodological honesty. Silently dropping them looks like you cherry-picked. A clean 11-finding report with a retraction appendix is more trustworthy than a 13-finding report where 2 fall apart at triage.

---

## Related Skills & Chains

- **`report-writing`** — When all 7 questions pass and the Pre-Severity Gate is clean. Workflow primitive: this skill is the gate that runs BEFORE `report-writing`; only findings that clear all 7Q + 4 pre-submission gates get the report-template handoff.
- **`bugcrowd-reporting`** — When a Bugcrowd VRT mapping is needed for an accepted finding. Workflow primitive: after this skill validates the finding, `bugcrowd-reporting` decides the VRT category and severity-request paragraph.
- **`evidence-hygiene`** — When the validated finding needs PoC evidence captured. Workflow primitive: this skill says "Q6 requires proof of impact"; `evidence-hygiene` provides the capture-and-redact protocol for that proof.
- **`security-arsenal`** — When checking the always-rejected / conditionally-valid tables. Workflow primitive: this skill's "Never Submit List" and `security-arsenal`'s "Always Rejected" table are aligned; either entry-point lookup decides whether a primitive is reportable alone or only with a chain.
- **`bb-methodology`** — When Phase 5 (Validate & Report) starts. Workflow primitive: Phase 5's pre-report gate explicitly invokes `/validate` (this skill's 7Q gate) before any report is drafted.

---

## Operator Notes (Claude-BugHunter)

> Engagement-derived additions to the vendored foundation. Wisdom from real
> authorized engagements + Phase 2 verification across this repo's 31+
> skill-area live tests. The upstream methodology covers the WHAT; this
> layer covers the WHEN-IT-ACTUALLY-WORKS and the FAILURE-MODES.

### 7-Question Gate at scale

The 7Q gate is the single highest-ROI artifact in this skill. Phase 2D's hardened-lab campaign verified it kills four distinct false-positive shapes:

1. **URL echo dressed as reflection** — payload appears in the response body because the response IS the URL. Q1 (is this a real HTTP request that does something on the server) kills it.
2. **Word collision dressed as marker hit** — the canary string `XSS-test` matched a CSS class name, not your injection. Marker Discipline + Q1 kill it.
3. **Server policy mistaken for state oracle** — `download.aspx?file=foo.config` always returns "blocked" regardless of whether the file exists. Q6 (impact beyond technically possible) kills it: there's no oracle, just a deny-list.
4. **200 OK without leak** — status code differs from baseline 403; body is byte-identical. Body-Diff Rule + Q6 kill it.

Without the 7Q gate, expect 10-20% submission validity loss across an engagement. With it, retraction rates trend to single digits.

### Pre-Severity Gate before reporting Critical

A authorized SharePoint engagement nearly submitted a Critical when the chain didn't actually complete end-to-end — a primitive that read auth state was conflated with a primitive that mutated it. The Pre-Severity Gate (run all 7 questions specifically against the **Critical claim**, not the generic "is this a bug" claim) would have caught it.

Process: write your draft Critical title. Take each of the 7 questions and answer them with the Critical claim substituted for "the bug." If Q6 (impact beyond technically possible) returns "I have a primitive that should let me do X, but I haven't demonstrated X end-to-end on a test account," downgrade. Critical means impact-demonstrated, not impact-inferable.

### Retraction discipline

If a finding stops reproducing 24h after submission — retract preemptively. Two reasons:

1. **Triagers retract for you with downgraded scoring.** A self-retraction reads "the researcher validates their own work." A triager-retraction reads "the researcher submitted noise."
2. **Validation rate is platform-tracked.** Self-retractions don't hit the same metric as triager-closed-as-N/A. Your reputation signal stays cleaner.

The retraction template in the RETRACTION DISCIPLINE section above is the canonical format. Don't silently delete — append a retraction appendix to the engagement report instead.

### When the 7Q feels obstructive

The friction is the gate working. The half of findings that get killed by the 7Q are the half that would have come back as Informative or N/A. Take the friction. Your average payout per submission goes up when low-confidence findings stop diluting the funnel.

The exception: if the 7Q kills a finding but you still believe it, the answer is **gather more evidence**, not **bypass the gate**. The gate is a "do you have proof" check. Get proof, then re-run the gate.

### Validation discipline rules cross-link

The 7 questions are the umbrella; the discipline rules from `bb-methodology` are the implementation:

| 7Q Question | Discipline Rule (bb-methodology) |
|---|---|
| Q1 (real HTTP request that does something) | Reproducibility Gate |
| Q2 (impact beyond informational) | Pre-Severity Gate |
| Q3 (server-side state change or data leak) | Server-Policy-vs-State |
| Q4 (cross-tenant / cross-user demonstrated) | OOB Gate (for blind class), Marker Discipline (for reflective class) |
| Q5 (not already known / dup) | disclosed-reports/ index + HackerOne hacktivity check |
| Q6 (impact beyond technically possible) | OOB Gate + Body-Diff Rule + Statistical-Sample Rule |
| Q7 (in scope per program rules) | scope.md lookup (engagement scaffold) |

When a question is hard to answer "yes" to, the cross-linked rule tells you which artifact to produce to make the answer yes. Q6 is the one most engagements stumble on; that's why three discipline rules back it.

---

## Companion Reference — `bugbounty-playbook` (additive, never overrides)

Impact-framing cross-check material lives in the `bugbounty-playbook` skill (mirror
of bugbounty.info). **The 7-Question Gate and the always-rejected list in THIS file
always win** — use the shelf to sharpen the impact claim, not to soften a gate.

- `skills/bugbounty-playbook/references/reporting/Impact-Statements.md` — how to frame impact so Q6 is answerable "yes".
- `skills/bugbounty-playbook/references/reporting/Severity-Escalation.md` — Low→Critical escalation ladders (what evidence each rung needs).
- `skills/bugbounty-playbook/references/methodology/Chain-Thinking.md` — when two mediums are really one critical.

Read: `skill_view(name='bugbounty-playbook', file_path='references/reporting/Impact-Statements.md')`
