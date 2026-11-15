## Appendix A: Solana Program Analysis (RPC-based, no source needed)

When BPF source is unavailable (closed-source, only client SDK found), verify program
architecture via Solana RPC calls. No decompilation needed.

```bash
SOL_RPC="https://api.mainnet-beta.solana.com"

# 1. Program owner → upgradeable?
curl -s -X POST "$SOL_RPC" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1,
  "method": "getAccountInfo",
  "params": ["PROGRAM_ID", {"encoding": "jsonParsed"}]
}'
# Owner: BPFLoaderUpgradeab1e = UPGRADEABLE
# Owner: BPFLoader2002728 = IMMUTABLE

# 2. Upgrade authority (from program data account)
curl -s -X POST "$SOL_RPC" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1,
  "method": "getAccountInfo",
  "params": ["PROGRAM_DATA_ACCOUNT", {"encoding": "base64"}]
}' | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
raw = base64.b64decode(d['result']['value']['data'][0])
auth = raw[-32:]  # Last 32 bytes = upgrade authority
if auth == b'\x00' * 32:
    print('Authority: NONE (immutable)')
else:
    import base58 as b58
    print(f'Authority: {b58.b58encode(auth).decode()}')
    print('If EOA → single key compromise risk')
"

# 3. Vault balance
curl -s -X POST "$SOL_RPC" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1,
  "method": "getTokenAccountBalance",
  "params": ["VAULT_ATA"]
}'

# 4. Recent transactions + instruction decode
curl -s -X POST "$SOL_RPC" -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1,
  "method": "getSignaturesForAddress",
  "params": ["PROGRAM_ID", {"limit": 10}]
}'
# Decode base58 instruction data → opcode + params
python3 -c "
import base58, struct
data = base58.b58decode('BASE58_IX_DATA')
print(f'Opcode: {data[0]}')
if len(data) >= 9:
    amount = struct.unpack('<Q', data[1:9])[0]
    print(f'Amount: {amount}')
"
```

**Cross-reference checklist (SDK source vs on-chain):**
- PDA seeds match on-chain vault PDA
- Instruction opcodes match SDK's Action enum
- Account layout matches expected positions
- Clear-sign message matches what user signs
- No hidden CPI targets
- Upgrade authority is multisig, not EOA

**Solana-specific high-value findings:**
| Finding | Severity |
|---------|----------|
| Upgrade authority is EOA when docs claim multisig | CRITICAL candidate |
| Signing path divergence (clear-sign vs canonical) | HIGH |
| Upgradeable main + immutable CPI → bypass via upgrade | HIGH |
| Offchain orderbook, no on-chain price validation | MEDIUM-HIGH |
| Admin-controlled opaque risk parameters | MEDIUM |
| API IDOR — account data exposed without auth | CRITICAL |

### Appendix A1: DEX API Attack Surface (offchain extension)

On-chain audits miss offchain API endpoints. For DEX targets, ALWAYS extend to API:

1. **Subdomain enum** — `subfinder -d target.trade` → api, staging, admin, ws, mobile
2. **Endpoint probe** — `POST /api/v1/account` with `{"type":"fullAccount","user":"<PUBKEY>"}` → IDOR
3. **Auth mechanism** — Check if API requires JWT/session/signature for account queries
4. **Batch IDOR** — Get 10+ real user pubkeys from on-chain txs, test each
5. **Write endpoints** — Can you place orders / transfer without signature? (usually blocked, but test)

**PDF audit report comparison:** Download vendor audit PDF → MCP `extract_text_from_pdf` → parse structured findings → compare with own findings. Findings NOT in vendor scope = new findings.

Full patterns + case studies: see `onchain-finding-verification` skill §1c and §6.

