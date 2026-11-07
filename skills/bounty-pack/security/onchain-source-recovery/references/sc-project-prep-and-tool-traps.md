# Preparing a recovered contract for the SC tools — and the 6 traps

Found 2026-10-08 during a real audit (Relay v3 Router, `0xb92fe925…`). The pipeline
reported "force execution COMPLETE" while **every single SC tool analysed a helper
library and produced nothing usable**. These are the traps, in the order they bite.

## Trap 1 — the wrong file is "the source"

`_resolve_solidity_source()` (force-full-execution.py) used to return
`list(sol_dir.rglob("*.sol"))[0]` — arbitrary rglob order. For a recovered Sourcify
dump that landed on `src/common/Multicall3.sol`.

Tell-tale: slither reports "analyzed (1 contracts …)" with only cosmetic hits
(unindexed-event, solc-version), and echidna/medusa say *"ABI is empty"* /
*"no assertion, property … found to fuzz"* — because the file they got has no
constructor and no properties.

**Fix** — score the candidates, and allow an explicit pin:

```python
aux = ("common","lib","interfaces","interface","test","script","mock",
       "node_modules","openzeppelin","solady","crytic")
def score(fp):
    parts = [x.lower() for x in fp.parts]
    is_aux = any(a in parts for a in aux)
    return (0 if not is_aux else 1, -fp.stat().st_size)   # main first, then biggest
best = sorted(sols, key=score)[0]
```

Also honour `output_dir/sol-target.txt` (first line = absolute path) so a caller can
pin the contract explicitly. Verify by printing the chosen path + how many helpers
were skipped.

## Trap 2 — remappings: an import prefix is a real directory

A Sourcify/Blockscout dump keeps the import prefixes as literal directories
(`@openzeppelin/…`, `solady/…`). Running the tool with `cd <dir-of-the-.sol>` and no
remappings makes every cross-prefix import fail:

```
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
^ Compilation Error
```

**Fix** — find the project ROOT (nearest ancestor containing any of
`@openzeppelin`, `solady`, `lib`, `src`, `node_modules`), write `remappings.txt`
there for each prefix that exists, and run every tool **from that root** with a
relative path:

```
@openzeppelin/=@openzeppelin/
solady/=solady/
```

**The targets MUST be RELATIVE, not absolute.** This was wrong here until
2026-10-08 and it silently breaks half the tool chain: slither/echidna run on
Windows (they would accept `/home/agentuser/<root>/@openzeppelin/`) but aderyn/myth run
inside WSL, where that path is meaningless —

```
Compilation Error: Source "/home/agentuser/sol-source/@openzeppelin/contracts/…" not found
```

and `/mnt/c/…` fails the other way round for the Windows tools. A root-relative
target (`@openzeppelin/=@openzeppelin/`) resolves correctly under **both**, so one
`remappings.txt` serves the whole split. Rewrite it on every prep — do not keep an
existing file that may hold absolute paths from an earlier version.

## Trap 3 — `src = "."` inside a recovered dump = forge stack overflow

A foundry.toml with `src = "."` makes forge walk the whole tree, including nested
duplicate package dirs under `lib/`:

```
'forge' returned non-zero exit code 3221225725
thread '<unknown>' (11736) has overflowed its stack
```

`3221225725` = `0xC00000FD` = stack overflow. **Fix**: `src = "src"` when a `src/`
dir exists, `libs = ["lib"]` only (never `[".", "lib"]`).

## Trap 4 — crytic-compile requires `out/build-info` to already exist

```
crytic_compile.platform.exceptions.InvalidCompilation:
  …out/build-info is not a directory. Can you run build command?
```

Having a `foundry.toml` is NOT enough — a build must have run. **Fix**: run
`forge build --build-info` at the root (bounded timeout ~900 s) before invoking
slither/aderyn/myth/echidna/medusa, and assert `out/build-info/` exists after.

## Trap 5 — `offline = true` silently blocks the solc download

```
Error: can't install missing solc 0.8.28 in offline mode
```

An `offline = true` line (added to "be safe") makes forge refuse to fetch the
compiler pinned by `solc_version`. **Fix**: do NOT set `offline` in the generated
profile. Let the first build pull solc, then everything else works from cache.

## Trap 6 — stale crytic artefacts make crytic pick the wrong framework

```
Multiple frameworks detected: Foundry, solc, Solc-json. Using Foundry (highest priority)
```

Leftover `crytic-export/`, `crytic-compile.json`, `combined_solc.json` from an
earlier attempt confuse the framework detection. **Fix**: delete them at prep time
before writing the fresh project files.

## Known-good generated project

```toml
[profile.default]
src = "src"          # NOT "."
out = "out"
libs = ["lib"]
solc_version = "0.8.28"
optimizer = true
optimizer_runs = 200000
via_ir = true
# do NOT add offline = true
```

## Per-tool invocation (Windows host + WSL split)

| tool | run from | form |
|---|---|---|
| slither | project root | `cd /d "<root>" && slither "<rel-path>"` (absolute Windows paths get mangled by crytic) |
| aderyn | WSL, project root | `wsl -d Ubuntu -- bash -c "PATH=… aderyn /mnt/c/…/<root>"` — needs the RELATIVE remappings above |
| myth | WSL | `cd <wsl-root> && SOLC=<solc> myth analyze "<rel-path>" --execution-timeout 240 --solver-timeout 20000 -t 1 --no-onchain-data` |
| echidna | project root | `cd /d "<root>" && echidna "<rel-path>" --contract <Name> --test-mode assertion` |
| medusa | project root | `cd /d "<root>" && medusa fuzz --compilation-target "<rel-path>" --target-contracts <Name> --timeout 30` |

**The two flags on the last two rows are not optional** — without them the tool
starts, reports a problem that reads like a target quirk, and analyses nothing:

- `echidna … --contract <Name>` — omit it and echidna treats the *path* as a contract
  name: `No bytecode found for contract "C:/…/RelayRouterV3.sol"`.
- `medusa … --target-contracts <Name>` — note the **plural**. The singular
  `--target-contract` does not exist (`unknown flag`); omit both and you get
  `Failed to initialize the test chain / ‣ specify target contract(s)`.

Use the `.sol` **stem** as `<Name>` (`RelayRouterV3.sol` → `RelayRouterV3`).

Keep the WSL invocations' quoting SIMPLE. An over-escaped nested `\\\\"` truncates
the path and produces `FileNotFoundError` on a half-written filename — that is a
quoting bug, not a missing file.

## "RAN_WITH_ERROR" is not automatically a failure

slither/aderyn exit non-zero when they FIND issues. Judge by the evidence body, not
the exit code: look for `analyzed (N contracts … M result(s) found` and the
`Detector:` lines. A file containing a Python traceback is a real failure; a file
containing findings + a non-zero code is success.

## Re-running: kill the whole tree and the state, or the run is a silent no-op

Killing the orchestrator on Windows does **not** kill its grandchildren. A
`force-full-execution` child keeps running, finishes, and writes
`trackers/force-state-<target>.json` with `status=complete`. The next run then
prints

```
STEP 1: SKIP force-full-execution (force-state sudah complete)
```

and analyses **nothing** — while the evidence from the previous attempt is
already deleted, so the gate reports
`Evidence files missing for: ['slither', 'aderyn', 'myth']`.

Before any re-run:

```bash
# kill the tree, not just the parent
wmic process where "commandline like '%force-full-execution%'" get processid
taskkill /F /T /PID <pid>
rm -f trackers/*<target>*                 # force-state + pipeline state
rm -rf <out>/tool-evidence <out>/tools-usage.json <out>/sol-source/out
```

Then confirm `force-state-<target>.json` is gone before starting. A "resume" that
skips the step you are trying to fix is worse than starting over.

## What good looks like

Before the fixes: `Multicall3.sol analyzed (1 contracts)`, 6 cosmetic results.
After: `src/v3/RelayRouterV3.sol analyzed (8 contracts with 102 detectors), 68 result(s) found`
— including a High `arbitrary-send-eth` on the real money path.

If the result count and the analysed file are not printed, you cannot tell success
from a silent wrong-file scan. Always surface both.
