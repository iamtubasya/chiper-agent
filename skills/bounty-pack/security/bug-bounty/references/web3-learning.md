# Web3 Security Learning Roadmap

## Active Curriculum (12 Minggu, 4 Fase)

**Start date:** 2 September 2026 | **Schedule:** Harian 21:00-00:00 WIB | **Total:** 136 jam

**Reference files:**
- `C:/Users/WINDOWS10/Downloads/Rencana_Belajar_Bug_Bounty_Web3.xlsx` — 2 sheets: "Rencana Belajar" (12 minggu, 8 kolom) + "Daftar Sumber" (17 sumber)
- `C:/Users/WINDOWS10/Downloads/Panduan_Teknis_Bug_Bounty_Web3.pdf` — 7 halaman: Ethernaut walkthrough + 6 kerentanan breakdown (reentrancy, oracle, access control, integer overflow, flash loan, front-running/MEV)

**Cron:** `belajar-web3-bounty` (job `dccb52a8275f`) — daily 14:00 UTC (21:00 WIB), delivers topic reminder to origin chat.

### Fase 1: Fondasi (Minggu 1-3, 30 jam)
| Minggu | Topik | Sumber |
|--------|-------|--------|
| 1 | Dasar Blockchain & Solidity | solidtylang.org, CryptoZombies |
| 2 | Solidity Lanjutan & Foundry | Foundry Book |
| 3 | Standar Token & Pola DeFi | OpenZeppelin, EIPs |

### Fase 2: Kerentanan & CTF (Minggu 4-7, 46 jam)
| Minggu | Topik | Sumber |
|--------|-------|--------|
| 4 | Ethernaut Level 0-10 | ethernaut.openzeppelin.com |
| 5 | Capture the Ether | capturetheether.com |
| 6 | Damn Vulnerable DeFi pt.1 | damnvulnerabledefi.xyz |
| 7 | Damn Vulnerable DeFi pt.2 | damnvulnerabledefi.xyz |

### Fase 3: Tools & Audit (Minggu 8-9, 22 jam)
| Minggu | Topik | Sumber |
|--------|-------|--------|
| 8 | Static & Bytecode Analysis (Slither, Mythril) | crytic/slither, Consensys/mythril |
| 9 | Fuzzing & Secureum (Echidna, invariant tests) | crytic/echidna, secureum.xyz |

### Fase 4: Bug Bounty Nyata (Minggu 10-12, 38 jam)
| Minggu | Topik | Sumber |
|--------|-------|--------|
| 10 | Platform & Format Laporan | Immunefi, Code4rena |
| 11 | Audit Kode Program Nyata (1-2 scope kecil) | immunefi.com/bug-bounty |
| 12 | Audit Contest & Submit | Code4rena, Sherlock |

---

## Kerentanan Prioritas (dari Panduan Teknis)

| # | Kerentanan | Inti | Mitigasi |
|---|-----------|------|----------|
| 1 | Reentrancy | Transfer ETH sebelum update state | Checks-Effects-Interactions + nonReentrant |
| 2 | Oracle Manipulation | Harga dari reserve pool instan | Chainlink / TWAP |
| 3 | Access Control Lemah | Fungsi sensitif tanpa modifier | onlyOwner + initializer guard |
| 4 | Integer Overflow/Underflow | Arithmetic tanpa batas (pre-0.8) | Solidity 0.8+ / SafeMath |
| 5 | Flash Loan Attack | Snapshot voting power instan | getPastVotes (blok sebelumnya) |
| 6 | Front-Running/MEV | Secret terlihat di mempool | Commit-reveal / Flashbots |

---

## Metodologi Ethernaut (Panduan Teknis Bagian 1)

Untuk setiap level:
1. Baca kontrak baris per baris — catat semua fungsi public/external
2. Cari "celah kepercayaan" — asumsi apa yang kontrak buat?
3. Map ke kategori bug (reentrancy, access control, dsb)
4. Tulis exploit (console browser atau Foundry script)
5. Baca write-up orang lain — bandingkan approach

**Tip:** Kalau stuck >30-45 menit, baca hint resmi dulu sebelum lihat write-up penuh.

---

## Format Laporan Bug Bounty (Panduan Teknis Bagian 3)

Struktur standar (Immunefi/Code4rena/Sherlock):
1. **Judul & Severity** — sebutkan dampak
2. **Deskripsi** — akar masalah, fungsi terdampak, kondisi exploit
3. **Proof of Concept** — kode test Foundry/Hardhat yang berjalan
4. **Dampak** — kuantifikasi dana/ pengguna terdampak
5. **Saran Perbaikan** — mitigasi + contoh kode

**Before submit:** cek known issues, ikuti scope ketat.

---

## Legacy Roadmap (generic reference)

| Phase | Hours/Week | Total |
|-------|-----------|-------|
| Foundation | 10 | 20 |
| Security Fundamentals | 10 | 20 |
| CTFs | 15 | 60 |
| Real-World Study | 10 | 40 |
| Hunting | 20+ | Ongoing |

**Total to job-ready:** ~140 hours (~3.5 months at 10h/week)

### Generic Resources
- **Docs:** Solidity, EVM Codes, Ethereum Yellow Paper
- **Community:** Ethereum Stack Exchange, Secureum Discord, Immunefi Discord
- **Tools:** Foundry, Hardhat, Slither
- **CTFs:** Ethernaut, Capture the Ether, DVDeFi, Paradigm CTF, QuillCTF, Sherlock CTF
