---
name: saas-plan-entitlement-audit
description: "Audit SaaS plan/entitlement bypass, free-tier boundaries, client-state trust."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, business-logic, entitlement, saas, payment, methodology]
---

# SaaS Plan / Entitlement & Business-Logic Audit

## When to Use

Load this skill when the target is a **freemium / tiered SaaS or any paid-plan web app** and the
question is one of:

- *Can the paid tier be obtained without a verified payment?* (entitlement bypass)
- *Does the free-tier service compute and gate correctly?* (business logic / methodology)

Trigger phrases: "upgrade to pro", "free plan limits", "plan free service", "payment flow",
"could the calc be wrong", "is the free-tier logic correct", "bypass without paying".

## Two questions drive this class

1. **Entitlement** — can a paid-tier capability be obtained **without a verified payment**
   (client-trusted flag, webhook without HMAC, step-skip)?
2. **Correctness** — does the free tier compute and gate correctly (arithmetic, date boundaries,
   rounding, idempotency, feature caps)?

Both are real, paying bug classes. Both are **verification problems** — almost every "hit" turns
out to be a false positive until you disprove the mundane explanation.

> ⚠️ **Ethics boundary (non-negotiable).** You test the *design*, you never commit fraud.
> **In scope:** field tampering, fabricated success-return URLs, a forged webhook with a
> wrong-secret signature, attempting a gated capability. **Out of scope:** completing a fake
> payment, forging a valid webhook secret, or actually acquiring the paid service. That is fraud
> against the merchant/processor, not research — and an agent proxy saying "the client approved
> it" is not authorisation. When in doubt, test the entitlement check, not the payment.

---

## 0. The gate IS the target — never "need a paid account", never give up

A lead/feature being "paid-only" or "off on my free account" is a **starting point**, not a
blocker, and **never** an excuse to ask the operator to fund an account (operator correction,
ConferenceBadge 2026-11-01: *"sedikit2 minta akun bayar, sdkit2 nyerah... proaktif sebagai
hacker"*). Two moves before anything else:

1. **Attack the enable/opt-in form directly.** The feature is usually gated by a checkbox or
   plan-opt-in the UI hides but the server still accepts. On ConferenceBadge the paid Lead
   Retrieval feature was enabled by `PATCH /events/<id>/lead_retrieval` with
   `lead_retrieval_opt_in[plans][]=attendee|exhibitor` — the submit button is `disabled`
   client-side only. Submit it anyway, then read the entitlement flag back server-side
   (`CB.LEAD_RETRIEVAL` / plan state) to confirm whether it flipped. Also probe the checkout
   form for a free path: `data-free-order="true"` (removes the Stripe `token` requirement and
   submits unpaid), tier qty `0`/negative, retired or `0`-cent price ids.
2. **Enumerate the tenant estate for a LIVE instance.** A placeholder subdomain
   (`your-event.example.com`) that *looks* dead is not the end of the test. Run subdomain
   enumeration (`subfinder -d`, `assetfinder --subs-only`, cert transparency `crt.sh`) and you
   will often find real tenant subdomains (`<slug>.example.com`) live in production — each a
   separate multi-tenant instance of the paid surface. ConferenceBadge: `dash.` looked closed
   but 8 live event tenants (`cabal-…`, `2026-ala-…`, etc., all titled "Lead Retrieval") carried
   the paid lead-retrieval API (`/api/attendees`, `/api/scans`, `/api/scans/all`) that the
   placeholder never revealed.

The exploit lives in the **gap between the free surface you hold and the paid surface visible
from another tenant** — `/api/scans` (mine) vs `/api/scans/all` (everyone) is the classic BOLA
red flag. Enumerate first, then bypass the entitlement; do not stall on "it's paid".

---

## 1. Entitlement-bypass test matrix

Run all of these; a correctly-enforced design means **every one is negative** (that is a valid,
reportable result — record it as "tested, held", never inflate it).

| # | Test | What a bug looks like |
|---|---|---|
| 1 | Click upgrade → is the plan changed **without** completing payment? | plan flips before the provider webhook |
| 2 | Fabricated return URLs: `?success=1`, `?checkout=success`, `?session_id=PROVIDER_FAKE`, `/<area>/success`, `?upgraded=true`, `?plan=pro` | any of these grants the tier |
| 3 | Tamper plan/price/interval fields on the checkout action | server reads the tier from the request |
| 4 | **Forged webhook**: well-formed signature header, wrong secret | handler accepts it (HMAC not verified) |
| 5 | Webhook with no / malformed / duplicate signature | accepted instead of 400 |
| 6 | Enumerate webhook paths (`/api/*/webhook`, `/api/webhooks/*`, `/api/<psp>/events`) | a second, unprotected handler |
| 7 | Call a paid *capability* directly (not just load its page) | capability works on a free account |

**Expected secure architecture:** upgrade action → provider checkout session → **entitlement set
only by a signature-verified webhook**; success URL is cosmetic; plan never read from the request.
Compare against that model and state exactly which leg failed.

**Known-good vendor shape to compare against** (filetype: freemium UK tax SaaS, 2026-09). Every leg
below came back NEGATIVE — that is the correct result to record, with the exact strings as evidence:

| Leg | Probe | Observed (secure) |
|---|---|---|
| webhook endpoint | `OPTIONS /api/stripe/webhook` | `405` on GET, `Allow: OPTIONS, POST` |
| missing signature | POST event JSON, no header | `400 {"error":"missing signature"}` |
| forged signature | 12 variants: garbage, `t=` only, `v1=` only, `v1=deadbeef`, `v1=64×0`, `v1=64×f`, `t=0`, `v0=` scheme, duplicate `t=`, space-separated, `sha256=` prefix, future `t` | all `400 {"error":"invalid signature"}` |
| fabricated return URL | 10 variants (`?success=1`, `?checkout=success`, `?upgraded=true`, `?plan=pro`, `?session_id=cs_live_fake`, `?subscription=active`, `/<area>/success`, `/pro`, combined) | every one still renders "You're on the free plan" |
| mass assignment | 13 fields injected into the account-update action (`plan, isPro, is_pro, tier, subscription, subscriptionStatus, role, isAdmin, pro, planTier, entitlements, stripeSubscriptionId, paid`) | "Your details have been saved." AND plan still free — all ignored |
| paid capability direct | `POST /api/ai/extract-expense` (route guessed from the client bundle) | `403 {"error":"AI scanning is a Pro feature."}` |
| free cap via real path | the genuine import flow | `"Your plan allows 1 property. Upgrade to Pro to import the rest..."` |
| client-state trust | grep bundle + test for plan/role/tier cookie or localStorage | none read; plan rendered server-side from the account record |
| price/interval tamper | re-submit the billing action with altered fields | **INCONCLUSIVE** — checkout sessions are reused per user, so the price cannot be A/B'd. Say so; do not call it safe. |

Also confirmed on the same target and worth re-using as a baseline: session revocation is real
("signed in on N other devices" → sign out others → second isolated context bounces to /login),
login lockout fires at ~10 wrong passwords (~15 min, correct password also blocked), `/reset`
locks after 5 wrong codes, and the OTP attempt counter leaks as `?codeLimit=N&why=cooldown`.

### 1b. The unauthenticated entitlement ORACLE (read-only BOLA, no payment leg)

A distinct variant from the write/bypass rows above: the entitlement **lookup** endpoint is callable
with **no auth at all** and **trusts client-supplied `tenantId`/`userId`/`appId`** as the identity,
returning tenant-level subscription + administrator identifiers. It is unauth *by design* because the
client calls it from an embed/iframe (Microsoft Teams SSO, a widget) *before* it has its own backend
session — but nothing proves WHO is asking, so it leaks across tenants.

Measured live (Witivio Teams Pro, 2026-11-02): `POST admin.teams-pro.com/teams-app/data`
(body `tenantId=<tid>&userId=<uid>&appId=<id>`) returned HTTP 200 with
`isUserPremium, isUserPlatinum, isUserAdmin, isTenantLicenceAvailable, subscriptionId,
subscriptionLicenceId, subscriptionOwner, admins[], tenantSuperAdmins[]` — no cookie, no header.

Method + the two proofs that move it from "by design" to "reportable":
1. **Product-name mapping proves a real DB lookup.** Submit the same `tenantId/userId` with two
   different `appId`s → the server returns a different `productName` each time. That kills the
   "it's a static stub" defence.
2. **Sibling-endpoint contrast proves the auth gap is exceptional.** Fire the sibling write/lookup
   endpoints on the same host unauth (`/users/licences`, `/access-request`) → `401
   authentication_required`. One unauthenticated lookup next to gated siblings = a genuine
   access-control defect, not the app's intended public surface.

Then be honest about the ceiling: it is **read-only** (mass-assignment of `isUserPremium=true` into
the body is ignored), and it returns **identifiers** (`admins[]`, `subscriptionOwner` = Azure AD
object GUIDs, `subscriptionId`), not emails/names, so the impact is tenant-subscription + admin-ID
disclosure for an attacker who knows a victim's AAD tenant id (discoverable via OIDC discovery for a
known customer domain). Frame as **Medium (CVSS ~5.3, AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)** — broken
access control, not a premium bypass. Do NOT claim cross-tenant data retrieval you did not actually
perform (see the data-handling rules: stop once proven, don't enumerate real tenants).

## 2. Free-tier boundary mapping

The free tier is fully testable at zero cost — map the whole boundary and hunt for a *capability*
that leaks (a page rendering ≠ the feature working).

- **Cap enforcement:** if the tier caps a resource, hammer the create action past the cap — and
  **fire it in parallel** (a check-then-act race can win). Confirm the **server** blocks it.
  See "Race the tier cap through the REAL UI" below — out-of-band replay usually proves nothing.
  - **When out-of-band replay is impossible, race through the real UI.** Many Next.js route
    actions are *bound* to a specific page render: replaying the captured POST later returns
    `500 {"digest":...}`. That 500 is **inconclusive, not a pass** — it proves the replay was
    rejected, not that the cap held. Real method that works: open **N pages in ONE authed
    browser context**, on each page drive the genuine create flow to the point where the form
    is rendered *and filled*, then fire the submit on every page inside a tight loop. Six
    submits inside ~86 ms is enough parallelism to win a naive check-then-act. Count the
    resulting resources afterwards — the count is the verdict.
  - **Never identify the action id from "the first `$ACTION_ID_` on the page".** Every authed
    layout renders a logout action first, and firing it will silently sign you out mid-test
    (symptom: 8 requests return 303, then every later GET lands on `/login`). Take the action
    id from an actually-captured request for the operation you want.
- **Capability, not page:** attempt the real mutation (upload / export / AI call / key creation)
  and read the server's error string.
- **Gate discovery:** auth-crawl the app and read every server-action **name**; `create*Key`,
  `*Export`, `*Upload`, `*Scan*` are prime gate candidates. If no such action exists at all, the
  gate is server-side (correct) — a good negative.
- **Read the gate's field name out of the client bundle, then inject it.** A prop-driven UI gate
  tells you exactly which parameter the server is supposed to be validating. Grep the bundle for
  the conditional that renders the gated control — e.g. a create form destructured as
  `{allowForeign:t=!1}` and rendering a checkbox only when `t` is true gives you the honest field
  name to abuse (`countryCode`, `plan`, `isPro`, `sourceType`, …). Submit that field straight
  into the genuine action through the real rendered form (append a hidden input next to the real
  ones, then click the real submit button so the React binding stays valid). A plan-check that
  returns a quotable refusal ("Overseas property is part of Pro.") is a clean negative; a silent
  success is a plan-entitlement bypass. Do the same with the *settings/update* action, not only
  *create* — an update path that accepts the gated field is the more common hole.
- **UI-hidden enum values are a separate, cheap check.** Many forms hide values the server still
  accepts. Diff the client-filtered list against the server's accepted set: extract every key
  the UI filters out, inject each one as an `<option>` into the real `<select>`, submit through
  the real form, and record the server's response per key. One key accepted out of N is a
  validation-asymmetry finding; all N rejected is a strong positive. Verify acceptance against
  the **export**, not the closed form — a modal that closes is not proof.
- **The UI gate and the REST gate are separate surfaces — test the endpoint even when the page
  hides the feature.** A Pro-only screen that renders nothing but an upgrade prompt still tells you
  the route; the JSON endpoint behind it is often reachable directly and answers with a quotable
  refusal. On Quarterwise (2026-09) `POST /api/ai/extract-expense` on a free account returned
  `403 {"error":"AI scanning is a Pro feature."}` while the free-plan object cap returned
  `Your plan allows 1 property. Upgrade to Pro to import the rest...` from the server action.
  Both gate correctly — that is the negative, and the exact strings are the evidence. Harvest the
  endpoint names from the client bundle (`grep /api/` over downloaded chunks) rather than assuming
  the shipped UI is the whole surface.
- **A hidden action id is itself a (weak) signal, not a verdict.** When a Pro capability exists only
  in the paid bundle, the free bundle contains no `$ACTION_*` id for it, so the action cannot be
  replayed at all. Record 'UI-gated, action id absent from the free bundle, not independently
  replayable' as a coverage note — never as either a pass or a finding.
- **Client-side filtering is a rendering decision, not a control — test gate/allow-list PARITY.**
  Two surfaces, both cheap: (a) a capability hidden behind a client prop (`allowForeign`, `isPro`,
  `featureFlag &&`) — read the prop out of the bundle to learn the exact server FIELD to inject,
  then submit it into the real form; (b) an enum filtered client-side
  (`list.filter(e => !e.nrlOnly)`) — inject the hidden `<option>` and compare the server's
  response across the **whole** enum. A lone accepted value proves nothing; the evidence is the
  **asymmetry** (observed: 3 of 4 flagged categories refused with `"Choose a valid category."`,
  the 4th written and carried into the official export). A success toast ("Settings saved.")
  proves the request was accepted, **not** that the field was honoured — always re-read the
  object. Do not inflate the result: a self-scoped validation gap is P4/P5, not P2.
  Full recipe, harness snippets, observed matrices and severity framing:
  `references/ui-vs-server-gate-parity.md`.

### Billing-action pitfalls

- **Checkout sessions are reused per user, so re-submitting the form cannot A/B the price.** The
  upgrade action may return the SAME open provider session id (`cs_live_...`) no matter what
  `interval`/`plan` you submit, because an unfinished session is still valid. Submitting
  `interval=month` and landing on the yearly page is therefore **not** evidence that the parameter
  is ignored or that the price is client-controlled — it is session reuse. Verify price integrity a
  different way: confirm the checkout URL is provider-hosted and the amount matches the advertised
  tier, and treat the interval test as inconclusive unless you can force a fresh session (only one
  identity, and abandoning does not close the session). Say 'inconclusive', not 'safe' and not
  'vulnerable'.
- A plain `POST` to a Next.js server-action form (urlencoded or multipart instead of the
  `text/plain` JSON body) returns `200` with the full HTML page and does nothing. Always re-read the
  state; the sibling `references/nextjs-server-action-replay.md` in this skill covers the wire
  formats.
- **Beware self-inflicted false positives:** if you name a test object "Second Property", later
  reading "Second Property exists" proves nothing. Count the resources.

### Race the tier cap through the REAL UI (a replay-500 is NOT enforcement)

Bound server actions cannot always be replayed out-of-band, and the failure is silent:

- A React-**bound** form action (rendered with NO `$ACTION_ID_*` hidden input; wire body
  `{"0":"[{},\"$K1\"]", "_1_<field>":"..."}`) replayed later with the EXACT captured headers
  and body returns **HTTP 500 + opaque `E{"digest":<n>}`**. A malformed replay and a *refused*
  action are indistinguishable. Never record "cap enforced" off a 500 — record INCONCLUSIVE
  and re-run through the browser.
- Conversely, a `$ACTION_ID_*` (unbound) form action DOES replay from curl/requests when you
  send `content-type: text/plain;charset=UTF-8`, `accept: text/x-component` and the body
  `{"0":"[\"$ACTION_ID_<hex>\"]", "_1_<field>":"..."}`. Progressively-enhanced GET forms use a
  plain urlencoded POST with the raw field names (`$ACTION_ID_<hex>=""`, plus the others).
- **Harvest the action id from captured traffic** (the `next-action` header), never from the
  page. The first `$ACTION_ID_*` input on an authed page is usually the **log-out** form.
  Firing a parallel burst with it logs you out and returns 303s that read like denials — the
  tell is that every request 303s and the next navigation lands on `/login`.
- Cap-race harness that actually works: one authed browser context, **N pages each with the
  create form already open and filled**, then submit all N in a tight loop (measured 0.086 s
  for N=6). Use a **fresh account with 0 resources** — on an account already at the cap the
  create control is not rendered at all, so the "race" silently tests nothing (observed: 6
  pages all reporting `modal=nobtn`, 0 forms, 0 submits).
- Known-negative baseline worth quoting: free-plan cap 1, fresh account, 6 parallel submits in
  one context → exactly **1** resource created. Cap held.
- Ready-to-run harness: `scripts/ui_cap_race.py` (parameterised selectors; copy and adapt).

### Under high latency / WAF, close the gap with a live runtime test

A scanner that never completes behind Cloudflare is **partial coverage**, not a clean result.
It also produces misleading logs: sqlmap running 25 min with no output was a WAF-induced stall,
and its intermittent 403s were burst/rate artefacts, NOT signature blocking — proven by
re-sending the raw payloads (`UNION SELECT NULL--`, `AND SLEEP(5)--`) which returned HTTP 200
with the NORMAL response. Re-test the raw payload by hand before writing any WAF claim.

### Reporting shape when asked "did you check business logic / compare with our PoC variants"

Deliver a **variant-by-variant matrix, one status per leg** — `DONE (result)`,
`INCONCLUSIVE (reason)`, or `NOT REACHABLE (gate)` — instead of prose. Cite evidence next to
each line. Mark inconclusive legs explicitly and never let one read as "safe". List the legs you
could NOT run (provider-credential-gated API, subscription-gated surfaces) as coverage gaps with
the concrete unlock, not as findings. The user asks for this shape by default.

## 2b. Two test classes this playbook was missing

### 2b-1. Client-side filter vs server-side allow-list
A category/feature can be *hidden in the UI* while the server still accepts it. Hidden-by-default
is the normal shape of this bug, so you will never find it by clicking the UI — you have to
inject the value.

**Test:** render the real page, then inject the hidden value into the control the UI actually
uses, and submit through the genuine form (so the server action binding stays valid):

```js
// category dropdown: add the option the UI removed, then pick it
const sel = document.querySelector('#category');            // or whatever the real id is
if (![...sel.options].some(o => o.value === CATEGORY)) {
  const o = document.createElement('option');
  o.value = CATEGORY; o.text = 'INJECTED'; sel.appendChild(o);
}
sel.value = CATEGORY;
sel.dispatchEvent(new Event('change', { bubbles: true }));
// fill the other required fields, then submit the form containing that select
```

**Always run the full matrix, not just the interesting one.** Findings live in the
*inconsistency*: 1-of-4 hidden values accepted while the other 3 return the same rejection
is the strongest argument that the accepted one is unintentional. Test every sibling value
plus one obviously-bogus control, or you cannot make that argument.

Find the hidden set by reading the client bundle, not by guessing. Look for a boolean flag on
the item definitions plus one filter expression, e.g.
`list.filter(e => !e.nrlOnly)`. Then check whether the app exposes **any** setting that would
legitimately unlock those items — if it exposes none, "hidden for everyone" is the design
intent and server acceptance is a gap by definition.

**Severity discipline:** this is usually LOW and self-scoped. Say so in the finding itself:
it only alters the actor's own records, exposes nobody else's data, grants no entitlement,
crosses no account boundary. `CWE-20` improper input validation, not access control.

### 2b-2. Scalar-without-an-effective-date (calculation correctness)
Freemium SaaS that models anything time-varying usually stores a single scalar where the real
world needs a timeline: ownership share, seats, quota, discount %, tier multiplier. If the
scalar applies to the whole period, any mid-period event is unrepresentable and every
remediation available to the user produces a wrong number.

**Test:** build a dataset that straddles the event, then toggle the scalar and read the
authoritative output:

```
share = 100%  ->  period total  <A>
share =  50%  ->  period total  <A/2>
```

If the pre-event rows scaled too, the scalar is period-wide and the case is proven. Then
quantify the concrete loss: which pre-event rows should have kept the old value, and what
direction the customer ends up taxed/overcharged.

Check the UI for *what is missing*, not just what is present: no date input, no "effective
from", no "sold or transferred on" anywhere in the model. Absence in the bundle is the proof.

**Frame it correctly.** This is product correctness, not security — nobody is attacked, the
customer's own figure is wrong. Report it as a correctness gap with a suggested data-model
fix, and resist promoting it to a financial-impact finding.

### 2c. Retired / unpublished PSP price ids — the "hidden plan" class

A checkout endpoint that takes a price/plan id **from the request** and validates it only
against the payment provider will accept any id still live in the provider account —
including prices retired from the public catalogue. This is a pricing/entitlement bypass
that needs **no payment** to prove, and it is a different bug from the field-tampering row
above (that row is "the server reads the tier from the request"; this one is "the server
accepts a tier that is no longer offered").

**Where the ids come from — they are not secret:**
- `gau` / `waybackurls` on the app host surface archived URLs carrying `?plan_id=price_...`.
  The Wayback CDX API works too:
  `http://web.archive.org/cdx/search/cdx?url=host*&fl=original&collapse=urlkey&filter=original:.*plan_id.*`
- Old ids also sit in client bundles, mobile-app bundles, and archived marketing pages.
- `GET /plans/stripe` **with** a token returns the same set as the public endpoint — it is
  not an enumeration shortcut. Check it anyway and record the parity.

**The test:**
1. `GET /plans/stripe/public` (or equivalent) → the published set.
2. Submit each discovered id to the checkout action. A **fabricated** id returning
   `400 No such price` proves the provider lookup happens — that is the control that HOLDS,
   and it belongs in the report.
3. An id **absent from the published set** but returning `201` + a session URL is the finding.
4. **Read the actual price by rendering the checkout page in a browser.** The amount is not
   in the static HTML — provider checkout is a JS app and a raw fetch returns only country
   lists. Use the FULL session URL including its `#fidn...` fragment; without the fragment
   Stripe answers "This link is incomplete" and you will wrongly conclude the session is dead.
5. Compare against the published price for the same capacity and state the discount
   (observed live: a retired id selling 1024 GB for EUR 1/month against a published
   EUR 699/month, and a second retired id selling 200 GB for EUR 20/year against EUR 1,999/year).

**What makes it a finding rather than housekeeping:** one leftover promo price is a
housekeeping miss; **two ids from two different pricing generations**, both absent from the
catalogue and both accepted through the same endpoint, is a missing control. Always hunt the
second instance — and note whether the second undercuts a tier the vendor *actively sells
today*, which is much harder to wave away than a legacy tier.

**Honesty bounds:** you cannot enumerate the provider account, so you cannot claim how many
unpublished ids remain. Create checkout sessions and **complete none of them**, then say
explicitly that no card was charged and no subscription was purchased. The proved/argued
table must carry "a subscription is actually granted at the discounted price — NOT PROVED,
no payment completed".

**Addendum pattern (use when the first report is already submitted):** a second instance of
an already-reported root cause goes out as an **ADDENDUM**, not a new report — same
recipient, `In-Reply-To` / `References` headers pointing at the original, subject prefixed
`[BUG BOUNTY] Addendum:`. A fresh report on the same root cause risks being closed as a
duplicate and loses the escalation argument. The addendum's job is to change how the vendor
reads the first report (one forgotten price → a systemic gap), so say that explicitly.

## 2d. Adjacent payment surfaces — run these in the same session

The price-id chain above lives next to four other money surfaces. All four came back
negative on Hivenet (2026-10); the *method* is what transfers.

**Schema-discovery battery.** When a checkout/verify endpoint answers `{}` with a generic
"Missing required request body parameters", send one-field bodies for every plausible name
and watch for a *different* error — that difference names the real field:

```
{} / {"code":..} / {"referralCode":..} / {"referral_code":..} / {"receipt":..} /
{"receiptData":..} / {"transactionId":..} / {"originalTransactionId":..} /
{"purchaseToken":..} / {"productId":..} / {"signedPayload":..} / {"transaction":{..}}
```
Found this way: `referralCode`, `transactionId` (Apple), `purchaseToken` (Google). A field
that keeps returning the generic message is not the field.

| Surface | Probe | Observed (control held) |
|---|---|---|
| Apple IAP | `POST /subscriptions/apple/check {transactionId}` | every format → `400 Invalid transaction ID` (format-validated server-side) |
| Google IAP | `POST /subscriptions/google/check {purchaseToken}` | any non-empty value → `502 Google Play API error` — the gateway really calls the Play API and Google rejects the token. Server-side validation proven; **no SSRF** because the upstream is a fixed endpoint |
| Referral | `GET /referral/limits` then redeem a valid code | limits were public (5 bonuses × 1 GB). **The bonus never landed** — capacity unchanged after a valid redeem |
| Referral replay | redeem the same code N times | all `200`, but with no bonus granted there is nothing to double-spend |
| Referral self-referral | an account redeems its own code | `200` — moot for the same reason |
| Subscription lifecycle | `PATCH .../cancel`, `DELETE /subscriptions`, `GET /subscriptions` | `404 Subscription not found` / `204` but the free record survived intact (no-op) / `405` |
| Credits / wallet | `GET /credits`, then POST/PUT/PATCH on every plausible write path | read-only; all write paths 404. Auto-top-up gated behind a prior purchase (`400 Purchase credits before enabling auto top-up`) |

**The referral lesson generalises: confirm the bonus actually lands before claiming
double-spend.** A replay that returns 200 is only a bug if something is granted twice.
Read the capacity/quota field before and after a valid redeem; if it does not move, the
feature is not implemented and replay/self-referral are both moot. Record that as the
negative rather than dressing the 200 up as a finding.

**Minor, worth a line, not a report:** a referral-verify response that returns the
*referrer's* accountId to any holder of the code. The code is 32 random bytes so it is not
enumerable; note it and move on.

**Wayback CDX rate-limits.** Looping the CDX API over many hosts in one command gets you
`Internet Archive: Temporarily Offline` (an HTML error page, not results) for the later
hosts. Query one host per call with a `sleep` between them, and treat an HTML body where
you expected a URL list as a rate-limit, not as "no results".

## 2e. The sibling-route gate — the same paid backend behind a second, ungated front door

Before you touch the payment flow, ask a cheaper question: **which other product surfaces invoke
this same paid backend, and does each of them check the entitlement?** Nothing is forged and no
field is injected in this class — the product exposes a second door and forgot the gate.

Measured live 2026-10-30 (Bankr, AI agent platform):

| Door | Probe on a free account (5 msgs/day, 0 credits, no subscription) | Result |
|---|---|---|
| `POST /agent/prompt` | `{"prompt":"say hi"}` x3 | `403 {"error":"subscription_required"}` - gate fires |
| `POST /webhooks/deploy` then `POST webhooks.<host>/u/<wallet>/<name>` | handler returns `{prompt}`, invoked x3 | `202` each time, three complete agent turns, each wrote a file as `createdBy: agent` |
| usage counter | `GET /user` before vs after | `dailyMessageLimit 5, dailyMessageCount 0` -> **still 0** |

Two bugs in one comparison: the gate is absent on door B, *and* door B's usage is never metered.
Neither the entitlement nor the quota is satisfied, yet the paid capability runs.

Method, in order:
1. **Enumerate every surface that can invoke the backend** from the docs sitemap
   (`/sitemap.xml` maps the whole product in one request) - hunt for *agent, automation, webhook,
   scheduler, app script, cron, chat, CLI, MCP, skill, plugin*. The pricing page only ever names
   one door.
2. **Gate-test each surface independently** and compare the *error strings*. A gate that fires
   returns a specific refusal; an ungated route returns success. Same account, same minute, two
   different answers - that comparison is the finding.
3. **Check the meter separately from the gate.** Read the usage counter, run the capability N
   times, read it again. `count unchanged after N successful paid runs` is what converts "maybe
   intended" into "unmetered". Do this even when the gate *is* present - a gate with a dead counter
   is its own bug.
4. **Prove it with the product doing the work, not your code.** Deploy a handler that takes a
   marker from the request body and asks the agent to write `run-<marker>.txt`; invoke with three
   distinct markers; list storage and show three agent-created files. Three markers = three
   independent turns, non-destructive, and a triager can re-run it.
5. When the handler contract only returns `{prompt}` (no response body), read diagnostics from
   `console.log` -> the vendor's invocation-log endpoint. Use the agent's own file tool for the PoC.

Severity: gate missing + metering missing + free account = **Medium, single tenant**. No boundary
crossed, no funds moved - say so. Per-endpoint rate limits multiply by how many endpoints one
wallet may deploy, so the unmetered use is not bounded by a single route; state that as impact
context, not as a claim of unbounded abuse.

What usually holds and belongs in the report as a negative: IP-allowlist enforcement on the second
door (XFF / `X-Real-IP` / `Forwarded` / `X-Client-IP` / `True-Client-IP` all still 403),
`readOnly` key flag across every deploy surface, and cross-tenant scoping of job/thread/log/file
ids. A vendor's own OpenAPI text claiming a handler skips `readOnly` is **stale documentation, not
a bug** - test it, then report the behaviour you measured. Full recipe, handler source, read-back
channels and the held-controls matrix: `references/sibling-route-gate-and-usage-metering.md`.

### 2e-bis. The WIDGET/EMBED host is a second door too — and it has its own route table

§2e is "a second surface that invokes the same paid backend". The cheapest instance of that on any
product with an embeddable view is the **widget/embed host**: the same resource is rendered through a
separate hostname with a separate front-end bundle and a **separately written authz filter**.

Measured 2026-10-31 (Scribble Maps, `widgets.scribblemaps.com`). Two endpoints existed only in the
widget bundle (`/js/core.js`, 143 KB — versus the 6.4 MB main editor SDK) and in no main-app route
inventory: `/api/maps/{code}/localLastModified` (returns the content hash) and
`/api/maps/{code}/smjsonLocal` (returns the document).

| resource class | document route | metadata/hash route |
|---|---|---|
| public | 200 | 200 |
| password-protected | 401 | **200 — hash leaked** |
| paid | 401 | **200 — hash leaked** |

Method, and it is minutes of work:

1. **Grep the widget bundle, not the app bundle.** The embed bundle is small and its route list is
   short; `/api/` grep gives you the complete second-door inventory.
2. **Fire each discovered route at BOTH hosts, across EVERY access class you hold** (public,
   password-protected, paid, tenant-scoped). The differential is the finding; a single host tells you
   nothing.
3. **Score metadata leaks as observations, not findings.** A content hash for a protected resource is
   not the content. Record it in coverage — its real value is the *negative* it lets you state
   ("the widget host enforces the content gate"), which is coverage a triager cannot get from
   main-app tests alone.
4. **Embed parameters are not a bypass.** `id`, `password`, `pw`, `plan`, `admin`, `secure`, plus the
   widget's own flags, were all tried against a password-protected resource: no parameter unlocked
   content and no resource data was inlined into the widget HTML. That is a clean negative worth
   writing down.

**Scope corollary that will otherwise bite you:** the widget bundle also referenced a **separate
domain** (`scribblemaps.io`, a tile server) that the program's published host list does not name.
Probe it passively at most, and report nothing from it. Before touching any host a bundle names,
check it against the policy's host list — "the product uses it" is not "the program covers it", and
reporting an out-of-scope host ends the engagement.

### 2e-ter. A rate limit your OWN probes tripped is a disclosure obligation

Probing a one-shot submit endpoint to learn its field names tripped a per-IP throttle
(`429 "You've submitted too many reports recently"`) that blocked the real submission for ~40 min.
Two rules:

1. **Never dry-run a one-shot submit endpoint.** Read field names from the form HTML + the page's own
   JS. A single validation failure is enough to burn the budget — 6 deliberately-incomplete payloads
   cost 40 minutes of blocked submission.
2. **Disclose the self-inflicted throttle in the deliverable**, not just in your notes: "a handful of
   deliberately-incomplete dry-run requests, all rejected by validation, none creating a report,
   tripped this endpoint's per-IP rate limit — which is why this arrived by e-mail." Unexplained 429s
   from your IP read as abuse.

Same obligation for every state-changing probe that leaves a trace on the vendor's billing or
anti-abuse systems — an orphan payment-processor account, an unpaid subscription record, a tripped
limiter. One sentence each: what was created, its state (unverified / inactive / no balance), and that
the vendor may delete it. See §2g for the provisioning case.

## 2f. The FORMAT-endpoint gate — entitlement enforced on the viewer, absent on every export

§2e is "a second door to the same backend". This is the same idea one layer down and much cheaper to
test: **one resource, N serialisation endpoints, and only some of them consult the entitlement.** Any
product that can render a gated resource can also export it (`raw`, `json`, `base64`, `kml`, `geojson`,
`csv`, `gpx`, `pdf`, `zip`), and the export routes are the ones written early and never re-gated.

Measured live 2026-10-31 (Scribble Maps, "Sell Access" paid maps):

| door | anonymous result |
|---|---|
| `GET /api/maps/paidsample` (metadata) | `200` - `isPaid:true`, `hasPassword:false` |
| `GET /api/market/defaultPlans/paidsample` | `200` - `free:false`, `allowCopy:false`, USD 199 one-time / 19.99 mo / 99.99 yr |
| `GET /api/maps/paidsample/raw` | **`200`, 16,908 B - the whole map, all overlays** |
| `/smjson`, `/smjsonbase64`, `/lzsbase64`, `/kml`, `/geojson` | **all `200`** |
| `GET /api/maps/images/800/600/paidsample.png` | `401` - the renderer *does* gate it |
| `GET https://api.scribblemaps.com/api/maps/paidsample/raw` | `401` - the sibling HOST gates it |
| control: password-protected ("Secure") map, same 6 routes | `401` on all six |

Four independent proofs that the gate is *meant* to exist - assemble at least two before writing:

1. **The renderer/image route gates it** while the data routes do not. Same resource, same host.
2. **A sibling host gates it.** Identical path on `api.` answered `401 application/problem+json` while
   `www.` served the file - one front door has the filter, the other missed the route.
3. **A sibling CLASS of the same resource gates it.** The password-protected map returned `401` on all
   six endpoints, so the endpoint family is capable of refusing; it just consults the password flag and
   never the paid flag.
4. **The product's own bundle stores paid maps in the secure state.** Grep the editor SDK for the save
   branch - `"paid"==d&&(a.listed=!1,a.secure=!0)` - i.e. the client treats paid as a protected state,
   while the backend's data routes read only `hasPassword`.

**Method (run before the payment flow, it takes minutes):**

1. From the bundle/route inventory, list **every serialisation suffix** the resource supports. Grep for
   `raw|smjson|lzs|kml|geojson|export|download` and for the SDK's own route table
   (`"maps/{mapCode}/raw"` style literals) - those tables are the complete list.
2. Pick a resource the vendor **owns and publishes as gated** (their own demo paid map, their sample
   premium report). Never a third party's.
3. Sweep all suffixes **anonymously**, plus the metadata route so you can quote the entitlement fields
   (`isPaid`, `free:false`, `allowCopy:false`, price plans) in the same report.
4. Run the control: a resource of the *same type* known to be gated (password/private/tenant-scoped).
   If that also leaks you have a different, bigger bug; if it holds, you have the differential.
5. Repeat the sweep on the **sibling API host** - a `401`/`200` split between `www.` and `api.` is the
   single strongest artefact in the report.
6. Validate 3x with different User-Agents and hash the bodies; identical SHA-256 across runs kills the
   "cache/state" objection before the triager raises it.

**Severity framing.** This is Confidentiality against the paying customer, not a payment bypass:
`AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` = 7.5 when the content *is* the product. Say explicitly that no
purchase flow was tampered with and nothing was forged - the paywall simply never runs on that route.
`allowCopy:false` plus a leaked `kml`/`geojson` is the impact sentence: those are the two formats that
make the content re-publishable, which is exactly the capability the owner disabled.

**Do not overclaim the population.** You can prove one vendor-owned resource and the *mechanism*; you
cannot claim "N paid maps are exposed" without sampling, and sampling ids means touching third-party
content - say "affects every paid map saved without a view password, because the route checks only the
password flag", and label it argued-not-measured.

Full probe matrix, the gated-sibling table and the coverage negatives: `references/paid-content-export-endpoint-gate.md`.

## 2g. Provisioning probes create REAL objects — record the side effect

"Can I mint my own gated resource?" means calling provisioning endpoints, and some of them succeed *for
real*. Measured 2026-10-31 (Scribble Maps seller flow, free account):

| probe | result |
|---|---|
| `GET /api/market/is-seller` | `false` |
| `POST /api/market/add-paid-map` (own map, plan 1999c/mo, `allowCopy:false`) | `200` body `false` — not applied |
| `POST /api/market/create-account` | `200 {"account":"acct_..."}` — **a Stripe Connect account now exists** |

Rules that follow:

- **Prefer a vendor-owned demo resource over self-provisioning.** The same target publishes its own paid
  demo map (`paidsample`); proving the leak there is stronger than any test account, touches no third
  party, and cannot be waved away as "your object was misconfigured".
- **Never complete KYC/KYB to unlock a paid surface.** If the price of self-provisioning is identity
  verification, that leg is `NOT TESTED (locked behind KYC onboarding)` — a coverage gap, not a finding,
  and not a reason to invent documents.
- **Disclose the artefact you created.** An orphan provider object (Stripe Connect `acct_...`, an unpaid
  subscription record, a shell workspace) exists after the test. Name it in the report notes and state it
  is unverified, inactive, holds no balance, and can be deleted by the vendor. Failing to disclose reads as
  sloppy handling of their billing system.
- **Idempotency is a control, not an invitation.** `create-account` returned the SAME `acct_` on a second
  call, so the probe is repeatable — still stop at one, and never fire it from more than one identity.

## 2h. A cross-tenant "negative" taken without tenant context is an INVALID run

Same session, team app: account B (no team of its own) called `GET /api/users?teamCode=<A's team>` and got
the SPA **login HTML with HTTP 200**; `POST /api/user` with A's `teamUserId` also returned login HTML.
Reading that as "authz holds" would have been wrong — the request never reached the authorizer, because the
session had no valid tenant context.

- **Tell:** a JSON API answering `200` with `text/html`, or a body that is the app shell/login page.
  Also `302` → `/login`. That is INVALID, not negative, and must be re-run.
- **Fix:** give the second identity its own tenant first. Self-service team creation usually works on a
  free plan (`POST /api/teams {name,description}` → new `teamCode`, account becomes Owner), then replay the
  cross-tenant call.
- **Always run the owner control in the same minute.** Owner `POST /api/user` on its own record returned
  `200` **JSON** and the change applied; attacker got HTML and the record was unchanged on re-read.
  That pair proves both "the endpoint works" and "the boundary holds". Without the owner control you cannot
  distinguish a real negative from an endpoint that is simply a no-op.
- Applies to every multi-tenant SaaS surface keyed by a tenant selector (`?teamCode=`, `?orgId=`,
  `X-Tenant`): a control that fires only when the caller *has* a tenant is not the same control as one that
  refuses a foreign tenant.

## 3. Business-logic / methodology verification (prove with ground truth)

Do not eyeball the UI — pull the **authoritative export** (xlsx/csv/json) and compare to what you
submitted. See `references/accounting-app-logic-checks.md` for the tested pattern.

- **Precision:** store in minor units; assert `0.01 × 3 == 0.03` exactly (no float drift).
  A net figure must equal income − expenses to the penny.
- **Boundary dates:** probe the taxonomy's period edges with **unique values** per case, then read
  back which bucket each landed in. Off-by-one at a period boundary is a classic, high-impact
  methodology bug — and its *absence* is a strong positive result.
- **Idempotency:** replay a submission id / capture token; duplicates must dedupe.
- **Input validation:** test type-vs-category mismatch, unsupported precision, empty/oversized/
  negative/NaN/Unicode values, and injection-shaped strings. Lenient-but-correct parsing
  (`1,000.00`, `£100`, padded spaces) is a *hardening note*, not a bug.
- **Locale/ID validators:** national-insurance / tax / VAT-style IDs should be shape-validated.
  Confirm a plausible-but-fake value is *format*-accepted (registration is a separate,
  provider-side gate — accepting the format is not the bug).

## 4. Tooling discipline — a tool only counts if it was *aimed*

A lesson worth more than any single finding: **running a scanner is not coverage.** A pass that
"ran nuclei/sqlmap/dalfox and found nothing" is worthless if the tools were pointed at the root
page or a static asset instead of the real, parameterised, authenticated surface.

- **Point every tool at the real sink.** `sqlmap -u https://target/` → "no parameter(s) found"
  tested *nothing*. Real targets for `sqlmap`/`commix`/`dalfox` are **parameterised authed** URLs
  (`?ty=…`, `?id=…`, API endpoints) with the session cookie attached.
- **Verify each tool actually executed.** Read the tool's own log/evidence file. Classic silent
  failures: `dalfox <url>` (wrong CLI — needs `dalfox url`/`dalfox file`), `CORScanner --headless`
  (arg rejected), `SSRFmap` without `-r/-p` (refuses), a scanner pointed at a `gov.uk` link lifted
  from page content (out of scope). "EXECUTED" in a tracker ≠ a scan that produced results.
- **Authenticated scanning is mandatory** for tiered SaaS: pass `--cookie`/`-H "Cookie: …"` so the
  scanner sees the real app, not the login redirect.
- **If the user asks "did you use all the tools / all the variants?", the honest answer is often
  no.** Say which ran, which silently failed, and re-run the failures *correctly* — don't defend a
  thin pass.
- **Finish stalls on high-latency/WAF targets**: a dalfox/nuclei authed scan may never complete
  behind Cloudflare. Treat that as **partial coverage** and close the gap with a live browser
  runtime test (navigate to the payload URL, read a sentinel), then say so in the report.

## 5. Anti-false-positive discipline (the core skill here)

Every promising signal in this class had a mundane explanation. Kill it before you report: Kill it before you report:

| Symptom | Cheap disproof |
|---|---|
| "free-tier cap bypassed" | count the resources; the "extra" was the first one, mis-named by you |
| "LFI / SSTI / XSS via a query param" | use a **unique** marker and require *file content*, *arithmetic evaluation*, or *raw* markup — a reflected string in an RSC/flight payload or an escaped literal is not a sink |
| "unauth data export returned 200" | check content-type + final URL: a 200 HTML body that is the SPA shell after a 3xx→/login is not a leak |
| "page still shows the entries" | pagination / display truncation ≠ data loss — confirm against the export |
| "forged webhook accepted" | re-check the status code; 400 `invalid signature` is a **pass** |
| "formula/CSV injection in an export" | **check every sibling export path and the cell/field TYPE before claiming it.** See the hard-won lesson below — this is the easiest false positive in the whole class. |

### Resource-quota / limit-field "bypass": characterize the enforcement, then decide (operator correction, djangoeurope 2026-10-24)
A panel that lets a tenant create sub-resources with client-supplied `limit_*` fields (RAM/disk/procs)
looks like a quota bypass the instant you POST above the plan. Before claiming it, characterize the
enforcement — the operator will challenge it as by-design, and they are often right:
- **Find the exact cap and its basis.** Binary-search the field. If `=64` and `=100` are accepted but
  `=128` is not, the ceiling is a fixed global / the physical server's capacity, NOT the plan — the
  real observation is that the plan quota is never consulted.
- **A field with NO validation is a free-form allocation input, not a security control.** Zero
  clamping is evidence of a user-set hint, not an enforced boundary; a real quota control rejects or
  clamps.
- **Entertain the benign model.** Group `limit_*` may be the plan TOTAL carved across `limit_users`,
  or a per-user default — either makes a higher per-sub-resource value the intended mechanism, not a
  bypass.
- **Before downgrading, try the CONTROL-ACCOUNT DIFFERENTIAL — it settles the question.** This section
  was written on the assumption that black-box field-tampering cannot distinguish a *free-form allocation
  hint* from an *enforced-but-wrong quota*. On djangoeurope 2026-10-25 the same target was settled
  **deterministically** with one extra step, and the answer inverted the earlier guess. Method:
  1. Create **two** sub-resources in the **same parent** on the **same host**: one *with* the
     client-supplied `limit_*` values, one **control** with those fields omitted.
  2. Log into the underlying host and read what the OS actually enforces on each — never the API echo.
     For Linux user-slice hosting: `ulimit -u`,
     `cat /sys/fs/cgroup/user.slice/user-<uid>.slice/memory.max`, `quota -s`.
     Analogues elsewhere: container `--memory`/`--pids-limit`, per-role DB `GRANT`/`max_connections`,
     mailbox byte quota.
  3. Compare **control vs overridden**. Measured here: control `memory.max` 2147483648 (2 GiB, exactly
     the X12 plan) vs overridden 17179869184 (16 GiB); `ulimit -u` 450 vs 2050; disk quota none vs 500G.
     Control == plan and overridden == multiple of plan means the client field is the cause. That is an
     enforced plan bypass, not a hint, and not by-design.
  4. **Probe the update path as well as create.** They often enforce different rules. Here `POST`
     validated *nothing* (500 GB accepted against a 100 GB global ceiling) while `PATCH` rejected
     anything past the **global absolute maximum**, answering `Max RAM limit is 16GB` /
     `Max nproc limit is 1600` / `Max disk space limit is 100GB`. That 400 is the strongest artefact in
     the report: the validator exists, knows how to refuse, and consults a fixed ceiling instead of the
     paid plan. Reporting only the create path throws it away.
  5. Check whether the plan-holding parent is protected: `PATCH /systemgroup/` returned 200 but was
     **silently ignored on read-back**. Stating that pre-empts the obvious vendor answer
     (that-is-how-allocation-works) by showing the gap is precisely the per-user path.
  6. **Find the sibling quota that IS enforced — it is the sharpest framing device.** On the same group
     `limit_users` (a COUNT) *was* enforced: with a limit of 5 and one user already present, creations
     2-5 succeeded and the 5th extra was refused with
     `SSH user count limit reached. Create a new group or upgrade the plan.` That single comparison turns
     "all quotas are fake" (which a vendor reads as by-design and closes) into "this one field family was
     missed while its sibling is enforced" — a defect claim the vendor cannot wave away. Always probe the
     count-shaped sibling alongside the resource-shaped ones, and put both results in the report.
  **Do not exercise the excess** — filling 16 GiB or 500 GB on a shared node hurts other tenants. Caps
  on sibling slices under a 2 GiB parent do not aggregate, so keep the aggregate-availability angle
  **argued, not measured**, and label it that way in the write-up.
- **Be ready to downgrade.** If intent is unprovable black-box and the operator pushes back, do NOT
  ship a "Medium bypass." Downgrade to a neutral vendor question ("intended free-form allocation, or
  a hard quota?"), delete the vuln-framed report, and let the vendor classify it. A clean question to
  a good-faith vendor beats a bounced overclaim. Full case + disclosure recipe:
  `authed-webapp-audit/references/djangoeurope-v2-quota-bypass-and-disclosure.md`.

### The formula-injection false positive (cost a whole finding)
The tempting observation is: *"input `=2+2` comes out raw in the export, therefore injection."*
That conclusion was wrong, and acting on it would have been a padded report.

Two things make raw output **non**-exploitable, and you must check both:

1. **XLSX: raw string ≠ formula.** A cell written as a shared string (`<c t="s"><v>N</v></c>`
   pointing at `<si><t>=2+2</t></si>`) is read by Excel as *text*. Only a formula-typed cell
   (`<f>=2+2</f>`) evaluates. So confirm: does the sheet contain any `<f>` elements at all?
   Count them. `0` means the value is inert regardless of its content.
2. **CSV: the guard usually exists on the *other* path.** Before claiming injection, test the
   guard's completeness across leading characters, and parse the file with `csv.reader`
   rather than eyeballing it — eyeballing a quoted field whose first byte is `"` looks like
   the guard is missing when the apostrophe is correctly the first character of the *content*.

Guard-completeness matrix to run (drive the value through whatever user-controlled field
lands in that export, then read the file back):

```
=1+1      -> '=1+1      guarded?
+1+1      -> '+1+1      guarded?
-1+1      -> '-1+1      guarded?
@SUM(1)   -> '@SUM(1)   guarded?
<TAB>=1+1 -> ?           guarded?
<CR>=1+1  -> ?           guarded?
=cmd|'/C calc'!A0       -> ?   (DDE)
=HYPERLINK("http://x/","c") -> ?   (contains quotes AND commas — quoting trap)
```

A product that guards `=`, `+`, `-`, `@` and control characters, and quotes correctly, is
**done** — downgrade the item to "verified mitigated", state that you could not achieve
execution on any path, and leave only a defence-in-depth note (hoist the guard into the data
layer so all exporters inherit it). Padding that into a bounty-grade finding costs the whole
report its credibility, and the honest negative is itself worth telling the vendor.

Corollary: **downgrade in writing.** Leave the corrected verdict in the report body and a
"FINAL VERDICT" block, don't quietly delete the earlier claim — the user needs to see the
reasoning changed.

## 5. Reference files

- `references/x402-and-hosted-sandbox-boundaries.md` — two "the vendor runs it for you" surfaces:
  the x402 payment-gate tamper matrix (sign EIP-3009 `TransferWithAuthorization` with a
  **zero-balance** throwaway key and send `value:0` / recipient-swapped / sign-1000-declare-0 /
  version-downgrade in the `X-PAYMENT` header — secure answer is four *distinct* rejection
  reasons, which is what proves each field is checked independently), and the hosted-serverless
  sandbox boundary probe (shell out, then test `169.254.170.2` ECS creds, `169.254.169.254` IMDS,
  `127.0.0.1:9001` Lambda runtime, `/proc/1/environ` — `000` everywhere means isolated and is a
  strong negative). Rule for both: report the **boundary**, not the primitive.
- `references/nextjs-server-action-replay.md` — replaying Next.js 14/15 Server Actions for real
  (required headers, router-state-tree, `_1_` field naming, capturing the app's own request), plus
  the RSC-reflection false-positive guard.
- `references/accounting-app-logic-checks.md` — ground-truth export verification, tax-year/period
  boundary matrix, integer-penny precision, idempotency, and the auth-hardening observations worth
  mentioning to the vendor.
- `references/excel-csv-injection-verification.md` — the CWE-1236 verification recipe: test every
  export path, prove XLSX cells are text-typed (0 `<f>` elements) before claiming anything, and
  test the CSV guard's completeness (`= + - @ TAB CR`) by parsing with `csv.reader` instead of
  eyeballing. Use it to decide "verified mitigated" honestly rather than shipping an overclaim.
- `references/uk-property-tax-rules.md` — condensed UK rules to check a bookkeeping/MTD product
  against: FHL abolished 6 Apr 2025, MTD thresholds and the 7 Aug/7 Nov 2026 update dates, cash
  basis as the property-income default plus the £150,000 cash-receipts ceiling, Form 17 / 50:50
  joint-ownership default, 6 Apr–5 Apr boundaries, and the scalar-ownership-share defect.
- `references/tax-software-compliance-review.md` — reviewing a tax/accounting app's calculation
  logic against current law: which claims to verify externally, which controls were verified
  correct, how to test gated features, and how to write the result without overclaiming.
- `references/uk-property-tax-compliance-review.md` — UK rule checkpoints (MTD dates/thresholds,
  FHL abolition, cash basis + the £150,000 ceiling, Form 17 beneficial split) with the test for
  each; the ownership-share-is-not-date-effective test; the Pro-gate-via-injected-field-name
  method; and the "raw value in an exported file is not a finding until you check the sink"
  rule with the `csv.reader` parsing trap.
- `references/paid-content-export-endpoint-gate.md` — §2f worked case: the paid resource gate that the
  viewer and image renderer enforce but every export format misses, the four intent proofs (renderer,
  sibling host, sibling resource class, client bundle), how to mint your own gated resource when the
  save API is undocumented (two-step `stream/new` → `stream/`), and the false-positive guards
  (unlisted-is-OOS, 409 conflict, stale `hasPassword` on legacy rows).
- `references/ui-vs-server-gate-parity.md` — testing whether the server enforces the gate/allow-list
  the client merely *renders*: feature-gate prop → gated-field injection, enum allow-list parity
  across the whole set, the inconsistency-as-evidence rule, and severity framing for self-scoped
  validation gaps.
- `scripts/ui_cap_race.py` — re-runnable cap-race harness: N pages in one authed context, create
  form pre-opened and filled, all submits fired in a tight loop, resource recount + verdict.
  Refuses to run on a stale session or an account already at the cap (both of which silently
  produce a meaningless "0" result). **Windows/MSYS gotcha:** pass URL-ish args with
  `env MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'` *per command* — a bare `/app/...` argv gets
  rewritten to a `C:/...` path before Python sees it. Do **not** `export` those globally: an
  exported `MSYS2_ARG_CONV_EXCL='*'` later mangled an unrelated `$PWD` into `D:\d\data...`.

## 6. Reporting

- Findings need **demonstrated attacker impact** (funds / data / entitlement actually obtained).
  A well-built entitlement gate is a **negative** — say so plainly; do not pad the report.
- **Label correctness defects as correctness defects.** Tax/accounting, pricing and
  business-rule problems ("a transfer mid-year cannot be represented", "no £150k ceiling
  check", "a UI-hidden category the server still accepts") are real and worth reporting, but
  they are *product correctness*, not access control. Keep them in a separate section, state
  the impact precisely ("the taxpayer's figure is wrong and the shortfall falls on them"),
  and do not dress them up with a CVSS vector that implies a boundary crossing. Mixing the two
  is what makes a report get rejected as overclaimed.
- Where a category/field is hidden in the UI but accepted by the server, the strongest
  argument that it is a bug is **inconsistency**: prove it by testing the sibling fields that
  share the same flag. 1 accepted of 4 rejected with the same error message is a defect
  argument; 1 accepted of 1 is a design question.
- State coverage gaps honestly (e.g. provider-credential-gated flows you legitimately cannot pass).

### Separate "security finding" from "product correctness" in the report itself
This class of audit reliably turns up defects that are *real* but are **not security
vulnerabilities** — the tax/accounting logic computes something wrong, or a data model cannot
represent a legitimate case. They have no attacker, no boundary crossed and no other user
harmed, so they are not bounty findings, but they are exactly what a vendor wants to hear.

Structure the deliverable so the reader cannot mistake one for the other:
- A **summary table with separate `Type` and `Severity` columns**, filled in BEFORE the detail
  sections — `Server-side validation gap / Low` next to `Tax calculation correctness / Product
  correctness`.
- Put the sentence *"I do not consider these to be security vulnerabilities"* in the **opening
  paragraph**, not in a footnote. A reader who stops after paragraph one must not come away
  thinking you claimed five vulns.
- For each non-security item, give the rule, the reproduction, the **user-side impact**, and a
  suggested fix — it reads as product feedback rather than a demand.
- State the boundary of every finding explicitly ("self-scoped: it only affects the account that
  creates the entry; no cross-account boundary is crossed"). That sentence is what keeps a P5
  from being read as a P2.

**A high-value correctness class to probe on any stateful financial/lifecycle model: does the
model have a DATE dimension for the thing that changes?** Quarterwise stored ownership share as
a single per-property number (`name="percent"`, in basis points) with **no effective date**, so
a property changing hands mid-year could not be represented: setting 50% halved the *entire*
tax year including months owned 100%, and the UI copy confirmed it ("you file your 50% share
with HMRC"). Whole-year-scalar where a period is required = a defect you can prove
arithmetically from the export, with no exploit needed. Look for the same shape in:
ownership/beneficiary splits, plan or price changes, tax-residency changes, rate changes,
address of record, and any "share of X" field.

Related correctness probes worth a run on a tax/accounting product: is there a ceiling or basis
change the model never checks (e.g. a cash-basis receipts limit that forces accruals above a
threshold — Quarterwise accepted £254,878 of receipts with no warning), and does the product
handle a statutory declaration/ election it silently assumes (e.g. a jointly-owned-property
split that HMRC treats as 50:50 in the absence of the required form)?
  pass). Name the gate ("Pro plan", "live Government Gateway authorisation", "the feature is
  Pro-gated server-side and I proved it") so the reader can judge.
- Info-only observations worth a one-line mention (not bounty-worthy): lenient numeric parsing
  (`1,000.00`, `£100`, padded spaces — correct, just notable), out-of-period dates accepted
  when handled correctly downstream, unhandled 500 on absurd input with an empty body,
  device-fingerprint/telemetry fields posted client-side (untrustworthy for security decisions,
  privacy note only), and soft-404s (unknown API paths returning 200 + the SPA shell).

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/entitlement-trust-testing/PLAYBOOK.md` — differential client-state testing when a
  client-set flag unlocks member entitlements: the four server-side entitlement legs (break the
  payment webhook, fabricate return URLs, mass assignment on profile actions, prove the plan is
  server-rendered), plus wire-format recovery from SPA bundles. Use it when the bypass is
  "poison the client state" rather than "cross the plan boundary".
