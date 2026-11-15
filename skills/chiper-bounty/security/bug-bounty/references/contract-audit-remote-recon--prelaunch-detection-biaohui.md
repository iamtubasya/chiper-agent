# Pre-Launch Detection — Worked Example: BIAOHUI (標會) on Robinhood Chain

Session 2026-08-18. Target picked at random from a 57-project list (UPONZI excluded as already
audited). Result: target was NOT deployed anywhere — a 30-min pass that correctly ended with
"BELUM DAPAT DIAUDIT" instead of a fake contract audit.

## Evidence chain that proved pre-launch

1. **Explorer search** `GET /api/v2/search?q=Biaohui` → 24+ token hits (biaohui, BIAOHUIv2, v3,
   HUI) — all `token` type, no protocol contracts. Quirk: every hit printed `address: None`
   under the `address` key; filter by `name`/`type` not by address.
2. **Blockscout address checks** of token contracts: 2–15 tx each, `is_contract: True`,
   `is_verified: False` — test tokens, not a live protocol.
3. **Frontend JS bundle** (`https://www.biaohui.xyz/_next/static/chunks/*.js`):
   - `performance.getEntriesByType('resource')` listed 22 chunk URLs; curl'd all to
     `biaohui_js/`. Next.js app router → no `window.__NEXT_DATA__` (that's pages-router only).
   - `grep -oE '[a-zA-Z0-9_]+:"0x[0-9a-fA-F]{40}"' 04e9707cc6f3e03d.js | sort -u` dumped the
     full deployment map: `deployer:"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"`,
     `poolManager:"0x5FbDB2315678afecb367f032d93F642f64180aa3"`, staking/treasury/bonds all
     hardhat default addresses.
   - Deployment map keyed ONLY by `31337:{...}` → hardhat local. `NEXT_PUBLIC_CHAIN_ID`
     defaults to 31337 → frontend connects to a local node.
   - Homepage literally renders "Chain 31337 is not answering."
4. **Blockscout address lookups** of the bundle addresses: `is_contract: False` (some had tiny
   RH balances — unrelated EOAs), and `0x998abeb3...` (calendar) `is_contract: True`,
   `is_verified: False`, 0 tx — i.e. an early unverified test deploy at best.
5. **Repo check**: website SOURCE link → `https://github.com/99mitch/biaohui` → 404
   (private/deleted). No public source to audit.

## Hardhat deterministic addresses cheat-sheet (bundle forensics)
| # | Address | Usual role |
|---|---------|-----------|
| 0 | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` | deployer / account[0] |
| 1 | `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512` | first deployed contract |
| 2 | `0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0` | second |
| 3 | `0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9` | third |
| 4 | `0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9` | fourth |
| 5 | `0x610178dA211FEF7D417bC0e6FeD39F05609AD788` | fifth |
| 6 | `0x8A791620dd6260079BF849Dc5567aDC3F2FdC318` | sixth |
| pool | `0x5FbDB2315678afecb367f032d93F642f64180aa3` | (Uniswap v4) PoolManager |

If a bundle's address map is entirely these, the dapp is pointed at a local test deployment.

## Chain-ID constants seen (don't chase these as project contracts)
- `0x2105` = 8453 Base; `0x14A34` = 4663 Robinhood. Appeared inside EIP-5792
  `wallet_getCapabilities` paymaster-service responses in the wallet-connect library chunk —
  wallet infra, not the protocol.
- Generic `swap()` (`0x4d819a2a`) proxy `0x65050A9b...` with 50 tx from many wallets = DEX
  aggregator infra, NOT the audited project.

## Design-level risks worth noting even pre-launch (from public docs)
- OHM-style reserve backed by tokenized equities (TSLA/NVDA/AAPL): "backing per $HUI never
  decreases" claim depends entirely on pricing oracle + treasury management; equity volatility
  → bank-run risk if backing price gaps.
- Session-aware fee (5 bps open / 30 pre+after / 100 closed / 200 earnings override): whoever
  controls the earnings flag can manipulate fees — flag governance is an audit question.
- Bond early-exit penalty 20% to stakers: pricing-oracle error amplifies into penalty
  arbitrage.

## Verdict template for pre-launch targets
"BELUM DAPAT DIAUDIT — kontrak belum deployed di mainnet (masih hardhat local), source
private/404. Rekomendasi: tunggu mainnet deploy + source verified, lalu audit ulang; atau
random-pick project lain dari list."
