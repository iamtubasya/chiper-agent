# odin.ai (Mozilla 0DIN) — GenAI Bug Bounty Target Intel

> Self-hosted program, portal `0din.ai`, contact `0din@mozilla.com`. Policy last updated 2026-10-02.
> Discovered via `lissy93/bug-bounties` `independent-programs.yml` (added Oct 2026).

## Reward
Low $500 / Medium $2,500 / High $5,000 / Severe $15,000 (discretionary). Paid ≤30 days after contract.
KYC for payout: government photo ID + W-9 (US) / W-8 (non-US).

## Scope classes (with starting severity)

**Model bugs — must be IN the model itself, not the surrounding ecosystem:**
| Class | Severity |
|---|---|
| Prompt Extraction | LOW |
| Guardrail Jailbreak | LOW–HIGH |
| Interpreter Jailbreak (escape code-interpreter restrictions) | MEDIUM |
| Content Manipulation | HIGH |
| Weights & Layers Disclosure (extract closed-model IP to replicate) | SEVERE |

**App bugs — must start from prompt injection → unauthorized action:**
| Class | Severity |
|---|---|
| Read Violation (data exfil) | LOW–MED |
| Write Violation (data modification) | MED–HIGH |
| Execute Violation (command/code exec) | HIGH–SEVERE |

Affected models must be "commonly adopted" (OpenAI, Meta, Google, Anthropic, SalesForce, etc.), commercial or open-source, latest generation.

## Reporting flow (unique)
1. Create account (email/password/name/country).
2. **Abstract sign-off** (recommended): submit high-level abstract + affected model list → **3 business days** → in/out-of-scope + likely bounty range. *Then* submit full details.
3. Validation ≤2 weeks (confidential during this period; extends through disclosure if contracted).

## Duplicate policy
- Medium+: duplicate within 7 days splits bounty (unequal quality → lesser-report level + prorated bonus to the better one).
- Low: 1st=100%, 2nd=50%, 3rd=20%, rest credit only.

## Eligibility
Not Mozilla staff; not staff/contractor of the reported model's vendor; didn't contribute to the vuln; age of majority; not on US sanctions list / sanctioned country; can't exploit for personal gain.

## Key lessons from engagement (2026-11-05)
- **Wrapper contamination voids findings**: testing via a self-hosted router that injects its own system prompt means the "leak" is the router's prompt, not the model's. Must test native guardrails on a clean deployment.
- **DeepSeek V4.1 Flash guardrails held**: basic probes (system-prompt extraction, DAN) were all refused — no valid finding.
- **False-positive judge**: a naive keyword judge flagged "NOLIMITS"/"HACKED" echoes as bypasses — those were benign instruction-following, not jailbreaks.
