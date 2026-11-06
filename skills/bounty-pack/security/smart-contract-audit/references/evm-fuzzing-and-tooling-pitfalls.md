# EVM fuzzing + tooling pitfalls (echidna / medusa / mythril / fork tests)

Learned the hard way on the Fira (Steady Labs) engagement, 2026-10-01.
Every item below is a failure that actually happened, with the fix that worked.

## A. echidna

1. **"Deploying the contract 0x00a3... failed (revert, out-of-gas, sending ether
   to a non-payable constructor, etc.)"**
   echidna sends `balanceContract` (default 10 ETH) as `value` to the target's
   constructor. A non-payable constructor reverts and the run dies before fuzzing.
   Fix: set `balanceContract: 0` in echidna.yaml **and/or** mark the constructor
   `payable`. (Both is safest.)

2. **"Unlinked libraries detected in bytecode of contract X"**
   crytic-compile compiles/deploys *every* contract in the build. One contract
   with an unlinked external library anywhere in the project aborts the whole
   run — even if your harness never touches it.
   Fix: create a **minimal sibling project** for fuzzing containing only the
   harness + the contract under test + its libs + OZ. Do not point echidna at
   the big multi-protocol build.

3. **Harness must live in `src/`, not `test/`**
   crytic-compile runs `forge build --skip ./test/** ./script/**`, so an echidna
   contract under `test/` is never compiled into the artifacts and you get
   "no tests found". Put fuzz harnesses in `src/` (or `contracts/`).

4. Prefix: echidna picks up `echidna_*` for property mode. Assertions inside
   actions are caught in `--test-mode assertion`.

5. **A non-payable constructor is not the only deploy trap**: your constructor
   must not depend on `vm.prank` semantics if you also want a Forge smoke test to
   share the code — keep the ctor to plain deploys + storage writes.

## B. medusa

6. Prefix: medusa picks up `property_*`. Since one harness usually has to serve
   both tools, define the same predicate three times
   (`echidna_x`, `fuzz_x`, `property_x`) all delegating to one internal `_x()`.
   That is cheap and makes a single source of truth.

## C. NEVER express liveness as a fuzzer property

7. Property mode evaluates the predicate **after every single call**, including
   the very first one — which may legitimately revert or be a no-op. A
   `successCount > 0` "liveness" property therefore ALWAYS fails and produces a
   bogus violation that you will waste time chasing (it showed up as medusa
   "28 passed, 1 failed" twice).
   Fix: demote it to a non-matching name (`meta_*`, so no tool collects it) and
   assert liveness in a Forge unit test instead, where you control ordering:
   `assertGt(success, 0, "harness is degenerate")`. Liveness matters — it is what
   proves a "no violations" fuzz result means something — it just does not
   belong in property mode.

## D. Invariant choice for a Morpho-style lending market

Useful, price-independent accounting identities (all held over 20k+ calls):

| # | Property |
|---|----------|
| P1 | `totalSupplyAssets >= totalBorrowAssets` |
| P2 | `loanToken.balanceOf(market) + totalBorrowAssets >= totalSupplyAssets` |
| P3 | `collateralToken.balanceOf(market) >= sum(position.collateral)` over all actors |
| P4 | per-actor `supplyShares`/`borrowShares` sums <= market totals |
| P6 | a targeted liveness claim: the new post-maturity liquidation must not revert while the borrower carries debt (probe a suspected rounding/DoS lead) |

Notes:
- P2 must be `>=`, not `==`, so that direct donations by the fuzzer cannot look
  like violations.
- Do NOT assert "no unhealthy position exists": partial liquidation legitimately
  leaves one. Assert health only as a **post-condition of borrow /
  withdrawCollateral** (inside the action, right after a successful call) — that
  is exactly where a missing health check would show up.
- Clamp fuzzer inputs (`_clamp(v, lo, hi)`) so the search cannot degenerate into
  all-reverts; wrap external calls in `try/catch` and count successes/reverts so
  you can see whether the run was meaningful.
- Fund the harness as the liquidator (mint plenty + `approve(max)`) so a revert
  can never be blamed on insufficient balance.

### D2. MetaMorpho-style vault cap: assert it at the ACTION boundary, never globally

A "supply never exceeds the cap" invariant looks obvious and is **wrong** as a
global property. MetaMorpho documents it in `PendingLib`:

    struct MarketConfig {
        /// @notice The maximum amount of assets that can be allocated to the market.
        /// @dev The exposure to a given market can go beyond the cap in case of interest or donations.
        uint184 cap;

The cap bounds the **principal a supply action may add**, not the
mark-to-market value of an existing position. Interest on a fully-allocated
position legitimately lifts `expectedSupplyAssets(vault)` above `cap`, so a
global `supplied <= cap` property fails by design and wastes a whole fuzzing
round chasing a false positive.

Correct pattern:
- enforce it where a supply happens — in every deposit/mint/reallocate action,
  after the call, `if (_supplied() > _cap()) capBreachCount++;` (this catches a
  real cap-bypass, because a bypass shows up in the action that performs it);
- expose the counter as the property (`*_capRespectedAtActionTime()`) instead of
  recomputing the mark-to-market comparison;
- if you want a global check, bound the *shares* or compare against
  `cap + accrued-interest`, never against `cap`.

Proving which one you are looking at (do this before writing it up):
1. deposit exactly `cap` (`_supplyMorpho` reverts with AllCapsReached if any
   asset would be left unsupplied, so filling the cap needs an EXACT amount —
   a clamped/fuzzed amount will not land on it);
2. assert `supplied == cap` right after the fill;
3. try to add more principal → assert `supplied` is unchanged (cap binds);
4. borrow to create utilisation, advance time, then touch any accruing entry
   point → assert `supplied > cap` and print the excess.
Fira reference run: cap 100,000,000,000 → filled exactly → extra 1,000 refused →
mark after interest 100,000,854,771 (excess 854,771). Cap intact, behaviour
documented upstream.

Corollary for the report: when a fuzzer "finds" an invariant violation, FIRST ask
whether the invariant is something the upstream project explicitly documents as
false. A real finding survives that question; a wrong invariant does not — and
shipping it costs credibility.

## E. mythril on a Foundry project

8. **It ignores foundry.toml**, so:
   - remappings must be patched into
     `~/.local/lib/python3.12/site-packages/mythril/ethereum/util.py`
   - `solc` on a WSL machine cannot download from `solc-bin.ethereum.org` when
     DNS is filtered: fetch `solc-static-linux` on the Windows side and drop it
     at `~/.solcx/solc-v<version>` + `chmod +x`.

9. **`--solc-json` CLOBBERS the remappings you patched.**
   The upstream code is:
   ```python
   settings = {}
   settings["remappings"] = [ ... ]     # your patch
   if solc_settings_json:
       settings = json.load(f)          # <-- wipes remappings
   ```
   That combination manifests as `ParserError: Source "@openzeppelin/contracts/..."
   not found` — but *only* for files that actually use a remapped import, which
   makes it look random (a relative-import file works, the next one fails).
   Fix: move the remappings assignment to **after** the json load.

10. **"Stack too deep" when the project is built with `via_ir = true`.**
    mythril will not honour foundry.toml. Pass the setting explicitly:
    `myth analyze Contract.sol --solv 0.8.30 --solc-json viair.json`
    with `viair.json = {"viaIR": true, "optimizer": {"enabled": true, "runs": 200}}`.
    This unblocked a file that had previously been written off as unanalysable.

11. **Honesty note for the report**: symbolic execution depth on layered DeFi
    logic is shallow. "No issues were detected" is weak evidence, not proof of
    absence. Say so in the ledger rather than counting it as coverage won.

## F. Mainnet fork tests

12. Many free RPCs (publicnode, etc.) **reject archive requests**:
    `"Archive requests require a personal token"`. You then cannot pin an old
    block. Do not silently fork a different block and pretend it is the audited
    state — instead:
    - fork `latest`,
    - print `block.number` in `setUp()`,
    - **assert every precondition on-chain** inside the test
      (`assertTrue(CT.isExpired())`, `assertEq(token.balanceOf(x), 0)`, ...) so
      the test is self-validating and fails loudly if the world moved.
    - pin the block in `[rpc_endpoints]` only when you have an archive RPC.

13. `vm.createSelectFork("mainnet")` reads `[rpc_endpoints]` from foundry.toml —
    put the endpoint there rather than scattering `--fork-url` through scripts.

14. Funding: check the whale balance *before* writing the test
    (`cast call USDC "balanceOf(address)" <whale>`) — a "Binance wallet" can hold
    only 52k because it is an omnibus. Prefer `vm.deal` for ETH and impersonating
    a verified large ERC20 holder for tokens (USDC's storage layout defeats naive
    balance-slot writes).

## G. Finding class worth checking in Pendle/Morpho-style forks

15. **Permissionless redeem that consumes the CONTRACT's pooled balance.**
    If a redeem/mint helper computes
    `amount = min(_selfBalance(tokenA), balanceOf(tokenB))` and pays out to a
    **caller-supplied receiver**, then any token parked in that contract (which
    the contract's own natspec often *requires*: "must be transferred prior to
    calling") belongs to whoever calls next. This is a front-runnable theft
    primitive, and the protocol's own router frequently amplifies it by doing
    `transfer-in ; redeem` mid-call.
    Test it with: victim parks tokens (step 1), attacker calls step 2 and
    receives the payout, attacker holds zero of both tokens, gas only.
    Also grep the router for the same calls: the router using the primitive means
    an ordinary user's healthy path sweeps someone else's parked balance.

16. **Diff the callback-blob assembly.** Routers encode callback payloads with
    `mstore(add(res, 32/64/96/...))` and decode with
    `calldataload(add(data.offset, 32/64/...))`. A one-word offset error is
    silent and would corrupt every swap. Instead of reading it, inherit the real
    helper in a probe contract, expose the `internal` encoders/decoders, and
    round-trip all action types plus a no-length-prefix-shift check.

17. **Enumerate slippage guards per entry point** with a grep
    (`grep -n "function \|Slippage\|min[A-Z]"`), then confirm that entry points
    passing a placeholder (`minFwOut = 1`) are genuinely covered by a later
    token-level check (`_redeemFwToToken` -> `out.minTokenOut`). Missing guards
    hide in the function that delegates to another guard.

## H. Output hygiene across ALL of these tools

18. **Name every run's log file distinctly, and never let a retry write to the
    same path as the run you already consumed.** These tools fail several times
    before they work, and their orchestrating scripts usually end with
    `echo ALLDONE` — so the *script's* exit code is 0 even when the tool inside
    failed, and a delayed background notification will happily report
    "exit code 0 / ALLDONE" for a run that produced nothing. Concretely, on one
    engagement: a failed echidna attempt, a fixed run, and a final clean run all
    targeted `scanners/fuzz/echidna_property.txt`; only the last one survived, and
    the raw deploy-failure evidence was destroyed. Fix: `echidna_run1_FAILED.out`,
    `echidna_run3_clean.out`, `medusa3.txt`, `myth5.out`, plus a `README.txt` in
    the directory stating which file is authoritative, what each contains
    (successes/failures/gaps), and how to reproduce the failures.
19. The tool's real exit code must be captured **inside** the log
    (`echo "exit=$?" >> log` immediately after the tool call), not inferred from
    the wrapper script. And when a late notification contradicts a result you
    already consumed, re-verify the artifact on disk (recency + content markers)
    instead of trusting either the notification or your earlier read.

20. **Verify a COUNT before you publish it.** A plausible-looking shell pipeline can
    silently produce a wrong number, and once written into an evidence index or a
    report it becomes a false statement nobody re-checks. Real case: `grep -B0 -A0
    "No issues" out | wc -l` returned **11** for a file that contained exactly **6**
    matches, and the number was about to be written into the directory README as
    "11 clean contracts". It was caught only by re-counting with independent
    commands (`grep -c`, `wc -l`, `grep -c '^##########'`) and cross-checking the
    three against each other. Rule: for any number that goes into a deliverable,
    derive it twice by different means and make the totals reconcile (e.g.
    `4 + 6 + 2 = 12`). Prefer `grep -c` and `wc -l` over multi-flag `grep` piped
    into `wc`.

21. **After a `replace`-style patch to a long markdown/skill file, verify the
    STRUCTURE — do not assume the edit only touched what you aimed at.** A patch
    that replaced a section heading swallowed the whole adjacent section: section
    "G" disappeared and its items were orphaned below "H", and the file still looked
    fine on a casual skim. It was caught by a deliberate post-patch check:
    `grep -nE '^## [A-H]\.|^[0-9]+\. \*' <file>` then confirming every heading and
    every numbered item is present, in order, with no gaps. Same check applies to
    the numbered-item list in a directory README. Cheap, and it is the only thing
    that catches silent content loss in a text patch.

## I. Forge 1.7.x build-info breaks crytic-compile (slither / echidna / medusa all die)

22. **Symptom**: `slither . --compile-force-framework foundry --foundry-ignore-compile` (and echidna
    with `cryticArgs: ["--compile-force-framework","foundry"]`) raises
    `FileNotFoundError: .../out/build-info/<id>.output.json`, or with a stub placed there,
    `KeyError: 'output'`.
    **Cause**: crytic-compile 0.4.2's foundry platform delegates to `hardhat_like_parsing`, which needs
    `out/build-info/<id>.json` to carry `solcVersion`, `input` and `output`. Foundry 1.7.x writes a
    *compact* build-info holding only `id`, `source_id_to_path`, `language` — no `input`/`output`.
    Nothing in the project is wrong; the loader simply cannot read the new format.
    **Fix — synthesise a hardhat-shaped build-info.** Build the standard-JSON input yourself
    (sources inlined under their build-info paths, plus `remappings`, `optimizer`, `viaIR`,
    `evmVersion`, `outputSelection` including `"": ["ast"]`), compile it once with the exact solc
    (`bin/solc-<ver>.exe --standard-json input.json > output.json`), then write
    `{"id": <id>, "solcVersion": "0.8.24", "input": <input>, "output": <output>}` over
    `out/build-info/<id>.json` and delete any `<id>.output.json` stub. `--foundry-ignore-compile` then
    works for slither, echidna and medusa at once — one ~16-min viaIR compile buys every tool.
    Two traps in that synthesis: **do not pass `solcVersion` with a `+commit.<sha>` suffix** — slither's
    `incorrect_solc` detector does `int("24+commit")` and crashes the whole run *after* printing the real
    findings, which reads like "the analysis failed" when it did not — and keep the sources' keys
    identical to the build-info paths, or the compile succeeds but remapping-based imports miss.
23. **Cheaper alternative when you only need a fuzzer**: echidna also accepts the plain solc platform,
    which needs no build-info at all —
    `echidna test/x/X.sol --contract X --crytic-args "--compile-force-framework solc --solc-remaps @openzeppelin=node_modules/@openzeppelin"`.
    Run it from the project root so the harnesses' relative imports resolve; use it to keep a fuzzing
    batch moving while a build-info synthesis compiles in the background.

## J. Never design a callback/reentrancy exploit before checking the callee's mutability

24. **If the function you re-enter through is declared `view`/`pure` in the interface, the compiler
    emits a STATICCALL and no state change is possible.** The entire exploit class is dead on arrival,
    no matter how unguarded the caller is.
    Real cost: ~40 minutes of design and a near-miss PoC on a dispatcher whose `registerValidator` is
    deliberately *not* `nonReentrant` and takes an attacker-controlled address as a whitelisting
    contract — an apparently perfect reentrancy window. It is not, because
    `ISSVWhitelistingContract.isWhitelisted(...)` is declared `view` (`ERC165Checker.supportsInterface`
    likewise).
    Run this check first, before any PoC work:
    ```bash
    search_files pattern='function <name>\(' path=contracts/interfaces
    # `external view` -> STATICCALL (no reentrancy);  `external` -> real CALL (reentrancy possible)
    ```
    Only a genuine non-`view` external call makes the caller's missing `nonReentrant` interesting.
    Enumerate every external call site of the target with this lens, and write the result down as a
    verified negative — a closed lead is a deliverable, not wasted work.
