# Toolkit & Shortcuts

## Web2 Tools (installed ✅)
- ffuf, nuclei, subfinder, httpx, naabu, katana, gau, waybackurls
- dalfox, kxss, arjun, sqlmap, gobuster, medusa
- commix (command injection), dirsearch (directory brute)

## SQLi Tools (installed ✅)
- sqlmap (38465★) — automatic SQLi + database takeover
- bbqsql (832★) — fast blind SQLi exploitation
- nosqlmap (3350★) — NoSQL injection (MongoDB/CouchDB)

## Crypto/Node Exploit Tools (installed ✅)
- theo (349★) — Ethereum recon + exploit via RPC
- scrooge-mcetherface (153★) — auto-looter via symbolic execution
- quimera (96★) — LLM-driven exploit generation
- rpc-fingerprint — RPC endpoint fingerprinting

## Web3 Tools (updated 2026-09-18)
- **Native Python 3.14:** slither, halmos, echidna, medusa
- **Native Foundry:** forge, cast
- **WSL Ubuntu (via wrapper):** aderyn 0.1.9 (`~/go/bin/aderyn.exe`), mythril 0.24.8 (`~/go/bin/myth`)
- Solana: cargo-build-sbf, llvm-objdump, llvm-readobj (WSL)
- **WSL Note:** aderyn/mythril route through WSL. ~10-20% slower than native. Use `wsl -d Ubuntu --` prefix if wrapper fails.

## Manual Testing
- curl with full payload lists
- Python scripts from proven-exploits.md
- GraphQL queries from graphql-attacks.md
- 403 bypass techniques from 403-bypass.md

## Hermes Platform Triggers

These are Hermes-specific interaction patterns (NOT part of the bundle):

| Trigger | Action |
|---------|--------|
| `kirim 1` / `send 1` | User confirms action (approval gate) |
| `ACC` / `approve` | Same as above |
| `lanjut` / `continue` | Resume after pause |
| `stop` / `berhenti` | Abort current operation |

**Note:** If running outside Hermes, ignore these triggers — the skill works standalone.

## Shortcut Reference

```
/audit DOMAIN        → Full web2 audit
/audit CONTRACT      → Full web3 audit
/audit DEFI          → Combined web2+web3
/SSRF                → SSRF playbook
/IDOR                → IDOR playbook
/RACE                → Race condition playbook
/GRAPHQL             → GraphQL attack playbook
/BIZLOGIC            → Business logic playbook
/XSS                 → XSS playbook
/AUTH                → Auth bypass playbook
/UPLOAD              → File upload playbook
/CORS                → CORS playbook
/CACHE               → Web cache deception playbook
/403BYPASS           → 403 bypass playbook
/FLASHLOAN           → Flashloan attack playbook
/REENTRANCY          → Reentrancy playbook
/ACCESSCTL           → Access control playbook
/BRIDGE              → Bridge exploit playbook
/TRADING             → DEX/AMM exploit playbook
/DEPWITH             → Deposit/withdraw exploit playbook
/GOV                 → Governance exploit playbook
/MATHERR             → Math/logic error playbook
/CHAIN               → Vulnerability chaining
/BAC                 → Broken access control playbook
/MASSASSIGN          → Mass assignment playbook
/OAUTH               → OAuth misconfiguration playbook
/PWDRESET            → Password reset poisoning playbook
```

## Wordlists & Payloads
```
Location: D:/data hermes/wordlists/

Recon (Phase 0B):
  subdomains: 0B-recon/subdomains/subdomains-top1million-20000.txt
  directories: 0B-recon/directories/raft-medium-directories.txt
  files: 0B-recon/files/raft-medium-files.txt
  params: 0B-recon/params/params.txt

Testing (Phase 0C) — load per vuln class via exploit-cookbook/references/:
  SQLi, XSS, SSRF, NoSQLi, CMDi, Path Traversal, XXE,
  JWT, GraphQL, WAF Bypass, Sensitive Files, Web3, Passwords
```
