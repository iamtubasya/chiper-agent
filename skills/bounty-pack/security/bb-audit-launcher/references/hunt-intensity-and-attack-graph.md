# Hunt Intensity, Attack-Graph Expansion & Pivot Discipline

> Load at **0C** (before the first probe) and again at any stall. Three questions the phase
> framework leaves open: *how hard am I hunting right now*, *what do I look at next when the obvious
> surface is exhausted*, and *when do I kill a lane*.
> Companion: `feature-abuse-doctrine.md` (how to find), `evidence-state-ladder-and-reachability-gate.md`
> (what counts as proof).

---

## 1. Intensity modes — a decision written down, not a mood

Declare the mode in `PHASE_LOG.md` at 0C. All modes stay in scope; only the amount of surface touched
differs.

| Mode | When | Behaviour |
|---|---|---|
| **NORMAL** | estate broad, surface unknown, first hour | breadth: enumerate, rank, test the top hypotheses shallowly |
| **AGGRESSIVE** | top candidates known, time budget left | depth on several lanes in parallel; correlate source ↔ deployment; inspect sibling functions/contracts; test composability; auto-generate follow-ups |
| **HUNTER** | a component moves value or touches privilege | one component, full pass below |
| **DEEP HUNT** | engagement's purpose is max discovery (paid / Critical mandate) | HUNTER on every crown jewel, map while attacking, several paths in parallel, variant-hunt every confirmed root cause |

**HUNTER 15-point pass** (per component, not per app):

```
 1 trust boundaries           9  initialization
 2 user-controlled inputs    10  upgrades / migrations
 3 privileged operations     11  failure & recovery paths
 4 state / asset transitions 12  external dependencies
 5 security invariants       13  deployment vs source diff
 6 invariant violations      14  historical security-sensitive commits
 7 alternate execution paths 15  composability with other features
 8 unusual state combos
```

One finding does **not** end the pass — it seeds the next (§2).

---

## 2. Attack-graph expansion — every observation is a seed

Something interesting (an extra field, a slow response, a 403 leaking a path, a sequential ID) is not
a note, it is a graph node. Run and write the chain:

```
OBSERVATION → ROOT CAUSE → AFFECTED PRIMITIVE → RELATED COMPONENTS → ALTERNATE PATHS
            → CROSS-CONTRACT / CROSS-TENANT → ECONOMIC EFFECT → IMPACT
```

Ten questions that force it:

1. Where else is this primitive used?
2. Which assumption is protecting it right now?
3. Can a *legitimate* feature violate that assumption?
4. Can the primitive be reached indirectly (an endpoint that calls it for you)?
5. Does another function trust its output without re-checking?
6. Does another contract / service / tenant depend on it?
7. Does another deployment carry the same weakness?
8. Does another chain / region / environment carry the same implementation?
9. Does an upgrade or new release reintroduce the same root cause?
10. Do two individually safe operations become unsafe when composed?

Every new observation re-enters the graph. This is how a Medium becomes Critical: not a bigger bug,
but the *second consumer* of the same broken assumption.

---

## 3. Pivot discipline

```
FAILED PATH → WHY EXACTLY → NEW HYPOTHESIS → NEW ENTRY POINT → RELATED COMPONENT → RETEST
```

- Never repeat an identical failed action. Same request + same payload + same result ≠ a test.
- **Cap 5 attempts per hypothesis.** Then classify **UNKNOWN** (never DISPROVEN), record, move on.
- Depth before breadth — exhaust one lead before opening another, unless it is externally BLOCKED.
- **A confirmed root cause obligates a variant hunt** before the report: same function, sibling
  functions, inherited functions, same modifier, same state variable, same contract family, same
  implementation on other deployments/chains, upgrade implementations, historical versions.
  One root cause = one class = one report with N evidence endpoints.
- "Try a completely different function/endpoint" beats "try the 6th payload variant".

---

## 4. Resource frugality — do not burn the engagement to prove a point

| Resource | Budget | Rule |
|---|---|---|
| e-mail OTP / magic link | 1 per account | read it from the operator's own mailbox over IMAP; never ask the operator to relay |
| CAPTCHA | max 2 solves, then **STOP** | the wall itself is the finding or the blocker — not something to grind |
| residential proxy | only when geo-blocked / IP-banned | never a default; never to evade an abuse control that already engaged |
| accounts | 1 attacker + 1 victim, reused | mint them yourself (`disposable-auth-identity`) |
| brute force | never to completion | bounded probe on your own account, stop early, state the bound |
| money-path needing a real deposit | **STOP, report to operator** | never spend the operator's money to prove a bug |

A burnt account or a flagged IP costs more than the finding.

---

## 5. Time-boxes

- **5-minute rule** — 401/403/404 that will not budge after 5 minutes of bypass attempts → MOVE ON,
  record the attempts.
- **1-hour rule** — one hour with zero new information → switch component/context entirely.
- **Rabbit-hole list** — every detour gets a line with a 15-minute budget; closed or promoted. Open
  detours at session end are the next session's queue.
- **3-iteration rule** — a failed vector is not closed until it has been run **three times with a
  different payload / encoding / method** and each attempt is recorded. One 403 is an observation,
  three different 403s with the server error string is a negative. Anything less is `UNKNOWN`.
- **Stuck ≠ stop.** "Stuck" means the current hypothesis is exhausted — move to a different
  endpoint / function / contract entirely, do not end the hunt and do not ask the operator whether to
  continue.

---

## 6. STATE checkpoint

```
STATE @ <target> <HH:MM>  mode=<NORMAL|AGGRESSIVE|HUNTER|DEEP HUNT>
findings:    <proven + candidates, each with its evidence-state label>
invariants:  <what must always hold>
tested-safe: <vector -> failure label -> why>
untouched:   <surface not yet tested>
next:        <3 concrete moves>
```

This block is the resume artifact: if the session dies, the next run restarts from it instead of
re-deriving the hunt.
