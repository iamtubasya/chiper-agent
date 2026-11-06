---
name: agentic-free-mint-hunt
description: Use when hunting free agent-id mints on BSC. Auto-mint.
metadata:
  author: RESEARCHER_NAME
  version: "1.0.0"
---

# Agentic Free-Mint Hunt (BSC)

Hunt + auto-mint free/gas-only Agent-ID-gated NFT mints on BNB Smart Chain.

## Context / sources
- Telegram ".ai agentic binance" is NOT a standalone group — it is TOPIC 1470154 inside CVC forum
  (`-1002103131992`, 45 topics). Related: 1498052 "Agentic Binance Chat", 263164 "AI AGENT".
  `t.me/c/2103131992/<msgid>` → peer `-1002103131992`.
- beastfarmer radar: `https://beastfarmer.xyz/monitorbnb/api/status` (GET no auth) →
  `detected_contracts`, `minted_contracts`, `feed`.
- Wallet `0xEa6a67dB6B6d595Da60111C39b72C74028FF7C62` (BSC). Agent ID `BC_USERNAME.ai`.

## Operator rules (final)
1. FREE / gas-only mint ONLY — never paid (PRICE/mintPrice>0 = skip).
2. recall >= 3 in the group (was 2, then 4, final "3 ke atas" = ≥3).
3. Auto-mint: `baw contract-call preview --value 0`, execute ONLY if sim success AND Erc721 change.
4. Skip if `balanceOf(me)>0`.

## Key tooling (this host)
- baw CLI = `C:/Users/WINDOWS10/AppData/Roaming/npm/baw.cmd` — Python subprocess MUST use .cmd, not bare `baw`.
- Telethon python = `C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe` (NOT uv/hermes venv).
- Etherscan V2 key: `C:/Users/WINDOWS10/AppData/Local/hermes/secrets/etherscan.key` →
  `https://api.etherscan.io/v2/api?chainid=56&module=contract&action=getabi&address=<ca>&apikey=<key>`.
- BSC RPC: `https://bsc-dataseed.bnbchain.org`, fallback `https://bsc-rpc.publicnode.com`.
- TG session: `C:/Users/WINDOWS10/telegram_scraper/tg_scan_session` (API_ID 2040).

## Wallet reconnect (drops silently)
`baw wallet status` → UNCONNECTED/NOT_LOGGED_IN ("illegal parameter" + UV_HANDLE_CLOSING crash).
1. `baw auth signin --json` → qrCodeId + pairingCode + urlForWeb.
2. QR PNG: `qrcode.make(url).save(path)` (needs pillow) → send MEDIA.
3. `baw auth verify --qrCodeId <id> --json` — blocking ~5min, run BACKGROUND.
4. Confirm `wallet status`=CONNECTED and `devMode.enabled`=true (`wallet settings`).

## Mint selectors (try in order)
```
mint()         0x1249c58b
freeMint()     0x5b70ea9f
claim()        0x4e71d92d
mint(1)        0xa0712d68 + 0*63 + "1"
mint(2)        0xa0712d68 + 0*63 + "2"
mint(3)        0xa0712d68 + 0*63 + "3"
mint(1,0x0)    0x94bf804d + 0*63 + "1" + 0*64
```
Many are unverified → no ABI; selector-guess via preview simulation is the only way.

## On-chain eligibility (eth_call)
name() 0x06fdde03 · symbol() 0x95d89b41 · totalSupply() 0x18160ddd · totalMinted() 0xa2309ff8 ·
mintOpen() 0x24bbd049 · freeMintOpen() 0x777fa9ab · FREE_SUPPLY() 0x9858cf19 · freeClaimed() 0x1b47ec3a ·
freeLeft(a) 0xeb28217e · freeAvailable(a) 0x9a5f5d31 · canFreeMint(a) 0xd5b78380 · mintedBy(a) 0x3cef28d2 ·
PRICE() 0xa035b1fe · mintPrice() 0x6817c76c · balanceOf(a) 0x70a08231
- exhausted = freeClaimed==FREE_SUPPLY → skip.  paid = PRICE/mintPrice>0 → skip.
- **feed `free_left` is MISLEADING**: it counts total remaining supply, NOT your claimable
  free quota. Always read on-chain `freeClaimed()` vs `FREE_SUPPLY()` AND `freeLeft(me)`.
- **`mint_fn=None` in feed is NOT dead**: many free mints (the "gent" family — Dronegent,
  Hackagent, Plasmagent, Terragent, Hexagent, Kappaxis, Deltavane, Sigmora, Thetavox) report
  `mint_fn=None` but use standard `mint(uint256)` with value=0 and still have feeLeft(me)>0.
  FALLBACK: when fn is None, try `mint(uint256)` qty 1 (0xa0712d68 + 0*63 + "1").
- scan the FULL detected_contracts + minted_contracts, verify on-chain free tier per-contract,
  do NOT rank by seen_count only (that surfaces old sold-out contracts first).

## Recall counting (group)
Scan topics with Telethon (iter_messages reply_to=tid, limit=None), regex `0x[a-fA-F0-9]{40}`,
count per CA, fold all 3 topics.

## Cron
Job `a76daa8ebc45` — `agentic_mint_monitor.py` (v4.1), no_agent, every 5m, deliver origin.
State `agentic_mint_state_v4.json` (NOT the old v1 state). MIN_RECALL=3, FLOOR_BNB=0.00012.

## Pitfalls
- subprocess MUST call baw.cmd (not baw).
- preview requestId expires ~5min → re-preview before execute.
- gas ~0.05 gwei → ~0.000006–0.00001 BNB/mint (~175 capacity on 0.0013 BNB).
- some are ERC20 (e.g. BOSS) → minted but no Erc721 in balanceOf.