# AppSheet Security Audit Methodology

Extracted from `appsheet-security-audit` skill (archived 2026-09-03). AppSheet is a Google no-code SaaS platform — this is platform-specific audit methodology under the SaaS bounty hunting umbrella.

## Overview

Audit AppSheet apps for: user data leaks, database read/write via REST API, unauthorized access, misconfigurations. User typically provides an `https://www.appsheet.com/start/<APPID>?...` URL and asks "ada celah? leak data? edit database?" — respond in Bahasa Indonesia, findings table + verdict + next-step options.

## App Anatomy

- **App ID** = the GUID after `/start/` (e.g. `f2b1743c-a68a-4a51-b153-79d4a1887df5`)
- **Backend** = usually a Google Sheet (the real data store — permission there matters more than AppSheet itself)
- **REST API host** = `api.appsheet.com` (v1/v2). Web app host = `www.appsheet.com`. Region mirrors: `eu.appsheet.com`, `asia-southeast.appsheet.com`.
- `vss` param in URL = base64/gzip view state, NOT an exploit vector. Decoding reveals nothing sensitive.
- 404 responses that return ~29KB HTML SPA = the app's fallback page, not a real endpoint.

## Probe Sequence (No Auth Required)

1. **Anonymous access**: `GET https://www.appsheet.com/start/<APPID>?platform=desktop`
   - `302 → /Account/Login` = anonymous disabled (good). `200` = app is public — dig deeper.
2. **REST API enabled?** `GET https://api.appsheet.com/api/v2/apps/<APPID>/tables` with header `ApplicationAccessKey: <any>`
   - `400 "ApplicationAccessKey is missing"` → key required (expected)
   - `403 "API is not enabled for the called application"` → REST API DISABLED (good — biggest AppSheet attack surface is closed)
   - `200` → REST API ENABLED → try `POST .../tables/<table>/Action` with `{"Action":"Find","Properties":{...}}`, `Add`, `Update`, `Delete` — full CRUD if key valid.
3. **Key robustness**: try `ApplicationAccessKey: ""` / `0` / `null` / `anonymous` — all should be rejected.
4. **JS bundle leak**: fetch login page, grab `<script src="/assets/*.js">`, download, grep for `ApplicationAccessKey|accessKey|apiKey|clientSecret|password`. (AppSheet bundles are clean — this is a confirmation step, not a leak source.)
5. **Deployments**: `/install/<APPID>`, `/apps/<APPID>/install`, Play Store `appsheet.com.<APPID>`, `/templates/Preview?appId=<APPID>` — 404 = private/not published.
6. **robots.txt**: `/API`, `/api`, `/Account`, `/Manage`, `/App/*` disallowed (standard — confirms nothing).

## The REAL Risk Surface (Needs Authenticated Access)

AppSheet's public surface is normally locked. Actual leaks come from config, only checkable when logged in or given backend access:

1. **Security filters (row-level permissions)** — AppSheet's ONLY row protection. Default = every user sees ALL rows. A missing filter = any app user reads every report (names, locations, photos).
2. **Backend Google Sheet share settings** — "Anyone with link" = total bypass of AppSheet auth.
3. **Allowed login domains** — generic "Sign in with Google" means ANY Google account can request access; check Security → allowed emails/domains.
4. **Application Access Key** — static, rotates only manually. If REST API is enabled and the key leaked (code, chat, config), anyone gets full CRUD via API. No rate limiting by default.
5. **REST API enabled + weak/empty key** = instant database edit.

## Pitfalls

- Use `User-Agent: Mozilla/5.0` on ALL requests (AppSheet drops/404s bare curl).
- Large batched curl loops → terminal stream timeout. Write a small probe script or split into small calls.
- Don't assume REST API endpoints exist beyond `/api/v2/apps/<id>/tables` and `/tables/<name>/Action` — everything else 404s.
- `api.appsheet.com/api/v2/apps/<id>/tables/Cleanliness/rows` returns 405 (method not allowed) — row CRUD goes through the Action endpoint only.

## Worked Example

See `references/cleanliness-report-app-audit.md` — Kebersihan Sumatra CleanlinessReportApp audit (app ID, findings, verdict).
