# TxFlow testnet perp-DEX engagement (2026-10) — worked case

Self-contained record of a full engagement against a perp DEX testnet with a signed order API.
Use as a template for the recon → client → test-grid → report chain; reuse the negatives so the
next pass skips them.

## Target shape

- App `txflow-testnet.xyz` (Cloudflare, SPA). API host `testnet-api.txflow-testnet.xyz`
  (also `rpc.txflow-testnet.xyz`). Wallets via Privy. Docs `docs.txflow-testnet.xyz`.
- **Docs expose `llms-full.txt` (~400 KB)** — the whole API + EIP-712 signing contract + the
  MessagePack/minimisation rules + **published test vectors**. This was the single most valuable
  artefact; always try `/llms-full.txt`, `/llms.txt`, `openapi.json` first.
- Endpoints: `POST /info` (unsigned reads) · `POST /exchange` (signed writes) ·
  WS `/ws`, `/api-ws`. 88 perp instruments + 378+ live **outcome (prediction) markets** on a
  partner channel.
- **Public bug bounty in the docs** (`/resources/bug-bounty`): up to **150 000 USDC Critical**,
  testnet explicitly in scope, `<email>` contact, direct submission (no platform).
  → Always check the docs' own `resources/bug-bounty` page before assuming a target is unpaid.

## Recon chain that worked

1. `curl` root HTML → `/assets/*.js` → grep `VITE_*API*` / `wss://` / `https://*-api*` → both API hosts.
2. `docs.*/llms-full.txt` (or a docs `/llms.txt`) → complete spec: domain `TxFlow-Testnet`
   chainId `2511`, `Agent(...)` struct, msgpack rules, test vectors, `/info` types, `/exchange` actions.
3. Rendered docs hide the request schema behind `<ExchangeBody field="order|orders"/>`; the field
   name lives in the per-page doc chunk `assets/<action>-<hash>.js` and in
   `/.vocs/search-index-<hash>.json` (`storedFields`). Reading `field="order"` (singular fixed
   `modify2`) vs `field="orders"` avoided `invalid request`.

## Account / capital flow (all legit testnet actions)

- Keys: `ethers.Wallet.createRandom()`-equivalent in Python; each account = main key + agent key.
- **Faucet `POST /request-fund {address}`** → **999 USDC, no email, per-address**. Fresh throwaway
  addresses each get 999 → generate N, claim, then `tokenSend` (direct `SendToken`) into the
  working account. Turned a 999 cap into ~$7 900 working capital.
- **Order of operations matters:** funding must precede `approveAgent` (on an unfunded account it
  returns `Account not found`). `tokenSend` is **owner-signed** (agent can't move funds).
- Sub-accounts: **perp** and **outcome** are separate; the outcome market needs collateral moved
  in via `tokenSend {fromAccountType:'perp',toAccountType:'outcome'}`.

## The finding — false acknowledgement → locked funds (reported)

- Sell price floor = **0.846 × oracle**; fills are on the **book**. On illiquid markets the oracle
  sat **+43…+76% above** the traded mark (HYPE +42.9, LDO +56.0, JUP +75.6 measured; BTC/CRO ~0.1%),
  so the book was far below the floor.
- Every reduce-only close was accepted (`{"status":"ok","statuses":["success"]}`) then cancelled:
  `historicalOrders` → `cancelSource: CancelByPriceLimitRule` (`price moved beyond slippage
  protection`) for market orders, `CancelByReduceOnlyPrice` for the limit-at-floor variant.
- Result: the position could be **neither closed nor liquidated** (deposit bonus kept ratio > 1)
  — collateral permanently inaccessible. Reproduced **3/3**.
- Reported as **Medium** (CVSS `AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H`, 6.5), honestly bounded to
  testnet. Deliverable: PDF + Gmail draft (one finding = one draft), contact from the docs page.
- **Same shape seen in 3 surfaces** (market close, outcome IOC `ok`+traceId with no position,
  order submit `ok` but not resting) → **one root cause, one report**.

## Liquidation / margin experiments (result: engine correct)

- Margin ratio `(margin + uPnL) / (notional·MMR + notional·feeRate)`; MMR is **tiered by size**
  (`perpMetaDetail` → `marginTable.tiers[]`). Partial liquidation is documented from **tier 3 up**,
  reducing to the tier-below cap.
- Mechanism that produces a controllable liquidation: opening a **long at the ask** when the mark
  is dislocated downward makes the position instantly negative (`uPnL = size·(mark−entry)`), so a
  small position can be driven below maintenance; engine closed it (full) and reduced size in
  another run — i.e. behaved as designed, no full-instead-of-partial bug proven.
- Price bands are **side-specific**: measured sell floor `0.846×oracle`, buy cap `1.05×oracle`
  (ratio 0.846/1.05 ≈ 0.805 vs the 0.8 config constant); market orders can execute below the
  stated limit band via a separate slippage rule, but a `CancelByPriceLimitRule` still fires.
- To hit a narrow band, **control equity**: `withdrawable = equity − marginUsed`; drain via
  `tokenSend` to a throwaway address, recompute `E_target = size·(ask−mark) + ratio·size·mark·(mmr+fee)`
  from the **real tier mmr**, then `updateLeverage` and open.

## Negatives (verified — do not re-run blindly)

- **`/info` cross-user reads** (positions/fills/balances by address, no auth): by design
  (all wallet tx are public, Hyperliquid-style). More sensitive types (`userFunding`,
  `userLedger`, `vaults`, `leaderboard`, `users`, `stats`) correctly return **403**. **No PII**
  (no email/IP/API key/KYC field). No user enumeration. → not a finding.
- **`outcomeOperate` split/merge**: split → two hedge legs at 0.50 with collateral frozen;
  merge capped by leg size; **concurrent double-merge is idempotent**; cross-market split does
  **not** double-spend (2×100 froze 200). Settlement paid 1.0/share for the winning leg. Correct.
- **Concurrency**: 10 concurrent `tokenSend` of 0.25× balance each → 5 succeeded (= exactly
  2.5× balance) then rejections; balance → 0, **never negative**. 8 concurrent resting orders of
  ~1× equity → **1 accepted** (margin reservation consistent). No over-commit race.
- **`modify2` reducing-only bypass**: `modify2 {order:{o,p,s}}` increasing an RO size to 4×/20×
  the position returns `success` but the order **stays at position size** (engine caps). Reprice
  and size-reduce work. → not a bypass (but another instance of the false-ack class).
- **`withdraw3` boundary**: over-balance and below-min (2 USDC) both rejected correctly (once the
  correct `Withdraw3` struct + a supported chain id are used).
- **Input validation**: size 0 / negative / 1e30, price 0 / off-tick all rejected with specific
  messages. Ordering/halt checks present.

## Pitfalls that cost time here

- Wrong MMR guess (0.0156 vs real 0.0106) → margin ratio stayed > 1 → a whole test round invalid.
- A monitor read returning `null` mid-poll was misread as "position closed" → retracted a wrong
  "always full-close" conclusion. **Re-read before concluding a state change.**
- Ticks: `0.0001` enforce; `f"{px:.10g}"`-style formatting can violate tick → format to the tick.
- Faucet/consensus latency: after `request-fund`/`tokenSend` a read can return the pre-credit
  balance for ~2-4 s; re-poll.
