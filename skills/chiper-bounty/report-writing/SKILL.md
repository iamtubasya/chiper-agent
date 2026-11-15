---
name: report-writing
description: Bug bounty report writing for H1/Bugcrowd/Intigriti/Immunefi — report templates, human tone guidelines, impact-first writing, CVSS 3.1 scoring, title formula, impact statement formula, severity decision guide, downgrade counters, pre-submit checklist. Validation gates and the submittability/always-rejected decision are owned by triage-validation; this skill owns the written report itself (templates, tone, formulas). Use after validating a finding and before submitting. Never use "could potentially" — prove it or don't report.
sources: community, operator_experience
---

# REPORT WRITING

> **Before you write, and again before you submit:** run **`report-gotchas`**.
> At 0E, its `references/class-gotchas.md` gives the per-class *minimum proof*
> and the overclaim traps — check the PoC meets the bar before you draft the
> Impact section. At 0F, its `references/ai-slop-patterns.md` is the slop
> detector to run over the finished draft. This skill owns the structure and
> tone; `report-gotchas` owns the proof bar and the slop checklist;
> `triage-validation` owns the go/no-go decision.

Impact-first. Human tone. No theoretical language. Triagers are people.

---

## THE DELIVERABLE MUST BE SELF-CONTAINED

> **Humanize every draft (operator hard rule, 2026-11-02).** Sebelum laporan dikirim (draft,
> PDF, email body, atau format apa pun), jalankan skill `humanizer` (patterns 1–29) atas teks
> laporan. **Clean text** wajib: hapus pemisah dekoratif `+++++`, `=====`, `_____`, `-----`,
> em-dash berlebihan, bold-mekanis, emoji, rule-of-three, dan AI-slop lain — KECUALI memang
> dibutuhkan di bagian PoC (batas blok kode, pemisah request/response). Laporan yang tampak
> "AI slop / low quality" rutin ditolak vendor. Ini pelengkap `report-gotchas`/`ai-slop-patterns.md`:
> `humanizer` menghilangkan *suara* AI, `report-gotchas` mengecek *substansi* PoC.

A report whose body says "attached PoC `foo.py`" while only the PDF is attached is a defect the
triager hits before they read a single finding. Rules that caught a real miss (2026-10, wallet audit):

- **Never reference a file the recipient does not receive.** Grep the final body for "attached",
  "see the PoC", "appendix", and any filename; every mention must resolve to something actually
  attached or inlined in that same artifact.
- **Prefer inlining the PoC into the PDF** — an "Appendix — PoC" section carrying the runnable
  script / the crafted request / the raw trace. Then one artifact is complete and survives being
  forwarded or re-attached by someone else.
- **Ship both forms when you have them:** a prose reproducer proves the behaviour; a drop-in test
  (e.g. a JUnit class that goes red on the current build) proves the fix. Label the expected result
  (which assertion fails today).
- Keep the report SHORT and the PoC in the appendix — the body states finding + steps + impact,
  the appendix holds the code.
- **A script alone is NOT sufficient details.** Every attached reproducer script MUST ship alongside:
  (a) a full list of the relevant endpoints (method + path + the exact parameter/body touched), and
  (b) a prose attack chain explaining step-by-step how the primitive reaches impact. The script is
  the *evidence*, not the *explanation* — a triager must be able to reproduce from the prose alone
  without running your code. Put endpoints + chain in the body; keep the script in the appendix.
- **Make scripts Burp-proxyable when you can.** A script that falls back to
  `http_proxy`/`https_proxy` env vars (or `requests`/`httpx` proxies, or a `--proxy http://127.0.0.1:8080`
  flag) lets the triager route it through Burp to read the raw HTTP requests — that materially speeds
  triage. State in the appendix how to set the proxy (one line), don't silently assume a proxy.

When the operator wants per-finding deliverables, each PDF must stand alone; the cross-finding
summary table belongs in the local combined artifact, never in an outbound body (see
`email-automation`: one finding = one PDF = one draft).

---

## THE MOST IMPORTANT RULE

> **Never use "could potentially" or "could be used to" or "may allow".**
> Either it does the thing or it doesn't. If you haven't proved it, don't claim it.

```
BAD:  "This vulnerability could potentially allow an attacker to access user data."
GOOD: "An attacker can access any user's order history by changing the user_id
       parameter to the target user's ID. I confirmed this using two test accounts:
       attacker@test.com (ID 123) successfully retrieved victim@test.com (ID 456)
       orders, including their shipping address and payment method last 4 digits."
```

---

## RE-MEASURE EVERY NUMBER BEFORE YOU FINALISE

A claim that was true when you found it can be false by the time you write the report, and a report
carrying a dead number is worse than one that never made the claim. Measured case (Social Deal,
2026-10-29): the report said `/city/` disclosed pre-launch cities because the schema carried
`is_development` and `is_white_label`. Re-measuring immediately before finalising showed both flags
were false for **0 of 119** cities — the claim was withdrawn from the PDF *and* the submission body,
and the "what I did not obtain" section gained the explicit negative.

Before a draft is staged, re-run the measurement behind every quantitative claim in the body:

```
[ ] every count re-measured against the live target (N cities, N tenants, N services)
[ ] every "X is true for N of M" statement re-counted, not carried over from notes
[ ] the build/version string re-fetched (it rotates — a stale hash is a dead claim)
[ ] each withdrawn claim moved into the explicit "what I did not obtain" list
```

The same pass is what makes a thin report credible: a triager who can verify your negatives trusts
your positives. Withdrawing a claim and saying so is not weakness — it is the difference between a
report that survives triage and one that gets closed as overstated.

## THE ACCOUNT & WALLET INVENTORY IS PART OF THE REPRODUCTION

Most crypto / web3 / agent-platform programs make this mandatory, and it is not the same thing as
"two test accounts used". Bankr §7 item 5, verbatim: *"list every Bankr account (email or handle)
and wallet address you used while testing, and the dates you tested. Activity we can't match to an
account or address you listed may be treated as unauthorized use."* A report without it gets
triaged as incomplete even when the bug is real, because the vendor's anti-abuse process cannot
clear the testing burst.

The section must carry, in the report **and** in the e-mail body:

- every login, including aliases (`+tag`, dot variants) that resolved to the same account — say
  why they collapsed and that no second wallet exists;
- every wallet on **every** chain (EVM *and* Solana), full address;
- disposable mailboxes that never produced a wallet, with the exact failure the vendor returned
  (e.g. `POST /user/bootstrap` → `500 Failed to set up your Bankr wallet`);
- locally generated key pairs created but never linked, never signed, no on-chain history;
- exact testing window (first and last event, UTC + local) and the egress IP;
- the balance the test wallet held (usually zero) — it explains why the finding is about
  entitlement/metering rather than funds and pre-empts a "you moved funds" reading.

Two layout consequences, both caught live 2026-10-30 on a staged Bankr draft: a 5-column
per-account table breaks e-mail addresses **mid-token** (`RESEARCHER_USERNAME` / `@gmail.co` / `m`) so the
full address never appears in the text layer — while `pdf_layout_check.py` still reports
`problems=0`. Use a two-column `Field | Value` table and then assert every complete address is
present in the extracted text. Also duplicate the block into the e-mail body as aligned
`key : value` lines, because some vendors accept only a web form and the PDF does not travel into
a form field. Full recipe, the failing table, and the assertion list:
`skills/report-writing/reportlab-security-pdf/references/account-wallet-inventory.md`.

When the operator asks for that inventory in the chat too ("tulis dsni jg boleh biar sy copi"),
hand over the same aligned block — not a prose summary.

## TITLE FORMULA

```
[Bug Class] in [Exact Endpoint/Feature] allows [attacker role] to [impact] [victim scope]
```

**Good titles (specific, impact-first):**
```
IDOR in /api/v2/invoices/{id} allows authenticated user to read any customer's invoice data
Missing auth on POST /api/admin/users allows unauthenticated attacker to create admin accounts
Stored XSS in profile bio field executes in admin panel — allows privilege escalation
SSRF via image import URL parameter reaches AWS EC2 metadata service
Race condition in coupon redemption allows same code to be used unlimited times
```

**Bad titles (vague, useless to triager):**
```
IDOR vulnerability found
Broken access control
XSS in user input
Security issue in API
Unauthorized access to user data
```

---

## HACKERONE REPORT TEMPLATE

```markdown
## Summary

[One paragraph: what the bug is, where it is, what an attacker can do. Be specific.
Include: endpoint, method, parameter, data exposed, required access level.]

Example: "The `/api/users/{user_id}/orders` endpoint does not verify that the
authenticated user owns the requested user_id. An attacker can enumerate any
user's order history, including PII (email, address, phone) and purchase history,
by incrementing the user_id parameter. No privileges beyond a standard free
account are required."

## Vulnerability Details

**Vulnerability Type:** IDOR / Broken Object Level Authorization
**CVSS 3.1 Score:** 6.5 (Medium) — AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N
**Affected Endpoint:** GET /api/users/{user_id}/orders

## Steps to Reproduce

**Environment:**
- Attacker account: attacker@test.com, user_id = 123
- Victim account: victim@test.com, user_id = 456
- Target: https://target.com

**Steps:**

1. Log in as attacker@test.com, obtain Bearer token

2. Send the following request:

```
GET /api/users/456/orders HTTP/1.1
Host: target.com
Authorization: Bearer ATTACKER_TOKEN_HERE
```

3. Observe response:

```json
{
  "orders": [
    {"id": 789, "items": [...], "email": "victim@test.com", "address": "123 Main St..."}
  ]
}
```

The response contains victim's full order history and PII despite being requested
by a different user.

## Impact

An authenticated attacker can enumerate all user orders by iterating user_id values.
This exposes: full name, email, shipping address, purchase history, and payment
method (last 4). With ~100K users, this represents a mass PII breach affecting
all registered users. Exploitation requires only a free account and takes minutes
with a simple loop.

## Recommended Fix

Add server-side ownership verification:
```python
if order.user_id != current_user.id:
    raise Forbidden()
```

## Supporting Materials

[Screenshot showing attacker's session returning victim's order data]
[Video walkthrough if available]
```

---

## BUGCROWD REPORT TEMPLATE

```markdown
# [IDOR] User order history accessible without authorization via /api/users/{id}/orders

**VRT Category:** Broken Access Control > IDOR > P2

## Description

[Same impact-first paragraph as HackerOne summary]

## Steps to Reproduce

[Same structured steps — exact HTTP requests, exact responses]

## Proof of Concept

[Screenshot/video showing the actual impact]

## Expected vs Actual Behavior

**Expected:** 403 Forbidden when user_id does not match authenticated user
**Actual:** 200 OK with victim's full order data

## Explaining findings back to the requester (second audience)

The vendor report and the chat reply to the user are **different documents**. A pentester who
runs a long session will otherwise receive a wall of terminology; that is not a display of
rigour, it is a handoff failure. This user in particular asks for plain language — *"cba jelaskan
dengan kalimat sederhana"* — so lead with the plain version.

Shape that works:

1. **Verdict first, one line.** "No bounty-grade finding; one low validation gap; one tax-logic
   gap." Nothing before that.
2. **What is safe** — short bullets of the controls you actually broke on. This is what the user
   needs to decide whether to keep digging.
3. **What is broken**, per item, in this order: what happens → who is affected → how bad.
   Leave field names, action ids, digests and wire formats for the artifact file; keep one
   concrete number per claim, because a single real figure beats three paragraphs of description.
4. **Answer what they explicitly asked about**, in its own block, including the honest
   "no, I could not reach that, here is the gate that stopped me."
5. **Next steps as a short choice list**, not a menu.

Rules for the plain version:
- Describe the *consequence*, not the mechanism: "the app cannot record that you sold half a
  property in June, so the yearly figure is wrong either way" — not "the ownership share is a
  scalar with no effective date".
- No jargon in the headings. "Problem 2 (main) — A property that changes hands mid-month cannot
  be recorded", not "Missing date-effective ownership partitioning (CWE-840)".
- **Never inflate, and never let a dead number live on.** If a finding was downgraded during the
  session, say so and say why, so the user does not act on the earlier figure. If something is
  unverified, label it as unverified in that same sentence, every time.
- Keep the heavy version (evidence tables, raw numbers, tool logs, per-request traces) in the
  artifact on disk and give the user the path. Do not paste it into chat.

## Severity Justification

P2 (High) — Direct read access to other users' PII. Affects all user accounts.
No user interaction required. Exploitable by any authenticated user.
Automated enumeration could exfil all [N] user records in minutes.

## Remediation

Add ownership verification: `if order.user_id != current_user.id: raise 403`
```

---

## INTIGRITI REPORT TEMPLATE

```markdown
# [Bug Class]: [Exact Impact] in [Endpoint/Feature]

## Description

[Impact-first paragraph. Start with what an attacker can do, not with how you found it.
Include: endpoint, method, parameter, data exposed, required privileges.]

## Steps to Reproduce

**Environment:**
- Attacker: email=attacker@test.com (standard account, no special role)
- Victim: email=victim@test.com
- Tested: [date]

**Reproduction steps:**

1. [Login as attacker / visit URL / send request]

2. Send the following HTTP request:

\```http
METHOD /endpoint HTTP/1.1
Host: target.com
Authorization: Bearer ATTACKER_TOKEN
Content-Type: application/json

{"param": "victim_id_here"}
\```

3. Observe response contains victim's private data:

\```json
{"email": "victim@test.com", "address": "123 Main St", ...}
\```

## Impact

[Specific, quantified impact. What data, how many users, what can attacker do.]

CVSS 3.1 Score: X.X ([Severity]) — AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N

## Remediation

[1-3 sentence concrete fix. Include code if helpful.]

## Attachments

[Screenshot or Loom video showing the impact — Intigriti triagers prefer video for complex bugs]
```

**Intigriti-specific notes:**
- Title format: `[Bug Class]: [One-line impact]` (no formula required, but keep it specific)
- Severity is set by you: Critical/High/Medium/Low/Exceptional
- CVSS 3.1 is standard (CVSS 4.0 also accepted on newer programs)
- PoC video is valued much more than screenshot alone — record with Loom
- Safe harbor: Intigriti enforces it, be comfortable going slightly aggressive with testing

---

## IMMUNEFI REPORT TEMPLATE
> **Severity for Immunefi submissions = Immunefi VSS v2.3 — NOT CVSS.** Do not paste a CVSS vector into
> the Severity field. Classify by IMPACT per domain (Smart Contracts / Blockchain-DLT / Websites-and-Apps);
> the impact must come from the program's official impact list and the asset from its official asset list.
> Elevated privilege or uncommon user interaction downgrades or rejects. Boundary lines that decide triage:
> *principal vs unclaimed yield* (Critical vs High), *temporary vs permanent freeze* (High vs Critical),
> *persistent vs reflected* HTML injection (High vs Medium). Full tables + out-of-scope list:
> `skills/security/bug-bounty/references/immunefi-vss-v2.3.md`
> (The CVSS 3.1 guidance elsewhere in this skill applies to H1 / Bugcrowd / Intigriti — **not** Immunefi.)

```markdown
# [Bug Class] — [Protocol Name] — [Severity]

## Summary

[One paragraph with: root cause, affected function, economic impact, attack cost.
Include numbers where possible: "attacker can drain $X in Y transactions."]

## Vulnerability Details

**Contract:** `VulnerableContract.sol`
**Function:** `claimRedemption()`
**Bug Class:** Accounting State Desynchronization
**Severity:** Critical

### Root Cause

[Exact code snippet showing the vulnerable code with comments]

## Proof of Concept

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
// Foundry PoC — run: forge test --match-test test_exploit -vvvv

contract ExploitTest is Test {
    // ... full working exploit
}
```

## Impact

[Quantified: "Attacker can drain X% of TVL = $Y at current rates.
Requires $Z gas. Attack is repeatable."]

## Recommended Fix

[Specific code change with before/after]
```

---

## CVSS 3.1 QUICK SCORING

### Formula
```
CVSS = f(AV, AC, PR, UI, S, C, I, A)
```

### Metric Quick Picks

| Metric | Value | Weight | When |
|---|---|---|---|
| **Attack Vector (AV)** | Network | +0.85 | Via internet |
| | Local | +0.55 | Local access needed |
| **Attack Complexity (AC)** | Low | +0.77 | Repeatable |
| | High | +0.44 | Race/timing needed |
| **Privileges Required (PR)** | None | +0.85 | No login |
| | Low | +0.62 | Regular user account |
| | High | +0.27 | Admin account |
| **User Interaction (UI)** | None | +0.85 | No victim action |
| | Required | +0.62 | Victim must click |
| **Scope (S)** | Changed | higher | Affects browser/OS/other |
| | Unchanged | lower | Stays in app |
| **Confidentiality (C)** | High | +0.56 | All data exposed |
| | Low | +0.22 | Limited data |
| **Integrity (I)** | High | +0.56 | Can modify any data |
| **Availability (A)** | High | +0.56 | Crashes service |

### Typical Scores by Bug Class

| Bug | Typical CVSS | Severity |
|---|---|---|
| IDOR (read PII) | 6.5 | Medium |
| IDOR (write/delete) | 7.5 | High |
| Auth bypass → admin | 9.8 | Critical |
| Stored XSS (any user) | 5.4–8.8 | Med–High |
| SQLi (data exfil) | 8.6 | High |
| SSRF (cloud metadata) | 9.1 | Critical |
| Race condition (double spend) | 7.5 | High |
| GraphQL auth bypass | 8.7 | High |
| JWT none algorithm | 9.1 | Critical |

---

## VERIFY THE ARTIFACTS YOU ARE TOLD TO "FIX" ACTUALLY EXIST — before touching anything

When the operator says "you already made drafts/PDFs — fix them per the policy", do NOT start
patching. Prior-session work frequently never persisted (interrupted session, failed upload,
different profile/machine). Run a 4-surface existence sweep FIRST, in one pass:

1. **Mailbox**: enumerate drafts (`users/me/drafts?maxResults=500`, follow `nextPageToken`,
   read To/Subject via `format=metadata`), then full-mailbox search (`q=<target>`,
   `includeSpamTrash=true`) — a self-addressed staging draft that merely MENTIONS the target in
   its body still counts as the only legitimate hit.
2. **Disk**: case-insensitive filename search over the audit roots, then content-grep
   (`grep -ril "<target>"`) over text files (md/txt/json/html/log) in those roots.
3. **Session DB**: `session_search(query=<target>)` plus a browse of recent sessions.
4. **Logs**: `grep -i <target> logs/agent.log*` including rotated files (the current log may
   postdate the work).

If all four are empty: state it in ONE line as the limiting fact ("no drafts/artifacts exist in
Gmail, on disk, in the session DB, or in the logs — nothing to patch in place"), then rebuild
the engagement from scratch and say that too. Never pretend a fix-up happened; never fabricate
the missing artifacts to satisfy the request. When staging the rebuilt drafts, follow the
target's own VDP to the letter — the two rules that most often differ from generic practice:
**1 finding = 1 message/ticket**, and the **full description must live in the message BODY**
(a report whose body is "see attached PDF" is rejected outright; screenshots/PoC video as
attachments are welcome). No severity self-assessment when the program reserves that judgement.

## TRIAGE AGAINST THE PROGRAM'S OWN NONE-LIST BEFORE DRAFTING ANYTHING

Verified 2026-10-17 (CoderPad VDP). Most modern VDPs publish an explicit out-of-scope / "None"
list, and it is usually stricter than the generic always-rejected list above. Before creating a
single draft, map every candidate finding against the program's own clauses and record the clause
that kills it:

- CoderPad examples that killed real, reproducible, tool-backed findings: "All RATE LIMITING related
  reports, or missing throttling" (killed a demonstrated 400-alias GraphQL amplification — and the
  "except if proven exploitable" carve-out was unreachable because proving it requires the DoS
  testing the program forbids); "CSRF with no or low impact" (killed a form-encoded GraphQL POST
  once testing proved the endpoint rejects the Rails session cookie and only accepts Bearer tokens);
  "data injection from clients to analytics tools" (killed publicly-exposed Stitch webhook tokens);
  "manipulation client-side faking vulnerabilities that are not real server-side" (killed a
  Turnstile bypass); web-archive links "except if showing a still-existing flaw".
- **Zero findings surviving the filter = zero drafts, stated as the limiting fact.** Out-of-scope
  reports get analysts banned from the program ("analysts not following the rules will not be
  eligible"), so staging them is actively harmful. Say what was tested, what was dropped, and the
  clause that dropped it — that is the deliverable, not a draft.
- **When the operator insists on drafting borderline items anyway, stage them UNSENT with bodies
  that claim only what was demonstrated** ("impact not demonstrated; assessment left to your team"),
  attach the full evidence, and put the ban-risk clause quote in the chat reply so the send decision
  is informed. Never upgrade a body's impact language to make a draft look worth sending.

## THE DEEPENING ROUND — CORRECT OVERSTATED CLAIMS IN PLACE

When the operator says "deepen this finding" (or any impact test disproves a claim you already
staged), fix the draft bodies immediately via update-in-place — a staged draft with a dead claim is
a loaded gun:

- Re-run the impact tests that matter: for DoS/amplification claims, measure the curve (1 vs 400
  aliases) and check whether an expensive unauthenticated field even exists; for CSRF claims, prove
  the auth model (send an authenticated query with only the session cookie — `NotLoggedInError`
  means cookie auth is absent and the CSRF chain is dead); for content-type claims, test the full
  matrix (json / urlencoded / text/plain / none / GET) because partial acceptance changes the story.
- Then rewrite the affected draft bodies to state verified behavior + "impact not demonstrated",
  add the deepening evidence as attachments, and update the sha256 manifest. Same draft id, never
  a duplicate.
- Useful side-evidence to capture while deepening: whether the target's OTHER services do the same
  thing correctly (e.g. their second GraphQL endpoint rejected urlencoded POSTs with 415 and blocked
  introspection — an internal inconsistency that strengthens a hardening argument without claiming
  impact), and whether rate limiting demonstrably works (429s observed during scanning undercut
  "no throttling" framing).

## SEVERITY DECISION GUIDE

### Critical (P1)
- Full account takeover of any user without interaction
- Remote code execution
- SQLi with ability to dump/modify entire DB
- Auth bypass to admin panel
- SSRF to cloud metadata → IAM credentials exfil

### High (P2)
- Mass PII exposure (email, phone, SSN, payment data)
- Privilege escalation from user to admin
- SSRF reaching internal services (data returned)
- Stored XSS executing for all users of sensitive feature
- Payment bypass / financial loss without limit

### Medium (P3)
- IDOR on specific user's non-critical data
- XSS on low-sensitivity page requiring victim interaction
- CSRF on important but non-critical action
- Rate limit bypass on OTP (with effort demonstrated)

### Low (P4)
- Information disclosure (non-sensitive, no PII)
- Clickjacking on sensitive action WITH working PoC
- CORS on limited data

---

## SEVERITY SELF-ASSESSMENT

Each YES raises severity:
```
1. Exposes PII / health / financial data of other users?        → +1 severity
2. Allows account takeover or privilege escalation?             → +2 severity
3. Requires ZERO user interaction from victim?                  → +1 severity
4. Affects ALL users (not specific condition)?                  → +1 severity
5. Remotely exploitable with no internal network access?        → baseline for High+
```

---

## DOWNGRADE COUNTERS

| Program Says | Counter With |
|---|---|
| "Requires authentication" | "Attacker needs only a free account — no special role or permission" |
| "Limited impact" | "Affects [N] users / exposes [PII type] / $[amount] at risk" |
| "Already known" | "Show me the report number — I searched hacktivity and found none" |
| "By design" | "Show me the documentation stating this is intended behavior" |
| "Low CVSS" | "CVSS doesn't capture business impact — attacker can extract [X] in [Y] minutes" |
| "Not exploitable" | "Here is the exact response showing victim's data returned to attacker session" |

---

## THE 60-SECOND PRE-SUBMIT CHECKLIST

```
[ ] Title follows formula: [Class] in [endpoint] allows [actor] to [impact]
[ ] First sentence states exact impact in plain English
[ ] Steps to Reproduce has exact HTTP request (copy-paste ready)
[ ] Response showing the bug is included (screenshot or JSON body)
[ ] Two test accounts used — not just one account testing itself
[ ] CVSS score calculated and included
[ ] Recommended fix is 1-2 sentences (not a lecture)
[ ] No typos in endpoint paths or parameter names
[ ] Report is < 600 words — triagers skim long reports
[ ] Severity claimed matches impact described — don't overclaim
[ ] Never used "could potentially" or "may allow"
[ ] PoC is reproducible by triager from a fresh state
```

---

## CVSS 4.0 QUICK REFERENCE (newer programs)

CVSS 4.0 replaced CVSS 3.1 in November 2023. Some newer programs require it.

### Key Differences from CVSS 3.1

| Metric | CVSS 3.1 | CVSS 4.0 |
|---|---|---|
| Attack Vector | Network/Adjacent/Local/Physical | Same |
| Attack Complexity | Low/High | Low/High |
| **NEW**: Attack Requirements | (didn't exist) | None/Present (replaces some PR/UI) |
| Privileges Required | None/Low/High | Same |
| User Interaction | None/Required | None/Passive/Active |
| Scope | Unchanged/Changed | REMOVED |
| **NEW**: Sub-Impact metrics | (didn't exist) | Vulnerable/Subsequent system impact |

### CVSS 4.0 Score Examples

| Finding | CVSS 4.0 Score | Vector |
|---|---|---|
| Unauthenticated RCE | 10.0 | CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H |
| IDOR read PII, auth required | 6.9 | CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N |
| Stored XSS, admin views it | 8.2 | CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:P/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N |
| SSRF → cloud metadata | 8.7 | CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:H/SI:H/SA:N |

### Quick CVSS 4.0 Calculator
```
Use: https://www.first.org/cvss/calculator/4.0
Key fields:
  VC/VI/VA = Vulnerable System Confidentiality/Integrity/Availability
  SC/SI/SA = Subsequent System (downstream impact)
  AT = None (no special condition) | Present (race/specific config needed)
  UI = None | Passive (victim visits URL) | Active (victim takes explicit action)
```

**Practical rule**: If program uses CVSS 4.0 and you don't know the vector, use the calculator and include the full string starting with `CVSS:4.0/AV:...`. Programs cannot dispute a valid vector string.

---

## HUMAN TONE GUIDELINES

**Write to a person, not a system:**
- Triagers are tired. Get to the impact in sentence 1.
- Use "I" not "the researcher" — you found it, own it
- Short paragraphs, bullet points for steps
- Hyperlink relevant docs if needed

**Escalation language (when payout is being downgraded):**
```
"This vulnerability does not require any special privileges — only a free account."
"The exposed data includes [PII type], which is subject to GDPR requirements."
"An attacker can automate this with a simple loop — all [N] records in minutes."
"This is exploitable externally without network access to any internal system."
"The impact is equivalent to a full data breach of [feature/data type]."
```

**Avoid:**
- Jargon the triager might not know
- 5-paragraph explanations of what IDOR is (they know)
- Theoretical chains ("could be combined with X to...")
- Passive voice ("it was observed that...")
- Qualifying language ("seems to," "appears to")

---

## STEPS TO REPRODUCE FORMAT (triager-optimized)

```markdown
**Setup:**
- Account A (attacker): email=attacker@test.com, ID=111
- Account B (victim): email=victim@test.com, ID=222
- Both created via normal registration — no special access

**Steps:**

1. Log in as Account A
2. Send this request (replace `111` with victim ID `222`):

\```
GET /api/v2/resource/222 HTTP/1.1
Host: target.com
Authorization: Bearer ACCOUNT_A_TOKEN
\```

3. Response contains Account B's private data:

\```json
{"id": 222, "email": "victim@test.com", "name": "Victim User", "address": "..."}
\```

**Expected:** 403 Forbidden
**Actual:** 200 OK with victim's private data
```

---

## Related Skills & Chains

- **`triage-validation`** — When deciding whether to write a report at all. Workflow primitive: NEVER open this skill before `triage-validation`'s 7-Question Gate passes; a finding that fails the gate should be killed, not written up.
- **`bugcrowd-reporting`** — When the target is a Bugcrowd program. Workflow primitive: this skill's body template is the foundation; `bugcrowd-reporting` overlays VRT selection, severity-request paragraph, OOS-clause rebuttals on top.
- **`evidence-hygiene`** — When PoC screenshots / HARs are being attached to the report. Workflow primitive: every artifact referenced in the "Supporting Materials" / "Proof of Concept" section gets routed through `evidence-hygiene` for cookie + PII redaction before attachment.
- **`redteam-report-template`** — When the engagement is an external red team (NOT bug bounty). Workflow primitive: confirm engagement mode via `bb-methodology` PART 0; if red-team, swap this skill out for `redteam-report-template` (different audience, different structure: Subject / Observations / Description / Impact / Recommendation / PoC).

---

## Operator Notes (Claude-BugHunter)

> Engagement-derived additions to the vendored foundation. Wisdom from real
> authorized engagements + Phase 2 verification across this repo's 31+
> skill-area live tests. The upstream methodology covers the WHAT; this
> layer covers the WHEN-IT-ACTUALLY-WORKS and the FAILURE-MODES.

### Title formula in practice

`<asset> | <bug class> | <impact>` — three components, no fluff. Triagers read titles in roughly three seconds and use them to order the queue.

- BAD: "Interesting finding on /api/users"
- BAD: "IDOR vulnerability in API"
- GOOD: "Authenticated IDOR on /api/users/{uid} -> admin email + role disclosure"
- GOOD: "Unauthenticated SSRF on /preview?url= -> AWS metadata 169.254.169.254 reachable"

The bad titles get opened last. The good titles get opened first. Same finding, different queue position, different triage day, different payout speed.

### What triagers actually read

Their reading sequence on a fresh report:

1. **Title** (3 seconds)
2. **First paragraph of impact / summary** (15 seconds)
3. **The curl command or HTTP request block** (30 seconds)
4. **Reproduction steps** (only if the first three were convincing)
5. **Everything else** (only on follow-up review)

Optimize the top of the report ruthlessly. Save narrative for the middle. Triagers who are convinced by step 3 will rubber-stamp the rest; triagers who aren't convinced by step 3 won't read step 5.

### CVSS 3.1 vs Bugcrowd VRT vs H1 default severity

These three systems disagree about 30% of the time. The most common gap: a finding that scores CVSS 7.x (High) maps to Bugcrowd P4 (Low) or H1 Medium-default. When the platform default rates lower than CVSS:

1. **File the severity-request paragraph as the first body section.** Bugcrowd respects this. (See `bugcrowd-reporting` for the canonical template.)
2. **Anchor the request in CVSS vector string + business impact, not feelings.** "CVSS 3.1 AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N = 7.5 High because Confidentiality:High applies to cross-tenant data exposure."
3. **Cite the platform's own VRT entry** that matches your finding. Don't argue against the platform; route within it.

An authorized bug-bounty engagement saw P4-default findings escalated to P3 via the severity-request paragraph. The escalation isn't automatic — you have to ask, with grounded reasoning, in the first body section.

### Evidence rotation

Everything in the submission body is logged forever by the platform. Operate accordingly:

- Use throwaway test accounts created specifically for the engagement.
- Rotate cookies / tokens after each submission (don't reuse the cookie that's pasted in the report).
- Never paste production cookies, real user emails, or real PII into the report body — redact in the PoC step.
- Screenshots of admin panels: blur the user list, blur the URL bar if it contains tokens.

Cross-link `evidence-hygiene` for the full capture-and-redact protocol.

### Templates by platform — when they differ

| Platform | Tone | Required Structure | Severity Mechanism |
|---|---|---|---|
| HackerOne | Narrative | Summary -> Steps -> Impact -> Suggested fix | Triager-set, contestable |
| Bugcrowd | Structured | Severity request -> VRT category -> Title -> Body -> Remediation | VRT-default + manual override paragraph |
| Intigriti | Between | Summary -> PoC -> Impact -> Recommendation | Researcher-proposed, triager-confirmed |
| Immunefi | PoC-first | Working PoC code -> Walkthrough -> Impact -> Severity | Foundry/Hardhat code is the primary deliverable |

Picking the wrong template style costs validity. A narrative-heavy Bugcrowd report misses the VRT mapping the triager needs; a structured H1 report reads as terse and gets follow-up questions that delay payout.

### The single biggest report-writing mistake

Claiming an attack works "in theory" or "could be chained to [bigger impact]" without demonstrating it. Triage-validation Q6 (impact beyond technically possible) kills these on the validation side; report-writing has to mirror it on the writing side.

Two valid paths:

1. **Show concrete impact end-to-end.** Capture the chain on a test account. Paste the full request/response sequence. Done.
2. **Downgrade the severity claim to match what you actually demonstrated.** "IDOR on /api/users/{uid} reading email + role" is real and reportable; "IDOR chained to potential admin takeover" is not until you demonstrate the takeover.

Pick one. Never split the difference with "could potentially" or "may allow" — those phrases are the triager's signal that the report is theoretical, and theoretical reports get N/A.
- **`bb-methodology`** — When Phase 5's report-writing step starts. Workflow primitive: Phase 5 calls `/report` which loads this skill for the platform-specific template (H1 / Bugcrowd / Intigriti / Immunefi).

---

## Companion Reference — `bugbounty-playbook` (additive, never overrides)

Extra report-shaping material (mirror of bugbounty.info, 186 pages) lives in the
`bugbounty-playbook` skill. This file's rules (impact-first, no "could potentially",
CVSS that matches demonstrated impact) still govern — the shelf below is for
alternative structures and phrasing:

- `skills/bugbounty-playbook/references/reporting/Report-Templates.md` — full report templates.
- `skills/bugbounty-playbook/references/reporting/Impact-Statements.md` — impact-statement patterns that pay.
- `skills/bugbounty-playbook/references/reporting/Severity-Escalation.md` — escalation ladders (Low→Critical).
- `skills/bugbounty-playbook/references/methodology/Chain-Thinking.md` — how to structure a **chain** report (the "how Step 1 enables Step 2" bridge section).

Read: `skill_view(name='bugbounty-playbook', file_path='references/reporting/Impact-Statements.md')`
