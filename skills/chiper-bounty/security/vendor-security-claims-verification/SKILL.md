---
name: vendor-security-claims-verification
description: "Verify vendor security claims against live deployment."
metadata:
  hermes:
    tags: [security, bug-bounty, web3, documentation, trust-model, evm, svm, audit]
    author: qwen
    license: MIT
version: 1.0.0
---

# Vendor security claims vs deployed reality

## When to Use

Load this when the target publishes a **security property** you are about to trust, or about to test
around. Typical phrasings on a docs page, security page, or audit summary:

- "Each contract is **non-upgradable** / immutable"
- "Admin functions are protected by a **Security Council multisig**"
- "Withdrawals require **Oracle authorization**"
- "All protocol contracts are **open source**" (→ then they are not in the named repo)
- "API keys are **required** for all operator endpoints"
- "The factory is deployed **once per supported chain**"

Every one of those is a **testable claim**, and on bug-bounty programs they are frequently false in a
security-relevant direction. A divergence between what the docs promise and what the chain/API
actually enforces is a legitimate reportable class — it is the single most common payout shape on
infrastructure programs, because it is cheap to verify and impossible to argue with.

**Do not test *around* a documented control. Test the control itself.**

## Why this pays

Measured on relay.link (2026-10): twelve findings across several rounds — R1 through R12 — were
**all** of this one class. Not a single memory-corruption or auth-bypass. Each was: docs say X,
deployment does Y, here is the read-only proof.

The reason it works: vendors write docs from intent and ship from convenience. The gap is where
integrators and auditors are misled, and the program cannot dismiss it as "by design" because their
own documentation is the counter-evidence.

## Procedure

### 1. Extract the claim as a falsifiable sentence

Copy the sentence verbatim, with its URL and fetch date. Note the **scope words** — "EVM and Solana
chains" means the claim covers SVM too, which is exactly where it is easiest to break.

```
CLAIM : "Each contract is non-upgradable, meaning its logic cannot be changed after deployment."
SCOPE : "deployed on every chain Relay supports — EVM and Solana chains, and MPC on Bitcoin"
SOURCE: docs.relay.link/references/protocol/components/depository (fetched 2026-10-30)
```

If the claim cannot be turned into a yes/no check against on-chain state, it is marketing, not a
claim. Skip it.

### 2. Locate the deployed artefact

- **Program/contract IDs from source**: `grep -rn 'declare_id!' --include=*.rs` for SVM;
  `deployments/addresses.json`, `/chains` API, or a verified-explorer lookup for EVM.
- **Never trust the docs' own address table** — it is the thing under test. Cross-check against the
  repo, the API config, and the explorer.
- Keep the exact address you tested in the report. "The Solana depository" is not evidence;
  `99vQwtBwYtrqqD9YSXbdum3KBdxPAVxYTaQ3cfnJSrN2` is.

### 3. Read the property from live state, read-only

See `references/onchain-property-probes.md` for the full probe table (EVM + SVM). The core checks:

| Claim | Probe | Falsified when |
|---|---|---|
| non-upgradable (EVM) | `eth_getCode` for proxy pattern; EIP-1967 admin slot; `upgradeTo` selector | proxy admin slot non-zero, or `upgradeTo(address)` present in bytecode |
| non-upgradable (SVM) | `getAccountInfo` → **owner loader** | owner == `BPFLoaderUpgradeab1e11111111111111111111111` |
| no upgrade authority (SVM) | ProgramData account, byte 12 = `Option` tag | tag == 1 → authority exists, read next 32 bytes |
| multisig / council (EVM) | `owner()`, `getOwners()`, `getThreshold()` | `owner()` is an EOA (no code) |
| multisig / council (SVM) | `getAccountInfo` on the authority | System Program owner + 0 data = plain keypair |
| Oracle-gated | grep the deployed source for the role / `hasRole` | role selector absent from the deployed contract |
| API key required | call the route with no key | 2xx with real data |
| open source | grep the named repo for the contract name | 0 hits |

### 4. Bound the severity with the program's OWN rules

This is where over-claiming happens. Most programs state an explicit ceiling for privileged-role
issues. Read it and apply it:

> Relay: *"**Admin-only bugs are S1.** Functions behind `onlyOwner` or an equivalent role do not
> escalate above S1 regardless of the potential damage. They are only eligible for a bounty when
> there is an **external path to reach the role**."*

So a single EOA holding upgrade authority over a fund-custodying program is **S1 ($2,000)**, not
S4 ($100,000) — because there is no external path to the key. Reporting it as critical gets it
downgraded and costs credibility.

**Say this out loud in the report.** A severity bound you set yourself, quoting their rule, reads as
rigour. An inflated one reads as inexperience.

The two directions the divergence actually breaks are worth stating because they are true even at S1:
1. **Integrator trust** — someone relying on "non-upgradable" believes the logic is frozen. It is not.
2. **Blast-radius difference** — an EVM `owner` can move funds *within* existing logic; a Solana
   upgrade authority can **replace the logic itself**, which is strictly worse.

### 5. Re-filing discipline — do not resend an old finding without new information

If the same divergence was already filed, re-verifying it produces **no new reportable content**.
Resending it is noise and burns the relationship. Only send again if you add one of:

- the custody model of the privileged key (who/what holds it),
- a reachable external path to that privilege,
- evidence a fix shipped and this is a **regression**.

Otherwise: record the re-verification in the engagement ledger, and spend the round on the money
path instead.

## Pitfalls

- **The docs site may be behind a bot challenge.** `curl` returns a "Security Checkpoint" page that
  is 40 KB of HTML and greps clean — so "the claim is gone" is a false conclusion. Check the body
  for `Vercel Security Checkpoint` / `Just a moment` and fetch via a real browser session instead.
  Verify you actually got prose: a legitimate docs page for a protocol component is several KB of
  sentences, not 2 lines.
- **`llms-full.txt` is not always the corpus.** It can be intercepted by the same challenge. Confirm
  the first line is markdown/text, not `<!DOCTYPE html>`.
- **Absence of a selector is not absence of the function.** `cast call` reverting on
  `APPROVED_WITHDRAWER_ROLE()` is evidence only if you also checked the deployed bytecode for the
  selector. Prefer both.
- **A role model can exist on a *different* deployment.** The docs may accurately describe the Aurora
  contract and inaccurately describe the one the vendor runs. Name which address you tested and
  whether a sibling deployment differs — that distinction is often the whole finding.
- **Do not claim a fix is needed for something already correct.** If the docs describe the deployed
  behaviour faithfully, you have a negative. Write it down as a negative and move on.

## Reporting shape

```
CLAIM   : <verbatim sentence> — <url>, fetched <date>
TESTED  : <exact address / program id / endpoint>
RESULT  : <what live state returns, verbatim>
DIVERGE : <one sentence: docs say X, deployment is Y>
IMPACT  : <who is misled and what they would wrongly conclude>
SEVERITY: <tier>, bounded by <their own quoted rule>
FIX     : <update docs, or ship the control, or publish the address>
```

Every probe in the PoC section must be read-only (`getAccountInfo`, `getCode`, `eth_call`,
`GET`). Nothing signed, no transaction created. Say that explicitly — it is what makes a
divergence report safe to receive.

## Support files

- `references/onchain-property-probes.md` — probe table for EVM + SVM, ProgramData byte layout,
  base58 decoding, worked examples from a real engagement.
- `scripts/svm_upgradeability_check.py` — ready to run: given program IDs, prints loader, ProgramData
  account, upgrade-authority flag, and the authority address, plus whether that authority is a
  multisig or a plain keypair.
