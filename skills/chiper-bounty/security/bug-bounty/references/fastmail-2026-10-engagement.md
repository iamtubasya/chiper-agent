# Fastmail Engagement 2026-10 — session reference

Target: fastmail.com (email/calendar SaaS). Program: self-hosted, $100 min–$5,000 max, discretionary.
Policy: https://www.fastmail.com/bug-bounty/ — test accounts OK, own accounts only, first reporter.
Valid: auth/session, XSS (*.fastmail.com ONLY — user.fm + fastmailusercontent.com explicitly OOS),
CSRF, RCE, privesc. OOS: email spoofing, CSV macro, DoS, social eng, brute force, username enum,
version leaks, bugs on non-Fastmail-run sites (fastmailfbl.com).

Hall of fame (paid classes, use as hunt map):
- OAuth redirect URI verification bypass ($2000)
- Calendar ACL checks ($3750) · CSS sanitisation bypass ($2000/$3500)
- Sensitive-action reauthentication bypass ($200) · External link protection bypass ($100)
- Internal metrics leak ($200) · Email auth/identity verification bypass ($400/$200)
- Android app credentials ($2000) · Trial abuse prevention bypass ($100)

## Surface (533 subfinder subs = 529 WILDCARD artifacts → 103.168.172.37/52; real clusters):
- api.fastmail.com (.38/.53) · app.fastmail.com (.39/.54) · DAV .46/.61 · imap .43/.58 · pop .44/.59 · smtp .45/.60
- non-prod each own IP: beta .96, qa .72, dogfood .116, api.beta .84, api.qa .69, api.dogfood .104
- Regional auth: phl.api (= api IP), ams.api (204.75.18.38 EU). Only these 2 resolve.
- support/wiki = custom help center on the SAME app stack (not Zendesk API)
- user.fm dir listings (public/dl.dmpop/mikebelanger...) = OOS domain
- myfiles/webdav/upload = Basic+Bearer file storage (PROPFIND 401 unauth)

## Signup API (api.fastmail.com/signup/api) — needs header `x-trustedclient: Yes`
JMAP-style: methodCalls = [name, args, callId] (3 elements). Methods:
- Signup/getEmailAvailability {email} → {isAvailable, reservationToken} (by design; enum OOS)
- Signup/getDiscount {talon?} → {percent} (talon optional)
- Signup/createAccount {serviceLevelName,name,username(FULL email),password,dataRegion(CLIENT "us"/"eu"),verificationId,verificationCode}
  → error types prove server-side SMS validation: needsVerification{countryCode}, notFound, expired, inUse, incorrectCode, rateLimited(rl3)
- Signup/sendVerificationSMS → needsCaptcha
- Geo-gate: IP Indonesia → needsVerification{countryCode:"ID"} = mandatory phone SMS. VERIFIED server-side
  (origin-direct hit still returns ID; NOT a CF header) → no header-spoof bypass. WARP exit also ID.

## OAuth (api.fastmail.com)
- Metadata: /.well-known/oauth-authorization-server + openid-configuration (open)
- DCR /oauth/register OPEN: accepts ONLY http://localhost|127.0.0.1 redirects (all https rejected);
  NORMALIZES (strips port, 127.0.0.1→localhost). Test client registered: 93a641ae (no creds issued).
- /oauth/authorize passes ANY redirect_uri (even evil.example.com) through to app.fastmail.com/oauth/
  → validation happens INSIDE the authenticated flow (untestable without account)
- PKCE S256, public clients (auth method "none"), scopes: mail/contacts/calendars/MCP/openid/offline_access
- token endpoint = /oauth/refresh; revocation = /oauth/revoke

## Login state machine (api.fastmail.com/auth/login)
start {type:start} → loginId + methods[passkey(rpId fastmail.com),username] + nextUrl(phl.api)
username {type,username,loginId} → methods[username,password,passkey] + nextUrl(ams.api)
- invalid/short loginId → 410 Gone {loginId:null}; missing fields → 400 Malformed; step sequence enforced
  (password without username → 400); replay of same step idempotent. NO state bypass found.

## App white-box (SPA, JMAP UI)
- Version: 64274585b7-b51ce62cfcb133b9; modules at /static/jmapui/{ver}/app/module/desktop/{Module}.mod.js
- Bootstrap module map at .../bootstrap/bootstrap.js reveals ALL logical paths
- Key modules (map to paid bug classes): OAuthToken, sudo (reauth modal), Passkey, TOTP,
  LoginYubicoOTPView, SecurityKeyInputView, defangHTML + rewriteInternalLink (external link protection),
  SignupView, PhoneVerifyView
- proxyWorker.js (182KB, SSE+IndexedDB offline) leaks FULL JMAP data model: ApiToken,
  ApplicationPassword, ExternalCredential, Identity, LoggedInSession, MaskedEmail, MailExport,
  MboxImport, BackupContactDetail, Billing* — these are the authenticated-phase IDOR targets
- robots.txt reveals routes: /sievetester/ /recover/ /login/ /signup/ (all JS/auth-gated)

## CORS: api.fastmail.com/jmap/session REFLECTS any Origin in ACAO BUT no Allow-Credentials +
Bearer-only auth = NON-EXPLOITABLE (documented negative). Exposes Mcp-Session-Id header (MCP at
api.fastmail.com/mcp, 401 auth-gated).

## Blocker (unchanged class): account creation geo-gated (ID → SMS). Everything high-value
(JMAP data model IDOR, OAuth consent, sievetester, MCP, reauth/sudo) needs an account.
Needs: SMS-capable number OR non-ID egress IP.
