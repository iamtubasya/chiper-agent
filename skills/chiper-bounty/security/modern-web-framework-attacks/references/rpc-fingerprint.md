# RPC Fingerprinting — Node Identification & Security Assessment
> Source: github.com/smolgroot/rpc-fingerprint (3★)
> Source: maxzzze/pwngeth (9★)

## What It Does
Identifies Ethereum/EVM node type, version, network configuration, and security posture via RPC calls.

## Quick Start
```bash
cd D:\data hermes\tools\rpc-fingerprint
pip install -r requirements.txt
python fingerprint.py --rpc $RPC_URL

# Manual checks
curl -X POST $RPC -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"web3_clientVersion","params":[],"id":1}'

curl -X POST $RPC -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"net_version","params":[],"id":1}'
```

## Fingerprinting Methods

### 1. Client Version Detection
```bash
# web3_clientVersion reveals node type
# Examples: "Geth/v1.13.0", "Erigon/v2.60.0", "Nethermind/v1.25.0"
```

### 2. Admin API Exposure
```bash
# Check if admin APIs are enabled (dangerous!)
curl -X POST $RPC -d '{"jsonrpc":"2.0","method":"admin_nodeInfo","params":[],"id":1}'
curl -X POST $RPC -d '{"jsonrpc":"2.0","method":"admin_peers","params":[],"id":1}'
curl -X POST $RPC -d '{"jsonrpc":"2.0","method":"admin_datadir","params":[],"id":1}'
```

### 3. Namespace Enumeration
```bash
# Try eth_, net_, web3_, personal_, debug_, txpool_, admin_, miner_
# Enabled namespaces = attack surface
```

### 4. Node Configuration Detection
```bash
# Chain ID (mainnet=1, goerli=5, sepolia=11155111)
curl -X POST $RPC -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'

# Gas price (reveals node config)
curl -X POST $RPC -d '{"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}'

# Block number (sync status)
curl -X POST $RPC -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

## Security Assessment
| Finding | Severity | Description |
|---------|----------|-------------|
| Admin API exposed | CRITICAL | Can unlock accounts, add peers, access data |
| personal namespace enabled | HIGH | Can sign transactions with stored keys |
| debug namespace enabled | HIGH | Can trace transactions, access memory |
| txpool namespace enabled | HIGH | Can see pending transactions (MEV) |
| No auth required | HIGH | Public RPC, all data accessible |
| Old client version | MEDIUM | Known CVEs may apply |

## pwngeth — JSON-RPC Exploit
```bash
# D:\data hermes\tools\pwngeth
# Scripts to exploit vulnerable Ethereum nodes
# Tests for: unlocked accounts, default passwords, exposed RPC
python pwngeth.py --rpc $SUSPECT_RPC --check-all
```

## Pipeline
- Phase 0B: Fingerprint target RPC endpoints during recon
- Phase 0C: Assess node security posture
- Phase 0C: Exploit exposed admin APIs if found
