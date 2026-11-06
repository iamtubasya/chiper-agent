# Blink / Galoy — email-only VDP + post-mortem-driven hunting (2026-10)

Target: `blink.sv` (Blink Technologies LLC — custodial Lightning wallet + non-custodial Spark wallet,
built on the open-source **Galoy** platform). Corporate/CI/chat domain: `blinkbtc.com`.

## 1. The policy shape — read it before you plan the session

`https://blink.sv/.well-known/security.txt` → `Policy: https://blink.sv/bounty-terms`. The page holds
**two separate programmes**, and conflating them wastes a session:

| Programme | Channel | Reward |
|---|---|---|
| **Recovery bounty** | `bounty@blinkbtc.com`, subject `[BOUNTY]` | 50% of recovered stolen BTC (25% informant / 25% charity). 6.61085425 BTC stolen 19 Sep 2026. Blockchain-tracing work, not app testing. |
| **Security disclosure channel** | `bounty@blinkbtc.com` (PGP: `blink.sv/.well-known/pgp-key.txt`) | discretionary **up to 0.1 BTC** for critical; smaller for lower; public credit on request. Assessed monthly, paid once fixed. |

No platform (no H1/Bugcrowd/Intigriti), no scope table, no OOS list — scope is the prose phrase
"Blink's software or services". Governing law: Próspera ZEDE; arbitration at the Próspera Arbitration Center.

**Safe-harbour clauses that constrain the method (quote them in the report):** report privately; do not
access/move/keep customer funds or data beyond what is needed to demonstrate, and delete data once
reported; do not degrade services or test against other customers' accounts; reasonable fix time before
publication; only the **first report of an issue Blink did not already know about** is rewarded.

## 2. Post-mortem-driven hunting (the highest-yield method here)

The vendor published a full post-mortem of the 19 Sep 2026 incident (`/blog/sept-19-attack-postmortem-and-bounty`)
naming the exact class, the three layers, and the **fix PR numbers**. That converts the engagement from
"scan and hope" into "verify a named control still holds, then hunt the same class one layer over".

Read it, then map every claim to a test:
- claim "the consent page now rejects any permission the app didn't ask for" → test the consent grant path
- claim "admin tokens must carry an audience issued only for the admin API" → test audience enforcement
- claim "admin API and admin panel taken off the public internet (VPN-only)" → test whether they are

Also note: version/date of the fix matters. The public repo `GaloyMoney/galoy` you clone may **predate**
the fix the vendor claims to have deployed — the deploy may be a private fork. Treat repo code as
*architecture evidence* and the live deployment as ground truth.

## 3. Architecture map (white-box, `git clone --depth 1 https://github.com/GaloyMoney/galoy`)

| Component | Role | Public host |
|---|---|---|
| **Ory Hydra** | OAuth2 server | `oauth.blink.sv` / `oauth.staging.blink.sv` (`/.well-known/openid-configuration` → 200) |
| **Ory Oathkeeper** | gatekeeper in front of GraphQL + admin API | internal; rules in `dev/config/ory/oathkeeper_rules.yaml` |
| **Ory Kratos** | identity server (sessions) | internal |
| `apps/consent` | the consent screen (Next.js) | `consent.blink.sv`, `consent.staging.blink.sv`, `consent.mainnet.blink.sv` |
| `core/api` | main GraphQL API (introspection **enabled**) | `api.blink.sv`, `api.staging.blink.sv` |
| `apps/dashboard`, `admin-panel`, `pay`, `voucher`, `map` | NextAuth apps wired to Hydra | `dashboard/pay/voucher/map.blink.sv` |
| `apps/voucher` | gift-card ("WithdrawLinks") service, Postgres | `voucher.staging.blink.sv` (prod `voucher.blink.sv` was unreachable) |

**Files that carry the 19-Sep bug** (`apps/consent/app/consent/page.tsx`):
`submitForm()` → `const grantScope = form.getAll("grant_scope")` → `acceptOAuth2ConsentRequest({ grant_scope: grantScope, grant_access_token_audience: body.requested_access_token_audience })`.
`grant_scope` comes from the **form**; the audience comes from Hydra (safe). The scope list is never
checked against `body.requested_scope`. The checkbox is
`apps/consent/components/scope-item/scope-item.tsx` → `name="grant_scope" value={scope}`.

**Layer 2 file** (`dev/config/ory/oathkeeper_rules.yaml`) — the `admin-backend` rule ships with the
TODO literally in the file, which is what PR #855 closed:
```yaml
    - handler: id_token
      config: #! TODO: add aud: {"aud": ["https://api/admin/graphql"] }
        claims: '{"sub": "{{ print .Subject }}", "scope": "{{ print .Extra.scope }}" }'
```
plus `authenticators: [cookie_session, oauth2_introspection]` and `authorizer: {handler: allow}`.
Introspection confirms the token is *live* — it is not an audience check, and `Extra.scope` is the
token's own claim.

## 4. Verified controls (tested live — negative results, all correct)

Recorded so the next session does not re-run them:

1. `/oauth2/auth` with `scope=read write admin` / `admin` / `receive` / `openid` / `bogus_scope` →
   `error=invalid_scope` (`"The OAuth 2.0 Client is not allowed to request scope 'x'"`). The
   "obvious route" is closed.
2. `redirect_uri` strict: `evil.example`, sibling-suffix `dashboard.blink.sv.evil.com`, traversal,
   `http://localhost:3000/cb` → all `error=invalid_request`.
3. GraphQL unauth: `me`, `authorization`, `custodialRestrictions`, `migration`, `windDown` → "Not authorized".
4. `admin-api.blink.sv` is nginx-fronted, reachable (`/healthz` 200, empty body) but **no routed
   path** — `/graphql`, `/admin/graphql`, `/metrics`, `/openapi.json` all 404. Not usable.
5. Next.js 14.2.26 across `apps/*` → CVE-2025-29927 middleware bypass tested with
   `x-middleware-subrequest` on dashboard/pay/admin-card/kyc → no bypass.
6. Hydra DCR (`POST /oauth2/register`) → "Dynamic registration is not enabled."
7. Matrix (`matrix.chat.blinkbtc.com`) registration disabled; only `m.login.application_service`.
8. `consent.blink.sv/consent?consent_challenge=…` → `Cache-Control: private, no-cache, no-store`
   (the 1-year `s-maxage` seen on `/` is the static shell, not the consent path — no cache poisoning).
9. `captchaRequestAuthCode` without a valid captcha → "Captcha validation failed."
10. `client_credentials` without a secret → `invalid_client`.

**Public by design — do NOT report:** `accountDefaultWallet(username:X)` unauth returns the wallet id
(ln-address resolution), `usernameAvailable(username:X)` (username-picker UI), `globals`,
`mobileVersions`, `payoutSpeeds`, `currencyList`, `businessMapMarkers`.

## 5. Candidate findings (honest severities)

- **Mattermost `chat.blink.sv` open self-registration.** `GET /api/v4/config/client?format=old` →
  `EnableOpenServer=true`, `EnableUserCreation=true`, `EnableSignUpWithEmail=true`, `NoAccounts=false`,
  MFA off, `SupportEmail=kemal@blinkbtc.com`, v11.6.1. The host is **not linked anywhere on the public
  site** → internal instance. All data APIs (`/api/v4/teams`, `/channels`, `/users/me`) answer 401, so
  impact is gated by team-join policy — say so. Medium.
- **Voucher secret uses `Math.random()`.** `apps/voucher/utils/helpers.ts:99 generateCode()` is
  `Math.floor(Math.random()*len)` (V8 xorshift128+, not a CSPRNG) and
  `services/db/index.ts:116` mints the bearer `voucherSecret = generateCode(12)`. `getWithdrawLink`
  (`graphql/resolvers/query/get-withdraw-link.ts`) has **no session check** and live
  `POST https://voucher.staging.blink.sv/api/graphql` answered 200 for 5 rapid probes (no rate limit
  observed). 12 chars over a 56-symbol alphabet (~9.6e20) makes blind brute force infeasible — the
  finding is the non-CSPRNG, and PRNG-state recovery needs consecutive outputs. Do not claim a
  demonstrated theft. Medium.
- **Concourse 8.3.0 at `ci.blinkbtc.com`** (`ci.blink.sv` 301s there). `/api/v1/info` leaks
  `external_url`; `/api/v1/workers`, `/user` → 401; `/pipelines`, `/teams` → 200 `[]`. Informational.

## 6. The blocker, and how to report it

**Authenticated testing is gated by identity, not by tooling.** Registration is
**phone number + SMS OTP** (`userLogin {phone, code}`; `captchaRequestAuthCode` is captcha-gated).
There is no email-only signup, no testnet API (`api.testnet/sandbox/dev.blink.sv` → NXDOMAIN), and DCR
is off. Email login exists on the consent app **only for already-registered accounts**.

Do **not** fall back to curl-only or declare the target clean. Deliver the unauth coverage as a
ledger, then name exactly what the account would unlock (consent `grant_scope` validation — the
incident's own class — GraphQL BOLA/IDOR across accounts, api-keys, pay/fiat flows) and ask the
operator for one phone number. That is the one legitimate blocking question in an engagement.

Related: 0.1 BTC-class rewards here came from an **authorization** bug, not a scanner hit. Budget the
session for white-box reading of the auth stack, not for template volume.
