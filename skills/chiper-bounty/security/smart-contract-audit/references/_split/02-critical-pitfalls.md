## Critical Pitfalls

### ⛔ Before ANY callback/reentrancy hypothesis: check the callee's mutability

An unguarded caller is not enough — if the function you re-enter through is declared `view`/`pure` in the
interface, the compiler emits a **STATICCALL** and no state change is possible. The whole exploit class
dies before you write a PoC.

Cost of skipping this check: ~40 minutes designing a double-withdrawal exploit through a dispatcher whose
`registerValidator` is deliberately *not* `nonReentrant` and accepts an attacker-controlled whitelisting
contract — killed by a single `external view` on `isWhitelisted`. Run
`search_files pattern='function <name>\(' path=contracts/interfaces` first and read the declaration.
Only a genuine non-`view` external call makes a missing `nonReentrant` interesting. Note the negative in
the ledger; a closed lead is a deliverable.

### ⛔ Delegation shape for deep source review: one narrow question, one file

Handing a subagent "read contract X and find bugs" does not fit its budget — the child spends
the whole wall clock on file reads and returns nothing usable (TimbSwap 2026-10: three
parallel deep-reads of separate contracts, three empty results). Shape the brief instead as a
single answerable question over a single file — *"does `_forfeitOne` in GameRegistry.sol ever
decrement `totalEthEscrow` twice for one ticket?"* — or read the contract in the main context,
where you can reason across the whole contract set and correlate with the live `cast` reads.
For most interface/accounting questions a `cast` probe or a 5-line fork test
(`onchain-finding-verification` §2b) answers faster than any delegation.

### ⛔ Deployed vs published source: VERIFY it, never assume it

The program's "codebase" link and an audit report's "final commit for mainnet launch is #X" are claims,
not facts. On SSV Network the live modules were built from a branch (`deploy/hotfix`) that is
`main` + 10 lines, so the default branch, the tag `v2.0.0`, `deploy/v2.0.0-mainnet` and the audited commit
all failed to reproduce the live bytecode. Two traps cost the most time:

1. **Never judge a difference by bytecode LENGTH.** Solidity appends CBOR metadata that embeds the
   *source paths* of the dependency closure, so a build using `project/contracts/...` is longer than one
   using `contracts/...` with identical code. A bogus "+231 bytes of unexplained code" evaporated to
   **0 differing bytes** once the tree was recompiled with its original paths. Compare the **code
   section**; treat the trailing metadata blob as noise.
2. **Before claiming "the deployed source is not published", enumerate every remote ref** —
   `git ls-remote --heads origin` — and grep each candidate for the suspect code, then quantify the
   delta with `git diff --stat <audited>..<branch> -- contracts/`. Fix branches are named after audit
   findings (`fix/remove-dead-cluster-flag`, `fix/sec-18`, …), and `deploy/hotfix` was the real launch build.
   Read the program's exclusion clause first: *"any issue documented … within any branch"* makes every bug
   with a `fix/*` branch unwinnable.

Recipes (verifier-alliance/eth-bytecode-db source recovery, the hardhat-shaped build-info synthesis that
makes slither/aderyn work on modern Foundry, finding the deployed branch, WSL quirks) live in the
`live-vs-source-bytecode-forensics` skill. Verification coverage is only complete when **every** in-scope
live contract has been diffed — including secondary proxies and tokens (the cSSV token was the one that
was nearly missed).

### ⛔ An interface method declared `view` is a STATICCALL — no reentrancy is possible

Before designing any reentrancy PoC, check the mutability of the interface you are re-entering through.
`ISSVWhitelistingContract.isWhitelisted` is declared `external view`, so the compiler emits STATICCALL:
an attacker-controlled whitelisting contract **cannot** mutate state from that callback — any state change
reverts. The entire "malicious whitelisting contract re-enters `removeOperator`" hypothesis was
unwinnable by construction, and it was caught only by reading the interface. Conversely, a `nonReentrant`
function can still be safe while an *unguarded* one is not, and vice versa — audit the external call's
enforced semantics, not just the modifier list.

### ⛔ Vendor docs that enumerate postcondition invariants are a free test oracle

Vendor repos for modular protocols ship `docs/FLOWS.md` / `docs/SPEC.md` with per-function
"Postcondition Invariants" and a "Global Invariants (Must Always Hold)" section (e.g.
`contract.ETH_balance ≈ Σ cluster balances + Σ operator earnings + networkTotalEarnings()`,
`ethDaoValidatorCount == Σ cluster.validatorCount`, `daoTotalEthVUnits == ethDaoValidatorCount*BPS + Σ deviations`,
`accEthPerShare` only increases). Harvest them verbatim: each one is a concrete, testable assertion, and a
*documented invariant the code can violate* is a finding whose impact is pre-agreed by the vendor's own
documentation. It also tells you which behaviours are deliberate (so you do not report them) versus
undeclared.

### On-chain state check BEFORE severity claims
User correction (Ern Protocol audit 2026-09-15): "Jgn kasih sy potensial, kasih yg real."
Never claim HIGH/CRITICAL on a contract without checking balance and activity first.
See onchain-finding-verification skill section "1b. Dormant contract triage."
Zero balance + zero txns = INFORMATIONAL regardless of code severity.

### ⛔ Unchecked Return Value — Do NOT Auto-escalate to HIGH
User correction (Ern audit 2026-09-22): "Saya mau cek dl temuannya valid atau gk"

**Pattern is real but severity depends on callee behavior, not just the pattern.**

When Slither/Aderyn flag `unused-return` on `pool.withdraw()`, `pool.supply()`, etc.:
- **FIRST check: Does the callee revert on failure?** If yes (Aave V3, Uniswap V3, most DEXes), the unchecked return is INFORMATIONAL/LOW — it's a defensive coding gap, not an exploit.
- **Do NOT claim "phantom withdrawal" or "permanent fund loss"** unless you can prove the callee can silently return 0 without reverting.
- Aave V3 `Pool.withdraw()` reverts on insufficient liquidity, invalid reserve, etc. The "silent return 0" scenario is theoretical for well-behaved protocols.
- Codehawks/Immunefi triagers consistently INVALIDATE unchecked-return reports on Aave V3 for this reason.

**Severity calibration for unchecked-return:**
| Callee Behavior | Severity |
|----------------|----------|
| Reverts on failure (Aave V3, Uniswap V3) | LOW/INFO — defensive gap |
| Can return false/0 without revert | HIGH — exploitable |
| No documented behavior | MEDIUM — needs verification |

**Before submitting unchecked-return finding:**
1. Read the callee's source code (on-chain or GitHub) — does it revert or return?
2. Check previous audits (Halborn, OpenZeppelin, etc.) — is this already known?
3. Write a Foundry fork test that DEMONSTRATES the silent failure — not just a narrative
4. If you can't demonstrate silent failure → submit as LOW/MEDIUM "missing balance-delta check"
5. NEVER submit as HIGH without on-chain PoC proving the callee can fail silently

### ⛔ Mandatory: Check Previous Audits Before Submission
User correction (Ern audit 2026-09-22): "Cek dulu apakah unchecked-return ini sudah pernah di-flag di audit itu."

Before submitting ANY finding:
1. Search for previous audit reports: `<target> audit <audit firm> <year>`
2. Check if the audit firm published a public report (Halborn, Trail of Bits, OpenZeppelin, Consensys Diligence)
3. Compare your findings against the audit's findings list
4. If your finding overlaps with an existing audit finding → it's a KNOWN ISSUE → not eligible for bounty
5. If the previous audit flagged it AND the fix was implemented → check if the fix is correct
6. If the previous audit missed it → strong signal it's a real finding, but still verify

**Example (ern.app):** Halborn audit 17 Feb 2026 — MUST check their public report before submitting unchecked-return findings.

### Do NOT conclude early
**User correction (Ern audit 2026-09-15):** "kamu blm ad cek secara menyeluruh dan detail memakai semua skill, tools, toolkit dan knowledge base, tapi sudah menyimpulkan bahwa ern udh solid"
- NEVER say "contract is solid" before running ALL tools and testing ALL vectors
- Even well-audited code has edge cases — immutable contracts especially
- Load all skills, run all tools, test all patterns BEFORE any conclusion

### Blockscout as primary source
Etherscan API often requires paid key. Blockscout is free:
- `GET /api/v2/addresses/{ADDR}` — contract info
- `GET /api/v2/addresses/{ADDR}/source-code` — verified source
- `GET /api/v2/addresses/{ADDR}/transactions` — deployer txs

### Unverified contracts
If source not on Blockscout/Etherscan/Sourcify:
1. `cast code ADDR` — get runtime bytecode
2. `cast disassemble BYTECODE` — opcodes
3. `cast selectors BYTECODE` — function selectors
4. `cast 4byte SELECTOR` — decode function names
5. Dedaub.net — web-based decompiler

### Foundry mock contracts
DeFi protocols depend on external systems (Aave, Uniswap, oracles). Mock them:
- Mocks must implement ALL functions the target calls
- Constructor params must match (e.g., `getReserveAToken()` for Aave)
- Silent failure mode for testing unchecked return values
- See `references/foundry-mock-templates.md` for templates

### OZ v5+ — `_transfer` is NOT virtual
OpenZeppelin 5.x removed `virtual` from `_transfer` in ERC20. You CANNOT override it:
```solidity
// ❌ FAILS in OZ 5.7.0: Error 4334: overriding function is not virtual
contract MaliciousToken is ERC20 {
    function _transfer(...) internal override { ... }
}

// ✅ WORKS: Manual IERC20 implementation (no OZ ERC20 inheritance)
interface IERC20 { function transfer(...) external returns (bool); ... }
contract ManualToken is IERC20 {
    mapping(address => uint256) private _bal;
    function _setBalance(address a, uint256 v) internal { _bal[a] = v; }
    function transfer(address t, uint256 a) external returns (bool) {
        require(_bal[msg.sender] >= a); _bal[msg.sender] -= a; _bal[t] += a; return true;
    }
    // ... balanceOf, totalSupply, etc.
}
```

### `vm.startPrank` + `new Constructor()` FAILS
Foundry's `vm.startPrank` persists for ALL subsequent calls including constructor. OZ
contracts call internal functions in constructors that conflict with pranked context:
```solidity
// ❌ FAILS: setUp deploys from address(0), not from allocator
vm.startPrank(allocator);
RD rd = new RD(...); // constructor runs as allocator

// ✅ WORKS: One-shot prank before new
vm.prank(allocator);
RD rd = new RD(...); // only the next external call is pranked
```
Cost: 4 debug cycles on Ern Protocol audit (2026-09-15).

### Struct qualification from external imports
When importing contracts with structs, always use `ContractName.StructName`:
```solidity
// ❌ Error 7920: Identifier not found or not unique
Allocation[] memory arr;

// ✅ Works
RewardsDistributor.Allocation[] memory arr;
```

### Echidna/Medusa: `crytic-compile` Skips `test/` Directory

**Known issue (Ern audit 2026-09-22):** When using `crytic-compile` (the compilation backend for both echidna and medusa), the tool runs `forge build --skip ./test/**` under the hood. This means test contracts (where echidna property functions and medusa fuzz targets live) are NEVER compiled into the artifacts. Result: "no assertion, property, optimization, or custom tests were found to fuzz".

**PROVEN WORKAROUND (ern.app 2026-09-22 — works 100%):**
Move test contracts into `src/` instead of `test/`. crytic-compile only skips `test/` and `script/`, not `src/`.
```bash
cp test/EchidnaTarget.sol src/EchidnaTarget.sol
forge build --force
# echidna now finds the contract
echidna . --contract ErnMedusaTest --test-mode assertion --test-limit 5000
# medusa now finds the contract
medusa fuzz --config medusa.json --compilation-target . --target-contracts ErnMedusaTest
```
**Results:** echidna ran 5,151 calls + medusa ran 2.5M calls, all passing.

**Other workarounds (if src/ move isn't viable):**
1. **Use Forge's built-in fuzz testing** — `forge test --match-test testFuzz -vv`
2. **Create isolated project** — Copy ONLY `src/` contracts + test file to a clean dir with `forge init`, no soldeer

**If using echidna directly (not via forge):**
- **Function prefixes are NOT the same across tools — this was wrong here until 2026-10-01:**
  - echidna → property mode collects `echidna_<name>() returns (bool)`
  - medusa  → property mode collects **`property_<name>() returns (bool)`**
  - `fuzz_<name>()` is **NOT** a medusa property prefix. Verified from a real medusa run: it
    classified `fuzz_cashConsistent()` as an *Assertion Test*, and only the `property_*`
    functions appeared under *Property Test*. So a harness written with `fuzz_*` silently
    gets no property coverage in medusa.
  - Safe pattern: one internal `_predicate()` and three thin wrappers
    (`echidna_x`, `fuzz_x`, `property_x`) all delegating to it — one source of truth, both
    tools work, and `forge test` can assert the same predicate too.
- **NEVER express liveness as a fuzzer property** (`successCount > 0`). Property mode is
  evaluated after EVERY call, including the first one which may legitimately revert or be a
  no-op, so such a property always fails and manufactures a bogus violation. Demote it to a
  non-matching name (`meta_*`) and assert liveness in a Forge unit test instead.
- Test file MUST be in `src/` or explicitly passed — never in `test/` with crytic-compile
- **echidna sends `balanceContract` ETH to the target's constructor** → a non-payable ctor
  reverts with *"Deploying the contract 0x00a3… failed (revert, out-of-gas, sending ether to
  a non-payable constructor, etc.)"*. Set `balanceContract: 0` and/or make the ctor `payable`.
- **crytic-compile deploys EVERY compiled contract**, so one contract elsewhere in the project
  with an unlinked library aborts the whole run:
  *"Unlinked libraries detected in bytecode of contract …FiraMarket"*. Build a **minimal
  sibling project** for fuzzing (harness + contract under test + its libs only).

> Full catalogue with every fix: `references/evm-fuzzing-and-tooling-pitfalls.md`

### Mythril: Python 3.14 Incompatibility

**Known issue:** Mythril's import chain (`mythril.plugin.interface → mythril.laser.plugin.builder → ... → mythril.laser.ethereum.state`) fails with Python 3.14 due to changed module loading. Error: `ImportError` deep in the stack.

**Workarounds:**
1. **WSL Ubuntu** — mythril in WSL uses Python 3.12 (still compatible). See proven workflow below.
2. **Python 3.12 venv** — `python3.12 -m venv mythril-env && source mythril-env/bin/activate && pip install mythril`
3. **Docker** — `docker run -v $(pwd):/src trailofbits/mythril myth analyze /src/Contract.sol`

**Proven Mythril WSL Full Setup (ern.app 2026-09-22):**

⚠️ WARP/VPN DNS blocks `solc-bin.ethereum.org` inside WSL — mythril can't auto-download solc. Must install manually.

```
Step 1: Download solc binary for Linux
  curl -sL "https://github.com/ethereum/solidity/releases/download/v0.8.35/solc-static-linux" -o /tmp/solc-0.8.35
  chmod +x /tmp/solc-0.8.35

Step 2: Place in WSL solcx directory
  mkdir -p ~/.solcx
  cp /tmp/solc-0.8.35 ~/.solcx/solc-v0.8.35
  chmod +x ~/.solcx/solc-v0.8.35

Step 3: Patch mythril util.py to add remappings
  Path: ~/.local/lib/python3.12/site-packages/mythril/ethereum/util.py
  Find: "    settings = {}"
  Replace with:
    settings = {}
    settings["remappings"] = [
        "@openzeppelin/contracts/=lib/openzeppelin/",
        "@/=src/",
        "aave-v3-origin/src/contracts/=lib/aave/src/contracts/"
    ]

Step 4: Patch mythril_disassembler.py to use SOLC env var
  Path: ~/.local/lib/python3.12/site-packages/mythril/mythril/mythril_disassembler.py
  Find the _init_solc_binary function, add at the TOP of the function body:
    solc_env = os.environ.get("SOLC")
    if solc_env:
        return solc_env

Step 5: Install setuptools (needed for pkg_resources)
  pip3 install --break-system-packages setuptools

Step 6: Run
  export SOLC=~/.solcx/solc-v0.8.35
  cd /path/to/audit
  python3 -m mythril.interfaces.cli analyze src/Contract.sol --solv 0.8.35 --execution-timeout 120
```

**Key gotchas:**
- Mythril uses `SOLC` env var (NOT `SOLC_BINARY`)
- `--solc-json` flag expects a solc settings JSON, NOT standard JSON input
- Remappings MUST go in the `settings` dict **before** `settings.update({"outputSelection": ...})`
- ⛔ **`--solc-json` CLOBBERS the remappings you patched.** Upstream code is
  `settings = {}` → `settings["remappings"] = [...]` → `if solc_json: settings = json.load(f)`,
  so the json load wipes them. Symptom is deceptive — a file using only *relative* imports
  succeeds while the next file dies with
  `ParserError: Source "@openzeppelin/contracts/..." not found`, which reads like a random
  per-file problem. Fix: assign `settings["remappings"]` **after** the `json.load(f)` line.
- ⛔ **"Stack too deep" means you must pass viaIR — mythril ignores foundry.toml.** A contract
  that only compiles with `via_ir = true` will fail mythril's own compile
  (`CompilerError: Stack too deep. Try compiling with --via-ir`). Pass it explicitly:
  `myth analyze X.sol --solv 0.8.30 --solc-json viair.json` where
  `viair.json = {"viaIR": true, "optimizer": {"enabled": true, "runs": 200}}`.
  Do NOT write such a contract off as "unanalysable".
- The wrapper `~/go/bin/myth` calls WSL recursively — always call `wsl -d Ubuntu --` directly
- After patching, verify syntax: `python3 -c "import py_compile; py_compile.compile('path/to/util.py', doraise=True)"`
- **Interpret results honestly.** `No issues were detected` from symbolic execution on layered
  DeFi logic (lending + vault + router + AMM) is WEAK evidence, not proof of absence. On the
  Fira engagement mythril was clean on 12 contracts and still missed the one real finding.

### ⛔ A passing PoC is NOT impact — read the live CONFIG before you claim anything

Proving the mechanism on the vendor's harness is the easy half. Before writing "Medium/High", read the
**live configuration the defect depends on**: feature flags, reward/limit parameters, and the token the
code would actually move. A proven double-grant of zero is worth zero.

DeXe 2026-10: the PoC for a duplicated proposal reward passed in two variants, yet the flagship
in-scope pool had `rewardToken = address(0)` and `executionReward = 0` — the entire reward system was
switched off there, so the defect moved nothing on any *listed* asset. Reading that config **before**
calibrating severity (not after) is the difference between a report and a wasted submission. It also
nearly produced the opposite error: `cast` mis-decoded the settings struct and reported
`duration = 0`, which the contract's own validator forbids, so that decode was a tool artifact, not a bug.

Checklist before any severity claim on a *configurable* defect:
1. read the parameter the exploit consumes (enabled flag, scale, limit, cap);
2. read the balance the exploit would move, **at the contract that would pay**;
3. if governance can change that parameter, say who can change it;
4. only then assign severity, and paste the config values into the report as evidence.

### ⛔ Fleet sweep — a defect disabled on the flagship may be live on siblings

Permissionless-factory protocols (DeXe, Morpho/Uniswap forks, Safe modules, …) deploy many instances
with **independent per-instance config**. "Disabled on the in-scope instance" ≠ "no impact anywhere",
and Immunefi's **Primacy of Impact** explicitly covers in-scope impacts on unlisted assets. Enumerate
the fleet before concluding — this is what turned a "value-less" finding back into a submittable one.

Recipe:
- find the enumerator: `PoolRegistry.countPools(name)` / `listPools(name, offset, limit)`, a factory's
  `DaoPoolDeployed`-style events, or a subgraph;
- per instance, resolve proxy → impl → the config the finding needs;
- filter to instances where the finding is **reachable** (every precondition true);
- rank the shortlist by at-risk balance, best first.

`templates/pool-fleet-config-sweep.py` is a working starter (raw JSON-RPC + manual ABI word decode, so
it is immune to the `cast` struct-decode trap above). Frame the result honestly: if the reachable
instances belong to third parties and the at-risk asset is their own token, say so up front rather than
implying the listed assets are affected.

### ⛔ Hardhat `HH502 Couldn't download compiler version list` — fix without network

Symptom: `npx hardhat compile` dies with
`Error HH502: Couldn't download compiler version list` because the host cannot reach
`binaries.soliditylang.org` (WARP/VPN/DNS filters). A repo with a `hardhat.config.js`
and no pre-existing native solc cannot bootstrap at all, which blocks its whole test suite.

Fix (verified 2026-10, DeXe Protocol on Windows): the needed solc is usually **already on
disk** via `solc-select` — `~/.solc-select/artifacts/solc-<ver>/solc-<ver>` — so hand
Hardhat's native-compiler cache the file plus a `list.json` and it skips download *and*
hash verification.

```
# from node_modules/hardhat/internal/solidity/compiler/downloader.js:
#   list.json path        = <compilersDir>/<platform>/list.json
#   binary path (win+zip) = <compilersDir>/<version>/solc.exe
#   isCompilerDownloaded() only stats that binary file
cp ~/.solc-select/artifacts/solc-0.8.20/solc-0.8.20 \
   ~/.cache/hardhat-nodejs/compilers-v2/0.8.20/solc.exe
# and write ~/.cache/hardhat-nodejs/compilers-v2/windows-amd64/list.json :
# {"builds":[{"version":"0.8.20","longVersion":"0.8.20+commit.a1b79de6",
#   "path":"solc-windows-amd64-v0.8.20+commit.a1b79de6.zip",
#   "keccak256":"0x<b9ad…>","sha256":"0xa0fa…","platform":"windows-amd64","urls":[…]}],
#  "releases":{},"latestRelease":"0.8.20"}
```

Notes: the cache-period is 360 s, but `_shouldDownloadCompilerList` is only consulted when the
build is absent from `list.json`, so a pre-seeded entry survives indefinitely. Delete any
`solc.exe.does.not.work` sentinel. First `npx hardhat compile` on a 129-contract repo with
`optimizer_runs = 200` then takes **10+ minutes** and prints the contract-sizer table at the end —
do not kill it early (this exact mistake was made twice).

### ⛔ Compiling a JS project with forge: drop `node_modules` from `libs`

`forge build` on a Hardhat repo appears to hang forever. Cause: foundry auto-adds
`node_modules` to `libs`, so it compiles every dependency source. Keep `libs` at its
default and declare explicit `remappings` only:

```toml
[profile.default]
src = "contracts"
solc = "0.8.20"
optimizer = true
optimizer_runs = 200
evm_version = "paris"
remappings = ["@openzeppelin/contracts/=node_modules/@openzeppelin/contracts/", ...]
```
Also: if `binaries.soliditylang.org` is blocked, download solc from the GitHub release
(`https://github.com/ethereum/solidity/releases/download/v0.8.20/solc-windows.exe`) into
`~/.svm/0.8.20/` and pass `forge build --use <path>`. And when crytic-compile/slither runs
`forge config --json` it picks up `solc-select`'s binary automatically, so no `--solc` is needed.

### ⛔ slither 0.11.6 `AssertionError` on `[a,b].asDynamic()` / `.call{value:}` — unrecoverable by patching

`slither .` aborts with a bare `AssertionError` at `slither/slithir/operations/member.py:33`
(`Member` constructed over a non-rvalue) on any contract using `[a, b].asDynamic()` array
literals or `x.call{value: v}(data)` chains. **Two patches were tried and BOTH fail:**
skipping the `Member` node breaks downstream IR extraction
(`SlithIRError: Not extracted … TMPCALL0 REF`); relaxing the assert reaches the same IR error.
Do not burn time patching it — record the file as `NOT RUN (tool)` in the ledger and cover it
by manual review, or pin/upgrade slither. (Files affected on DeXe: GovPool, GovUserKeeper,
PoolFactory, DistributionProposal — i.e. exactly the ones you most want scanned.)

### ⛔ PoC on a vendor test suite: inject the test, don't rebuild the deployment

When the target ships a mature test suite, its `beforeEach` already deploys the whole system
(registry, factory, pool, settings, user-keeper, validators, reward token). Do **not** hand-roll a
minimal harness — that is days of work and rarely matches production wiring. Instead:

1. `cp test/<Suite>.test.js test/POC.test.js`
2. Insert your `describe` **inside** an existing top-level describe (so it inherits that describe's
   `beforeEach`), e.g. immediately before the first nested `describe("init()", …)` — a plain string
   replace on a unique marker line. Generator script + `--grep` on your test name keeps the loop fast.
3. Helpers defined in the suite's closure (`succeedProposal`, `tokenBalance`, `deployPool`, …) are
   visible to a sibling describe, so you can reuse them.

Two traps that cost several iterations on DeXe (2026-10):
- **Nobody has deposited.** Vendor suites often only `mint`/`approve` in setup; `canCreate` then
  reverts with `Gov: low creating power`. Deposit explicitly for every account you use.
- **Quorum is relative to live total supply.** `getTotalPower()` returned `token.totalSupply()`, so
  your voting account must be minted a **dominant** share *after* reading the real number — log
  `getTotalPower()` and the voter's power before asserting, or you will silently never reach quorum
  (symptom: `moveProposalToValidators` reverts `Gov: can't be moved`, which looks like a logic bug in
  the target but is a fixture bug). Always instrument: print proposal state + powers at each step.

### ⛔ `cast call` mis-decodes structs whose last member is dynamic — fetch raw and decode yourself

Reading a live `ProposalSettings`-style struct via `cast call ... "(bool,bool,...,(address,uint256,uint256,uint256),string)"`
returned field values shifted by one (`duration = 0`, and a nonsense address inside the nested struct) —
the tuple printer mis-orders a struct that ends in a dynamic `string`. It *looks* like a target bug
(`GovSettings` forbids `duration == 0`), so it is an easy false lead.

Reliable recipe (verified 2026-10 on DeXe):
```bash
curl -s -X POST "$RPC" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x<addr>","data":"0x<sel><arg>"},"latest"]}' \
  -o raw.json
```
then split `result[2:]` into 32-byte words in Python and map fields **by hand**. Two self-checks that
make the decode trustworthy:
- **offset check** — the head is N words, so the dynamic member's offset word must read exactly `N*32`
  (DeXe: 15 words → `480`); if it doesn't, your field count is wrong.
- **cross-check every value against a second source** — the project's own deployment config
  (`deploy/config/configs/*.conf.js`) reproduced all 14 fields, including `PRECISION = 1e25` (so
  `quorum = 5e25` means "5%", not a broken value). Do NOT conclude "quorum is unreachable" before
  confirming `PRECISION` in `Globals.sol`.

Also: `cast rpc eth_call` through a shell mangles the returned hex (escapes break word alignment) —
write the JSON to a file with `curl` instead.

### ⛔ `wsl bash -lc "export PATH=$PATH:..."` explodes on Windows — never touch PATH via WSL

Running a WSL tool from the Windows shell with an inline PATH edit fails before the tool ever starts:

```
wsl -d Ubuntu -- bash -lc "cd /mnt/d/... && export PATH=\$PATH:/home/u/.local/bin && aderyn ."
# bash: line 1: export: `WARP:/mnt/c/Program': not a valid identifier
# bash: line 1: export: `Files/Git/cmd:...': not a valid identifier   (dozens of these)
```

Cause: the Windows `PATH` (full of spaces — `Program Files/...`, `Cloudflare`, `Docker Desktop`) is
inherited into the WSL bash and then re-parsed as part of the `export` statement. Fixes, in order of
preference:
1. **Don't set PATH at all** — invoke the binary by absolute path (`~/.local/bin/aderyn`).
2. Put the commands in a **`.sh` file with LF endings** on the host and run `wsl -d Ubuntu -- bash /mnt/d/.../run.sh`
   (also set `MSYS_NO_PATHCONV=1` on the Windows side, otherwise git-bash rewrites `/mnt/d/...` into `C:\...`).
3. If you must prepend, quote it: `export PATH="\$PATH:/home/u/.local/bin"`.

Sibling note: on this host WSL itself intermittently fails to boot
(`Wsl/Service/CreateInstance/CreateVm/ERROR_TIMEOUT`), which makes `aderyn` and `mythril` unusable
regardless of the PATH fix. Record those as `NOT RUN (environment)` in the coverage ledger rather than
retrying indefinitely — `forge` + `slither` (native Windows) still gave full compile coverage.

### ⛔ A proven code defect is NOT a funded impact — sweep every deployed INSTANCE before writing

The finding can be real, PoC-proven, and still worth **nothing**, because the flagship in-scope asset
may be configured so the defective path moves no value. Deciding submit/no-submit therefore needs a
second, separate proof: *is the reachable configuration live anywhere, and how much is at stake?*

Recipe (worked 2026-10 on DeXe, flipped a "do not submit" into a "reportable, with caveats"):

1. **Find the registry's enumerating getter.** DeXe's `PoolRegistry` exposes
   `countPools(string)` + `listPools(string,uint256,uint256)`; equivalents elsewhere are
   `getProxyPools`, `allPairsLength` + `allPairs`, factory `DaoPoolDeployed` logs, etc. For an
   upgradeable/registry-deployed protocol this is the complete instance list, and it is cheap.
2. **Decode each instance's LIVE config**, not the source defaults. For each pool: resolve its
   settings/keeper from a getter, read the config struct (see the raw-`eth_call` decode pitfall
   above), and read `balanceOf(instance)` of the payout token.
3. **Apply the precise reachability predicate** for the defect — not just "rewards enabled". For the
   DeXe duplicate-execution-reward bug it was: `validatorsVote == true` **AND**
   `executionReward > 0` **AND** `rewardToken != 0x0` **AND** pool balance > 0. Anything looser
   over-claims; anything tighter misses instances.
4. **Report the counts and the cash**, e.g. *228 pools deployed; 21 reachable; 66 with rewards but
   unreachable; flagship = rewards disabled; largest reachable budget 8.5e27*. That single table is
   what lets the operator and the triager price the finding, and it is also what you need for the
   honest caveats.
5. **State the two caveats that follow**, every time:
   - the **listed in-scope assets may be unaffected** (flag it up front, do not bury it); and
   - **the affected instances may be third-party** (permissionless-factory deployments whose payout
     tokens are their own, not the project's) — which is exactly what Primacy-of-Impact language
     covers, but the triager may not agree. Put both in the report and in the submission draft.
6. **Do not skip step 1-4 just because the defect is proven.** "PoC passes" answers *does the bug
   exist*; it does not answer *is anything at risk*. Skipping the sweep is how a session either
   over-sells a valueless finding or throws away a payable one.

Corollary: when the flagship's live config disables the path (e.g. DeXe's pool is
`rewardToken = 0x0, executionReward = 0, validatorsVote = false` — corroborated against
`deploy/config/configs/prod*.conf.js`), say so in the very first line of the finding. A triager who
finds that themselves after reading three pages will distrust the rest.

### Windows Tool Quirks (2026-09-22)

**Mythril wrapper recursive call:** `~/go/bin/myth` is a bash wrapper that calls `wsl -d Ubuntu -- bash -c "$HOME/.local/bin/myth $*"`. Inside WSL, this wrapper tries to call `wsl` again = recursive hang. Fix: call WSL directly.
```bash
# ❌ WRONG — recursive wrapper, hangs 30s+
~/go/bin/myth analyze src/Contract.sol

# ✅ CORRECT — direct WSL call
wsl -d Ubuntu -- myth analyze src/Contract.sol

# ✅ ALTERNATIVE — Python 3.12 venv on Windows
python3.12 -m venv mythril-env && source mythril-env/bin/activate
pip install mythril && myth analyze src/Contract.sol
```

**Echidna Windows paths:** echidna.exe on Windows needs `C:/` paths, NOT Unix `/tmp/` paths. crytic-compile rejects Unix-style paths.
```bash
# ❌ WRONG — crytic-compile "unrecognized arguments"
echidna /tmp/Contract.sol --contract Test

# ✅ CORRECT — Windows path
echidna "$HOME/project/src/Contract.sol" --contract Test

# ✅ CORRECT — with foundry compilation
echidna "C:/project" --contract Test --crytic-args "foundry"
```

**Echidna test functions:** Must use `echidna_*` prefix for property mode, NOT `test_*` (Foundry convention).
```solidity
// ❌ Echidna ignores these — "no tests found"
function test_balance() public view returns (bool) { ... }

// ✅ Echidna finds these
function echidna_balance_positive() public view returns (bool) { ... }
```

### File write size limit
`write_file` and `patch` tools have ~8K token limits. For large test files:
1. Write header + mocks first
2. Append test functions via Python terminal scripts
3. Use `python3 -c "with open(..., 'r') as f: ..."` for in-place edits
4. Heredocs fail on backticks and single quotes in Solidity — use Python file writes

### ⛔ Empty `lib/` submodules + the foundry `src/src/src` remapping trap

A `git clone --depth 1` of a public monorepo leaves every `lib/*` submodule EMPTY, so nothing
compiles and slither/aderyn/echidna are all dead on arrival. Fix:

```bash
git submodule update --init --depth 1 lib/forge-std lib/openzeppelin-contracts \
    lib/openzeppelin-contracts-upgradeable
# skip huge monorepos (chainlink); vendor the one interface file from a release TAG, not a branch
curl -sL "https://raw.githubusercontent.com/smartcontractkit/chainlink/v2.14.0/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol" -o <dest>/AggregatorV3Interface.sol
head -3 <dest>/AggregatorV3Interface.sol    # a 14-byte file means you got "404: Not Found"
```

Then the trap: foundry derives remappings from directory names, and **once `<lib>/src/` exists
it rewrites `<libname>/` → `<lib>/src/`**. An import written `chainlink/src/v0.8/...` resolves
to `lib/chainlink/src/src/v0.8/...`; creating that dir makes foundry detect it again and
escalate to `src/src/src/...`. Do not chase it — pin an explicit `remappings.txt` entry that
points at a directory **not** containing `src/` (`chainlink/=lib/chainlink-dep/`). Explicit
`remappings.txt` wins over the auto-derived mapping.

### ⛔ `slither .` on a foundry project needs `--build-info` first

```bash
forge build --build-info --skip test
slither . --foundry-ignore-compile
```

⛔ **forge ≥1.7 writes a build-info that crytic-compile cannot read.** `out/build-info/<id>.json` then
contains only `{id, source_id_to_path, language}` — no `input`/`output` — so the foundry platform blows up
(`FileNotFoundError: out/build-info/<id>.output.json` on 0.4.x, `KeyError: 'output'` on 0.4.2) and
**every** crytic-compile consumer dies with it: slither, aderyn, echidna, medusa. Two proven ways out
(2026-10, forge 1.7.1 + crytic-compile 0.4.2):

1. **Synthesize a hardhat-shaped build-info** — fixes slither, aderyn and medusa in one go. Build a
   `solc --standard-json` input from the compact file's `source_id_to_path` (same solc,
   `optimizer{runs}`, `viaIR`, `evmVersion`, remappings as foundry.toml), compile once, then write
   `out/build-info/<id>.json = {"id":<id>,"solcVersion":"0.8.24","input":<input>,"output":<output>}`
   and delete any `<id>.output.json`. Use a **bare** `0.8.24` for `solcVersion` — a `+commit.e11b9ed9`
   suffix makes slither's own `incorrect-solc` detector abort the whole run with
   `ValueError: invalid literal for int() with base 10: '24+commit'`, which silently truncates the
   detector list (the run looks like it found less than it did).
2. **Point echidna at the harness with the solc framework** — no build-info involved at all:
   `echidna test/echidna/X.sol --contract X --crytic-args "--compile-force-framework solc --solc-remaps @openzeppelin=node_modules/@openzeppelin"`.
   ~110 s compile + ~105 s slither warm-up per harness, and it compiles the vendor's own
   `test/echidna/*.sol` property harnesses directly.

> Full recipe (input generator, aderyn/mythril variants, the deployment-branch hunt):
> `references/deployed-vs-source-module-architecture.md`.

