# Windows Audit Tool Status & Installation Notes

Last verified: 27 Aug 2026

> **Broad tool install guide** (Go tools, Python tools, system tools): see `references/tool-installation-windows.md`
> This file focuses on **smart contract / Solidity audit tools** specifically.

## Current Tool Inventory (Windows 10 + MSYS git-bash)

| Tool | Version | Install Method | Status |
|------|---------|---------------|--------|
| Foundry (forge/cast/anvil) | 1.7.1 | `~/.foundry/bin` | ✅ Native Windows |
| Slither | 0.11.6 | pip install | ✅ Native Windows |
| Z3 solver | 4.12.6 | pip install | ✅ Native Windows |
| Halmos | 0.2.0 | `pip install --only-binary :all: halmos` | ✅ Native Windows |
| Echidna | 2.3.3 | GitHub release zip → `~/.foundry/bin/echidna.exe` | ✅ NEW |
| Semgrep | 1.175.0 | pip install semgrep | ✅ NEW |
| Mythril | — | coincurve build fails on Windows | ❌ Use WSL2 |
| Aderyn | — | No Windows binary; cargo install fails (getrandom) | ❌ Use Slither instead |

## Echidna 2.3.3 — Windows Installation

Echidna ships a Windows binary. curl often fails on GitHub release URLs from MSYS; use PowerShell instead:

```powershell
powershell.exe -Command "Invoke-WebRequest -Uri 'https://github.com/crytic/echidna/releases/download/v2.3.3/echidna-2.3.3-x86_64-windows.zip' -OutFile 'C:\Users\WINDOWS10\.foundry\bin\echidna.zip'"
cd ~/.foundry/bin && unzip -o echidna.zip && rm echidna.zip
```

Verify: `echidna.exe --version` → `Echidna 2.3.3`

**Usage (for DeFi bounty targets):**
```bash
# Basic fuzz test
echidna-test contracts/Exploit.sol --contract ExploitTest

# With config
echidna-test contracts/Exploit.sol --config echidna.yaml

# Property functions must return bool
# Name them something_YYYYMMDD (auto-named in config)
```

## Semgrep 1.175.0 — Windows Installation

```bash
python3 -m pip install semgrep
```

**Deprecation note:** Running via `python -m semgrep` is deprecated as of 1.38.0. Use bare `semgrep` instead:
```bash
semgrep scan --config p/solidity contracts/
semgrep scan --config "r/solidity" contracts/
```

**Custom rules for bounty targets:**
```yaml
# .semgrep.yml — custom rules
rules:
  - id: unchecked-return-value
    pattern: |
      $CALL;
    message: "Unchecked external call return value"
    languages: [solidity]
    severity: WARNING
    paths:
      include: ["src/**/*.sol"]
```

## Aderyn — Not Available on Windows

No pre-built Windows binary exists (only macOS arm64/x86_64). `cargo install aderyn` fails on Windows due to `getrandom` crate compilation error. WSL2 cargo install times out (120s+ build).

**Workaround:** Use Slither for static analysis coverage. Slither detectors overlap significantly with Aderyn's feature set. If Aderyn is specifically needed, run it inside a Docker container:
```bash
docker run -v "$(pwd):/src" cyfrin/aderyn /src
```

## Mythril — WSL2 Only (established pattern)

Mythril's `ethereum` dependency has no Windows binary wheel → coincurve build fails. WSL2 is the only viable path on this machine.

**Setup (WSL2 Ubuntu):**
```bash
wsl -d Ubuntu -- python3 -m venv ~/mythril-venv
wsl -d Ubuntu -- ~/mythril-venv/bin/pip install --upgrade pip setuptools wheel
wsl -d Ubuntu -- ~/mythril-venv/bin/pip install mythril
wsl -d Ubuntu -- ~/mythril-venv/bin/pip install 'setuptools<81'  # pkg_resources fix
```

**solc in WSL:** `solc-bin.ethereum.org` DNS fails from this WSL. Download from GitHub:
```bash
wsl -d Ubuntu -- curl -sL -o /tmp/solc https://github.com/ethereum/solidity/releases/download/v0.8.26/solc-static-linux
wsl -d Ubuntu -- chmod +x /tmp/solc
```

**Run Mythril on Windows project files:**
```bash
wsl -d Ubuntu -- bash -c "cd /mnt/c/<path> && SOLC=/tmp/solc ~/mythril-venv/bin/python -m mythril analyze Contract.sol"
```

## Coverage Summary

All audit domains covered with available tools:

| Domain | Primary Tool | Backup |
|--------|-------------|--------|
| Static analysis | Slither | Semgrep (custom rules) |
| Symbolic execution | Halmos | Z3 (manual constraints) |
| Fuzzing | Echidna | Foundry built-in fuzzer |
| PoC development | Foundry | — |
| Manual review | — | Core methodology |

## Source Code Access for The Graph

```bash
# Core contracts
git clone https://github.com/graphprotocol/contracts.git
cd contracts/packages

# REO (Rewards Eligibility Oracle) — newest in scope (Aug 2026)
git clone https://github.com/graphprotocol/rewards-eligibility-oracle.git

# Audit reports (dedup check!)
ls contracts/audits/
ls issuance/audits/
ls horizon/audits/
```
