# LoopScale engagement (2026-10-18) — Solana lending protocol, API-first audit

Target: LoopScale — modular order-book lending on Solana.
- Docs: `docs.loopscale.com` (Mintlify) · API: `tars.loopscale.com/v1/markets` · App: `app.loopscale.com` (Angular+Privy) · `case.loopscale.com/v1/{mpc,ruby,pandora,endurance}`
- On-chain: Core `1oopBoJG58DgkUVKkEzKgyG9dvRmpgeEm1AVjoHkF78`, BEAM oracle `beamVVkNmKeXcuZ6zLpC9eM5YgVyAn4Z9xdPrz3gCW2`
- Program: `security@loopscale.com`, up to $250k Program / $50k App+Services (Medium $10k/$5k, Low $2.5k/$500). Scope explicitly includes **internal API endpoints + supporting backend infra** — the API is first-class scope, not a side quest.
- Prior audits: Adevar Labs ×7 (2025–26), sec3 + OShield (V1, private), Highland. Contracts mature → spend the budget on API/backend + live config state.

## Recon path that worked (Mintlify playbook)
1. `curl https://docs.loopscale.com/llms.txt` → full page index (every doc page listed with `.md` URLs).
2. Every Mintlify page has a clean markdown twin: append `.md` to the path (`/resources/audits.md`, `/api-reference/.../x.md`). No browser needed for docs recon.
3. `https://docs.loopscale.com/api-reference/openapi.source.json` → **full OpenAPI 3.1 spec, 126 paths**, incl. server base URL. Whole API attack surface in one file.
4. GitHub recon: program source is NOT public; the IDL is — `palindrome-eng/loopscale-client` (codama-generated Rust+TS clients: 42 instructions, 150 error codes, all account structs). `orca-so/loopscale-pricing-adapters` turned out to be a DefiLlama TVL adapter, NOT the lending oracle (BEAM on-chain is the pricing authority) — verify what a repo actually is before deep-reviewing it.
5. App bundle (`app.loopscale.com/main.*.js`): grep for base URLs → found `case.loopscale.com/v1`, service map (mpc/ruby/pandora/endurance/napoleon/arrakis/syndicated/bsMetadata), staging Cloud Run URL, `NX_API_KEY`, Privy/Mixpanel IDs.

## API auth-model mapping (reusable — script: `scripts/api_auth_map.py`)
Probe every spec path with an empty body (`{}` for POST) and classify:
- `200` → open · `401/403` → gated · `400/422` → **reachable WITHOUT auth** (validation error = the handler ran) · `429` → rate-limited (back off, re-run subset).
**Error-message differential discovers the auth header name**: send a dummy value under candidate headers; `ApiKeyNotFound` (absent) vs `Invalid or disabled API key` (present-but-wrong) pinned `X-Api-Key` on `/deals/submit`.
LoopScale auth model found: `X-Api-Key` gates partner writes (deals/valuations); `User-Wallet` header gates user-scoped reads; **one endpoint (`/loans/toggle_position`) does it right with a wallet signature** — cite the correct in-app pattern as the contrast in the report.

## The BOLA class on Solana dApp backends (LS-01, Medium)
`User-Wallet` header = **presence-only, no signature/ownership verification**. Endpoints with no gate at all (`/user/loans`, `/user/vaults`, `/user/strategies`, `/lending_vaults/user`, `/earn/portfolio/*`) and header-gated siblings (`/lending_vaults/user_positions`, `/deposit_summary`, `/portfolio/rewards`, `/user/genesis`) all return any wallet's full portfolio: loan health ratios, LTV, liquidation proximity, PnL, staked LP, rewards. Random wallet → empty 200 (no ownership oracle). Verified 3×.
Impact framing that survives triage: raw chain data is public, but the API exposes **computed off-chain analytics** (health ratio, PnL, reward USD) and removes enumeration friction → systematic liquidation targeting/MEV + privacy loss. Enabler, not direct theft — calibrate Medium, don't inflate.

## Other findings
- LS-02 (Low): `POST /earn/vaults/acknowledge` — unauthenticated server-side state write; acknowledged deposit terms for a wallet not controlled. Log the state change in ENGAGEMENT_LOG.md (idempotent one-way flag, can't self-revert → must disclose).
- LS-03 (Low): `GET /deals` + `/deals/{id}/valuations` — internal RWA partner data (SPV IDs, NFT mints, NAV history) readable without the API key that gates the write side.
- LS-04 (Low): app bundle leaks `NX_API_KEY` (Nx Cloud — may grant remote-cache/source access, verify org perms), internal service topology, staging URL.

## On-chain black-box checks (no program source)
- **IDL signer scan**: parse each codama instruction's `AccountMeta::new(self.X, true|false)` pushes and flag authority/manager/admin fields that are NOT signers. LoopScale: clean (all real authorities sign; `event_authority` non-signer is the normal Anchor event PDA — do NOT flag it).
- **Live config anomaly analysis**: `POST /oracles/data/market_informations` → 97 markets / 1,553 asset configs; check lqt≤ltv (none), thin buffers, maxAge extremes (`loopscale_nav` maxAge=65535 ≈ 18h — by design for NAV reporting cadence), maxUncertainty extremes (one 40% asset, but ltv=0 → harmless direction), aggressive LTV on verified markets (mkt 87: 98% LTV / 99% LQT on NAV collateral — observation, not a bug).

## Verified negatives (write them down)
- `/prices/external/{symbol}` strict allowlist (BTC/ETH/SOL/AAPL/xStocks all "Unknown external price symbol") → no SSRF via symbol.
- Staging Cloud Run (`markets-beta-vmyhi2huoa-uc.a.run.app`) — dead revision, Flask 404 on every path.
- `case.loopscale.com/v1/mpc|ruby` → 503 (exist, currently down); `/endurance` → OK.
- 150 error codes show mature on-chain checks (slippage, oracle staleness/uncertainty, weight-matrix, caps).

## Pitfalls hit this session
- **126-endpoint probe 429s** (`Rate limit exceeded (quotes:ip)`) partway → run the probe as a background process with notify_on_complete, ≥0.25s spacing, and re-run the 429'd subset after cooldown. Per-IP quote rate limits are tight.
- **Heredoc containing `&` (e.g. "App & Services") makes the terminal tool refuse the command** (backgrounding detection) → write files via `python3 << 'PYEOF'` instead of `cat > file << 'EOF'`.
- `web_extract` failed (ddgs search-only backend) and Camofox wasn't running → plain `curl` for docs/API reads is fine and fastest for static pages; don't burn time on browser bring-up for docs recon.
- `/user/loans` response shape switches on `orderFundingTypes` (Generic→`loanGroups`, Loop→`loopGroups`); a Loop-type borrower returns EMPTY under the default filter — set `orderFundingTypes: 2` or you'll false-negative the endpoint.

## Round 2 — on-chain forensics via the discovered open RPC (LS-05, Medium)
- **`rpc.loopscale.com` is an open Solana JSON-RPC** (found via DoH subdomain sweep; `{"error":"Method not allowed. Use POST JSON-RPC."}` on GET). Use it for all on-chain reads: getProgramAccounts, getAccountInfo, getTransaction, getSignaturesForAddress.
- **LS-05 (Medium, sent): single-key upgrade authority vs documented 3/5 multisig.** Read the program account (36 bytes) → programdata address at bytes 4–36 → fetch programdata → upgrade authority at bytes 12–44. Core AND BEAM oracle both have `7qNW6geC4uFv6Pi85mW3HFXMqYoyLvtK6VKi8UD2Xj8` — a bare pubkey whose account was never initialized (= standalone EOA keypair, not a Squads vault PDA). The documented "Multisig Authority" `DwBXwJDZ…` is itself a plain system wallet (0 data). A REAL Squads multisig exists (`GLke7iqy…`, SQDS-owned, vault `AZxSvUwN…`) and executes operations (loan creation via `VaultTransactionExecute`) but does NOT control upgrades. Docs claim "All program upgrades require approval from a 3/5 multisig" → docs-vs-on-chain contradiction is the finding. Impact: one key replaces lending logic + price oracle → drain everything.
- **NAV oracle account decode**: `H84M3es89eLfGRDhUFxo7xgTQmhzAx4h2oBexU7WNiGN` (BEAM-owned, 76,656 B) holds all 33 RWA collateral NAVs as **152-byte entries** (32-B mint pubkey, 18-decimal fixed-point price at +32, duplicate value at +56, unix ts at +80). Cross-check vs `/deals/{id}/valuations`: on-chain NAVs match the last ACCEPTED valuation; `held_for_ack` submissions are NOT pushed. `WritePriceEntry` instruction data is just an 8-byte discriminator — the price comes from the referenced account, signed by a single pusher key `4jHcKHTfb7…` batching ~4 writes/tx every ~30 min (documented centralization, not a finding).
- **Instruction co-sign map**: parse all 42 codama instructions' signer flags → 40/42 require `bs_auth` (Secrets Manager co-sign); only `liquidate_ledger` skips it (by design — liveness) and `update_market_information` (protocol admin). No bypass. All 39 protocol-verified markets share one authority key `BBEPbsJAM5ec…` for parameter updates (same centralization theme as LS-05, noted as observation).
- **Health scan**: pulled all 2,930 USDC loans + 21 dawn loans via `/loans/core` pagination; computed health for the top 40 borrowers via the (BOLA) `/user/loans` endpoint — lowest health 0.036, zero loans < 0.02 → liquidation engine keeping up. Clean negative.
- **The 18 RWA loans** (1 NFT vs $20k–$200k principal) looked impossible until tx tracing showed they were created via Squads `VaultTransactionExecute` — protocol-created bootstrap/test positions for the whitelisted test borrower (smoke-test deals). Not user flow, not a finding.
- **Borsh Loan account decode validated** against a known loan (1,634 B: disc/version/bump/status, borrower, nonce, 5×Ledger(182 B), 5×CollateralData(73 B), 3× 5×5 u32 matrices). Write a decoder and validate against API data before trusting it.

## Round 3 — negatives (record so the next pass skips them)
Web app bundle: no postMessage handlers, stock Privy SDK, routes only `/`, `/waitlist`, `/testing`(404). Marketing site (Next.js+Cloudflare): `/_next/image` strictly allowlisted (own favicon 400s; 169.254.169.254 blocked at edge), no server actions, no /api routes. Injection battery on open endpoints (SQLi/Log4Shell/SSTi/traversal): clean — invalid base58 treated as no-match. `/timelock/list` empty. Quote engine `priceOverride` is a by-design simulation input (on-chain guards protect). Earn vaults run on a third-party program (`sVau1tX…`, Exponent-integrated, own upgrade key) — OOS third-party. LS-04 dropped: program OOS excludes secret reports "without proof of active exploitation" (NX key liveness not demonstrable — api.nx.app doesn't resolve).
