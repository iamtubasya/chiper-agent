# The Graph — indexer software (graph-node, Rust) audit

Companion to the contract-side work. Reach for this whenever an Immunefi/audit target ships
indexer or node software and the only reachable reward impact is **High = "private information
being stolen"**.

## Why this slice of the target

- The Graph's Immunefi impact table accepts exactly 4 impacts. Indexer software can only map to
  High "private information being stolen"; the program-overview blurb about "indexer slashed /
  not running effectively" is NOT in the reward table, so DoS-ish indexer bugs have no payout path.
- graph-node stores **no indexer private key** (that lives in indexer-agent / indexer-cli, TS).
  The secrets actually present on the node are:
  - provider RPC URLs that carry an API key in the path (Alchemy/Infura/QuickNode/similar),
  - the Postgres connection string,
  - log-store (Loki/Elasticsearch) passwords.
  GCP/AWS-style key exposure is therefore the wrong hunt here — chase the *URL/credential in
  error output* angle instead.

## Attack-surface map (graphprotocol/graph-node)

| Location | What matters |
|---|---|
| `server/json-rpc/src/server.rs` | Admin JSON-RPC. Binds `Ipv4Addr::new(0,0,0,0)` (all interfaces, **no auth middleware**); the log line misleadingly says `http://localhost:{port}`. Methods (`handlers.rs:61-68`): `subgraph_create`, `subgraph_deploy`, `subgraph_remove`, `subgraph_reassign`, `subgraph_pause`, `subgraph_resume`. |
| `node/src/launcher.rs:657-669` | Admin server started **unconditionally**. |
| `node/src/opt.rs:135-141` | `admin_port` default **8020**. |
| `server/index-node/src/service.rs` | `POST /graphql` on **:8030**. Serves `indexingStatuses{ fatalError{message} nonFatalErrors{message} }`. |
| `server/index-node/src/auth.rs` + `resolver.rs:388-389` | Auth (`PoiProtection`, `GRAPH_POI_ACCESS_TOKEN`) gates **only the `proofOfIndexing` field**. Error messages are served to anyone. Default = unset = no protection. |
| `graph/src/data/subgraph/status.rs:169-207` | Serialises `fatalError.message` / `nonFatalErrors[].message` verbatim into the API response. |
| `core/src/subgraph/runner/mod.rs:1399` | `let message = format!("{:#}", e)` — the **full anyhow chain**, unredacted → becomes `SubgraphError.message`. |
| `graph/src/util/futures.rs:342-353` | `redact_log_urls` redacts `https?://…` in the **retry log line only**. The returned error is passed through untouched (`Err(result.map_err(TimeoutError::Inner))`). |
| `chain/ethereum/src/ethereum_adapter.rs` | ~25 RPC call sites set `.redact_log_urls(true)` — proof that these error strings DO contain provider URLs. |
| `node/src/chain.rs:243-249` | Startup logs the full `web3.url` (key included). |
| `chain/ethereum/src/env.rs:14-18` | `GRAPH_RPC_ETH_CALL_ERRORS` — "additional deterministic errors", `;`-separated. Knob that decides whether an `eth_call` error is persisted. |
| `docker/docker-compose.yml` | Publishes `8000 8001 8020 8030 8040`. |

## The two techniques that found it

1. **Redaction asymmetry.** When a codebase has a `redact_*` / `sanitize_*` helper, grep both its
   call sites AND the sites that *don't* call it. Here redaction is applied to log lines only, so
   the error *value* keeps the secret and any consumer of that value leaks it.
2. **"Does the served field carry the internal string?"** Trace backwards from the field an
   unauthenticated endpoint returns to where it is built, and check every formatting step for
   redaction. `format!("{:#}", e)` on an anyhow chain is a classic full-detail leak.

## Honest limits — what is and isn't provable (learned the hard way)

- CONFIRMED live: URL+key printed **unredacted** in graph-node's error output (the retry `WARN`
  shows `[REDACTED]`, the adjacent `ERRO` from another component shows the full URL); a
  **handler-level** error carries it too (`Ethereum node returned an error when calling function
  "balanceOf" …: error sending request for url (http://…/KEY)`); a handler failure **is** persisted
  and served unauthenticated on :8030 (proved with a deterministic ABI error).
- NOT provable: the URL inside a **served** `fatalError.message`. Under default config an `eth_call`
  **transport** failure is classified **non-deterministic** → graph-node retries it forever and
  never persists a `SubgraphError` (the subgraph stays `healthy`). Setting
  `GRAPH_RPC_ETH_CALL_ERRORS="error sending request for url"` did not change that on 0.45.0.
- **Lesson:** before claiming "secret leaked via API", prove the string is **persisted on the
  deterministic path**, not merely logged. A log-level leak alone is weak against the standard
  "best-practice critiques are out of scope" clause.

## Reusable local PoC harness

- `docker-compose`: `graphprotocol/graph-node` + `ipfs/kubo` + `postgres`. Publish only
  `8000/8020/8030` — host port 5432 is often already taken.
- Provider URL carries the fake key: `ethereum: "mainnet:http://host.docker.internal:8545/v2/<FAKEKEY>"`.
- `proxy.py`: a tiny JSON-RPC reverse proxy that forwards POST bodies to a real public RPC.
  - Forward with **curl via `subprocess`**, not `urllib`/`requests`: several public RPCs (e.g.
    publicnode) answer 403 to Python's TLS/UA fingerprint but accept curl.
  - To produce a client-side error that **contains the URL**, `os._exit(0)` the proxy on the target
    method (e.g. `eth_call`) so retries hit a dead port → reqwest renders
    `error sending request for url (http://…/KEY)`. An HTTP **status** error is NOT good enough:
    graph-node unwraps it to `HTTP error 401 with body: …` and drops the URL.
- Force a handler to run: a `blockHandlers` entry runs for every block. Do **not** set a `startBlock`
  far behind the head (the node backfills forever and the handler never reaches the head); omit
  `startBlock` (starts at head) or keep it inside the node's block cache — otherwise
  `subgraph_deploy` fails with `BlockNotFound(<n>)`.
- Minimal-subgraph gotchas (each one cost a deploy cycle):
  - `type X @entity(immutable: true|false)` — the `immutable` argument is **required**.
  - `source.address` is **required** for an `ethereum/contract` data source.
  - the mapping must `import { ethereum } …` or the AS compiler crashes with an unhelpful message.
  - a chain-call signature must match graph-node's `FunctionExt::signature_compat`:
    `name(inputs):(outputs)` — **no space after the colon** (`balanceOf(address):(uint256)`).
  - `graph deploy` needs the subgraph name to exist first: call the admin JSON-RPC
    `subgraph_create` (unauthenticated) or let graph-cli do it, else `subgraph name not found`.
  - redeploying identical content reuses the same deployment hash → **no new `indexingStatuses`
    entry**; to see a new one, change the manifest/mapping.
- Pre-check before budgeting: confirm the Docker Linux engine is actually up (`docker ps`) and leave
  any pre-existing lab containers alone.

## Verdict pattern

Report only if the secret is **demonstrably served by an unauthenticated endpoint**. Otherwise
write it up as "credential leaks unredacted into error output + unauthenticated admin/index-node
APIs" and expect a best-practice rejection. Do not upgrade a log-level leak into a High API
disclosure.
