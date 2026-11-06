# Immunefi Vulnerability Severity Classification System v2.2

> **SUPERSEDED (kept for history).** The operative system is **v2.3** — see
> `skills/security/bug-bounty/references/immunefi-vss-v2.3.md` for the full 4-level x 3-domain tables, out-of-scope list and prohibited activities.
> v2.3 change to note when arguing severity: **governance manipulation = Critical**, NFT-specific Criticals
> (unauthorized mint / manipulable RNG / NFT metadata XSS), and the DLT numeric thresholds.

**CRITICAL:** Immunefi uses its OWN severity system — NOT NIST CVSS.

## Critical

### Direct Fund Loss
- Assets directly stolen/lost
- Principal loss: Assets stolen, locked, or inaccessible
- Attacker can mint/borrow uncollateralized
- Permanent loss of all user funds

### Protocol Compromise
- Loss of governance control of protocol
- Protocol insolvency
- Voting rights stolen

### Infrastructure
- DoS of critical functionality (>1 hour)
- Temporary or permanent shutdown of bridge
- Pricing oracle compromised

### Access Control
- Bypass of KYC (non-incidental)

## High

### Fund Impact
- Temporary freezing of funds
- Theft of non-principal assets
- Temporary freezing of unclaimed yield

### Infrastructure
- DoS of critical functionality (>10 min)
- Temporary or permanent shutdown of non-critical oracle

### Governance
- Governance manipulation

### Access Control
- Bypass of KYC (incidental)

### Other
- DoS of non-critical functionality (>14 days)
- Financial loss without exploit on-chain

## Low

- Griefing
- DoS of non-critical functionality (>10 min)
- Required authentication doesn't prevent impersonation
- Other impacts without exploit on-chain

## Severity Mapping Guide

| Finding Type | Typical Severity |
|-------------|-----------------|
| Reentrancy (fund theft) | Critical |
| Flashloan price manipulation | Critical |
| Uninitialized proxy | Critical |
| Oracle manipulation | Critical |
| Bridge message spoofing | Critical |
| Access control bypass (critical func) | Critical |
| Temporary fund freeze | High |
| DoS critical >10 min | High |
| Governance manipulation | High |
| Griefing | Low |
| DoS non-critical >10 min | Low |

## ⚠️ Key Rules
- Use Immunefi classification, NOT CVSS calculator
- If in doubt between Critical/High → argue with concrete impact scenario
- Project's scope defines which impacts are in-scope
- Impact MUST come from project's official impact list
- Asset MUST come from project's official asset list
