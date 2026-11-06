## Deployed-vs-source selector diff (do this EARLY on any deployed target)

Programs that ship a lifecycle like "the deployed build is an earlier build than the published
source" also close every already-fixed issue as known-and-unpaid. You cannot tell which fixes are
actually live by reading the source. Measure it instead — no explorer API key needed:

```bash
# 1. selector set derived from the source you were given
forge inspect <Contract> methodIdentifiers --json > sel.json
# 2. runtime bytecode of the live address
cast code <addr> --rpc-url <rpc> > code.hex
# 3. any selector in sel.json whose 4 bytes are absent from code.hex is NOT on chain
```

```python
missing = [sig for sig, sel in sels.items() if sel.lower() not in code.lower()]
```

How to read the result:

- **A missing public getter is a build-generation signal, not a bug on its own.** Group the absent
  selectors and map each onto the fix it carries. Real mapping from one engagement:
  `epoch()` + `newEpoch()` = the stale-weight epoch guard; `minNudgeAmountIn` +
  `DEFAULT_WETH_NUDGE_FLOOR` = the paid-nudge input floor; `roundEntrantsLength` = the settlement
  gas-DoS fix; `retiredPrize` + `setRetiredPrize` = the escrow-repoint fix; `maxTimbsPerWallet` +
  `timbsClaimedBy` = a per-wallet cap; `operator*` on a treasury = the rate-limited operator role.
  **If the absent function is a listed known-issue fix, the live system still has that bug — and it
  earns nothing.** Do not spend report effort there.
- **Every source selector present = the deployed build equals the source.** Only then is a
  source-derived finding certainly live; say so in the report, because it pre-empts the triager's
  first question ("is this even deployed?").
- Confirm with read-only calls: a `cast call` on a source getter that reverts is the cheapest
  possible confirmation that the build is older.

Trap: the published bundle can be NEWER than several deployed contracts at the same time. Observed
2026-10 (TimbSwap): the live Vault, Treasury, Router, Registry, Prize, Escrow and Faucet were all
pre-fix builds while the Token, BoostFarm, Pair and Factory matched the source exactly. So: audit the
source, then concentrate your reporting on defects that are live on BOTH — and grep the known-issue
list one more time before writing anything up.

**⛔ The selector diff is the WEAK version of this check — prefer a full `deployedBytecode` byte compare.**
A selector diff cannot see a changed body, added internal-only logic, or a module that was *swapped for a
patched build of the same contract*. The strong primitive: recover the live source from
Blockscout `/api/v2/smart-contracts/{addr}` (fields `file_path`, `compiler_settings`, `viaIR`,
`additional_sources[]`, `is_verified_via_verifier_alliance`), compile it and the repo tree with the
record's exact settings, and compare `deployedBytecode` byte-for-byte against `cast code`. Same length
with diffs only at a `PUSH32` window and in the trailing ~51 metadata bytes = the build IS the source
(say so in the report). **A length difference = the published source does not reproduce what runs.** On a
module/dispatcher design, also read the module-registry storage table and the `ModuleUpgraded`-style
event history: a **later replacement** is the strongest signal of a post-audit patch, and the live-added
hunks are unreviewed code — the prime audit target, since no report line covers them.
Recipe, the immutable-resolution trick, the wide-range logs call, and a worked example:
`references/deployed-vs-published-source-verification.md`.

### After a missing selector is found: verify the CONSEQUENCE from logs, don't assume it

A missing constant/function only matters if its absence changes live behaviour. Before writing a
timing or liveness finding off a selector diff, measure it. Event data is usually enough and needs no
indexer: design the event so it carries what you need, or take block timestamps.

Worked example (same engagement): the live TimbPrize lacked `GRID_GRACE()`, which the source uses to
fall back to lock-time segment starts when a VRF lock lands late — so the hypothesis was "segments can
be silently shortened". Closed by measurement, not argument:

```bash
cast logs --from-block <a> --to-block <b> --address <prize> --json \
  "SegmentAdvanced(uint256,uint256,uint256)"     # topic0 is a POSITIONAL arg, not --topic0
cast logs --from-block <a> --to-block <b> --address <vrf> --json "DrawFulfilled(bytes32,uint256)"
```
- `SegmentAdvanced` carries its own timestamp in the data → the whole segment-start series is free of
  block lookups; diff consecutive starts to get segment durations.
- `DrawFulfilled`'s block timestamp is the lock moment → `lock_ts - segment_start_ts` is the lateness.
- Public RPCs often accept a 1M-block span for `eth_getLogs`; verify the span limit before crawling.

Result there: 660 segments, every start-to-start delta between 3597 s and 3606 s against a 3600 s
grid, lock lateness 10–170 s past the interaction window — no shortened window at `INTERACTION_WINDOW`
(3585 s), no drift. Hypothesis dead. **A hypothesis you can close with data is worth the 10 minutes;
report it as a negative so nobody re-opens it.** Note the exact command shape — `forge`/`cast` differ
between versions and `cast logs --topic0` does not exist (it is a positional signature/topic).

