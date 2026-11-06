# Aurory Bug Bounty Program — Reference

Source: Bugcrowd program page (extracted 2026-08-31)

## Program Identity
- **Name:** Aurory
- **URL:** bugcrowd.com/engagements/aurory-mbb-og2
- **Status:** Ongoing (since Sep 11, 2024, last updated Aug 26, 2026)
- **Managed by:** Bugcrowd
- **Safe Harbor:** Partial (not all listed vulnerabilities)

## In-Scope Targets
| Asset | Type |
|-------|------|
| `*.aurory.io` | Web |
| `*.aurorynet.io` | Infrastructure |
| `aurory.io` | Web |
| `aurorynet.io` | Infrastructure |
| `amikoarena.com` | Web (Amiko Arena game) |
| `amikolegends.com` | Web (Amiko Legends game) |

## Focus Areas
1. Transaction manipulation
2. Access (authentication/authorization)
3. Insecure API endpoints
4. Mobile Applications (iOS and Android) — both in test version mirroring production
5. Game Client & Server — Amiko Legends (Epic Games launcher) + servers
6. API Docs available (AuroryAPIDocs.xlsx download on program page)

## Rewards (with increase active until ~30 Jun 2025)
| Priority | Cash Range | Kudos |
|----------|-----------|-------|
| P1 (Critical) | $3,500 - $4,500 | 40 |
| P2 (High) | $1,500 - $2,500 | 20 |
| P3 (Moderate) | $400 - $650 | 10 |
| P4 (Low) | $100 - $200 | 5 |

## Out-of-Scope
- `blog.aurory.io` (blog)
- Sentry.io (third-party error tracking)
- Arbitrum Casier Smart Contract
- `wss://ws.aurorynet.dev.aurory.io` (dev WebSocket)

## Program Stats (verified 2026-08-31)
- **Scope Rating:** 1 out of 4
- **Vulnerabilities rewarded:** 13
- **Validation within:** ~1 month (75% accepted/rejected within 3 months)
- **"Reward increase" label** active on program page (verify date before submission)
- **Testing period:** Ongoing (started Sep 11, 2024)
- **Last updated:** Aug 26, 2026
- **"Submit report" button** requires login → user submits manually

## Known Architecture
- **Game:** Blockchain game on Solana (Nefties characters, NFTs, items)
- **Auth:** Wallet-based (Solana/EVM) for main game; secret string for API
- **API pattern:** `{service}.live.aurory.io` (prod), `{service}.preprod.live.aurory.io` (preprod)
- **Public APIs:** auth-public-api, items-public-api, referral-public-api, marketplace-public-api, commerce-public-api, social-public-api, stats-public-api, presence-public-api
- **CMS:** Payload CMS at `cms.cdn.aurory.io/payload-cms`
- **RPC:** `aurory.rpcpool.com`, `rpc.aurorynet.dev.aurory.io`
- **Token:** AURY on Solana (`AURYydfxJib1ZkTir1Jn1J9ECYUtjb6rKQVmtYaixWPP`)
- **SyncSpace bridge:** Arbitrum → paused (contract `0x5318f9515c4b9de7188e570830e801588d62be88`)

## Validated Findings (2026-08)

### F1: Unauthenticated JWT Minting (P2-P1)
- **Vector:** `POST /v1/ownership/{ownership_id}/token` (no auth required)
- **Impact:** Mint valid JWT for any ownership_id → account takeover → buy items in victim's account
- **Key detail:** `ownership_id` is UUID v4 random (not enumerable), but discovery through other vectors (CORS, referral stats, XSS) makes it exploitable
- **Framing:** "Broken Authentication — Unauthenticated JWT Minting via Public API"

### F2: Account Creation + Auth Token Access (P2)
- **Vector:** `POST /v1/auth/signup` (unauthenticated) → `POST /v1/account/token` (unauthenticated)
- **Impact:** Create account → mint JWT → access private data (CABAL-O, inventory, purchases)
- **Key detail:** Dev environment identical to production (IS_PROD=true), platform spoofing accepted

### F3: CORS Misconfiguration on Public APIs (P3)
- **Vector:** `items-public-api` reflects Origin + allows Authorization headers
- **Impact:** Cross-origin JS can read API responses with user's auth token
- **Framing:** Chain with XSS or other vector for token theft

### F4: Stored XSS on Game Domain (P2)
- **Vector:** Avatar filename not sanitized (stored in DB, reflected in profile page)
- **Impact:** Execute JS on `*.aurory.io` → steal JWT from localStorage → account takeover
- **Framing:** Chain with F1 (JWT minting) for zero-knowledge exploit

### F5: Captcha/Name Validation Bypass (P4)
- **Vector:** Registration accepts `<script>alert(1)</script>` as display name
- **Impact:** Stored XSS in user profiles (reflected in admin/other user views)
- **Low severity:** Limited impact without chaining

## Key Lessons from Aurory Engagement
1. **Programs with "focus areas" give you framing hints** — match your finding to their language
2. **Game domains = goldmine for XSS** — JWT stored in localStorage, not HttpOnly cookies
3. **Public APIs with wallet auth = verify server-side** — client auth ≠ server auth
4. **Dev environments in production = common** — check preprod/staging URLs
5. **JWT minting is the killer finding** — frame as auth bypass, not as XSS
6. **Preprod with IS_PROD=true = production data accessible** — common in game platforms
