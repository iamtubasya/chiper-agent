# United Internet mail platform (mail.com / GMX / WEB.DE) — recon + API map

Measured 2026-10-24/25 during the mail.com bug bounty engagement. The three brands are
ONE product per program rules (policy: bugbounty.mail.com, report: report@bugbounty.mail.com).

## Scope reminder
- In scope: authenticated web apps processing customer data (email, calendar, file
  storage) + authentication systems. Everything else accepted but unrewarded.
- OOS examples: product features, spam/malware, non-exploitable (missing headers, info
  leakage), self-XSS, availability (logout CSRF).

## Host map (production)
- Webmail SPA: navigator-lxa.mail.com (mailint 1.484.0 on s.uicdn.com); siblings:
  addressbook / oauthbridge / trackbar / cats / epimetheus / interception / lps
- Account mgmt: account.mail.com (+ -lxa, -ba, ciss.mail.com, myaccount) — Apache Wicket
  app "ciss" 1.16.132, path /ciss/login, JSESSIONID leaked in redirect URL
- Calendar: calendar.mail.com (nginx; EVERY path returns 200 "OK" 2 bytes = health
  endpoint, not the app)
- Storage: storage-{us,eu}.mail.com, storage-file-{us,eu}.mail.com (Basic realm
  "Online Storage"), attachment-download.mail.com (OAuth Bearer; URL pattern
  /mailbox/primary/Mail/{uuid}/{ts}/Attachment/{id} — IDOR candidate WITH token)
- Auth: login.mail.com/login (UAS POST form, encrypted `statistics` blob),
  password.mail.com/passwordrecovery (Wicket, session-bound srttkn),
  oauth2.mail.com (OAuth2; /authorize functional), auth.mail.com (403 JSON)
- Registration: signup.mail.com (geo-blocked at edge for non-allowed countries),
  register-service.mail.com (404 on /config), register-suggest.mail.com/rest/email-alias/availability
  (403 edge)
- Edge: "platform-mesh" (k8s); leaks X-App-Dc / X-App-Host (pod name) headers

## Shared registration backend (flexreg 2.14.1) — GMX/WEB.DE reachable, mail.com geo-blocked
- Wizard: register.gmx.net / register.web.de (Astro SPA + CaptchaFox smart checkbox —
  single dispatch_event click usually solves it)
- API: register-service.gmx.net (and .web.de)
  - GET  /config?product=gmxnetFree&defaultCountryCode=DE -> registrationFlowId + mTan policy
  - POST /captcha-verification  (sets binding cookies reg-flow-data0/1, chunks-flow-data)
  - POST /personal-info         (ct: application/vnd.ui.mam.flexreg.user.personalinfo-v1+json)
  - POST /aliases               (ct: ...alias.suggestioninput-v2+json) — availability oracle
  - POST /alias-selection, /address-details, /password-check, then mTan (SMS, 6 digits,
    3 attempts, 60s cooldown)
  - All need header `x-ui-app: flexreg/2.14.1` + cookies bound to the flow (encrypted,
    NOT forgeable; random flow id -> 401 cookie-validation-error)
- Registration needs mTAN SMS -> no test account without a phone number
- Anti-automation: after N test registrations the wizard bails to
  hilfe.<brand>.net/kundenservice/flexreg.html and /aliases answers 401 denial-error.
  Cooldown ~30-60 min, ONE flow per window. Bypass the UI bail-out with
  `page.route('**hilfe.gmx.net**', abort)` (see geo-block-proxy-ops §8).

## OAuth one-connector (public credential exposure)
- connect.gmx.net/entry embeds data-clientid + data-clientsecret in HTML
  (gmxnet_connect_live). connect.mail.com / connect.web.de do NOT exist (NXDOMAIN).
- The secret is live: oauth2.gmx.net/token with grant_type=authorization_code +
  the leaked secret -> invalid_grant (client authenticated); wrong secret ->
  invalid_client. client_credentials / password / refresh_token -> invalid_client
  (grant not allowed for this client).
- oauth2.mail.com/authorize is functional (invalid_client redirect for bad client_id);
  state param is NOT reflected into the landing page.

## Findings delivered from this platform (2026-10-25)
- F1: OAuth client secret in public HTML (validated 3x, Low)
- F2: account enumeration via /aliases available:true/false (3 runs, 17/17 checks, Low)

## Negative results (don't re-test)
- Login: no user enumeration (generic error, uniform ~1.2-1.7s), no SQLi (SLEEP(5)
  payload no timing delta), statistics blob encrypted
- Recovery: srttkn session-bound; no host-header reflection; enumeration inconclusive
- CORS no reflection; no GraphQL; TRACE 405; no subdomain takeover (67 NXDOMAIN subs,
  no dangling CNAME); search.mail.com reflections all encoded; ciss status param not
  reflected; sensitive-files sweep clean (only robots.txt/security.txt; /_debug is a
  stock Apache 403 page, not a debug endpoint)
