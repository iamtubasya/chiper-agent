# Mythril Installation Failures — Python 3.14 & WSL Issues

Verified: August 28, 2026

## Problem 1: Windows — blake2b-py / pyethash build failure

Mythril depends on `ethereum` → `coincurve` → `blake2b-py` and `pyethash`, which are native C extensions requiring MSVC build tools on Windows. Even in a Python 3.11 venv (Hermes), these fail:
```
ERROR: Failed building wheel for blake2b-py
ERROR: Failed building wheel for pyethash
```

**Root cause:** No MSVC Build Tools installed on this Windows machine.
**Workaround:** Mythril MUST run in WSL2.

## Problem 2: WSL2 with Python 3.14 — coincurve build failure

Ubuntu 26.04 ships Python 3.14 which is too new for `coincurve`:
- `cffi` fails to build (needs `libffi-dev`, `python3-dev` which require sudo)
- `coincurve` fails to build (needs `cffi` + C compiler toolchain)
- `get-pip.py --break-system-packages` works, but `pip install mythril` fails on native deps

**Root cause:** Python 3.14 is cutting-edge; most crypto C extensions don't have wheels for it yet.
**Workaround:** WSL2 must have Python 3.11 or 3.12. If only 3.14 is available:
```bash
# Option A: Install older Python via deadsnakes PPA (needs sudo)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.12 python3.12-venv python3.12-dev

# Option B: Use conda/mamba (no sudo needed)
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p $HOME/miniforge3
$HOME/miniforge3/bin/conda create -n mythril python=3.12 -y
$HOME/miniforge3/envs/mythril/bin/pip install mythril
```

## Problem 3: WSL2 without python3-venv package

If `python3 -m venv` fails with "ensurepip is not available" and `apt install python3-venv` fails without sudo:

```bash
# Use get-pip.py + --break-system-packages instead of venv
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
python3 /tmp/get-pip.py --break-system-packages
pip3 install --break-system-packages mythril
```

This installs system-wide but works when venv is unavailable.

## Working Setup (Verified)

```bash
# WSL2 Ubuntu 24.04 (Python 3.12) — confirmed working
wsl -d Ubuntu-24.04 -- python3 -m venv ~/mythril-venv
wsl -d Ubuntu-24.04 -- ~/mythril-venv/bin/pip install --upgrade pip setuptools wheel
wsl -d Ubuntu-24.04 -- ~/mythril-venv/bin/pip install mythril
wsl -d Ubuntu-24.04 -- ~/mythril-venv/bin/pip install 'setuptools<81'  # pkg_resources fix

# solc — solc-bin.ethereum.org DNS fails from WSL; use GitHub:
wsl -d Ubuntu -- curl -sL -o /tmp/solc https://github.com/ethereum/solidity/releases/download/v0.8.26/solc-static-linux
wsl -d Ubuntu -- chmod +x /tmp/solc

# Run:
wsl -d Ubuntu -- bash -c "cd /mnt/c/<path> && SOLC=/tmp/solc ~/mythril-venv/bin/python -m mythril analyze Contract.sol"
```

## Decision Tree
```
Windows? → Mythril CAN run natively (patched pyethash + MSVC Build Tools)
  ├─ MSVC Build Tools installed? → Native install (references/mythril-windows-native-install.md) ✅
  └─ No MSVC → WSL2 available?
       ├─ Python ≤3.12 → venv + pip install mythril ✅
       ├─ Python 3.14 → need older Python or conda ⚠️
       └─ No WSL2 → install MSVC Build Tools first ❌→✅
```
