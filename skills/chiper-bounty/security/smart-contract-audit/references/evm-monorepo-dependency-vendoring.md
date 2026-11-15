# Vendoring a Hardhat/yarn monorepo's deps so Foundry (and slither/aderyn) can build it

## When to use
`node_modules/` is absent (fresh clone) or `yarn` isn't installed, so the vendor's Hardhat build is
dead on arrival and every static tool fails with a wall of `ParserError: Source "@scope/pkg/... not
found`. You do **not** need Hardhat: copy the contracts tree into a Foundry project and vendor only
the imported packages. The contracts' *internal* imports are relative and keep working when you
preserve the directory shape.

Verified on `UMAprotocol/protocol` (packages/core, 256 `.sol`, solc 0.8.16) — 335 artifacts built,
all key contracts compiled.

## Procedure

```bash
mkdir -p build && cd build
mkdir -p src && cp -r <repo>/packages/core/contracts src/contracts   # PRESERVE the tree
```

Then vendor deps. **Fetch exact npm tarballs — do not `git clone` big dependency repos**: a
`git clone` of gnosis/zodiac timed out twice at 60s, while the npm tarball for the exact version
downloaded in seconds.

```bash
cd lib
fetch() { curl -sL -m 120 -A "Mozilla/5.0" "$1" -o pkg.tgz && mkdir -p "$2" && tar xzf pkg.tgz -C "$2" --strip-components=1; }
fetch https://registry.npmjs.org/@openzeppelin/contracts/-/contracts-4.9.6.tgz                           openzeppelin-contracts
fetch https://registry.npmjs.org/@openzeppelin/contracts-upgradeable/-/contracts-upgradeable-4.9.6.tgz   openzeppelin-contracts-upgradeable
fetch https://registry.npmjs.org/@gnosis.pm/zodiac/-/zodiac-3.2.0.tgz                                     zodiac
fetch https://registry.npmjs.org/@maticnetwork/fx-portal/-/fx-portal-1.0.4.tgz                            fx-portal
fetch https://registry.npmjs.org/@eth-optimism/contracts/-/contracts-0.5.40.tgz                           eth-optimism-contracts
git -c core.longpaths=true clone --depth 1 --branch v1.3.0 https://github.com/safe-global/safe-contracts.git safe-contracts
```

### ⛔ The package-layout trap — the remapping depends on where the sources sit
Two OpenZeppelin packages have **different shapes**, and getting this wrong produces a
`File not found` that looks like a missing dependency rather than a wrong remapping:

| package | sources live at | remapping |
|---|---|---|
| `@openzeppelin/contracts` | **`contracts/`** subdir | `@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/` |
| `@openzeppelin/contracts-upgradeable` | package **root** (`access/`, `proxy/`, …) | `@openzeppelin/contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/` — **no `contracts/`** |
| `@eth-optimism/contracts` | root (`libraries/`, `L1/`, `L2/`) | `@eth-optimism/contracts/=lib/eth-optimism-contracts/` |
| `@gnosis.pm/zodiac` | root (`contracts/`) | `@gnosis.pm/zodiac/=lib/zodiac/` |
| `@maticnetwork/fx-portal` | root (`contracts/tunnel/`) | `@maticnetwork/fx-portal/=lib/fx-portal/` |

Confirm before writing the remapping — `find <pkg> -name "<ImportedFile>.sol"` tells you the real path.

`foundry.toml`:
```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
remappings = [
  "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
  "@openzeppelin/contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/",
  "@gnosis.pm/zodiac/=lib/zodiac/",
  "@gnosis.pm/safe-contracts/=lib/safe-contracts/",
  "@maticnetwork/fx-portal/=lib/fx-portal/",
  "@eth-optimism/contracts/=lib/eth-optimism-contracts/",
]
solc_version = "0.8.16"
optimizer = true
optimizer_runs = 200
evm_version = "paris"
```
Omit `solc_version` only if the repo pins it inside the contracts; here the files are
`pragma solidity 0.8.16`, so pin it (never pass `--solc` to slither afterwards — see SKILL.md).

### Iterating on ParserErrors
**One file with an unvendored import fails the entire build** (solc compiles everything). Read the
error's `--> src/...` path and decide: vendor the dep, or move that directory out of `src/` if it is
not a production target. Example: `contracts/proxy-scripts/uniswap-broker/` needed Uniswap V3
libraries and is not a deployed oracle contract → `mv src/contracts/proxy-scripts _excluded/`.
Chase only what is actually in scope.

## Verify the build actually produced artifacts (not just "Compiler run successful")
```bash
forge build 2>&1 | grep -iE "compiler run|error" | tail -3
find out -name "*.json" ! -name "*.dbg.json" | wc -l          # expect hundreds
for c in OptimisticOracleV3 OptimisticOracleV2 VotingV2 Store Finder; do
  f=$(find out -iname "$c.json" | head -1); [ -n "$f" ] && echo "OK  $c" || echo "--  $c"
done
```
A green "Compiler run successful" with zero artifacts, or a missing target contract, means the
include tree was wrong — do not proceed to slither/aderyn on that basis.

## After the build
`forge build --build-info --skip test` then `slither . --foundry-ignore-compile --filter-paths
"lib/|test/|mock|Mock"`.
