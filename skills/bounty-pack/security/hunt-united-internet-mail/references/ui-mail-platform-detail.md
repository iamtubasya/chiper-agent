# United Internet mail platform — session detail (2026-10-24/25 engagement)

Detail behind `hunt-united-internet-mail`. Everything here was observed live against
mail.com / GMX / WEB.DE from egress 104.28.226.245 (Cloudflare WARP, Medan ID).

## Host inventory (subfinder -all, 154 subs; 64 live via httpx)

In-scope priority set used for scanning:

```
navigator-lxa.mail.com, addressbook.navigator-lxa.mail.com, oauthbridge.navigator-lxa.mail.com,
trackbar.navigator-lxa.mail.com, cats.navigator-lxa.mail.com, epimetheus.navigator-lxa.mail.com,
interception-lxa.mail.com, lps.navigator-lxa.mail.com, account.mail.com, account-lxa.mail.com,
ciss.mail.com, myaccount.mail.com, calendar.mail.com, caldav.mail.com, organizer-us.mail.com,
cloud.mail.com, storage-us.mail.com, storage-eu.mail.com, storage-file-us.mail.com,
storage-file-eu.mail.com, login.mail.com, password.mail.com, oauth2.mail.com, auth.mail.com,
mlogin.mail.com, shop.mail.com, attachment-download.mail.com, register-suggest.mail.com,
register-service.mail.com, postmaster.mail.com, forwarding.mail.com, mailcheck.mail.com,
permissions.mail.com
```

Notable non-resolving (67 total, no dangling CNAME → no takeover):
navigator/webmail/app/api/premium.mail.com, plus most `*-pre-*` / `*-qa` internals.
`ooeditor.mail.com` CNAMEs to `ept-p-us.gmx.net` (live service, not claimable).

## Key request/response transcripts

### Login (login.mail.com/login, UAS)

POST form fields: `service=ciss`, `statistics=<encrypted blob>`, `username`,
`password`, `successURL`, `loginFailedURL`, `loginErrorURL`. A stale `statistics`
blob copied from another page still processes — the blob is not session-bound.
Responses: bad creds → 303 to loginFailedURL (`?status=login-failed`), generic
"Log in was not successful", identical for existing vs non-existing users, timing
~1.6 s both ways. No enumeration.

### Password recovery (password.mail.com, Wicket)

1. `GET /passwordrecovery/` → 302 `?srttkn=<uuid>` + JSESSIONID (path-scoped).
2. `GET /wicket/page?1&srttkn=<uuid>` → form; hidden `srttkn` must equal the URL token.
3. POST `./page?1-1.-recoveryAuthorizeForm&srttkn=<uuid>` with
   `accountIdentContainer:accountIdentInput=<email>`.
4. `GET /wicket/page?2&srttkn=<new-uuid>` → error state ("Verification
   unsuccessful") or clean form.

Tokens are session-bound: a page-2 token replayed from another session → 401.
Host header is not reflected anywhere in the flow.

### OAuth (oauth2.gmx.net / oauth2.mail.com)

- `authorize` is functional on both brands; with an invalid client_id it 303s to
  `support.mail.com/account/login/still-no-login.html?error=invalid_client&…&state=<echoed>`.
  The state param is echoed in the URL but NOT rendered into the target page (no XSS).
- Token endpoint grant behaviour for `gmxnet_connect_live` (secret leaked on
  connect.gmx.net):
  - authorization_code + valid secret → `invalid_grant` (client authenticated)
  - authorization_code + wrong secret → `invalid_client`
  - client_credentials / password / refresh_token / shared_login_cookie → `invalid_client`
    (per-grant client authorization enforced)
- `um-data-facade.<brand>/.well-known/oauth-protected-resource` is exposed (standard
  OAuth metadata, not a finding).

### register-service (flexreg)

Full endpoint table in SKILL.md §3. Cookies: `reg-flow-data0` / `reg-flow-data1`
(encrypted — base64 decode yields binary, not JSON), `chunks-flow-data`. Random
registrationFlowId + valid cookie → `cookie-validation-error`. After sustained
probing, `/aliases` → 401 `urn:problem:mam:flexreg:denial-error`.

### Anti-automation timeline (same IP, all brands)

- ~10 registration starts → wizard bails to `hilfe.<brand>.net/kundenservice/flexreg.html`.
- One wizard load succeeded again ~35 min later; the next start blocked again.
- Pattern: ~1 usable flow per 30–60 min. Validation loops must sleep ~20 min between
  attempts and treat "blocked" as expected, not as a finding change.

## Evidence layout used

```
D:/data hermes/mail-com-audit/
  recon/      subfinder_mailcom.txt, live.txt, gau_mailcom.txt, katana_inscope.txt,
              nuclei_focused.txt, ffuf_sensitive.txt, inscope_hosts.txt, recon_summary.md
  evidence/   finding1_oauth_client_secret.txt, finding2_alias_enumeration.txt,
              finding3_xapphost_disclosure.txt, finding4_jsessionid_url.txt
  reports/    finding1_oauth_client_secret.md + .pdf, finding2_alias_enumeration.md,
              body_F1.txt
  stage_draft_imap.py   IMAP draft stager (see reportlab-security-pdf reference)
```

## Delivered vs pending (this session)

- F1 OAuth client-secret exposure: validated 3x, PDF (4 pp, layout problems=0),
  Gmail draft staged to report@bugbounty.mail.com (NOT sent).
- F2 alias enumeration: 1 clean run (5/5 correct); 3x validation blocked by
  anti-automation, retry loop running.
- Authenticated-area testing (attachment-download IDOR pattern, webmail, calendar,
  cloud, Premium entitlement): blocked on test-account creation (geo-block + mTAN).
