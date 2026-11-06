# Recurring-engagement prior art — check before you re-hunt

**Trigger:** the target or vendor has engagement history — by the operator, by you, or by an
earlier session. Run this before scoring a single lead.

**Why this file exists.** 2026-10-27: the operator asked to "dig deeper" into a High finding
on Flux/Titan. The finding had been reported **and rejected 12 hours earlier**. Deepening it
would have (a) paid nothing and (b) repeated a testing violation the vendor had already
flagged in writing. Both costs were avoidable with one mailbox search.

## Step 1 — Reconstruct the sent map

Search by **criteria**, never by recency. A fixed "last N messages" window silently misses
the relevant thread (same class of error as the IMAP-window trap in
`artifact-backed-claims`).

```python
q = '(from:<vendor-domain> OR to:<vendor-domain>)'
# Gmail API: users/me/messages?q=<q>&maxResults=100
# then format=metadata with metadataHeaders=From,To,Subject,Date
```

Normalize before deduping — both sides mangle subjects:

```python
s.replace("[BUG BOUNTY] ", "").replace("[Bug Bounty] ", "")
# collapse "Re: " / "Re: Re: " prefixes
# dedupe on s.lower()[:60]
```

Split by direction: `from:` containing the operator's address = reports; else = verdicts.

**Flux result:** 77 messages → **60 unique outbound reports**. The duplicate sends
(same finding mailed twice within minutes) are real and inflate the map without dedupe.

## Step 2 — Reconstruct the verdict map

For every inbound reply, extract the **verbatim** rejection phrase per finding. Do not
compress to "rejected" — the reason is the entire value.

## Step 3 — Cross sent map against the in-scope host list

```python
inrep = host.lower() in reported_text or host.split(".")[0].lower() in reported_text
```

**Flux result:** 263 in-scope hosts → 75 name-matched, **188 never named**.

Filter the 188 before probing:

| Bucket | Action |
|---|---|
| third-party hosted (docs, wiki, games, n8n, grafana, status pages) | OUT per most policies — do not touch |
| thin services exposing only `/health` | Low ceiling; usually skip |
| what remains | the real candidate set |

## Step 4 — Read verdicts as an oracle

| Verdict phrase | Meaning for the next move |
|---|---|
| "covered by our internal security audit" | Closed **regardless of severity**. Never re-report the class, not even with a better PoC. |
| "reported before you" / "already known to us" | Closed. Being first is the only gate that pays; a supplement earns thanks, not a bounty. |
| "by design" / "intended" / "compatibility mode" | Closed unless you show a *different* impact the design did not intend. |
| "we rate it Low rather than High, because …" | Real finding, **Low ceiling**. Believe the argument over your own scorer. |
| "please keep live testing to your own accounts and data" | Binding for the rest of the engagement. See Step 5. |

### The severity-downgrade rejection is the instructive one

Flux/Titan, verbatim:

> "Titan staking API (public pending payments and per-ID stake data): already covered by our
> internal security audit, so it isn't eligible for a reward. **We rate it Low rather than
> High, because the data is payout bookkeeping that is largely visible on-chain anyway.**"

That is a correct severity argument, not a brush-off: `payment_address`, `collateral` and
`tx` genuinely are derivable from the public ledger. An unauthenticated IDOR that leaks only
on-chain-derivable data is Low/Medium, not High. The durable rule: **severity is a property
of the data, not of the access-control gap.** Only off-chain secrets (email, KYC, credential,
session token, identity linkage) hold High/Critical.

The same engagement also produced the "gate held but scored High" false positive: notes read
*"8 bypass attempts, all returned 403 -> gate held"* and the scorer still emitted `PURSUE /
High` because the word `secret` appeared in the explanation. A control that held is the
opposite of a finding.

## Step 5 — Testing discipline on a repeat engagement

When a vendor has already paid you and then states a constraint, it is binding:

- Enumerate population **counts** only — never other users' record contents.
- "Digging deeper to prove High" on a rejected finding repeats the exact violation that was
  flagged. That is how a researcher gets disqualified instead of paid.
- If the remaining interesting surface needs an account you do not have (owned node, KYC,
  paid tier), **stop and surface the decision** to the operator. Do not improvise around a
  stated constraint.

## Step 6 — Prefer the untouched surface, and accept a negative

The 188 untouched Flux hosts were mostly hardened thin services. The two genuinely
interesting ones (`manager.runonflux.io` business API, `admin.console.runonflux.com`) both
required a Firebase-authenticated account — a legitimate gate to report back, not a reason to
bend the rules.

**Honest outcome shape.** This round ended as a *verified negative*: surface mapped, auth
differentials run, leads scored, ceiling stated as Low with the reason. That is a deliverable.
It is worth more than one inflated submission to a program that runs a no-reply policy on
improper reports.
