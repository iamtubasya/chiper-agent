# Counter-Downgrade Playbook — answering the four standard rejections with evidence

> Load at **0E/0F** when writing the impact section, and again when a triager replies with a
> downgrade. The goal is not to argue harder; it is to make the *correct* severity unavoidable by
> putting the missing fact in front of the triager.
> Companion: `triage-validation-7qgate.md` (kill gate before writing), `severity-rules.md`.

---

## 0. Rule zero

Severity is argued with the **program's own scale** (tiers, Immunefi impact matrix, VRT), not with
your preferred CVSS number. CVSS is supporting material when the program asks for it. If the
program's rubric says "no fund-loss path = not Critical", then no amount of chaining changes that —
the rubric is the ceiling. State the rubric clause you are matching, then match it.

---

## 1. "This requires authentication"

**What they mean:** lower privileges-required, lower score.
**What you show:** the exact cost of the account, and the fact that the account is free and
self-service.

Write it as:

```
Privileges Required: Low — a self-service account with no approval, no invite, no payment.
Account created in <N> minutes via <endpoint>. No role, no tenant admin, no staff involvement.
Affected principals: <every account in the product / every tenant>.
```

If the account *does* need a paid plan or an invite, say so honestly — the honest version still
scores, and an inflated version gets closed as Informational.

## 2. "Impact is limited"

**What they mean:** your impact paragraph is abstract ("could expose sensitive data").
**What you show:** count, type, and one concrete instance you actually read (redacted).

```
Measured: <N> objects reachable from a single low-privilege account, across <M> tenants.
Data classes observed: <email, address, IBAN, invoice PDF, API key prefix, …>
One example (redacted): <field>=<redacted> belonging to tenant <X>.
Reproduction: <endpoint> with <attacker account> returns the object of <victim account>.
```

`N` must come from a bounded, polite sample (10–20 IDs), extrapolated with the method stated. Do not
mass-dump; do not claim a total you did not measure.

## 3. "This is known / duplicate"

**What you show:** the search you already did, with the specific gap.

```
Searched: program disclosed reports (<n>), changelog (<n> entries), repository issues/PRs,
vendor advisories, audits. No report covers <root cause>.
Closest match: <report id / advisory> — different root cause (<why>), different endpoint, and it was
fixed in <version>; the current deployment still returns <evidence>.
```

If you cannot say that, the finding was not dedup-checked — go do the four lanes
(`evidence-state-ladder-and-reachability-gate.md` §4) before replying.

## 4. "This is by design"

**What you show:** the design claim, quoted, and the invariant it breaks.

```
Documentation states: "<quoted sentence>" (<link/version>).
The documented behaviour covers <X>. It does not cover <Y>: <the response/state that contradicts it>.
Consequence: an actor who is not supposed to hold <capability> obtains it via <path>.
```

If the documentation genuinely covers the behaviour, **accept the downgrade and drop it.** A
by-design finding costs reputation and pollutes the ratio.

---

## 5. When the downgrade is a chained-impact denial

Triagers score components in isolation; you score the chain. Do the work for them:

```
Component severities (standalone, as a triager would score them):
  A: <class> — Low (info disclosure of <x>)
  B: <class> — Low (missing check on <y>)
  C: <class> — Medium (write to own tenant)
Combined: A→B→C reaches <terminal impact> across <N tenants> — one PoC walks step 1→3.
Each hop's precondition is produced by the previous hop's output; no seeded state.
```

Requirements before you write that paragraph (from `chain-to-impact` → Multi-Low composition):
every hop has an artifact, the end-to-end PoC runs in one continuous path from a clean session, and
no intermediate state is fixture-seeded. A chain that seeds state is FIXTURE-VERIFIED and capped at
Medium — say so instead of arguing.

---

## 6. What never to write

- "possibly", "could potentially", "an attacker might" — replace with what you ran and what came back.
- Severity adjectives without a measured number or a rubric clause.
- Threats, deadlines, "I will disclose publicly", bounty-size complaints.
- A CVSS vector that contradicts your own impact paragraph (AV:L on a remote bug, PR:H on a
  free-account bug — triagers read the vector first).
- Claims about affected user counts you did not sample. "All 40M users" from one ID is a fabrication.

---

## 7. Accept-and-move rule

If the triager's technical objection is correct, say so in one line, correct the record, and pivot
to the next candidate. Fighting a correct downgrade costs more time than the next hunt, and a clean
"you're right, this is Medium" buys credibility for the next submission.

## 8. Severity calibration by example — why a pattern stops at a tier

The tier comes from **demonstrated impact**, never from the shape of the bug. Each row names the
sentence that holds it there; if you cannot break that sentence with evidence, the tier stands.

### Stops at LOW
| Pattern | The sentence that holds it there |
|---|---|
| Self-XSS with no way to force a victim session | no cross-user consequence |
| UI shows a wrong balance/price, nothing signed is affected | cosmetic, no exploitable path |
| Function reverts on odd input, retryable, no loss | UX issue |
| Missing event on a state change | observability gap only |
| Dust-level rounding, no profitable size | theoretical only |
| Rounding that favours the protocol | no attacker profit path |

### Stops at MEDIUM
| Pattern | The sentence that holds it there |
|---|---|
| IDOR read of another user's private object, read-only | private data leak, no write |
| UI says "approve 10", calldata requests unlimited | future risk, drain not demonstrated |
| Missing `onlyOwner` on a fee-recipient setter | redirects future revenue, cannot touch principal |
| Withdrawal without a rate limit, signature check sound | amplifies another bug, enables nothing alone |
| Sandwich on a thin pool, no on-chain min-out | per-trade loss, not systemic drain |
| Reward drift, not triggerable on demand | fairness issue, no deterministic profit |

### Reaches HIGH / CRITICAL
| Pattern | What pushes it up |
|---|---|
| Stored XSS in other users' authenticated pages | executes in the victim's origin → High |
| SSRF returning metadata/internal content | credential theft / pivot → High; infra control → Critical |
| SQLi that actually extracts records | mass breach → Critical |
| Logic flaw that logs in as ANY user | full ATO at scale → Critical |
| Reentrancy/ordering drain shown by fork PoC | principal loss → Critical |
| Oracle manipulation with extraction | principal loss → Critical |

**The argument test:** name the victim, name the gain, name the unit (records / accounts / currency).
Missing any of the three = you are describing a pattern, not a finding.

## 9. The 60-second pre-submit sweep

Read the draft once, fast. Any "no" = do not submit yet.

```
[ ] title follows "[Class] in [endpoint] allows [actor] to [impact]"
[ ] first sentence states the impact, not the background
[ ] repro request is copy-pasteable and complete (method, path, headers, body, token)
[ ] evidence shows the GAIN (victim data / changed state), not just a 200
[ ] two accounts used, and the report says which is which
[ ] CVSS vector agrees with the impact paragraph
[ ] one-line remediation names the missing control
[ ] every path and parameter spelled exactly as captured (no drift, no typo)
[ ] under 600 words, no hedging ("possibly", "might", "could", "should")
[ ] severity equals the reached impact, not the class's usual score
```
