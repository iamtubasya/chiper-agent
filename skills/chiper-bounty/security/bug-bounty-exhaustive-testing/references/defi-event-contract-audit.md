# DeFi Event Contract / Binary Option Audit Guide

**Trigger:** Target is a crypto trading platform, event contract, or binary option site.

## Architecture Discovery

### Step 1: Verify On-Chain vs Off-Chain

Many platforms market as "on-chain" but operate as centralized APIs.

```bash
# Search GitHub for SDK / reverse-engineered code
curl -s "https://api.github.com/search/repositories?q=${TARGET}+in:name&per_page=10" | \
  python3 -c "import sys,json; [print(f\"{r['full_name']}: {r['description']}\") for r in json.load(sys.stdin).get('items',[])]"

# Check JS bundles for Solana program IDs
grep -oE '[1-9A-HJ-NP-Za-km-z]{32,44}' main-*.js | sort -u | head -20

# Check API endpoints (if REST = CEX, if RPC = on-chain)
curl -s "https://api.${TARGET}/pool/pair/list" | head -c 200
```

**TurboFlow case study (Sep 2026):**
- Markets as "on-chain perpetuals"
- SDK reveals: REST API + JWT auth + server-side matching
- NO Solana program interaction in trading path
- Settlement: price comparison at expiry (server-side)

### Step 2: Map Trading Flow

```bash
# Common event contract endpoints:
# POST /account/pm/order/submit    — Place order
# GET  /account/pm/positions       — Current positions
# GET  /account/pm/histories       — Order history
# GET  /public/pm/config           — Trading configs
# GET  /public/pm/trades           — Public trades
# GET  /market/kline               — Price candles
# GET  /pool/pair/list             — Pair list + prices
```

### Step 3: Price Feed Analysis

```bash
# Compare platform price vs major exchanges
# Consistent offset = different oracle source
# Variable offset = latency (arbitrage possible)
# Measure update frequency with rapid checks
```

### Step 4: Settlement Mechanism Analysis

```bash
# Check PM trades for settlement pattern
# Compare kline close vs spot price
# Determine: candle-based, real-time, or external oracle
```

### Step 5: Return Rate Analysis

```bash
# Get return rates from PM config
# Calculate breakeven winrate = 100 / (100 + return_rate * 100)
# Platform edge = breakeven_winrate - 50%
```

## Common Vulnerability Classes

1. Price Feed Manipulation — if settlement uses external oracle
2. Timing Attacks — front-run settlement with correct direction
3. API Abuse — from leaked SDK (bots, enumeration, rate limit bypass)
4. Business Logic — negative/zero amounts, leverage bypass

## References
- Also read: `cors-multisubdomain-testing.md`
- Also read: `jwt-attack-suite.md`
