# GenAI Bug Bounty Scope — 0DIN (Mozilla) taxonomy

Condensed from https://0din.ai/policy (Last Updated 2026-10-02). 0DIN is Mozilla's GenAI bug
bounty — self-hosted portal, contact `0din@mozilla.com`. Its scope/severity taxonomy is a useful
template for *any* AI/LLM bounty program, since most GenAI bounties mirror this split.

## Payout tiers
Low $500 · Medium $2,500 · High $5,000 · Severe $15,000. Bounties discretionary. Paid ≤30 days
after contract; requires KYC (gov photo ID + W-9/W-8). May be donated to charity.

## Scope taxonomy (with starting severity)

### Model bugs — the flaw must exist INSIDE the model itself
| Class | Starting severity | Definition |
|---|---|---|
| Weights & Layers Disclosure | SEVERE | Extract IP of a closed model so it can be replicated |
| Content Manipulation | HIGH | Predictably inject harmful/misleading data the model consumes or produces |
| Interpreter Jailbreak | MEDIUM | Bypass the LLM interpreter's execution-environment restrictions → arbitrary code |
| Guardrail Jailbreak | LOW–HIGH | Inject malicious/altered prompts to manipulate output or jailbreak guardrails |
| Prompt Extraction | LOW | Unauthorized extraction of original inputs/queries given to the model |

### Application bugs — MUST start with prompt injection and result in an unauthorized action
| Class | Severity | Definition |
|---|---|---|
| Execute Violation | HIGH–SEVERE | Unauthorized command/code execution via the app |
| Write Violation | MEDIUM–HIGH | Unauthorized data modification via the app |
| Read Violation | LOW–MEDIUM | Unauthorized data exfiltration via the app |

## Scope rules
- Models must be **commonly adopted** (OpenAI, Meta, Google, Anthropic, SalesForce, etc.) and **latest generation**.
- Commercial OR open-source both eligible. Bug must be original/unreported.

## Report flow — "Abstract Sign-off" (the differentiator)
1. Create account (email, password, country, first/last name).
2. Submit a **high-level abstract** + list of affected models → team answers in **3 business days** with in-scope decision + likely bounty range. → *validate direction cheaply before full write-up.*
3. Full details → validated within 2 weeks → confidential 2 weeks (extends through disclosure if contracted).

## Duplicate policy
- Medium+: dupes within 7 days split the bounty (unequal quality → lesser-report level + prorated bonus to the better one).
- Low: 1st = 100%, 2nd = 50%, 3rd = 20%, rest = credit only.

## Eligibility (hard disqualifiers)
- Not Mozilla staff/contractor, not staff of the vendor whose model you're reporting, didn't author the vuln.
- Age of majority (or guardian consent); not on US sanctions list / sanctioned country.
- Must not exploit the vuln for personal gain.

## Public disclosure
- Model: publish after 0DIN deems it mitigated (their discretion).
- App: vendor uncontactable after 3 tries/2 weeks → disclose ≤30 days; contactable → 120 days to fix.

## Hunting priorities (ranked by ROI)
1. **Interpreter Jailbreak** ($2.5k) — code-interpreter escape; less crowded than web.
2. **Guardrail Jailbreak** ($500–5k) — PAIR/TAP/Crescendo/many-shot; most automatable.
3. **Prompt Extraction** ($500) — system-prompt extraction; fast entry.
4. **Weights/Layers Disclosure** ($15k) — model extraction/membership inference; hardest, largest.
5. **App bugs** — find public LLM apps, prompt-inject, prove concrete Read/Write/Execute.
