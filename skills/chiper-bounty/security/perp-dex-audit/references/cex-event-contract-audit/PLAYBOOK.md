---
name: cex-event-contract-audit
description: "Audit CEX event contracts for settlement bias vectors."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, cex, event-contract, binary-option, settlement, price-feed]
  scope: [CEX event contracts, binary options, prediction markets]
---

# CEX Event Contract Audit — Settlement & Price Feed Analysis

## ⛔ REFERENCE AUTO-LOAD (MANDATORY — load when this skill is activated)
When this skill is loaded, IMMEDIATELY read this reference file:
```
read_file('references/cex-settlement-bias-analysis.md')
```

## ⛔ CANDIDATE RULE (MANDATORY — EVERY TEST)
- **Each test = one candidate. Finding something = mark candidate. CONTINUE to next test.**
- **Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0F).**
- **DO NOT generate report during Phase 0C. Report = ABSOLUTE LAST.**
- **If you find CRITICAL → mark candidate → KEEP TESTING. Do NOT stop.**

## When to Use

Target is a CEX event contract / binary option / prediction market platform (TurboFlow-style).
Trigger: user asks to audit a DeFi trading platform, binary option, or prediction market that uses server-side settlement.

> **KEY LESSON (TurboFlow Sep 18):** When auditing CEX event contracts, FOCUS ON TARGET'S INTERNAL SYSTEMS FIRST. Don't jump to external exchange manipulation (Binance, OKX) before understanding how the target's own price feed and settlement work.

## Pitfall: External vs Internal Analysis

```
WRONG: "Can we manipulate Binance to influence TurboFlow?"
RIGHT: "How does TurboFlow's own system determine settlement price?"

Wrong first:
1. Analyze Binance order book
2. Calculate flash loan costs
3. Study cross-exchange arbitrage
... (wasted time, not target-specific)

Right first:
1. Trace price feed source (which exchange? which endpoint?)
2. Compare cross-subdomain prices
3. Analyze settlement direction from public trade data
4. Detect systematic bias
... (target-specific, actionable findings)
```

**Rule:** Exhaust INTERNAL vectors before analyzing EXTERNAL manipulation. The target's own system is the attack surface, not Binance.

## Methodology

### Phase 1: Price Feed Source Tracing

Determine WHERE the target gets its price from.

```bash
# Compare target price with multiple exchanges simultaneously
echo "=== Price Source Tracing ==="
TF=$(curl -s "https://api.target.xyz/pool/pair/list" -H "Biz-pf: 6" 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print([p['price'] for p in d['data'] if p['pair_id']=='6'][0])" 2>/dev/null)
echo "Target: $TF"

BN_SPOT=$(curl -s "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" 2>/dev/null | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['price'])" 2>/dev/null)
echo "Binance Spot: $BN_SPOT (diff: $(echo "$TF - $BN_SPOT" | bc 2>/dev/null || echo "?"))"

BN_FUT=$(curl -s "https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT" 2>/dev/null | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['price'])" 2>/dev/null)
echo "Binance Futures: $BN_FUT (diff: $(echo "$TF - $BN_FUT" | bc 2>/dev/null || echo "?"))"
```

**Interpretation:**
- TF ≈ BN Spot → uses spot feed
- TF ≈ BN Futures → uses futures feed (most common for CEX event contracts)
- TF ≈ neither → uses own internal feed or another exchange
- TF has constant offset → deliberate markup/markdown

### Phase 2: Cross-Subdomain Price Inconsistency

Check if different API subdomains return different prices.

```bash
for sub in api api2 api3 api4 apis; do
  P=$(curl -s "https://${sub}.target.xyz/pool/pair/list" -H "Biz-pf: 6" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print([p['price'] for p in d['data'] if p['pair_id']=='6'][0])" 2>/dev/null)
  echo "${sub}: $P"
done
```

**If prices differ:**
- Different subdomains may have different backend servers
- Settlement may use a specific subdomain's price
- Potential arbitrage if you can predict which subdomain is used

### Phase 2.5: Volume & Feed Verification

Check if price is driven by internal order book or external feed.

```bash
# Check if volume changes (indicating internal order matching)
echo "=== Volume Check ==="
for i in 1 2 3 4 5; do
  V=$(curl -s "https://api.target.xyz/pool/pair/list" -H "Biz-pf: 6" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print([p['volume_24h'] for p in d['data'] if p['pair_id']=='6'][0])" 2>/dev/null)
  echo "[$i] volume=$V"
  sleep 1
done
```

**Interpretation:**
- Volume CHANGES → internal order matching (price influenced by trading)
- Volume FIXED → external feed (price comes from outside, not influenced by trades)
- If FIXED: price manipulation from inside the platform is NOT possible
- If CHANGES: large trades might influence settlement price

### Phase 2.6: Settlement Timestamp Analysis

Verify WHEN settlement price is captured relative to order time.

```python
from datetime import datetime

for t in finished[:10]:
    created = t['created_at']
    settled = t['settled_at']
    duration = t['duration']
    
    ct = datetime.fromisoformat(created.replace('Z', '+00:00'))
    st = datetime.fromisoformat(settled.replace('Z', '+00:00'))
    actual = (st - ct).total_seconds()
    
    print(f"Duration: {duration}s | Actual: {actual:.1f}s | Delta: {actual-duration:+.1f}s")
```

**Key:**
- Delta ≈ 0 → settlement at exact duration expiry
- Delta > 0 → settlement delayed (potential timing attack)
- Delta < 0 → settlement提前 (potential front-running)

### Phase 3: Settlement Direction Analysis

Analyze public trade data for systematic bias.

**⛔ CRITICAL PITFALL: Market Trend ≠ Platform Bias**
```
WRONG: "Settlement 71% DOWN → LOWER always wins → CRITICAL VULNERABILITY"
RIGHT: "Market was trending down during observation → directional bias is MARKET, not PLATFORM"

How to distinguish:
1. Raw settlement direction (UP vs DOWN) ALWAYS reflects market trend
   - Bull market → more UP settlements → HIGHER wins more
   - Bear market → more DOWN settlements → LOWER wins more
   - THIS IS NORMAL BINARY OPTION BEHAVIOR
2. Real platform bias = settlement DIVERGES from market trend
   - If market goes UP but settlement goes DOWN → platform bias
   - If settlement follows market direction → no bias
3. Statistical significance (Z-test) only tests if direction ≠ 50/50
   - It does NOT test if direction differs from MARKET
   - Z=9.91 with market downtrend = expected, not exploitable
```

**Verification: Settlement vs Market Trend**
```python
# The RIGHT way to test for platform bias:
# Compare settlement direction with ENTRY PRICE TREND (proxy for market)

for i in range(1, len(finished)):
    prev_entry = float(finished[i-1]['entry_price'])
    curr_entry = float(finished[i]['entry_price'])
    market_trend = curr_entry - prev_entry  # positive = market up
    
    curr_settle = float(finished[i]['settled_price'])
    settlement_move = curr_settle - curr_entry  # positive = settle up
    
    # If settlement follows market trend → NO bias
    # If settlement goes against market → platform bias
    follows_trend = (market_trend > 0 and settlement_move > 0) or \
                    (market_trend < 0 and settlement_move < 0)
```

**If settlement FOLLOWS market trend (50-60%+):** No platform bias. Directional wins are from market movement, not vulnerability.

**If settlement goes AGAINST market trend (50%+):** Real platform bias. Exploitable.

```python
import requests, math

# Get trades (paginate for more data)
all_trades = []
for page in range(1, 10):
    r = requests.get(f'https://api.target.xyz/public/pm/trades?limit=100&page={page}',
                      headers={'Biz-pf': '6'}, timeout=5)
    data = r.json()['data']['data']
    if not data: break
    all_trades.extend(data)

finished = [t for t in all_trades if t['order_status'] == 'Finished']
print(f"Total finished trades: {len(finished)}")

# Direction analysis
up = sum(1 for t in finished if float(t['settled_price']) > float(t['entry_price']))
dn = sum(1 for t in finished if float(t['settled_price']) < float(t['entry_price']))
print(f"UP: {up} ({100*up/len(finished):.1f}%) DOWN: {dn} ({100*dn/len(finished):.1f}%)")
print(f"  ⚠️ This reflects MARKET TREND, not platform bias. Don't overclaim.")

# Win rate by side
h_wins = sum(1 for t in finished if t['side']==1 and float(t['realized_pnl'])>0)
h_total = sum(1 for t in finished if t['side']==1)
l_wins = sum(1 for t in finished if t['side']==2 and float(t['realized_pnl'])>0)
l_total = sum(1 for t in finished if t['side']==2)
print(f"HIGHER: {h_wins}/{h_total} ({100*h_wins/h_total:.1f}%)")
print(f"LOWER:  {l_wins}/{l_total} ({100*l_wins/l_total:.1f}%)")

# Market trend check — ESSENTIAL before interpreting directional wins
entries = [float(t['entry_price']) for t in finished]
overall_trend = (entries[-1] - entries[0]) / entries[0] * 100
print(f"Market trend during observation: {overall_trend:+.2f}%")
if abs(overall_trend) > 0.1:
    print(f"  → Market moved {overall_trend:+.2f}% — directional wins reflect MARKET, not bias")

# Settlement vs trend — THE ACTUAL TEST
follows = 0
against = 0
for i in range(1, len(finished)):
    trend = float(finished[i]['entry_price']) - float(finished[i-1]['entry_price'])
    move = float(finished[i]['settled_price']) - float(finished[i]['entry_price'])
    if (trend > 0 and move > 0) or (trend < 0 and move < 0):
        follows += 1
    else:
        against += 1

print(f"Settlement follows market: {follows}/{follows+against} ({100*follows/(follows+against):.1f}%)")
if 100*follows/(follows+against) > 55:
    print("  → NO platform bias. Directional wins = market trend.")
else:
    print("  → POSSIBLE platform bias. Settlement diverges from market.")

# Statistical significance (Z-test) — STILL useful but context matters
p_hat = dn / (up + dn)
z = (p_hat - 0.5) / math.sqrt(0.5 * 0.5 / (up + dn))
print(f"Z-score: {z:.2f} (|z|>2.58 = p<0.01)")
print(f"  ⚠️ Z-test only checks if ≠50/50. Does NOT check vs market trend.")

# Expected value
ret = 0.85  # typical return rate
l_ev = (l_wins/l_total) * ret - (1 - l_wins/l_total) * 1.0
kelly = (l_wins/l_total * (ret+1) - 1) / ret
print(f"LOWER EV: {l_ev*100:+.1f}% | Kelly: {kelly*100:.1f}%")
print(f"  ⚠️ EV based on raw win rate. If win rate = market trend → EV is market return, not edge.")
```

### Phase 4: Settlement Timing Analysis

Check WHEN settlement price is captured.

```python
# Analyze entry time vs settlement time
from datetime import datetime

for t in finished[:10]:
    entry_time = t.get('created_at', '')
    settle_time = t.get('close_time', t.get('settlement_time', ''))
    duration = t.get('duration', 0)
    
    try:
        et = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
        st = datetime.fromisoformat(settle_time.replace('Z', '+00:00'))
        actual = (st - et).total_seconds()
    except:
        actual = '?'
    
    print(f"Duration: {duration}s | Actual: {actual}s | Entry: ...{entry_time[-8:]}")
```

**Key questions:**
- Does settlement use entry price, close price, or average price?
- Is there a delay between order and settlement start?
- Can you predict settlement price from current price trend?

### Phase 5: Vulnerability Classification

| Finding | Severity | Evidence Required |
|---------|----------|-------------------|
| Settlement bias (Z > 2.58 AND diverges from market) | HIGH-CRITICAL | 200+ trades, trend-controlled test |
| Cross-subdomain price diff | MEDIUM-HIGH | Consistent $1+ spread |
| Price feed source exposed | INFO | JS bundle analysis |
| Settlement timing predictable | MEDIUM | Timestamp correlation |
| No rate limit on orders | LOW | Rapid fire test |
| Volume FIXED (no internal matching) | INFO | Volume unchanged over time |
| Settlement follows market trend | INFO (NOT a finding) | Trend-controlled analysis |

**⛔ OVERCLAIMING PITFALL:**
```
WRONG: "71% settlement DOWN (Z=9.91) → CRITICAL platform bias"
RIGHT: "71% settlement DOWN, BUT market trend was -X%. Settlement FOLLOWS market → no bias."

Overclaim patterns in settlement analysis:
1. Raw directional win rate WITHOUT market trend context
2. Z-test significance WITHOUT trend-controlled test
3. EV calculation based on raw win rate (which includes market returns)
4. Claiming "bias" when settlement follows market direction
5. Claiming "arbitrage" when cross-subdomain prices converge over time
```

## TurboFlow Case Study (Sep 18, 2026)

- Pair IDs: BTC=6, ETH=5, XAU=467401036654819328
- Price endpoint: `/pool/pair/list` → `price` field
- Trade history: `/public/pm/trades` → public, no auth
- Return rates: BTC 30s ask=87.2%/bid=88.7%
- Auth: Bearer JWT + uid header
- Settlement: server-side, not on-chain
- Volume: FIXED (confirmed — 5 readings identical) → external price feed
- Settlement delta: ≈ duration (30s → 29.8s) → no timing attack
- Kline close ≈ settlement price (±$0.15) → settlement uses internal kline
- Settlement bias claim (71% DOWN): FALSE — was market downtrend, not platform bias
- Cross-subdomain price diff: $1-26 observed but inconsistent over time
- Price source: Binance Futures ($1-3 offset, not spot which is $30+ off)
- SDK reverse-engineering: `linshengyyy/turboflow-rs` (full API surface)
- All audit files DELETED per user request

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Price feed source tracing: target vs Binance spot vs Binance futures (3-way diff) | Menentukan apakah feed internal atau eksternal — semua analisis berikutnya bergantung padanya |
| 2 | Volume stability: 5 reading berturut, fixed vs berubah | Volume FIXED = eksternal feed = manipulasi internal mustahil |
| 3 | Settlement delta vs declared duration (10+ trade) | Delta ≈ 0 = tidak ada timing attack; jangan klaim tanpa ini |
| 4 | Settlement-vs-market-trend test (bukan raw directional rate) | Raw win rate 71% DOWN di pasar turun = NORMAL, bukan bias platform |
| 5 | Cross-subdomain price consistency sweep | Spread yang konvergen seiring waktu = bukan arbitrage |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## 2026 sweep (settlement & oracle yang masih jadi jebakan)

- **Kline-close as settlement source** — settlement price == internal kline close (±$0.15) berarti platform mengutip dirinya sendiri; tapi itu BUKAN bias kalau kline-nya mengikuti market. Uji divergence, bukan equality.
- **Staleness tanpa grace period** — oracle feed yang tidak cek `updatedAt` = stale price saat feed freeze. Probe: bandingkan `updatedAt` dengan block timestamp.
- **Confidence interval diabaikan** — Pyth `price.conf`: kalau kontrak cuma baca `price` dan abaikan `conf`, price dengan confidence lebar bisa dipakai.
- **Cross-subdomain settlement routing** — settlement mungkin pakai subdomain spesifik; kalau bisa diprediksi subdomain mana, ada edge. Tapi kalau harga konvergen, edge-nya nol.
- **EV tanpa trend control** — EV dihitung dari raw win rate termasuk market return. Selalu kurangi market beta sebelum klaim edge.

## References

- `references/cex-settlement-bias-analysis.md` — TurboFlow case study with full methodology


## Critical severity anchor (apa yang membuat temuan dari skill ini Critical)

Skill ini menghasilkan *analisis settlement*, bukan temuan. Yang membuatnya Critical adalah
kalau ada **edge yang bisa di-exploit berulang**:

| Temuan | Severity |
|---|---|
| Settlement bias yang DIVERGE dari market trend (trend-controlled, 200+ trade) | HIGH-CRITICAL |
| Timing attack: settlement delayed → prediksi harga settlement | HIGH-CRITICAL |
| Cross-subdomain price diff konsisten $1+ yang bisa diprediksi subdomain mana yang dipakai | MEDIUM-HIGH |
| Settlement follows market trend | **INFO — BUKAN temuan** |
| Volume FIXED (eksternal feed) | INFO |
| Price source teridentifikasi (JS bundle) | INFO |

**Kalibrasi wajib:** raw directional win rate TANPA market-trend context = overclaim. Z-test
hanya menguji ≠50/50, TIDAK menguji vs market trend. EV dihitung dari raw win rate termasuk
market return — kurangi market beta sebelum klaim edge.
