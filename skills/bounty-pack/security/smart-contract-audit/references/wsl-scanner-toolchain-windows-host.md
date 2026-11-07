# WSL scanner toolchain on a Windows host (slither / aderyn / mythril / echidna)

Use when running the mandatory scanner suite for a Solidity audit on this Windows host, where
forge/cast live natively (`/home/agentuser/.foundry/bin`) but slither/aderyn/mythril/solc-select
live in WSL Ubuntu. Verified 2026-10-23 on the ACE audit (30 contracts, solc 0.8.19, viaIR).

Companion detail: `forge-buildinfo-and-deployed-source-verification.md` covers the forge ≥1.7
build-info synthesis; this file covers getting each *tool* to run at all.

## 1. ⛔ Project path must not contain spaces

`forge` remapping resolution silently mangles paths with spaces — symptoms: `Source
"lib/openzeppelin-contracts/contracts/..." not found. Searched: "/ace-audit"` (drive letter
stripped). Fix: work in a space-free path (`/home/agentuser/ace-audit`, NOT
`D:/data hermes/...`). Copy the project before bootstrapping.

## 2. ⛔ crytic-compile shells out to bare `forge` — WSL needs a shim

WSL inherits the Windows PATH, so `forge.exe` resolves (`/home/agentuser/.foundry/bin/forge.exe`)
but crytic-compile's foundry platform runs `forge config --json` — the bare name `forge` does not
exist in WSL and slither dies with `FileNotFoundError: 'forge'`.

Fix — shim at `~/.local/bin/forge`:

```bash
#!/bin/bash
exec /home/agentuser/.foundry/bin/forge.exe "$@"
```

⛔ **Write the shim from the Windows side** (`cat > .../forge-shim.sh <<'EOF'` then
`wsl -- cp .../forge-shim.sh ~/.local/bin/forge`). Writing it via a nested
`wsl -d Ubuntu -- bash -lc "printf '...\"\$@\"...'"` gets eaten by two quoting layers and
produces `exec forge.exe ""` — the symptom is `forge config --json` answering
`error: unrecognized subcommand ''`. Verify with `forge config --json | head -3` before
launching a 15-minute scan.

## 3. Per-tool invocation (all verified working)

### slither (0.11.6, WSL)

```bash
wsl -d Ubuntu -- bash -lc "bash /home/agentuser/ace-audit/scanners/run-slither.sh"
```

- `--solc-remaps` takes **ONE comma-separated argument**, not space-separated:
  `--solc-remaps @openzeppelin/contracts/=lib/openzeppelin-contracts/,@openzeppelin/contracts-upgradeable/=lib/openzeppelin-contracts-upgradeable/,@pythnetwork/pyth-sdk-solidity/=lib/pyth-sdk-solidity/`
  Space-separated → `slither: error: unrecognized arguments: <2nd remap>`.
- Per-file (`slither src/contracts/x.sol`) analyzes the file's full import closure — sufficient
  coverage without a whole-project build. With the shim present, foundry auto-detection works and
  recompiles per file (~3 min each; run as one background script, not 6 foreground calls).
- ⛔ **The run ends in `AssertionError` at `slither/detectors/statements/pyth_unchecked.py`**
  (slither 0.11.6 bug on Pyth-SDK-shaped code). It fires at the END, after every other detector
  has printed. The output before the traceback is a COMPLETE result for those detectors — record
  it as "ran; N detectors; terminal pyth_unchecked crash", never as NOT RUN and never as clean.
- Never count severities from console output (no `Impact:` field) — parse `--json` if you need counts.

### aderyn (WSL)

```bash
wsl -d Ubuntu -- bash -lc "cd /home/agentuser/ace-audit && aderyn . -o scanners/aderyn.md"
```

The Windows npm shim dies with a Node crash; the WSL binary works and produces the full report.

### mythril (0.24.8, WSL)

```bash
solc-select install 0.8.19   # once; mythril needs the exact pragma version
myth analyze src/contracts/x.sol --execution-timeout 240 -o json > out.json 2> out.log
```

- ⛔ mythril has **no `--solc-remaps` flag** (`unrecognized arguments`). Run from the project
  root and let crytic-compile read `foundry.toml` remappings itself.
- Exit 0 + `"issues": []` in the JSON = clean. Check the JSON, not the log tail.
- ⛔ **When the project is `viaIR = true` and remappings don't resolve, FLATTEN instead.**
  mythril's `--solc-json` takes the *settings object directly* — passing `{"settings": {...}}`
  errors `Unknown key "settings"`; and `--solc-args '--via-ir'` is rejected in JSON mode
  (`options are not supported in the current input mode`). Working path:
  ```bash
  forge flatten src/contracts/X.sol > scanners/flat/X.flat.sol
  # flatten emits a multi-version pragma -> rewrite to the single project version
  #   pragma solidity =0.8.28 ^0.8.19 ^0.8.20 ^0.8.22;  ->  pragma solidity 0.8.28;
  # then: myth analyze scanners/flat/X.flat.sol --solc-json scanners/flat/myth_solc.json
  #   myth_solc.json = {"remappings":[], "optimizer":{"enabled":true,"runs":700}, "viaIR":true}
  ```
  Expect **shallow coverage** on a viaIR flat file — on Klima it only reached OZ compiler stubs
  (`SWC-101` on `decimals()/totalSupply()/approve()` = FP, "internal compiler generated code")
  and never entered the swap/retire accounting. Label that a weak-coverage result, NOT a clean
  sweep.

### echidna (Windows native, `.foundry/bin/echidna.exe`)

```bash
echidna contracts/harness/X.sol --contract X --test-mode property --test-limit 30000 --seq-len 60
```

- Harness MUST live under `contracts/` (crytic won't compile `test/` harnesses) with `echidna_*`
  property prefixes (medusa wants `property_*` — check before budgeting a campaign).
- Grep the log for `Running slither failed` — a degraded campaign is "no counterexample in a
  degraded run", not "the invariant is safe".
- It runs `forge clean` first — expect the next `forge test` to recompile (viaIR: ~10 min).
- ⛔ **forge ≥1.7 build-info breaks echidna too** (`Failed to parse combined JSON file
  crytic-export/combined_solc.json` / `Unlinked libraries detected`). Two working fixes, in order:
  1. Pass the **single harness FILE** (not `.`) plus `--crytic-args`:
     ```bash
     echidna contracts/harness/X.sol --contract X --config echidna.yaml --test-mode property \
       --crytic-args "--compile-force-framework solc --solc-remaps @openzeppelin/=lib/openzeppelin-contracts/,@openzeppelin-upgradeable/=lib/openzeppelin-contracts-upgradeable/,forge-std/=lib/forge-std/src/,@prb/math/=lib/prb-math/src/,libraries/=src/libraries/,interfaces/=src/interfaces/"
     ```
     ⛔ `--compile-force-framework solc` on a **directory** fails (`Expected a Solidity file`).
     ⛔ remaps must be **comma-separated inside ONE arg** — space-separated remaps get eaten
     (`unrecognized arguments: forge-std/=...`).
  2. Or synthesise the hardhat-shaped build-info per `forge-buildinfo-and-deployed-source-verification.md`.
- ⛔ **Fork mode:** put `rpcUrl:` + `rpcBlock:` in `echidna.yaml` (CLI has no `--fork-url`). Without
  it the deploy runs on a fresh local chain where the target's dependencies don't exist — symptom
  is a constructor revert like `call 0x<credit>::approve(...) (0x)`. Also: keep the constructor
  free of external calls (approvals/deals) — do them lazily in the fuzz action, since the fork may
  not be available at deploy time.
- `--test-limit` is honoured; a 30k campaign on a forked Base target took ~15 min wall.

### halmos

Installed version rejected `--solver-timeout`. If the flags don't match, don't burn time — echidna
usually covers the invariant space. Record as NOT RUN with the reason.

## 3b. ⛔ Writing Foundry PoC/harness files on this host — four traps that cost the most time

1. **NEVER build a `.t.sol` with a shell heredoc.** On MSYS the heredoc silently fails to land the
   file; `forge test` then answers `No tests found in project!` (it skipped compilation because
   "No files changed"). This looks like a forge bug and is not. **Fix: write every test/harness
   file with `execute_code` → `open(ABS_PATH,'w').write(content)`** (or `write_file`), then run
   forge. Same rule for any script longer than a couple of lines.
2. **Every `0x…` address literal must be EIP-55 checksummed** or solc errors
   `Error (9429): This looks like an address but has an invalid checksum`. Addresses copied from
   `protocol-config/*.toml`, docs, or `cast` output are frequently lower-case. **Fix: after writing
   the file, loop `cast to-check-sum-address <addr>` over every literal and rewrite.** Do NOT
   hand-roll the checksum (sha3_256 ≠ keccak256 — a naive Python version produces wrong results).
   ```python
   import re, subprocess
   s = open(p, encoding='utf-8').read()
   for a in set(re.findall(r'0x[0-9a-fA-F]{40}', s)):
       b = subprocess.run(f'cast to-check-sum-address {a}', capture_output=True, text=True, shell=True).stdout.strip()
       if b.startswith('0x') and a != b: s = s.replace(a, b)
   open(p, 'w', encoding='utf-8').write(s)
   ```
3. **Interface structs in test files need named types, not inline tuples.** `function f(...(uint256,address))`
   in an interface errors `Expected type name`. Declare `struct CouponBurnParams { uint256 tonnes; address from; }`
   and use it. A returned struct tuple likewise needs a named struct type for the return.
4. **`console2.log` takes at most 4 args and no `(string, string, uint, uint)` mix beyond 4** —
   split long log lines into several calls (this bites when logging 5+ values).

## 3c. Fork RPC selection on Base (and the archive requirement)

Public Base RPCs that served a **pinned-block fork** during this engagement:
`https://base-mainnet.public.blastapi.io` (primary, worked for all fork tests),
`https://base.gateway.tenderly.co`, `https://base-pokt.nodies.app`.
⛔ `https://base.drpc.org` rate-limits hard mid-fork (`429 ... upgrade to paid plan`) and
`https://1rpc.io/base` is discontinued (`410`). Test a candidate with a one-test fork before
committing to a suite; a mid-run 429 surfaces as a bogus
`failed to get storage/account for 0x…` EVM error that reads like a target bug.

## 4. Ledger discipline for failed runs

A run that died before analysis (shim traceback, escaping bug, build-info error) is a TOOLING
FAILURE, not a result. Quarantine those logs (`scanners/_FAILED_TOOLING/`) and write a
`scanners/README.md` table separating REAL results from failures — otherwise a 29-line traceback
with zero findings sits next to real logs and reads as a clean sweep.
