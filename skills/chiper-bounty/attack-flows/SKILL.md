---
name: attack-flows
version: 1.0.0
author: RESEARCHER_NAME
description: >-
  End-to-end attack flows built from the existing hunt-* skills: dangling-domain
  takeover, zombie/undocumented API to production data, and adjacent variants. Use
  when you want a ready path from recon to proven impact instead of probing class by
  class.
metadata:
  hermes:
    tags: [security, attack-flow, takeover, zombie-api, chain, methodology, bug-bounty]
---

# Attack Flows — alur siap pakai (dari skill yang sudah ada)

Tiga alur lengkap. Tiap langkah menyebut **skill** dan **depth target**. Bukan daftar
probe — ini jalur yang bisa dijalankan berurutan.

---

## ALUR 1 — Dangling domain → takeover → produksi

**Tesis:** subdomain yang CNAME-nya menunjuk ke servis yang sudah mati = siapa pun bisa
mengklaim servis itu, lalu melayani konten di domain korban. Cookie `.target.com`
yang sudah dipegang browser korban jadi bisa dicuri.

### Langkah

**1. Inventaris DNS (0B)**
```bash
# subfinder + amass -> subs.txt, lalu resolve & ambil CNAME
subfinder -d target.com -silent | httpx -silent > subs.txt
dig +short CNAME <sub>   # cari yang menunjuk ke servis pihak ketiga
```
Skill: `hunt-subdomain` (380 baris) · alat: `subfinder`, `amass`, `httpx`, `dnsfix.py`
Depth: **L0** (inventaris)

**2. Deteksi dangling (0B)**
```bash
# dnsReaper: 50+ signature provider (S3, Azure, GitHub Pages, Shopify, Fastly…)
dnsreaper domain --domain target.com
# manual: NXDOMAIN pada CNAME target, atau halaman "no such bucket/404 Not Found"
```
Skill: `dnsReaper` (95 baris, 50+ signature) · `hunt-subdomain`
Depth: **L1** (sinyal dangling)

**3. Konfirmasi bisa diklaim (0C) — JANGAN klaim kalau belum yakin**
```bash
# bucket S3: cek apakah nama bucket tersedia
aws s3api head-bucket --bucket <nama> 2>&1 | grep -q "404" && echo "AVAILABLE"
# GitHub Pages: repo <org>.github.io belum ada
# Azure: <nama>.azurewebsites.net NXDOMAIN
```
**Aturan aman:** verifikasi ketersediaan dulu. Kalau sudah ada pemilik, itu **bukan**
takeover — catat sebagai third-party dan keluar dari scope.
Depth: **L2** (mekanisme: servis mati, nama bisa diklaim)

**4. Klaim + sajikan bukti minimal (0C)**
```bash
# klaim servis (S3 bucket / repo Pages / App Service), lalu sajikan halaman
# yang MEMBUKTIKAN kendali — BUKAN halaman phishing
```
Sajikan halaman berisi: marker unik, timestamp, dan kalimat *"proof-of-control, security
research, contact: <email>"*. **Jangan** sajikan halaman login palsu atau konten yang
meniru korban.
Depth: **L3** (primitif: kendali konten di domain korban)

**5. Eskalasi — dari kendali konten ke dampak nyata (0C)**
```
a. Cookie scoping: cookie dgn Domain=.target.com sekarang terkirim ke subdomain kamu
   -> kalau ada cookie non-HttpOnly, bisa dibaca JS kamu
b. OAuth redirect_uri: kalau target mendaftarkan https://<sub>.target.com/callback
   -> curi authorization code -> ATO
c. CSP / HSTS: subdomain kamu bisa melemahkan policy untuk apex
d. Email: subdomain takeover -> kirim mail dari domain korban -> phishing kredensial
```
Skill: `hunt-oauth` (537 baris) · `hunt-ato` (271 baris) · `hunt-xss` (530 baris)
Depth: **L4** (eskalasi)

**6. Buktikan dampak (0E/0F)**
- Minimal: halaman proof-of-control + daftar cookie yang terkirim ke subdomain itu
- Lebih kuat: OAuth code tertangkap di log akses kamu (dengan akun tes sendiri)
- Reproduksi 10 menit dari sesi bersih
Depth: **L5** (impact terbukti)

**7. Lepas klaim** — setelah bukti lengkap, hapus konten dan lepas klaim servis.
Tulis di laporan kapan klaim dilepas.

---

## ALUR 2 — Zombie / undocumented API → database atau produksi

**Tesis:** endpoint yang masih hidup tapi sudah tidak dipakai (versi lama, fitur
dimatikan, sisa integrasi) jarang dipelihara — authz-nya biasanya bolong.

### Langkah

**1. Petakan host & surface (0B)**
```bash
# apex sering cuma marketing; API di host lain
# skill: api-host-surface-mapping (196 baris)
# kumpulkan: subs.txt + JS bundle + source map + dork
katana -u https://target.com -silent | grep -iE "api|/v[0-9]|internal|graphql" > api_candidates.txt
```
Skill: `api-host-surface-mapping` · `hunt-spa-api` (256 baris) · `hunt-source-leak` (316 baris)
Depth: **L0**

**2. Temukan endpoint zombie (0B/0C)**
```bash
# a. source map: .js.map berisi path asli
# b. versi lama: /api/v1/... saat /api/v2/... aktif
# c. fitur mati: endpoint yang direferensikan JS lama tapi tak ada di UI
# d. dork: site:target.com inurl:api OR inurl:v1 OR inurl:internal
ffuf -u https://target.com/api/FUZZ -w api-wordlist.txt -mc 200,401,403,405
```
Skill: `hunt-shadow-api` (210 baris, OWASP API9) · `hunt-spa-api` · `hunt-source-leak`
Depth: **L1** (endpoint hidup tapi tak terdokumentasi)

**3. Uji authz — anon control DULU (0C)**
```bash
# tanpa cookie sama sekali
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" https://T/api/v1/users
# lalu bandingkan dengan versi aktif & dengan sesi
```
Skill: `hunt-auth-bypass` (618 baris) · `hunt-data-exposure` (165 baris)
Depth: **L1 → L2** (differential + mekanisme)

**4. Kalau endpoint mengarah ke data — ikuti `hunt-data-exposure`**
```
- tentukan mekanisme (8 kemungkinan: unauth collection, IDOR, GraphQL BOLA,
  datastore exposed, SQLi, file leak, mass assignment, shadow API)
- ambil count + MINIMAL 10 record (bukan dump)
- redaksi PII
```
Depth: **L2 → L3**

**5. Eskalasi ke produksi (0C)**
```
a. Endpoint debug/actuator hidup  -> heapdump/env -> kredensial DB & cloud
   skill: hunt-springboot (256 baris)
b. Endpoint yang terima URL/webhook -> SSRF ke metadata 169.254.169.254
   skill: hunt-ssrf
c. Endpoint yang menjalankan template/eval -> SSTI/RCE
   skill: hunt-ssti / hunt-rce
d. Endpoint dengan field tersembunyi -> mass assignment (role, isAdmin)
   skill: hunt-api-misconfig
e. Endpoint lama tanpa patch -> N-day (patch-diff)
   skill: hunt-rce + patch-diff-exploit
```
Depth: **L3 → L5**

**6. Buktikan & laporkan**
- Rantai lengkap: zombie endpoint → authz bolong → data/produksi
- Bukti: request/response + count + 10 record ter-redaksi + langkah reproduksi
- Depth: **L5**

---

## ALUR 3 — Varian berulang (polimerisasi temuan)

**Tesis:** satu celah jarang dibayar mahal. **Pola** yang sama di banyak tempat =
laporan klasifikasi, severity naik, sulit ditolak.

### Langkah

**1. Dari satu temuan, sebut polanya**
```
"endpoint /api/v1/orders tidak cek kepemilikan"
-> pola: "endpoint /api/v1/* tidak cek kepemilikan"
```

**2. Uji SEMUA yang sejenis (aturan adjacent-gate)**
```bash
# semua resource di versi sama
for r in orders users invoices payments tickets; do
  curl -s -o /dev/null -w "$r %{http_code}\n" "https://T/api/v1/$r/1"
done
# semua versi
for v in v1 v2 v3; do ... done
# semua method
for m in GET POST PUT DELETE PATCH; do ... done
```

**3. Eskalasi per titik (pakai `exploit-chain-graph`)**
Setiap titik yang lolos → buka chain-graph → eskalasi ke kelas berikutnya.

**4. Laporkan sebagai klasifikasi**
```
Judul  : Broken object-level authorization across /api/v1/* (N endpoints)
Dampak : baca/tulis data lintas akun pada N resource
Bukti  : tabel endpoint × status × jumlah record
```
Ini jauh lebih kuat daripada "1 endpoint IDOR".

---

### Alur 9 — Unauth battery → authed battery → report (the engagement spine)

The ordered LIFECYCLE that ties recon to the two vector batteries. Run it as the
default frame for any web2 target, so no surface is skipped and no negatif is
declared empty before both batteries are walked.

1. **0B recon** — enumerate the estate: `subfinder/assetfinder/crt.sh` + `httpx`,
   fingerprint the stack (headers, favicon hash, TLS SAN). Pick templates from the
   fingerprint, not a blanket spray.
2. **0C unauth battery** — `unauth-surface-discovery` →
   `references/unauth-vector-battery.md` (Tier 0→7): `.well-known`, `.git/.env`,
   framework-specific exposure, discovery oracles, access-control probes, injection,
   infra/DNS. Every reachable tier to an artifact or a W-ritten negative.
3. **Provision the account** — self-serve signup (headed browser if WAF/Turnstile),
   mint a SECOND account the moment the first lands (anti-abuse walls usually appear
   after the first). `disposable-auth-identity` for the inbox.
4. **0C authed battery** — `authed-webapp-audit` → `references/authed-vector-battery.md`
   (Tier 0→7): session settle + identity assert, BOLA differential (marker-seeded),
   BFLA, money-surface business logic, race, session lifecycle, export-exposure,
   authed injection.
5. **Chain every lead ≥3x** — `exploit-chain-graph` + `exploit-depth` to L5. One
   endpoint in isolation is a probe; the same primitive composed across IDOR→ATO /
   IDOR→refund / race→double-spend is the finding.
6. **0F report gate** — three-part negative (tested counts / NOT-tested with named
   gate / tool artifacts) before any "0 temuan" claim. Same exit-gate as both batteries.

Rules that keep it honest:
- **Do not gate into authed until the reachable unauth tiers are walked** — the highest-
  severity primitives (unauth collection dump, `.env`, actuator) live there and are free.
- **Run `proactive-hunt-driver` at the 0B→0C boundary** to force the fitur→class matrix.
- **`bb-2026-attack-surface` first on the money/AI/GraphQL/cache surface** before generic
  IDOR-sequential — those four classes are the top payers in 2026.

## Peta skill per alur

| alur | skill utama | skill eskalasi |
|---|---|---|
| **1. Dangling domain** | `hunt-subdomain` · `dnsReaper` | `hunt-oauth` · `hunt-ato` · `hunt-xss` |
| **2. Zombie API** | `hunt-shadow-api` · `hunt-spa-api` · `api-host-surface-mapping` · `hunt-source-leak` | `hunt-auth-bypass` · `hunt-data-exposure` · `hunt-springboot` · `hunt-ssrf` · `hunt-ssti` |
| **3. Polimerisasi** | `exploit-chain-graph` · `exploit-depth` | semua |
| **6. Smart-account module → drain** | `hunt-aa-modular` | `hunt-diamond-proxy` · `hunt-permit2-signature` · `hunt-rce` |
| **7. Vault/AMM price → oracle → liquidation** | `hunt-vault-inflation` · `hunt-amm-hooks` | `hunt-oracle-l2` · `hunt-restaking-lrt` · `hunt-business-logic` |
| **8. Solver/attestor trust → settlement theft** | `hunt-intent-settlement` | `hunt-permit2-signature` · `hunt-race-condition` · `web3-audit` |

## Aturan lintas alur

1. **Anon control dulu** — selalu bandingkan tanpa auth vs dengan auth
2. **Minimal 10 record** untuk klaim data exposure
3. **Depth L5** sebelum lapor; `depth_gate.py` memblokir yang dangkal
4. **Sebut eskalasi** atau alasan primitif habis (`exploit-chain-graph`)
5. **Proof-of-control, bukan phishing** — untuk takeover, sajikan marker, jangan meniru korban
6. **Lepas klaim** setelah bukti lengkap, dan catat di laporan

## Alur tambahan

- **`attack-flows-db-web3`** — alur 4 (menyerang lapisan DATABASE: 8 vektor masuk,
  dari permukaan sampai RCE) dan alur 5 (web3: bytecode → decompile → 12 kelas bug →
  PoC Foundry).

### Alur 6 — Smart-account module → drain (web3)
1. Fingerprint account type: `installModule`/`setValidator` di ABI, atau chain dengan EIP-7702 aktif.
2. `hunt-aa-modular` probe 1: install module dengan address attacker dari akun terkontrol.
3. Kalau diterima → `onInstall` berjalan di konteks akun → tunjukkan state write / token move.
4. Eskalasi: kalau module dapat `delegatecall` → `hunt-rce` (arbitrary code sebagai akun).
5. Alternatif entry: validator bypass (malleability / empty-signature) → install module → drain.

### Alur 7 — Vault/AMM price → oracle → liquidation (web3)
1. `hunt-vault-inflation` probe 2: mint 1 wei → donate → victim deposit → cek share victim.
2. Atau `hunt-amm-hooks` probe 1: initialize pool dengan hook address attacker.
3. Rantai: harga pool terdistorsi → protokol lain yang membaca pool ini sebagai oracle
   (`hunt-oracle-l2`) → likuidasi posisi sehat / borrow undercollateralised.
4. Kill test wajib: attacker P&L eksplisit + single-party pool check sebelum klaim.

### Alur 8 — Solver/attestor trust → settlement theft (web3)
1. `hunt-intent-settlement` probe 1: `solve()`/`fill()` dengan solver address arbitrary.
2. Kalau diterima → tunjukkan outbound call dan apa yang bisa dicapai.
3. Alternatif: attestation replay (dua kali / di fork / recipient berbeda) → mint ganda.
4. Eskalasi: `hunt-permit2-signature` kalau intent ditandatangani, `hunt-race-condition` kalau
   settlement bisa race.
