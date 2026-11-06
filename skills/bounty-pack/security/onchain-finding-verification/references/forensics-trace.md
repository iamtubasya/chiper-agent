# Blockchain Forensics & Trace Tools
> Source: rohteemie/Open-Source-Blockchain-Forensics (5★)
> Source: rajdeepcodeshere247/Crypto-Trace-AI

## Transaction Tracing

### Entity Clustering
- Group addresses controlled by same entity
- Heuristics: common input ownership, change address detection
- Tools: Open-Source-Blockchain-Forensics

### Trace Analysis
```bash
# Etherscan API for tx history
curl "https://api.etherscan.io/api?module=account&action=txlist&address=$ADDR&startblock=0&endblock=99999999&page=1&offset=100&sort=desc&apikey=$KEY"

# Trace internal transactions
curl "https://api.etherscan.io/api?module=account&action=txlistinternal&address=$ADDR&startblock=0&endblock=99999999&page=1&offset=100&sort=desc&apikey=$KEY"

# Token transfers
curl "https://api.etherscan.io/api?module=account&action=tokentx&address=$ADDR&page=1&offset=100&sort=desc&apikey=$KEY"
```

### Pattern Detection
- Layering: Multiple hops through mixing services
- Peeling chains: Sequential small transfers
- Tornado Cash interaction: Deposit → wait → withdraw from new address
- Cross-chain bridging: Move funds across chains to obscure trail

### AML Red Flags
- Interaction with sanctioned addresses
- High-volume circular transactions
- Rapid deposit/withdrawal patterns
- Interaction with known scam addresses

## Pipeline
- Phase 0C: Trace exploited funds after PoC
- Phase 0C: Verify on-chain impact for report
- Phase 0F: Include trace evidence in report
