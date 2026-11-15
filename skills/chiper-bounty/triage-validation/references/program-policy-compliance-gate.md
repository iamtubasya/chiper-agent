# Program-Policy Compliance Gate — worked example

Source: an email-submission bug-bounty program (vendor-published policy page, Sept 2026).
Two findings (missing login rate limiting, unauthenticated config/secret disclosure) were
drafted and then audited against the live policy before sending. Everything below is the
shape of what that audit caught. Generalise to any program.

---

## 1. What the policy page handed us (mechanics worth extracting from ANY policy)

| Element | This program | Why it matters to the submission |
|---|---|---|
| Submission channel | email to a bounty alias, evidence as attachments | No platform UI, no auto-scope checks, no "incomplete" warnings — you must self-audit. |
| Payout table | Critical $5,000 / High $2,000 / Medium $500 / Low $50 / Informative $0 | Low is $50. An Informative-class finding is not worth a strike. |
| Severity authority | CVSS base score **adjusted by the vendor**, "sole discretion" | Your proposed vector is an input, not a decision. Say so in the report to look calibrated. |
| Accepted classes | a CWE table (78, 89, 200, 307, 352, 434, 601, 611, 79, 862/863, 918, 444 …) explicitly "no severity pre-assignment" | Enumerated CWE = your strongest argument when the ineligible list tries to sweep the class away. |
| Required report fields | description, steps, working PoC on a live asset, impact, **CVSS vector on the latest version**, affected URLs/params, browser/OS/product version, **traffic-identifier header value**, **source IP(s) used** | The last two are the ones researchers forget. Missing them = "incomplete". |
| Reporting clock | live assets **within 72 hours of discovery** | Compute from your own evidence file mtime. |
| Quality rules | no scanner output without manual confirmation; "apparent unedited AI generation" may be closed untriaged | Manual verification + human voice are compliance requirements, not style. |
| Strikes | 1 = warning, 2 = final, 3 = 6-month ban + forfeit, 4 = permanent; separately "3+ invalid reports in 90 days = 6-month suspension" | The real cost of a borderline submission. |
| Duplicates | first complete reproducible report wins; internally-known = not eligible; **one root cause = one reward**; splitting = violation | Don't split variants per host. Do note extra instances inside one report. |
| Disclosure | no public disclosure without written permission; 180-day no-response backstop | Don't blog it. |
| Appeals | once per report, within 30 days, **new technical evidence or a specific articulated error** only | Write the appeal ammunition while evidence is fresh. |
| Safe harbour | covers in-scope assets + "accidental, good-faith violations" | Makes proactive disclosure of a scope slip the low-risk option. |
| Governing law | the vendor's home jurisdiction | Note it; don't argue in email. |

## 2. The self-contradiction you can exploit — carefully

The ineligible list said (verbatim shape):

- "Most rate-limiting issues"
- "Verbose error pages; software version disclosure; account/email enumeration without
  demonstrated PII exposure"
- "Missing security HTTP headers; missing cookie flags; CSP preferences"

The accepted-class list said: **CWE-307 — Improper Restriction of Excessive Authentication
Attempts — missing login rate limiting; CAPTCHA bypass** and **CWE-200 — Information
Exposure including admin/status pages with credentials**.

So both findings sat on both sides of the policy. The winning argument is *specific*:

- **Rate limiting (CWE-307):** not "the limit is loose" but "the lockout feature is OFF in
  production, by the product's own config that leaks pre-auth (`blockDuration: 0` on every
  host tested), and 60 consecutive failed logins never locked, throttled or challenged".
  Disabling a security control product-wide is not "a rate-limiting issue".
- **Config disclosure (CWE-200):** not version/banner disclosure. It is third-party API
  keys + OAuth client IDs + per-tenant internal config, pre-auth, on production AND
  staging — the policy's own CWE-200 example ("admin/status pages with credentials").
  Be honest that the leaked Google keys proved RESTRICTED (`REQUEST_DENIED`), so there is
  no monetisable abuse — that keeps the severity claim defensible.

Write both framings into the report body explicitly, so the triager does not have to
reconcile the contradiction themselves.

## 3. CVSS 4.0 numbers computed, not guessed

```python
# pip install cvss
from cvss import CVSS4, CVSS3
CVSS4("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N").base_score  # 6.9 Medium
CVSS3("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N").base_score                     # 5.3 Medium
# sensitivity of the same finding, for knowing where the tier lines are:
#   VC:H  -> 8.7 High    UI:A -> 5.1 Medium    AT:P -> 6.3 Medium
```

Both findings here map to the conservative 6.9/Medium. Note the practical lesson: CVSS 4.0
is often HIGHER than 3.1 for confidentiality-only impact — so "we scored it 5.3 on 3.1"
is not a reason to skip the 4.0 vector if the policy asks for the latest version.

## 4. Scope verification, run before submission

`dig` was not available; `nslookup -type=CNAME` was. Batch-checked ~155 live hosts from the
recon list and split them:

| Bucket | Example | Action |
|---|---|---|
| direct / first-party CNAME | `demo.atmail.com → us-east.atmailcloud.com`; `autoconfig.orchid.atmailcloud.com → admin.orchid.atmailcloud.com` | safe to name |
| third-party alias | `support.* → *.zendesk.com`; `static/aws-signup/dev-vpn/docs.sdev.* → *.cloudfront.net`; `mpl.* → api-us1.chd01.com` | omit from the report entirely |
| judgment call | `ops-api.pc5*.atmailcloud.com → …elb.amazonaws.com` (vendor's own AWS ALB) | read the exclusion's example list; if ambiguous, leave it out |

Because the broad subdomain sweep had incidentally sent a few GETs to the third-party
aliases (all 403/404, nothing retrieved), the submission carried one proactive disclosure
line rather than silence. Confirm the hosts you NAME are clean, not just the host you
found the bug on.

## 5. Evidence duties that came from the policy, not from good manners

The policy required: stop on encountering sensitive info, report the exposure, and
**"permanently delete all copies"** — with sensitive data never stored, transferred,
shared, or placed in public locations, explicitly including **AI tool prompts**, plus
"all supporting evidence must be contained within the report itself / do not host evidence
on external services".

Consequences for the submission as drafted:

- The report and local evidence files contained the leaked keys in the clear → redact to
  prefix + SHA-256 (`devKey "D9K5nAIr…"  sha256:1f9c…`), which proves possession without
  republishing the secret, and delete the raw dumps after submission.
- "63 hosts affected" is enumeration beyond "least possible data access" as the policy
  defines it → lead with ONE minimal repro (one host, one unauthenticated request) and
  offer the rest on request.
- Never "prove" a leaked third-party key by exercising it against the third party's API
  beyond a bare validation call — that is unauthorised testing of a third party, outside
  scope and outside safe harbour.
