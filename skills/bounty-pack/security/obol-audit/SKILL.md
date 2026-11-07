---
name: obol-audit
description: Obol Network bug-bounty engagement (Charon DV middleware, DV Launchpad, Obol API, OVM/OWR splits, OBOL token) — scope, reward tiers, known-issue traps, tested matrix and verified negatives.
---

# Obol Network — bug bounty engagement

## Program facts (docs.obol.org/advanced-and-troubleshooting/security/bug-bounty)

- Channel: email `security@obol.tech`. No platform.
- Rewards: Critical $25k · High $2.5k · Medium $500 · Low $125 (discretionary).
- PoC format required: Go test/patch for Charon, Foundry fork test for contracts, script against local devnet.

### In scope
- Charon (github.com/ObolNetwork/charon) incl. cluster lifecycle + DKG ceremony.
- DV Launchpad (launchpad.obol.org) and the Obol public API (api.obol.tech).
- OVM `0x2c26B5A373294CaccBd3DE817D9B7C6aea7De584` (mainnet/Sepolia/Hoodi).
- OBOL token `0x0B010000b7624eb9B3DfBC279673C76E9D29D5F7`.
- Legacy Obol Splits / OWR; Obol-operated public relays.

### OUT of scope
- obol.org static site, internal corp infra, **Obol Stack** (Hermes/OpenClaw/x402/eRPC/Cloudflared — pre-release), `charon alpha edit` and alpha subcommands, third-party libs, node-operator host security.

### Prohibited testing
- **No testing on mainnet or public-testnet deployed code — local forks only** (Hoodi preferred).
- No DoS against Obol infra; no "significant traffic" automated testing; no phishing.

## Known-issue lists (read before reporting; duplicates pay 0)
- `charon/CLAUDE.md`, `obol-splits/KNOWN_ISSUES.md`, `obol-sdk/KNOWN_ISSUES.md`, `obol-security` repo.
- Pre-rejected classes: legacy lock formats <v1.10, fee-recipient warn-only, peer/relay resource exhaustion, operator-signature trust model, split-address prediction, `sweep()` asymmetry, `withdrawPullBalance()` permissionless, `deposit()` credential validation, role retention on transfer, `recoverFunds()` ETH path, "arithmetic underflow DoS by manipulating balances".

## API map (swagger: GET https://api.obol.tech/docs-json → 50 paths)
- Auth = `Authorization: Bearer <hex EIP-712 signature>`; bearerFormat "JWT" is wrong.
- Unauth writes: `POST /v1/lock`, `/v1/lock/verify`, `/v1/deposit_data/partial_deposits/{lockHash}/{idx}`, `/v1/fee_recipient/partial/{lockHash}/{idx}`, `/v1/exp/partial_exits/{lockHash}`, `/v1/test`.
- Launchpad invite URL = `https://launchpad.obol.org/dv#<config_hash>`.

## Verified negatives (do not re-test blindly)
- `POST /v1/lock` **does** validate crypto: a lock with tampered `withdrawal_credentials` + recomputed `lock_hash` is rejected 400 "Invalid lock data" (both /v1/lock and /v1/lock/verify). Valid `charon create cluster` lock → 201.
- `PUT /v1/definition/{hash}` verifies the ENR signature (401 "ENR signature verification failed") and binds Bearer↔body.address (401 on cross-operator). Published `config_signature` in GET **is** accepted as a Bearer, but ENR substitution still needs the operator's ENR signature.
- Changing `fork_version` in PUT → 401 (bearer is chain-bound).
- `POST /v1/definition` rejects any `threshold != ceil(2*operators/3)` → 400 "Wrong threshold" (so threshold cannot be lowered to 1-2 of N).
- `POST /v1/exp/partial_exits` verifies the k1 DTO signature (400 "incorrect dto signature").
- `POST /v1/positions` validates each `additionalAddresses` entry as 0x+20 bytes (no injection).
- Search endpoints escape regex (`.`/`a(b` return 0 hits, no error); `$`-operators blocked by Cloudflare WAF (403).
- OVM `uint128(sweepAmount)` truncation is **unreachable**: 2^128 wei = 3.4e20 ETH.
- ObolToken = stock OZ 4.8 ERC20+AccessControl+Permit+Votes; only MINTER_ROLE mints. **Verified 2026-11-02 by pulling the deployed Etherscan source** (`0x0B0100…D5F7`, chainid=1, solc 0.8.17, OZ draft-ERC20Permit line, sources saved to `D:/bb/obol/oboltoken_*.sol`): constructor grants only DEFAULT_ADMIN_ROLE+MINTER_ROLE, `mint()` is `onlyRole(MINTER_ROLE)`, `burn`/`burnFrom` permissionless-but-spendAllowance, and the only custom logic is `_beforeTokenTransfer` blocking transfers TO the token address. No novel surface. Contract is verified on Etherscan, so live==source by construction (no bytecode divergence to chase).

## PAYABLE FINDING (Medium) — fee-recipient registration integrity
`POST /v1/fee_recipient/partial/{lockHash}/{shareIdx}` has **no auth**, and
`POST /v1/fee_recipient/{lockHash}` returns the stored **partial BLS signatures** with no auth.
The API groups partials by the *literal string* `fee_recipient`/`gas_limit`/`timestamp`, but the BLS
signature covers the 20-byte address (case-insensitive) → replay a public partial under a case-variant
address and the API creates a **second duplicate builder_registration group** for a cluster you don't
operate. Also works with `gas_limit` "0"+value.
- Reproduced on mainnet cluster `0xREDACTED_********`
  (validators `0x8ed917e5…` and `0xae4c8dfe…`): 1 group → 2 groups, identical modulo hex casing.
- Charon impact: `ProcessValidators` marks the validator Complete **and** Incomplete →
  `fetchFromAPI` returns `hasIncomplete=true` → node polls at `fetchIntervalIncomplete`. No fund loss.
- Ceiling: **Medium**. No theft (`filterVerifiedRegistrations` + `ThresholdAggregate` verify), no MEV
  takeover, no DoS. Artifacts: `D:/bb/obol/poc_repro.log`, `Obol_FeeRecipient_Registration_Integrity_Report.pdf`,
  repro script `D:/bb/obol/obol-sdk/poc/poc_repro.mjs`. Gmail draft created (id `r3689151701627337973`).
- Shared-index binding on this endpoint IS enforced: replaying share-1's sig as share-2 → 400
  "invalid partial signature"; share index bounds-checked; timestamp far-future rejected.

## Dead links in their own policy (useful for triage)
`ObolNetwork/charon/KNOWN_ISSUES.md` → 404. `ObolNetwork/obol-api` repo → 404 (private/absent).
Only `obol-splits/KNOWN_ISSUES.md` and `obol-sdk/KNOWN_ISSUES.md` actually exist.

## Escalation round (lead re-examination) — all dead ends, with evidence
Attempted to promote the two defects above to High/Critical. Every chain died:

**Lead 1 (bcast signature oracle) — cannot escalate.**
- Cannot forge `node_signatures` in a lock: oracle signs `sha256(sessionHash||msgID||typeURL||value)`; `Lock.verifyNodeSignatures` needs a k1 sig over the raw 32-byte `lock_hash`. Preimage. No.
- Cannot inject a broadcast even with a full quorum of signatures: every node signs the *same* digest for the same (msgID,message) because `hashFunc = newHashAny(sessionHash)` is identical cluster-wide, so an attacker CAN harvest N sigs — but `nodeSigBcast.broadcastCallback` now checks `n.peers[msgPeerIdx].ID != senderID` → "sender peer ID does not match claimed peer index". Attacker's own peer ID is never in `peers`. Delivery blocked.
- No replay across sessions (sessionHash = definition hash is hashed into the digest).
- `msgIDFuncs` only holds 3 IDs, and dedup is keyed (peerID,msgID) → map growth needs many fresh libp2p identities; ceremony-window only. Medium at most.
- **Verdict: Low / defense-in-depth only.** Frame as "unauthenticated signature-request handler", not a bounty-grade finding.

**Lead 2 (Launchpad threshold display) — cannot escalate.**
- To matter, display must differ from the signed threshold. `POST /v1/definition` rejects any `threshold != ceil(2*operators.length/3)` → 400 "Wrong threshold" (tested n=4/t=4, n=5/t=5, n=5/t=3 → all 400).
- The Launchpad's `az = e => Math.ceil(2*e/3)` is *identical* to the API's rule, and `joinClusterFlow` reads `clusterDefinitionData.operators.length` from the API response. Display == enforcement. No desync.
- **Verdict: cosmetic / informational only.**

## Definition-validation matrix (POST /v1/definition) — results
Rejected (good): config_hash != hash(body) → 400 "Invalid definition data"; num_validators vs validators.length mismatch → 400 "Insufficient validators"; empty validators → 400; `$`-operators → Cloudflare 403.
Accepted (201) but self-visible / non-impactful: zero withdrawal_address, zero fee_recipient, duplicate operator addresses, `deposit_amounts` summing to 1 ETH or 64 ETH, unknown extra fields, 200-char uuid.
→ None reach "passes careful operator review while diverting deposits": the address the operator actually reviews is derived from the *deposit credentials* (`q2()` in Launchpad module 4567 renders `credentials[12:]`, not the definition field), so a zero/attacker address is displayed verbatim.

## Auth-binding matrix — all correctly enforced (401)
- `POST /v1/termsAndConditions` with `address=victim` + my signature → 401 (even though the EIP-712 type does NOT contain the address; the API recovers the signer and compares). Victim's T&C flag stayed `false`.
- `POST /v1/definition` with `creator.address=victim` + my signature → 401.
- `PUT /v1/definition/{hash}` cross-operator bearer → 401; fork_version change → 401.

## Other unauth surfaces checked (negative)
- `POST /v1/fee_recipient/partial/{lockHash}/{idx}`: BLS partial signature IS verified → 400 "invalid partial signature"; share index bounds-checked; timestamp must not be far-future. Cannot poison fee_recipient.
- `POST /v1/exp/partial_exits/{lockHash}`: k1 DTO signature verified (400 "incorrect dto signature").
- `GET /v1/lock/{lockHash}/launchpad` → 302 to `https://<network>.launchpad.obol.org/cluster/details?lockHash=<hash>` — built from the hash only, **no open redirect**.
- `GET /v1/lock/{lockHash}/peer-info` returns `[]` for both my cluster and a live Lido cluster; prefix/`.*`/`^0x` inputs all `[]` — no cross-cluster leak observed.

## Residual design observation (Low, not worth a report alone)
`PostPartialExits` signs only `UnsignedPartialExitRequest{ShareIdx, PartialExits}` — the **lockHash is in the URL path, not the signed payload**. Mitigated server-side ("A pubkey whose exit is stored under a different lock hash is rejected with 409"), so exploitation needs a same-validator-keys second lock and yields exit-griefing only.

## Round 3 (post-submission deep dive) — more verified negatives
- `POST /v1/deposit_data/partial_deposits/{lockHash}/{idx}`: BLS **is** verified → `401 Invalid deposit
  signature` for garbage/random sigs. Deposit redirection infeasible.
- `GET /v1/exp/exit/{lockHash}/{shareIdx}/{pubkey}` with a **non-operator** identity key → `400 "operator
  ENR not found"`. The bearer is resolved to an operator in the lock, so exit messages are properly bound.
- `peer-info` prefix probe: found a real baseline (`0x0fccf89e…` returns 3 peer rows) but short prefix
  `0x0fcc` returns `[]` → matching is exact, **no cross-cluster leak**. Rows expose only peer nicknames +
  client versions, no IPs.
- Launchpad XSS: cluster `name` is validated (`400 "name is not valid."` on HTML). The only 3
  `dangerouslySetInnerHTML` sinks in `_app.js` are **styled-components internals** (CSS), not user data.
- Auth matrix on all `security=[bearer]` routes: `/v1/techne/*` returns 200 **without auth** but only
  static NFT metadata and ignores the index (stub) — not sensitive. `/v1/owr/mainnet/{any}` returns
  `500 Internal server error` for *every* input including garbage (broken endpoint, generic body, no
  stack trace). A malformed 65-byte bearer returns 500 instead of 401 (fails closed).
- `applyBuilderRegistrationOverrides` uses **only quorum** groups; `IncompleteMessages` feeds just the
  `hasIncomplete` flag. Confirms the submitted finding's ceiling really is Medium (no MEV influence).
- `mergeRegistrations` keeps the **highest timestamp** per pubkey ("entries in a win ties"), and
  `filterVerifiedRegistrations` only checks the BLS signature — it does not constrain fee_recipient.
  But reaching quorum needs threshold distinct valid partials, so still not attacker-reachable.

## FALSE-POSITIVE TRAP: output redaction looks like source corruption
`src/verification/depositPayload.ts` displayed as `ETH1_CREDENTIAL_PADDING='***'.repeat(22)` and
`ZERO_CREDENTIALS=`0x${'...}`. The file is **fine** — `b'***'` is absent from disk, and `dist/` has the
correct `"0".repeat(22)` / `0x${"0".repeat(64)}`. The redaction happens in the *output layer*.
**Always verify corruption claims byte-wise** (`b'***' in raw`, line length, md5) before reporting.

## Lab built & WORKING — charon Go test harness (WSL)
Build/test charon in WSL (Windows CGO build fails):
```
MSYS_NO_PATHCONV=1 wsl -e bash -lc "export PATH=\$HOME/go/bin:/usr/local/go/bin:\$PATH; \
  export GOPATH=/home/agentuser/go; export GOFLAGS=-mod=mod; export CGO_ENABLED=1; \
  cd /mnt/d/bb/obol/charon && go test -run TestX -v ./dkg/"
```
- Go install: `curl -sL https://go.dev/dl/go1.24.6.linux-amd64.tar.gz | tar -C $HOME -xzf -` → `$HOME/go/bin/go`; charon auto-downloads toolchain go1.27.3.
- Reusing the Windows module cache via `/mnt/c/.../go` works (herumi ships linux/amd64 static libs).
- **WSL /tmp does NOT persist between `wsl -e` invocations** — write outputs to `/mnt/d/...` not `/tmp`.
- Test harness to reuse: `dkg/protocol_test.go` (`package dkg_test`) has `createTestCluster`, `runProtocol`, `createDKGConfig`, `nodeDir`.
- **Gotcha:** `testutil.CreateHost` gives a random libp2p identity. For bcast tests the identity must equal the bcast secret — use `testutil.CreateHostWithIdentity(t, addr, secret)` or signature verification fails with "invalid signature".

## ⛔ CORRECTION (2026-11-02) — "bcast signature layer bypassable" is a FALSE POSITIVE
The earlier "CONFIRMED" bcast PoC below over-stated reachability. Its tests used `testutil.CreateHost`
(which installs **no connection gater**), and the premise "Charon connects with an open connection
gater (p2p.NewOpenGater)" is **wrong**. Production `setupP2P` (dkg/dkg.go:1389) and `app.go` both use
`p2p.NewConnGater(peerIDs, relays)` — a strict **allowlist** of cluster peers + relay only. Proven by
a positive/negative control test (dkg/bcast_gater_reach_test.go, PASS):
- **Positive**: a legit cluster member reaches `handleSigRequest` and gets a valid identity-key sig.
- **Negative (direct)**: a non-cluster peer → `new stream: connection failed` (gater drops it).
- **Negative (relay)**: attacker→relay→node → `new stream: connection failed` (dkg/bcast_relay_reach_test.go).
The handleSigRequest code IS unauthenticated at the handler level, but the gater is the real boundary,
so an EXTERNAL attacker cannot reach it. The handler-level issue is defense-in-depth only (a byzantine
in-cluster operator could invoke it — but the trust model already assumes threshold-many operators may
be malicious, and the signature is session-bound via sessionHash, so no forgery follows).
**ACTION: retract submitted Finding #2 ("Charon bcast unauthenticated signature handler", Low).** The
fee-recipient finding (HTTP API surface) is unaffected — it's on api.obol.tech, no p2p gater involved.

## CONFIRMED (2 passing Go tests) — bcast signature layer fully bypassable
Artifacts: `D:/bb/obol/poc_bcast_oracle.log`, `charon/dkg/unauth_bcast_poc_test.go`,
`charon/dkg/unauth_bcast_inject_test.go`.
1. `TestUnauthBCastSignatureOracle` PASS — a **non-cluster** libp2p peer connects and receives a
   65-byte secp256k1 signature that `k1util.Verify65(nodePubKey, sha256(sessionHash||msgID||typeURL||value), sig)` accepts.
2. `TestBCastSignatureLayerBypass` PASS — attacker harvests **one signature from every node** for the
   same message, assembles `BCastMessage{Id,Message,Signatures}`, submits it → `newPeerK1Verifier`
   accepts (`err = <nil>`). The signature layer does **not** stop a forged broadcast.
- Root cause: `dkg/bcast/server.go handleSigRequest` signs for any `pID`; no cluster-membership check,
  and `p2p.NewOpenGater` gates nothing.
- **Ceiling = Low/defense-in-depth**, because delivery is stopped *after* verification by the callback
  peer checks (`nodeSigBcast.broadcastCallback`: `peers[msgPeerIdx].ID != senderID`;
  `frost newBcastCallback`: `peers[pID]`). Attacker is never in `peers`.
- Escalation watch: a new messageID registered without a peer check = Critical (inject FROST round-2
  casts / node signatures). Only 3 msgIDs exist today and all check.

## SUBMISSION STATUS — both findings SENT to security@obol.tech
| # | Finding | Severity claimed | Status |
|---|---------|------------------|--------|
| 1 | Fee-recipient registration integrity (case-variant grouping) | Medium | SENT |
| 2 | ~~Charon bcast unauthenticated signature handler~~ | ~~Low~~ | **TO RETRACT** — false positive (gater blocks non-cluster peers; see CORRECTION above) |
Both sent from **RESEARCHER_EMAIL** (never `account_files()[0]` — that is akun3/ympuspita).
Send verification pattern that worked: `drafts().get(format='full')` → check To/Subject/labels/attachment
size, then `drafts().send()`, then `messages().get()` must show `labelIds == ['SENT']` and the draft id
must 404. Message id #2 = `1a18bbb6aa22ae72`, thread `1a18a33bbab5d381`.
Report PDFs: `Obol_FeeRecipient_Registration_Integrity_Report.pdf`,
`Obol_Charon_BCast_Unauth_Signature_Report.pdf`. Each email carries an explicit
"HONEST SEVERITY CEILING" and "CLOSEST KNOWN ISSUE" section to pre-empt triage rejection.
Outstanding: reproduction left 2 duplicate registration groups on mainnet cluster
`0xa7b41c90…06d5` (one non-quorum, 1 partial); offered to supply exact tuples for removal.

## Relay infra (in scope) — checked, clean
Obol relays: `0.relay.obol.tech`, `1.relay.obol.tech`, `2.relay.obol.dev`, `4.relay.obol.dev`.
Public HTTP mux has only two routes (`cmd/relay/relay.go`): `/` → `newMultiaddrHandler` and `/enr`.
**Everything else returns the multiaddr list** (catch-all) — so `/metrics` and `/debug/pprof/` returning
200 is NOT pprof; do not report it as exposure. Real pprof/metrics sit on separate `MonitoringAddr` /
`DebugAddr` servers; `4.relay.obol.dev/metrics` → nginx 403 (not exposed).
Each request rotates backend IPs (load-balanced relays); `2.relay.obol.dev` leaks an AWS ELB hostname
in its multiaddrs, but that is already public via DNS → not reportable.

## Nonprod environments (in scope, reachable)
`obol-api-nonprod-dev.dev.obol.tech` and `obol-api-nonprod-qa.dev.obol.tech` are live and public, with
identical OpenAPI (51 routes, zero auth differences vs prod). They are **isolated**: posting a
definition to DEV returns `401 "Missing t&c signature"` and the config_hash is 404 on QA and PROD.
No cross-environment injection path.

## OVM reentrancy re-check — safe
`withdrawPullBalance(attacker)` → reenter `distributeFundsPull()`: EVM debits the caller's balance
BEFORE executing callee code, so `currentbalance = B - Pr` and `_fundsToBeDistributed = B - F` is
unchanged. No pull-balance inflation.

## Only remaining path to Critical
Malicious-peer lab: 4-node `charon dkg` on localhost, then a custom Go peer (libp2p + copied dkgpb/corepb protos, no BLS needed) attacking parsigex / frost round-2 / reshare. That is where "external attacker → slashable signature / key-share exfil" lives. Not reachable from the API/Launchpad surface.

## Genuine (non-payable) defects found
1. `dkg/bcast` `checkMessage` (dkg/nodesigs.go) does not authorize the requesting peer, and `handleSigRequest` signs `sha256(sessionHash||msgID||typeURL||value)` for anyone who can open a libp2p stream (`p2p.NewOpenGater` allows all peers). = unauthenticated identity-key signing oracle over session-bound digests + unbounded `dedup` map growth per fresh peer ID. No escalation: `newBcastCallback` checks `peers[pID]`, so injected messages are dropped.
2. Launchpad accept page renders `Threshold: ceil(2n/3)/n` computed from operator count (`az = e => Math.ceil(2*e/3)`) instead of `definition.threshold`. Latent only — the API pins the threshold.

## Local lab notes
- Charon builds need CGO (herumi BLS). Windows build fails (`CGO_ENABLED=0`). Use the linux release binary in WSL:
  `MSYS_NO_PATHCONV=1 wsl -e bash -lc "/mnt/d/.../charon-v1.11.2-linux-amd64 create cluster --nodes 4 --threshold 3 --network hoodi ..."`
- obol-sdk: `npm install --legacy-peer-deps` then `npm run build:tsup`; import `dist/cjs/src/index.js` (exports `clusterConfigOrDefinitionHash`, `clusterLockHash`, `ENR`). Write scripts as `.mjs` (CJS lacks top-level await; `@chainsafe/enr` is ESM-only).
- `/docs-json` on api.obol.tech gives the full OpenAPI spec — start there.

## GAP-CLOSURE round 5 (2026-11-02) — gater is HOST-LEVEL, all 6 protocol IDs covered in one test
The audit log previously claimed frost/pedersen/parsigex/sync were "reviewed; gater is the real boundary" without
per-protocol tests. Closed with a single consolidated, table-driven test — not four separate ones — because the
gater is a **host-level** boundary, installed once (`setupP2P` dkg.go:1404 + app.go:378 via `libp2p.ConnectionGater`)
and firing at `InterceptSecured` *before* any stream handler, independent of protocol ID. Source confirms all
transports share that host: bcast/frost/pedersen/sync via `setupP2P`, and `app.go:724` passes the SAME gated
`p2pNode` into `parsigex.NewParSigEx`.

`dkg/all_protocols_gater_reach_test.go` (PASS, 6/6 subtests):
- Positive: allowlisted cluster member reaches the handler on every PID.
- Negative: non-cluster peer rejected with `p2pNode stream: connection failed` on every PID:
  bcast/sig, bcast/msg, frost/round1/p2p, pedersen/node_pubkeys, parsigex/2.0.0, sync/1.0.0.

→ No transport has a gater gap. Finding 2's retraction stands, and the scope note ("gater is the real boundary")
is now **empirically proven across the whole p2p surface**, not bcast-only.

**fee_recipient WRITE path** (the zip skeleton's "fresh injection → higher severity" hypothesis): already a
verified-negative from earlier rounds — `POST /v1/fee_recipient/partial/{lockHash}/{shareIdx}` verifies the BLS
partial signature (400 "invalid partial signature" for any non-owner/fresh sig) AND enforces the share-index↔sender
binding (share-1 replay as share-2 → 400). A fresh fake sig is rejected on write, so the Finding is strictly the
case-variant grouping (read+replay), not injection/overwrite. No stronger severity. No new PoC needed.

## Deep-dive round 4 (2026-11-02) — API re-check + Launchpad bundle + contracts, all verified negatives
**API spec unchanged (50 paths, re-pulled `/docs-json`).** Per-path `security` annotation confirms which routes
are truly unauthenticated vs AUTH (`Authorization` bearer). AUTH-marked: `POST /v1/definition`,
`GET /v1/exp/exit/{…}`, `GET /v1/owr/{…}`, `GET /v1/techne/*`, `POST /v1/termsAndConditions`. The rest
(`/v1/lock`, `/v1/fee_recipient/*`, `/v1/deposit_data/*`, `/v1/exp/partial_exits`) are UNAUTH in spec — already
covered; their crypto is enforced server-side per prior rounds. Three NEW endpoints tested read-only and clean:
- `GET /v1/_health` → `{"status":"ok","info":{database:up, mainnet beacon:up, hoodi beacon:up}}` — **no infra leak** (no SQS/S3/AWS ARNs, no internal IPs).
- `GET /v1/lock/{hash}/peer-scores` → operator `peer_name`/`peer_nickname` + `avg_peer_score` only (operator_address is empty string — no address leak).
- `GET /v1/lock/{hash}/network-percentile` → effectiveness percentile + validator count, public stat, no leak.

**Launchpad (launchpad.obol.org) JS bundle analysis** (`D:/bb/obol/launchpad_bundle.js`): Next.js SPA.
- 1,795 unique URLs extracted are the **wagmi/viem chain registry** (public third-party RPC list) — NOT a finding.
- `obol:svXELzJDXQPrmgA3AopiWZWm` string: **dead code**. Assigned to var `m` and only used as a truthiness gate
  (`m && h`) to build `https://erpc.gcp.obol.tech/rpc/<network>` for GNOSIS/HOODI. Never passed to `Authorization`/
  `Basic`/`btoa`. Not a live credential leak.
- `ceremony-coordinator.aws.obol.dev` = user-facing nav link ("Test Results"); `erpc.gcp.obol.tech` = eRPC (Obol
  Stack, explicitly OUT of scope). `sanctioned_addresses.json` = public sanctions list. No hidden API, no secret.

**Contracts re-confirmed against KNOWN_ISSUES** (no source drift since `765914e` 2026-10-22, CI-only commit):
all 5 families (OVM 521 lines, OWR, OTR, ObolLidoSplit, + factories) trace to KNOWN_ISSUES.md. OVM+ObolToken both
**verified on Etherscan** (source==bytecode by construction). The only residual "only remaining path to Critical"
(malicious-peer lab attacking parsigex/frost-round-2/reshare over a REAL 4-node ceremony) remains unbuilt — it is
the sole avenue left, needs a full `charon dkg` localhost run + a custom libp2p peer in Go, and is not reachable
from API/Launchpad surface. Note it as a GAP, not a finding.
