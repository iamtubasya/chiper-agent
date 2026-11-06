---
name: artifact-backed-claims
description: "Claim discipline: artifact-backed proof, controls, negative and coverage claims."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [verification, evidence, bug-bounty, reporting, discipline]
    budget_kb: 20
---

# Artifact-backed claims

A finding is not what you concluded. It is what someone else can reproduce from the
artefacts you left behind.

This skill governs the moment between "I observed something" and "I told the operator or
the vendor what it means". Most bad reports and most wrong conclusions die here.

## When to Use

Load this skill when:

- You are about to state a technical finding, confirm one, or write it into a report.
- The operator asks for proof, asks "ad sampelnya?", or says your claim "cm kamu tulis aja"
  (that was just you writing it).
- You are about to conclude something is **not** reachable/exploitable — negative results
  need controls too.
- A finding's artefact might belong to a party outside the engagement target.
- You are about to claim impact beyond what the raw response actually shows.

Do NOT use for exploratory recon notes with no claim attached.

## The two rules

### 1. Every claim carries a re-runnable artefact

When the operator asks for proof, a written summary of what you found is **not** proof.
They said it plainly after a bucket finding was described in prose only:

> "td itu cm kamu tulis aja" — that was just you writing it.

Deliver, together:

| Artefact | Why |
|---|---|
| The raw response / file itself (attachment via `MEDIA:<abs path>`) | They can look at it without trusting you |
| The exact command that produced it, copy-pasteable | They can re-run it and get the same bytes |
| `sha256` of each retrieved file | Ties the artefact to the transcript; catches drift between capture and report |
| A saved transcript file (`evidence/PROOF-<topic>.txt`) | Survives the chat; re-runnable months later |

A claim in chat with none of the above is a draft, not a finding. Label it as such
("observed, not yet evidenced") rather than stating it as fact.

### 2. Every claim ships with the control that kills the boring explanation

Before believing an anomaly, ask what mundane thing would produce the same observation —
then test that. A signal without its control is not evidence.

- **Encoding control** — if a probe 404s, re-probe one case with the naive/obvious input.
  A `%2F`-encoded object key returns 404 while the plain path returns 200; the bug was the
  probe, not the bucket. See `references/negative-controls.md`.
- **Blanket-cache control** — a listing that appears open must return 404 for a random
  key, or it is a catch-all responder, not an exposure.
- **Ownership control** — a name matching your target is not ownership. Attribute from
  content or explicit config, never from the name.
- **Population control** — if you invented the input set (guessed IDs, guessed
  addresses), an answer about it says nothing about the system. Confirm identifiers came
  from the system itself.

## Never claim content you did not read

A folder was named `driving_licence_user`, so it read like a KYC leak. The retrievable
files were a stock photograph and a chat-app export. Asserting "customer licences are
exposed" would have been false on the evidence.

State the reachability you proved and stop:

> "objects under a folder named `driving_licence_user` are publicly retrievable (HEAD 200,
> N bytes, image/jpeg, JPEG magic bytes verified); I did not read their contents."

Fingerprinting substitutions that satisfy the proof requirement without opening the
document: `HEAD` (status, size, ETag, type) plus a **4-byte `Range`** for magic bytes.
That is the minimum that demonstrates reachability and stays inside the usual
safe-harbour clause ("do not access data beyond what is needed to demonstrate the issue").

## "Real user data" is a claim — fingerprint the dataset before you make it

The most expensive overclaim in this class is not a wrong status code; it is calling
**demo/test data** "real user data". Severity, impact statement, and the vendor's triage
time all hang off that one word, and it is checkable from the data itself before you
draft anything.

Run these fingerprints on any dataset obtained through an unauthenticated read:

| Fingerprint | What it means |
|---|---|
| **Default SDK identifier format** — `user_<32hex>`, `user_<uuid>` | The platform's own SDK mints these for anonymous/demo sessions. Real tenants usually carry their own ID scheme. |
| **Canonical demo payload shape** — `{createdAt, id, text, type:"default"}` | Matches the vendor's published sample payload verbatim. |
| **Garbage content** — "ddd", "hase", "sdasdasd", repeated single chars | Keyboard-mash from someone clicking through a demo, not conversation. |
| **`default` channel carrying `type:"default"`** | The SDK's out-of-the-box channel. |
| **Zero occupancy on presence** | Nobody is on it. A production moderation channel with real traffic almost never reads empty. |
| **Isolated, not fleet-wide** | Sweep every sibling keyset/host you hold. One asset leaking while N siblings return 403/empty points at a demo asset, not a systemic gap. |
| **Host is a demo/marketing surface** | `demo.*`, `moderation-dashboard.*`, `example.*` — and re-read the program exclusions for "demo apps / test / sandbox environments". |

**Measured miss (PubNub, 2026-10-31).** An unauthenticated history read returned ~70
messages with 9 "user" UUIDs and was filed **High (7.5)** as *"real user chat history"*.
Every fingerprint above fired. The operator caught it with one question — *"Ini bukannya
data public?"* — and the severity had to be withdrawn. The check costs one sweep and ten
minutes; the retraction costs the vendor's triage time and your credibility on the
findings that were real.

**Rule:** before the words "real user" appear in a report, the dataset must fail *every*
fingerprint above. If any fingerprint fires, either prove production provenance
(tenant-specific IDs, non-default channel names, live occupancy, fleet-wide exposure) or
downgrade to Informational and ask the vendor to confirm the asset class. This is the
public-by-design reflex — *call the front-end's own unauthenticated route and compare* —
applied to the **content** rather than the endpoint.

Corollary that saves the finding: **the write may be reportable where the read is not.**
On the same run, a second keyset returned **403** on history read while accepting
unauthenticated publishes with **200**. PAM configured for read and absent for write is an
authorisation omission, not a demo default, and it survives the "public subscribe key"
argument because the same key is already gated for reads. Before dismissing an unauth read
as by-design, test the write.

## A field that is PRESENT but NULL inverts your verdict

After a vendor fixes an issue, the security-relevant field often does not disappear — it becomes
`null`. A presence check then reports the exact opposite of the truth:

```python
"token" in body          # True   <- reads as "still vulnerable"
bool(body.get("token"))  # False  <- correct: no usable token
```

Measured 2026-10-31 (FIRST.org, FCaptcha): pre-fix `{"success":true,"token":"eyJzaX..."}`,
post-fix `{"success":false,"token":null,"reason":"pow_not_satisfied"}`. My first automated pass
printed `token=True` for three consecutive rounds and briefly contradicted the honest conclusion.

Rules:

- Test **presence with `bool(...)`** for any field whose fix would null it; print the **value**
  (`repr(body.get("token"))`), never the presence flag.
- Read the failure reason too (`reason`, `error`, `status`). `pow_not_satisfied` / `redirect_uri_mismatch`
  name the mechanism, which is what a fix reply should quote back to the vendor.
- Same family as the truncation traps below: the instrument reported a fact about the *envelope*
  and I read it as a fact about the *security property*.

## HTTP 200 can mean 401 — read the envelope, never the status line

Some APIs wrap every response in a fixed envelope and return **HTTP 200 for failures**:

```json
{"status":"error","data":{"code":401,"name":"Unauthorized","message":"Unauthorized. Access denied."}}
```

Seen live 2026-10-27 on a staking API: `POST /register` answered **HTTP 200** while its
body said `401`. A probe that classifies on status code reports *"write endpoint has no
auth gate"* — a Critical-shaped false positive on an endpoint that is in fact protected.

Rules:

- Before ANY auth-differential claim, print the body. If the service has a
  `{status, data, code}` shape, the real verdict is `data.code`, not the HTTP status.
- A `400`/`422` "Invalid message / invalid parameter" from a write endpoint means the
  **parser ran before auth** — it is not evidence that auth is missing. Re-test with a
  minimal *well-formed* body; if it then demands a signature/token, the gate is present.
- Symmetrically, a gate that **held** (all attempts refused) is a *verified negative*.
  Score it as closed, not as a lead: `all N attempts returned 40x` ⇒ drop. Do not let
  the words "secret"/"bypass"/"admin" appearing in the explanation resurrect it.

## Your own probing is a state change on the target — disclose it in the deliverable

Every claim rule above governs what you may *assert about the target*. This one governs what you must
*admit about yourself*, and it is the same honesty applied in the other direction: a probe that left a
trace is a fact about the engagement, and the vendor will find it whether or not you mention it.

Measured 2026-10-31 (Scribble Maps). Three separate traces, all created by my own testing:

| trace | cause | how it reads if undisclosed |
|---|---|---|
| `429 "You've submitted too many reports recently"` on the portal's own submit endpoint | 6 deliberately-incomplete dry-run payloads used to "learn the field names" | unexplained rate-limit hits from the researcher's IP → reads as abuse |
| an orphan Stripe Connect Express account (`acct_…`) | probing the seller-provisioning endpoint | an unexplained object in the vendor's billing system |
| config left enabled on a test tenant (SSO toggles, 13 verification domains) | feature testing | looks like an abandoned half-configured tenant |

Rules:

- **Never dry-run a one-shot submit endpoint.** Field names come from the form HTML + the page's own
  JS. One validation failure is enough to trip a per-endpoint throttle; six cost 40 minutes of blocked
  submission. This is a claim-discipline rule because the throttle then becomes the reason a report
  could not be filed — and that reason has to be stated.
- **One sentence per trace, in the report notes** — what was created, its state
  (unverified / inactive / holds no balance), and that the vendor may delete it. Put it in the
  deliverable, not just in your coverage file.
- **Clean up what is cleanable, and say what was cleaned.** Toggle the test features back off, delete
  the test records through the product's own endpoints, remove uploaded files — then verify the
  cleanup by re-reading the list (an empty list is the artefact). What cannot be cleaned (a
  provisioning side effect, a consumed daily quota) gets disclosed instead.
- **A consumed quota is a trace too.** If the program allows N reports/day and your testing used one,
  say so — the operator needs to know before they plan the next submission.

The generalisation: *a negative claim needs an artefact, and a positive claim needs a control — but a
side effect needs a sentence.* Omitting it converts a clean engagement into one that looks careless on
the exact systems the vendor cares most about.

## A rejected finding is a closed file, not a lead

Before spending hours deepening a candidate on a target with engagement history, check
whether it was already reported — and what the vendor said. One mailbox search beats a
day of re-exploitation:

```
Gmail API:  q = '(from:<vendor-domain> OR to:<vendor-domain>)'
            format=metadata, metadataHeaders=From,To,Subject,Date
```

Build two maps: **sent** (unique outbound report subjects, deduped after stripping
`[BUG BOUNTY]` / `Re:`) and **verdict** (each vendor reply, with its verbatim reason).
Then cross the sent map against the in-scope host list — hosts never named are the only
genuinely new surface.

Worked example (Flux, 2026-10-27): 77 messages → **60 unique reports**; 263 in-scope
hosts → **188 never named**. The finding the operator asked to "dig deeper" had been
reported **and rejected 12 hours earlier**, with the reason *"already covered by our
internal security audit … we rate it Low rather than High, because the data is payout
bookkeeping that is largely visible on-chain anyway."* Deepening it would have paid
nothing and repeated a testing violation the vendor had already flagged in writing.

Read verdicts as an oracle for what is dead on that estate:

| Verdict phrase | Meaning |
|---|---|
| "covered by our internal security audit" | Closed **regardless of severity** — never re-report the class |
| "reported before you" / "already known" | Closed; being first is the only gate that pays |
| "by design" / "intended" / "compatibility mode" | Closed unless you show a *different* unintended impact |
| "we rate it Low rather than High, because …" | Real finding, **Low ceiling** — believe the argument over your own scorer |

When a vendor states a testing constraint (*"keep live testing to your own accounts and
data"*), it binds the rest of the engagement: enumerate **counts**, never other users'
record contents, and if the remaining surface needs an account you do not have, stop and
surface the decision rather than improvising around it.

## A repeat round is not new evidence — check engagement history BEFORE recon

Measured 2026-10-30 (relay.link): a full round produced recon, 3 OpenAPI sweeps, an 11-shape
auth-bypass battery, nuclei, JS-bundle mining, RPC-namespace probes and takeover checks across 59
subdomains — and every one of those had already been run in **three prior rounds** (2026-10-03,
10-15, 10-18) with identical results. Roughly **90% of the round was duplicate work**, discovered
only when `session_search` was finally run *after* three hours. The single genuinely new item was a
residual gap the round-2 ledger had already named.

The check costs one call and belongs in 0A, before the first request:

```
session_search(query='<target> audit findings', sort='newest', limit=5)
ls -d "D:/data hermes/_progress/"*<target>*  "$HOME/AppData/Local/hermes/poc-plans/"*<target>* 2>/dev/null
```

Answer three things and write them into `SCOPE-<target>.md`:

1. **How many rounds already ran, and the verdict each time?**
2. **Which vectors are already NEGATIVE** — re-running them cannot produce new evidence.
3. **Which leads were left OPEN?** Read the prior report's *residual gaps / not tested* section.

The opening move is then **close the open leads**, not redo recon.

Why this belongs in a claim-discipline skill: a negative from a repeat round is not a negative, it
is a **re-derivation of an older negative**. Reporting "round 4: 0 findings" without saying it
repeats rounds 1-3 presents the absence of new work as fresh assurance, and it inflates the
apparent coverage fourfold. State the round number and what was actually new.

A repeat round is legitimate when the vendor shipped changes (diff the spec/bundle hashes), the
prior round left named gaps, or scope changed. "I forgot we already did this" is not.

Corollary — the same applies to a *sub-system* you already reviewed. Before re-deriving an adapter
verdict table, grep the previous ledger for it; a table of nine adapters is cheap to re-run but
worthless as new evidence, while the one row marked `needs-verify` is the whole assignment.

## A claim is not worth making until you know what the program PAYS for

Evidence discipline decides whether a claim is *true*. The payout model decides whether it is
*worth making at all*. Two bounty programs with identical scope lists can have opposite economics,
and reading only the scope wastes the engagement.

| Shape | Pays for | Ignores | Opening move |
|---|---|---|---|
| **Hygiene-shaped** (most web VDPs, Bugcrowd/Intigriti web targets) | missing headers, version disclosure, open redirect, CORS, rate-limit, GraphQL introspection | — | surface sweep: nuclei, headers, JS, endpoint map |
| **Fund-loss-shaped** (bridges, DEX, lending, solvers, chain infra) | theft, insolvency, permanent freeze | **everything in the left row** | trace the money path: who authorizes a transfer, and can you be someone else |

Measured 2026-10-30 (relay.link): the program defines `S1 = griefing / DoS-with-no-fund-loss /
admin-only`, `S4 = total theft`. A missing header is therefore not S1 — it is **not a finding at
all**. A full day of nuclei + header + JS sweeping on that target yields $0 by construction, no
matter how clean the artefacts are.

Five minutes before recon, answer and write into `SCOPE-<target>.md`:

1. **What is the severity model?** CVSS, fund-loss tier, or impact tier?
2. **What phrase sets the floor?** (relay: *"Admin-only bugs are S1"*, *"DoS with no fund loss"*.)
3. One sentence: *"This program pays only for X."*
4. Derive the opening move from that sentence, not from habit.

Corollary for the honesty ledger: an impeccable negative on a class the program never paid for is
not coverage, it is **effort spent off-target**. Say which lane you spent the time in and whether
that lane was payable — otherwise "we tested 12 vectors, all negative" reads as diligence when it
may read as a mis-scoped engagement.

**OOS lists name PRODUCTS, not words.** relay.link excluded *"Relay Vaults: contracts … + the
vaults API + the vaults UI"*. `vaults-api.relay.link` had open GraphQL introspection with an
enumerable `userBalances` query — the best-looking finding of the round, worth **$0**. For every
live host, grep the OOS text for the host's *product noun* (`vaults`), not just its FQDN: that
catches `vaults-api.*`, `*-vaults.*`, `/vaults/*` and the vaults UI in one pass.

## By-design access is not a vulnerability (read the vendor's policy first)

Before calling anonymous reachability a broken-access-control bug, check whether the
vendor's own CVD/policy explicitly sanctions it. Zenya/iProva (2026-10) states verbatim:
"Some parts of Zenya can be used without logging in on purpose... portal content a
customer has published (incl. documents)." So 1000 published medical documents being
anonymously listable + downloadable is **by design**, not a finding — and the policy even
routes over-exposure concerns to the *customer*, not the platform vendor.

Rule: a 200-with-data on a route the policy names as intentionally-public is a hardening
note, not a vuln. Reserve "broken access control" for data the policy does **not**
sanction — non-published records, other tenants' objects, sensitive modules. Prove the
control *fails* on non-public data (arbitrary ID → 200, cross-tenant → 200) before
claiming exposure; arbitrary-ID → 404 and sensitive module → 403 means the control holds.

Corollary — customer vs platform ownership: if the over-exposed content belongs to a
*customer* of the platform (a hospital's published docs), that is the customer's
configuration and their disclosure channel, not the platform vendor's. Submitting a
customer's misconfiguration to the platform vendor (or vice-versa) misroutes the finding.

## Proven vs theoretical — say which link is missing

When the operator demands "buktikan, jgn teori" and the final impact step cannot be
executed (no test account, won't brute-force a third party), split the claim in the same
message: primitives that are PROVEN (with artefact) vs the chain's final step that is
THEORETICAL (not executed). Never let a sound chain be stated as an achieved breach.
"Enumeration oracle + no auth rate-limit = credential-stuffing → ATO" is a proven-enabler
claim; "I accessed patient data" would be fabrication if the sensitive modules returned
403/404. Report the enabler honestly; a Medium-with-honest-limits beats a retracted
Critical.

## State boundary and uncertainty in the same message as the claim

Where a chain is only partly built, say which link is missing in the same breath as the
finding — not in a footnote after the vendor has already read an inflated title:

> "What I proved: X (evidence). What I am NOT claiming: the prediction/recovery chain —
> it was not executed end to end."

This is what keeps a "Low/Medium with honest limits" report accepted instead of a
retracted Critical. A candidate that does not reproduce on re-test is **unstable** — do
not report it; record it as excluded with the reason.

### …but "unstable" is a conclusion you EARN, not a label for the second sample

Measured 2026-10-25 (betterteam, `app.betterteam.com/debug`): request 1 returned **200**, request 2
returned **302**, so it was written down as `UNSTABLE → DROPPED`. It was deterministic the whole time —
**200 for every `Accept` value except `text/html`**, and the two probes differed only because `curl` and
Python `urlopen` set `Accept` differently. A real Low-severity info-disclosure was nearly destroyed by a
correct-sounding rule applied to an incomplete test. The rule was right; the *test* was not.

Before writing `UNSTABLE` / "not reproducible", run this matrix — one variable at a time, 3× each:

| axis | values to try |
|---|---|
| `Accept` | `text/html`, `application/json`, `application/vnd.api+json`, `*/*`, **omitted** |
| `Content-Type` (POST/PATCH) | json, form-urlencoded, vnd.api+json, multipart |
| `User-Agent` | browser string, `curl/8.x`, library default, empty |
| cookie | authenticated jar / anonymous / jar with one cookie removed |
| method & shape | GET vs HEAD, trailing slash, with/without query string, `X-Requested-With: XMLHttpRequest` |
| `Sec-Fetch-*` | browser-realistic (`Sec-Fetch-Mode: navigate`) vs absent |

Why this class matters: a **header-gated** page is exactly the shape of a *browser-blocked,
tool-served* endpoint. Browser-only testing misses it; tool-only testing sees it and looks flaky. So the
trigger condition belongs **verbatim in the repro** ("returns 200 unless `Accept: text/html`"), which
simultaneously explains the discrepancy and pre-empts the triager's "cannot reproduce".

If you never ran the matrix, the honest status is `NOT FULLY CHARACTERISED` and the candidate stays
open — not dropped. Full worked example: `audit-pipeline-operations` §5b.

### …and the mirror case: a genuinely FLAPPING error is noise, but you must PROVE it is noise

The matrix above exists to stop you discarding a *deterministic* finding. The opposite error is just
as costly: promoting a **transient backend degradation** into a security finding because it produced
a `500`. Measured 2026-10-30 (Sentz/Moby): `moby.app/healthz`, `/admin`, `/api`, `/favicon.ico`,
`/sitemap.xml`, `/null` all returned empty `500`s, while `api.moby.app` served the same paths
normally (`/healthz` 200, `/admin` 401). It looked like a parser differential between two front-ends.
It was a **degraded pay-page renderer**.

Run all four gates before calling a `500` noise — and record each:

| Gate | What to run | Noise verdict when |
|---|---|---|
| **Repeat-N** | hit the *same* path ≥10×, count the status distribution | non-deterministic (`/test` 500×10, `/admin` 500×9/200×1, `/api` 500×9/200×1) |
| **Body-leak** | `-i` on the 500; assert on the body, not the status | `Content-Length: 0`, no stack trace / server version / reflection |
| **Input-independence** | probe benign, unrelated paths | 500s on `favicon.ico`, `sitemap.xml`, `null` ⇒ handler's generic error, not injection |
| **Positive-control isolation** | re-run the *known-good* control throughout | `api.moby.app/healthz` stayed 200×6 and `/proxy/fuspay` stayed 401×6 ⇒ flap is isolated to one renderer |

If all four hold, the verdict is `transient degradation — ops heads-up, NOT a security finding`, and
it goes in the report as a negative *with the four gates quoted*. If any gate fails (deterministic,
leaks a trace, input-dependent, or the control also degrades), it is a live lead — keep digging.

Corollary technique that surfaced it: **two hostnames fronting one backend can route differently.**
`moby.app` treated *every* path as a handle (`x-location-debug: prefix`), so `/healthz` and `/admin`
were looked up as usernames and the renderer errored; `api.moby.app` routed them to real API
handlers. When one host 500s where another answers, check for a routing divergence before assuming
injection — and check a response header like `x-location-debug` that reveals the internal route class.

## Never let a tool's output count become a finding count

Corrected live 2026-10-25. `dalfox` emitted three `[POC]` lines; the progress update said "3 POC" and the
operator read it as three findings and pushed back: *"kamu blm temuan ad 3, tp sy cm ad 1 draft dan udh
dikirim, yg lain mana"* — where are the other two? There were none. All three POCs were the same **false
positive** (`ref` never reflected; identical response length with and without the payload).

Rule: **a scanner's unit is not a finding.** When reporting progress, always use the vendor's unit and the
lineage, never the tool's own naming:

```
BAD   "3 POC found"                        -> reads as 3 findings
GOOD  "1 candidate, 3 scanner hits, all 3 = one FP (disproved by X)"  -> audit-proof
GOOD  "0 new findings; 41 tests run, 12 classes closed negative"
```

Three habits that prevent the misfire:

1. **One candidate = one row.** Dedupe scanner hits by *root cause*, not by URL or parameter. Three POCs on
   the same parameter are one candidate with three probes.
2. **Report the count you have EVIDENCE for.** "Findings" only counts what survived the control test and is
   ready to submit. Everything else is `candidate`, `unverified`, `FP`, or `not tested` — say which.
3. **When the operator challenges a count, answer with the accounting, not a defence.** List every number
   and what it maps to (`submitted / staged / candidate / FP / negative / untested`). The corrected answer
   here was: *1 real finding, and the "3" was 3 FPs on one parameter* — stated first, in one sentence,
   before any explanation of the work done.

**A scanner HIT is also only a candidate — and your own sweep can be what breaks it.** Zenya,
2026-10-31: `nuclei` reported `wp-user-enum` on `developer.zenya-software.com` returning **200**
with six usernames, and it went into the ledger as `CONFIRMED`. Three later re-tests (curl, 4 s
spacing, browser UA) all returned:

```
HTTP 403  {"code":"ninjafirewall_access_restricted","message":"Verboden toegang"}
```

NinjaFirewall was now blocking the route. The 200 was real when captured and was not
reproducible an hour later — almost certainly because the 168k-request sweep that produced it
tripped the WAF. Two rules follow:

- **Never write a scanner hit into the ledger as CONFIRMED.** It enters as `candidate`, and only
  becomes CONFIRMED after the same ≥3× re-test a hand-found bug gets. A scanner's severity label
  is not evidence either.
- **Re-test before you report, not before you scan.** A finding captured during an aggressive
  sweep is the most likely to have been *caused* by the sweep. If it does not reproduce, the
  status is `RETRACTED — not reproducible`, and you say the scan was the likely trigger; you do
  not quietly keep it because it looked good at capture time.

Corollary for negatives, same failure shape in reverse: **a scanner's "0 matches" is not a clean target.**
Check completion before it counts — `nuclei` finishing at 95% of its request budget with 22/22 hosts still
answering, 0 matches, is a legitimate negative *for that template set*. A run killed at 12%, or one whose
output file is 0 bytes because it never started writing, is `NOT TESTED`. Say which template set the
negative belongs to; never widen it to "the host is clean".

**A zero needs a positive control, and errors are a health metric.** Measured 2026-10-30 on relay.link:
a `nuclei` run across 45 live hosts returned 0 lines and I reported it as "0 hits, verified". It was
nothing of the kind. The tell is a **control that must match**:

```bash
nuclei -l live.txt -silent -tags tech -o control.txt   # tech tags MUST hit a live host
# -> 0 hits on 45 live hosts  => the INVOCATION is broken, the target is not clean
```

Two independent non-result shapes, both of which still read as "clean":

| Shape | Signature | Verdict |
|---|---|---|
| output suppressed | `-silent` + `-o` + `2>/dev/null` → 0 lines, **0-byte stderr** | NOT TESTED — nothing reached stdout |
| engine thrashing | `Matched: 0` with **`Errors: 216270`** of 695,295 requests (~31%) | NOT TESTED — re-run at lower `-rl`/`-c` |

Rules: (a) every scan whose zero you intend to report needs a tag set guaranteed to match
(`-tags tech` / `-waf-detect`); no control hit ⇒ discard the run, don't report its zero. (b) Record
`templates / control hits / scan hits / Errors` as a line — that is a measurement, "0 hits" alone is a
claim. (c) Errors as a **fraction of requests** is the health metric; >10% means re-run. A controlled
re-run of the same estate sat at ~2% errors, which is what made its zero reportable.

Three more shapes that read as a negative and are not — all three fired in one session
(2026-10-26, hivenet) and each nearly became a published false negative:

- **A `401` from an expired token is a token problem, not a control holding.** Mid-validation
  the session token aged out, two of three validation runs came back `401 Unauthorized`, and
  the naive read was "the endpoint rejects cross-tenant access". It was an auth failure.
  Refresh the token and re-run before recording anything as a verified negative; an
  expired-token 401 is the single easiest way to publish a control that was never tested.
- **A search window that is too narrow reports absence.** An IMAP fetch limited to the last N
  messages printed "recipient mail: False" for mail that had in fact been delivered — it was
  simply older than the window. Search by criteria (`AND(from_=...)`), not by recency, and
  when a check comes back negative, widen the window before believing it.
- **Verify a count before quoting it.** `ls -la f | awk '{print $5,$9}'` prints BYTES, not
  lines; quoting that column as "N URLs crawled" when N was the file size survived into a
  status report. Use `wc -l` for counts and re-read the number off the actual output before
  it goes into a message. A wrong count in a progress update is the same failure as a wrong
  finding count — it makes every other number in the report suspect.
- **A `...` in a captured value is usually YOUR truncation, not the data.** The near-miss of
  this class (Genians, 2026-10-27): a verification URL printed as
  `…/login?loginuse_mailkey=eyJhbG...k89A&user_idw74` read as a lost `=` in the template, i.e.
  "every new registration is permanently unverifiable". I then "confirmed" it by trying
  `=w74`, `=74`, `=1`, key-only — all failed — and reported it to the operator as a functional
  bug. It was **my own shell head/buffer cutting the string**; the link was intact (1056 chars,
  `key` param 766 chars) and opening it worked. The variant sweep "confirmed" nothing because
  the key had simply expired by then (Keycloak action tokens live <20 min), so failure was
  over-determined twice and the wrong story survived both checks. **Rule:** before characterising
  any captured string, read it from a FILE and assert on it
  (`len(v)`, `"..." in v`, parse the query params) — never off console output. Anything that
  "looks truncated" is a rendering question until the byte-level check says otherwise. This
  applies to JWTs, tokens, hashes, base64 blobs and long URLs alike.
- **Your own slice is the same trap, and it reads as fact.** Zenya, 2026-10-31: a `Location`
  header was printed with an explicit `[:220]` in the probe code, the visible tail ended at
  `...redirect_uri=<url>&response_type=code&scope=openid+email` with no `state`, and that became
  the finding *"OAuth flow ships no state parameter — login CSRF"*. The full header was 354
  chars and **did** carry `state=<base64 JSON nonce>` (unique per request) plus
  `prompt=select_account`; the callback also rejected arbitrary state values. The finding was
  fabricated by a display slice, and it printed with the same authority as a real one. This
  specific failure mode was already documented one row above and still happened, because the
  truncation was in **my** code rather than the shell — so the rule was never recognised as
  applying. **Before any claim about an absent substring: `print(len(value))` first, then the
  value, then assert `"state" in value`. Never eyeball a sliced string and conclude absence.**
- **The same `...` makes you mistake a whole page for a value.** Printing a body with
  `head -c` gave `eyJhbG...` twice, and re-printing with a wider buffer changed the apparent
  "finding". If a value's length matters to the claim, print `len()` first, then the value.

- **"Blocked / unreachable" is the most expensive instrument artifact, because it *closes* surface.**
  Measured 2026-10-27 (Genians NAC captive portal): `curl -skL https://<site>/cwp2/` landed on
  `sessExpired.xhtml` → "Your Session has expired", reproduced across a dozen paths, and was written
  into the status report as *"CWP requires a captive-portal session from the network sensor —
  unreachable, blocker"*. Wrong. `curl` **discards `Set-Cookie` on a 302** unless you pass a jar;
  the app was issuing its `JSESSIONID` on the redirect and the next hop arrived cookieless, which
  the app correctly renders as an expired session. With `-c jar -b jar` the same URL returned
  **HTTP 200, 32 KB, "CWP (Captive Web Portal)"** — the whole surface opened, including a
  `user.xhtml` account oracle. Nothing about the target changed; only the client did.
  Rule: **any "session expired / not authorised / login wall" verdict from a redirect-following
  client must be re-run with an explicit cookie jar before it becomes a coverage limitation.**
  Generalise: before recording a negative as a *blocker*, ask whether your client preserved every
  piece of state the protocol needs (cookies on 3xx, `Referer`, `X-Requested-With`, a session id
  carried in a header rather than a cookie). A blocker that is really a missing flag is the one
  false negative that permanently hides a whole attack surface — and it is the one the operator
  finds later and has to correct you on.

- **The OUTPUT LAYER can mask the very bytes you are reasoning about — hexdump before you
  characterise a redirect, token, or URL.** This is the mirror of the truncation trap above, and it
  manufactures a **false positive** instead of a false negative. Measured 2026-10-30 (Sentz/Moby,
  `sentz.page.link` Firebase Dynamic Link allowlist test): a probe of
  `link=https://moby.app#@evil.com/` returned `302` and the console printed
  `Location: https://***@evil.com/` — the tool-output layer had redacted the substring `moby.app#@`
  into `***`. Read naively that is an open redirect to `evil.com`. The raw bytes (`grep -i '^location'
  hdr.txt | xxd`) showed the header was literally `Location: https://moby.app#@evil.com/`, where `#`
  begins the **fragment** — the browser navigates to host `moby.app` and the fragment is inert. Not a
  redirect at all; the allowlist held. Rule: **any time a captured value looks altered, redacted,
  shortened, or suspiciously convenient, re-read it from a file at byte level before building a
  claim on it.** `***`, `…`, `[truncated]`, `<redacted>` in console output are rendering questions,
  never data. This applies to redirect targets, JWTs, signed URLs, and anything whose *host* or
  *structure* carries the finding. Full matrix + worked example:
  `references/redirect-allowlist-probing.md`.

The common shape: all of these are the instrument reporting on itself. Before writing any
negative, name what the instrument actually did — ran to completion? authenticated? looked
in the right window? counted the right column? **truncated the string?** — not merely what it
printed.

## A scanner's POSITIVE hit needs a re-test too — your own scan can flip the answer

The zero-discipline above governs false negatives. The mirror failure is a scanner hit you promote
without re-testing, and it has a nastier cause than an ordinary false positive: **your own scan can
change the target's behaviour between the hit and the report.**

Measured 2026-10-30/31 (Zenya). `nuclei` reported `wp-user-enum` HTTP 200 on
`developer.zenya-software.com/wp-json/wp/v2/users/` and harvested six usernames; it went straight
into `COVERAGE-LEDGER.json` as `CONFIRMED`. On a 3× re-test (curl, 4 s spacing, browser UA) every
attempt returned:

```
HTTP 403 {"code":"ninjafirewall_access_restricted","message":"Verboden toegang","data":{"status":403}}
```

NinjaFirewall now blocks the route. Most likely cause: the 134,000-request nuclei sweep that found
it. The enumeration was real when observed and was gone by report time.

Rules:

- **A scanner hit enters the ledger as `candidate`.** Promotion to `CONFIRMED` requires the same 3×
  + control ladder as a hand-found bug. A tool's confidence is not a sample size.
- **Re-test after the aggressive window closes, not from inside it.** A hit observed at request
  #90,000 of a sweep has not been verified — it has been sampled under load, against a WAF that is
  now awake.
- A hit that no longer reproduces is `UNSTABLE → excluded`, and the exclusion is worth writing down
  with its reason. The next round would otherwise inherit the same phantom.
- Corollary: if you are about to quote a scanner hit to the operator as a finding, the re-test costs
  three requests. Do it first.

## A client that refuses old TLS is reporting on itself

Measured 2026-10-31, same target. Testing `t.zenya-software.com` for TLS 1.0/1.1 with Python `ssl`
pinned via `minimum_version` / `maximum_version` returned **FAIL for both** — which reads as "the
server refuses, nuclei was wrong" and nearly became a retraction. It was the *client*. OpenSSL 3.x
ships `SECLEVEL=2`, which will not even offer TLS 1.0/1.1 cipher suites, so the handshake dies
locally before the server is asked anything.

Authoritative re-test:

```bash
echo | openssl s_client -connect <host>:443 -tls1   -cipher "ALL:@SECLEVEL=0" -sigalgs "RSA+SHA256:RSA+SHA1" 2>&1 | grep -E "^ *Protocol|^ *Cipher"
echo | openssl s_client -connect <host>:443 -tls1_1 -cipher "ALL:@SECLEVEL=0" -sigalgs "RSA+SHA256:RSA+SHA1" 2>&1 | grep -E "^ *Protocol|^ *Cipher"
```

Result: `Protocol: TLSv1  Cipher: ECDHE-RSA-AES128-SHA`, and the same for TLSv1.1 — the server
genuinely does accept both, matching nuclei's `TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA`, which is simply
the IANA name for that OpenSSL cipher.

Rules:

- **A "version not supported" from a modern client is a statement about the client's security
  level.** Drop `SECLEVEL`, re-test, and only then record a verdict.
- Read the negotiated cipher name back and map it to the scanner's IANA name. **Matching cipher is
  the proof that both tools saw the same thing** — far stronger than matching verdicts.
- Same class as everything above: before publishing a negative, name what the instrument did. A
  pinned-version client that cannot speak the protocol will always report the protocol missing.

## A severity SCORER is an instrument too — and it lies in eight known ways

If you automate candidate scoring (a severity calculator, a triage classifier, an LLM
grading your notes), treat its output as an instrument reading, subject to the same
"name what it actually did" rule as any scanner. Measured 2026-10-27: a purpose-built
scorer mis-scored **six of twelve** real leads, silently, in both directions — and kept
producing new failure modes on the next two datasets (rows 7-8 below), which is the
actual lesson: **re-run the paired fixtures on every new target, not just after a code
change.** Each new data shape finds a new way to fool the classifier.

Every trap below converts *your own note wording* into a fake verdict:

| Trap | Failure | Guard |
|---|---|---|
| **Plan text read as evidence** | A field saying `technique: 169.254.169.254 -> cloud creds` describes what you *intend to try*. Scored as "SSRF proven" → STRONG. | Keep `PLAN_FIELDS` (`technique`, `primitive`, `escalations`, `probes`, target) permanently out of the evidence blob. **If a field states intent, it is never proof.** |
| **Exposure scored as use** | `.env` leaking `DB_PASSWORD` rated **Critical** though the password was never exercised | Cap leak-only at High; require a usage marker (`logged in`, `accepted by`, `authenticated as`, `token issued`) before promoting |
| **Negation blindness** | `"public bucket **no** secret"` matched `secret` → STRONG | Scan a window before the marker for `no\|not\|without\|tanpa\|bukan\|non-\|tidak ada` |
| **Substring collision** | `rce` matched inside `resou**rce**`; `root` inside `web **root**` | `\b` word-boundary for any marker under ~5 chars |
| **Missed quantity evidence** | `"14 records"`, `"23 rows"` not read as mass → lead stayed WEAK | Parse count≥10 + noun (`records/rows/tenants/orders/invoices`) |
| **Floor above ceiling** | A class whose floor is High printed `High → Low`, an impossible row | Clamp the ceiling up to the floor |
| **A gate that HELD scored as a lead** | Notes read *"8 bypass attempts, all returned 403 -> gate held"* and the scorer still emitted `PURSUE / High`, because the word `secret` appeared in the explanation | Detect the verified-negative shape and force `CAPPED-DROP`: `all (N) attempts ... 40[13]`, `gate held`, `N/M rejected`. **A control that held is the opposite of a finding.** |
| **On-chain-derivable data scored as confidentiality** | Unauthenticated IDOR leaking `payment_address`, `collateral`, `tx` scored **High**; the program rated it **Low** because *"the data is payout bookkeeping that is largely visible on-chain anyway"* — and the program was right | If the exposed fields are derivable from a public ledger, drop confidentiality one tier. Only off-chain secrets (email, KYC, credential, session token, identity linkage) hold High/Critical. |
| **Category mention read as evidence** | `"Every PII service (user, org, dlfileentry) returned 404"` and `"No PII, no write, no auth bypass"` both matched `pii` → reference-data leak scored **High**. Same for `"a Next.js **shell**"` matching `shell` | Suppress a marker when it sits in a *category* frame: preceded by `every/all/each/any` or followed by ` service/field/class/endpoint`. A list of services you tried is not a list of things you found. |
| **Your own retraction not read as one** | Notes said `"RETRACTED by control: same 10 requests to one ghost address behaved identically"`; the scorer still emitted `NEED-ONE-MORE / Medium` | Detect explicit retraction vocabulary — `retracted`, `no oracle`, `not an oracle`, `killed by control`, `claim withdrawn` — and force `CAPPED-DROP`. If you wrote the word, believe it. |
| **Dangling-subdomain scored as High with no auth impact** | Third-party content on `*.target.com` (cert `CN` = another domain) scored High purely from "foreign content on target host" | Class-specific ceiling: third-party-operated subdomain = **High at most**, and `Critical` only with a *proven* OAuth `redirect_uri` or parent-scoped session cookie. On most policies it is out of scope entirely — see the eligibility gate. |

That last row is the sharpest lesson available from automated scoring: **severity is a
property of the data, not of the access-control gap.** An unauthenticated IDOR onto
public-ledger bookkeeping is a real bug with a Low ceiling — the engine's "it's a foreign
object, therefore High" inference is wrong there, and a vendor will say so in one sentence.

**The paired fixture that proves a scorer discriminates.** After any change, feed it the
same leak twice — once without and once with the credential *used*. High vs Critical
respectively means the discriminator works; both landing on one tier means it is broken.
This is rule 2 (ship the control) applied to your own tooling.

**A scored verdict is a hypothesis.** Ask: *which sentence in my notes proves a boundary
was crossed?* If you cannot quote it, the score is wrong. The one reading worth trusting
without re-reading is a **structural cap** (self-XSS, missing headers, "admin can do X") —
those match properties no wording can rescue, which is exactly why they are the reliable
half of the tool.

Corollary for half-formed notes: a lead with no class still scores, because symptom text
routes it (`/admin` → auth-bypass, `?next=` → ATO, `?user=` → IDOR). A lead that lands in
`default` is telling you it has **no vulnerability shape yet**, or that your note omits the
one detail that makes it scoreable — which endpoint, which parameter, what changed.

## A uniform response across every variant means your variable was never consulted

Differential testing earns its keep only if the variants can actually diverge. Measured
2026-10-27 while testing a suspected cross-account password change (`gn_user_profile_process`
on a CSM): the same `{"result":false,"message":"invalid access"}` came back for **my own
email**, a **second real account I owned**, and a **nonexistent `example.invalid` address**.
The tempting read is "all rejected, control holds". The correct read is stronger and different:
if a real victim address and a nonexistent one are indistinguishable, the server rejected the
request **before** it ever looked at the variable — so the test says nothing about
authorization, and the hypothesis (the `email` param drives the lookup) is **not supported**,
which is not the same as "disproved".

Rules that follow:

- **Always include a nonexistent/negative value in a differential set.** Without it you cannot
  tell "denied for you" from "denied for everyone, always".
- **Identical responses ⇒ you are testing the wrong layer.** Find what gates *before* your
  variable (session binding, CSRF, a consent/2FA precondition, ownership of a different object)
  and satisfy that first. Replaying a captured legitimate request is how you earn the right to
  vary one field.
- **Do not report a "negative" you cannot distinguish from a broken test.** `NOT FULLY
  CHARACTERISED` is the honest status; "denied" is a claim that needs the positive control.
- **Capture the real payload by hooking `page.on("request", …)` during one genuine UI submit.**
  Hand-assembling parameters skipped two consent flags that the button's JS handler added,
  silently invalidating several attempts; the captured body had them.

## `CONFIRMED` is a verdict with a sample size attached — the ledger is a claim too

Measured 2026-10-31 (Zenya), forced by the operator asking *"sdh kamu cek lagi tiap temuan sebanyak
3x?"*. Eight findings sat in `COVERAGE-LEDGER.json` all labelled `CONFIRMED`. Only **one** had
actually been run 3×. The other seven were single observations from one sweep, promoted to
`CONFIRMED` because the request had returned what I expected. Two of them did not survive the
re-run — the WAF-flipped `wp-user-enum` and the TLS-version verdict above.

That is the same overclaim as inflating a report, just aimed at your own notes: the ledger is read
by the next session as established fact, so a `CONFIRMED` it did not earn poisons every downstream
decision.

- A ledger entry earns `CONFIRMED` only when it carries `n ≥ 3` **plus** its control. Anything else
  is `candidate` or `single-observation`, and the ledger spells out which.
- **Run the 3× before the operator asks.** If they have to ask, the answer is already no — and the
  honest reply is "only one of them", not a defence.
- A finding that is `Low` and maps to a policy exclusion still needs the same verification if you
  are going to name it in a status report. *"It's only Low"* is not permission to under-test; it is
  the reason the miss is easy to make.
- When the re-run contradicts the ledger, **record the retraction as a first-class entry** —
  `{"id": "...", "status": "RETRACTED", "reason": "..."}` — rather than silently deleting the row.
  The retraction is what stops the next round inheriting the phantom, and it is the artefact that
  makes the correction auditable.

## Verification ladder — before the word "confirmed"

```
[ ] Probed from a clean session (not reusing a cached/authenticated state)
[ ] Re-verified 3x; disagreements recorded as UNSTABLE, not averaged away
[ ] Control for the boring explanation executed (see rule 2)
[ ] Raw artefact + command + sha256 on disk
[ ] Operator can re-run every line without asking a follow-up question
[ ] Reading the artefact does not exceed the programme's "minimum needed" limit
[ ] Claim text stops exactly where the evidence stops
```

## Oracle-specific validation traps (timing & rate-limit)

Two over-claims corrected live on Zenya (2026-10-24) — both were single-observation oracles that
looked real and were not. The operator forced the re-test ("bukktikan, jgn teori"); encode as rules:

- **A timing oracle needs N-sample validation on BOTH sides; the first request is always an outlier.**
  "valid user 1.23 s vs invalid 0.24 s" looked like a clean login-timing enumeration oracle — but the
  1.23 s was the cold-start first request. An 8-sample alternating test gave valid=[1.089, 0.211,
  0.217, 0.228, …] (only the first slow) vs invalid=[0.239, 0.222, …]; separation = FALSE. Rule:
  run ≥6–8 alternating samples per side, flag/discard the first, and require `min(valid) > max(invalid)`
  before claiming a timing differential. A single fast/slow pair is not an oracle.
- **"No rate limiting" requires volume past the expected threshold.** "10–15 login attempts, no 429"
  was stated as "login is unthrottled" — wrong: at 60 attempts the 429 first appeared at ~#25. Rule:
  to claim absence of rate-limiting, probe 50–100+ and report the exact attempt number where 429 first
  appears (or that none did at that volume). A low-volume "no 429 yet" is not proof of absence; it is
  "threshold not yet reached."
- **Volume is not enough — the requests must REACH the secret check.** Measured 2026-10-25 (Proton
  Drive share-link): 30 rapid `POST /urls/{token}/auth` returned 30× `422 "Invalid SRP parameter"`
  with no 429, which reads like "unthrottled password endpoint". It is not evidence of anything: the
  payloads carried a random 256-byte client ephemeral, rejected at **parameter validation** because it
  is not an element of the SRP group. **No password was ever compared**, so a throttle on the real
  credential path could exist and stay invisible. Rule: name the layer that produced the rejection.
  A format/type/validation error means you tested a **parser**, not an authenticator — and 400/422
  "invalid parameter" is not "wrong password". Before a brute-force claim, require the rejection to be
  *indistinguishable from a deliberate wrong-credential response with a WELL-FORMED payload* (same
  code + message); otherwise the sample never exercised the check. Where the protocol must be
  implemented client-side to try even one guess (SRP verifier, PGP-auth challenge, signed proof), the
  honest status is **UNTESTED** — not "no rate limit", and not "negative".
- Both are the same discipline as rule 2 (ship the control): the control for a timing oracle is the
  multi-sample distribution; the control for a rate-limit claim is the higher-volume run. State the
  sample size and the threshold in the finding, or downgrade the claim. When you correct an earlier
  over-claim mid-session, say so explicitly ("koreksi: klaim X salah, buktinya Y") — the operator
  values the correction over a quietly-rewritten narrative.

- **A probe script must emit MEASUREMENTS, never verdicts.** Measured 2026-10-30 (DedSec CCTV auth
  server, account-enumeration timing on `POST /auth/register`): the probe printed its own conclusion —
  `-> a repeatable, sizeable delta = account enumeration oracle` — from three medians
  (nonexistent 1653 ms / unverified 1924 ms / verified 2019 ms). The very same output carried the
  spread: **min 302 ms, max 3474 ms**. The delta was 270–366 ms inside a 3.2 s spread, i.e. no
  separation whatsoever; the `min(valid) > max(invalid)` test above would have refused it in one line.
  The verdict was fabricated by my own formatter and printed with the same authority as a real
  finding — the operator was one message away from receiving an invented medium-severity bug.
  Rules: (a) a script prints numbers and their spread (`median / min / max / n`), never `=> bug`;
  (b) run the separation test in the write-up where it is visible and reviewable, not in the probe;
  (c) if an auto-generated verdict is later retracted, say the sentence was the script's, not a
  considered claim — otherwise the audit trail reads as though you reasoned your way to it. This is
  the automated form of the rule above ("never let a tool's output count become a finding count"):
  the tools that lie here are your own formatter and your own summary line.

## Third-party assets

If the artefact turns out to belong to someone who is not the engagement target, the
finding does not transfer. Escalate to the operator, mark it
`excluded — third-party asset, ownership elsewhere`, and do **not** submit it to the
engagement's vendor channel. Submitting a third party's misconfiguration to the wrong
company ends the engagement.

**A finding whose only reproduction vehicle is a third party is not a dead finding — it is a
proof-location problem.** Move the reproduction to infrastructure you own and keep the claim:
run the vendor's own code path locally, then reproduce the downstream effect with a control.
Concretely, for a resource/limit bug in a fleet-run platform, the evidence that a vendor *can*
verify is `file:line` call-sites plus a two-container differential on your own Docker
(`--cpus 0` vs `--cpus 0.1`, cgroup counters, not CPU%). A container on a stranger's node is
unverifiable by the vendor and reads as unauthorised access, so it converts a real bug into a
rejected report. Recipe: `probe-validation` §2g + `references/owned-infra-quota-proof.md`.

Corollary for delivery: numbers a reviewer could accuse you of typing are worth less than
numbers served live. A public endpoint that reads kernel state on every request (and a labelled
control panel beside it) removes the "you wrote that yourself" objection without an argument.

## Related

- `triage-validation` — the 7-question gate that runs before any report.
- `evidence-hygiene` — capture-and-redact protocol for PoC evidence.
- `bug-report-delivery` — report/PDF/draft mechanics once a claim clears this ladder.
- `references/negative-controls.md` — concrete control recipes, incl. the S3 `%2F` trap and the
  bucket-ownership attribution table.
- `references/gmail-draft-send-account-pinning.md` — why `gmail_ops.py send-draft` returns
  `404 Requested entity was not found` on a draft that plainly exists (it resolves the DEFAULT
  account, not the draft's), the pin-the-account API pattern that fixes it, the sent-artefact
  verification checklist, and the sibling failure modes (drafts destroyed by repeated
  `update()`, duplicate staging, empty-body DELETE). Read this the moment a staged draft
  refuses to send.
- `references/money-path-claim-verification.md` — probe recipes for targets that move value
  (bridge/solver/DEX/payments): auth-class-per-route from the spec, key-bypass shapes, the
  **signature-binding** probe (whose signature does the claim/permit endpoint accept?), calldata
  integrity vs displayed quote, quote business-logic fuzz, RPC namespace sweep — each ending in a
  readable verdict, plus the stop line that keeps the test lawful (never complete the theft).
- `references/redirect-allowlist-probing.md` — open-redirect / allowlisted-`link`-param hunting:
  the 16-row host+scheme matrix, why `#@evil.com` and `?@evil.com` returning 302 is **not** a bypass
  (fragment/query is inert — hexdump the Location), the output-mask trap that manufactures a false
  Critical, and the adjacent surfaces (custom vs generic FDL domain, `?d=1`, `.well-known`
  app-link files, long-value handling).

## Absorbed playbooks (complete sub-packages under `references/`)
This is the umbrella for claim discipline: what you may assert, and what must exist before you
assert it.

- `references/negative-claim-discipline/PLAYBOOK.md` — exhaustion claims must reconcile against your
  own enumeration; eligibility/severity is not scope; how to answer when the operator challenges a
  negative.
- `references/audit-coverage-discipline/PLAYBOOK.md` — the mandatory three-column coverage ledger
  before any negative, the two completeness checks, "a gate that held is a finding-shaped result",
  plus the submission gates (in scope and payable / artifact matches LIVE version / deliverable
  matches the ask). `references/live-version-verification.md` and
  `references/negative-claim-ledger.md` are the working templates.
