# Hardhat / lerna monorepo → Foundry bootstrap

Use when the target repo is a **hardhat + yarn/lerna monorepo** (e.g. UMA's
`UMAprotocol/protocol`, `packages/core/contracts`) with no `node_modules`, and
`slither` / `aderyn` / `echidna` need a compile database. Do **not** fight hardhat —
stand up a sibling Foundry project instead. Verified 2026-10 on UMA core (256 `.sol`,
solc 0.8.16) → 335 artifacts, every key contract compiling.

## 1. Copy the contracts tree so RELATIVE imports resolve

```bash
mkdir -p build && cd build
mkdir -p src
cp -r <repo>/packages/core/contracts  src/contracts     # preserve the tree, don't flatten
```

UMA-style contracts import siblings by relative path (`../../data-verification-mechanism/...`),
so the directory shape must be preserved. Only the `@scope/pkg` imports need remappings.

## 2. Vendor dependencies from the **npm registry tarball**, not `git clone`

`git clone` of a large dep repo blows a 60 s foreground timeout and a wrong
org/repo name silently yields an empty dir (both happened: `UMAprotocol/oval` → 404,
`gnosis/zodiac` → timeout). The registry tarball is exact-version, small, and fast:

```bash
curl -sL "https://registry.npmjs.org/@gnosis.pm/zodiac/-/zodiac-3.2.0.tgz" -o z.tgz
mkdir -p lib/zodiac && tar xzf z.tgz -C lib/zodiac --strip-components=1
```

Same recipe fetched: `@maticnetwork/fx-portal 1.0.4`, `@eth-optimism/contracts 0.5.40`,
`@openzeppelin/contracts-upgradeable 4.9.6`. (Use `git clone --branch v4.9.6` only where
the tarball lacks what you need — e.g. `openzeppelin-contracts`.)

If a git clone is unavoidable, give the terminal tool an explicit long timeout
(`timeout: 300–420`) — the default 60 s will kill it mid-clone.

## 3. Remapping traps — INSPECT the extracted tree, never assume `contracts/`

The single highest-value check. Packages differ in whether sources sit under `contracts/`
or at the package root:

| import prefix | remapping (note the trailing segment) | layout |
|---|---|---|
| `@openzeppelin/contracts/` | `lib/openzeppelin-contracts/contracts/` | **has** `contracts/` |
| `@openzeppelin/contracts-upgradeable/` | `lib/openzeppelin-contracts-upgradeable/` | **NO** `contracts/` — sources at ROOT |
| `@eth-optimism/contracts/` (0.5.x) | `lib/eth-optimism-contracts/` | `libraries/` at root |
| `@gnosis.pm/zodiac/` | `lib/zodiac/` | needs OZ-upgradeable |
| `@gnosis.pm/safe-contracts/` | `lib/safe-contracts/` | `contracts/` |
| `@maticnetwork/fx-portal/` | `lib/fx-portal/` | `contracts/` |

Symptom of getting this wrong: `Source ".../contracts/access/OwnableUpgradeable.sol" not
found` on an upgradeable package — the giveaway is a *doubled* or *missing* `contracts/`
segment, and the fix is one line in `foundry.toml`.

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
remappings = [
  "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
  "@openzeppelin/contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/",
  "@eth-optimism/contracts/=lib/eth-optimism-contracts/",
  "@gnosis.pm/zodiac/=lib/zodiac/",
  "@gnosis.pm/safe-contracts/=lib/safe-contracts/",
  "@maticnetwork/fx-portal/=lib/fx-portal/",
]
solc_version = "0.8.16"      # match the repo's pragma, not "latest"
optimizer = true
optimizer_runs = 200
evm_version = "paris"
```

## 4. Iterate `forge build`; EXCLUDE what you don't need instead of chasing deps

Add remappings one error at a time until it compiles. Contracts that need a niche dep with no
security value for the engagement (UMA's Uniswap brokerage scripts under `proxy-scripts/`) should
be **moved out of `src/`** rather than vendoring Uniswap:

```bash
mkdir -p _excluded && mv src/contracts/proxy-scripts _excluded/
```

Then **write the exclusion into the tool-coverage ledger** — an excluded directory is a coverage gap,
and gaps must be listed, not silently dropped.

## 5. Notes that bite later

- `slither .` on a Foundry project **requires `forge build --build-info` first**, else it dies with
  `FileNotFoundError: out/build-info/<id>.output.json`. Exit code 127 can still mean the analysis
  *succeeded* — confirm via the final `analyzed (N contracts …), M result(s) found` line.
- aderyn: if the npm-installed shim dies with `MODULE_NOT_FOUND` (node shim broken), run the WSL build
  instead — `wsl -d Ubuntu -- bash -lc 'cd "/mnt/d/.../build" && aderyn . -o out.md'`. Quote paths that
  contain spaces.
- A repo that ships its **own** `foundry.toml` + `remappings.txt` + `lib/` (e.g. `oval-contracts`) needs
  only `git submodule update --init --recursive --depth 1` then `forge build` — no bootstrap needed.
- Newer solc for mythril: `curl -sL https://github.com/ethereum/solidity/releases/download/v0.8.16/solc-static-linux`
  → `~/.solcx/solc-v0.8.16` in WSL.
