# Mobile / APK attack surface — United Internet mail platform (verified 2026-10-25)

Companion to the web-surface map in SKILL.md §1. Source: mail.com Android APK
`com.mail.mobile.android.mail` v7.51.2 (52 MB, from APKMirror — see skill
`apk-redteam-pipeline` for the download flow and the androguard / resources.arsc /
source-map toolchain notes).

## Live endpoints discovered from the APK

| Endpoint | Status | Notes |
|---|---|---|
| `POST https://brand-resolver.mail.com/resolution` | **LIVE** | Body `{"username":"<email>"}` → `{"brand":"mailcom"\|"gmxnet"\|"webde"}`. Strict: only exact brand domains (case-insensitive); subdomains, trailing space, null byte, non-UI domains → 400/empty. No injection, no enumeration value (maps domain→brand, not account existence). Requires `Origin: https://auth.mail.com` (else 403 "Invalid CORS request"). |
| `https://auth.mail.com/loginapp` | **LIVE** | React SPA — the mobile side of the "WebSignIn" flow (desktop login approved on phone). Full source map at `/assets/login-app.js.map` (90 TypeScript sources). |
| `https://storage-file-us.mail.com/restfs/guest/{ownerId}/share/{shareHash}/{resourceId}` | 401 Basic (realm "Online Storage") at edge | **Prime IDOR candidate once authenticated** — public cloud-share access pattern. Also `/children`, `/children?conflictResolution=rename`, `/children/move` variants. |
| `https://lts.mail.com/logintokenserver-1.1/Logintoken` | dead (000) | Same path family on lts.gmx.net / lts.web.de / lts.1und1.de / lts.gmx.com — all unreachable. |
| `https://cocos-lookup.mail.com/context-configuration-lookup/rest` | 404 | Context-configuration service; needs specific paths/params not in the APK. |
| `lcloud.mail.com`, `bigfile.mail.com`, `xps.uimserv.net` | dead (000) | Legacy hosts from wayback data; do not re-probe. |

## Login-app API map (from the source map, `authentication-fe` 2.2.34)

Server-injected config (inline `<script>` JSON in the loginapp HTML) carries
`brandResolverApiUrl`, `loginService{serviceId, serviceUrl, successUrl, errorUrl,
failureUrl}` and `navigateBackToAppUrl` — the mobile app deep link
`com.mail.androidmail.redirect://authorization_code_grant/close` confirms an **OAuth
authorization-code grant** mobile flow. Endpoint constants (relative to the injected
serviceUrl):

- `identification` (email → brand/session)
- `captchafox-verification` / `recaptcha-verification`
- `authentication/password`, `authentication/token`
- `authentication/webauthn-start` / `authentication/webauthn-finish` (both take a `sessionId`)
- `rest/webauthn/registrations`

Standalone page load errors client-side ("An error occurred") without deep-link params —
drive it from the mobile app flow or with the injected config, not bare.

## Secrets / headers found in the APK (test before claiming impact)

- `X-UI-API-KEY` values: `0-MAMOSANDROID-16373-0-b65ee68d84515224` (cloud_restfs_api_key),
  `0-ANDROIDPHOTOBACKUP-16997-0-3bdfb16ec7a23d3f` (restfs_auto_backup_api_key).
  Companion headers: `X-UI-APP`, `X-UI-Share-Authorization`, `X-UI-CLIENTID`,
  `X-UI-APPINSTALLID`. **These do NOT bypass the Basic-auth edge on storage hosts** —
  tested, still 401. Only report if a live bypass is demonstrated.
- Sentry DSN in public JS: `480ae9a110338dc4a58a338a8978e920@trace-proxy.mam.dev/04/157`.
- 7 internal JIRA refs in public JS (jira.mam.dev): UMX-1348, UMX-979, UMX-3359,
  UMFE-381, UMFE-295, UMFE-17, UMX-873 — informational, auto-close material.
- Firebase/GAE backend: `deeuemobileandroid-da26c.appspot.com`.

## RestFS API shape (from DEX class names, for the authenticated phase)

Operations: CreateContainer/CreateSingleFile/CreateShare/Copy/Move/Trash/EmptyTrash/
FileSearch/Shares/UpdateShare + phototimeline (GetPhotoTimeline, GeoSearch) +
`UserinfoOperation`. Content types: `application/vnd.ui.restfs.multifacetquery+json`,
`application/vnd.ui.restfs.searchresult-v2+json`. Endpoint base is resolved at runtime by
`RestFsEndPointResolver` (no hardcoded URL) — get it from an authenticated session, then
test the guest-share pattern for shareHash guessing and ownerId/resourceId swapping.
