# CEX Settlement Bias Analysis — TurboFlow Case Study

## Target: turboflow.xyz

CEX event contract platform (binary option / prediction market).
Settlement is server-side, not on-chain.

## Discovery Timeline

1. **Price Feed Source Tracing** — Compared TF price with Binance Spot, Binance Futures, OKX
   - Result: TF ≈ Binance Futures ($1-3 diff), NOT spot ($30-35 diff)
   - TF uses futures feed + deliberate offset

2. **Cross-Subdomain Price Inconsistency** — Compared api, api2, api4, apis
   - Result: Prices differ by $1-26 between subdomains
   - Different backends may serve different prices

3. **Settlement Direction Analysis** — Analyzed 548+ finished trades from public API
   - Result: 71.2% of settlements go DOWN (settle < entry)
   - Z-score: 9.91 (p < 0.000001) — HIGHLY significant
   - HIGHER win rate: 31.1%, LOWER win rate: 75.5%
   - LOWER EV: +40% per trade

4. **Settlement Timing** — Analyzed entry vs settlement timestamps
   - Settlement uses LIVE price at expire time
   - No fixed settlement source (not kline close)

## Key Findings

### Settlement Bias
- 71.2% of settlements settle LOWER than entry price
- This means HIGHER orders lose 69% of the time
- LOWER orders win 75.5% of the time
- Statistical significance: Z=9.91, p<0.000001

### Price Feed
- TurboFlow uses Binance Futures price (not spot)
- Constant offset ~$1-3 from Binance Futures
- Updates every ~150-200ms
- Price feed is internal, not directly manipulable from outside

### Cross-Subdomain Inconsistency
- api, api2, api4, apis return different prices
- Spread: $1-26 (variable)
- Could indicate different backend servers or stale caches
- Settlement may use specific subdomain's price

## Exploitation Strategy

### Strategy: Always LOWER
- Place LOWER orders consistently
- Win rate: 75.5%
- Return per win: ~85%
- Expected profit: +40% per trade
- Kelly optimal: 46.8% bankroll

### Implementation
1. Monitor `/public/pm/trades` for settlement patterns
2. Place LOWER orders on any pair (BTC/ETH/XAU)
3. Duration: 30s (most data available)
4. Amount: Kelly criterion sizing
5. Expected return: 2000-4000% per day (theoretical)

## Risk Factors

1. **Platform may patch** — If they detect unusual win rates
2. **Sample size** — 548 trades may not be representative
3. **Time-varying** — Bias may change over time (recent 100 trades showed 32% UP)
4. **Account detection** — Platform may flag consistent winners
5. **Liquidity** — Large bets may affect settlement

## Methodology for Future Targets

```python
# Quick settlement bias check
import requests, math

r = requests.get('https://api.target.xyz/public/pm/trades?limit=100', 
                  headers={'Biz-pf': '6'})
trades = r.json()['data']['data']
finished = [t for t in trades if t['order_status'] == 'Finished']

up = sum(1 for t in finished if float(t['settled_price']) > float(t['entry_price']))
dn = sum(1 for t in finished if float(t['settled_price']) < float(t['entry_price']))

p_hat = dn / (up + dn)
z = (p_hat - 0.5) / math.sqrt(0.5 * 0.5 / (up + dn))

print(f"DOWN rate: {p_hat:.1%}, Z-score: {z:.2f}")
if abs(z) > 2.58:
    print("SIGNIFICANT BIAS DETECTED")
```

## Related Files

- `D:/data hermes/bug-bounty/turboflow/TURBOFLOW-AUDIT-REPORT-FINAL.md` — Full audit report
- `D:/data hermes/bug-bounty/turboflow/findings.json` — 6 candidates
- `D:/data hermes/bug-bounty/turboflow/recon/vector-tracker-final.md` — 30/30 vectors
