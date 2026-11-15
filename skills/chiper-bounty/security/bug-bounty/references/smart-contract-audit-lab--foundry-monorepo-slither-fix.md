# Slither on Foundry Monorepos — Fix Guide

Verified: August 28, 2026 on The Graph Protocol (`arlo-bounty/contracts`)

## Problem
Slither fails on Foundry monorepos with: `out/build-info is not a directory` or `InvalidCompilation: Compilation failed`

## Root Causes
1. **Missing `pnpm install`** — monorepo dependencies not resolved
2. **Output directory mismatch** — Foundry `foundry.toml` sets `out = 'build'` but Slither always looks for `out/`
3. **Missing `--build-info`** — Slither needs source map files that `forge build` alone doesn't generate

## Fix (step by step)

```bash
# 1. Install monorepo dependencies
cd contracts-root
pnpm install   # (or npm install for npm monorepos)

# 2. Build each package with --build-info
cd packages/horizon
forge build --build-info    # generates out/build-info/*.json

# 3. Create symlink so Slither finds artifacts
#    (Slither hardcodes "out/" path for Foundry projects)
cmd.exe /c "mklink /J out build"   # Windows MSYS
# ln -s build out                  # Linux/Mac

# 4. Run Slither
slither . --filter-paths "node_modules|lib|cache_forge|build|test" \
  --detect reentrancy-eth,reentrancy-balance,reentrancy-no-eth,uninitialized-state,arbitrary-send-eth,suicidal,controlled-delegatecall

# 5. Repeat for each package in the monorepo
cd ../subgraph-service
forge build --build-info
cmd.exe /c "mklink /J out build"
slither . --filter-paths "..." --detect ...
```

## What does NOT work
- `--ignore-compile` — Slither still reads `out/build-info/` even with this flag, fails with `InvalidCompilation`
- `--foundry-compile-all` — Triggers `forge build --build-info` internally but may conflict with monorepo workspace settings
- Running Slither on root of monorepo without separate foundry.toml — Slither can't detect the framework

## Key Slither Flags for DeFi Audits
```bash
# Detectors (no --detect-all exists!)
--detect suicidal,arbitrary-send-eth,uninitialized-state,reentrancy-eth,reentrancy-balance,controlled-delegatecall,public-mappings-nested

# Path filtering (skip node_modules noise)
--filter-paths "node_modules|lib|cache_forge|build|test"

# Force framework when multiple detected
--compile-force-framework foundry
```

## Slither + Pnpm Monorepo Gotcha
The `pnpm install` at root may fail on some packages (e.g., `contracts-test` postinstall). This is OK — as long as the target package's node_modules are populated, Slither will work.
