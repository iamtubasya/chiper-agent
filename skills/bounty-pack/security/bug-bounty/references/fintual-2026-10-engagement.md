# Fintual (CL/MX) — 2026-10 engagement notes

Self-run email-only bug bounty. `security@fintual.com`, PGP at
`fintual.com/pgp-key.txt`. Policy: `fintual.com/security-policy.txt`.
Bounty $100→$10k+ by business impact (not CVSS). Report in English, email
only. Dedup baseline = `fintual.com/hall-of-fame.txt` (53 entries 2019-2025).

## Scope
- IN: `fintual.cl .mx .com .in`, `fintu.al`, `fnt.al` + their services.
- OUT: `fintualist.com`, `store.fintual.cl`. No social eng, no DDoS, own
  accounts only, no data modify/delete. Explicitly NOT rewarded: rate-limit
  on non-sensitive endpoints, best-practice, race w/o security compromise,
  scanner output w/o explanation, cookie flags, missing headers, TLS ciphers
  w/o PoC, open ports, robots.txt-type, DNSSEC/DANE, HSTS/CSP, host-header
  w/o 3rd-party path, **Firebase apiKey (public by design)**, DMARC/BIMI.

## Architecture (verified 2026-10)
- **CL**: Next.js marketing at `/f/` (Vercel+CF); **Rails monolith** is the
  real app: JSONAPI `/api/*` (`me`, `goals`, `banks`), GraphQL **`/gql/`**
  (Apollo `uri:"/gql/"`), Rails view packs under `/app/*`. `/graphql` and
  `/api/graphql` are dead (403 WAF / 404). `api.fintual.cl/.mx` = 403 from
  this egress (unreachable, WAF).
- **Auth**: `POST /auth/sessions/initiate_login {email,password}` → emailed
  6-digit code → `POST /auth/sessions/finalize_login_web {email,password,
  code,after_sign_in_path}` → `monolith_token` RS256 JWT cookie (kid
  `_VOfSTIugek`, issuer `auth.fintual.com`, **TTL 300 s**), +
  `auth_refresh_token`, `uid` (=user id, unsigned), `email` cookie.
- **MX signup differs**: single-shot `POST /onboarding-mx/api/signup/web
  {email,password,first_name,last_name,telephone,referrer_code,partnership}`
  — NO verify_email step (CL is lead→verify_email→convert_web). MX GraphQL
  is the same `/gql/` on `fintual.mx`.
- `POST /auth/jwt {aud}` mints per-service JWT cookies. Server allowlist =
  `stocks-broker-mx` only (others → `aud_not_found`). Its consumer URL is a
  build-time env (`NEXT_PUBLIC_STOCKS_BROKER_MX_URL`) NOT inlined in the
  served build; no same-origin path consumes the cookie → minting is
  likely by-design. Cookie is path-scoped `/stocks-broker`.
- 6 apex zones all on Cloudflare NS. `*.fintual.in` internal hosts = 403
  "Necesitas VPN" (Cloudflare Access). `storybook-web/mobile.fintual.in` =
  public Storybook design system (97/96 titles, no secrets). `id.fintual.com`
  = Okta custom domain. `*.pr-NNNN.fnt.al` = Vercel PR previews, **all
  DNS-dead** (5637 historical CT entries). `links.fintu.al`/`lnks.fnt.al` =
  Rebrandly (third-party, no Fintual short links referenced besides
  `fintu.al/hola`).

## Business logic map (money surface)
CL GraphQL: 95 mutations / 128 ID-arg resolvers (Goals*, ApvA/B/Dc*,
Company*, Group*, CustomAllocated*, Stocks*, Pacs*, TrxCl*, Forex*,
CreateUserClBankAccount, RegisterAmount/FullUnrestrictedWithdrawal).
MX GraphQL: 88 ops / 21 ID-arg resolvers (GoalsMx*, ReserveMx*, PprMx*,
dollars). Key money movers: `reserveMxRequestWithdrawal`,
`goalsMxRequestWithdrawal`, `pprRequestWithdrawal` (all take
`userBankId:ID!` + geolocation `{latitude:String!,longitude:String!,
accuracy:...}` + `pin`). Entitlement state lives in `/api/me` attrs
(`can_invest`, `has_deposited`, `restricted`, `risk_profile`...).

## Verified controls (skip re-testing)
- JWT forgery battery all rejected (alg:none, HS256 key-confusion SPKI/PKCS1/
  PEM/DER, kid injection traversal/SQLi/unknown, tampered sig, expired) —
  see `multi-account-auth-testing.md`.
- IDOR: `userClBankAccount(id)`, `goalsMxInvestmentInformation`,
  `reserveMxWithdrawalOrder(id)`, `reserveMxPurchaseOrder(id)` → uniform
  "Cuenta no encontrada"/"Not found" cross-account. `reserveMxFind` is
  session-scoped (each account sees own reserve). Sequential IDs
  (user 1205931→1206122, bank acct 586895, reserve 63192/63193) but scoped.
- Entitlement gate pre-KYC: MarketBuy / DepositIntention / Withdrawal /
  PACS mandate / Fintoc intent all `success:false` or
  `USER_NOT_ELIGIBLE_TO_INVEST`. Bank-ID oracle: uniform "Bank account not
  found" across 6 IDs (no differential).
- Introspection off (`__schema`/`__type` don't exist), error messages leak
  schema (use as oracle). CORS `ACAO:*` WITHOUT credentials (by-design).
  Admin `/admin/reception/*` + `*.fintual.in` = VPN-gated. Webhook
  `/app/deposit-altervatives/fintoc-pac-notification` = dead (404).
  Cache-poison XFH: not reflected. Open redirect: client-side only.
  Rebrandly: third-party landing, `?url=` ignored. Subdomain takeover: 0
  across 1060 (subzy) / 5637 PR hosts (DNS-dead). nuclei 235 tpl → 0 match.
  Nickname NOT unique (CL-D got nick `x` = CL-A's) but has **zero identity
  function** (no resolver takes it) → cosmetic, not reportable.

## Honest candidates (none submittable)
- **L1 UNPROVEN**: `/auth/jwt aud=stocks-broker-mx` cross-realm mint from
  CL pre-KYC account. No consumer located; aud allowlisted; likely by-design.
- **MX-TOS CONFIRMED 3x, Low**: MX signup issues account+session with NO
  server-side ToS/consent field (client Formik requires `accepted`, server
  ignores; only separate `CreateAndSignAdvertisingConsent` marketing opt-in).
  CL unaffected (different verify_email flow). Compliance gap for a
  CMV-regulated MX broker; expect "Not to be fixed".

## Coverage wall (what needs ONE funded+KYC'd account)
IDOR on withdrawal/purchase/movements, race on money ops, referral credit
logic, PIN/step-up bypass all sit behind: **KYC (Mati identity verification)
+ funded balance + bank account + security PIN**. Without it, IDOR scoping
is UNPROVEN-BENIGN (no positive control). Referral: `canSignReferralContract
=false` on all accounts → no referralCode → self-referral untestable.
Ask operator for exactly that one thing; do not fabricate KYC.

## Tooling notes for this target
- WAF answers 403 for many unauth paths AND for `api.fintual.*` entirely —
  `evidence of 403` ≠ finding, and WAF-block ≠ target-clean (see coverage
  ledger rule). ffuf `/api/*` = 5044×403 (1037-byte admin-block page is
  still the WAF, not an app).
- nuclei full-tag wedged silently at gentle rate (0 output, 0.23s CPU/20s,
  62 stalled sockets → killed); 3-host focused run (235 tpl) completed in
  4 min, 0 matches. Prefer focused target lists over apex-wildcard lists.
- deep-audit guard: BLOCKED on the manual `_progress/fintual_v1` dir (no
  `tools-usage.json`); GREEN on `orchestrator-fintual_com` (13-check) —
  the orchestrator dir is the authoritative evidence store.
