# Protocol recon BEFORE claiming novelty

Four cheap checks that decide how a finding must be *framed*, and whether a hypothesis is worth
the hours. Each one was learned the hard way on a target where skipping it would have produced a
wrong report.

Run them after you have a candidate, before you write a single word of the report.

---

## 1. Grep the protocol's own repo for the vulnerability class

Before writing "I found X", search the repo for the vocabulary of X — test names, comments,
audit notes, commit subjects. Protocols frequently ship a test that asserts the property you
think is missing, or name the class explicitly.

```bash
grep -rniE "reentran|depth|guard|nonReentrant|invariant" --include=*.sol --include=*.md .
git log --oneline -S "<the vulnerable function>" -- <path>   # when was it touched, and why
git log -1 --format='%h %ad %s' --date=short -- <file>       # last change to this file
```

Real case (Relay v3 Router): a test named `VIG084Test.sol` existed and its stated assertion was
the invariant in question, and a commit titled *"fix: preserve reentrancy guard across nested
calls"* was merged 2026-08-27 — while the deployed contract was from 2025-11-05. That turned the
report from "novel discovery" into **"deployment gap: the fix exists and has not reached the
contract holding funds"**.

That reframing is not a downgrade. It is the difference between a report the team rejects as
"already known" and one they act on immediately. **Say it in the report yourself** — a disclosure
note that voluntarily names the public fix costs nothing and protects you if they reply
"duplicate".

## 2. Check what the published audits ACTUALLY covered

Protocols list audits that sound comprehensive and are not. Read the scope line, not the title.

The Relay `docs/audits/README.md` table read:

| Report | Date | Scope |
|---|---|---|
| Certora | Jun 2025 | **Solana** programs |
| Zellic | Nov 2025 | **Solana** depository + settlement |
| Zellic | Apr 2026 | `relay-protocol-oracle` — **TypeScript**, `src/**/*.ts` |

Three audits, **zero coverage of the EVM contracts** — the ones holding funds. Without reading
that table you would assume "three audits = well covered" and either skip the EVM contracts or
misjudge the novelty of what you find there.

Rules:
- **VM / language mismatch is the trap.** `RelayDepository` exists on *both* Solana and EVM;
  an audit of "Relay Depository" may mean only one of them. Check the repo path in the report.
- The README usually states the audited **commit hash** — compare it against the deployment
  block/time. An audit at commit A does not clear a contract deployed at commit B.
- Quote the scope line in your own notes so you can cite it later.

## 3. Separate "already reverted" from "still live"

A same-named contract can be superseded. On Base there were **two** Relay routers:

| address | chains | guard |
|---|---|---|
| `0xe6b730e5…` | 54 | corrected |
| `0xb92fe925…` | 22 | vulnerable |

The repo's own `deployments/v3/addresses.json` named `0xe6b730e5…` for Base — but the protocol's
**live quote API** returned `0xb92fe925…` in current order data. The registry was stale.

**A deployment registry enumerates candidates; it does not evidence what is live.** Settle it
from the protocol's own API, or from a fork probe against the address you actually intend to
report — never from the registry alone.

---

## 4. Read the NatSpec of the function you are attacking — the author may have named your hypothesis

Before spending time on the maths of a substitution / replay / collision attack, read the doc
comment above the function. Good authors document the exact threat they defended against, and
that tells you in seconds whether your idea is alive.

Real case (`lit-deposit-address/src/attestation/index.ts`), the comment on `verifyOrderData`:

> *"…`derivationFields.solver` is the relay-protocol `ethereum-vm` virtual address derived from
> `(order.solverChainId, order.solver)`. This binds the order's solver to the wallet derivation
> path **so a malicious caller can't substitute a different order with the same derivation
> fields**."*

I had spent effort on a collision attack: the deposit address is
`keccak256(abi.encode({…, depositor, salt}))` → 8 × uint31 **non-hardened** BIP32 indexes, and
two of those fields (`depositor`, `salt`) were not cross-validated against the order. The plan was
to forge a trigger whose derivation path collided with a victim's so their deposit landed in a
shared address.

Two things killed it, and both were cheap to check:
1. **the comment** — the authors had already reasoned about exactly this and bound the solver;
2. **`salt` is `randomBytes(32)` per trigger** — a collision is a 2^248 search, i.e. not one.

The lesson is not "give up when you see a comment". It is: **the comment tells you which
sub-field the author *thought* was load-bearing, so you can attack the one they didn't mention**
— here `depositor`, which turned out to feed the on-chain event attribution instead (a real, if
backend-dependent, issue). Read the defence to find its edge.

Corollary: a thorough-looking validator is not proof of completeness. `verifyOrderData` checked
input weight/chainId/currency/amount, **every** refund entry, output chainId/currency/recipient,
price expiry, recomputed `getOrderId`, the solver's EIP-191 signature, and the solver↔path
binding — and it still never mentions `depositor`. Enumerate what a validator checks, then look at
what is left over.

---

## Why these belong together

All four answer the same question the triager will ask first: *"is this new, is it in scope, and
is it live?"* Answer it yourself before they do. A finding that survives those questions is worth
ten that don't, and the ones that fail are still reportable — as deployment gaps, which get fixed
faster than novel findings get triaged.

And when a hypothesis dies (all four of these kill hypotheses, not just reports): **say so, with
the number that killed it.** "100k gas is plenty — the 5th cold SSTORE is the first to revert" is
a useful negative. Silently dropping a dead hypothesis leaves the next auditor to re-walk the same
path; dressing it up as a finding is worse.
