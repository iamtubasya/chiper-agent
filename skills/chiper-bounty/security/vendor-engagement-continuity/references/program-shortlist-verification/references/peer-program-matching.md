# Worked case — "cari target dalam pool yg mirip seperti runonflux" (2026-10-25)

Reference target: **RunOnFlux** (`runonflux.com`) — Web3 cloud: decentralized GPU/CPU compute,
node marketplace, app hosting, own blockchain, email-only bounty. Prior engagement's paid finding
was a **medium `postMessage("*")` WebAuthn-assertion leak in a web app** (`passkey.runonflux.com`),
not a contract bug. That single fact drove the whole match.

## Query ladder and what each rung yielded

Pool: `D:/data hermes/target-pool/pool.json`, **35,633 rows**.

| query | yield | verdict |
|---|---|---|
| `search runonflux` / grep the raw JSON | **0** | the reference target is NOT in the pool — match by shape |
| `search flux` | 8 (`bitflux.ch`, `creditflux.com`, `fluxcd.io`, `fluxer.app`, …) | **all noise** — shared letters only |
| 53 hard-coded DePIN peer names (akash, io.net, golem, phala, aethir, nosana, ankr, pocket, storj, arweave, livepeer, quicknode, alchemy, filecoin, crust, subsquid, celestia, eigenlayer, fly.io, koyeb, railway, northflank, coolify, caprover, elestio, fleek, spheron, runpod, lambda, coreweave, replicate, pinata, nft.storage …) | **3 present** | `nosana.io` (monetary), `chainstack.com` (vdp), `hivenet.com` (monetary) |
| fuzzy stem match on those 53 stems | 7, mostly wrong | `render.com` (VDP for a different company), `golem.de` (German news site), `pocket`/`graph` matched `pocketsmith.com`, `graphite.io`, `innography.*` |
| `reward_type=monetary` + ≥2 infra/crypto words anywhere in scope/company/reward_text | **3** | `iceline-hosting.com`, `knowledge.nextcloud.com`, `storage.googleapis.com` (k8s) |
| `web3=True` + `monetary` | **141** | nearly all wallets/DEXes/exchanges — saturated, unusable |
| `web3=True` + `monetary` + scope mentions a web surface | **19** | readable; this is where the real shortlist came from |

**Lesson:** the wide crypto filter (141) is not a superset that you filter down by eye — it is a
*different population*. The infra-word query surfaced candidates (`hivenet.com`, `iceline-hosting.com`)
that the crypto filter never ranked, and the crypto filter surfaced most of the eventual top five.
Run **both** and merge.

## Verified verdicts (all fetched live, 2026-10-25)

| domain | shape | scope includes web? | reward | verdict |
|---|---|---|---|---|
| `docs.obol.org` | distributed-validator infra, Charon middleware, DV Launchpad, public relay | ✅ Launchpad + Public API (both 200) | **Critical $50k** / High $5k / Med $1k / Low $250 | **LIVE** — top pick; closest architecture peer |
| `hivenet.com` | cloud storage + GPU/CPU rental + inference console — the *product* is nearly identical | ✅ in-scope asset table: `app.hivenet.com`, `send.hivenet.com`, `console.hivecompute.ai`, + mobile/desktop apps | Critical $500 / High $250 / Med $100 / Low $50 | **LIVE** — pool said `retired`, that was STALE; policy dated Sep 24 2026 |
| `chainflip.io` | Rust backend + Solidity + web apps (scan/swap/auctions/validators) | ✅ scan + swap both 200 | discretionary, paid in FLIP | **LIVE** — note: policy has an explicit **AI-submissions paragraph** demanding concise verified reports |
| `nosana.io` | GPU compute DePIN — direct product peer | ❌ scope = "Nosana on-chain programs (Solana)" only | up to 10% value-at-risk, max $100k in NOS, **locked 12 months** | LIVE but weak fit for a web-app-shaped hunt; `app.nosana.io` = 401 login wall |
| `iceline-hosting.com` | VPS/game-server hosting + Shield DDoS | ✅ auth/billing/vps-panel hosts listed | *"may recognize or reward based on impact"* | live but **reward unquantified** — treat as swag-tier |

## Rejected, with the reason (do not re-litigate)

| candidate | reason |
|---|---|
| `axionax.org` | published table is genuinely good (Critical $5-10k, scope = contracts + core protocol + **backend APIs + frontend**) — but **DNS resolves (217.216.109.5) while both HTTPS and HTTP time out**, and `github.com/axionaxprotocol` 404s. Unreachable = park, note the blocker. |
| `chainstack.com`, `coreweave.com`, `deta.app`, `graphcdn.app`, `graphite.io` | **VDP only** (`reward_type: vdp`, RFC 9116 security.txt) — not cash |
| `spectrocoin.com` | pool `retired` **and** the flag was correct |
| `k8s.io` / `kubernetes.io` / `storage.googleapis.com` | OSS program, not a commercial product; scope is the CNCF estate |
| `bitflux.ch`, `fluxcd.io`, `fluxer.app` | vocabulary coincidence only |
| `panteracapital.com` | matched `infra`/`network` from a VC firm's marketing copy |

## Keyword traps that fired

- **`no longer`** on Obol's page is a *threat-model* sentence ("the cluster is no longer controlled by
  its legitimate operators"), not a shutdown notice. A keyword-only read nearly discarded the best
  candidate in the list.
- **`$0.00` / `$0.52`** price tickers on `chainflip.io` and `nosana.io` homepages look like reward
  figures to a naive `\$\d[\d,\.]+` regex. Extract amounts from the **policy page body**, not the
  marketing homepage.
- **`hivenet.com` was tagged `retired` in the pool** while being live, dated and paying. After
  verifying, the correction was written back:
  `pool.py set hivenet.com untouched --note "... policy LIVE, last update 24 Sep 2026, published
  table ..., pool 'retired' flag STALE"` — same for `docs.obol.org`, `chainflip.io`, `nosana.io`,
  `axionax.org`. Keeping the state `untouched` keeps the picker working; the note carries the proof.

## Recommended order given to the operator

1. **Obol** — biggest ceiling ($50k) with a real web/API surface.
2. **Hivenet** — the most product-identical scope, but a $500 ceiling; worth it only for a fast,
   clean web-app finding.
3. **Chainflip** — token-denominated, and its policy explicitly penalises verbose unverified reports,
   so budget for a tight write-up.

Note the ranking logic: **ceiling × scope-fit / friction**. Hivenet has the best fit but the worst
ceiling; Obol has both a good fit and the best ceiling; Chainflip has the best surfaces but pays in a
token and has a report-quality bar.
