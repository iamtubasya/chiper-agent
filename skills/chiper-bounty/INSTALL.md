# Bounty Pack — Portable Skill & Tooling Bundle

Paket siap-pakai untuk instance Hermes lain. Identitas & kredensial pribadi SUDAH dihapus
(diganti placeholder RESEARCHER_NAME / RESEARCHER_EMAIL / GITHUB_USER / BC_ALIAS).

## Struktur
```
bounty-pack/
├── skills/                # ~136 skill bounty/offensive/OSINT/Web3
│   ├── security/          # 117 skill (engagement-per-target + attacker primitives)
│   ├── tob/               # 28 skill Trail-of-Bits (fuzzing, semgrep, codeql, scanner)
│   ├── hunt-*/            # 67 hunting checklist per vuln-class
│   └── ...                # attack-flows, audit-*, exploit-*, web2/web3, osint, report
├── data/                  # wordlists, poc-techniques, poc-plans, bug-bounty/reference
├── INSTALL.md             # file ini
└── TOOLING.md             # panduan install tools per fase (0A-0F)
