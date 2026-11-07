# Detailed Install Transcript — 19-Aug-2026 (this host)

## Foundry direct-download fix (foundryup fails in MSYS)

`curl -sL https://foundry.paradigm.xyz | bash` → `curl: (23) Failed writing body` in git-bash. Root cause: MSYS pipe/socket handling with the installer. Workaround: never use the installer on this host; download the GitHub release zip:

```bash
curl -sL https://api.github.com/repos/foundry-rs/foundry/releases/latest | grep -oE '"tag_name": "[^"]*"' | head -1
# v1.7.1 as of Aug 2026
curl -sL -o ~/foundry-bin/foundry.zip https://github.com/foundry-rs/foundry/releases/download/v1.7.1/foundry_v1.7.1_win32_amd64.zip
cd ~/foundry-bin && unzip -o foundry.zip
cp ~/foundry-bin/*.exe ~/.foundry/bin/   # forge.exe, cast.exe, anvil.exe, chisel.exe
echo 'export PATH="$HOME/.foundry/bin:$PATH"' >> ~/.bashrc
```

## Halmos pkg_resources failure → --only-binary

Observed: `python -m pip install halmos mythril` → cryptography build fails:
```
ModuleNotFoundError: No module named 'pkg_resources'
ERROR: Failed to build 'cryptography' when getting requirements to build wheel
```
Fix (Halmos 0.2.0, pulls z3-solver 4.12.6):
```bash
python -m pip install --only-binary :all: halmos
```

## Mythril pkg_resources failure in venv → setuptools<81

Observed inside WSL venv after successful `pip install mythril`:
```
File ".../eth/__init__.py", line 1, in <module>
    import pkg_resources
ModuleNotFoundError: No module named 'pkg_resources'
```
Fix:
```bash
~/mythril-venv/bin/pip install 'setuptools<81'   # 80.10.2 verified
```
`pkg_resources is deprecated` UserWarning on every run is harmless.

## solc install: solc-bin DNS fails from WSL

py-solc-x install attempt:
```
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='solc-bin.ethereum.org', ...) Failed to resolve
```
Fix: static binary from GitHub (github.com resolves fine):
```bash
curl -sL -o /tmp/solc https://github.com/ethereum/solidity/releases/download/v0.8.26/solc-static-linux
chmod +x /tmp/solc
SOLC=/tmp/solc ~/mythril-venv/bin/python -m mythril analyze Contract.sol
```

## Mythril analysis runtime

- First analysis on a non-trivial contract took > 5 minutes → always `background=true, notify_on_complete=true`.
- Access Windows files from WSL via `/home/agentuser/...`.

## Halmos property-check results (reference for interpretation)

| Contract | Result |
|---|---|
| AdvancedProps | 3 PASS, 1 TIMEOUT (check_inflationAttackUnprofitable) |
| CrossContractProps | 4 PASS, 2 FAIL (counterexamples at 0 / 2^255 — overflow boundary) |
| CrossContractV2 | 4 PASS, 2 TIMEOUT (check_crossContractSolvency, check_ltv) |

Interpretation: TIMEOUTs are solver bounds (raise `--solver-timeout-assertion`); boundary counterexamples are overflow edges worth inspecting, not necessarily production bugs.
