# Reading a self-hosted programme's policy — worked example

Companion to SKILL.md §10. Concrete, quoted mechanics from one real self-hosted programme
(Atmail, policy read 2026-09; the shape recurs across vendor-run programmes that take
reports by email). Use it as a template for what to extract from any policy page before
submitting — not as a mirror of that page.

## What to pull out of the policy, in this order

| Extract | Why it changes your submission |
|---|---|
| Reporting deadline + what starts the clock | Often 72 h from **discovery** for live assets; "withholding to stockpile or time submission" is a stated material violation. Late ≠ invalid, but it is a policy problem. |
| Required report fields | This one mandated **the `X-Bug-Bounty` header value AND the source IP(s) used**, plus a CVSS vector with no environmental/temporal modifiers, browser/OS/product version, and "all evidence inside the report — do not host on external services". |
| CVSS version | "latest published CVSS version" → compute 4.0. Same finding: **6.9 Medium on CVSS 4.0 vs 5.3 on CVSS 3.1** (`CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N`). |
| Payout table | Critical $5,000 · High $2,000 · Medium $500 · Low $50 · Informative $0 — severity assigned by the vendor "in its sole discretion"; your CVSS is only an input. Calibrate expectations before promising anything. |
| Accepted classes (CWE guide) | The list carries **no severity pre-assignment**. Its presence is your argument when the finding sits near an ineligible line. |
| Ineligible list | Read it as a checklist against your finding, BEFORE submitting. |
| Identity rules | "One identity per researcher", one email; rewards paid only to the verified submitter; sanctions/age/employee exclusions. |
| Strike system | 3+ invalid/non-reproducible reports in 90 days → 6-month suspension. Cheap to avoid: don't file weak adjacent variants. |
| Duplicates | First complete reproducible report wins; internally-known = ineligible (vendor must show the internal ticket on request); **one root cause, one reward** — don't split by host/endpoint/parameter. |
| Appeal envelope | Once per report, written, within 30 days, new technical evidence only. Not appealable: out-of-scope assets, unverified/AI-generated reports, bad-faith findings. |
| Safe harbour scope | Covers only in-scope assets; explicitly does **not** extend to third parties (suppliers, CDNs, customers). |
| Disclosure terms | No public disclosure without written permission; a backstop exists if the vendor goes silent for a set period. |
| Scan/AI clause | "Anything reported by passive or active automated scanners is ineligible" + "apparent unedited AI generation may be closed without response". Scanner output only counts once manually confirmed with a working PoC. |

## The contradiction to look for

The two tables can contradict each other, and that contradiction is the strongest argument
you have:

- Ineligible list: *"Most rate-limiting issues"* → Informative ($0).
- Accepted-class table: *"CWE-307 — Improper Restriction of Excessive Authentication
  Attempts — missing login rate limiting; CAPTCHA bypass"* → accepted class.

Resolution that actually works: do not argue about the class, argue about the **control**.
"Our tests show the lockout feature is switched off product-wide — your own unauthenticated
config endpoint returns `blockDuration: 0` on every host sampled — so this is not a tuning
preference, it is a security feature disabled in production." Evidence over adjectives.

## Scope trap to check before your report goes out

The clause usually reads: *"all domain scopes exclude any host that is a CNAME alias for a
third-party system or proxied directly to a third-party platform (e.g. billing./status./success.)."*

On a 155-host live list, the third-party aliases were: `support.*` → Zendesk,
`static./aws-signup./dev-vpn./docs.sdev.*` → CloudFront, two API hosts → a vendor SaaS
domain, two ops hosts → AWS ELB. Every host that was actually *named in the report* resolved
first-party. Run `scripts/host_scope_check.py` over the list and keep the two sets separate:
what you tested broadly vs what you cite.

Also worth knowing: a broad subdomain sweep will have already sent a few harmless requests to
some of those hosts. Disclose it in one line, name nothing, and stop — safe harbour covers
accidental good-faith violations, and the disclosure costs nothing.

## Evidence-handling duty (pairs with SKILL.md §1.1)

The programme's data-handling clause typically says inadvertently accessed sensitive
information must be reported, must not be stored/transferred/shared, and "must never appear
in public locations (including pastebins, screenshots posted externally, **or AI tool
prompts**)". Practical consequence for a report about a pre-auth config-disclosure endpoint:
show the key name + truncated prefix + SHA-256 as proof, never the raw value, and delete the
local JSON dumps after filing. The full-length keys in `settings_full/*.json` are the kind of
artifact that turns a valid finding into a policy exposure.
