# Immunefi Blockchain/DLT program mechanics (reference)

Notes taken from a live Immunefi program page (Hedera, 2026-10). Reusable for any Immunefi
Blockchain/DLT engagement — read the actual page each time, the numbers move.

## Reading the program page

- The page is a **server-rendered Next.js app**. `web_extract` may be pointed at a
  search-only backend and refuse; use `curl` to fetch the HTML, then strip tags with a small
  Python filter. Relevant tabs:
  - `/bug-bounty/<project>/information/` — overview, rewards, prohibited activities, KYC, SLA
  - `/bug-bounty/<project>/scope/` — the asset list + impacts-in-scope table
- Grep the raw HTML for asset links: `grep -oE 'https://github.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+'`.
  For a codebase program the assets ARE repo URLs (that's the signal it's a **codebase track** —
  no live host, and see the prohibited-activities clause below).

## Typical shape

- **Assets**: 5–8 GitHub repos (services codebase, mirror node, RPC relay, crypto library, SDKs).
- **Rewards by threat level** (Blockchain/DLT): Critical band (e.g. $10k–30k), High ($3k–10k),
  Medium flat, and a much smaller Web&App band (often Low only, ~$50–100).
- **Vault program / Primacy of Rules**: rewards paid from a vault in a stablecoin; some Criticals
  are "10% of funds directly affected, capped at $X, min $Y".
- **KYC required** for payout; **PoC always required** for all severities.
- **Response SLA** per severity (ack+triage, resolution+payment).

## Prohibited activities (read these BEFORE any tool fires)

- **No testing on mainnet or public testnet** — "all testing on local forks". This alone forces the
  codebase/white-box track for node/protocol repos; scanners are N/A.
- No DoS against project assets; no automated testing generating significant traffic.
- No phishing / social engineering against employees or customers.
- No testing third-party systems (oracles, SSO, browser extensions).
- No public disclosure of an unpatched/embargoed bug.

## Impact tiers (Blockchain/DLT — the ones that pay)

- **Critical**: direct theft of funds; unintended permanent freezing of funds; total network halt;
  network partition outside design params; material impact from tampering with hashgraph history.
- **High**: temporary freeze/delay of transactions; preventing gossip; reorg without direct theft;
  authorizing transactions without signer approval.
- **Medium**: +30% node resource consumption; halting ≥30% of nodes; incorrect/missing records
  exported to mirror nodes (authoritative records only).

## Downgrade clauses you must pre-empt IN the report

Quote them yourself and apply the honest severity, rather than letting the triager discover them:

- **Functionality Not Active in Production** — if the bug is behind a feature flag (`x.enabled=false`),
  severity may drop ≥1 level, but the report is still in scope and "encouraged".
- **Privileged-account vectors** — attack vectors requiring a team account, a roster-admitted node or
  an authenticated gossip connection may be downgraded or N/A'd.
- **Network-Impact Proof** — impact proven on a single node (or a reconnecting node) is out of scope;
  it must be network-wide.
- **Economic Viability** — if the attack costs more than it can extract, downgrade/N/A.
- Feasibility limitations (chain rollbacks, pre-impact monitoring, attacker financial risk) are defined
  separately — read them before claiming severity.

## Practical consequence

For node/protocol codebases the winning shape is a **white-box source review** (see the parent skill):
clone the in-scope repos, find an isolated defect in a security-critical path, and prove it with a PoC
that drives the real production entry point — then report with self-applied downgrade clauses.
