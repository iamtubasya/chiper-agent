# Worked example — LoopScale API engagement (2026-10-18)

Shape: Solana DeFi lending protocol, bug bounty by email (security@loopscale.com), rewards up to
$250k program / $50k app+services. Target surface = docs (Mintlify), markets API
(tars.loopscale.com/v1/markets, 126 endpoints from their openapi.source.json), on-chain program IDL
(palindrome-eng/loopscale-client), app bundle (Angular+Privy). Useful as the template for
"API-first DeFi bounty with an email channel".

## What produced findings

1. Pulled the program's own OpenAPI spec (`/api-reference/openapi.source.json` on the docs host) —
   126 paths with schemas, the complete endpoint map without guessing.
2. Probed every endpoint once (GET as GET, POST with `{}`), classified by response: 401 ApiKeyNotFound
   (write side key-gated), 401 User-Wallet (header-gated), 422 (reachable, no auth), 200 (open).
   Ran it as a background job with notify — 126 endpoints at 0.25s spacing exceeds the 60s
   foreground limit.
3. The auth map exposed the bugs: user-scoped endpoints accepting arbitrary `userAddress`/`wallet`
   with no credentials, and a `User-Wallet` header that is presence-only (no signature) — proven by
   setting the header to a random address (200 empty) and to a real address (200 with data).
4. Contrast anchor for the report: one endpoint (`/loans/toggle_position`) DID require a signature —
   proof the correct pattern exists in their codebase.

## Findings staged (3 drafts, one per finding)

- LS-01 Medium: BOLA on user-scoped endpoints (`/user/loans`, `/user/vaults`, `/user/strategies`,
  `/lending_vaults/user`, `/earn/portfolio/*` no-auth; `/lending_vaults/user_positions`,
  `/lending_vaults/deposit_summary`, `/portfolio/rewards`, `/user/genesis` header-presence-only).
  Evidence: another wallet's loan with healthRatio/ltv/liquidationThreshold/PnL verbatim.
- LS-02 Low: unauth server-side write `POST /earn/vaults/acknowledge` (consent-gate record).
- LS-03 Low: unauth read of internal RWA deals `GET /deals` + `/deals/{id}/valuations` (write side
  correctly X-Api-Key gated — the asymmetry is the report).
- Dropped LS-04 (NX_API_KEY in bundle): program OOS excludes secret reports without proof of active
  exploitation; key liveness not demonstraable.

## Evidence recipe that worked

- Local evidence server (`evidence_server.py`, pattern from `scripts/evidence_screenshot_server.py`)
  with one route per finding; each route performs the REAL request server-side at page render and
  prints request line + raw response. Headless Chrome screenshot per route, FRESH
  `--user-data-dir` per shot, `--virtual-time-budget=15000`.
- Ink check: PIL unique-grey count; content check: `--dump-dom` of the same route, grep for the
  expected token (healthRatio / acknowledged / navBaseUnits). A route that 500s during the DOM check
  after a "successful" screenshot means the screenshot caught the error — compare sha256 against a
  fresh capture of the current state to tell them apart.
- Re-validation: 3x per finding with dated raw captures into `evidence/LS-xx_reverify.txt`, plus a
  negative control (random unused address → empty) to prove responses are data-dependent.
- Staging: patched `stage_finding_draft.py` (see SKILL.md pitfalls) with `--attach` for the evidence
  txt + PNG; verified each draft by read-back (subject, attachment list, sha256 of every attachment),
  batch-asserted exactly N LoopScale subjects in ONE `messages.list(labelIds=['DRAFT'])` pass,
  `qa_pdf_layout.py --margin-mm 16` clean on all PDFs, `/Subtype /Image` present in PDF bytes.

## Engagement hygiene

- State changes on the target (the acknowledge writes) logged in ENGAGEMENT_LOG.md with exact bodies,
  timestamps, and which wallets were self-generated vs. observed; the LS-02 email body discloses the
  residue and offers it for cleanup. Use self-generated random base58 addresses for repeat write
  tests instead of re-using a real user's address.

## Deep-dive round 2 (same day, after the 3 findings were sent)

User instruction was "lanjut deepdive lg" — act like a hacker, find fund-level impact. Surface added:
`rpc.loopscale.com` (open Solana RPC found via subdomain DoH sweep) + full on-chain state. Techniques
are generalised in `bug-bounty` → `references/solana-onchain-forensics-and-idl-decoding.md`; the
engagement-specific outcomes:

- **LS-05 Medium (new, staged NOT SENT)**: single-key upgrade authority
  `7qNW6geC4uFv6Pi85mW3HFXMqYoyLvtK6VKi8UD2Xj8` on BOTH the core program and the BEAM oracle, while
  the docs promise a 3/5 multisig. The documented "multisig" `DwBXwJDZ…` is a plain wallet; the real
  Squads multisig `GLke7iqy…` (vault `AZxSvUwN…`) executes operations (loan creation via
  `VaultTransactionExecute`) but is not the upgrade authority. Extraction: program account
  data[4:36] → programdata, then [12:44] → authority; "account not found" = bare EOA key.
- **RWA/NAV analysis**: decoded the BEAM NAV oracle account (152-byte entries, 18-decimal prices, 33
  collaterals) and cross-checked against the deals API. On-chain NAVs match the last ACCEPTED
  valuation; the pusher refreshes timestamps on frozen values every ~30 min so the on-chain maxAge
  staleness check can never trip. Deal 1's accepted NAV was 87 days old with a -36.5% drop stuck in
  `held_for_ack`. Observation-grade: the only loans against those collaterals were 18
  protocol-created test positions (Squads-executed, whitelisted test borrower, smoke-test deals) —
  traced via the loan's single creation tx before claiming anything.
- **Health sweep**: 2,930 USDC loans + 21 dawn loans pulled via the indexed API; computed health for
  the top 40 borrowers via the (by then reported) no-auth user endpoints. Lowest health 5.1%, none
  underwater, no liquidations in the last 60 program txs — a clean negative stated in the report.
- **Scope discipline paid off twice**: LS-04 dropped (secret without exploitation proof) and the
  earn-vault program identified as third-party (Exponent-integrated, own upgrade key) before any
  time was spent on it.
