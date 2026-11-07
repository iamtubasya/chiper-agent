---
name: yandex-engagement
description: Use when auditing the Yandex bug bounty scope and rules.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, yandex, scope, engagement, authorization, llms]
    related_skills: [recon-scope-triage, bot-protected-target-testing, chain-to-impact, lead-to-critical, bug-bounty]
---

# Yandex Bug Bounty — verified engagement brief

## When to Use

When the operator names Yandex (or any `yandex.*` / `kinopoisk.ru` / `edadeal.ru` /
`bookmate.ru` / `band.link` host) as a bug-bounty target. Load this BEFORE touching any
host: it carries the mandatory `llms.txt` authorization gate, the verified in-scope domains,
the reward table that decides where to spend time, and the out-of-scope list to filter at
finding-gate.

Scope/rules rewritten 2026-11-02 by reading the live program end-to-end (headed
Playwright → Chrome, captcha bypass, then `/bugbounty/llms.txt` + every category page).

## 0. The `llms.txt` authorization gate (MANDATORY, read this first)

Yandex renders this verbatim on every scope page, and it binds the AGENT specifically:

> *"AI agents and automated tools must read and follow the vulnerability testing rules at
> `/llms.txt` before performing any security testing. If those rules cannot be accessed or
> followed, vulnerability testing is not authorized."*

**Non-obvious: it is NOT at the web root.** `https://yandex.com/llms.txt`,
`yandex.ru/llms.txt`, and `/.well-known/llms.txt` all 404. The real file is at
**`https://yandex.com/bugbounty/llms.txt`** (200, plain text). Fetch it raw with
`request.get()` (clean text), don't render it. Find the link by grepping the bounty page's
anchors for `llms|rules|regulat|policy|bounty`.

**This generalizes to any bug-bounty/VDP target.** An `llms.txt` (the `robots.txt`/`security.txt`
analogue aimed at LLM agents) is a NEW authorization artifact — if a program ships one, you MUST
read and follow it, and "stop and ask human approval" gates inside are binding. Never treat a web-root
404 as "no rules exist"; pull the real link off the bounty page.

The mandatory rules inside:
1. Read general rules + the applicable category rules before testing (precedence: general → category
   → target-specific → additional; most specific wins; if you can't determine applicability, **do NOT
   do intrusive testing**).
2. **Stop-and-ask-human** when: target not clearly in scope · may touch other users' data or act on
   their behalf · may cause degradation/artificial load · needs real-user interaction · needs
   third-party data · or sufficient evidence is already obtained.
3. **IDOR/BOLA discipline**: only self-created accounts/identifiers; after proving cross-account
   access between two accounts you control, STOP — don't enumerate real/unrelated user IDs.

## 1. In-scope domains (main scope)

```
*.yandex.ru  *.yandex.com  *.yandex.com.tr  *.yandex.kz  *.yandex.by  *.yandex.st
*.yandex.net  *.ya.ru  *.yandex-bank.net
*.kinopoisk.ru  *.edadeal.ru  *.bookmate.ru  *.band.link
```

`*.yandex.net` and `*.yandex-bank.net` are special: rewards paid **only for server-side-class
vulnerabilities** (no XSS/script-exec there — they're session-less/sandbox domains).

## 2. Reward table (max $, by service tier: Authentication > Key > Main > New)

| Class | Auth | Key | Main | New |
|---|---|---|---|---|
| RCE | $36,000 | $13,300 | $8,300 | $5,000 |
| ATO zero-click (beats 2FA) | $36,000 | — | — | $570–$1,100 |
| LFI/RFI/XXE · Injection | $12,000 | $6,700 | $4,100 | $1,700 |
| SSRF | $6,700 | $3,300 | $2,500 | $1,700 |
| SSRF blind | $2,200 | $1,600 | $1,200 | $500 |
| IDOR / sensitive-user disclosure | $2,500–$6,100 | $800–$2,100 | $500–$1,300 | $200–$500 |
| CSRF | 300–2,100 ₽ | 300–$800 | 300–$500 | 100–$300 |
| XSS (not self-XSS, not `*.yandex.net`) | 300–$2,700 | 300–$1,300 | 300–$800 | 100–$500 |

IDOR payout driver: data sensitivity (ride/order history, private email, private docs = highest) ·
identifier predictability (sequential/incremental > UUIDv4) · affected-user base.

Separate categories have their own reward tables (see below), but "Other vulnerabilities" always
fall back to Main-scope assessment.

## 3. Cloud category (yandex cloud, own tiers)

Cross-tenant IAM bypass (R/W $6k–$10k T1; read-data $5k–$8k) · unsandboxed SSRF w/ response
$2k–$6k · VM escape $36k · unsandboxed RCE $10k–$12k · single-tenant IAM bypass
$2k–$6k (R/W) / $1k–$4k (read).
Tiers: **T1** = Compute, VPC, Object Storage, managed-DB, managed-k8s, Console, Console-auth,
Cloud-Center, Identity-Hub, Data-Transfer, SpeechSense, Cert-Manager · **T2** = Monitoring, DataLens,
DataSphere, Backup, GitLab, Vision-OCR, YandexGPT-API, Foundation-Models, Container-Registry,
Message-Queue, Data-Streams, SourceCraft · **T3** = Load-Testing, CDN, IoT-Core, GitHub-hook env,
preview-status services.

## 4. AI/ML category (all YandexGPT/YandexART services: Alice, Neuro search, Shedevrum)

- training-data poisoning / supply chain: **$2,000–$11,000**
- info disclosure (third-party dialog history via prompt, system prompt, model weights/confidence):
  **$1,500–$11,000** (sensitive) / up to 2,000 ₽ (technical)
- prompt-injection-as-business-decision (affects search ranking, other users): **$500–$3,300**
- infrastructure behavior change (SSRF via prompt, cross-user behavior change): **up to $5,500**
- plugin vulns / billing bypass / technical restriction bypass: **up to $2,500**

## 5. Out-of-scope (filter at finding-gate BEFORE writing any report)

Scanner-only / automated-tool reports (N/A) · version/software-name disclosure without exploitation ·
public user info · IP/DNS/open-port info · TLS zero-day · SSL/TLS cipher reports without exploitation ·
lack of BCP/SSL · physical attack · missing security mechanisms without impact (missing tokens,
clickjacking, login/logout CSRF) · open redirect without token theft (HoF) · self-XSS & XSS outside
Chrome/Firefox/Yandex-Browser (HoF) · reflected-download / same-site scripting · XSS/CSRF requiring
extra user action · header-forgery XSS (Host/UA/Referer/Cookie) (HoF) · CORS misconfig on
`mc.yandex.ru`/`mc.yandex.com` + ad domains without impact · tabnabbing · content/text spoofing ·
missing flags on *insensitive* cookies · autosuggest · **lack of rate limit without proven impact** ·
SPF/DKIM/DMARC · known-vulnerable library without demonstrating exploitation · social engineering ·
partner-service vulns not affecting Yandex data · password-policy/auth-data "vulnerabilities" ·
Cloud user-project vulns (check WHOIS / bgb.he.net) · root/jailbreak mobile · restricted access-keys
embedded in APK · reverse-engineering apps · email spam/bombing · subvert attachment-antivirus ·
DLL hijacking / local code execution.

## 6. Hard rules that change how you run this target

- **No DoS, no artificial load.** If you think you found an infra-failure vuln, send the hypothesis —
  Yandex tests it in their own env. This means run the pipeline `BB_GENTLE=1`.
- **IDOR/BOLA**: two self-created accounts only; stop after proving cross-account access.
- **"Reports of security scanners and automated tools" are NOT rewarded.** The pipeline (0A–0F) is
  for lead *discovery*; what you submit must be a verified exploit with a proven impact chain
  (chain-to-impact / lead-to-critical), never a scanner dump.
- Review up to ~30 business days; reward reduced for poorly-written reports (skip repro steps = less).
- **90-day non-disclosure** after submission; no public posting of the vuln before fix.

## 7. Captcha / bot-protection note

Yandex front-end walls headless fetches behind `showcaptcha` ("confirm you are not a robot").
`browser-use` CLI / headless Chrome get blocked; a **headed** Playwright → real Chrome with a
persistent profile passes. Recipe (the one that worked):

```python
from playwright.async_api import async_playwright
ctx = await p.chromium.launch_persistent_context(
    PROFILE, headless=False, channel="chrome",
    args=["--disable-blink-features=AutomationControlled"],
    viewport={"width": 1366, "height": 768})
page = ctx.pages[0]
# fetch llms.txt RAW without HTML wrapper:
r = await page.request.get("https://yandex.com/bugbounty/llms.txt")
text = await r.text()   # clean plain text, no <html> wrapper
```
Profile dir: `~/.chiper/skills/bounty-pack/browser-profiles/yandex`. See `bot-protected-target-testing`
for the general anti-bot doctrine.

## 8. Command (PowerShell, ready to run)

```powershell
$env:BB_GENTLE="1"; python ~/.chiper/skills/bounty-pack/audit-pipeline-orchestrator.py "https://yandex.ru" --scope "*.yandex.ru,*.yandex.com,*.yandex.com.tr,*.yandex.kz,*.yandex.by,*.yandex.st,*.yandex.net,*.ya.ru,*.yandex-bank.net,*.kinopoisk.ru,*.edadeal.ru,*.bookmate.ru,*.band.link"
```

Suggested highest-value surface per reward table: (A) Yandex ID / Mail auth — ATO $36k / IDOR $6k;
(B) AI/ML (Alice, YandexGPT) — prompt-injection / system-prompt extract $1.5k–$11k, a surface most
hunters skip; (C) Yandex Cloud console/Storage — cross-tenant IAM bypass $6k–$10k.