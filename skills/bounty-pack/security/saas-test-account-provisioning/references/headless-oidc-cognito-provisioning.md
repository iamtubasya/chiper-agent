# Headless OIDC/Cognito provisioning: account + web session without a browser

Worked end-to-end on finanzen.net (2026-10-16): account created, confirmed, full web session
minted, cross-account IDOR harness running — zero browser (the stealth-browser tab-create was
timing out; this path never needed it). Use when the target is an SPA behind an OIDC provider
whose IdP is an AWS Cognito user pool and the signup/login form is not scriptable.

## 1. Map the flow from the app's own redirects (2 requests)

- `GET https://<app>/<register-or-login-path>` (full browser headers) -> `302` to
  `<idp-host>/extern-register?client_id=...&redirect_uri=...&scope=openid&state=<b64url>`.
- Decode `state` (base64url + padding -> JSON, e.g. `{"returnUrl": "...", "flag": false}`).
  It may be server-canonicalised on every hop: an attacker-supplied `returnUrl` was silently
  replaced with the default on re-issue — that is the open-redirect negative, not a bug.

## 2. Mine the SPA bundle for pool config and API contract

- Prod AND local-dev config objects sit in the main bundle: grep `userPoolId`,
  `userPoolWebClientId`, `oauth2ClientId`, `oAuth2Endpoints` -> region, pool id, app client id,
  and which host serves `authorize/token/authenticate/key/session` (dev/test hosts are usually
  embedded too — test only in-scope hosts, record the dev ones as observations, never as targets).
- Webpack5 runtime maps lazy chunks: `r.u=e=>e+"."+{<id>:"<hash>"}[e]+".js"` inside
  `runtime.<hash>.js` -> fetch every `<id>.<hash>.js` (28 files, seconds) and grep for the flows
  (`signUp`, `confirmRegistration`, `authenticate`, `recaptcha`, route table).

## 3. Cognito user-pool API calls need NO SigV4 for public-client ops

```
POST https://cognito-idp.<region>.amazonaws.com/
Content-Type: application/x-amz-json-1.1
X-Amz-Target: AWSCognitoIdentityProviderService.SignUp        (or ConfirmSignUp / InitiateAuth)
{"ClientId":"<32-hex>","Username":"<random-not-email>","Password":"<policy-strong>",
 "UserAttributes":[{"Name":"email","Value":"<you+tag@gmail.com>"}]}
```

- **Email-alias pools reject an email Username**: `InvalidParameterException: Username cannot be of
  email format, since user pool is configured for email alias` -> generate a random username
  (`fzfnz<hex>`), keep the email in `UserAttributes`.
- `USER_PASSWORD_AUTH flow not enabled for this client` -> the pool is SRP-only; do not fight it
  (see4b).
- Read the confirmation code from the operator's **Gmail plus-alias** via the Gmail API
  (refresh: `client_id`+`client_secret`+`refresh_token` grant to `token_uri`, then
  `messages?q=to:<alias> newer_than:1d`). Extract the code **by context**: the same mail carried a
  6-digit company-registry number (`HRB 740449`) that a naive `\d{6}` regex grabs as a decoy.

## 4a. Web session via the app's own BFF (preferred)

The frontend encrypts credentials before login:
1. `GET <idp>/api/oauth2/key` -> `{key: base64 SPKI, nonce}` (fresh key+nonce per attempt;
   replaying an old ciphertext is meaningless).
2. Plaintext is `{"username":email,"password":pw,"nonce":<nonce>}` — exact field names come from
   the bundle's class (e.g. `class vt{constructor(P,a,u){this.username=P;this.password=a;this.nonce=u}}`).
3. Encrypt **RSA-OAEP SHA-256**, base64 -> `POST <idp>/api/oauth2/authenticate?
   client_id&redirect_uri&scope&state` body `{"c": <b64>}`.
4. Response `{code, redirectUri, state}` -> `GET <app>/auth/oidc/callback?code&state`
   (`allow_redirects=False`) -> session cookies land (including a readable entitlement cookie —
   run an entitlement-trust differential on it).

Error-language map (saves retries): empty/invalid `state` param -> generic `Technischer Fehler`;
omitted `state` -> credential path (`Ungültige Zugangsdaten` / `Invalid credentials`); wrong
username form -> `Technischer Fehler`.

## 4b. SRP for token-level proof

`pip3 install --user --break-system-packages pycognito` (PEP668 on WSL), then
`Cognito(pool_id, client_id, username=email).authenticate(password)` — works with the email alias
even when `USER_PASSWORD_AUTH` is off. Use it to prove credentials independent of the BFF.

## 5. Wrap it in a reusable login helper

One module with `login(meta)` returning an authenticated `requests.Session` (state -> login page
-> encrypt -> authenticate -> callback; raise if the session cookie is absent) keeps every later
test at `s = login(A2)`. Build one per account and keep cookie jars strictly separate — that IS
the cross-account test harness.

## 6. Hygiene before closing the engagement

- Attempt self-deletion of the test accounts (Cognito `DeleteUser` with
  `Authorization: Bearer <access token>`). If the pool rejects every form (observed: `accessToken
  must not be null` / constraint errors even with a valid JWT in the header), **stop retrying and
  DISCLOSE**: accounts + usernames + passwords into `ENGAGEMENT_LOG.md` for vendor cleanup. The
  attempt plus the disclosure is the deliverable.
- Restore mutated own-account state where an endpoint exists (unfollow / rename back); where none
  exists (e.g. no entry-delete route), disclose the residue explicitly instead of leaving it implied.
- Log EVERY address used for signup — probing the email policy alone can create incidental
  accounts, and each is a state change on the target.

## 7. WSL artifact rule (cost two lost result sets here)

Save everything under `/mnt/c/...` from the first fetch: WSL stops between `wsl -e` calls and
`/tmp` is wiped on the next invocation. Pipe page output through `tr -d '\000' | grep -a` —
HTML bodies with NUL bytes otherwise make grep drop the entire stream.
