---
name: local-vuln-lab
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  Local vulnerable labs (Docker) for practising RCE, IDOR/BOLA and ATO before touching
  a real target. Use when you need to verify a technique works, or when a hunt skill
  says "probe wajib" and you want a safe place to try it first.
metadata:
  hermes:
    tags: [security, lab, docker, practice, rce, idor, ato, juice-shop, dvwa]
---

# Local Vulnerability Lab

Lab lokal sengaja rentan. **Bukan untuk dilaporkan** — ini tempat mencoba teknik
sebelum dipakai di target nyata, dan tempat memverifikasi bahwa sebuah probe
benar-benar bekerja.

## Lab tersedia

| Lab | Port | Kelas utama | Catatan |
|---|---|---|---|
| **OWASP Juice Shop** | `http://localhost:3000` | IDOR/BOLA, ATO, injection, upload, SSRF, broken auth | Modern SPA + REST API; paling dekat dengan target bounty nyata |
| **DVWA** | `http://localhost:4280` | RCE (command injection), LFI, SQLi, file upload | Klasik; butuh setup awal (`/setup.php` → login `admin`/`password`, set security Low) |
| **Web3 Foundry Lab** | `D:/isplab/web3-lab` (no port — `forge test`) | Vault inflation, modular account (ERC-7579/7702), oracle/sequencer (L2) | **Tidak butuh Docker.** Foundry 1.7.1 + forge-std. 23 test = 23 probe, semua lulus |

### Web3 Foundry Lab — cara pakai

```bash
cd /d/isplab/web3-lab
forge test                                    # semua 23 test
forge test --match-contract VaultInflationCalibration -vv   # probe + log angka
forge test --match-test test_Probe1 -vvvv     # trace lengkap
```

Kontrak rentan di `src/vulnerable/`, kalibrasi di `test/`:

| Suite | Skill yang dikalibrasi | Probe |
|---|---|---|
| `VaultInflationCalibration` | `hunt-vault-inflation` | 0 single-party kill, 1 inflation, 2 rounding, 3 fee-on-transfer, 4 attacker P&L |
| `AAModularCalibration` | `hunt-aa-modular` | 1 module install, 1b delegatecall context, 2 empty-sig, 3 nonce ordering, 3b reentrant control, 4 registry admin, 5 type confusion |
| `OracleL2Calibration` | `hunt-oracle-l2` | 1 uptime, 1b grace, 2 staleness, 2b round, 2c negative price, 3 conf, 3b publishTime, 5 exploitation gate |
| `Permit2Calibration` | `hunt-permit2-signature` | 1 domain binding, 2 allowance decrement, 2b control, 3 witness binding, 4 ERC-3009 replay, 4b expiry, 5 low-s malleability |
| `AmmHooksCalibration` | `hunt-amm-hooks` | 1 hook allowlist, 2 cross-pool reentrancy, 3 fee mutation mid-swap, 5 flash-accounting delta |
| `RestakingLRTCalibration` | `hunt-restaking-lrt` | 1 unrestricted slash, 2 double slash, 3 withdrawal delay, 4 rate desync |
| `IntentSettlementCalibration` | `hunt-intent-settlement` | 1 solver allowlist, 2 attestation replay, 3 minOut, 4 overfill |
| `DiamondProxyCalibration` | `hunt-diamond-proxy` | 1 unprotected cut, 2 selector hijack, 3 storage collision, 4 initializer replay |

**Total: 8 suite, 48 test, semua lulus** (`forge test`). Setiap suite punya Control test (bentuk FIX)
di sebelah test rentan.

**Aturan lab web3:** setiap suite punya CONTROL test (bentuk FIX) di sebelah test rentan. Kalau
control juga "gagal", yang salah adalah harness, bukan kontrak — perbaiki harness dulu.

**Trap harness web3 yang sudah memakan waktu (jangan diulang):**
- `sload(slot)` di dalam test membaca storage TEST contract, bukan target → pakai
  `vm.load(address(target), bytes32(slot))`.
- `immutable` TIDAK menempati storage → slot 0 adalah state variable non-immutable pertama.
- Foundry default `block.timestamp` = 1 → `block.timestamp - N` underflow. `vm.warp()` dulu.
- Mock oracle harus punya bentuk return yang SAMA dengan feed asli (Chainlink uptime = 5-tuple).
  Mock yang lebih sederhana membuat cek grace/staleness lolos palsu.
- `vm.prank` hanya berlaku untuk satu call. Deposit sebagai X lalu borrow sebagai Y butuh
  prank terpisah atau helper `depositCollateralFor`.
- `keccak256(abi.encode(poolKey))` berbeda kalau field `hooks` berbeda — hook yang menaikkan fee
  pool "yang salah" terlihat seperti tidak berpengaruh.
- Fungsi `unlock()`-style yang memanggil `msg.sender.call(data)` menuntut caller mengekspos fungsi
  tujuan; dan delta dibukukan ke pemanggil, jadi swap + unlock harus dari kontrak yang sama.
- Untuk memanggil fungsi lewat diamond/proxy, **setiap** selector yang dipakai harus di-cut
  (setter DAN getter). Kurang satu selector → fallback mengembalikan garbage yang terlihat seperti
  "tidak ada collision".
- Pool yang di-slash butuh seed deposit dulu, kalau tidak `totalPooled -= x` underflow.
- `mapping(address => bool) allowlist` yang ADA tapi tidak pernah dibaca adalah pola bug yang lebih
  umum daripada allowlist yang tidak ada — grep deklarasinya, lalu cek pemakaiannya di write path.

## Menjalankan

```bash
# engine harus hidup
docker ps    # kalau gagal: nyalakan Docker Desktop dulu

# kalau container mati:
docker start juice-shop dvwa
```

## Alur latihan per kelas

### RCE
1. DVWA → Command Injection → `;id`, `|id`, `` `id` `` — lihat beda output
2. DVWA → File Upload → upload `.php` dan akses langsung
3. Juice Shop → cari endpoint yang menerima input ke `eval`/template

### IDOR / BOLA
1. Buat 2 akun di Juice Shop (A dan B)
2. `identity_harness.py capture` untuk keduanya
3. `identity_harness.py diff --label-a a --label-b b --urls http://localhost:3000/rest/products/reviews`
4. Cari `BASKET_ID` / `userId` milik A dari response, akses dengan sesi B

### ATO
1. Juice Shop → forgot-password flow; amati token di response & email (mailpit lokal)
2. Coba token reuse, cross-account, expiry
3. DVWA → CSRF → ganti password admin dari sesi lain

## Aturan

- **Jangan pernah** melaporkan temuan dari lab ini ke program mana pun.
- **Jangan** expose port lab ke internet (`0.0.0.0` hanya untuk lokal).
- Setelah selesai: `docker stop juice-shop dvwa` supaya RAM bebas (host 6GB).
- Bukti latihan disimpan terpisah dari bukti audit nyata.

## Menambah lab

```bash
docker run -d --name <nama> -p <port>:<port> <image>
# lalu tambah baris ke tabel di atas
```

Kandidat berguna: `webgoat/webgoat-8.0`, `psiinon/open-letter`, `vulhub/<?>`.

**Web3 tidak butuh Docker.** Foundry (`forge`/`anvil`/`cast`) sudah terpasang di
`~/.foundry/bin`. Untuk lab kontrak, `forge init` + kontrak rentan + test = lab lengkap dalam
hitungan menit, tanpa image dan tanpa RAM overhead.

## Bukan lab ini? Pilih yang benar

| Kebutuhan | Skill |
|---|---|
| Latihan teknik di app sengaja rentan (Juice Shop, DVWA) | **skill ini** |
| Produk **asli vendor** (billing/control panel) yang harus di-install sendiri karena aturan bounty "hanya produk yang kamu miliki" | `security/vendor-product-lab` |
| Firmware / appliance / NAS OS image di VM | `security/vm-appliance-lab` |

Bedanya: lab di sini sengaja dibuat rentan dan **tidak boleh dilaporkan**.
`vendor-product-lab` memakai software produksi yang sama dengan target bounty,
dengan lisensi dan identitas uji sendiri — di sanalah IDOR, privilege escalation
dan business-logic bug yang bisa dibayar diuji dan dibuktikan.
