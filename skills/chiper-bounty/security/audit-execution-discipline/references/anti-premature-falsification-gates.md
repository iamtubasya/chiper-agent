# Gate per-tahap + anti-premature-falsification (operator docs, 2026-10-12)

Source: operator-supplied `gate-pipeline-end-to-end.md` + `gate-rule-validasi-hipotesis.md`
(delivered via the MyGroupBot workspace). These are **complementary** to RULE 18, not
duplicates:

- **RULE 18** governs the *positive* side — don't call something `informational`/`low`
  before exhausting vectors.
- **These gates** govern the *negative* side — don't declare `FALSIFIED` / "safe" /
  "not vulnerable" without winning that verdict with evidence.

Both exist because the two failure modes are different, and the second one is how a real
bug gets closed as "no finding".

---

## Part 1 — Per-stage gates (Recon → Threat Modeling → Hipotesis → Validasi)

Principle: **every stage has an explicit gate; you may not advance with the gate unmet** —
unless you record it as an explicit gap carried forward as a risk note, never silently.

Why: a generic hypothesis almost always descends from generic recon/threat-modeling. A
gate only at validation filters at the end; gates at every stage filter at the root.

### Stage 1 — Recon
Gate checklist before advancing:
1. Entry-point enumeration — every way in (API endpoint, contract function/event, admin
   panel, webhook, third-party integration), not just the obvious ones.
2. Trust-boundary mapping — where data/control crosses from untrusted → trusted
   (user input → backend, off-chain → on-chain, contract A → B, frontend → contract).
3. Dependency/version inventory — libs, frameworks, contract/protocol versions.
4. Data-flow sketch — who trusts whom, on what basis.

Fail → may not advance. If forced (rate limit, limited access, poor docs), mark:
```
RECON GAP: <what is uncovered, and why>
```
and **carry it forward** as an explicit risk note.

### Stage 2 — Threat Modeling
Each threat needs **4 concrete elements**, all filled:
1. Attacker capability — exactly what can the attacker control?
2. Trust boundary violated — must reference a *specific* boundary from Stage 1.
3. Assumption being broken — what does the developer assume, and under what conditions
   does this threat disprove it?
4. Expected observable effect — if it succeeds, what changes/leaks/moves?

Fail → threat **rejected**, cannot become a hypothesis candidate. Copying a generic vuln
class name with no tie to recon is a rejection.

### Stage 3 — Hipotesis
Required format:
```
Jika [actor] melakukan [aksi konkret]
pada [target spesifik — fungsi/endpoint/kontrak tertentu, bukan "sistem"],
maka [expected effect terukur] akan terjadi,
yang melanggar [asumsi/invariant dari tahap threat modeling].
```
Three gates: **specificity** (testable by concrete steps; "need to check further" = still a
threat, send back) · **linkage** (explicitly ties to attacker-capability + trust-boundary +
assumption; pattern-matching a vuln name = regenerate) · **testability** (≥1 concrete first
execution step before it may enter the validation queue).

### Stage 4 — Validasi
See Part 2. A `RECON GAP` from Stage 1 that bears directly on a hypothesis is a valid
reason for `INCONCLUSIVE` (not `FALSIFIED`).

| Stage | Validated before advancing | Consequence of gate failure |
|---|---|---|
| Recon | coverage of entry points, trust boundaries, deps | mark `RECON GAP`, carry as risk |
| Threat Modeling | 4 concrete elements per threat | threat rejected, not promoted |
| Hipotesis | specificity, linkage, testability | hypothesis returned / regenerated |
| Validasi | 7 anti-premature-falsification gates | verdict becomes `INCONCLUSIVE`, not `FALSIFIED` |

---

## Part 2 — Anti-premature-falsification gates

Base principles:
1. **Equal burden of proof on both sides.** Concluding `FALSIFIED` is as heavy a claim as
   `CONFIRMED` — both need evidence, neither is a default.
2. **Default when unsure = `INCONCLUSIVE`**, not `FALSIFIED`. An agent must not force a
   binary when evidence is insufficient.
3. **`FALSIFIED` must be *won* with executed evidence** — it may not appear merely because
   reproduction failed or resources/tooling were limited.

Allowed statuses: `CONFIRMED` / `FALSIFIED` / `INCONCLUSIVE` — only these three.

### The 7 gates — all must pass before writing `FALSIFIED`

1. **Ladder complete** — all validation stages walked. A skipped stage marked
   `SKIPPED: <reason>` automatically fails this gate.
2. **Multi-variation** — at least 3 different condition/input variations attempted, not a
   single attempt.
3. **Steelman mandatory** — before writing the reject reason, first write the *strongest*
   possible attack scenario (assume the smartest attacker), then explain why it fails. If a
   concrete steelman cannot be articulated, the agent does not understand the case →
   verdict **must** be `INCONCLUSIVE`.
4. **Concrete mitigation evidence** — if the reject reason is "protection X exists"
   (rate limit, auth check, validation), evidence of the protection actually blocking must
   come from **real execution**, not from reading code. Plus ≥1 bypass attempt against it.
5. **Explicit evidence tier** — `Observed` (executed, concrete result) vs `Prepared`
   (read code / simulated / assumed). A final `FALSIFIED` may only come from `Observed`;
   `Prepared` → `INCONCLUSIVE`.
6. **Classify the root cause of a failed reproduction**:
   - (a) failed because the vulnerability genuinely does not exist → may proceed to FALSIFIED
   - (b) failed due to tooling/resource/access limits (network block, RAM/fork limit, rate
     limit on the test env) → **must** be `INCONCLUSIVE`
   - (c) failed because the test environment differs from the real target (fork vs mainnet,
     testnet vs production) → **must** be `INCONCLUSIVE`
7. **Independent re-check (cross-framing)** — re-run the reasoning under the opposite
   framing: once instructed "try to find a way to break this", once "assume it IS
   vulnerable, prove why that is wrong". If the two framings disagree → `INCONCLUSIVE`,
   flag for manual review.

### Explicit prohibitions
- ❌ Concluding `FALSIFIED` from 1 observation / 1 attempt.
- ❌ Equating "could not reproduce" with "proven not vulnerable" without root-cause
  classification (gate 6).
- ❌ Stopping early on the validation ladder without a recorded explicit reason.
- ❌ Hedging language as a final verdict ("probably safe", "seems mitigated") — a verdict
  must be backed by executed evidence, not qualitative estimation.

### Required output format per verdict
```
Verdict: CONFIRMED / FALSIFIED / INCONCLUSIVE
Evidence tier: Observed / Prepared
Steelman scenario: <2-3 sentences, the strongest attack considered>
Counter-evidence: <concrete evidence defeating that scenario, if rejecting>
Gate checklist: [pass/fail per point 1-7, with a short reason each]
Root-cause (if reproduction failed): (a)/(b)/(c) — see gate 6
Next step (if INCONCLUSIVE): <concrete recommendation>
```

### Extra rules (validation runs autonomously)
- On `INCONCLUSIVE`, include a **plain-language summary**: what was tried, why it could not
  be concluded, and what concrete manual step the operator can take (specific command,
  endpoint) — not "needs further investigation".
- On `CONFIRMED`, **show the full evidence checklist to the operator before generating the
  report** — one explicit pause for a manual sanity-check before submitting.
