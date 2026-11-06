---
name: lead-to-critical
description: Use to drive a lead candidate to Critical/High.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, severity, escalation, lead, critical, high, triage]
    related_skills: [exploit-depth, chain-to-impact, exploit-chain-graph, triage-validation, report-gotchas, attack-surface-index]
---

# Lead → Critical/High

## When to Use

- You have a **lead candidate** (any positive signal: 200 with data, 403, weird error,
  reflection, timing delta, cross-account read) and need it to become **Critical or High**
  instead of dying as Info/Low.
- A previous engagement closed with "no findings" while every lead was dismissed in isolation.
- You are about to spend hours on a lead and need to know whether its ceiling is reachable
  *before* the hours go in.
- The operator asks *"lead-nya jadi bug gede nggak?"* / *"kejar sampai Critical"*.

## The one distinction this skill enforces

`exploit-chain-graph` answers **"which class do I pivot to next?"**
`exploit-depth` answers **"how deep am I (L0–L5)?"**

Neither answers: **"what exact artifact moves this from Medium to High to Critical, and is
that artifact reachable at all?"** That is severity *arithmetic*, and it is the thing that
decides whether a lead is worth the next two hours.

**A lead is not scored by what it currently is. It is scored by its provable ceiling.**

## Step 1 — Score the ceiling before spending time

```bash
# skor + tulis artefak untuk 0E
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/severity_ceiling.py <target_dir>
# skor + BLOK staging kalau ada lead CAPPED (exit 2)
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/severity_ceiling.py <target_dir> --gate
```

Reads `findings.json` (list of leads; `title`/`vuln_type`/`reason`/`signal`/`evidence`).
Emits per lead: evidence strength (STRONG/MIXED/WEAK/UNCLEAR), severity floor → ceiling,
a verdict, and **the crossing artifact** — the single piece of evidence that unlocks the
next tier. Writes `severity-ceiling.json` next to the input for 0E to consume.

**What the scorer reads as evidence, and what it refuses to read:**
- Strong = crossed a boundary: foreign/cross-tenant object, second account, `uid=`/exec,
  live credential *used*, money delta, mass count (≥10 records/tenants/orders).
- Weak = surface only: reflected, DNS-callback-only, bare introspection, timing, banner.
- Negation-aware: `"no secret"`, `"tanpa token"` do **not** count as a hit.
- **Plan text is never evidence.** Fields like `technique`/`primitive`/`escalations`
  in `lead-escalation.json` are *plans*; counting them would score every lead STRONG.
- Exposure ≠ use: for `info-disclosure`/`data-exposure`, a leaked credential caps at
  **High** unless you show it *authenticating*.
- **On-chain derivability (web3):** if the exposed data is derivable from a public
  ledger (address, collateral, tx, payout bookkeeping), confidentiality drops one tier.
  Vendor-validated on Flux/Titan 2026-10-27 — data rated High by the tool, Low by the
  program, and the program was right. Off-chain secrets (email, KYC, credential,
  session token, identity linkage) are what actually hold High/Critical.
- **Credential exposed ≠ credential used as a tool.** "GET invoice with user A token"
  is the *researcher's* token — High at most. Only "response **contains** the victim's
  token" reaches Critical, and only after replaying it.

Verdicts and what each one obliges you to do:

| Verdict | Meaning | Your next action |
|---|---|---|
| `PURSUE` | evidence already crosses a boundary (foreign object, exec, live credential, money delta) | go straight for the crossing artifact in the row; target Critical |
| `NEED-ONE-MORE` | real signal, no boundary crossed yet | get exactly one artifact, re-score |
| `NEED-CHAIN` | class has **no** standalone High (open redirect, bare introspection) | find the consumer (OAuth `redirect_uri`, resolver-level authz) or DROP |
| `CAPPED-DROP` | structurally cannot reach High, regardless of effort | stop now, write the cap reason, move on |

**Rule: never invest in a lead whose row says CAPPED-DROP.** Those are the hours that
produce Informative submissions and burn validity ratio.

## Step 2 — Climb with the per-class play

The climbing technique per class — how to *get* the crossing artifact — is in
`references/severity-climb-plays.md`. Read only the class you are on.

The three moves that appear in almost every climb:

1. **Cross a boundary.** Own account → second own account. Own object → foreign object.
   Public data → private data. Same tenant → other tenant. A bug that never crosses a
   boundary is Info no matter how clean the PoC is.
2. **Escalate read → write.** A read proves access; a write proves *impact*. Try
   `PUT`/`PATCH`/`DELETE` on the same object, then re-read to confirm the state actually
   changed (re-read is mandatory — a 200 is not a state change).
3. **Find the consumer.** A token/key/URL that mints is worthless until a host *accepts*
   it. Grep the bundle for the service map, then locate the real backend. If the consumer
   is unreachable, the lead is `UNPROVEN` — not a finding, and not a verified negative.

## Step 3 — Prove it (the gate between High and Critical)

Critical needs **impact demonstrated, not inferred**. Before writing `Critical`:

- All preconditions executed by you, in a clean session, twice.
- No remaining gate you have not bypassed (signature, audience, inheritance, step-up auth).
- Cross-account work done with **two accounts you created** — never a real third party.
- The money/data movement shown as a number, not a claim (`balance 0 → 240000`,
  `12 orders from 1 cart`, `14 foreign invoices`).

If any of those is missing, the honest label is High. `triage-validation`'s
Pre-Severity Gate is the enforcement; this skill is how you get past it.

## Step 4 — Anti-inflation (what keeps your validity ratio alive)

| Trap | Reality |
|---|---|
| "Could potentially lead to RCE" | not a severity — it is a TODO. Either execute or downgrade. |
| One foreign record read | High at best. Mass (≥10) or write is what pushes further. |
| Live-but-idle credential leaked | prove it authenticates. An unused key is Info. |
| Self-XSS / header-missing / banner | CAPPED. The script flags these; believe it. |
| Prompt-injection that only changes its own output | not a finding; needs to read another user's data. |
| "Admin can do X" | centralization, not a bug. |

A lead you correctly **drop** with a named structural cap is worth more than a
submission that comes back Informative — it protects the ratio you need for the next
engagement.

## Pipeline position

```
0C   signal found            -> severity_ceiling.py (score all leads, drop capped)
0C-C7 per LEAD               -> step 2 climb (references/severity-climb-plays.md)
                              -> exploit-depth for depth (L0->L5)
                              -> exploit-chain-graph for the pivot class
0E   candidate review        -> report-gotchas per-class proof bar
0F   report                  -> triage-validation 7Q + Pre-Severity Gate
```

## Related

- `exploit-depth` — L0→L5 depth ladder + per-class 403/500/200 escalation ladders.
- `exploit-chain-graph` — which class to pivot to (its own
  `references/graph.md`, 57 classes). Load that skill to read the table; it is not
  duplicated here.
- `chain-to-impact` — the chain question per primitive, and the honest-negative discipline.
- `report-gotchas` — per-class minimum proof (run before the 7Q gate).
- `triage-validation` — the gate that kills inflated severity.
- `attack-surface-index` — what to probe for a feature you just found.
