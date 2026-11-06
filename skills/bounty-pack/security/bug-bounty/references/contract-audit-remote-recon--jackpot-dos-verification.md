# Jackpot DoS Re-verification — worked example (UPONZI, 2026-08-18)

Context: an earlier static pass on a cross-chain jackpot (core on Robinhood → CCIP → VRF on
Base → CCIP back) reported a HIGH DoS with 4 failure points + 2 supporting points. The client
asked "cek lg jackpot dos" (re-check). The re-check CONFIRMED the overall severity but
CORRECTED 2 of 6 claims — a good example of why the validation pass exists.

## State reads that classified the finding as LATENT (design flaw, not live outage)

```
CORE (Robinhood):        activeRound = all-zero struct     → no active round
                         nextRoundId = 1                   → NO prior request (initial value!)
                         lastJackpotRequestTs = 0
                         lastJackpotDrawTs = 0
                         jackpotPool = settledJackpotPool = 0.01386 ETH (accumulated, never drawn)
ADAPTER (Robinhood):     requestStartedByRound[0..2] = 0
                         responseMessageByRound[0..2] = 0
GATEWAY (Base):          resultReady[0..2] = 0
                         resultSendStartedByRound[0..2] = 0
EVENTS:                  explorer logs → 0 JackpotRequested across 50 logs
CONSTANTS:               JACKPOT_INTERVAL = 86400 (24h); jackpotEpochStart = deploy ts
                         now - epoch = 20.1h → first request triggerable in ~3.9h
```

Key trap: `nextRoundId` read 1 and LOOKED like "one round already happened". Grep the source
first: `uint256 public nextRoundId = 1;` is the INITIAL value → zero requests ever.

## Static corrections (what the re-check changed)

| Claim in first pass | Re-check result |
|---------------------|-----------------|
| 1. CCIP RH→Base lost → `activeRound.active` stuck forever | VALID HIGH. `activeRound.active=true` + `lastJackpotRequestTs` set before send; message dropped = `JackpotRoundActive()` forever. `reportDelayedJackpotRequest()` only `emit`s — NOT a recovery path. |
| 2. VRF request lost/failed on Base → pending forever | VALID HIGH. Gateway `_ccipReceive` sets `vrfRequestStartedByRound` then calls `requestRandomWords`; VRF failure reverts the CCIP message → relayer retries forever. |
| 3. `sendResult()` sets `resultSendStartedByRound` before `ccipSend` → flag permanent | **CORRECTED — not standalone.** `ccipSend` revert rolls the whole tx back, flag included. Only lost-message-after-success leaves it stuck. Merged into #4. |
| 4. Adapter `_ccipReceive` sets `responseMessageByRound` before external `fulfillJackpotRandomness` → replay loop | VALID MEDIUM. If fulfill reverts, mapping rolls back → CCIP relayer retries forever (gas drain). |
| 5. `allowOutOfOrderExecution: true` both directions | **DOWNGRADED to informational.** Single `activeRound` slot → cross-round out-of-order not exploitable. Folded into #4. |

Verdict: HIGH still valid, but now 2 HIGH + 1 MEDIUM, not 4+2. Report the corrected count.

## Checklist embedded in SKILL.md (the reusable lesson)
1. Live-state every pipeline flag before claiming live vs latent DoS.
2. Source-check initial values of counters (`nextRoundId = 1`).
3. Event-only "recovery" functions are not recovery.
4. Flag-before-call is permanent ONLY on success-then-lost-message, not on revert.
5. Single-active-round state neuters out-of-order severity.
6. Re-rank after correction; report corrected counts.

## Tooling notes hit during this pass
- Robinhood direct RPC that WORKS: `https://rpc.mainnet.chain.robinhood.com` (POST JSON-RPC,
  User-Agent required). `https://robinhoodchain-rpc.publicnode.com` → HTTP 404.
- Blockscout v1 proxy (`/api?module=proxy&action=eth_call`) rate-limits to HTTP 400/429 fast —
  prefer direct RPC eth_call.
- Blockscout v2 logs: `GET /api/v2/addresses/<addr>/logs` returns items with `topics` (may be
  null-safe: some entries have `"topics": null` — guard before indexing).
- Transactions: `GET /api/v2/addresses/<addr>/transactions` (no filter param) is reliable.
- Base gateway + VRF state reads via `https://base-rpc.publicnode.com` (mainnet.base.org
  rate-limits).
- Pure-python keccak256 in the probe script worked fine for selector computation — no eth-hash
  dependency needed when eth-hash isn't installed; but eth-hash/pycreyptodome is the simpler
  path when pip install is available.
