# Remote-Only Contract Audit via Blockscout + RPC — Working Recipe (UPONZI on Robinhood Chain)

Audited `uponzi.network` (Robinhood Chain, chainId 4663) with no local toolchain:
pulled verified source from Blockscout, read live state via direct RPC. All steps verified working.

## Chain discovery
```bash
curl -s https://chainid.network/chains.json | python -c "
import json,sys
for c in json.load(sys.stdin):
    if 'robinhood' in c.get('name','').lower():
        print(c['chainId'], c['name'], c.get('rpc',[])[:2])"
```
→ `4663 Robinhood Chain ['https://rpc.mainnet.chain.robinhood.com', ...]`

## Pull verified source (Blockscout)
```bash
curl -s "https://robinhoodchain.blockscout.com/api?module=contract&action=getsourcecode&address=0x..." 
# -> result[0].SourceCode (multi-file, concatenated), ContractName, CompilerVersion
```
Verification check: `GET https://robinhoodchain.blockscout.com/api/v2/smart-contracts/<addr>` → name, is_verified, coin_balance (raw wei).

## Read state via direct RPC
**CRITICAL PITFALL: urllib gets HTTP 403 on this RPC without a User-Agent header.** Always send one.
```python
import urllib.request, json
RPC = "https://rpc.mainnet.chain.robinhood.com"
def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(RPC, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())
def eth_call(to, data):
    return rpc("eth_call", [{"to": to, "data": data}, "latest"]).get("result", "0x")
def balance(addr):
    return int(rpc("eth_getBalance", [addr, "latest"]).get("result", "0x0"), 16) / 1e18
```

## Selector computation — NEVER guess
Wrong selectors silently return `0x` → misleading zeros that look like real state.
```bash
pip install eth-hash pycryptodome   # if keccak missing
python -c "
from eth_hash.auto import keccak
print(keccak(b'participantsCount()').hex()[:8])   # -> 0xdd60c898"
```
Note: public state variables expose BOTH `name()` getter and raw slot selector `keccak(name)[:4]` — use the `()` form.

## Blockscout rate limits
- `/api?module=proxy&action=eth_call` → HTTP 400/429 quickly. Switch to direct RPC.
- `eth_getBalance` for contract addresses needs no special permission on RPC.

## Verified findings pattern (what the audit surfaced)
State reads gave: ENTRY_AMOUNT=0.033 ETH, SERVICE_AMOUNT=0.001 ETH (router), 6 paid + 4 free participants, totalEntryFunds=0.198 ETH, jackpotPool=0.01386 ETH (7%), settled weights, owner==developer==0x21e16d..., token/buybackBurn NOT yet configured, adapter isProductionReady=1 (Chainlink VRF on Base relayed via CCIP).

Audit output (ranked): [MEDIUM] jackpot round permanently lockable — `reportDelayedJackpotRequest()` only emits an event, never resets activeRound; a failed/lost CCIP request = jackpot pool (7% of all entry) frozen forever (no retry path). [LOW] deterministic invite codes (`keccak256(abi.encode("UPONZI_INVITE", chainid, address(this), participant, slot))`) — anyone can precompute and front-run another's invite. [LOW] sybil-able jackpot weight formula. [INFO] full centralization: owner==developer, pause + token/buyback redirect without timelock/multisig; ponzi economics (81% entry → referral tree).

## Cross-check pass (2nd session) — verified additions

### Full system map (all verified on explorers)
| Contract | Address | Chain |
|---|---|---|
| Uponzi core | 0x956FDe234F369784cFa79bc511E3C300954A2c59 | Robinhood 4663 |
| UponziPaymentRouter | 0xFF524e3aa40A883937300A5Db3b3144275a3e5CB | Robinhood 4663 |
| RobinhoodCcipRandomnessAdapter | 0xE31f00c9C3a47Dee7B1A0BA57F61Ad144Df61F82 | Robinhood 4663 |
| BaseVrfRandomnessGateway | 0x60fb69234e63d50a84296577dcd3fb4e51651982 | Base 8453 |
| VRF Coordinator (v2.5) | 0xd5d517abe5cf79b7e95ec98db0f0277788aff634 | Base 8453 |

### Key addresses (from eth_call getters)
- owner == developer == `0x21e16dec140c94d48133adc6482e276b8fe43870`
- teamTreasury = `0x9fb59199d44a03e6553af017d489b004013e6222`
- **initialBuybackWallet = `0x6ee3eefb854497599e90830989d1f7effc30496f` — SEPARATE EOA** (HIGH centralization: `releaseBuybackFunds` needs only `msg.sender == buybackRecipient`, no timelock; 7% of all entry funds flow there; 0 tx so far)
- requestSigner (backend signing key) = `0x9676418c14c3e05b40e2e9885cf6310cba764086` — separate from owner/dev (good)
- configurator = address(0) — configuration locked after bindCore (good)
- VRF subscription: 0.5 ETH funded, owner = dev wallet (kill switch), consumer = Base gateway

### Cross-chain jackpot path → 4 failure points, 0 recovery (HIGH)
`core.requestJackpot()` → `adapter.requestRandomness()` → CCIP(RH→Base) → VRF request → `sendResult()` → CCIP(Base→RH) → `_ccipReceive()` → `fulfillJackpotRandomness()` → `selectAndAwardJackpotWinner()`
1. CCIP RH→Base lost → `activeRound.active=true` + `requestStartedByRound=true` → stuck, no retry
2. VRF request lost (subscription underfunded / coordinator error) → same
3. **`sendResult()` grief: `resultSendStartedByRound[roundId]=true` set BEFORE `ccipSend`**; if ccipSend reverts the flag is permanent → `ResultAlreadySent` forever (permissionless function — anyone can trigger the grief)
4. CCIP Base→RH lost → `responseMessageByRound` unset but core state stuck

Also: `allowOutOfOrderExecution: true` both directions → `_ccipReceive` replay/ordering race: `responseMessageByRound` set (line ~141) before external call `fulfillJackpotRandomness` (line ~142); fulfill revert rolls the whole tx back → CCIP relayer retries forever, gas burned, no dedup survives rollback.

### VRF subscription check recipe
```python
# Base v2.5 coordinator
# getSubscription(uint256) selector = 0xdc311dd3
# eth_call to 0xd5d517abe5cf79b7e95ec98db0f0277788aff634 with subId (32-byte padded)
# -> balance (wei), nativeBalance, reqCount, owner, requesters, consumers
```
Mainnet Base RPC (`mainnet.base.org`) rate-limits hard; use `https://base-rpc.publicnode.com` (worked).

### Blockscout v2 tx-history note
`GET /api/v2/addresses/<addr>/transactions` works plain. Adding `?filter=to | from` → HTTP 422. 0-tx address = dormant but capability live.

### Duplicateability verdict
All 4 contracts verified + source public → entire system replicable on any EVM chain (core + router + adapter + gateway + new VRF subscription). Deterministic invite codes make cloning easier, not harder. No secrets beyond the backend `requestSigner` private key.
