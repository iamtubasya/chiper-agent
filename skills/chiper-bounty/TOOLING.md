# TOOLING.md — Install Tools per Fase (0A–0F)

Semua command dibawah untuk host barunya. Daftar = 13 tools WAJIB + pendukung.
Go tools butuh Go >= 1.21 terpasang dulu.

## Pra-syarat (sekali)
```bash
# Go
# Windows: https://go.dev/dl/  (go1.22+.windows-amd64.msi)
# Ubuntu/WSL: 
sudo apt update && sudo apt install -y golang-go python3 python3-pip jq
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc && source ~/.bashrc
```

## 0A — Intake target (scope, policy, rules)
Tidak butuh tool berat. Pakai skill: `bb-methodology`, `bb-audit-launcher`, `recon-scope-triage`.
- Baca policy/scope target (PDF → `pymupdf`): `pip install pymupdf`

## 0B — Recon / attack-surface discovery
```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/lc/gau/v2/cmd/gau@latest
go install -v github.com/tomnomnom/assetfinder@latest
go install -v github.com/tomnomnom/anew@latest
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
# wordlist & config
mkdir -p ~/wordlists ~/.config/subfinder
cp data/wordlists/*/ ~/wordlists/ 2>/dev/null || true
```
- `amass`: `go install -v github.com/owasp-amass/amass/v4/...@master`

## 0C — Scanning & fuzzing (13 WAJIB)
```bash
# nuclei (templates ikut)
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
nuclei -update-templates   # clone https://github.com/projectdiscovery/nuclei-templates

go install -v github.com/ffuf/ffuf/v2@latest
go install -v github.com/hahwul/dalfox/v2@latest
go install -v github.com/projectdiscovery/arjun/cmd/arjun@latest
go install -v github.com/BishopFox/jsluice/cmd/jsluice@latest      # butuh gcc (WinLibs) di Windows
go install -v github.com/tomnomnom/qsreplace@latest
go install -v github.com/detectify/page-fetch@latest

# sqlmap (pip)
pip install sqlmap
# ghauri (python) — pindah dari pip ke repo
git clone https://github.com/r0oth3x49/ghauri && cd ghauri && pip install -r requirements.txt && pip install .

# graphql-cop
go install -v github.com/dolevf/graphql-cop@latest
# interactsh (SSRF/OOB)
go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest
# mitmproxy (proxy 8080)
pip install mitmproxy
```

## 0D — Vuln-class deep-dive
Skill `hunt-*` = checklist per kelas. Cukup baca + jalankan probe-nya.

## 0E — Triage & validasi
Skill: `triage-validation`, `exploit-depth`, `lead-to-critical`, `chain-to-impact`.
```bash
pip install requests  # hanya untuk triage/decode output, BUKAN probe utama
```

## 0F — Report & delivery
Skill: `report-writing`, `bugcrowd-reporting`, `pgp-email-submission`, `humanizer`.
```bash
pip install reportlab weasyprint   # PDF
# PGP (opsional)
sudo apt install -y gnupg
```

## Data besar (TIDAK termasuk zip — clone/download manual)
- nuclei-templates: `git clone https://github.com/projectdiscovery/nuclei-templates`
- target-pool (35k domain): regenerate via skill `target-pool` + cron `early-warning`
- cve PoC corpus: `git clone https://github.com/nomi-sec/PoC-in-GitHub`
- advisory-intel: dari skill `advisory-intel`

## Web3 (opsional, bila audit kontrak)
```bash
pip install slither-analyzer
cargo install cargo-audit cargo-deny
# mythril / aderyn via WSL Ubuntu
pipx install mythril
cargo install aderyn
# echidna / medusa / foundry
cargo install --locked echidna-upgradeable
```
