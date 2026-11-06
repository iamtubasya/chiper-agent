# Tool-Aiming + Entitlement/Business-Logic Review — evidence pack

Source: QuarterWise.co.uk re-audit (2026-09-28). Companion to SKILL.md §10, §11, §12.
Purpose: the raw verdicts + recipes a future session can trust and re-run, so a hardened
target is reported as a verified negative instead of a false "clean".

---

## A. The correction that triggered §10

User: *"maksudnya gkad temuan? bener kamu udh pakai tools nya semua sesuai target? bukan
curl aja?"* — pointing out (correctly) that earlier runs aimed raw tools at unparameterised
root URLs. Evidence files proved it:

| File | Content | Meaning |
|---|---|---|
| `tool-evidence/dalfox-xss.txt` | `unknown command "https://…" for "dalfox"` | never scanned |
| `tool-evidence/CORScanner-cors.txt` | `Error: unrecognized arguments: --headless` | never scanned |
| `tool-evidence/SSRFmap-ssrf.txt` | `ssrfmap.py: error: the following arguments are required: -r, -p` | never ran |
| `tool-evidence/sqlmap-sqli.txt` | `[CRITICAL] no parameter(s) found for testing` | tested nothing |
| `tool-evidence/nosqli-nuclei.txt` | target URL = an out-of-scope `gov.uk` URL | wrong target |

Lesson enforced in the skill: **grep each tool's evidence file for the no-op strings before
you write "0 findings".**

---

## B. Correctly-targeted re-run — real verdicts

Authed URL list (real routes + real params) + session cookie passed to every tool.

**sqlmap** (level 3 / risk 2 / `--technique=BEUST`, with `--cookie`):
```
/app/other-income?ty=2026-27   -> [WARNING] GET parameter 'ty' does not seem to be injectable
                                  [WARNING] Cookie parameter 'qw_session' does not seem to be injectable
                                  [WARNING] parameter 'User-Agent' does not seem to be injectable
                                  [WARNING] parameter 'Referer' does not seem to be injectable
                                  [CRITICAL] all tested parameters do not appear to be injectable
/app/sources/{uuid}?ty=2026    -> same
/api/v1/categories?sourceType= -> [WARNING] GET parameter 'sourceType' does not seem to be injectable
```

**commix** (level 2–3, `--cookie`, ~44 probes per endpoint) → every probe:
`[warning] Detected a false positive or unexploitable injection point` and **no**
`is vulnerable` / `exploitable` confirmation → not injectable.

Setup fix that unblocked commix on Python 3.14:
`pip uninstall -y pyreadline pyreadline3` (pyreadline's `collections.Callable` breaks),
then `python commix.py --url=... --batch`. Before the fix it printed a traceback and a
"generate a GitHub issue?" prompt — that is a broken install, not a scan result.

**nuclei** — 3 runs:
- unauth, all templates: 7035 templates, 10 921 req, **0 matches**
- targeted tags (cve/exposure/misconfig/takeover/default-login/config/backup/disclosure):
  6097 templates, 44 113 req, **0 matches**
- authed (16 URLs, tags exposure,misconfig,sqli,xss,ssrf,idor,auth-bypass,cve):
  44 827 req / 54 min, **0 matches** (note: some targets auto-skipped as unresponsive →
  honest partial coverage)

**ffuf** — param VALUE fuzz on `?ty=FUZZ` (28 payloads: SQLi/XSS/traversal/SSTI/CRLF/null):
response sizes clustered 67 200–67 700 B across ALL payloads = no differential.
param NAME fuzz (42 candidates on `/api/v1/categories?FUZZ=1`) = 0 new params.
Authed dir fuzz `/app/FUZZ` (30 words) = only the known routes.

**arjun** — 4 authed endpoints, no hidden params (crashed on an endpoint returning a plain
dict — tool quirk, note it, don't claim coverage from that endpoint).

**dalfox** — correct CLI `dalfox file urls.txt --header "Cookie: …"`. It mined
"43 testing point in DOM base parameter mining" on the RSC page, but the scan stalls against
a Cloudflare-fronted RSC page (no completion after 30+ min). Honest note: dalfox authed
= partial coverage, mitigated by manual + live-browser runtime XSS checks.

---

## C. RSC-reflection false positives (debunk recipe)

`?ty=<payload>` reflects into `self.__next_f.push` flight data. Definitive disambiguation:

| Probe | Expected if BUG | Observed | Verdict |
|---|---|---|---|
| baseline `?ty=2026-27`, grep `49` | absent | **present** (year digits) | earlier "SSTI 49" was a baseline artefact |
| `?ty={{1337*3}}` grep `4011` | present | absent (literal reflected) | not SSTI |
| `?ty=../../../../etc/passwd` grep `root:x:0` | present | absent (path echoed only) | not LFI |
| `?ty=<script>alert(1)</script>` | raw `<script>` | `\u003cscript\u003e` | not XSS |
| `?ty=2026-27%0d%0aX-Injected:yes` | response header | no injected header | not CRLF |

Live-browser DOM check (`?tab=`, `#<img onerror>`, `?foo=<svg onload>`) — navigate, then read
`document.title`: unchanged = not DOM-XSS. The `?tab=` value must also match an existing tab
id (unknown input dropped).

---

## D. Payment / Pro-entitlement matrix (all NEGATIVE = secure)

| # | Test | Result |
|---|---|---|
| 1 | upgrade click → plan without payment | redirects to `checkout.stripe.com/c/pay/cs_live_…`; plan stays `free` |
| 2 | fabricated success URLs ×8 | all `isPro=false` (no client-trusted flag) |
| 3 | forged webhook `Stripe-Signature: t=…,v1=<random>` ×3 | `{"error":"invalid signature"}` 400 |
| 4 | webhook `missing`/`garbage`/`v0`-only | `missing signature` / `invalid signature` 400 |
| 5 | arbitrary webhook JSON bodies | 400 (signature checked before parse) |
| 6 | checkout action field tamper (`interval=lifetime_free` etc.) | no entitlement path |
| 7 | `plan=pro` / `amount=0` / `trial=1` in action fields | no effect, plan unchanged |
| 8 | sibling webhook paths (`/api/webhooks/stripe`,…) | 404 — only the signature-gated one exists |

Source of truth used: `GET /api/account/export` → `account.plan`. Also note the export is
**rate-limited** (`429 "Too many exports. Try again in an hour"`).

Ethics note recorded in the skill: tested entitlement design only; did NOT complete a fake
payment or forge a live value (that is fraud, not research).

---

## E. Free-tier business-logic / tax-year mapping (VERIFIED CORRECT)

Clean-room account, unique-value boundary entries, ground truth from `?format=xlsx` export
(unzip → `xl/sharedStrings.xml` + `xl/worksheets/sheet1.xml`).

| Entry | Expected tax year | Actual (export) |
|---|---|---|
| 2025-04-06 (£992) | 2025-26 | 2025-26 ✅ |
| 2026-04-05 (£993) | 2025-26 (last day) | 2025-26 ✅ |
| 2026-04-06 (£994) | 2026-27 (first day) | 2026-27 ✅ |
| 2026-07-05 (£995) | 2026-27 Q1 | 2026-27 ✅ |
| 2026-07-06 (£996) | 2026-27 Q2 | 2026-27 ✅ |
| 2027-04-05 (£997) | 2026-27 (last day) | 2026-27 ✅ |
| 2027-04-06 (£998) | 2027-28 (first day) | 2027-28 ✅ |

Per-year totals matched member sums exactly (2025-26=£2085 · 2026-27=£4882.03 ·
2027-28=£1098 · all=£10055.03). **No off-by-one, no double-count.**

Input validation (free-tier entry form):
- rejected: negative/zero, `> £100,000,000`, `> 2 decimals`, empty, `1e5`, `NaN`,
  `Infinity`, `1';DROP--`, `<img onerror>`, non-ASCII digits
- accepted (parsed correctly): `1,000.00`, `£100`, ` 100 `
- category/type mismatch → "Choose a valid category"; invalid date → "Choose a valid date";
  far-future date → "real date between 2000 and next year"
- precision: `0.01 × 3` → exactly **0.03**; net = income − expense exact
- `submissionId` replay → deduped (no double count)

Self-debunk notes: (1) "6 boundary entries missing" was page pagination — the XLSX export
contained them all; (2) verify counts from the export, never the rendered page.

---

## F. Quarterly (MTD) flow + 2FA/NINO gates

- Free-tier: quarterly updates page is free; figures are gated behind **2FA + NINO +
  Government Gateway authorisation** (the last needs real HMRC credentials — a legitimate
  black-box coverage gap, not a finding).
- **2FA self-enrolment (own account):** `beginMfaSetup` requires the **account password**
  first ("a stolen session cannot do it"), then reveals a Base32 secret + QR; confirm with a
  `pyotp.TOTP(secret).now()` code → MFA on. Disable requires a current code. Enrolling MFA
  unblocked previously gated pages — do this early when the engagement needs MFA-gated flows.
- **NINO save** (`saveNino`) validates format (`AB123456C` ok; `INVALID123`, `QQ12345`,
  `1234567890` rejected) AND requires `mfaCode` server-side.
- Local setup: `pip install pyotp` to generate TOTP codes instead of hand-rolling HMAC.

---

## G. Quick reusable probe (adapt targets/fields)

See `scripts/nextjs-server-action-probe.py` in this skill for a copy-paste harness that:
logs in via the action wire format, replays a server action with router-state-tree, and
dumps the captured request — the pattern that produced sections A–E above.
