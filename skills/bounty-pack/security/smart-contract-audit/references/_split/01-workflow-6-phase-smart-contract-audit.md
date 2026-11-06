## Workflow — 6-Phase Smart Contract Audit

### Phase 1: Source Acquisition (15 min)

**Priority order:**
1. GitHub repo (if public) — clone directly
2. Blockscout API — `curl "https://eth.blockscout.com/api/v2/addresses/{ADDR}"` + `/source-code`
3. **Sourcify — works on ANY chain, no API key, no explorer account.** This is the first
   choice when the chain's explorer API needs a paid key (BscScan/Etherscan) and there is no
   Blockscout instance:
   ```bash
   curl -s "https://sourcify.dev/server/v2/contract/{CHAINID}/{addr}?fields=sources" -o dep.json
   # chainId: 1=ethereum 56=BSC 8453=base 137=polygon 42161=arbitrum 10=optimism
   ```
   - ⛔ **`?fields=sources` is REQUIRED.** Without it the response is only
     `{matchId, creationMatch, runtimeMatch, match, chainId, address}` — no name, no compiler,
     no `sources` — which reads like "not verified" but is just the default field selection.
   - ⛔ **The address must be lower-case.** A checksummed address returns HTTP 400
     `{"customCode":"invalid_parameter","message":"Invalid address: 0x…"}` *even for a verified
     contract*. Always `.lower()` before querying, then read the checksummed form back out.
   - `match: "exact_match"` = full match; `"match"` = partial (metadata differs, bytecode
     identical — still usable). A `400 invalid_parameter` on a lower-case address genuinely
     means "not in Sourcify" → fall through to Blockscout / the vendor repo.
   - Sources come back as `{"sources": {"<path>": {"content": "..."}}}`; the key is the
     *compiler's* import path, so match on `basename` to align them with the repo.
   A re-runnable version of this whole flow is in `scripts/sourcify_repo_diff.py`.
4. Etherscan API — needs API key (may not be available)
5. EVM decompiler — Dedaub web, Foundry `cast disassemble`

**Blockscout source download pattern (verified working 2026-09-30):**

The correct endpoint is `/api/v2/smart-contracts/{ADDR}` — it returns `name`, `file_path`,
`source_code`, `abi`, `additional_sources`, `compiler_version`, `optimization_runs`,
`verified_at`. No API key required. (`/api/v2/addresses/{ADDR}/source-code` is a different,
older shape — do not rely on it.)

```bash
curl -s "https://eth-sepolia.blockscout.com/api/v2/smart-contracts/{ADDR}" -o impl.json
python - <<'PY'
import json
d = json.load(open('impl.json', encoding='utf-8'))
print(d['name'], '|', d['file_path'], '| verified:', d['is_verified'])
print('compiler:', d['compiler_version'], '| opt:', d['optimization_enabled'], d['optimization_runs'])
open('Impl.sol', 'w', encoding='utf-8').write(d['source_code'])
json.dump(d['abi'], open('Impl.abi.json', 'w'), indent=1)
PY
```

**`match: null` from Sourcify is NOT proof the contract is unverified** — it only means
Sourcify does not have it. Try Blockscout before concluding "no source available".

**⛔ Cheapest and strongest "is the repo I was handed actually deployed?" proof: pull the live
sources and diff them.** The selector-diff section further down tells you whether a *fix* is
live; this tells you whether the *reading material* is live at all, and it is one curl per
contract. Do it before any deep review — it retires the entire "maybe the audit is against the
wrong revision" class of doubt, and it is a sentence you want in the report ("deployed bytecode
== repo HEAD, verified"), because it pre-empts the triager's first question.

```bash
curl -s "https://sourcify.dev/server/v2/contract/56/$addr?fields=sources" -o $name.json
```
```python
import json, os, re
def norm(s):                       # strip comments + all whitespace, then compare
    s = re.sub(r'//[^\n]*', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    return re.sub(r'\s+', '', s)
d  = json.load(open(f'{name}.json'))
src = d['sources']
hit = next(k for k in src if k.endswith('/' + os.path.basename(rel_repo_path)))
dep = src[hit]['content'] if isinstance(src[hit], dict) else src[hit]
repo = open(rel_repo_path, encoding='utf-8').read()
print(name, 'identical =', norm(dep) == norm(repo), len(dep), len(repo))
```
Worked 2026-10 on DeXe Protocol: a repo `HEAD` **11 months newer** than the bounty's stated
"last updated" date was still byte-identical on all 8 in-scope implementations — the vendor had
upgraded the proxies to the current code. Had the diff come back *different*, that is the
build-generation signal to switch to the selector diff + `cast getter` reverts and to say in the
report which reading material is deployed. `scripts/sourcify_repo_diff.py` runs this for a map
of `name → (address, repo path)`.

**⛔ Proxy targets: resolve the implementation first.** For an upgradeable contract the
verified source you want is on the *implementation*, not the proxy. Read the EIP-1967 slot:

```bash
cast storage {PROXY} 0xREDACTED_******** --rpc-url $RPC
# then fetch /api/v2/smart-contracts/{IMPL}
```

**⛔ When the public repo is STALE vs what is deployed:** if the vendor docs announce a new
contract version that appears in no public branch, the deployed implementation is the only
source of truth. Recover it (recipe above), then **recompile it with the verification
record's exact solc + optimizer_runs** — a clean build proves the flattened source is
complete and bytecode-consistent. This is how the Superstate Allowlist v4.2 (announced
September 2026, absent from all 21 public branches) was obtained and reviewed.

> Full step-by-step (submodule bootstrap, the foundry `src/src/src` remapping trap, slither
> `--build-info`, proxy-deployed PoC harness, public-RPC table, engagement anchors):
> `references/repo-bootstrap-and-onchain-source-recovery.md`

**If unverified:** Use `cast code ADDR` + `cast disassemble` + `cast selectors` + `cast 4byte SELECTOR`

**⛔ Vendor-run / self-hosted bounty programs (dApp + protocol): the program publishes its own scope
gate, and often its own source.** This is a different intake shape from HackerOne/Bugcrowd/Immunefi —
do the gate BEFORE recon, not at write-up. Fetch the program's own `/SECURITY.md` (usually linked
from a `/source/` page) and extract: scope IN/OUT, the **known-issues table** (`TS-001…` refs → a
do-not-report list), the severity **tier table** with its dollar bands, and the rules of engagement.
Findings the policy pre-excludes — owner/privileged-role issues on a single-key deployment, a
governance module that is not live, an explicitly named contract group — are unwinnable; filter them
out of the candidate list early.

When the project's repo is unreachable, the site is the primary source:
`curl -sL https://<site>/<project>-source.zip` returns the full source at the **deployed** commit, and
the dApp's `config.js` is the deployment manifest —
`grep -nE '0x[a-fA-F0-9]{40}' config.js` gives the name↔address map in one shot, and any
`// gen-N re-migration … Prev: 0x…` comment reveals which contracts were migrated and which fixes
already landed. If you cannot diff against the vendor's "mainnet source", say so in the report.

**Docs are usually GitBook — extract them machine-readably instead of scraping HTML.** Append **`.md`**
to the page URL (`https://docs.<host>/resources/audit-and-bug-bounty-programs.md`) to get the full page
as markdown, and `https://docs.<host>/llms.txt` lists every page as a link. One `curl` then yields the
scope IN/OUT, reward table and rules of engagement as clean text — the HTML for the same URL was 612 KB
of nav scaffolding versus 8 KB of markdown. Works for the whole docs tree, so pull the program page and
the deployment/network page together. The per-chain address manifest also lives in-repo:
`packages/core/networks/<chainid>.json` is the `contractName ↔ address` list for every deployed contract,
which is what turns "all UMA production contracts" into an actual target list.

Two cheap, decisive proofs to run before writing anything up:

- **Missing-selector proof (no forge needed):** `cast call <addr> "fn()(uint256)"` returning
  `execution reverted, data: "0x"` (EMPTY payload) means the selector does not exist and there is no
  fallback. Control with a known-good call in the same block, and back it with
  `grep -rn '<fn>' contracts/` showing the identifier only in the *caller*. That trio is a complete
  interface/implementation-drift finding.
- **Live balance-sheet invariant:** read the accounting counters plus the custody contract's ETH
  balance and assert the sheet balances (`escrow.balance == pot + unclaimedPool + cutAccrued`). A
  sheet that balances to the wei retires a whole class of "missing accounting" hypotheses — record
  it as a **verified negative**, since negatives are deliverables here. One that does not balance is
  an immediate candidate.

> Full recipe (policy-extraction table, `config.js` manifest, `cast` proofs, `via_ir` build note,
> un-guarded-function sweep, scope-flag template) and the TimbSwap worked example:
> `references/vendor-program-recon-and-scope-gate.md`

### Phase 2: Foundry Project Setup (10 min)

**⛔ STEP 0: VERIFY DEPENDENCIES EXIST before ANY tool execution.**
User correction: "loh, slither kan udh ada, kok miss dependency?"
- Check if `dependencies/` or `lib/` has actual `.sol` files: `find dependencies/ -name "*.sol" | head -5`
- If empty/partial → install deps BEFORE running slither/aderyn/mythril
- If `forge soldeer install` or `forge install` fails → use Windows workaround below

```bash
mkdir -p /path/to/audit && cd /path/to/audit
forge init --no-git --force
rm src/Counter.sol test/Counter.t.sol script/Counter.s.sol
cp /path/to/Contract.sol src/
mkdir -p src/interfaces
# Write minimal interfaces for Aave, Uniswap, OpenZeppelin, etc.
forge install OpenZeppelin/openzeppelin-contracts --no-git
cat > foundry.toml << 'EOF'
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
remappings = [
    "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/"
]
evm_version = "cancun"
optimizer = true
optimizer_runs = 200
# via_ir = true   # add ONLY if forge build fails: "Stack too deep. Try compiling with --via-ir".
                  # Costs a much slower build, and makes slither's compile step very slow — if you
                  # set it, run slither in the background with a long timeout, or lean on manual
                  # review + `cast` live reads instead. Do not write the contract off as unanalysable.
EOF
forge build
```

### ⛔ Windows Soldeer Dependency Workaround

**Known issue:** `forge soldeer install` fails on Windows when repos have deep paths like `certora/basic/specs/aux/AaveMath.spec` (exceeds MAX_PATH or contains reserved names).

**Proven workaround (Ern audit 2026-09-22):**
1. Check what soldeer already downloaded: `ls dependencies/`
2. Use GitHub API to list all `.sol` files at the specific commit:
   ```bash
   curl -sL "https://api.github.com/repos/OWNER/REPO/git/trees/COMMIT?recursive=1" | \
     python3 -c "import sys,json; [print(i['path']) for i in json.load(sys.stdin).get('tree',[]) if i['path'].endswith('.sol')]"
   ```
3. Batch-download with Python ThreadPoolExecutor (20 workers):
   ```python
   import concurrent.futures, urllib.request, os
   BASE = f"https://raw.githubusercontent.com/OWNER/REPO/{COMMIT}"
   def download(path):
       os.makedirs(os.path.dirname(path), exist_ok=True)
       urllib.request.urlretrieve(f"{BASE}/{path}", path)
   with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
       list(ex.map(download, sol_files))
   ```
4. Verify critical files exist: `ls dependencies/.../DataTypes.sol`

### ⛔ Vendor missing imports from their npm tarball (faster + exact-version)

For UMA-style repos a contract imports `@openzeppelin/contracts`, `@openzeppelin/contracts-upgradeable`,
`@gnosis.pm/zodiac`, `@maticnetwork/fx-portal`, `@eth-optimism/contracts`, … . `git clone`ing those
repos is slow (zodiac, optimism) or exceeds the 60 s tool limit entirely. Pull the **published npm
tarball** instead — exact version, small, seconds:

```bash
curl -sL "https://registry.npmjs.org/@eth-optimism/contracts/-/contracts-0.5.40.tgz" -o d.tgz
mkdir -p lib/eth-optimism-contracts && tar xzf d.tgz -C lib/eth-optimism-contracts --strip-components=1
```

⛔ **Two path traps, each of which costs a full rebuild:**
- `@openzeppelin/contracts` keeps sources under **`contracts/`**; `@openzeppelin/contracts-upgradeable`
  keeps them **at the package root** (`access/`, `proxy/`, …). So the remappings differ:
  `@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/` but
  `@openzeppelin/contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/` (NO `/contracts`).
  Symptom of getting it wrong: `Source "…/contracts/access/OwnableUpgradeable.sol" not found`.
- Some packages resolve from their own root too, e.g. `@eth-optimism/contracts/libraries/bridge/…`
  maps to `lib/eth-optimism-contracts/` (not `…/contracts/`).

Verify one import resolves before the next build (`find lib/<pkg> -name "<NeededFile>.sol"`), then
build **iteratively**: fix the first missing import → rebuild → repeat. Do NOT try to predict the whole
remapping set up front. For a directory that is genuinely out of scope (e.g. a `proxy-scripts/`
Uniswap broker needing 6 Uniswap packages), **move it out of `src/`** rather than chasing its deps —
one exclusion beats an hour of dependency archaeology. Worked live 2026-10: UMA `packages/core`
(256 .sol) → 335 artifacts + all key in-scope contracts compiled this way.

**Isolated analysis project (when main project won't compile):**
If tests have incompatible imports (e.g., `openzeppelin-contracts/` vs `@openzeppelin/contracts/`), create a minimal standalone project:
```bash
mkdir -p /tmp/audit/src /tmp/audit/lib
cp Contract.sol /tmp/audit/src/
cp -r dependencies/@openzeppelin-* /tmp/audit/lib/openzeppelin/
# Write minimal foundry.toml with correct remappings
cd /tmp/audit && forge init --no-git --force && forge build
# Then run slither from the clean project directory
```

**Common compilation issues:**
- `UNDERLYING` address passed as `address(pool)` instead of `address(token)` — check constructor params
- Missing interface functions — add stubs to interface files
- Address checksum errors — use `vm.addr(PRIVATE_KEY)` or correct checksum
- Em-dash characters in comments — replace with `--`
- Windows path length limits — use `git -c core.longpaths=true clone` as first attempt

### ⛔ Building a HARDHAT/JS repo under Foundry (the `forge build` that looks like a hang)

A JS project (hardhat + `node_modules`, no `lib/`) is the fastest way to get a whole-project
compilation for slither/echidna/mythril. Three traps make it look broken:

1. **`libs` silently pulls in `node_modules`**, so `forge build` compiles the entire dependency
   tree and appears to hang for 5+ min with an empty `out/`. Do NOT set
   `libs = ["node_modules"]` — foundry adds it anyway when the dir exists. Set only explicit
   `remappings` and leave the default `libs` alone:
   ```toml
   [profile.default]
   src = "contracts"
   out = "out"
   remappings = [
       "@openzeppelin/contracts/=node_modules/@openzeppelin/contracts/",
       "@openzeppelin/contracts-upgradeable/=node_modules/@openzeppelin/contracts-upgradeable/",
       "@solarity/solidity-lib/=node_modules/@solarity/solidity-lib/",
   ]
   solc = "0.8.20"        # copy hardhat.config.js settings verbatim
   evm_version = "paris"
   ```
   Redirect the build to a **file**, not `| tail` — piping buffers everything until exit, so a
   normal 3-minute build of ~190 files looks identical to a hang. Watch progress with
   `ls out | wc -l` climbing, or `tail -f` the log for `Compiling N files with Solc …`.
   Do not kill it before `ls out | wc -l` stops growing.
2. **Hardhat itself dies with `Error HH502: Couldn't download compiler version list`** when
   `binaries.soliditylang.org` / `solc-bin.ethereum.org` is unreachable. You do not have to fix
   hardhat — the exact compiler is usually already on disk, and crytic-compile finds it from
   `foundry.toml`'s `solc = "0.8.20"` (it literally runs `forge config --json`):
   `C:/Users/<user>/.solc-select/artifacts/solc-0.8.20/solc-0.8.20`. If it is genuinely absent,
   take the binary from **GitHub releases** (reachable when the soliditylang CDN is not):
   ```bash
   mkdir -p ~/.svm/0.8.20
   curl -sL "https://github.com/ethereum/solidity/releases/download/v0.8.20/solc-windows.exe" \
     -o ~/.svm/0.8.20/solc-0.8.20.exe        # solc-static-linux / solc-macos on those hosts
   forge build --use "C:/Users/<user>/.svm/0.8.20/solc-0.8.20.exe"
   ```
3. **Import-path duplication → `Error: Identifier already declared`.** Repos that mix
   `@openzeppelin/contracts/proxy/utils/Initializable.sol` (its own declaration) with the
   `-upgradeable` copy cannot be compiled in ONE unit. This is a property of the repo, not your
   setup — so **do not build a single "import every contract" aggregator file**
   (`contracts/_All.sol`); it will always trip this. Scan per top-level contract instead, or
   exclude the colliding pair from the aggregator and scan those two on their own.

### Phase 3: Static Analysis (10 min)

Load DeFi workflow and patterns first:
```
read_file('references/defi-dapp-workflow.md')   → audit workflow for DeFi dApps
read_file('references/defi-patterns.md')        → exploit catalog + PoC templates
```

```bash
# Native Python 3.14
slither src/Contract.sol 2>&1 | tee slither_report.txt
halmos --contract TestContract --function testSpecific

# WSL Ubuntu (via wrapper ~/go/bin/)
aderyn .
mythril analyze src/Contract.sol
```

**Slither finding triage:**
- `reentrancy-benign` → Check: is `nonReentrant` used? External calls mid-state-change?
- `unused-return` → Does callee revert on failure? If yes → informational. If no → exploitable.
- `timestamp` → Usually informational for DeFi
- `assembly` → Review inline assembly for stack manipulation bugs
- `incorrect-equality` → Can the compared values be manipulated?

### Phase 4: PoC Development (30-60 min)

**For EACH finding, write a Foundry PoC test.**

```solidity
contract FindingPoCTest is Test {
    function setUp() public { /* deploy mocks + target */ }
    function test_FindingDescription() public {
        // 1. Setup: create victims, fund accounts
        // 2. Attack: execute the exploit path
        // 3. Verify: assert vulnerability exists
        // 4. Clean up if needed
    }
}
```

**Mock contract patterns (see references/foundry-mock-templates.md):**
- MockAavePool — supply/withdraw with configurable failure modes
- MockAToken — mint/burn with name/symbol/decimals
- MockDex — exactInputSingle with fee simulation

**Common PoC pitfalls:**
1. `vm.warp()` required for time-locked functions
2. Mock tokens need `name()`, `symbol()`, `decimals()` if constructor calls them
3. `nonReentrant` blocks re-entry — test via callback, not same-function re-entry
4. Approval amounts — set `type(uint256).max` in mock setup
5. Balance assertions — use `assertGt` for relative checks, not exact amounts
6. **Fork tests: snapshot-then-delta, never an absolute balance.** On `--fork-url` the
   destination already holds live funds, so `assertEq(token.balanceOf(dest), expected)` is a
   guaranteed false failure that reads like a finding.
   `uint256 b = bal(dest); …act…; assertEq(bal(dest) - b, expected);`
7. **Every PoC needs a POSITIVE control**, not just a "bad thing happened" assertion — run the
   same path with the broken input replaced by a working one and assert it succeeds. That is
   what converts "your test might be wrong" into an accepted report. Plus a healthy-environment
   control so a revert is not just a broken RPC. Full shape: `onchain-finding-verification` §2b.

### Phase 5: Finding Verification (20 min)

**For each finding:**
1. Is the PoC passing? Does it demonstrate impact?
2. Is it exploitable in production? (access controls, timing, prerequisites)
3. What is the impact? Fund loss, state corruption, privilege escalation?
4. Is it in scope? Does the bounty program cover this contract/finding type?
5. Severity calibration — match severity to PROVEN impact

**Unchecked return value pattern:**
```solidity
// VULNERABLE
pool.withdraw(asset, amount, recipient);

// SAFE
(bool success, ) = pool.withdraw(asset, amount, recipient);
require(success, "Withdraw failed");
```

**Key question:** "Does the callee REVERT on failure, or return FALSE?"
- Reverts → unchecked return is informational (Aave V3 standard)
- Returns false → exploitable (phantom withdrawal, fund loss)

### Phase 6: Report Compilation

1. Executive Summary (protocol, scope, tools, findings count)
2. Findings table (severity, title, contract, line)
3. Each finding: Title, Severity, Location, Description, PoC, Impact, Fix
4. Test suite summary (X/Y tests passing)
5. Tools used and results

**Severity rules:**
- CRITICAL: Direct fund theft, complete account takeover
- HIGH: Significant fund loss, major state corruption
- MEDIUM: Limited fund loss, state corruption with conditions
- LOW: Minor issues, code quality, informational
- NEVER overclaim

**Impact writing — attacker perspective (MANDATORY):**
User correction (Ern audit 2026-09-22): "harus ad impact spt: 'as attacker i could...'"
Every finding's Impact section MUST include attacker-perspective statements:
```markdown
