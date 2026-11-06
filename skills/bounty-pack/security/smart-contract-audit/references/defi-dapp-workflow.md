# DeFi dApp Audit Workflow — SDK Reverse Engineering

**Source:** TurboFlow audit session (2026-09-18)
**Problem:** DeFi targets marketed as "on-chain" may actually be CEX API platforms. Program IDs obfuscated in JS bundles. Traditional smart contract audit tools (slither, foundry) find nothing because there's no on-chain contract.

## Detection: Is it really on-chain?

1. **Check JS bundles for program interaction patterns:**
   ```bash
   grep -oE '(sendTransaction|signTransaction|Transaction\(|programId)[^;]{0,100}' main-*.js
   ```
   If no Solana/EVM transaction patterns found → likely CEX API.

2. **Search for reverse-engineered SDKs on GitHub:**
   ```bash
   curl -s "https://api.github.com/search/repositories?q=turboflow+in:name" | python3 -c "
   import sys,json
   for r in json.load(sys.stdin).get('items',[]):
       print(f\"{r['full_name']}: {r['description']}\")
   "
   ```

3. **Check if trading happens via REST API or on-chain tx:**
   ```bash
   # If this returns JSON with order data → CEX API
   curl -s "https://api.TARGET/account/pm/order/submit" -X POST -H "Content-Type: application/json" -d '{}'
   ```

## Reverse Engineering Closed-Source Client SDKs

### Step 1: Find SDK source
- GitHub search: `target-site in:name`, `target-rust in:name`, `target-sdk in:name`
- Check npm/pip/cargo registries for published packages
- Look for "reverse engineering" or "逆向" in repo descriptions

### Step 2: Extract API surface
From SDK source, extract:
- **Base URL** (usually `const BASE_URL = "https://api.target.xyz"`)
- **All endpoint paths** (grep for `format!("{}/...`)
- **Auth headers** (JWT, API key, session)
- **Request/response schemas** (struct definitions)
- **Trading parameters** (pair IDs, durations, order types)

### Step 3: Map trading flow
```
SDK reveals:
1. Auth mechanism (JWT + uid header)
2. Order submission (POST /account/pm/order/submit)
3. Balance check (GET /account/assets/v2)
4. Position query (GET /account/pm/positions)
5. History (GET /account/pm/histories)
→ All REST API, no on-chain transaction
```

### Step 4: Test for vulnerabilities
With the full API surface:
- **IDOR:** Test `account_id` in POST body vs `uid` in header
- **Auth bypass:** Try expired/modified tokens
- **Rate limiting:** Test rapid order submissions
- **Business logic:** Manipulate duration, return_rate, order_way
- **Admin endpoints:** Test `/admin/*` paths from SDK

## TurboFlow-Specific Findings

| Finding | Detail |
|---------|--------|
| Architecture | CEX API (not on-chain perps as marketed) |
| SDK | `linshengyyy/turboflow-rs` (Rust, reverse-engineered) |
| Auth | JWT + uid header |
| Order endpoint | POST `/account/pm/order/submit` |
| Pair IDs | BTC=6, ETH=5, XAU=467401036654819328 |
| Order ways | 1=Higher, 2=Lower |
| Durations | 30s, 60s, 180s, 300s, 600s, 900s, 3600s |

## Key Lesson

**"On-chain" in marketing ≠ on-chain in implementation.** Always verify by:
1. Checking JS bundles for transaction-building code
2. Searching for reverse-engineered SDKs
3. Testing if orders go through REST API or blockchain transactions
4. Looking for Solana program IDs in the codebase
