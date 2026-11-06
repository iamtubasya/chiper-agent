---
name: vendor-engagement-continuity
description: "Vendor engagement lifecycle: shortlist, contact discovery, submission, follow-up, resume."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, dedup, vendor, submission, triage, severity, novelty]
    related_skills: [lead-to-critical, triage-validation, disclosure-followup-evidence,
                    program-shortlist-verification, target-pool, report-gotchas]
---

# Vendor Engagement Continuity

## When to Use

- You are about to hunt a target you have **already submitted reports to**.
- A previous report was rejected and you are tempted to re-argue it with better evidence.
- You need to pick a surface that the vendor has **not already adjudicated**.
- You are resuming an engagement across sessions and cannot remember what was sent.
- **You just submitted a report** and need to handle the auto-ack, capture the ticket number,
  and set up a reply watcher (Step 7).
- A staged draft shows `SENT` and you need to establish whether you or the operator sent it.
- **The vendor replied "we believe this is fixed — please confirm"** and you must re-verify the
  PoC and reply inside the existing thread (Step 8).
- You need to create a test account on a target and the signup is closed.

This skill exists because the most expensive mistake on a returning engagement is not a
missed bug — it is **spending a full round re-discovering a finding the vendor already
rejected**. That failure is invisible while it happens: the analysis looks productive, the
severity argument gets sharper, the PoC gets cleaner, and every hour of it is worthless.

## The rule

**Before scoring, probing, or writing one line of analysis: search the outbound mailbox.**

On a returning target, the single most likely outcome of a "new" finding is not a payout.
It is one of:

| Vendor phrase | Meaning |
|---|---|
| "already covered by our internal security audit" | permanent no, **independent of severity** |
| "reported before you" / "already known to us" | duplicate, no payout |
| "by design" / "intended part of the integration" | no payout |
| "valid, and you were the first to report it" | **this is the only shape that pays** |

Notice what is *absent* from that list: severity. Most rejections are won on novelty and
adjudication status, not on how bad the bug is. Re-scoring a rejected finding higher is
almost always wasted work.

## Step 1 — Recover what was already sent

Query your own mailbox before anything else:

```
to:<vendor-security-address>          # everything you sent
from:<vendor-domain>                  # every reply the vendor wrote
subject:<product or feature>          # is this exact surface already adjudicated
```

Then **read the vendor's replies in full**, oldest to newest. A rejection email is the
highest-value recon artefact available on a returning engagement: it states the program's
real acceptance taxonomy in its own words.

Concrete Gmail recipe, the message-metadata pass, and a worked reconstruction of a
60-report engagement: `references/prior-submission-recon.md`.

**Also read the local engagement directory before the mailbox.** Reports, PoCs, evidence runs and
the negative ledger live at `D:/data/hermes/audits/<target>-<date>/` (`recon/ tools/ evidence/
poc/ findings.json`). When the operator asks "is the data from that target still around?", answer
from the filesystem and the mailbox together — the mailbox says what was *sent*, the audit dir
says what was *proven*. `session_search(query='<target>')` recovers the audit dir path when the
folder name is not obvious.

Never conclude "no data" from a stale `find` on the home directory: audit dirs live on `D:`, and
the pre-built `deep-audit-mode.py guard` status for an old round is often `BLOCKED` because
`tools-usage.json` was never written — that reflects the round's pipeline bookkeeping, **not**
the validity of findings the vendor has already accepted in writing.

## Step 2 — Build the reported-map, then cross it with scope

Two lists, then a set difference:

1. **Reported** — unique outbound report subjects (dedupe case-insensitively; "Supplement
   to X" and "Correction to F37" collapse into their parent).
2. **In scope** — the program's current in-scope host list.

Anything in the scope list that appears **nowhere** in the reported list is surface the
vendor has not adjudicated. That set difference is the only defensible way to claim
novelty, and it converts a huge scope into a short, honest shortlist.

Then subtract, before probing:

- third-party-hosted assets the policy excludes (docs, wiki, games, status pages, SaaS
  dashboards, mirrors) — these are OUT regardless of what they serve,
- hosts whose only live endpoint is `/health`.

Measured on RunONFlux (2026-10-27): 263 in-scope hosts → 188 never named in any of 60
prior reports → after removing third-party and thin services, the genuinely new
first-party surface was a handful of hosts.

**Also cross-check ownership, not just the name.** A subdomain of the target is not
automatically the target's software. Confirm the API base the frontend actually calls —
a `admin.<target>.com` panel whose bundle points at `api.<other-company>.tv` is a
third-party product and is OUT. Grep the bundle for absolute URLs before spending time.

## Step 3 — Calibrate severity against the vendor's prior grading

When the vendor has already graded a class, **their grading is the reference point, not
yours**. If you rate it High and they rated it Low, re-read their reasoning before
disputing it — on Titan they were right: the exposed data was payout bookkeeping largely
derivable from a public ledger.

Two calibration rules that came out of that:

- **On-chain derivable data is not confidentiality.** For web3 targets, if the exposed
  fields (address, collateral, tx, payout bookkeeping) can be reconstructed from the
  public ledger, the confidentiality claim drops a tier. Only off-chain secrets — email,
  KYC, credentials, session tokens, identity linkage — hold High/Critical.
- **A credential exposed is not a credential used.** "I fetched the invoice with my own
  token" is High at most. Only "the response **contains** the victim's session token",
  replayed successfully, reaches Critical.

Common false-positive patterns in prose-based severity scoring (negated markers, plan text
read as evidence, substring collisions like `enfo**rce**`, tool-credential vs leaked
credential, gate-held-but-still-scored): `references/severity-scorer-false-positives.md`.

### Check the reward FLOOR before writing anything

Read the payout table's **lowest tier** before drafting, not after. A finding below the floor
is worth zero AND costs a triage slot you may want later for a real one.

Measured on Deutsche Telekom (public programme): the table is **P1/P2/P3 only** —
€5,000 / €2,000 / €1,000. There is no Low tier. That single fact decided two calls this
session:

| candidate | technical verdict | decision |
|---|---|---|
| VistaAPI Swagger UI + 290 KB spec, 81 ops incl. `stopProduct` | auth **enforced** on every read (6/6 → 401) and on writes (401 before identifier lookup) → Low | **not submitted** — below floor, no bypass |
| WildFly default welcome page, `Undertow/1` | console not deployed (`/console/` → 302 → `/noredirect.html` 404), both invoker servlets 404 → informational | **not submitted** |
| Unrestricted Google Maps key, 5 billable APIs | live, no referrer restriction, 3/3 reproduced → Low, arguably Medium on cost | **submitted**, and said so in the body: *"a triager may reasonably score it Medium on cost exposure, and I would not argue with that"* |

The middle row is the discipline: a scary-looking result (a spec naming `stopProduct`) is not
a finding once auth is proven to fire **before** identifier lookup. Test that ordering
explicitly with a bogus identifier — `401` rather than `404` is the proof that auth precedes
the object lookup.

**When a finding sits at or below the floor**, record it in the engagement artefact's
negative ledger with the reason, and move on. Do not draft it "just in case", and do not
inflate it a tier to clear the floor — inflating to reach a payout band is the same failure
as overclaiming impact, with a clearer paper trail.

## Step 4 — Provision a test account, or say why you cannot

Self-service signup on a hardened target is often closed. Probe in this order and record
each result — the failure list is itself a finding-shaped artefact for the report:

1. password signup → note the exact error code
2. email magic-link / OOB code → note the error code
3. OAuth providers → note which are advertised vs actually reachable
4. **If you test a password-reset or enumeration endpoint, run the control first**: send
   the same request for a definitely-nonexistent identifier. If both return the identical
   response, there is **no oracle** — do not report enumeration.

Measured on Flux Firebase (2026-10-27): `signUp` → `OPERATION_NOT_ALLOWED`,
`sendOobCode EMAIL_SIGNIN` → `OPERATION_NOT_ALLOWED`, `PASSWORD_RESET` → `200` for both a
real and a nonexistent address (so: **not** an oracle). Only Google OAuth remained, and
that requires an existing account. Documented and moved on, rather than claiming an
unreachable authenticated surface.

Recovering the provider config from the bundle, the three probes that answer "can an account
be created at all", and the `404`-regardless-of-auth signal that means a route is absent
rather than protected: `references/test-account-provisioning.md`.

## Step 5 — Honour what the rejection told you about your own conduct

A vendor reply frequently carries a testing constraint aimed at you specifically. The same
Titan rejection that graded the finding Low also asked to keep live testing to our own
accounts and data, after other users' staking records had been read.

- Treat that as a **hard boundary for every later round**, not a formality.
- It is not a reason to stop the engagement — it is a reason to change the surface and the
  method.
- Report the constraint honestly in the next report; being caught omitting it is worse
  than the original overreach.

## Pitfalls

1. **Do not re-argue a rejected finding with better evidence.** Unless the vendor asked a
   question, a rejection is final. Spend the round elsewhere.
2. **Do not trust "0 findings" on your own sent-list.** Your mail client may not index the
   vendor's older address (`security@vendor.com` vs `security@vendor.io` are different
   mailboxes in a query — search both, and search by domain).
3. **Dedupe by root cause, not by subject line.** A report titled "Supplement to X" is part
   of X, and filing it as new evidence is how a duplicate gets filed.
4. **A 200 from a reset/OOB endpoint is not an oracle until the control fails.** Send the
   nonexistent-identifier control every time.
5. **"No signup" is not "no surface".** Move to hosts whose interesting surface does not
   require the account, rather than claiming the engagement is blocked.
6. **Do not report a gate you could not open.** Eight failed bypass attempts is a verified
   negative, not a finding — and scoring it as a lead is what `severity_ceiling.py`'s
   `GATE_HELD` rule exists to prevent.
7. **Do not treat the auto-ack as triage, and do not let it go unread.** The ack carries the
   ticket number that every later reply must quote, and it may restate OOS carve-outs that
   differ from the programme page. Read it the same day you submit (Step 7).
8. **Do not re-ask "did you send it?" across turns.** When a staged draft shows `SENT`, verify
   via `threadId` + a cron audit, ask the operator **once**, then read the mailbox for the ack.
   Looping on the question delays the only action that resolves it — and on a
   draft-by-default workflow, the operator sending manually is the *expected* case, not an
   incident.

## Step 6 — Write the resume artefact DURING the engagement, not after it

The mailbox search in Step 1 recovers what you **sent**. It does not recover what you
**learned and disproved**. On a long engagement the second one is usually the bigger asset:
the hand-reversed auth protocol and the list of vectors that are already ruled out. Without a
written artefact, a resumed session re-derives both from zero — the most expensive form of
re-work, and it looks like progress while it happens.

Keep one file per target, `references/<target>-engagement.md`, and update it as you go:

1. **Protocol map** — envelope shape, required field *formats*, token prefixes, the exact
   multi-step auth call chain, AppID/tenant constant map. Anything you spent more than ten
   minutes reversing belongs here verbatim; it is unrecoverable from the UI and often not in
   any docs.
2. **Verified-negative ledger** — one row per disproved vector with the *denial string*.
   This is the highest-value section: it prevents re-testing, and it is the raw material for
   the COVERAGE section of the final report (`diuji:` vs `BELUM diuji:`).
3. **Reported / in-flight** — what was filed, what severity, what the vendor replied.
4. **Resume queue** — the surfaces you identified but did not reach, in priority order.

Two rules that keep this honest:

- Record the denial **string**, not your interpretation of it. `-11002002 "the user does not
  have permission"` is evidence; "authz looked fine" is not reusable.
- Record false positives you personally created and killed (an embedded key that turned out to
  be a library test fixture, a `code: 0` write that landed on the caller's own object). They
  are the vectors a future session is most likely to re-chase and re-believe.

Example artefact: `bug-bounty` → `references/vesync-iot-engagement.md` (VeSync IoT — full auth
chain incl. the two-different-token-exchanges trap, 17-item negative ledger with denial codes,
and the untested-store queue).

## Step 7 — Read the acknowledgement the same day; the ticket number is load-bearing

Submission is not the end of the round. Most programmes auto-ack within minutes, and that
ack is **operational data you need**, not a receipt to archive.

Measured on Deutsche Telekom (2026-10-29, two reports submitted ~1 h apart):

```
CDR#2026102942015633   M2M Customer API (Medium)   ack 16:04:45 +0100
CDR#2026102942016703   Google Maps API key (Low)   ack 17:14:00 +0100
```

What the ack actually carries — all of it actionable:

| element | why it matters |
|---|---|
| **Ticket / CDR number** | The ack states *"Any further communication related to this case must refer to this ticket number in the subject."* Follow-ups sent without it are at risk of being filed as new mail. Put `[CDR#…]` in the subject of every later reply. |
| **Auto-ack ≠ evaluation** | The text is *"will be evaluated individually and we will contact you in the upcoming days."* Nothing has been triaged yet. Do not read silence-after-ack as rejection, and do not read the ack as acceptance. |
| **Restated OOS carve-outs** | The ack may re-declare exclusions that also sit on the programme page. Telekom's restated the PHP RCE carve-out (`CVE-2026-109618` / `CVE-2026-109619`: accepted, **not rewarded**). If the ack's carve-out list is longer than the page's, the ack wins for this engagement. |
| **One ticket per report** | Two reports = two tickets. Never merge them into one thread later; each has its own adjudication. |

**Do this immediately after submitting**, not next session:

1. Search `from:<vendor-domain>` and read every inbound message, oldest first.
2. Record ticket numbers into the engagement artefact (Step 6, item 3).
3. Install a reply watcher so a human reply surfaces without you polling. Watchdog shape:
   print **nothing** when there is no new mail, alert on any inbound from the vendor domain,
   seed the seen-set from the acks so they do not re-fire. Runnable pattern:
   `scripts/vendor_reply_watch.py`.

### Send provenance: a `SENT` label you did not create is a question, not a crisis

On an engagement where reports are staged as **drafts** (the default-safe workflow), a report
can appear as `SENT` because the **operator sent it manually**. That is normal and it is the
intended division of labour — the agent stages, the human decides.

Verify once, then move on. Three checks settle it:

1. **`threadId` matches the draft you created** → the content is yours; only the send action
   differs.
2. **Audit scheduled jobs** for any `drafts.send` / SMTP path. If every job is a read-only
   script watcher, no automation sent it.
3. **Ask the operator exactly once.**

Then go read the mailbox. The ack will confirm delivery and give you the ticket number. Asking
repeatedly across turns is the actual failure: it burns the operator's attention and delays the
one action that resolves the ambiguity (Step 7). **One question, then verify from the ack.**

## Step 8 — "We believe this is fixed" is a request for evidence, not a closing note

The highest-value email in an engagement is the one where the vendor says *fixed* and asks you
to confirm. It is the last gate between a report and a **credit + token of appreciation**, and it
is trivially losable: reply "looks good, thanks" and you have confirmed nothing, given triage no
artefact, and left the payout resting on their goodwill.

**Never confirm a fix from memory or from their changelog. Re-run the PoC live, in the same
session, and reply with the transcript.**

### The re-verify pass (mandatory before replying)

1. **Re-run the original request verbatim — THREE independent rounds, not twice.** Same endpoint,
   same body, same headers, **fresh cookie jar / session per round**. Two byte-identical
   responses separate "fixed" from "flaky", but they do not satisfy the operator's standing
   `min 3x` bar for a claim — and if they have to ask *"itu udh d tes ulang min 3x?"*, the answer
   is already no. Measured 2026-10-31 (FIRST.org): F1 was re-verified **twice** before replying
   and the operator caught it immediately. Cost of the miss is the whole credit.
2. **Capture before/after side by side.** The *old* response string lives in your evidence dir
   (`evidence/validation_run*.txt`); quote the new one next to it. A fix reply without the
   original behaviour is unverifiable.
3. **Run a negative control whose output actually DIFFERS.** "A bogus siteKey is now evaluated and
   rejected → enforcement is real" is **not** valid reasoning, and it was disproved live on
   FIRST.org (2026-10-31): `siteKey=nope.invalid` returned a **byte-identical** body to the real
   siteKey, so that control could not distinguish anything. See `probe-validation` §2l.

   What actually worked — **branch discrimination**. Enumerate the distinct rejection branches and
   show that the unverified request lands on the *intended* one rather than being bounced early:

   ```
   broken __req   -> "This request is expired or invalid."      (CSRF branch, EARLIER)
   unverified tok -> "requires additional verification ..."     (captcha branch, the one we want)
   burst volume   -> "sent more requests than allowed ..."      (rate-limit branch, THIRD)
   ```

   Three different strings from the same endpoint prove the captcha check is a real, separate gate
   that the request actually reached — far stronger than a control that agrees with the target.
   On F2 the discriminating control was `client_id=bogus → 400 invalid_client` while all six
   `redirect_uri` variants gave `400 redirect_uri_mismatch`: different errors prove both parameters
   are still evaluated, i.e. the endpoint is not simply failing open.
4. **Sweep every variant you originally reported.** If F2 had 6 redirect_uri tricks, re-test all
   6. A fix that closes 5 of 6 is not a fix, and reporting it as one costs you the credit.
5. **State explicitly what you did NOT replay.** Deliberately skipping the side-effecting step
   (the `/auth/confirm` that mails a victim, the code exchange that mints a token) is a
   discipline signal vendors notice — and it stops you claiming a proof you did not run.
6. **Save the transcript to disk** and attach it. `evidence/reverify_<date>/reverify.txt`.

Measured on FIRST.org (2026-10-31): F1 went from
`{"success":true,"score":0.40,"token":"eyJ..."}` to
`{"success":false,"score":0.6,"wouldBlock":true}` (no token field, 2 identical runs);
F2 went from `302 → https://evil.example.com/cb` to `400 redirect_uri_mismatch` with no
`Location` header on all six variants. Both confirmed fixed, and the vendor had already
committed in writing to HoF credit + token.

### Reply anatomy that gets the credit closed out

1. Thank them, and **echo their root cause** back ("outdated FCaptcha build allowing tokens for
   unverified PoWs") — it proves you read the reply and it locks their admission into the thread.
2. Pasted before/after request + response blocks, in the mail body. Not only in the attachment.
3. The negative-control result.
4. An explicit scope statement: what was not replayed, so no victim-side emails were sent and no
   tokens were minted during verification.
5. **Ask for the close-out**: "could you let me know once the credit and the token of
   appreciation are processed?" — without this the thread dies silently and the HoF entry
   never appears.
6. Reaffirm the credit handle ("Mr Fz"), attach the transcript, sign off.

### Thread mechanics — reply, never start a new mail

The operator's instruction is usually literal: *"jgn buat email baru, tp balas d thread email
masing2"*. One finding = one thread = one reply. Two findings = two separate reply drafts, never
merged into one mail (per-report adjudication, per-ticket accounting).

Use `scripts/threaded_reply_draft.py`. It exists because the stock helper cannot do this job:

- `gmail_ops.encode_mime()` has **no attachment support** and only sets `In-Reply-To`; a reply
  that needs evidence attached has to be built with `MIMEMultipart("mixed")` wrapping an
  `alternative` part plus a `MIMEApplication`.
- Pass `threadId` **on create**, and additionally set `In-Reply-To` + `References` to the real
  parent `Message-ID`. Set both and then **re-fetch the draft** — Gmail will silently open a new
  thread if the two disagree, and an out-of-thread reply on a Freshdesk ticket is filed as new mail.
- `gmail_ops.pick_service()` returns `(label, service)`. Unpack it. `svc.users()` on the raw
  return raises `'tuple' object has no attribute 'users'`.
- Verify after staging by listing the thread and confirming the draft is the last message in it.

### Pitfalls specific to this step

1. **Old report drafts rot.** A draft staged at report time can be gone weeks later
   (`drafts().get` → 404) while its sibling survives. Do not assume the pre-fix draft still
   exists; check each id, and treat a missing one as "the report was already sent", not as data loss.
2. **Do not delete the stale pre-fix draft just because it is superseded.** Confirm with the
   operator first; draft ids are not recoverable from the conversation.
3. **`/auth/confirm`-style replay is a real side effect.** Re-running a step that dispatches mail
   to a third party during a *verification* pass is unnecessary and looks careless. Skip it and say so.
4. **Do not upgrade the finding's severity in the fix reply.** The message being answered is
   "is it fixed?". Re-arguing impact at close-out risks the credit you already won.
5. **HTML-escape the body, and round-trip the draft before sending.** The reply is
   `multipart/alternative`; if the HTML part is built as `<pre>{body}</pre>` with the body
   interpolated raw, every `<...>` in the text is parsed as a tag and **deleted from what the
   recipient sees** — Gmail then regenerates the plain-text part from that same broken HTML, so
   both copies lose it. Measured on FIRST.org (2026-10-31, already-sent): `<unique per request>`
   and `<variant>` vanished, leaving `&state=` and `&redirect_uri=` blank in the delivered mail,
   while the attachment stayed intact. Use `html.escape()` (or `gmail_ops.html_pre()`), then
   **re-fetch the draft and diff it against the source file**:
   `lost = set(re.findall(r"\S{3,}", source)) - set(re.findall(r"\S{3,}", delivered))` must be
   empty. Whitespace rewrap is normal and harmless; a missing *token* is data loss. Never hand a
   draft to the operator unverified — they will send it from the Gmail UI and the loss becomes
   permanent.

## Pipeline position

```
0A   before scoping          -> mailbox search: what did I already send?
0A   after scoping           -> reported-map x scope-list = un-adjudicated hosts
0B   recon                   -> subtract third-party + thin services; verify API ownership
0C   scoring                 -> calibrate against the vendor's prior grading
0E/0F                        -> only submit what the vendor has not already decided
```

## Related

- `scripts/threaded_reply_draft.py` — stage an in-thread reply draft with attachment + verified
  `References` chain (Step 8). Never sends.
- `scripts/vendor_reply_watch.py` — watchdog that surfaces a new vendor reply without polling.
- `references/fix-confirmation-reverification.md` — full worked recipe for Step 8: the 3-round
  fresh-session harness, the **CSRF-token trap** that silently turns every test into
  `"request is expired or invalid"` (and the naive classifier that mislabels it as a captcha
  rejection), replaying the form **verbatim including the shipped `_utoken="none"` default**, why a
  rate-limit branch must be disclosed rather than folded into either column, `bool(token)` vs
  `"token" in body` after a fix nulls the field, branch-discrimination controls that replaced the
  non-discriminating `siteKey` control, generating attachments from the same JSON as the verdict,
  and the safe delete-after-verify order for superseded drafts.
- `lead-to-critical` — ceiling scoring, climb plays, per-class crossing artifacts.
- `triage-validation` — the 7-Question Gate; GATE 4 owns program-policy compliance.
- `disclosure-followup-evidence` — when the vendor asks for a specific repro or commit.
- `program-shortlist-verification` — picking which target to engage next.
- `target-pool` — the local target pool to query before starting.

## Absorbed playbooks (complete sub-packages under `references/`)
Scope note: this skill now covers the whole engagement lifecycle — pick target, find the contact,
submit, survive the follow-up, then resume later.

- `references/program-shortlist-verification/PLAYBOOK.md` — Phase 0: profile the reference target by
  product shape, verify liveness/registrability before proposing an order, the pause/retire keyword
  trap (`scripts/policy_verify.py`).
- `references/disclosure-contact-discovery/PLAYBOOK.md` — Phase 1: `security.txt` as scope document,
  SMTP `RCPT TO` mailbox probing, the near-miss domain trap, the legal-PDF address, GitHub-issue
  mining, and the published-address black hole (parse the DSN, do not eyeball it).
- `references/disclosure-followup-evidence/PLAYBOOK.md` — Phase 3: answer the follow-up item by item,
  a self-asserting reproduction script, the bundle manifest, correct thread reply, re-testing every
  write path after "we fixed it", and retracting cleanly when the vendor disproves the claim.
- `references/proton-engagement/PLAYBOOK.md` — worked vendor dossier (Proton AG): scope, policy
  constraints, channel notes. Pattern for any vendor-specific dossier.
