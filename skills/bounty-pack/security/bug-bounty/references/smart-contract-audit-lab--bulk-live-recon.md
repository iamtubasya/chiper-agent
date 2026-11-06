# BULK Exchange — Live Protocol Recon (2026-08-24)

## Protocol Overview
- **BULK**: Fully on-chain perpetuals exchange on Solana
- **Architecture**: BULKBFT consensus, custom matching engine in validator nodes
- **TVL**: $21.7M
- **Docs**: https://docs.bulk.trade

## Key Architecture Findings
- Production uses standard Solana instructions (MarketOrder, LimitOrder) — NOT the eBPF VM
- eBPF VM code (`BulkBookVM`) exists in repo but is only used in `#[cfg(test)]`
- Self-Trade Prevention operates at ACCOUNT level, not WALLET level
- AURA points system for trading rewards
- Referral system with access codes
- Validator rewards: 12.5% of trading fees, weighted by origination (50%) + participation (40%) + stake (10%)
- Sub-accounts supported (main + multiple sub)

## Live Vulnerability Surface (verified from production docs)
1. **L-01**: Multi-account wash trading bypasses STP (STP = account-level, not wallet-level)
2. **L-02**: AURA points gaming via sub-account volume splitting
3. **L-03**: Referral self-referral farming (no wallet clustering check)
4. **L-04**: Validator collusion in peer-witnessed origination credits
5. **L-05**: Liquidation cascade manipulation via position sizing
6. **L-06**: API IDOR — unsigned account query endpoint
7. **L-07**: Builder code injection (third-party integration)

## Key Lesson
**Static code analysis of unreachable code = wasted time.** Always verify code is in production flow BEFORE deep analysis. The eBPF VM audit produced 5 "critical" findings that were all non-exploitable because the VM was test-only.

## API Endpoints
- Base: `https://exchange-api.bulk.trade/api/v1/`
- Market data (unsigned): `/stats`, `/exchange-info`, `/ticker`, `/candles`, `/l2-book`, `/risk-surfaces`, `/size-impact`, `/fee-state`
- Account (unsigned): `/account/query` — potential IDOR
- Trading (signed): `/orders`, `/agent-wallet`, `/settings`, `/sub-accounts`, `/transfer`, `/multisig`
- Testnet: `/faucet` (signed)
- WebSocket: market data streams, account stream, trading via WS
