---
name: attack-flows-db-web3
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  Two more end-to-end flows: (1) attacking the DATABASE layer through every reachable
  surface, (2) web3 smart-contract flow from bytecode to proven impact. Use alongside
  attack-flows; every step names the skill and depth target.
metadata:
  hermes:
    tags: [security, attack-flow, database, web3, smart-contract, decompiler, chain]
---

# Attack Flows — Database & Web3

Dua alur tambahan. Sama seperti `attack-flows`: tiap langkah sebut **skill** +
**depth target**. Bukan probe list — jalur yang bisa dijalankan berurutan.

---

## ALUR 4 — Menyerang lapisan DATABASE

**Tesis:** database jarang bisa dijangkau langsung. Yang bisa dijangkau adalah
**permukaan yang mengarah ke sana** — aplikasi, API, debug endpoint, datastore yang
ter-expose, dan file yang memuat kredensial. Alur ini menyerang semuanya berurutan.

### Langkah

**1. Petakan jalur menuju database (0B)**
```bash
# a. API & endpoint yang menerima parameter query
katana -u https://target.com -silent | grep -iE "api|/v[0-9]|search|filter|query|graphql"
# b. debug/actuator yang bocorkan kredensial DB
curl -s https://T/actuator/env | grep -iE "datasource|password|jdbc|mongo|redis"
# c. port datastore yang ter-expose
naabu -host target.com -p 27017,9200,6379,5984,5432,3306,1433
# d. file yang memuat kredensial
curl -s https://T/.env | grep -iE "db_|database|mongo|redis|jdbc|connection"
```
Skill: `api-host-surface-mapping` · `hunt-shadow-api` · `hunt-springboot` ·
`hunt-source-leak` · `hunt-cloud-misconfig`
Depth: **L0 → L1**

**2. Pilih vektor masuk berdasarkan apa yang ditemukan**

| temuan di recon | vektor | skill |
|---|---|---|
| parameter search/filter/login | SQLi / NoSQLi | `hunt-sqli` (457 baris) · `hunt-nosqli` (190) |
| endpoint ber-id | IDOR → baca baris DB | `hunt-idor` · `hunt-data-exposure` |
| GraphQL aktif | BOLA-by-resolver → dump | `hunt-graphql` (610) |
| gRPC + reflection | enumerasi method → query | `hunt-grpc` (288) |
| actuator/heapdump | kredensial DB → login langsung | `hunt-springboot` (256) |
| port 27017/9200/6379 terbuka | datastore tanpa auth | `hunt-data-exposure` |
| `.env`/`.git`/source map | kredensial → koneksi langsung | `hunt-source-leak` (316) |
| LDAP auth | LDAP injection → bypass | `hunt-ldap` (332) |

Depth: **L2** (mekanisme terpilih)

**3. Eksekusi vektor — anon control dulu**

```bash
# SQLi: error-based → boolean → time → UNION
# skill hunt-sqli: payload tree + WAF bypass + gate statistik (5×0s vs 5×10s)

# NoSQLi: operator injection
curl -X POST https://T/api/login -d '{"user":{"$ne":null},"pass":{"$ne":null}}'

# IDOR: pakai harness supaya terukur
python identity_harness.py diff --label-a a --label-b b \
  --urls https://T/api/orders https://T/api/users/1
```

Depth: **L2 → L3** (primitif: baca/tulis baris DB)

**4. Eskalasi dari baca ke tulis, lalu ke RCE**

```
a. SQLi baca  → SQLi tulis (INSERT/UPDATE) → INTO OUTFILE → webshell → RCE
   skill: hunt-sqli → hunt-file-upload → hunt-rce
b. NoSQLi baca → $where → eksekusi server-side → RCE
   skill: hunt-nosqli → hunt-rce
c. kredensial DB (dari actuator/.env) → koneksi langsung → baca/tulis
   skill: hunt-springboot → hunt-data-exposure
d. datastore expose (Redis) → tulis cron/key → RCE
   skill: hunt-data-exposure → hunt-rce
e. heapdump → session/token → ATO
   skill: hunt-springboot → hunt-ato
```
Depth: **L3 → L5**

**5. Buktikan & laporkan**
- Rantai: permukaan → mekanisme → primitif → eskalasi → impact
- Bukti: request/response + count + **min 10 record** ter-redaksi + langkah reproduksi
- Kalau sampai RCE: `whoami`/OOB DNS dengan marker unik
Depth: **L5**

---

## ALUR 5 — Web3: bytecode → decompile → analisa → impact

**Tesis:** kontrak on-chain yang belum di-verify tetap bisa dianalisa dari **bytecode**.
Yang penting: bytecode → decompilasi/pseudocode → identifikasi pola rentan → buktikan
dengan PoC Foundry.

### Langkah

**1. Recon on-chain (0B)**
```bash
# dapatkan alamat kontrak dari frontend/dApp
# skill: evm-chain-recon (172 baris) — black-box forensics dari public RPC
cast code <ADDRESS> --rpc-url <RPC>          # bytecode
cast abi <ADDRESS> --rpc-url <RPC> 2>/dev/null  # ABI kalau ter-verify
```
Skill: `evm-chain-recon` · alat: `cast`, `forge`
Depth: **L0**

**2. Cek status verifikasi & ambil sumber (0B)**
```bash
# a. ter-verify di explorer → ambil source
# skill: onchain-source-recovery (467 baris)
# b. TIDAK ter-verify → bandingkan bytecode deployed vs bytecode hasil compile
# skill: live-vs-source-bytecode-forensics (365 baris)
```
**Ini bagian penting:** `live-vs-source-bytecode-forensics` mendeteksi kalau source yang
dipublikasikan **tidak sama** dengan yang benar-benar deployed — itu sendiri temuan.
Depth: **L1**

**3. Decompilasi bytecode (0C) — TOOL LENGKAP (terverifikasi 2026-10-22)**

| tool | status host | fungsi |
|---|---|---|
| **heimdall** 0.9.2 | ✅ **TERPASANG & TERUJI** | decompile EVM → `decompiled.yul` + `abi.json` |
| **slither** | ✅ ADA | static analysis (butuh source) |
| **aderyn** | ✅ ADA | static analysis (butuh source) |
| **echidna** | ✅ ADA | fuzzing properti (butuh source) |
| **medusa** | ✅ ADA | fuzzing paralel (butuh source) |
| **forge** | ✅ ADA | test + PoC |
| **cast** | ✅ ADA | baca chain, bytecode, call |
| **solc / solc-select** | ✅ ADA | compiler + pemilih versi |
| **contract_source.py** | ✅ **BARU** | ambil source dari Etherscan v2 / Sourcify / Blockscout / IPFS metadata |

**Alur lengkap (yang tadinya HILANG — ini kenapa dulu gak gacor):**

```bash
# LANGKAH 1: ambil bytecode
cast code <ADDRESS> --rpc-url <RPC>

# LANGKAH 2: coba ambil SOURCE (4 sumber, berurutan)
python contract_source.py <ADDRESS> --rpc <RPC> --out contract-src
#   a. Etherscan API v2   (butuh ETHERSCAN_API_KEY, gratis)
#   b. Sourcify           (tanpa API key)
#   c. Blockscout         (tanpa API key) ← TERUJI: WETH9 berhasil, 755 baris
#   d. metadata IPFS      (CBOR di bytecode -> CID -> metadata JSON)

# LANGKAH 3: kalau TAK ADA source -> decompile
heimdall decompile <ADDRESS> --rpc-url <RPC> -d --include-yul
#   output: abi.json (fungsi+signature) + decompiled.yul (logika, 314 baris utk WETH9)

# LANGKAH 4: analisa
slither .          # kalau ada source
aderyn .           # kalau ada source
medusa fuzz        # kalau ada source
# atau baca decompiled.yul utk pola: delegatecall, selfdestruct, tx.origin, timestamp
```

**Teruji nyata (2026-10-22):**
- `contract_source.py` + Blockscout → WETH9 source **755 baris** ✅
- `heimdall decompile --include-yul` → `decompiled.yul` **25KB / 314 baris** + `abi.json` **4KB** ✅

**Kalau tak ada source sama sekali, yang bisa dilakukan sekarang:**
```bash
# ABI + selector
cast abi <ADDRESS>
# string constants dalam bytecode
strings <(cast code <ADDRESS>) | grep -iE "error|owner|admin|pause|upgrade"
# heimdall: disassemble + cfg + dump storage
heimdall disassemble <ADDRESS> --rpc-url <RPC>
heimdall dump <ADDRESS> --rpc-url <RPC>
```

**4. Analisa source (kalau didapat) — 12 kelas bug**
```bash
slither .                        # static analysis
aderyn .                         # static analysis (Cyfrin)
medusa fuzz                      # property-based fuzzing
forge test                       # unit + PoC
```
Skill: `smart-contract-audit` (521 baris) · `web3-audit` (1.076 baris, **12 kelas bug**:
accounting desync, reentrancy, oracle manipulation, access control, upgrade proxy,
signature replay, flash-loan, dll)
Depth: **L2 → L3**

**5. Eskalasi ke impact**
```
a. Reentrancy → drain kontrak          web3-audit → defi-exploit-forensics
b. Oracle manipulation → harga palsu   web3-audit → defi-exploit-forensics
c. Access control → kuasai kontrak     smart-contract-audit → hunt-auth-bypass
d. Upgrade proxy → ganti logika        smart-contract-audit → hunt-rce
e. Accounting desync → saldo palsu     web3-audit → hunt-business-logic
f. Signature replay → aksi ganda       web3-audit → hunt-ato
```
Skill: `defi-exploit-forensics` (181 baris — ubah exploit tx nyata jadi pola deteksi) ·
`onchain-finding-verification` (604 baris — verifikasi temuan sebelum lapor)
Depth: **L3 → L5**

**6. Buktikan dengan PoC Foundry**
```bash
forge init poc && cd poc
# tulis test yang mendemonstrasikan kerugian nyata (bukan sekadar "bisa dipanggil")
forge test -vvv
```
Skill: `onchain-finding-verification` — verifikasi temuan on-chain sebelum lapor
Depth: **L5**

---

## Peta skill untuk 2 alur baru

| alur | skill utama | skill eskalasi |
|---|---|---|
| **4. Database** | `hunt-sqli` · `hunt-nosqli` · `hunt-idor` · `hunt-graphql` · `hunt-grpc` · `hunt-springboot` · `hunt-source-leak` · `hunt-ldap` · `hunt-data-exposure` | `hunt-file-upload` · `hunt-rce` · `hunt-ato` |
| **5. Web3** | `evm-chain-recon` · `onchain-source-recovery` · `live-vs-source-bytecode-forensics` · `smart-contract-audit` · `web3-audit` | `defi-exploit-forensics` · `onchain-finding-verification` · `hunt-auth-bypass` · `hunt-rce` · `hunt-business-logic` · `hunt-ato` |

## Worked example — Alur 4 on a hardened registrar (do.de, 2026-10-26, all negative)

Full guest-surface DB attack on a domain-registrar portal. Every vector ran; what each
taught (the negatives are the deliverable):

- **Form-encoded-only APIs kill NoSQLi in one request.** POST JSON `{"$ne":null}` to a
  form endpoint → CSRF rejection; the app never parses a JSON body. Check the content-type
  the real form sends before building operator payloads.
- **Sequential IDs behind a capability key are not IDOR.** Cart/item IDs incremented
  visibly (280730+, 1296811+) but every endpoint required a 22-char cart key; no ID-only
  route existed and cross-cart item access returned NOT_EXISTS. The IDOR test on this
  shape is: enumerate endpoints, look for any that take a bare ID with no capability token.
- **A quote-exception on login is a parser, not SQLi** — full discrimination recipe in
  `hunt-sqli` ("quote-triggered exception is NOT SQLi until discriminated"). Ran boolean
  pair + time probe + sibling-input comparison; all three negative.
- **Second-order lead worth recording:** cart params stored arbitrary values verbatim
  (`test'--payload` round-tripped through get). If an authenticated checkout interpolates
  cart params into SQL, that is the injection point — logged as a lead requiring an account,
  not claimed as a finding.
- **Datastore ports + file leaks:** 3306/5432/6379/27017/9200/1433/5984/11211 all filtered;
  wp-config/.git/.env/debug.log all masked by the SPA catch-all (see bb-methodology
  SPA-Catch-All Rule — hash the shell baseline first or every probe "succeeds").
- rce-verify ledger: 0/12 confirmed (time + OOB channels) — the honest end state for a
  target with no injection surface.

## Rekomendasi tindakan

**Kedua alur siap pakai sekarang (terverifikasi 2026-10-22):**

- **Alur 4 (database)** — semua skill & tool sudah ada, bisa dijalankan langsung.
- **Alur 5 (web3)** — **lengkap**: `contract_source.py` (4 sumber source) +
  `heimdall` (decompile bytecode → yul) + `slither`/`aderyn`/`echidna`/`medusa`/`forge`
  (analisa & PoC). Teruji: WETH9 source 755 baris via Blockscout, decompile 314 baris yul.

**Satu-satunya yang butuh tindakan darimu:** `ETHERSCAN_API_KEY` (gratis di
etherscan.io) — supaya sumber #1 (paling lengkap) aktif. Tanpa itu, Sourcify +
Blockscout + IPFS metadata + heimdall sudah cukup.

---

## Alur 5 — perluasan kelas (2026-10-27)

Alur 5 aslinya berhenti di 12 kelas bug generik. Delapan kelas modern yang **tidak** tercakup
di sana sekarang punya skill sendiri, masing-masing dengan gate "minimum 5 probes" + 2026 sweep:

| Kelas | Skill | Probe pertama |
|---|---|---|
| Smart account / modular authz | `hunt-aa-modular` | `installModule` dengan address attacker |
| Signed approval replay | `hunt-permit2-signature` | domain separator field census |
| AMM hooks / singleton | `hunt-amm-hooks` | initialize pool dengan hook attacker |
| Restaking / LRT | `hunt-restaking-lrt` | slash request dengan attestation fabric |
| Intent / solver / attestor | `hunt-intent-settlement` | `solve()` dengan solver arbitrary |
| Oracle / sequencer uptime | `hunt-oracle-l2` | uptime down + sebelum/sesudah grace |
| Vault inflation | `hunt-vault-inflation` | single-party kill test → mint 1 wei → donate |
| Upgradeability / diamond | `hunt-diamond-proxy` | `diamondCut` dari non-owner |

**Aturan pemakaian:** kelas yang tidak ada di target → catat `N/A: <alasan>` di LEDGER
(lihat `howtohunt-checklist` kelas 11-19). Semua temuan wajib lewat
`onchain-finding-verification` (fork PoC + attacker P&L + negative control) sebelum ditulis.
