# Aderyn WSL Workflow — Rust Binary Execution on Windows

## Problem
Aderyn is a Rust-based Solidity static analyzer. Official releases only provide binaries for:
- `x86_64-unknown-linux-gnu` (Linux x64)
- `aarch64-apple-darwin` (Apple Silicon)
- `x86_64-apple-darwin` (Intel Mac)

**No native Windows binary exists.** Attempting to run aderyn.exe on Windows produces: "This version of /home/agentuser/aderyn.exe is not compatible with the version of Windows you're running."

## Solution: Run Aderyn Inside WSL Ubuntu

### Installation (WSL Ubuntu)

```bash
# Step 1: Download Linux binary directly in WSL
cd /tmp
curl -sL --max-time 90 -o aderyn.tar.xz \
  "https://github.com/Cyfrin/aderyn/releases/download/aderyn-v0.6.8/aderyn-x86_64-unknown-linux-gnu.tar.xz"

# Step 2: Extract and place in PATH
mkdir -p ~/aderyn-wsl && tar xf aderyn.tar.xz -C ~/aderyn-wsl/
chmod +x ~/aderyn-wsl/aderyn-x86_64-unknown-linux-gnu/aderyn

# Step 3: Move to ~/.local/bin (standard user binary location)
mkdir -p ~/.local/bin
cp ~/aderyn-wsl/aderyn-x86_64-unknown-linux-gnu/aderyn ~/.local/bin/aderyn
chmod +x ~/.local/bin/aderyn

# Step 4: Verify installation
which aderyn
aderyn --version  # Should output: aderyn 0.6.8
```

### Usage via Windows Command (from force-full-execution.py)

```python
# In execute_all_tools(), smart_contract branch for tool == "aderyn":
wsl_root = self._win_to_wsl_path(str(Path(sol_src).parent))
cmd = f'wsl -d Ubuntu -- bash -c "PATH=/home/windows10/.local/bin:/usr/local/bin:/usr/bin:/bin /home/windows10/.local/bin/aderyn {wsl_root}"'
```

**Key points:**
- Always call WSL **directly**, NOT the wrapper `~/go/bin/myth` (myth itself also has recursive issues)
- Set **explicit PATH** (do NOT inherit Windows PATH — `C:\Program Files\...` breaks bash quoting)
- Pass the **DIRECTORY (project root)**, not a single file — aderyn scans all contracts in the root
- Path conversion must handle backslashes correctly (`/home/agentuser` → `/mnt/c/Users/...`)

### Full Command Example

```bash
# From Windows command line:
"/usr/bin/python3" -c "..."

# Which calls internally:
wsl -d Ubuntu -- bash -c "PATH=/home/windows10/.local/bin:/usr/local/bin:/usr/bin:/bin /home/windows10/.local/bin/aderyn /tmp/sc-test"
```

### Evidence Format

After execution, evidence file should include:
- Exit code (typically 0 for success)
- Output bytes showing scan results
- Reference: https://github.com/Cyfrin/aderyn
- Report confirmation: "✔ Aderyn did its job. Solidity's a bit safer now."

**Sample successful output size:** ~1500-2000 bytes

## Comparison with Other SC Tools

| Tool | OS Support | How to Call | Notes |
|------|-----------|-------------|-------|
| slither | Windows | Native exe | CD into contract dir first |
| echidna | Windows | Native exe | Use Windows paths + `--test-mode assertion` |
| medusa | Windows | Native exe | Use `fuzz --compilation-target` |
| mythril | WSL only | `wsl -d Ubuntu -- ...` | Patch `util.py` remappings + SOLC env var |
| **aderyn** | **WSL only** | **`wsl -d Ubuntu -- ...`** | **Pass DIRECTORY, not file** |

## Troubleshooting

### Error: "Not a directory"
- You passed a file path (`QuickTest.sol`) instead of directory (`sc-test`)
- Fix: `wsl -d Ubuntu -- bash -c ".../aderyn /mnt/c/path/to/dir"`

### Error: "bash -c 'PATH=...' broken quoting"
- Windows PATH contains spaces (`C:\Program Files`) that break bash -c
- Fix: Set **fully explicit PATH** without `$PATH` inheritance
- Correct: `PATH=/home/w10/.local/bin:/usr/local/bin:/usr/bin:/bin`
- Wrong: `PATH=/home/w10/.local/bin:$PATH`

### Error: "command not found" after PATH set
- Aderyn not installed in WSL
- Re-run installation steps inside WSL terminal
- Verify with `which aderyn` and `aderyn --version`

---

**Installation verified:** 2026-09-24, aderyn v0.6.8 installed in WSL Ubuntu `~/.local/bin/aderyn`, tested successfully with QuickTest.sol project. All 5 SC tools now execute real analysis: slither (102 detectors), aderyn (88 detectors), mythril (SWC-105 High found), echidna (50k calls), medusa (2.5M calls).
