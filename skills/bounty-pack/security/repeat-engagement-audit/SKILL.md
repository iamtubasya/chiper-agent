---
name: repeat-engagement-audit
description: "Dedup a target against prior audit rounds before recon."
author: Hermes Curator
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, audit, dedup, session-history, repeat-engagement]
version: 1.0.0
---

# Repeat-Engagement Audit — check history BEFORE recon

## When to Use

Load this at the very start of 0A — **before the first `subfinder` call** — whenever you did not
personally audit this exact target earlier in the *current* session.

Applies to any target, including one the operator has just named for the first time in this chat.
A target being new to *this conversation* says nothing about whether it is new to *this machine*.

---

## Why this exists

Measured 2026-10-30 on `relay.link`. The session opened with "Gas target relay", ran 0B recon,
pulled three OpenAPI specs, swept auth-bypass shapes, ran nuclei, grepped JS bundles, probed the
RPC namespace, and checked subdomain takeover — hours of real work — and only then called
`session_search`. It returned **three prior rounds plus a deep-dive** on the same target:

| round | date | result |
|---|---|---|
| R1 | 2026-10-03 | 0 validated, 3 observations |
| R2 | 2026-10-15 | 0 validated, 4 observations |
| R3 | 2026-10-18 | 0 validated, 6 observations |
| deep-dive | 2026-10-07 | R5 (Low) filed |

Roughly **90% of that session's work was a duplicate**, reaching conclusions the prior rounds had
already written down. Worse: the prior rounds had left an explicit residual-gap list
("lighter-vm API-sourced amount — needs live Lighter tx to diff") — precisely what should have
been the session's *opening* task instead of its footnote.

The cost is not just wasted budget. The operator paid for a run that produced no new information,
and the report had to admit it.

---

## Step 1 — the history check (5 minutes)

```
session_search(query="<target> audit findings", limit=5, sort="newest")
session_search(query="<target> validated observations", limit=5)
```

Search by target name **and** by the product/protocol name — prior rounds may be filed under
either.

Then on disk, in this order — prior runs often survive in one of these even when another is gone:

```bash
ls -d ~/.chiper/skills/bounty-pack/poc-plans/*<target>* 2>/dev/null
ls -d "/d/data hermes"/*<target>* 2>/dev/null
ls -d ~/.chiper/skills/bounty-pack/_progress/*<target>* 2>/dev/null
find /c/Users/$USER "/d/data hermes" -maxdepth 5 -name "findings.json" -path "*<target>*" 2>/dev/null
find /c/Users/$USER "/d/data hermes" -maxdepth 6 -type d -name "COVERAGE*" -path "*<target>*" 2>/dev/null
```

**Never conclude "no prior work" from one missing directory.** Measured 2026-10-30: both
`/d/data hermes/_progress/relay_link_v1` and `/d/data hermes/relay` were **gone from disk**, while
the findings were fully recoverable from session history. Disk absence ≠ history absence.

---

## Step 2 — turn the result into the plan

### A. No prior work → normal phased audit.

### B. Prior work exists, ended NEGATIVE → do not re-run the same phases

Open with the prior run's **residual-gap list**, not with recon. Every honest report ends with a
"not tested / blocker" section; that section IS your task list. Ask of each item: has the blocker
lifted? (account now available, API key obtainable, a tx hash now exists, a fix shipped?)

If the gap list is empty and the negative was clean, the correct move is to **tell the operator
the target is exhausted and propose a pivot** — not to burn four phases re-confirming it. Saying
"4 rounds, same answer, recommend pivot" is a better deliverable than a 5th identical round.

### B2. An inherited residual gap is a HYPOTHESIS, not a finding

The prior round's "not tested / blocker" line is a note about *what they did not check*, written
without evidence. It carries whatever framing the previous session imagined, and that framing is
usually more alarming than the truth. **Re-derive it from primary data before you build on it.**

Measured 2026-10-30, relay round 4. The inherited gap read *"lighter-vm API-sourced amount — needs
live Lighter tx to diff"*, i.e. the attestor credits a deposit using an amount taken from a REST
API rather than a verified balance delta, with a sibling adapter (`solana-vm`) that *does* clamp to
the balance diff. That reads like an over-credit bug on a $16k depository.

Pursuing it produced a clean-looking crash PoC — and it was wrong. The sample had been filtered by
an explorer **label substring** (`"ransfer"`), which unions `InternalTransfer` (type 0) with
`L2Transfer` (type 12). Type 0 carries a reduced 6-field payload; the attestor guards
`if (tx.type !== TransactionType.TRANSFER) return []` *before* parsing, so those records never reach
the dereference. Re-sampled correctly (enum resolved from the SDK, filtered to real inbound deposits
into the configured depository) → **20/20 with all 13 expected fields present**, amount exactly
equal to the explorer's `pubdata.amount`. No bug.

Two rules follow:
- When a gap names a *code path*, your first job is to establish which **input population** reaches
  it. Print the discriminator values of your sample and confirm the target's own guard accepts that
  class, before you claim the guard is missing.
- A gap that survives a genuine attempt to kill it is worth reporting; a gap that dissolves under
  correct sampling is worth a **retraction note in the report**, because the next round will
  otherwise inherit the same phantom.

The retraction is not a wasted round. It closes the item permanently and it is the honest output.

### B3. Prior round was TRUNCATED, not concluded — the mid-session observations ARE the gap list

Not every prior round ends with a summary. Measured 2026-10-30 on `zenya-software.com`: the only prior
session touching the target ended with several **empty assistant responses** and the operator typing
"lanjutin" / "ulangi" / "mana, kok blm kamu kerjakan". There was no residual-gap section, no
conclusion, no COVERAGE-LEDGER — the round simply died mid-flight.

Two consequences:

1. **Scroll to the session tail and read the last substantive assistant message.** That is where the
   round actually stopped, and its observations are the only handover you get. On Zenya the tail named
   four live hosts with their exact behaviour (`t` = Cloudflare 0-byte 200; `marketing-mcp` = `/chat`
   UI + `/mcp` 401; `collect` = 400 on every analytics-beacon shape; `community` and `e` = redirects
   out of scope) plus one explicit lead ("`/swagger/` 404 page = Iris app serves HTML without a SAML
   redirect — there is a non-gate path"). Those five lines were the round's real output, and
   re-deriving them cost most of an hour.
2. **Do not treat "no findings recorded" as "nothing was found".** A truncated round may have had a
   live lead it never got to write up. Assume the opposite of a clean negative until you have read
   the tail.

### B2b. The prior round may be filed under a DIFFERENT target's name

The Zenya work above lived inside a session titled **"CDN77 Offensive Recon and Bug Hunting"** —
Zenya was a side-target in someone else's engagement and the title never mentions it. Searching
`session_search(query="zenya")` on the bare domain string is what found it; searching by topic
("marketing-mcp intranet findings residual gap") returned **zero** results.

**Search the raw domain string, then the product name, then the hostnames — in that order — and do
not stop at the first empty result.** A target being absent from every session *title* proves nothing.

### C. Prior work exists with an OPEN finding → verify current state, do not refile

Check whether it is still live, whether it was fixed, whether it regressed. Never resubmit a
previously-filed finding without new information — that is noise to the program and costs
credibility. "Filed" also means an **unsent Gmail draft**: a prior round may have already drafted
the report to the vendor and only left it unsent (e.g. a `gmail_ops.py draft ...` run with a draft
id the operator is about to send themselves). Re-deriving that same bug and drafting it again is a
duplicate the operator will catch — check pending drafts (`gmail_ops.py drafts` / the recorded draft
ids) before re-drafting.

### C2. Vendor replied "we fixed it, please confirm" → stop hunting, run the re-verify protocol

This is the highest-value state an engagement can reach: credit already promised, all that is owed
is a correct FIXED / NOT-FIXED answer. Do **not** spend the round hunting new bugs.

The prior round's `findings.json` is not evidence of the current state — on first.org it advertised
two staged drafts, while the vendor had replied twice per finding and one draft had been deleted
(404). Read the vendor thread first; re-check every draft id before quoting it.

Full protocol (variant matrix replay, why a control that returns the same body as the target proves
nothing, the FIXED/PARTIAL/INCONCLUSIVE vocabulary, and the reply shape):
`references/vendor-fix-confirmation.md`.

---

## Step 3 — what "re-verify, don't re-hunt" looks like

Measured 2026-10-30 (relay.link R5, originally filed 2026-10-07). The prior record said *"SVM
depository documented as non-upgradable but actually upgradeable"*. Re-hunting that class means
re-reading the Solana programs from scratch. Re-verifying took three RPC calls:

```
getAccountInfo on each program  -> which loader owns it?
    BPFLoaderUpgradeab1e... = upgradeable        BPFLoader2111... = immutable
getAccountInfo on the upgrade authority -> multisig or single keypair?
```

Result: both programs on `BPFLoaderUpgradeab1e`; authority `6Bz8AWW…aMWD` with
`owner = System Program, data length 0` → a **single keypair, not a multisig**. Combined with the
docs page still claiming *"Each contract is non-upgradable"*, R5 was confirmed still open in ~10
minutes instead of a fresh multi-hour audit.

That is the correct shape: **confirm the open item, then spend the remaining budget on the
residual gap.**

---

## Step 4 — record the round

Write the round number and what changed. The next session reads this first:

```json
{
  "target": "<target>",
  "round": 4,
  "prior_rounds": [
    {"date": "2026-10-03", "result": "0 validated"},
    {"date": "2026-10-15", "result": "0 validated"}
  ],
  "new_this_round": ["R5 confirmed still open", "nuclei control-verified: 0 in-scope"],
  "residual_gaps": ["<the one thing still unproven, named precisely>"],
  "recommendation": "pivot | continue on <gap>"
}
```

`COVERAGE-LEDGER.json` in the engagement dir is the natural home.

---

## Pitfalls

### The prior scripts may be gone while the conclusions are not

Do not rebuild tooling that already exists. Before writing a probe script, check
`~/.chiper/skills/bounty-pack/` **and** every skill's `scripts/` dir. This session nearly
re-wrote an asset-coverage generator that already existed at
`skills/security/audit-execution-discipline/scripts/asset-coverage.py` — it was looked for only in
`scripts/`, not found there, and briefly reported to the operator as "missing".

Standing rule: a gate that demands `<artifact>.json` is telling you the generator exists
somewhere. Search the skills tree before concluding a tool is absent.

### A truncated round leaves no ledger — check the session tail, not just the disk

`COVERAGE-LEDGER.json`, `findings.json` and `_progress/` dirs are written by rounds that *finished*. A
round that died mid-flight (empty assistant turns, the operator typing "ulangi" / "lanjutin") wrote
none of them, so the Step 1 disk checks come back empty and read as "no prior work". The history is
still in the transcript. Run the disk checks, but treat an empty result as inconclusive until
`session_search` on the bare domain has also been run. See §B3.

### A "fresh" instruction does not erase history

Operator phrasings like *"abaikan hasil sebelumnya / fresh"* or *"gas"* reset the **baseline for
this run**, not the obligation to know what was already tried. Read the history first, then decide
what "fresh" means — usually it means "do not trust the old conclusions blindly", not "pretend
the old work never happened".

### Repeat rounds need a stopping rule

Four rounds returning the same negative is not persistence, it is a loop. State the count, state
that the answer has not moved, name the one residual gap, and recommend pivot. Let the operator
choose to continue — do not silently start round 5.

### A negative round still owes the operator a deliverable

Do not close a round with "nothing found" and stop. The round's output is (a) the test matrix
proving which controls held, and (b) a staged negative-result report the operator can send.
Shape, tone, the safety-contract paragraph, and the rules for which hardening notes are worth
sending: `references/negative-result-report.md`.

---

## Related (other skills — not files in this skill dir)

- Read the program's payout model before hunting anything: skill `bb-audit-launcher`, file
  `bounty-program-shape-and-payout-model.md` under its own `references/`.
- Money-path testing detail (auth class, signature binding, calldata): skill `bb-audit-launcher`,
  file `money-path-api-audit.md` under its own `references/`.
- Scanner zero-discipline (positive controls, false negatives): skill
  `fuzzing-false-negative-pitfalls`.
