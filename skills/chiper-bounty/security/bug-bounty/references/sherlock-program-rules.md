# Sherlock Platform Rules — submission mechanics, triage exclusions, prior-audit duty

Authoritative sources:
- **Program page = primary source of truth** (individual program on `audits.sherlock.xyz/bug-bounties/<id>`). If the
  program page and code comments contradict each other, the program page wins, and a judge may declare the code
  comments outdated.
- **Sherlock-wide validity criteria:** `https://docs.sherlock.xyz/bug-bounties/criteria-for-bug-bounty-reports-validity`
  (GitBook; fetch and strip tags to read it)
- Many programs state verbatim: *"All reporters should consult Sherlock's Criteria for Issue Validity"* and
  *"All standard Sherlock Bug Bounty Platform Rules and safe harbor provisions apply."* — so this file applies to
  every Sherlock program, not just the one it was learned on.

---

## 1. Submission mechanics (NOT email)

- Submission is a **web form behind a login** — the program page shows a button (labelled e.g. `Report a bug`;
  the page also exposes a `My Submission` tab). There is normally **no bug-bounty e-mail address**.
  - Verify before promising the operator an email channel: grep the vendor docs/site for `@`; if the only hit is
    something like `support@…`, that is a support inbox, not the bounty channel. The docs will say
    *"notified through the official submission process"* / *"through the official Sherlock submission flow"*.
- A **registered payout wallet on the Sherlock profile** is required, otherwise the report cannot be paid.
- **One report = one vulnerability.** Several vulnerabilities ⇒ several submissions.
- Report promptly (programs may require it within ~24h of discovery).
- Never exploit the finding on the live network; the demonstration belongs on a fork/simulation.

## 2. Disclosure gate (all four must be satisfied)

1. the team has been notified through the official process,
2. the issue has been acknowledged,
3. a fix/mitigation is deployed **or** written permission to disclose was granted,
4. Sherlock has completed/approved the disclosure process.

Premature disclosure of a live unpatched issue can disqualify the reward.

## 3. Excluded classes (submitting these = rejected, not "downgraded")

Gas optimizations · wrong values in emitted events · zero-address checks · user-input validation to prevent user
mistakes · admin input/call validation and admin mistakes that break assumptions (incl. an admin action causing
unfair liquidations) · front-running initializers with no irreversible damage · minor UX/inconvenience without fund
loss · a user blacklisted hurting only themselves · future opcode gas repricing · `call` vs `transfer` as a design
choice · **view functions returning incorrect values** (exception: if such a value feeds a larger function that
loses funds) · **stale price / Chainlink round-completeness recommendations** · issues from prior audits marked
*acknowledged (not fixed)* · chain re-org / network liveness · future integrations not in the docs · weird tokens
unless explicitly in scope (decimals 6–18 are **not** weird) · Solidity/EVM-opcode mismatch · sequencer
misbehaviour or downtime · **design decisions** (even suboptimal, if no fund loss ⇒ informational) · lack of storage
gaps · loss of airdrops not part of the protocol design.

Two of these kill whole families of findings that look juicy:

- **Stale-price rule, verbatim:** *"Recommendations to implement round completeness or stale price checks for any
  oracle are invalid."* An exception exists only for pull-based oracles (e.g. Pyth) where the price must be
  requested first. ⇒ An "oracle adapter fabricates a fresh `updatedAt`, so staleness can never be detected"
  observation is **informational at best** and must NOT be submitted as a finding. (Learned on Fira: the adapter
  really did fabricate `updatedAt = block.timestamp`; the correct call was to leave it out.)
- **View-function rule** ⇒ do not spend time on "this getter returns a wrong number" unless something loses funds.

## 4. THE clause that kills "stray/pooled token" findings — and its two escape hatches

Verbatim:

> Users accidentally or intentionally directly transferring any tokens (native, ERC20, etc.) into the in-scope
> contracts, **while it is not a part of the expected protocol operations**, and the contract doesn't have a way to
> retrieve them, is not a valid issue and is considered a user mistake, **if the user hurts themselves only**.
> However, if it leads to hurting the protocol and/or other users, it may be considered a valid issue (if qualifies
> for in-scope severity definitions).

This is the first thing a triager reaches for when a finding needs tokens to be sitting in a contract. Pre-empt it
**inside the report** with a two-row table, because both prongs must be answered:

| Prong | How to defeat it |
|---|---|
| *"…while it is not a part of the expected protocol operations"* | Show the transfer is **required by the protocol itself**: the contract natspec says so (e.g. *"BT/CT must be transferred to this contract prior to calling"*), and/or the protocol's **own router performs that transfer mid-transaction** as part of a normal user flow. Then the resting-balance state is an expected intermediate state, not a stray transfer. |
| *"…if the user hurts themselves only"* | Show the harmed party is a **third party** (pooled/shared balances) and/or **the protocol** — not only the depositor. |

If you cannot satisfy prong 1 **or** prong 2, do not submit; it is an accepted user mistake. Also add the line
*"the vulnerability does not depend on that comment being accurate — it depends on the code"* so a judge who calls
the natspec outdated cannot dismiss the finding through the comments route.

## 5. Duplication is decided by ROOT CAUSE

> If the reported issues have the same root cause or address the same vulnerability, but appear in multiple places,
> even in different contracts, they may be considered to have the same root cause and considered duplicates.

Consequence for report structure: **several reachability ROUTES of one root cause are ONE report.** Typical example:
a permissionless function whose root cause is "reads the contract's pooled balance and pays a caller-chosen
receiver", reachable (a) directly, (b) via the protocol's own router exit path, (c) via an unauthenticated callback.
Splitting those into three submissions produces two duplicates that earn nothing. Present them as *routes* inside a
single report instead.

## 6. Best practices that affect whether it lands

- **Impact must NAME the missing control.** Bad: *"Loss of funds for the user."* Good: *"Loss of funds for users as
  there is no access control for the `withdraw` function."*
- Keep code snippets short — limited to the scope of the impact; be descriptive in the prose sections.
- Do not copy-paste findings from other contests/reports/past audits.
- Scope note: if a contract is in scope, **all its parent contracts are included by default**; a library bug that
  affects an in-scope contract is valid; a bug in a non-scope contract cannot be valid.
- Admin functions are assumed to be used correctly unless the program states otherwise — do not report "admin could
  call things in the wrong order" or "pausing X hurts users".

## 7. Prior-audit due diligence (mandatory before writing the report)

Programs exclude anything already identified in prior audits / internal reviews / docs / acknowledged before
submission. Procedure:

1. Read the program's audits page and list every engagement (firm + date + scope).
2. Try to fetch each report.
3. **Expect that you often cannot.** Observed reality: vendor audits are frequently published as GitBook *file
   blocks* (`/files/<id>`) that return **404 to unauthenticated requests**; audit firms may have no public repo;
   GitHub **code search requires auth**; the `sherlock-audit` GitHub org hosts only *contest* engagements, so an
   audit engagement (as opposed to a contest) may have no repo at all. Web search for the report title usually
   returns only the vendor's own docs page.
4. If you cannot access them: **say so in the report and offer to withdraw.** Do not claim novelty you cannot
   verify. Wording that worked:

   > I attempted to check the prior audits (Sherlock, Spearbit/Cantina, Hexens, yAudit) and could not: the audit page
   > links its reports as GitBook file blocks that return 404 to unauthenticated requests, no `sherlock-audit`
   > repository exists for the engagements, and no Cantina or Hexens report is publicly indexed. I therefore cannot
   > rule out that part of this was raised before. If it was already identified and acknowledged, please treat this
   > submission as withdrawn.

5. If you CAN access them: grep the findings for the contract/function name **and** the bug class before writing a
   word. Cheap to do, fatal to skip.

## 8. Pre-submit checklist

- [ ] account exists **and** payout wallet registered on the profile
- [ ] exactly one vulnerability in the submission
- [ ] severity justified with manual CVSS + an explicit *proved vs argued* table (honest downgrade over overclaim)
- [ ] impact sentence names the missing control
- [ ] PoC reproducible, with measured numbers and the exact command
- [ ] every exclusion in §3 checked — especially the pooled-balance clause (§4) and the stale-price rule
- [ ] prior-audit duty done, or the inability disclosed with a withdrawal offer (§7)
- [ ] nothing disclosed publicly; disclosure gate (§2) understood
- [ ] all vendor-facing artifacts in English

## 9. Worked example (Fira protocol, program #298)

Finding: `CouponToken.redeemBC(receiver)` is permissionless, computes the amount from the contract's **own** pooled
`BT` balance, and pays the FW to a caller-chosen address ⇒ third-party theft, proven with a mainnet-fork PoC
(attacker holds 0 BT/0 CT; victim parks 50 BT; attacker receives 49.984443 FW; victim 0; 188,639 gas).

How the rules above shaped it:
- §4 pre-empted with both prongs (the natspec *requires* the transfer and the protocol's own router performs it
  mid-transaction; the harmed party is a third party) — this was the single highest-value paragraph in the report.
- §5 kept three reachability routes as **one** report.
- §3 stale-price rule ⇒ the oracle-adapter observation was deliberately **not** submitted.
- §7 prior audits were unreachable ⇒ disclosed, with an explicit withdrawal offer.
- §6 impact phrased as *"there is no access control on redeemBC and the amount comes from the contract's pooled
  balance"* rather than "users lose funds".
- Graded **Medium, not Critical**, because the stealable balance was 0 at the time; the report states plainly that
  High is arguable — an honest downgrade is worth more than an inflated claim that gets closed as invalid.
