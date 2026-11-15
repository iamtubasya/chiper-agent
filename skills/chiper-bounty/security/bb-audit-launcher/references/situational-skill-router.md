# Situational Skill Router — load ONLY when the condition matches

> **Why this file exists.** The phase router (`security/bug-bounty/SKILL.md`) wires the *always-on* skills.
> ~60 further security skills are **condition-triggered**: they are correct, non-empty, and must load when
> the target shows a specific signal — not on every audit (that would blow the 120 KB phase budget).
> **Usage:** scan the CONDITION column while fingerprinting (0B) and before each 0C test batch. When a
> condition matches, `skill_view()` that skill and add it to the current phase. Nothing here changes the
> phase order or eviction rules.
>
> Legend: `→ skill` = load it. Path is relative to `skills/` unless it starts with `security/` or a category.

---

## 1. Target platform / stack

| CONDITION (signal on target) | Load |
|---|---|
| Adobe Experience Manager (AEM) — `/content/dam`, `/libs/granite`, `/crx/de` | `security/aem-attack-surface`, `security/hunt-aem` |
| SAP Commerce / Hybris — `/rest/v2/{site}/`, `/medias`, `/hac`, `/backoffice` | `security/hunt-hybris` |
| WordPress / Drupal / Joomla / generic CMS | `security/cms-security-testing` |
| Next.js App Router | `security/nextjs-app-security-testing`, `security/nextjs-server-actions-audit`, `security/server-actions-auth-audit` |
| Modern framework edges (RSC, CDP, MCP, feature flags, RPC) | `security/modern-web-framework-attacks` |
| SPA with a hidden backend API (`__NEXT_DATA__`, bundled routes, sourcemaps) | `hunt-spa-api` |
| vBulletin + Cloudflare + reCAPTCHA-Enterprise (e.g. forexfactory.com) | `security/forexfactory-engagement` |
| Undocumented / zombie / versioned API surface | `hunt-shadow-api` |

## 2. Authentication & session situations

| CONDITION | Load |
|---|---|
| JWT in use (any `Authorization: Bearer …` / session token) | `hunt-jwt-crypto` |
| OAuth / OIDC / SSO flow present | `security/hunt-oauth` (also `hunt-oauth`) |
| Forgot-password / account-recovery flow | `hunt-forgot-password` |
| You have working test credentials (authenticated surface) | `security/authed-webapp-audit`, `security/modern-webapp-auth-hunting` |
| Session must survive many steps / many tabs | `security/browser-session-daemon` |
| Auth audit must be driven via browser CDP | `security/browser-cdp-auth-audit` |
| You need test accounts to prove cross-account IDOR | `security/disposable-auth-identity` |
| Target needs a **verified account** before authed testing (signup behind reCAPTCHA + email verify) | `saas-test-account-provisioning` |
| Target leaks tenant config / API keys **pre-auth** | `security/unauth-config-disclosure` |

## 3. Blockers & bypasses

| CONDITION | Load |
|---|---|
| WAF blocks *every* path you try | `security/waf-stateful-bypass` |
| Google dork / SERP scraping hits the CAPTCHA wall | `security/google-dork-consistent` |
| curl is 403/429 but a real browser gets in | `security/bot-protected-target-testing` |

## 4. Business logic, financial & entitlement

| CONDITION | Load |
|---|---|
| Product handles **money** (prices, fees, balances, payouts) | `security/financial-logic-verification` |
| Tax / bookkeeping software (HMRC/MTD, self-assessment) | `security/tax-rule-verification`, `security/tax-calculation-audit`, `security/tax-rule-correctness-review` |
| SaaS plans / free-tier / feature gating | `security/saas-plan-entitlement-audit`, `security/entitlement-trust-testing` |
| Fintech GraphQL (money mutations, ledger, rounding) | `hunt-fintech-graphql` |
| Meme coin / token / SPL / Token-2022 | `meme-coin-audit` |
| Target is **realtime / pub-sub** (Ably, Pusher, PubNub, Socket.IO, Supabase Realtime) or mints **scoped tokens**; also webhook/outbound-URL SSRF | `realtime-capability-token-authz` |

## 5. Web3 / on-chain

| CONDITION | Load |
|---|---|
| Unknown EVM chain, only public RPC | `security/evm-chain-recon` |
| Verified contract source NOT in the repo | `security/onchain-source-recovery` |
| Need to verify a web3 finding before reporting | `security/onchain-finding-verification` |

## 6. Mobile

| CONDITION | Load |
|---|---|
| iOS app in scope (IPA, App Store, TestFlight) | `ios-redteam-pipeline` |
| Android app in scope (APK) | `apk-redteam-pipeline`, `android/android-emulator-automation` |

## 7. Recon / OSINT / scope

| CONDITION | Load |
|---|---|
| External OSINT needed (identity fabric: Entra/Okta/ADFS, person/org) | `offensive-osint`, `osint-methodology` |
| Need to pick an OSINT tool for a specific task | `osint-toolkit` |
| **Before any active testing** — confirm authorization/ownership | `recon-scope-triage` |

## 8. Lab / practice / local VM

| CONDITION | Load |
|---|---|
| Want a local copy of the vendor appliance to test freely | `security/vm-appliance-lab` |
| Drilling a technique on a lab range | `security/security-lab-range-practice` |
| PortSwigger Academy labs | `security/portswigger-labs` |

## 9. Tooling & execution discipline

| CONDITION | Load |
|---|---|
| Tooling not installed / wrong verdicts about "missing" tools | `security/security-tooling-setup`, `bb-local-toolkit` |
| Must enforce execution over skill-loading (the 13-check disk gate) | `security/audit-execution-discipline` |
| Considering autonomous multi-agent hunting | `autonomous-vuln-researcher`, `autonomous-ai-agents/superagent-v7` |

## 10. Evidence, reporting & disclosure (0D)

| CONDITION | Load |
|---|---|
| Capturing/reporting evidence (cookie redaction, PII black-bar) | `evidence-hygiene` |
| PDF report needed (reportlab) | `security/pdf-bug-report-generation`, `report-writing/reportlab-security-pdf` |
| Vendor/triager asks for a **video PoC** | `security/video-poc-production`, `report-writing/poc-video-production` |
| Coordinated disclosure to a developer/owner (non-platform) | `bug-bounty-disclosure` |
| Reward/severity question | `triage-validation` (7-question gate — enforced mechanically, see §11) |

## 11. Pre-report gate — MECHANICALLY ENFORCED (not advisory)

`triage_gate.py` runs inside the orchestrator between 0E and 0F and **blocks** any finding that fails the
7 questions. This list is no longer "remember to check" — it is a hard gate:

```
Q1 real impact on data/user/system/business-logic/funds?   Q5 not by-design / not documented behaviour?
Q2 proven with a reproducible request/response?            Q6 not only info/hardening/version/headers?
Q3 impact in the program's in-scope impact list?           Q7 not a scanner dump / tool error?
Q4 chain reaches the impact (no dead step)?
```
Fail any → the finding cannot reach the report. See `D:/data hermes/advisory-intel/patches/PIPELINE-AUDIT.md`.

## 12. Skill-library maintenance (not target-specific)

| CONDITION | Load |
|---|---|
| Creating/updating a skill | `skill-management`, `hermes-agent-skill-authoring`, `context-resilient-skill-design` |
| Auditing skills for duplicates/staleness | `skill-audit`, `skill-anti-duplicate` |
| Strengthening an existing skill | `skill-strengthen` |
| Auto-organising / auto-creating skills | `skill-auto-organize`, `skill-auto-create` |
| Mirroring a site/repo into a skill | `skill-management/site-to-skill-mirror` |
| SOUL.md / system-prompt loading | `skill-soul-loader` |
| Report tone polish (strip AI-isms) | `creative/humanizer` |

---

## Maintenance

- When a **new** condition-triggered skill is added, add one row here (condition first — the loader is
  condition-driven, not skill-driven).
- Keep this file **on-demand**. It is referenced from `reference-loader.md` (§0B/0C) but must NOT be
  loaded as part of the always-on bundle — it would waste budget.
