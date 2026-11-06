# Program Info Discovery + Auth-Bypass Probing (Recon Techniques)

Condensed recon patterns from TeamViewer session (2026-09). Use during Phase 0 before any report.

## 1. Bounty Program Discovery — use APIs, not SPA scraping

Most program pages (YesWeHack, TeamViewer trust center, HackerOne) are Angular/Next SPAs — curl+grep only gets meta tags. Go straight to the platform JSON APIs:

**YesWeHack (works unauthenticated):**
```bash
curl -s "https://api.yeswehack.com/programs/<program-slug>" -H "User-Agent: Mozilla/5.0" | python3 -m json.tool
```
Returns in ONE call: `scopes[]` (with `asset_value` CRITICAL/HIGH), `bounty_reward_min/max`, `reports_count`, `type` (bug-bounty vs vdp), full `rules` markdown, scope_type (application/web-application/mobile). Slug = URL path segment of the program page (`yeswehack.com/programs/<slug>`).

**Program page check (search engines):**
- `"<target>" bug bounty program yeswehack OR bugcrowd OR hackerone OR intigriti`
- Target's own trust-center page tells you WHICH platform hosts the paid program.

**Key scope clause to look for:** many programs include "Backend services you might directly interact with from the client app are considered part of the scope" — this pulls API hosts (webapi.*, api.*) into scope even when only frontend domains are listed. Always quote this clause in the report's scope justification.

**Paid vs VDP gate:** check `bounty_reward_min/max` and `vdp` flag before investing hours. VDP-only = skip per payout gate.

## 2. Auth-Bypass Probe — 404 vs 401 pattern

Detects missing/misordered auth middleware on GUID-routed APIs WITHOUT needing an account.

**Method:**
```bash
# A) Random GUID — bypasses route constraints, tests resource path
curl -s -o /dev/null -w "%{http_code}" "https://api.target.com/api/v1/contacts/6f1c2e3a-9b4d-4c5e-8f7a-1d2e3f4a5b6c"
# B) Zero GUID — often hits a different (guarded) route
curl -s -o /dev/null -w "%{http_code}" "https://api.target.com/api/v1/contacts/00000000-0000-0000-0000-000000000000"
# C) No GUID — baseline
curl -s -o /dev/null -w "%{http_code}" "https://api.target.com/api/v1/contacts/"
```

**Interpretation:**
- Random GUID → **404** (not 401) = auth middleware NOT applied to that route pattern. 404 means the server processed the lookup unauthenticated.
- Zero GUID → **401** = auth filter DOES exist but has a gap (different route/middleware ordering). The 401-vs-404 delta IS the evidence.
- Test PUT/DELETE on the same GUIDs — write ops bypassing auth is far stronger than read-only.

**ASP.NET pattern (common root cause):** model binding/routing executes before `[Authorize]` for certain route shapes; invalid-format GUIDs (all zeros) fall through to a fallback route that IS guarded. Report as "authorization filter not applied to parameterized resource routes".

**Evidence discipline:** capture full curl with `-i` (headers) for every probe. Status-code table (endpoint × method × GUID type) is the core exhibit — build it in the report.

**Honesty rule:** auth bypass CONFIRMED ≠ data access CONFIRMED. Without valid resource GUIDs (needs a test account), data impact is [THEORETICAL]. Say so in the report — never inflate.

## 3. webapi-style backend enumeration

When program scope lists frontend hosts only, enumerate the backend the web client calls:
- Read JS bundles from the in-scope web app for `fetch`/XHR base URLs (`webapi.`, `api.`, `graph.` subdomains).
- Check for Swagger/OpenAPI on discovered hosts: `/swagger`, `/swagger/v1/swagger.json`, `/api-docs`, `/.well-known/openapi.json`.
- Swagger shows `[Authorize]`/lock icons per endpoint — endpoints WITHOUT the lock that return 404-not-401 on random GUIDs are prime suspects (see §2).
