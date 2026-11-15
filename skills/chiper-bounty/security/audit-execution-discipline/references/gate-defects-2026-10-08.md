# Gate defects: 18 ways the 0A–0F pipeline lied about itself

Found 2026-10-08 auditing Relay (relay.link) v3 Router —
`0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f`, tech `solidity web3 evm`.

**Why this file exists.** Every one of these defects let the pipeline look
healthy while doing nothing, or blocked a run that had actually succeeded. The
first symptom is almost always "the run failed" — but the run had *finished* and
the gate was rejecting it for a reason that was impossible to satisfy.

**End state after the fixes:** `audit-checkpoint: 33/33 checks passed`,
`🎯 FINAL GATE PASSED`, five smart-contract tools producing real results, and an
honest *negative* report. That is the bar.

---

## A. The tools never analysed the target

| # | symptom | root cause | fix |
|---|---|---|---|
| 1 | all SC tools "run" but produce nothing useful | `_resolve_solidity_source()` returned `list(rglob("*.sol"))[0]` → `src/common/Multicall3.sol` (a helper), not the target | score candidates: skip `common|lib|interfaces|test|script|mock|openzeppelin|solady|node_modules`, then largest file wins; honour a `sol-target.txt` pin |
| 2 | `import "@openzeppelin/..." cannot be found` | tools run with `cd <dir-of-the-.sol>` | run from the **project root** with the relative path |
| 3 | aderyn dies in WSL, slither fine | `remappings.txt` held **Windows** absolute paths (`/home/agentuser`), which WSL cannot resolve | write **relative** remappings (`@openzeppelin/=@openzeppelin/`) — works for both |
| 4 | `forge` exits `3221225725`, "has overflowed its stack" | `foundry.toml` had `src = "."`, so forge walked `lib/`'s nested duplicate packages | `src = "src"` (a real subdir) |
| 5 | `...\out\build-info is not a directory` | crytic-compile's Foundry backend needs a prior build | run `forge build --build-info` before slither |
| 6 | `can't install missing solc 0.8.28 in offline mode` | `offline = true` in `foundry.toml` blocks the solc download | drop `offline`; pin `solc_version` instead |
| 7 | slither marked `RAN_WITH_ERROR` after finding 68 issues | exit code judged as failure — **SC tools exit non-zero when they SUCCEED and find something** | completion-marker list overrides the exit code (`analyzed (`, `result(s) found`, `total calls`, `test summary`, `analysis was completed`, …) |
| 8 | echidna `No bytecode found for contract <path>` | missing `--contract <Name>` | pass it |
| 9 | medusa `Failed to initialize the test chain` | `--target-contract` does not exist | the flag is **`--target-contracts`** (plural) |

## B. The gate demanded things that cannot exist

| # | symptom | root cause | fix |
|---|---|---|---|
| 10 | 49/76 assets `NOT_RUN` on a contract target | the asset manifest is web-centric: subfinder/httpx/nuclei/ffuf cannot run without a hostname | split `WEB_ONLY` / `SC_ONLY`; `needed_for()` is track-aware via `_is_web3()` |
| 11 | `refs` class unpassable, forever | manifest named corpora like `bugbounty-playbook`, but `reference-usage.json` records the **fired FILENAME** (`403-bypass.md`) from `exploit-cookbook/references/` | match the real corpus; an asset naming no real corpus dir becomes `N/A` (a manifest error, not a run failure) |
| 12 | `asset-coverage FAIL 0C` for 105 "ready" candidates while 0F suppressed the report | the 0F draft/PDF requirement keyed off `ready-candidates.json`; the report step keyed off **validated** findings | drive 0F off `validated-findings.json`; 0 validated ⇒ `N/A — nothing to draft` |
| 13 | `triage-validation` / `onchain-finding-verification` impossible at 0D | their evidence is `findings.json`, produced at **0E** — the 0D gate runs first | move them to `late-skills.txt`, verified by `final_coverage_gate()` |
| 14 | `skill-usage.json missing` on every resume | the scaffold was written *inside* `if not loaded-skills.txt.exists()` | scaffold outside the guard, and re-read the skill list from `loaded-skills.txt` |
| 15 | `AUDIT-REPORT.md [NOT_RUN]` although refusing to report was CORRECT | 0F returned `None` when nothing cleared validation | write an explicit **negative** report (with counts) so a clean run can complete |
| 16 | `candidates.json exists` never satisfiable | legacy filename nothing writes any more | accept `review-candidates.json` / `findings.json` / `ready-candidates.json` |
| 17 | `live.txt / ports.txt / crawled.txt` fail on a contract | web recon artefacts required for a target with no hostname | `N/A (contract target)` on a web3 track |
| 18 | `Report contains severity / CWE` fails on a no-findings report | severity/CWE is meaningless when there are no findings | `N/A (0 validated findings)` |

## C. State handling that destroyed its own work

| # | symptom | root cause | fix |
|---|---|---|---|
| 19 | gate failures **oscillate**: `tools-usage.json not found` → `reference-usage.json missing` → `tools-usage.json not found` → HARD BLOCK | every `execute-*.py` wrote its usage JSON **once, at the very end of the file**. A step cut short (killed child, timeout, memory) produced **no file at all**; REWORK re-ran it identically and lost more each pass | persist on **every append** (`_PersistList`). Proof: force-full-execution killed at 75 s still left a valid 26-entry `tools-usage.json` |
| 20 | a re-run skips the whole SC step and analyses nothing | killing the orchestrator does **not** kill its grandchildren on Windows; the survivor wrote `force-state-*.json = complete` | `taskkill /F /T /PID` the whole tree **and** delete the state before any re-run |

## D. Remember when reading a run

- The orchestrator **captures** its children's stdout, so a long step writes **one**
  line and then nothing for minutes. A log that is not growing is **not** proof the
  run died — check whether evidence files are still appearing
  (`tool-evidence/`, `variants/`). Misreading this cost hours: "the run keeps dying"
  was wrong, three runs had completed and were being gate-blocked.
- A gate failure with **no** evidence file is a *harness* bug; a gate failure with
  evidence is a *substantive* one. Triage accordingly before touching the target.

## E. Verification that actually proves something

```bash
# one tool at a time, from the project root
cd <sol-source>                      # has remappings.txt + foundry.toml + out/build-info
slither "src/v3/Target.sol"           # expect "analyzed (N contracts …), M result(s) found"
aderyn .                              # expect "Running N detectors" + report.md
echidna "src/v3/Target.sol" --contract Target --test-mode assertion   # expect calls > 0
medusa fuzz --compilation-target "src/v3/Target.sol" --target-contracts Target --timeout 30
```
A tool that exits 0 with **0 results** on a non-trivial file has **not** run — read
the analysand path out of the evidence header before believing anything.
