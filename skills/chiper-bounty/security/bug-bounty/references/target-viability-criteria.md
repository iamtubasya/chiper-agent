# Target Viability Criteria

Before committing time to any bug bounty target, verify ALL criteria below.

## Decision Matrix

| Criterion | Green Light | Yellow | Red Light |
|-----------|------------|--------|-----------|
| **Program Status** | Active, accepting reports | Paused (audit now, submit later) | Closed / Terminated |
| **KYC Required** | No KYC | KYC but acceptable | KYC + $5+ submission fee |
| **Submission Method** | Own email / platform | HackerOne / Bugcrowd | Requires invitation |
| **Bounty - Critical** | $5K+ | $1K-$5K | <$1K |
| **Bounty - High** | $2K+ | $500-$2K | <$500 |
| **Scope Breadth** | 10+ assets, multiple domains | 3-10 assets | 1-2 assets only |
| **Tech Stack Match** | Matches our skills (Solidity, TON, Web) | Partial match | Unknown stack |
| **Competition** | <50 hackers, <$5K paid | 50-200 hackers | 200+ hackers, low payout |
| **Past Findings** | Public CVEs / writeups exist | Audited but no public findings | No audit history |

## Quick Checks (5 minutes)

### 1. Program Status
Check the program page for status indicators. Paused programs cannot accept submissions.

### 2. Bounty Tiers
- Critical-only programs = very high bar
- Medium/Lower tiers = more realistic for quick wins
- Calculate: is the minimum bounty worth the time investment?

### 3. Competition Assessment
- Check `# hackers` and `total rewards paid` on program page
- If `total rewards < 10% of max budget` = hard targets or low triage

### 4. Tech Stack Match
- Solidity = strongest skill (Slither, Echidna, Foundry)
- FunC/Tolk = specialized (TON sandbox)
- PHP/WordPress = vdp-recon has extensive patterns
- Python/FastAPI = cloud-infra-recon patterns
- Node.js/React SPA = JS bundle analysis

## Target Selection Workflow

1. Filter list by bounty amount (>$1K minimum)
2. Check program status (must be Active)
3. Check KYC (prefer no KYC)
4. Check scope breadth (>5 assets = good)
5. Check tech stack (match to skills)
6. Check competition (<100 hackers = less competition)
7. Go/no-go decision in <5 minutes

## Pool-metadata lies — verify the POLICY PAGE before committing (2026-10-17)

The target pool's `reward` field is **unreliable in both directions**. Measured this session:
`lolipop.jp` / `shop-pro.jp` / `suzuri.jp` (pool: `monetary`) → Pepabo policy says
**"現在、報奨金制度は設けておりません"** (no bounty programme at all); `dopetech.au`
(pool: `monetary`) → *"does not currently advertise a cash reward programme"*. Conversely
`abhieo.in` and `levoit.au` (pool: `monetary`) DID have real, paying programmes — so the field
is noise, not signal. **Rule: after pool shortlist, fetch the actual policy URL and confirm a
reward table (or an explicit bounty statement) exists BEFORE starting Phase 0B.** Two minutes of
policy reading prevents a full engagement on a no-pay target.

Operator regional preference (stated 2026-10-17: *"india gkpernah bayar"*): deprioritize `.in`
targets unless the program is exceptional; the operator's requested rotation this session was
Asia → Japan/Korea → South Asia → Australia. Note JP/KR monetary self-hosted is thin in the pool
(most are platform/HackerOne-routed); AU monetary self-hosted was 2 candidates, one of which
(dopetech) had no cash — check both before committing.

## Key Lessons (August 2026)

| Target | Status | Bounty | Decision | Lesson |
|--------|--------|--------|----------|--------|
| Torch Finance | Active | $20K (Critical only) | Audited → NO FINDING | Critical-only = very high bar |
| SuperEarn | PAUSED | $30K | Skip for now | Check status first |
| Atmail | Active | $5K | Good target | Broad scope, multiple subdomains |
| Obol | Active | $100K | Auth barrier | Can't test without access |

**Critical-only bounties** require finding something truly critical. Most well-audited contracts won't have one. Factor this into time investment decisions.
