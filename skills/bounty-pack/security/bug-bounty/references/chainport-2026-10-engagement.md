# ChainPort (chainport.io) — cross-chain bridge, closed-source, no payable finding (2026-10-24)

Target: **ChainPort** — cross-chain token bridge (wrapped-asset / native / stablecoin bridging,
25+ chains, Cardano bridge). DeFi → fund-loss is the paid class.

## Program
- Own bug-bounty page `chainport.io/bug-bounty` (NOT Immunefi). Reward by **OWASP** severity:
  Low ≤$100 / Medium ≤$500 / High ≤$2,000 / Critical ≤$5,000 (stable or PORTX). Report via web form.
- **Scope (broad):** Contracts (logic flaws / financial breaches / upgradability), Protocol
  (crypto errors), Front-end (XSS/clickjacking/Web3), API (data/permission breaches),
  `app.chainport.io`, `chainport.io` + subdomains + mainnet.
- **OOS:** 3rd-party sites (unless ChainPort-specific), test-WIP envs, game-theoretic, known issues,
  unreproducible. Note: several subdomains are third-party CNAMEs (see negatives) → OOS.

## Surface map (don't re-derive)
- **23 subdomains** incl. many live dev/staging/preprod: `develop`, `next`, `preprod`,
  `preprod-legacy`, `prod-predeployment`, `staging`, `test` all 200 the bridge app;
  `prod-sandbox` → Cloudflare Access; `staging-api` key-gated. `update`→update.infoland.eu,
  `status`→status.infoland.nl (off-scope redirects).
- **app.chainport.io** = Next.js dApp (32 JS bundles), uses **Turnkey** embedded-wallet infra.
  Its own `/api/*` routes proxy the backend server-side (no client x-api-key):
  `GET /api/port/tokens` (200, token list), `POST /api/port/balances` `{walletAddress,tokens}`
  (public on-chain balances), `POST /api/bridge/quotes` (QuoteRequest, public calc),
  `GET /api/port/native-prices`. All public data — no IDOR/data-leak found.
- **api.chainport.io** = AWS API Gateway, `x-api-key` required ("Missing Authentication token").
  Key is server-side (not in client JS). S3 buckets `chainport-public-files-prod` /
  `chainport-frontend-resources-prod` → 403 (secured, no list/write).

## Contracts — the money path, and why it's blocked
- **Vaults** (lock/mint) per chain from the `/transparency` + `/security` pages. Ethereum Vault
  proxy `0xca9a74c22f0a2eb91909d59a98f48f9357499a46` → impl `0xa3e950bf…`; Deployer
  `0xfe834758…`. Roles readable: `bridge` `0x…d02c8a35`, `gateKeeper` `0x…26ab6291`,
  `validator` `0x…c97c01ab`; `paused()=false`.
- ⛔ **Closed-source:** Vault + Deployer + impl all **unverified** on Etherscan, and heimdall
  `--include-yul/--include-sol` (beta) produced nothing. So the fund-loss logic (validator-signature
  verification, replay protection, deposited-vs-withdrawn accounting, wrapped-token mint authority)
  **cannot be source-audited**. Technique that DID work → `smart-contract-audit` →
  `references/unverified-contract-abi-ethcall-recon.md` (heimdall ABI + eth_call access-control sweep).
- **Access-control result (solid, a real negative):** all **16 state-changing** functions
  (`setBridge`/`setGateKeeper`/`setChainportCongress`/`setMaintainersRegistry`/`freeze`/`unfreeze`
  + the `Unresolved_*` deposit/withdraw variants) **REVERT** from an arbitrary address → no
  unprotected state-changing function. Named admin getters return role addresses.

## Verified negatives (close the surface, don't re-litigate)
- No reflected XSS on app/staging/`/portal/start` (SPA shell). No secrets in staging JS bundles.
- No subdomain takeover (CNAMEs → live: flowmailer/stape.io/lagrowthmachine/homerun/fastly/iris).
- No injection (quick_codes/field_id/username parameterised, error+time-based both clean).
- No CORS exploit (WP n/a here; app API is JSON, no reflect+creds cookie surface).
- Wrapped-token API field `tokens_to_be_approved_by_exact_user_amount` is a spender/approval
  target, NOT the wrapped token — COPI's EVM addr resolved to an unrelated verified ERC20
  ("XNLToken"); verify a token contract references the bridge before auditing it as the minter.

## Re-hunt unblock (the ONE thing needed)
The fund-loss audit needs the **contract source** (GitHub internal / deploy artifact / a verified
deployment). Without it, the honest deliverable is the access-control-solid negative + the
closed-source barrier — never "audited, no bugs". A Foundry dynamic/fuzz pass against the deployed
bytecode is possible but limited without a full ABI.
