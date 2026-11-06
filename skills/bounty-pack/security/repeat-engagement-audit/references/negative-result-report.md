# The Negative-Result Report — how to close a round that found nothing

**Load at:** the end of any round where the attack did not work and the honest answer is
"the control held". Companion to the stopping rule in `SKILL.md` §Pitfalls.

---

## Why send anything at all

A repeat round that ends negative has three possible outputs:

| Output | Verdict |
|---|---|
| Silence | Worst. The operator paid for the work; the vendor is entitled to know the control was tested. Silence also makes the next round indistinguishable from never having run. |
| A dressed-up vulnerability | Worse. Costs credibility and can trip a strike rule. |
| A **negative-result report** | Correct. It is a real deliverable with real content. |

The content is not "I found nothing". The content is **which controls held, proven how**, plus
whatever genuinely survives the filter.

---

## Shape that works (measured 2026-10-30, fee-claim endpoint)

### 1. Verdict first, unhedged, in two sentences

> "I tried to claim fees belonging to a wallet I do not control. I could not. I am not
> submitting a vulnerability claim, and I am not asking for a reward."

A vendor reads a negative report scanning for whether you are about to waste their triage time.
Disarm that in sentence one. Do not build suspense.

### 2. State the safety contract explicitly

This is what makes an aggressive test read as research rather than attempted theft:

> "Every signature I submitted was produced by a freshly generated throwaway key holding no
> fees. I never possessed a valid owner signature, so no funds could move at any point. No
> transaction was broadcast and no on-chain call was made."

Name what you did **not** do. It is the single most load-bearing paragraph in the document.

### 3. List what held, as a table of tests

This is the actual value to the vendor: they learn which controls were exercised. One row per
test, each with the concrete response observed.

```
- A signature from a non-owner is rejected with 400 "Invalid signature". Verification binds to
  the fee-owning wallet, not to the recipient.
- The recipient is bound into the requestId commitment: three different recipients for the same
  wallet and amount produced three different requestIds.
- The amount is bound the same way: null, 1000000, and 50560170 each produced a distinct id.
- requestIds are single-use. Resubmitting the same id returns "inexistent or expired".
- There is no existence oracle: all-zero, all-ff, and random 32-byte ids all return the same error.
- Amount tampering is rejected by ^[0-9]+$, a $0.05 minimum, and an "Insufficient balance" check.
- Signature encoding abuse is rejected: v normalized to 0/1, v=255, 64-byte truncation, 66-byte
  padding, r=s=0, high-s, and all-ff.
- Path-traversal forms do not change which wallet is debited.
- A mainnet requestId is not valid on testnet.
```

Close the list with the one-sentence summary a triager can quote: *"Claiming someone else's fees
requires their private key. That is the correct design and I could not find a way around it."*

### 4. Separate the hardening notes into their own section, labelled as notes

For each: the observation, the raw evidence (exact inputs → exact responses), and the **bounded**
impact. Bound it explicitly — "error-classification noise only", "no fund loss observed", "not
exploitable by itself".

### 5. Quote the program's own exclusion clause against each hardening note

This is the credibility move. If the policy says *"DoS with no fund loss and no path to fund
loss"* or *"issues requiring phishing, social engineering, or a compromised private key"*, name
the clause and say *"I am not claiming otherwise."*

A researcher who pre-empts the triager's rejection is trusted on the next report.

### 6. Close with the offer and the stop condition

> "I can provide the full request/response transcripts or reproduction scripts if useful. If you
> would prefer I stop testing this surface, tell me and I will."

---

## What makes a hardening note worth sending rather than dropping

Both must be true:

1. It is **cheap for them to fix** — a `try/catch`, a throttle, an EIP-712 struct.
2. It is the **prerequisite for someone else's attack** even though it is not one itself.

Blind signing is the canonical example: the server-side commitment is correctly bound, so it is
not exploitable alone — but an unauthenticated "prepare" step that accepts `recipient = attacker`
plus an opaque 32-byte hash to sign is exactly the raw material a phishing flow needs. Say that
plainly and let them decide. Do not escalate it into a claim.

---

## Hard rules

- **No CVSS score on a negative report.** There is no finding to score.
- **Do not invent an impact to justify the message.** If nothing survives, the test table alone
  is the deliverable.
- **The subject line must promise exactly what the body delivers** — e.g. *"authorization test
  results (negative) + 3 hardening notes"*. A subject implying a vulnerability, followed by a
  negative, burns trust.
- **Default to DRAFT.** Stage it, show the operator, let them decide to send.
- One email per issue; check the program's stated channel before writing.

---

## Where the artefacts go

| File | Content |
|---|---|
| `<engagement>/<AREA>-REPORT.md` | the full test matrix + hardening notes |
| `<engagement>/<AREA>-EVIDENCE.txt` | raw request/response transcript, appended by the verify script |
| `<engagement>/EMAIL-DRAFT-<area>.md` | the outbound body, staged unsent |
| `<engagement>/COVERAGE-LEDGER.json` | per-area verdict + `hardening_only` block |

The reproduction scripts stay alongside so the vendor's engineer can re-run them; name them in
the closing paragraph rather than pasting them into the body.
