# YesWeHack Platform Workflow

## Platform Overview
- French bug bounty platform (yeswehack.com), major EU programs
- Two API versions coexist — **v2 is partially broken**, use v1-style endpoints
- Unlike Bugcrowd (React SPA, needs aggregator), YesWeHack exposes program data directly

## Program Enumeration

### Search programs by keyword
```bash
curl -s "https://api.yeswehack.com/programs?search=<KEYWORD>" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Total: {data.get('pagination', {}).get('nb_results')} results\")
for p in data.get('items', []):
    print(f\"{p.get('slug')} | {p.get('title')} | bounty:{p.get('bounty')} | vdp:{p.get('vdp')}\")
"
```
- Pagination: `?page=N` (default 42 per page, `nb_pages` in response)
- Filter: `?search=teamviewer` returns fuzzy-matched results

### Get specific program (rules + scopes)
```bash
curl -s "https://api.yeswehack.com/programs/<SLUG>" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Title:', data.get('title'))
print('Slug:', data.get('slug'))
print('Rules:', data.get('rules', 'N/A')[:500])
print('Rewards:', json.dumps(data.get('rewards', []), indent=2))
print('Scopes:', json.dumps(data.get('scopes', []), indent=2))
"
```

## ⚠️ API Pitfalls (discovered 2026-09-07)

### v2 endpoint is unreliable
The `https://api.yeswehack.com/v2/programs?slug=<SLUG>&with_fields=...` endpoint frequently returns 404. Do NOT rely on it.

### Correct endpoints
| Action | Endpoint |
|---|---|
| Search programs | `GET /programs?search=<q>` |
| Get program details | `GET /programs/<slug>` |
| Reports API | Not public (requires auth) |

### Scope format from API
Scopes come back with:
- `scope_type`: `"application"` (not `"in_scope"`)
- `type`: `"web-application"`, `"mobile-application-android"`, etc.
- `target`: often empty string in API — actual targets listed in `rules` text (parse manually)

### Rewards field
`rewards[]` is often **empty** even for bounty programs. Check the `rules` text for payout tiers, or view the program page directly.

## Browser Submission Flow
YesWeHack requires authenticated browser session for report submission:
1. Navigate to `https://yeswehack.com/programs/<slug>`
2. Click "Submit a report" button
3. Fill: Title, Severity, Category, Description, Steps to Reproduce
4. Attach PDF/screenshots
5. Submit

**When browser CDP is unavailable:** Prepare complete submission package (PDF + formatted report text) for user to submit manually.

## Key Response Fields (verified 2026-10, zecible program)
Core: `slug`, `title`, `bounty` (bool), `vdp`, `status` ("V"=live), `rules`, `scopes[]`
(`scope`, `scope_type` — "web-application"/"api"/…, `asset_value` — CRITICAL/HIGH/MEDIUM/LOW/VERY_LOW).

**The fields worth reading BEFORE touching any host:**

- `user_agent` — template like `{{your_username}}`. This is a BINDING program rule: every tool
  request (httpx, ffuf, nuclei, curl) must carry `-H "User-Agent: <your-ywh-username>-bounty-hunter …"`.
  Non-compliant UAs can get you blocked by the target's WAF ("apply hunting requirements policy,
  specifically User-Agent … you might be blocked from our assets"). Set it in EVERY tool invocation.
- `reward_grid_critical|high|medium|low|very_low` + `reward_grid_default` — the REAL reward table:
  `{bounty_low, bounty_medium, bounty_high, bounty_critical}` in EUR, keyed by each scope entry's
  `asset_value`. `rewards[]` being empty is NORMAL — the grid IS the payout table. Also
  `bounty_reward_min`/`bounty_reward_max`.
- `out_of_scope` — usually "all domains/subdomains not listed in Scopes". Scope follows the LISTED
  host, not the brand.
- `qualifying_vulnerability[]` and `non_qualifying_vulnerability[]` — read both in full. The
  non-qualifying list is long and kills whole workstreams before you start (typically: user
  enumeration, rate-limit/brute-force/captcha, open redirect, missing security headers, GraphQL
  introspection, blind SSRF without PoC, session-management issues, content/text injection,
  clickjacking, missing cookie flags, disclosed public API keys, CSV injection, subdomain takeover
  without full PoC, HSTS, SPF/DKIM/DMARC, weak password policies). Drop those classes from your
  plan; reporting them wastes quota and credibility.
- `account_access` / `account_access_html` — the test-account policy, decisive for coverage
  planning. Typical text: "No test accounts are provided and there is no self-registration on the
  in-scope hosts: test what is reachable without an account" → your entire engagement is UNAUTH;
  authenticated classes (IDOR/ATO/business-logic on account state) become a coverage wall, state
  it explicitly rather than claiming negatives. Also often forbids creating accounts on
  out-of-scope siblings (e.g. www).
- `systemic_issue_rule_enabled` + `systemic_issue_rule_grid` — dedup payback for repeat reports of
  the same root cause (e.g. level1 100%, level2 100%, level3 75% … level6 10%). NOT a known-issues
  list — there is no public known-issues endpoint (`/programs/<slug>/known-issues` → 404) and no
  HTML section; dedupe happens at triage, so favour novel root causes on crowded programs.
- `leakage_rule_enabled` + grids — how leaked data in/out of scope is scored.
- `stats` — `total_reports`, `total_reports_last_7_days`, `total_reports_current_month`,
  `average_first_time_response`. Crowding intel: 200+ reports / 16-per-month = heavily hunted,
  angle for novelty matters more than speed.
- `business_unit.description` — one-line description of the vendor's core business. Fastest seed
  for your business-logic map (e.g. "selection of prospecting files of professionals and
  individuals" → data broker → credits/file-exchange/GDPR-portal/OTP flows are the money paths).
- `restricted_ips`, `vpn_active`, `vpn_ips` — VPN requirement if present.
- `rules_html`/`account_access_html` — HTML variants when the markdown truncates.

## YWH pre-test extraction order
1. `user_agent` → wire UA into every tool before the first request.
2. `scopes[]` + `asset_value` + `out_of_scope` → target list + reward expectation per host.
3. `account_access` → auth posture (unauth-only? contact-form-only?) and hard coverage walls.
4. `qualifying_vulnerability` / `non_qualifying_vulnerability` → kill list for your test plan.
5. `stats` + systemic grid → novelty pressure.
6. `business_unit.description` + `rules` → core-bisnis & business-logic hypothesis map.

## Pitfalls
- **v2 API broken** — always prefer `/programs/<slug>` over `/v2/programs?slug=...`
- **Scope targets empty in API** — parse `rules` text for actual scope definitions
- **Rewards array empty** — read `reward_grid_*` keyed by scope `asset_value`; program page UI mirrors it
- **Report submission requires auth** — no public API for creating reports
- **Known issues invisible** — no endpoint, no HTML; do not burn time hunting for the list
- **YWH-hosted targets run "YwhModSec"** (Server header) with HSTS and aggressive rate limiting —
  keep batches tiny (see references/passive-recon-during-target-lockout.md)

## Session Provenance
Updated from live session 2026-09-07: TeamViewer program discovery via `curl https://api.yeswehack.com/programs?search=teamviewer` → found slug `teamviewer-bounty-program`, confirmed `account.teamviewer.com` in-scope via rules text.
