---
name: yandex-audit
description: Use when hunting Yandex Bug Bounty. Scope, rewards, AI/ML.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, yandex, alice, yandexgpt, shedevrum, ai-security, llm]
    related_skills: [hunt-llm-ai, hunt-ssrf, hunt-idor, bot-protected-target-testing, cloud-iam-deep]
---

# Yandex Bug Bounty — scope & rules snapshot (verified 2026-11-02 via headed browser)

## Mandatory gate (target-required, do NOT skip)

Yandex publishes machine-readable rules at **`https://yandex.com/bugbounty/llms.txt`** (NOT the root
`/llms.txt`, which 404s). The page body states verbatim:

> "AI agents and automated tools must read and follow the vulnerability testing rules at /llms.txt
> before performing any security testing. If those rules cannot be accessed or followed, vulnerability
> testing is not authorized."

Read it (and the per-category page it links) before testing. Rule precedence: general → category →
target → vulnerability policy; specific beats general; if a rule's applicability is unclear, do NOT do
intrusive testing.

## Scope (main) — domains

```
*.yandex.ru   *.yandex.com   *.yandex.com.tr   *.yandex.kz   *.yandex.by
*.yandex.st   *.yandex.net   *.ya.ru   *.yandex-bank.net
*.kinopoisk.ru   *.edadeal.ru   *.bookmate.ru   *.band.link
```

Service tiers (highest → lowest): **Authentication services** (Yandex ID, Mail) → **Key services**
(Alice, Maps/Navigator, Market, Balance/Payment Gateway, Plus, Search, Metrica/Direct/Ad Network,
Yandex360, Taxi, FinTech, FoodTech) → **Main** → **New**.

## Reward table (max USD, main scope)

| Vuln | Auth svc | Key | Main | New |
|---|---|---|---|---|
| RCE | 36,000 | 13,300 | 8,300 | 5,000 |
| ATO (zero-click, bypass 2FA) | 36,000 | — | — | 570–1,100 |
| LFI/RFI/XXE | 12,000 | 6,700 | 4,100 | 1,700 |
| Injections | 12,000 | 6,700 | 4,100 | 1,700 |
| SSRF | 6,700 | 3,300 | 2,500 | 1,700 |
| SSRF blind | 2,200 | 1,600 | 1,200 | 500 |
| IDOR / sensitive disclosure | 2,500–6,100 | 800–2,100 | 500–1,300 | 200–500 |
| CSRF | 300–2,100₽ | 300–800 | 300–500 | 100–300 |
| XSS (not self, not *.yandex.net) | 300–2,700 | 300–1,300 | 300–800 | 100–500 |

IDOR payout scales on: sensitivity of data, predictability of identifier (sequential > UUIDv4),
affected user base.

## AI/ML Security category (this is the high-value/low-noise surface)

Scope = **all Yandex services using generative models (YandexGPT / YandexART families)**:
`Alice`, `Neuro search`, `Shedevrum`, plus any service using those models for ranking/search.

| Category | Example | Reward |
|---|---|---|
| Data/training poisoning, supply chain | poison source → future response quality | $2,000–$11,000 |
| Info disclosure (dialog history of OTHER users via prompt; system prompt w/ real technical data) | retrieve third-party dialog history; extract weights/confidence/system prompt | $1,500–$11,000 (sensitive) / ≤$2,000₽ (technical-only) |
| Business decision adversarial attack | prompt-injection in product description → search ranking | $500–$3,300 |
| Infrastructure attack (cross-user behavior, SSRF via prompt) | `set_mode=french` for everyone; prompt → SSRF internal | up to $5,500 |
| Plugin/tool abuse, billing bypass | plugin fetch → internal host; Market price → 0₽ | up to $2,500 |

### AI exceptions — what does NOT pay (read before burning time)

- **Ethical issues** (bias, hallucination, wrong facts) — reported via other channel, not bounty.
- **Prompt injection that only affects the ATTACKER's own output** (own chat style, own image style) — NOT rewarded. Injection MUST have a security impact: affect OTHER users, SSRF, steal another user's data.
- **System-prompt dump WITHOUT significant technical secret** — "own UID / OrgID" is not a secret. You must leak a NON-guessable technical secret (internal URL, token, weight, config).
- **Model hallucination** — simulating code exec / disclosure is not real. Use `ssrf-sheriff` to prove code actually executed.
- **Availability/DoS** — do NOT test yourself; report the hypothesis, they test in their own env.
- Third-party Yandex Cloud client services (out of scope this category). Spoofing chat system-markup without actual XSS.

## General rules (all categories)

- **Own account only** for testing; never access other people's accounts/data. For IDOR/BOLA use TWO researcher-controlled accounts; NEVER enumerate/guess real/unrelated user IDs to confirm (llms.txt "Authorization vulnerabilities").
- **DoS / resource exhaustion** → do NOT test; send hypothesis, they verify. Rule: "Do not check and exploit potential DoS".
- **No artificial load**; treat everything as production.
- **Report quality**: concise, reproducible PoC, only verified findings; mass/unverified/auto-generated reports → temporary program restriction. No invented terminology.
- Disclosure embargo: 90 days; no public PoC.
- Rewards NEW vulnerability only (dupe = earlier report number wins / known 0day/1day).

## Explicitly out of scope (main)

Reports of security scanners/automated tools (i.e. must submit proven EXPLOIT+IMPACT, not scanner
dump) · software name/version disclosure · public user info · version-based vuln w/o exploitation ·
IP/DNS/open-ports info · insecure TLS ciphers w/o exploitation · missing security mechanisms w/o
impact (CSRF tokens, clickjacking, Cookie flags) · open redirect w/o token theft · self-XSS · XSS
needing user action / header injection · CORS misconfig on mc.yandex(.ru|.com) w/o impact ·
tabnabbing · content spoof w/o impact · no rate-limit w/o impact · SPF/DKIM/DMARC · known-vulnerable
library w/o exploitation · social engineering/phishing · partner services w/o Yandex user data ·
password/vuln-of-auth-data · user projects in Yandex Cloud · rooted/jailbroken-only mobile ·
restricted access keys · outdated-browser-only · physical access · script exec on sandbox domains
(*.yandex.net) · Connect domains (transition period) · decompile/reverse-engineering · email
spam/bombing · antivirus-bypass · DLL hijacking/local-only.

For `*.yandex.net` / `*.yandex.st`: rewards server-side class vulns ONLY.

## SmartCaptcha — the access wall (verified live)

`yandex.com` puts Yandex **SmartCaptcha** in front of the bounty pages and many services; headless +
browser-use get redirected to `/showcaptcha`. Bypass path that worked: **Playwright + headed real
Chrome + persistent profile** (`--disable-blink-features=AutomationControlled`), click the checkbox.
Profile dir: `~/.chiper/skills/bounty-pack/browser-profiles/yandex`. Script: `scripts/yandex_scope_headed.py`.

## Command (PowerShell, GENTLE + full scope)

```powershell
$env:BB_GENTLE="1"; python ~/.chiper/skills/bounty-pack/audit-pipeline-orchestrator.py "https://yandex.ru" --scope "*.yandex.ru,*.yandex.com,*.yandex.com.tr,*.yandex.kz,*.yandex.by,*.yandex.st,*.yandex.net,*.ya.ru,*.yandex-bank.net,*.kinopoisk.ru,*.edadeal.ru,*.bookmate.ru,*.band.link"
```

## Strategy — highest value, lowest noise

1. **AI/ML** (this category): cross-user/state poisoning ($5.5k) + other-user dialog-history disclosure
   ($11k) + SSRF-via-prompt ($5.5k) + plugin/billing abuse ($2.5k). Use `hunt-llm-ai`.
2. **Auth (Yandex ID/Mail)**: ATO $36k, IDOR $6k — but behind captcha + high competition.
3. **Cloud**: cross-tenant IAM bypass $6k–$10k (`cloud-iam-deep`, `hunt-cloud-misconfig`).

Relationship to pipeline: the 0A-0F pipeline is for RECON + lead discovery; the ACTUAL submission
must be a proven exploit+impact (scanner reports are explicitly NOT rewarded).