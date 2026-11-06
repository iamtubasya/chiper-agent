# Duplicate / known-issue triage, and reporting a deployment gap

Do this **before** drafting, on every finding you intend to report. It answers two
questions: *has the vendor already fixed this in their repo?* and *if so, is it still
worth reporting?* Getting this wrong costs credibility in one direction and loses a
payout in the other.

## Standing rule (operator, 2026-10-08)

> "duplikat gpp ttp lapor, ktnya ad reward duplikat"

**A known or duplicated issue is still reported.** Several programs pay duplicate
rewards, and a pending-but-not-deployed fix is live risk regardless of who knew first.
Never self-censor into silence because the fix looks public — investigate, then report
with the duplication stated openly. What you must NOT do is present it as novel.

## Step 1 — is the fix already public?

The repository is often public even when you assumed otherwise. Check first:

```bash
# is the repo public at all?
curl -s "https://api.github.com/repos/<org>/<repo>" | grep '"private"'

# commit history for the exact file you think is vulnerable
curl -s "https://api.github.com/repos/<org>/<repo>/commits?path=<path/to/File.sol>&per_page=5" \
  | grep -E '"date"|"message"'
```

A hit like `fix: preserve reentrancy guard across nested calls (#62)` is a disclosure
event with a date. Pull the PR for the full record:

```bash
curl -s "https://api.github.com/repos/<org>/<repo>/pulls/<N>" \
  | grep -E '"title"|"created_at"|"merged_at"|"state"'
```

Also worth a look, cheapest first:
- a test file named after the issue (`*VIG084Test.sol`, `*_advisory*`) — its **assertion
  text states the property the vendor expects to hold**, which is the strongest possible
  confirmation that your finding is a real defect and not a design decision;
- GitHub Security Advisories / the ecosystem advisory DB;
- a plain code search for the guard or invariant you are testing.

If nothing public, treat the finding as novel and proceed normally.

## Step 2 — is it actually deployed?

**A merged fix is not a deployed fix.** This is the whole reason a "known" issue can
still be worth money. Establish the contract's deployment date and compare:

```python
# Sourcify / verified-source payload carries this
dep = payload["deployment"]          # {"blockNumber": 37777618, "transactionHash": "0x…", "deployer": "0x…"}

# then resolve the block timestamp over RPC
# eth_getBlockByNumber(hex(blockNumber), false) -> result.timestamp
```

```
deployed      2025-11-05   (block 37777618)
fix merged    2026-08-27   (PR #62)          <- 9.5 months LATER
today         still vulnerable on-chain
```

If the deployment **predates** the fix and no later deployment carries it, the live
contract is exposed. That is the finding — and it is actionable even though the fix is
public, because the vendor may simply not know their rollout is behind.

To be certain the deployed bytecode (not a local tree) is affected, fork and test against
the live address:

```bash
forge test --fork-url <rpc> --match-path test/Live.run.sol -vv
```

A recovered source can be stale; the fork cannot. This is what converts "the repo has
this bug" into "the contract holding funds has this bug today".

## Step 3 — frame it honestly

Name the duplication in the report rather than hoping nobody checks. It costs nothing
and it protects you if the vendor replies "known":

```markdown
## Disclosure context

The correction is publicly visible in the repository, merged <date> as a commit titled
"<message>", and the repository contains a test whose stated assertion is that <property>.
I am therefore treating this as a deployment gap rather than a novel discovery, and
reporting it because the fix has not reached the contract that custodies funds. If the
issue is already tracked internally, this report should be read as confirming that the
deployed instance remains affected.
```

That paragraph does the work: it pre-empts the "duplicate, closed" reflex, reframes the
submission as *deployment verification*, and keeps you accurate. Do not write it as an
apology, and do not bury it — give it its own numbered section.

## Step 4 — decide what to do with the weak sibling

A common shape: one strong finding plus one genuinely weaker observation on the same
asset. **Two findings = two drafts** (see the anti-slop rule and RULE 0 in
`reportlab-security-pdf` — "same asset" is not a merge reason). If the weak one is too
thin to stand alone against the program's own bar, the honest move is to **drop it**, not
to staple it to the strong report as a "secondary observation". Padding a credible High
submission with a Low dilutes it and invites a downgrade of the whole thing.

## Checklist before you draft

```
[ ] repo public?           curl /repos/<org>/<repo> | grep '"private"'
[ ] fix commit found?      commits?path=<file>  -> message + date
[ ] PR merged date known?  /pulls/<N>
[ ] test whose assertion states the property? (strongest confirmation)
[ ] deployment date        Sourcify deployment.blockNumber -> eth_getBlockByNumber
[ ] deployed < fix?        if yes -> deployment gap, report it
[ ] verified on the LIVE address via fork, not just the repo?
[ ] duplication stated plainly in its own section?
[ ] weak sibling split out or dropped -- NOT merged as a section?
```
