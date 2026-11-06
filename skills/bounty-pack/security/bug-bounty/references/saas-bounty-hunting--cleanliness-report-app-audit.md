# Worked example: CleanlinessReportApp (Kebersihan Sumatra) — 2026-08-19

Target: `https://www.appsheet.com/start/f2b1743c-a68a-4a51-b153-79d4a1887df5?platform=desktop#appName=CleanlinessReportApp-619142847&view=Cleanliness_Detail`

User context: this is the Kebersihan Sumatra reporting app (user monitors it actively; reports include names, locations, photos). Question: "ada celah keamanan, spt leak data user, atau edit database?"

## Verdict
**No exploitable public surface.** Anonymous access OFF, REST API DISABLED, no data endpoints, no APK, app private (not a template/gallery). JS bundles clean. Residual risk is all internal config requiring authenticated access.

## Findings detail

| Surface | Probe | Result |
|---|---|---|
| Anonymous start | GET /start/<id>?platform=desktop | 302 → /Account/Login (locked) |
| REST API enabled? | GET api.appsheet.com/api/v2/apps/<id>/tables, hdr ApplicationAccessKey: 0 | 403 "API is not enabled for the called application" → DISABLED |
| AccessKey missing | GET same, no header | 400 "ApplicationAccessKey is missing" |
| Action endpoint | POST api.appsheet.com/api/v2/apps/<id>/tables/Cleanliness/Action | 400 missing key (same gate) |
| Rows endpoint | GET .../tables/Cleanliness/rows | 405 (CRUD only via Action endpoint) |
| All other /api/v2/apps/<id>/* paths | /action /versions /appsettings /properties /security /users /databases /model /schema /settings | 404 SPA fallback |
| Templates/gallery | /templates/CleanlinessReportApp, /templates/Preview?appId= | "App not found" → private |
| Mobile install | /install/<id>, /apps/<id>/install, Play Store appsheet.com.<id> | 404 |
| JS bundles | /assets/<hash>.js (6 files from login page) | No keys/secrets (only Google Maps API_KEY_* error codes, URL parser code) |
| robots.txt | www + api | Standard: /API /api /Account /Manage /App/* disallowed |

## Key interpretation notes
- `403 API is not enabled` ≠ `403 wrong key`. It specifically means the app owner never enabled the REST API — the #1 attack vector (full CRUD via ApplicationAccessKey) is closed by default.
- The ~29KB `<!doctype html>` SPA fallback on 404 = AppSheet's own error page. Not a real endpoint.
- Region hosts eu/asia-southeast mirror the same API and return identical results — one host probe suffices.

## Recommendations given to user (hardening checklist)
1. Verify backend Google Sheet NOT shared "Anyone with link" (that bypasses AppSheet auth entirely).
2. Verify Security Filters set per user/role — AppSheet's only row-level protection; default shows ALL rows to any app user.
3. If REST API ever enabled: rotate ApplicationAccessKey, keep it out of client code/chat, expect no rate limiting.
4. Consider restricting allowed Google accounts to an org domain instead of generic sign-in.
