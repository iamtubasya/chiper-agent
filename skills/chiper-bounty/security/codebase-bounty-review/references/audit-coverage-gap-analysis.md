# Mature protocol: find the UNAUDITED surface (audit-coverage gap analysis)

Use when the target is **heavily pre-audited** (a dozen+ audits, large mature codebase, e.g. a
Solana/EVM lending or prime-broker protocol). Reading the code blind is a waste — the audits and the
vendor's own Known-Issues list already cover the obvious. The job is to locate **what the audits
missed**, and to not re-report what the vendor already documents as known.

Worked context (2026-10): `0.xyz` = **marginfi rebrand** (Solana DeFi prime broker). Scope: on-chain
`marginlend` program (up to $500k, needs a localnet/deployed-contract PoC) + infra assets (up to $5k).
12+ audit PDFs in `audits/`, a very complete `SECURITY.md`.

## Step 0 — the `/security` page is the door

A protocol site's security page almost always links to the repo's **`SECURITY.md`** and/or
`docs/<x>/audits`. That single file is the whole engagement: scope, bounty tiers, **the complete
known-issues list**, invalid-report rules, and the contact. Pull it raw:

```
https://raw.githubusercontent.com/<org>/<repo>/main/SECURITY.md      # try main, then master
```

If the site is a Webflow/SPA shell, `grep -o 'href="[^"]*"' page.html | grep -Ei 'bounty|audit|github|immunefi|docs'`
recovers the real links (they live in the HTML even when the rendered text hides them).

## Step 1 — the Known-Issues list IS the dedup map

Before hunting, extract **every** item under `## Known Issues and Scope Clarifications` /
`Invalid Bug Bounties` into a list. Any finding that matches one — even partly — is auto-rejected,
and a triager will bounce you for not having read it. Also read the **Credits** section: it names the
bug *classes* they have actually paid for (e.g. "debts below zero threshold remain after a borrow",
"LST with low staked liquidity inflated by donating SOL to the stake pool"). That is a direct hint at
the shape of report that lands.

⚠️ Doc-comments that pre-emptively list "accepted approximations" / "by design" / "design choice"
are *defences*, not documentation. A finding inside that list is dead on arrival. The live surface is
what is **not** in Known-Issues.

## Step 2 — map audit coverage with the PDFs

Each `audits/*.pdf` covers some modules. Extract text and count module keywords per PDF to see which
audit touched which module, and which modules have **zero** coverage:

```python
from pypdf import PdfReader
KW = ['premium','liquidation record','order','rebalance','variable borrow',
      'circuit break','flow control','emode','receivership','insurance']
for f in sorted(glob('audits/*.pdf')):
    t = " ".join((p.extract_text() or "") for p in PdfReader(f).pages).lower()
    print(f, {k: t.count(k) for k in KW if k in t})
```

- A module with **no hits in any audit** = unaudited → highest-value.
- A module that *is* audited is only a starting point — see Step 3.

Install note (Windows): bare `pip install pypdf` may resolve to a different interpreter and silently
no-op, leaving `No module named 'pypdf'` on the next run. Use the full interpreter path:
`/usr/bin/python3 -m pip install pypdf`, then run
the script with the same interpreter.

## Step 3 — NEW == UNREVIEWED (post-audit commits are the prime surface)

Audits are snapshots. Code committed **after** the last audit on a module is effectively unaudited
even if that module was audited before.

```
git fetch --unshallow            # depth-1 clone hides the history you need
git log --oneline -60 --date=short --pretty=format:"%ad %h %s"
git tag --sort=-creatordate | head -20
git diff --stat <last-audit-tag>..HEAD -- programs/<x>/src
```

Rank modules by **insertions since the last audit tag**. A module with the largest insertion count
*and* no audit-keyword hits is the bullseye. Cross-reference the two lists.

Read the recent commit **subjects** too — a subject like `Fix ... bug (#691)` or `Fix borrow revert
on stale zero-weight collateral` tells you a bug class was *live recently*; hunt its **siblings**
(the same shape elsewhere, or the same file's other branch). Recently-fixed classes are frequently
not fully closed.

## Step 4 — check what is actually DEPLOYED

Newest commits may not be on mainnet yet. `SECURITY.md` usually states whether **release /
pre-release**-flagged code is in scope ("bugs in the most recent code marked for release are also
eligible") — read it, and confirm the deployed program version before claiming an on-chain impact.

## Pitfalls

- Don't report an **audit-known** item. Grep your candidate against the Known-Issues list *and* the
  audit PDF text before writing it up.
- `git log` on a `--depth 1` clone shows one commit. You **must** `git fetch --unshallow` (or
  `--depth N`) before the diff/since-tag analysis means anything.
- The repo may ship the audit reports *inside* the clone (`audits/`) — you don't need to hunt the
  vendor's website for them.
- Solana/Rust PoC is `cargo test` (see `references/soroban-stellar-review.md` and
  `references/source-only-poc-harness.md`); the first build is slow — background it.
- A very complete Known-Issues list is a *signal the target is mature*. Lower the expected hit rate
  and raise the bar for what you write up; verified negatives are the honest deliverable.
