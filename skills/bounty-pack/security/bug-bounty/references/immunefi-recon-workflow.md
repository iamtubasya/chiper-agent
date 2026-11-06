# Immunefi Target Recon Workflow

**Proven pattern** for systematic recon on Immunefi bounty targets. Works when Immunefi's Next.js SPA blocks curl/web_extract.

---

## Phase 0 — Extract the program JSON from the Next.js flight stream (DO THIS FIRST)

This supersedes the old "fall back to web_search and rebuild the scope by hand" advice. The program
page ships its entire structured record inside React Server Component flight chunks
(`self.__next_f.push([1,"…"])`), so one curl + one parser gives you the *authoritative* scope, rewards,
impacts, known-issues and out-of-scope text — no scraping of rendered HTML, no guessing.

`web_extract` will NOT work here: with the `ddgs` backend it is search-only and returns
`"DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content"`. Use curl.

```bash
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36" \
  "https://immunefi.com/bug-bounty/<PROGRAM>/information/" -o info.html
```

Then unwrap the flight payloads (write the parser to a FILE and run it — heredocs with `<<'PY'` mangle
backslashes inside regexes on git-bash/MSYS, and `re` raises `unterminated character set`):

> **Ready-to-run: `scripts/immunefi_program_extract.py <page.html> [--json out.json]`.** It does all of the
> below in one shot and prints the reward table, assets (+primacy flags), impacts, the **known-issues
> do-not-report list**, audits, codebase/docs links and the non-empty out-of-scope fields. Prefer it over
> re-typing the parser; keep the snippet below as the fallback if the page format shifts.

```python
# parse_flight.py
import json, sys
data = open(sys.argv[1], encoding='utf-8', errors='replace').read()
out, i, marker = [], 0, 'self.__next_f.push([1,'
while True:
    j = data.find(marker, i)
    if j < 0: break
    k = j + len(marker); assert data[k] == '"'; k += 1
    buf = []
    while k < len(data):
        c = data[k]
        if c == '\\': buf.append(data[k:k+2]); k += 2; continue
        if c == '"': k += 1; break
        buf.append(c); k += 1
    out.append(''.join(buf)); i = k
raw = ''.join(out).encode('utf-8', 'surrogatepass').decode('unicode_escape', errors='replace')
open('flight.txt', 'w', encoding='utf-8').write(raw)
```

The program object is the JSON after `{"bounty":` — balance the braces from that offset and `json.loads`
it. Fields that decide the whole engagement:

| field | why it matters |
|---|---|
| `maxBounty`, `bounties[]`, `rewardsToken`, `kyc` | reward model, whether KYC is required, per-severity bands |
| `assets[]` + `isPrimacyOfImpact` | in-scope addresses; a "Primacy of Impact" placeholder makes **unlisted project-owned contracts in scope** for the listed severities — enumerate the actual proxy+module set, not just the listed address |
| `impacts[]` | the only valid impact wording; severity must come from here |
| `knownIssues[]` | the do-not-report list (`$39`, `$3a`, … placeholders resolved from free-text blobs lower in the same payload) |
| `audits[]` | auditor + date; the report is a hard scope gate |
| `programCodebases`, `programDocumentations` | the *claimed* source of truth — verify it, do not trust it: see the `live-vs-source-bytecode-forensics` skill |
| `proofOfConceptType`, `attackTimeInterval`, `reductionPercentage` | PoC requirement, contest window, scoring |
| `eligibilityCriteria` (`no_ofac_sdn`, `no_employee`) | KYC / tax eligibility |

Two exclusion shapes that decide whether a target is worth starting at all — read them before recon:
1. *"any vulnerability identified in these reports that remains unfixed"* → the vendor audits are a scope gate.
2. *"any issue documented on <docs site> or within any branch of the specified repository"* → this is broad.
   Combined with a repo that carries named `fix/<audit-id>` branches, it converts nearly every known
   class into an exclusion. Check `git ls-remote --heads origin` early and price that in.

---

## Phase 1: Program Discovery (Ranked List)

When user asks for "immunefi" or "top programs":

```bash
# Immunefi is a Next.js SPA, but `curl` DOES return the whole program payload:
# scope, reward tiers, the known-issues list, the exclusion prose and the KYC flag all sit inside the
# RSC flight stream as self.__next_f.push([1,"<escaped json>"]) chunks. web_extract on the DuckDuckGo
# backend fails (search-only, cannot extract) — so go straight to curl with a browser UA.
# Full extraction recipe + the exclusion-pricing checklist: see "Program scope extraction" below.

# For *program discovery* (you do not know the slug yet) use web_search:
# Search queries:
# 1. "immunefi.com bug bounty active 2026 highest payout"
# 2. "site:immunefi.com bug bounty critical payout million"
# 3. Cross-reference with bounties listed on sherlock.xyz, bountyhunte.rs, smartcontractshacking.com
```

**Known data sources for Immunefi program listings:**
- `smartcontractshacking.com/tools/web3-auditing-competitions-and-bug-bounties/immunefi` — Live tracker, but JS-rendered (curl returns partial data)
- `arkadiyt/bounty-targets-data` — `data/immunefi_data.json` (BROKEN as of 2026-09, returns 404)
- `sherlock.xyz/post/best-web3-bug-bounties-in-2026-*` — Curated high-payout list
- `m3dython.com/blog/immunefi-review-2026` — Reviews + marquee programs

**Known top Immunefi programs (Sep 2026):**
| Program | Max Payout | Category |
|---------|-----------|----------|
| Uniswap v4 | $15.5M | DEX |
| LayerZero | $15M | Interoperability |
| Stargate | $10M | Bridge |
| MakerDAO | $10M | Stablecoin |
| Arbitrum | $2M | L2 |
| Lido | $2M | Liquid Staking |
| Aave | $1M | Lending |
| Wormhole | $1M | Bridge |
| 0x | $1M | DEX Aggregator |
| Injective | $500K | L1 DeFi |
| Sei | $500K | L1 Trading |
| BENQI | $500K | Avalanche Lending |
| Maple | $500K | Institutional Lending |
| Orca | $500K | Solana DEX |
| Nucleus | $500K | Yield |

---

## Phase 2: Single Target Deep Recon

After user selects a target, follow this 5-step workflow:

### Step 0: Get the program JSON out of the SPA — do not scrape, do not web_search

`web_extract` is usually wired to a search-only backend (DDGS) and returns
`"search-only backend and cannot extract URL content"` for immunefi.com, and
`curl` returns a Next.js shell. The scope/reward/known-issue data **is** in the fetched HTML, inside
the RSC flight stream: many `self.__next_f.push([1,"<escaped JS string>"])` chunks. Parse them, then
pull the program object out of the concatenated text.

```python
# save the page first: curl -sL -A "Mozilla/5.0" <url> -o page.html
import json
data = open('page.html', encoding='utf-8', errors='replace').read()
marker = 'self.__next_f.push([1,'
out, i = [], 0
while True:                                  # tolerant JS-string scanner (regex chokes on the escapes)
    j = data.find(marker, i)
    if j < 0: break
    k = j + len(marker) + 1                  # skip the opening quote
    buf = []
    while k < len(data):
        c = data[k]
        if c == '\\': buf.append(data[k:k+2]); k += 2; continue
        if c == '"': k += 1; break
        buf.append(c); k += 1
    out.append(''.join(buf)); i = k
raw = ''.join(out).encode('utf-8','surrogatepass').decode('unicode_escape', errors='replace')
i = raw.find('{"bounty"'); depth, k = 0, i           # brace-match the program object
while k < len(raw):
    if raw[k] == '{': depth += 1
    elif raw[k] == '}':
        depth -= 1
        if depth == 0: break
    k += 1
b = json.loads(raw[i:k+1])['bounty']
```

Useful keys on that object (all present, no HTML parsing needed): `maxBounty`, `kyc`, `audits[]`,
`assets[]` (with `url`, `description`, `isPrimacyOfImpact`), `impacts[]` (severity + title),
`programRewards`/`bounties[]` (per-severity `maxReward`/`minReward`/`fixedReward`),
`knownIssues[]` (the do-not-report list, each with a `link` to the closed report), `githubUrl`,
`programCodebases[]`, `programDocumentations[]`, and the whole `description`/`rewardsBody` text
(KYC terms, payment token, aggregate pool cap, repeatable-attack and prior-audit exclusions).

Two gotchas: Python on Windows resolves `/tmp/...` against the *current drive*, so write scratch files
to a relative path (or a real `C:/Users/<u>/AppData/Local/Temp` path) when the working directory is on
`D:`. And `tr -d '\000\014'` extracted text before grepping it — stray control bytes make `grep` call a
plain-text file "binary" and silently skip the matches you are looking for.

### Step 1: Immunefi Bounty Page → Rules + Payout Structure
```bash
curl -sL "https://immunefi.com/bug-bounty/<PROGRAM>/information/" \
  -H "User-Agent: Mozilla/5.0" | python3 -c "
import sys, re
html = sys.stdin.read()
html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', html)
lines = [l.strip() for l in text.split('\n') if l.strip()]
printing = False
for line in lines:
    if 'Maximum Bounty' in line or 'Live Since' in line:
        printing = True
    if printing:
        print(line[:200])
"
```

**Extract:** Max payout, payout calculation (e.g., "10% of funds affected"), severity tiers, PoC requirements, payment currency, KYC requirements, prohibited activities.

### Step 1b: Git history → the team's OWN recent security-fix commits
The single highest-signal recon step on a modern Immunefi repo. Shallow clones hide this, so
deepen first (`git fetch --depth=200 origin`), then:
```bash
git log --since='90 days ago' --format='%ci %h %s' | grep -iE "security|fix|advisory|ghsa|vuln|slippage|inflation"
git show --stat <fix-commit>            # files touched = the hot code
git diff <merge>^1 <merge> -- <file>    # the actual change
```
Real value: the fix names the EXACT bug class the team already cares about (e.g. Graph
2026-09: "prevent curation inflation attack" + an L2GNS slippage param). Then (a) read the
one audit report added with the fix to learn what is already "known", and (b) grep for SIBLING
code paths with the same root cause — that is where the next report CAN live (class: "missing
guard on the sibling function"), but clear two gates before you write it up:
  (1) **Same root cause or different?** If the "sibling" is the already-fixed bug applied to a
      second function, expect it to be triaged as a known-issue duplicate. Only a genuinely
      distinct root cause survives.
  (2) **Does the arithmetic actually lose value?** Model the value flow numerically before
      claiming theft. Graph 2026-10 example: the L2GNS sibling mints (`finishSubgraphTransferFromL1`,
      `_mintSignalFromL1`) looked like the fixed publishNewVersion slippage bug — but L2's
      `fixedReserveRatio = MAX_PPM` makes the bonding curve linear, so the pool round-trip
      (mint→burn) returns ~the same tokens regardless of prior inflation. Fewer *signal*, same
      *value* → nothing to report. Kill the lead instead of overclaiming. `packages/*/CHANGELOG.md` `Minor Changes` entries spell out
the deployed fix in plain English.

### Step 2: GitHub API → Contract File Inventory
```bash
# List repo contents
curl -s "https://api.github.com/repos/<ORG>/<REPO>/contents/" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data:
    print(f'{item[\"type\"]:4s} {item[\"name\"]:50s} {item.get(\"size\",\"\")}')
"

# List subdirectories (repeat for each dir)
curl -s "https://api.github.com/repos/<ORG>/<REPO>/contents/<DIR>" | ...
```

**Extract:** Contract files, repo structure, file sizes (large files = complex logic = more attack surface).

### Step 3: Protocol Docs → Architecture + Addresses
```bash
# Check docs for contract addresses, architecture, risks
curl -sL "https://docs.<protocol>.fi/" -H "User-Agent: Mozilla/5.0" | python3 -c "
import sys, re
html = sys.stdin.read()
# Extract nav links for doc structure
links = re.findall(r'href=[\"\'](/[^\"\']*)[\"\']', html)
for link in sorted(set(links))[:50]:
    print(link)
"
```

**Key pages to check:**
- `/resources/contracts` — Deployed contract addresses
- `/resources/risks` — Known risk factors (often reveals attack surface)
- `/architecture` — System design + trust boundaries
- `/llms.txt` or `/master.md` — GitBook full content dump (may be small)

### Step 4: Audit Reports → Known Vulnerabilities
```bash
# Dedaub audit reports (most Web3 audits are here)
curl -sL "https://dedaub.com/audits/<PROGRAM>/<audit-slug>/" -H "User-Agent: Mozilla/5.0" | python3 -c "
import sys, re
html = sys.stdin.read()
html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', html)
lines = [l.strip() for l in text.split('\n') if l.strip()]
for line in lines:
    if len(line) > 15:
        print(line[:180])
"
```

**Extract:** Known findings (especially unfixed or acknowledged), severity ratings, audit scope gaps.

### Step 5: Attack Surface Map
Compile everything into structured analysis:
- **Contract inventory** with file sizes
- **Deployed addresses** (mainnet)
- **Oracle dependencies** (Chainlink feeds, staleness risks)
- **Access control model** (proxy, timelock, admin keys)
- **Known audit gaps** (findings from Step 4 that weren't fully fixed)
- **Recommended attack vectors** ranked by potential impact

---

## Program scope extraction — the whole program JSON is in the flight payload

`https://immunefi.com/bug-bounty/<slug>/information/` is a Next.js RSC page. The rendered HTML is a
shell, but the complete program record is streamed in `self.__next_f.push([1,"…"])` chunks. Walk each
`push([1,"…"])` argument as a **JS string literal** (handle `\"` / `\\` escapes), unescape the lot, then
brace-balance the `{"bounty": …}`/`{"contentfulId":…}` object. One shot yields everything the UI shows,
machine-readable — no browser needed, and far cheaper than scraping:

- `maxBounty`, `bounties[]` / `rewards[]` per severity (`maxReward`, `minReward`, `fixedReward`,
  `rewardCalculationPercentage`, `rewardModel`)
- `kyc`, `launchDate`, `updatedDate`, `rewardsToken` / `rewardsTokenNetwork`
- `assets[]` (`url`, `type`, `description`, `isPrimacyOfImpact`) — note the **Primacy of Impact**
  placeholder: it pulls otherwise-unlisted project contracts into scope for the listed severities, so
  the *real* asset list is "the addresses this repo deploys", not the two URLs in the table
- `impacts[]` — the in-scope impact list; severity comes from HERE, not from CVSS
- **`knownIssues[]`** — the do-not-report list, typically `{"description": "$3a", "link": …}`
  referencing prose blocks that also live in the payload (grep `3a:` style keys)
- the exclusion prose (`outOfScopeAndRules`, `rewardsBody`, `programOverview`) carrying clauses like
  *"any vulnerability identified in these reports that remains unfixed, or any issue documented on
  docs.<x> or within any branch of the specified repository is strictly ineligible"*
- `audits[]` (URLs + dates) and `programCodebases[]`

### Price the exclusions BEFORE testing, not at write-up

1. Pull every **audit report** the program lists; diff your candidate list against their findings
   (`pdftotext -layout` then grep for the finding ids — the reports often include a test appendix that
   names the team's own "known issue" tests, which is also exclusion surface).
2. Enumerate the repo's **non-default branches**: `git ls-remote --heads origin`. A `fix/<finding-id>`
   or `deploy/hotfix` branch is the team's own record of a bug, and the "any branch" clause converts
   every one of those into an unwinnable item. Do this at scope time.
3. Verify the audited commit is what is actually deployed — see `smart-contract-audit` →
   `references/deployed-vs-source-module-architecture.md`. An audit's "final commit for launch" is a
   claim; if the launch build is a later branch, both your findings *and* the "already known" defence
   move. (SSV Network 2026-10: live modules = `main` + 10 lines from `deploy/hotfix`, absent from the
   audited commit — so the audit covers a tree 10 lines short of what runs.)
4. If the program is structurally closed — mature protocol, 5 audits, per-finding fix branches,
   explicit known-issues table — say so and plan for a verified-negative deliverable rather than
   burning the budget hunting variants of the report's own findings.

---

## Common Immunefi Target Patterns

### Lending Protocol (Compound-fork)
- QiToken/CToken model → check reentrancy, oracle manipulation, interest rate model abuse
- Comptroller → liquidation logic, collateral factor manipulation
- Proxy upgradeability → storage slot collision risks

### Liquid Staking
- Exchange rate calculation → flash-stake-and-borrow loops
- P-Chain delegation → validator selection influence
- MPC key management → threshold signature bypass

### Bridge / Cross-Chain
- Validator set → guardian compromise
- Message verification → signature forge
- Replay attacks → same message on multiple chains

### DEX
- Price oracle → TWAP manipulation
- Flash loan → sandwich attacks, price manipulation
- Fee logic → fee-on-transfer token edge cases

---

## Pitfalls

1. **Immunefi data source broken:** `arkadiyt/bounty-targets-data` immunefi_data.json returns 404 as of 2026-09. Do NOT fall back to web_search to reconstruct scope by hand — use the Phase 0 flight-stream parser above, which yields the program's own JSON (scope, rewards, impacts, known issues) verbatim.

1b. **Windows slither hangs on the project's solc version.** The Graph / Horizon repos pin
`solc_version = '0.8.35'`; solc-select usually lacks it and slither stalls trying to download,
so `slither . --foundry-compile-all` spins for 10+ min. Fix: build once with `forge build`
(fetches solc into `~/.svm/<ver>/`), then run
`slither . --solc "$HOME/.svm/0.8.35/solc-0.8.35" --filter-paths "node_modules|test|mocks"`.
That completes in ~2 min. Also raise the terminal timeout (this host defaults to 60s).

1c. **aderyn / mythril on Windows:** `@cyfrin/aderyn` npm refuses `Windows_NT`
("Platform ... is not supported"), and there is no Windows release asset (only macOS/Linux).
The WSL fallback is dead on this host: the distro will not boot —
`Wsl/Service/CreateInstance/CreateVm/ERROR_TIMEOUT`, reproduced after `wsl --shutdown`. Treat
aderyn/mythril as UNAVAILABLE and say so in the coverage ledger instead of budgeting time.
Related: **Docker Desktop's daemon comes and goes** (started intermittently during a session;
`docker info` failed for ~15 min then `docker ps` suddenly worked). Poll with
`docker ps` in a background loop rather than declaring Docker dead after one check.
**Rust tooling:** the default toolchain here is `stable-x86_64-pc-windows-gnu`, which fails with
`error calling dlltool 'dlltool.exe': program not found`. The MSVC toolchains are installed —
build with `cargo +stable-x86_64-pc-windows-msvc ...` (or pin it in `rust-toolchain.toml`).

1d. **pnpm monorepos:** `packages/address-book/src/<pkg>/addresses.json` are often one-line
*symlinks* (e.g. `../../../horizon/addresses.json`) so `json.load` throws
"Expecting value: line 1 column 1". Read `packages/<pkg>/addresses.json` instead; it maps every
deployed contract (plus proxy/implementation) per chain id — the fastest way to turn an Immunefi
scope table into a concrete target list.

1e. **`--depth=1` clone hides the whole engagement.** Nearly all the useful history is in the
last 90 days of commits; deepen the clone before any recon (Step 1b).

1f. **Off-chain / indexer software (e.g. graph-node, Rust): "the secret is in the logs" !=
"the secret is served".** Before claiming an info-disclosure via an API, verify the error is
actually *persisted* and *served*, not just printed. Graph-node concretely: a handler error does
become the subgraph's `fatalError.message` and IS served unauthenticated by the index-node API
(:8030 `indexingStatuses`), but graph-node classifies an `eth_call` transport failure as
**non-deterministic** and merely retries it — so the URL-bearing message never lands in the store.
Local graph-node PoC that works: docker-compose stack + `python3 -m http.server`-style JSON-RPC
proxy that forwards to a real public RPC (forward with `curl`, not urllib — some RPCs 403
Python's TLS/UA) so the subgraph is assigned, then fail `eth_call`; the served/not-served split
is decided by determinism, not by the error text. Also: node ports 8000/8001/8020/8030/8040 are
published by the repo's own `docker/docker-compose.yml`, and the admin JSON-RPC binds `0.0.0.0`
with **no auth** (its log misleadingly says "localhost").

2. **Smartcontractshacking.com is JS-rendered:** curl returns price/prize data but NOT program names. Use it for quick payout verification, not full enumeration.

3. **Dedaub audit reports are large:** 100KB+ HTML pages. The vulnerability summary is in the first ~2KB of extracted text — don't try to read the whole thing.

4. **Contract repos may be partial:** Some programs have private repos (e.g., BENQI Ignite). Focus on what's publicly available.

5. **Payout calculation matters:** Many Immunefi programs use "10% of funds affected up to $X" — this means your actual payout depends on proving LARGE economic damage, not just finding a bug.

6. **QI/token payment:** Some programs pay in native tokens (not USDC). Factor in token volatility and liquidity when assessing bounty attractiveness.
