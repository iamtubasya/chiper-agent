## ⛔ RULE 17: Solidity Tool Windows Quirks

**Session findings (2026-09-22):**

| Tool | Issue | Fix |
|------|-------|-----|
| mythril wrapper | ~/go/bin/myth calls WSL recursively, 30s+ timeout | `wsl -d Ubuntu -- myth analyze <file>` directly |
| echidna | crytic-compile needs Windows-style paths | `echidna "C:/path/to/file.sol" --contract X` |
| echidna | test functions need `echidna_*` prefix | NOT `test_*` (that's Foundry style) |
| echidna | crytic-compile skips test/ directory | Use forge test OR isolated project with src/ |
| medusa | `medusa version` fails | Use `medusa --help` |
| execute_code | shutil.copy2 not persistent | Always use terminal cp/mv |

**Windows path rule:** When running echidna/medusa from git-bash, ALWAYS use `C:/` paths, NEVER `/tmp/` or MSYS paths.

