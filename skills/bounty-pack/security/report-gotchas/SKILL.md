---
name: report-gotchas
version: 1.0.0
author: "Qwen (adapted from YesWeHack claude-kit, GPL-3.0-or-later)"
license: "GPL-3.0-or-later (adapted work; source: yeswehack/claude-kit)"
description: Per-class proof bar + AI-slop detector for reports.
metadata:
  hermes:
    tags: [bug-bounty, report-quality, triage, false-positive, overclaim]
    provenance: "adapted from yeswehack/claude-kit (GPL-3.0-or-later) — skills/gotchas + skills/triage/references/ai-slop.md, 2026-10-26"
---

# Report Gotchas — per-class proof bar + AI-slop detector

## When to Use

- **0E candidate review** — a candidate just passed discovery and you are
  about to decide whether it is a real finding. Load the claimed class from
  `references/class-gotchas.md` **before** `triage-validation`'s 7-Question
  Gate, so the gate is fed a candidate that already meets the class proof bar.
- **0F pre-submit** — the draft is assembled. Run
  `references/ai-slop-patterns.md` over the whole draft, always.
- A scanner emitted a "POC" and you need to know whether it is a finding, a
  false positive, or an overclaim.
- A draft claims a severity you are not sure the PoC supports.

Two references that sit **between finding a bug and submitting it**:

| File | Use when | Answers |
|---|---|---|
| `references/class-gotchas.md` | the report claims a specific vuln class | what is the *minimum* proof, what gets auto-closed as N/A, what impact claims need extra evidence |
| `references/ai-slop-patterns.md` | any draft, always | does this read like verified lab notes or like unverified LLM output |

**Provenance & license.** Both are adapted from YesWeHack's public
[claude-kit](https://github.com/yeswehack/claude-kit) (`skills/gotchas/SKILL.md`,
`skills/triage/references/ai-slop.md`), GPL-3.0-or-later. Structure and the
class list are theirs; the operator-specific notes, the integration with our
0A→0F pipeline, and the cross-links to `triage-validation` / `report-writing` /
`bug-bounty-disclosure` are ours. Credit retained deliberately — if a triager
asks where the checklist came from, it is a public, citable source.

## Where it plugs in (do not duplicate existing gates)

This skill is **additive** — it does not replace anything:

- `triage-validation` owns the **7-Question Gate**, the NEVER SUBMIT list, the
  CONDITIONALLY VALID chain table, and CVSS 3.1 quick reference. That is the
  *decision* layer.
- `report-writing` owns the **templates, tone, title formula, impact-first
  structure**. That is the *authoring* layer.
- `bug-bounty-disclosure` owns the **channel, contact discovery, email shape,
  one-finding-one-draft rule**. That is the *delivery* layer.
- **This skill owns the per-class proof bar and the slop detector** — the layer
  that was missing. Run it at **0E (candidate review)** and again at **0F
  (pre-submit)**, feeding `triage-validation`'s gate rather than replacing it.

## How to run it

### At 0E — per candidate, before the 7-Question Gate

1. Name the class the candidate claims (XSS, IDOR, SSRF, race, …).
2. Open `references/class-gotchas.md` at that class only. Read all three blocks.
3. Check the PoC against **minimum proof**. If it does not meet it → the
   candidate is not a finding yet; write what would prove it, do not submit.
4. Check the draft's impact wording against **overclaim traps**. Every
   escalation in the Impact section must be demonstrated in the PoC, not
   inferred from it.
5. Check whether the shape matches a **common N/A**. If it does, disprove it
   explicitly (see `bb-methodology` Marker Discipline / Body-Diff Rule /
   Statistical-Sample Rule) or kill the candidate.

### At 0F — on the assembled draft, always

Run `references/ai-slop-patterns.md` in full over the draft. Output the
`[CRITICAL|STRONG|MINOR] - <category>: <quote> → Fix: <instruction>` lines.
Any CRITICAL → **DO NOT SUBMIT**. This is the same discipline
`triage-validation` enforces mechanically via `triage_gate.py`; this file is
the human-readable checklist behind it.

## The rules that carry the most weight

1. **Prove the primitive, describe the impact, don't exercise it.** A confirmed
   injection, an OOB callback, a single cross-account read — that is the proof.
   Dumping the DB, pivoting, mass-exfiltrating, or scaling a race burst past
   the invariant break is *past proof and into damage*, and breaches most
   program rules. (class-gotchas: SQLi, RCE, XXE, LFI, Race.)
2. **Score `AC:H` when the identifier is not discoverable.** A random UUIDv4
   you happened to know is not an enumerable ID. If the attacker needs the ID
   to leak from somewhere else, say where — and don't claim mass exploitation
   off one self-owned resource. (class-gotchas: IDOR.)
3. **Environmental/Temporal CVSS metrics are the program's to weigh, not
   yours.** Base metrics only, each justified by what was actually verified.
   The `AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H` = 9.8 default is the single most
   recognisable LLM tell. (ai-slop-patterns §6.)

4. **No concrete attacker win → it is not a finding. Write the "attacker-win
   test" before drafting.** Ask "as an attacker, what can we actually DO with
   this?" A pure observation with no in-scope downstream effect — email / user
   enumeration whose only use is phishing (OOS social engineering), version
   disclosure, a missing header, a weak info leak with no chain — is something
   to *note*, not a report to *write*. If the answer is a chain into account
   access, data read, or privilege, write it. If the answer is "targeted
   "phishing (out of scope)" or "nothing", drop it. The operator explicitly
      rejects vague chainless findings ("hindari bug yg gkjela — sebagai attacker
      kita bisa apa?"); catch it at 0E so it never reaches a draft.

   5. **Leaked-credential findings need a liveness delta, and live keys hijack the
      evidence file.** A "hardcoded API key in the bundle" is informational noise
      unless you prove the key is LIVE — send the exact full key + an invalid-key
      control to the vendor API and report the response-code delta (`400`
      business-error vs `401 invalid_api_key` = live; never use a truncated copy,
      it falsely reads as "valid"). Most bundle keys (WalletConnect projectId,
      thirdweb clientId, Sentry DSN, free-tier RPC keys) are public-by-design →
      note, don't inflate. Also: writing a live `Bearer <key>` into a report file
      on this host makes the secret-tripwire rewrite the FILE (not just the
      display) — compose the key via string concatenation, then grep the file to
      confirm. Full recipe in `references/leaked-credential-proof.md`.»

## Known gaps in this skill

- Class list covers **23 classes** — 15 web2 (XSS, SQLi, SSRF, IDOR/BOLA, CSRF, RCE,
  SSTI, XXE, open redirect, auth bypass, info disclosure, race, CORS, path traversal/LFI,
  OTP/magic-link brute-force)
  and **8 web3/on-chain** (reentrancy, on-chain access control, price oracle, signature
  replay, vault share accounting, AMM/swap accounting, restaking/slashing, intent
  settlement). Anything else → apply general PoC + impact rigour and state the class +
  impact model in the report's first paragraph, because the triager has no
  class-specific mental model to fall back on.
- The YesWeHack-specific section names in the source (`write` skill) are NOT
  reproduced here — `report-writing` already owns our section structure, and
  YesWeHack's form-field layout does not transfer to H1/Bugcrowd/Intigriti.
- No platform-specific reward caps. `triage-validation` GATE 4 owns
  program-policy compliance.

## Support files
- `references/class-gotchas.md` — **23 classes** × (minimum proof / common N/A /
  overclaim traps): 15 web2 + 8 web3/on-chain, plus `[ours]` operator notes per
  class where this estate has a measured lesson. The web3 classes carry the
  Foundry-on-fork proof bar (`forge test --fork-url … -vvvv`) and the economic
  gates (attacker P&L after gas, cost-of-manipulation vs extractable value).
- `references/ai-slop-patterns.md` — the red-flag taxonomy (Critical / Strong
  / Minor) with the `[CRITICAL|STRONG|MINOR] - <category>: <quote> → Fix:`
  output format, plus estate-specific additions (attachment defects, POC-count
  slop, scope drift, first-contact tone).
- `references/leaked-credential-proof.md` — proof bar for "exposed API key /
  hardcoded secret" (liveness 400-vs-401 delta, public-by-design key list), the
  secret-tripwire file-mangling workaround, and the Gmail draft-with-attachment
  recipe `body={"message":{"raw":…}}`.
