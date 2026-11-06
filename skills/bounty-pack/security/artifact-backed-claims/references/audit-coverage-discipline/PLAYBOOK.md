---
name: audit-coverage-discipline
description: Use before declaring a target clean or a finding ready.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [security, audit, coverage, negative, scope, submission, discipline]
    related_skills: [bb-methodology, triage-validation, report-gotchas, exploit-depth, chain-to-impact]
---

# Audit Coverage Discipline

Two moments decide whether an engagement was real work or theatre:

1. **The negative** — "this target has nothing payable."
2. **The positive** — "this finding is ready to submit."

Both get declared too early. This skill is the gate in front of each.

## When to Use

- You are about to write "no findings", "nothing payable", "verified negative", or "N/A" for a
  class, host, or the whole engagement.
- You have a technically proven finding and are about to draft or stage a report.
- The operator says anything like *"cepat menyerah"*, *"kok segitu aja"*, *"cari lagi"*, *"masa
  cuma itu"*.
- You are auditing a Rust/Substrate runtime and want the highest-yield pallet bug class first:
  `references/substrate-weight-gap-audit.md` (constant declared weight vs O(N) iteration, with the
  full hunt, the severity-bounding questions, and four pallet-PoC harness traps).

---

# PART 1 — The negative claim

## The failure being corrected

Operator, 2026-10-28, verbatim: *"kamu, dgn berbagai update, sebanyak itu skill n tools, cepat sekali
menyerah nya."*

It landed after I wrote "nothing reportable" while leaving **13 of 18 discovered paths unprobed**,
**392 service×method combinations untried**, and a surface I had **named myself one message
earlier** (`/documents/`) never touched.

The failure is never the conclusion itself. It is **asserting a conclusion the coverage cannot
support.** Tools and skills do not make that failure less likely; they make it more embarrassing,
because the capability to finish was demonstrably present.

## The three-column ledger (mandatory before any negative)

Produce this and make it add up:

| Column | Rule |
|---|---|
| **TESTED** | every claim backed by a tool artefact on disk |
| **NOT TESTED — blocked** | name the exact blocker (no account, KYC gate, out of scope, WAF, rate limit) |
| **NOT TESTED — my own shortcut** | ← must be **EMPTY** before you conclude |

If column three has anything in it, you are not done. Run it, then conclude.

Ship the ledger in the write-up. A negative with a named blocker reads as discipline; a bare
"nothing found" reads as laziness.

## Two completeness checks that catch most instances

**The fraction test.** You extracted N routes from a bundle, a JS file, an OpenAPI doc, or a
wordlist hit. Did you probe **all N**, or the five that looked interesting?

- Write the fraction: "18/18 unsecured paths probed", never "the main ones".
- The honest forms are "N/N" and "M/N with the rest blocked because X". There is no third form.

**The oracle test.** You used a differential to *discover* surface — `403 vs 404`, a NotNull
validation message, error-text grep. Did you then sweep the full candidate set, or stop at the
first hit?

- An oracle that returns zero hits after a **full** sweep is a real result and worth reporting.
- An oracle abandoned after 19 of 400 candidates is not a result; it is a sample.
- **Calibrate the oracle before trusting its silence.** Confirm it answers differently for a
  known-present and a known-absent item. A false-negative oracle reads exactly like a clean target.

Worked example of all three failures and the corrected pass:
`references/negative-claim-ledger.md`.

## A gate that held is a finding-shaped result

Not a dead lead. Write it as a verified negative **with the control that killed it**:

> `/api/debug/*` — 8 bypass shapes (`?secret=undefined/null/true/empty`, `X-Debug-Secret`,
> `X-Node-Env`, `X-Forwarded-For`) → all 403. Gate held.

That sentence is worth more than a paragraph of "the endpoint looked protected". It proves you
tested, it counts toward coverage, and it is what makes an eventual positive credible to a triager.

## Anti-patterns to kill on sight

| Anti-pattern | Why it is theatre |
|---|---|
| "I ran nuclei across 184 hosts" | if the run was killed at 1%, that is a sentence, not coverage. State the honest cap. |
| "The endpoint requires auth" | did you try the 8 shapes in `exploit-depth`, or one? |
| "No vulnerabilities were found" | which classes, on which hosts, with what evidence? |
| Narrating effort instead of finishing | the artifact is the coverage, not the description of it |

---

# PART 2 — The submission gate

A technically real finding can still be unsendable. Run these **before** drafting.

## Gate 1 — Is it in scope, and is it payable?

Policy text outranks your severity score. Read the exclusions **verbatim** and quote them.

The near-miss this section exists to prevent: two subdomains were proven to serve third-party
content (one presenting a TLS cert for an unrelated domain from a Hetzner IP, one resolving to a
commerce-platform edge). Both were scored **High** by the technical tool and announced as "ready to
report". The program's own policy said, verbatim:

> "Subdomains operated by third parties (e.g: info.runonflux.com)."

Excluded outright. **Technical severity and programme eligibility are different axes.** A tool that
scores severity knows nothing about what a programme pays for.

Hard rules:

- **Check ownership before naming a host.** `nslookup -type=CNAME`, the TLS subject, and the rDNS
  are the three cheap tells. A host that resolves to someone else's infrastructure is a DNS
  delegation observation, not a bug in the target's software.
- **Read the "we do not pay for" list first, then map your finding onto it.** If it lands on an
  exclusion, drop it — do not soften the language and send anyway.
- **Do not report a third-party alias at all.** Do not even name it in report body unless you are
  filing a one-line good-faith note.
- **A finding the vendor already rejected is closed.** Re-testing a closed finding and re-reporting
  it with better prose burns the channel. Check the sent-mail history before drafting.

## Gate 2 — Does the artifact match the LIVE version?

Only matters where deployed ≠ published, which is most web3 and many self-hosted products.

Worked case: the audited repo was a January commit; the report was about to be drafted against it.
Before writing a word, the live chain was queried and returned `specVersion: 76` — an exact match
to the audited runtime constant. That single check is what made the report safe to send.

If live ≠ audited: **re-audit the deployed version first.** Reporting a bug that was patched two
spec-versions ago is worse than not reporting.

Recipe (Substrate): `references/live-version-verification.md`.

## Gate 3 — Does the deliverable match what the operator asked for?

Format is part of the deliverable, not a detail.

- **Operator preference (2026-10-28): `.docx`, not PDF, for Deeper Network.** Stated as
  *"pakai doc dan tata bahasa yg teratur y, jgn pakai pdf kl utk deeper"*.
- **Grammar preference, same instruction:** well-formed sentences, no chat shorthand, no
  dot-point fragments standing in for prose. Technical identifiers stay in their original form
  (`extrinsic`, `storage map`, `weight`) — do not translate them, but embed them in complete
  sentences.
- Default-to-ask only when the program's submission channel forces a format (e.g. a portal field
  that rejects attachments). Otherwise honour the operator's stated format.

## Gate 4 — Have you stated what you are NOT claiming?

Every report should contain one short section naming the limits. This is not modesty; it is what
stops a triager downgrading you.

Example, from a real Medium:

> This report requests Medium rather than High or Critical. Three properties bound the impact:
> the call requires a device signature; a level gate caps a single account at eight triggers;
> era rotation already walks the same set once per era. An unauthenticated remote halt of the
> chain is not claimed.

A report that maps its own ceiling is trusted. One that reaches for Critical and misses gets
downgraded *and* remembered.

---

## Pipeline position

```
0C   surface discovered   -> coverage ledger opens (TESTED / blocked / shortcut)
0D   verification         -> third column must be empty before 0E
0E   candidate review     -> Gate 1 (scope) + Gate 4 (limits) before drafting
0F   report               -> Gate 2 (live version) + Gate 3 (format) before sending
```

## Related

- `bb-methodology` — Pushback Protocol; load it when the operator says "find more".
- `triage-validation` — the 7-Question Gate and programme-policy compliance.
- `report-gotchas` — per-class minimum proof and the AI-slop detector.
- `exploit-depth` — the escalation ladders that turn a one-shape attempt into eight.
- `chain-to-impact` — scoring a lead by its provable ceiling rather than its current state.
