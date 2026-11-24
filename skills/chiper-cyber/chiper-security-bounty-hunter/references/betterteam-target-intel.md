# Betterteam Target Intel & Program Scope

> **Program Status**: Active self-hosted bug bounty (opened 22 Oct 2026, policy updated 27 Oct 2026).
> **Contact**: `security@betterteam.com` (Subject: `Bug bounty: <short title>`)
> **RFC 9116 Endpoint**: `https://www.betterteam.com/.well-known/security.txt`
> **Payment Methods**: PayPal or Bank Transfer (USD or local currency equivalent). No crypto.

---

## 1. Reward Matrix (USD)

| Severity | CVSS v3.1 | Bounty Band | Archetype Examples |
|---|---|---|---|
| **Critical** | 9.0 – 10.0 | **$1,000 – $2,000** | RCE, SQLi accessing customer data, cross-account auth bypass, cross-tenant resume reading, zero-interaction ATO |
| **High** | 7.0 – 8.9 | **$400 – $800** | IDOR / BOLA on applicant or job data, stored XSS in dashboard, privilege escalation |
| **Medium** | 4.0 – 6.9 | **$150 – $400** | State-changing CSRF, reflected XSS, sensitive data in responses/logs, guessable candidate exposure |
| **Low** | 0.1 – 3.9 | **$50 – $150** | Minor info leaks, open redirect, critical rate-limit omission enabling brute force |
| **Info** | None | $0 | Informational / hardening |

*Note*: Static marketing site (`www.betterteam.com`) issues receive the band minimum unless demonstrably reaching customer data.

---

## 2. Attack Surface & Scope

### In-Scope Assets
- `dashboard.betterteam.com` — Primary web app (ATS, job posting, billing) and API.
- `files.betterteam.com` — Document/resume file storage and authorization controls.
- `app.betterteam.com` — Legacy app endpoints and legacy API.
- `betterteambugbounty.betterteam.com` — Dedicated test career site. **The only site where job applications may be sent (max 10 total).**
- `storage.googleapis.com` (GCS Buckets) — Betterteam-owned buckets referenced in app links (logo uploads, attachments). Stop at 1 object or listing proof.
- `s.betterteam.com` — Static asset bucket via Cloudflare.
- `i.betterteam.com` & `*.i.betterteam.com` — Fastly/internal measurement hosts (DNS included, no flood).
- `srp.betterteam.com` & `srp-api.betterteam.com` — Segment analytics reverse proxy (test proxy forwarding/header leaks; Segment backend out-of-scope).
- Subdomain Takeover: in-scope across `betterteam.com`, `betterteam.net`, `betterteam.xyz`, `betterteam.au`, `betterteam.com.au`, `bte.am`.

### Out-of-Scope Assets
- Customer career portals (`*.betterteam.com` other than test site) and custom customer domains.
- `careers.betterteam.com` — Internal hiring site (read-only; submitting application is a ban).
- Auth/Identity: **WorkOS** handles sign-in, sign-up, password reset, and 2FA codes.
- Staging environments: `betterteam.net`, `betterteam.xyz` (except dangling DNS/takeover).

---

## 3. Disqualification Pitfalls (Critical)

1. **Submitting job applications anywhere other than `betterteambugbounty.betterteam.com`** triggers an **instant permanent ban** and forfeiture of all unpaid bounties.
2. Hard cap of **10 applications** across all jobs on `betterteambugbounty.betterteam.com`. Higher volume requires advance written test-plan approval from `security@betterteam.com`.
3. Account sign-up email must contain `bugbounty` (e.g. `user+bugbounty@domain.com`).
4. Include HTTP header `X-Bug-Bounty: <trial-email>` where possible to assist triage.
5. Max request rate: **< 5 req/sec** aggregate.

---

## 4. Known Issues & Exclusions (Do Not Report)

- Persistent session after password reset, 2FA enable, or logout.
- JS source maps on `app.betterteam.com`.
- Free trial ability to post jobs without subscription (by design).
- Timing/existence difference on dashboard export download endpoints.
- Wildcard cookie scoping to `.betterteam.com`.
- Public/non-expiring resume URLs on `files.betterteam.com`.
- Third-party dependency CVEs published < 14 days ago.

---

## 5. Triage / WAF Bypass Technique for Policy Inspection

When server or scanner IP is blocked with Cloudflare 403 on `/bug-bounty`:
1. Query RFC 9116 `https://www.betterteam.com/.well-known/security.txt` directly (whitelisted by Cloudflare edge rules).
2. Start Tor multi-instance daemon: `sudo systemctl start tor@default` (SOCKS5 at `127.0.0.1:9050`).
3. Query Wayback Machine API: `curl --socks5-hostname 127.0.0.1:9050 "https://archive.org/wayback/available?url=https://www.betterteam.com/bug-bounty"`.
4. Fetch raw snapshot `http://web.archive.org/web/<ts>id_/<url>`. Note: raw archive response preserves upstream gzip encoding; decompress via `gzip.open` or `gunzip` before parsing.
