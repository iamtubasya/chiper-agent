# RCE Surface Atlas — 10 entry points (web2 + web3)

**Kenapa file ini ada.** `hunt-rce` dan skill kelas turunannya punya *payload* dan *teknik*.
File ini memetakan **titik masuk** — di mana RCE benar-benar bisa lahir — plus apa yang
membuktikannya, dan di kedalaman mana harus digali.

Aturan: **satu kelas belum tercakup sampai setiap permukaan dicoba atau N/A dengan alasan teknis.**

Severity mengikuti impact terminal. RCE yang tidak terbukti eksekusi = bukan RCE.

---

## A. WEB2 — 7 titik masuk

### A1. Deserialisasi tidak aman
| | |
|---|---|
| **Permukaan** | cookie sesi, token "remember me", cache/session store, `ViewState`, RMI/JMX, queue message, file upload yang di-parse, parameter `?data=` base64 |
| **Probe pertama** | cari blob base64/hex panjang di cookie atau body → decode → cek magic: Java `AC ED 00 05` / `rO0AB`, PHP `O:`, Python `\x80\x02`/`\x80\x04`, .NET `AAEAAAD/////` |
| **Bukti** | gadget chain benar-benar jalan: `ysoserial` (Java), `phpggc` (PHP), `pickle` `__reduce__` (Python) → callback OOB atau output command |
| **Sev** | Critical |
| **Depth** | `hunt-deserialization` · `hunt-aspnet` (ViewState) |

Jebakan: deserialisasi yang **hanya** memicu error bukan temuan. Butuh eksekusi atau OOB callback.

### A2. File upload tanpa validasi konten
| | |
|---|---|
| **Permukaan** | avatar, dokumen, impor CSV/XML, lampiran tiket, tema/plugin CMS, backup restore |
| **Probe** | kirim `shell.php` dengan `Content-Type: image/png` + magic bytes `GIF89a` di depan; coba ekstensi `.phtml .php5 .phar .pht .php.` `;` `.jpg.php`; nama `x.php%00.jpg`; `.htaccess` upload |
| **Bukti** | file bisa diakses via URL dan **dieksekusi** (bukan cuma diunduh sebagai teks) |
| **Sev** | Critical (RCE) / High (stored XSS via SVG/HTML) |
| **Depth** | `hunt-file-upload` · `hunt-laravel` · `hunt-aem` |

Jebakan: "upload berhasil" ≠ eksekusi. Wajib buktikan path URL-nya dan interpreter-nya.

### A3. Command injection di parameter sistem
| | |
|---|---|
| **Permukaan** | konversi gambar (`convert`, `ffmpeg`), ping/traceroute/nslookup, backup/export, PDF generation (`wkhtmltopdf`, `pdflatex`), git operations, archive extract (`tar`, `unzip`), DNS lookup |
| **Probe** | `;id` `\|id` `$(id)` `` `id` `` `%0aid` `&&id` `\n id`; untuk blind: `;sleep 5`, `;curl <interactsh>`; filter bypass: `$IFS`, `${IFS}`, `{cat,/etc/passwd}`, `c\at`, `who$@ami` |
| **Bukti** | output command di respons ATAU delay terukur ATAU callback OOB |
| **Sev** | Critical |
| **Depth** | `hunt-rce` |

Jebakan: parameter yang "kelihatan seperti" command (`?sort=name`) belum tentu shell. Uji dengan `sleep`, bukan `id`, untuk menghindari WAF + membuktikan timing.

### A4. Template injection (SSTI)
| | |
|---|---|
| **Permukaan** | nama/email di email template, PDF/invoice generator, preview template, notifikasi, laporan kustom, "custom email body", error page yang memantulkan input ke template |
| **Probe** | poliglot: `${7*7}` `{{7*7}}` `#{7*7}` `<%= 7*7 %>` `{7*7}` `@(7*7)` `[[7*7]]` → cari `49`. Lanjut: `{{7*'7'}}` (Jinja2=49, Twig=7777777) |
| **Bukti** | evaluasi aritmetika terjadi **di server**, lalu eskalasi ke `__class__`/`__mro__` (Jinja2) atau `_self.env` (Twig) → RCE |
| **Sev** | High→Critical |
| **Depth** | `hunt-ssti` |

Jebakan: `{{7*7}}` yang muncul sebagai `49` di **client-side** (JS framework) bukan SSTI. Cek di respons mentah server.

### A5. Dependency / supply chain (CVE RCE)
| | |
|---|---|
| **Permukaan** | versi framework/library, plugin CMS (WordPress/WooCommerce/Drupal/Joomla), middleware (Log4j, Spring, Struts, Confluence, Jenkins), JS build artifact yang memuat versi |
| **Probe** | fingerprint versi (`/wp-content/plugins/<slug>/readme.txt`, `X-Powered-By`, JS bundle, `package.json` bocor) → cocokkan CVE publik → jalankan PoC **versi-spesifik** |
| **Bukti** | PoC CVE berjalan pada versi yang terpasang (bukan "seharusnya rentan") |
| **Sev** | High→Critical (tergantung CVE) |
| **Depth** | `hunt-rce` · `hunt-springboot` · `hunt-laravel` · `hunt-sharepoint` · `hunt-aem` |

Jebakan: versi terdeteksi ≠ versi rentan (backport patch). Coba PoC dulu, jangan lapor dari versi saja.

### A6. Admin panel / debug endpoint terbuka
| | |
|---|---|
| **Permukaan** | Spring Boot Actuator (`/actuator/env`, `/actuator/heapdump`, `/actuator/gateway/routes`, `/jolokia`), Werkzeug console (`/console` + PIN), Django debug, Laravel `/_ignition/execute-solution`, PHPInfo, `/debug/vars`, GraphQL playground, Jenkins script console |
| **Probe** | direktori sweep terarah per framework; untuk Actuator: `POST /actuator/env` set `spring.cloud.gateway.routes` → SpEL RCE; untuk Werkzeug: hit `/console` → butuh PIN, cari PIN leak di `/proc` via LFI |
| **Bukti** | aksi yang mengubah state server, atau eksekusi (SpEL/OGNL/EL) |
| **Sev** | High→Critical |
| **Depth** | `hunt-springboot` · `hunt-laravel` · `hunt-nodejs` |

Jebakan: `/actuator` terbuka tapi hanya `health`/`info` = Low, bukan RCE. Cek endpoint yang benar-benar mengeksekusi.

### A7. Unsafe eval / reflection / plugin sandbox escape
| | |
|---|---|
| **Permukaan** | fitur "custom script", formula/spreadsheet, rule engine, template plugin, expression language di filter/report, "advanced search" DSL, webhook transform, user-defined function |
| **Probe** | injeksi ekspresi: SpEL `T(java.lang.Runtime).getRuntime().exec(...)`, OGNL, MVEL, Groovy, JS `require('child_process')`, Python `eval` via `__import__` |
| **Bukti** | eksekusi terjadi di server; sandbox benar-benar terlewati (bukan cuma "script tersimpan") |
| **Sev** | Critical |
| **Depth** | `hunt-rce` · `hunt-nodejs` |

Jebakan: banyak "sandbox" hanya membatasi UI. Uji bypass: `constructor.constructor('return process')()`, prototype pollution → RCE.

---

## B. WEB3 — 3 titik masuk (analog RCE)

### B1. Node / RPC dengan method debug & admin terbuka
| | |
|---|---|
| **Permukaan** | RPC publik (`:8545`, `:8546`, `:8547` Besu, `:9933` Substrate, Hedera mirror/consensus node), `debug_*`, `admin_*`, `personal_*`, `miner_*`, `txpool_*`, `eth_accounts` yang mengembalikan akun **ter-unlock** |
| **Probe** | `{"jsonrpc":"2.0","method":"rpc_modules","id":1}` → lihat modul aktif; lalu `admin_nodeInfo`, `admin_peers`, `debug_traceTransaction`, `personal_listAccounts`, `eth_accounts` |
| **Bukti** | modul admin/debug aktif **dan** ada dampak: akun ter-unlock bisa dipakai `eth_sendTransaction` (drain dana), atau kontrol node (addPeer/setHead/startRPC) |
| **Sev** | High→Critical |
| **Depth** | `evm-chain-recon` · `hunt-diamond-proxy` (bila menyentuh kontrak) |

**Penting — bedakan dua hal:**
- **RPC publik untuk baca** (`eth_call`, `eth_getLogs`) = by design, **bukan** temuan.
- **Modul `admin_`/`personal_`/`debug_` aktif + akun ter-unlock** = temuan nyata.

`personal_unlockAccount` + `eth_sendTransaction` adalah jalur paling langsung ke kehilangan dana —
dan paling sering dibayar. Buktikan dengan akun milik sendiri, jangan pernah memindahkan dana pihak lain.

### B2. Proxy / upgradeable misconfiguration
| | |
|---|---|
| **Permukaan** | `initialize()` yang bisa dipanggil ulang (**reinit**), implementasi yang belum di-inisialisasi, `upgradeTo`/`upgradeToAndCall` tanpa auth, storage collision, selector clash, `delegatecall` ke target arbitrer, `selfdestruct` di implementasi |
| **Probe** | panggil `initialize(...)` **kedua kali** dengan akun sendiri → berhasil? cek `initialized`/`_initializing` flag; panggil fungsi implementasi **langsung** (bukan lewat proxy) → apakah state implementasi bisa diambil alih; cek `getImplementation()` vs `upgradeTo` auth |
| **Bukti** | state proxy berubah oleh pemanggil tak berhak, ATAU implementasi bisa diganti → kontrol logika kontrak (analog RCE: eksekusi logika arbitrer) |
| **Sev** | Critical (bila menyentuh dana) |
| **Depth** | `hunt-diamond-proxy` · `web3-audit` · `hunt-aa-modular` |

Jebakan: `initialize()` yang revert pada panggilan kedua = benar (sudah dijaga). Yang dicari:
flag tidak pernah di-set, `initializer` modifier absen, atau implementasi bisa di-`initialize` langsung.

### B3. Build / CI pipeline untuk node software
| | |
|---|---|
| **Permukaan** | workflow GitHub Actions (`.github/workflows/*.yml`), dependency npm/pip/cargo yang dipakai operator node, image Docker rilis, artefak rilis yang tidak ditandatangani, script instalasi (`curl \| bash`), Dockerfile `latest` |
| **Probe** | baca workflow publik repo target: `pull_request_target` + checkout PR head, `${{ github.event.* }}` masuk ke `run:`, secret dipakai di job yang bisa dipicu fork, dependency tanpa lockfile, `actions/*` tidak di-pin ke SHA |
| **Bukti** | jalur eksekusi kode di runner/infrastruktur operator (bukan cuma "workflow terlihat longgar") |
| **Sev** | Critical |
| **Depth** | `cicd-security` · `hunt-cicd` · `supply-chain-attack-recon` |

Jebakan: workflow publik yang "terlihat salah" tanpa jalur eksekusi = observasi, bukan temuan.
Buktikan rantainya: pemicu → langkah → eksekusi → dampak.

---

## C. Matriks silang — permukaan × teknik

| Permukaan | Teknik | Kelas |
|---|---|---|
| A1 cookie Java | ysoserial gadget + JNDI | RCE |
| A1 PHP upload | `phar://` deserialization | RCE |
| A2 upload | polyglot `GIF89a` + `.phtml` | RCE |
| A3 konversi gambar | ImageMagick MVG / `convert` injection | RCE |
| A4 email template | Jinja2 `__class__.__mro__` | RCE |
| A5 plugin WP | CVE versi-spesifik | RCE |
| A6 Actuator | `POST /env` → SpEL | RCE |
| A7 expression | SpEL/OGNL sandbox escape | RCE |
| B1 RPC | `personal_unlockAccount` → `eth_sendTransaction` | fund loss |
| B2 proxy | reinit / upgrade tanpa auth | logic control |
| B3 CI | `pull_request_target` + PR head | infra RCE |

---

## D. Gate sebelum submit

**RCE**
- [ ] Eksekusi **terbukti** (output command, callback OOB, atau side effect terukur) — bukan error/stack trace
- [ ] Kontrol: payload jinak → perilaku berbeda
- [ ] Tidak memindahkan/merusak data pihak lain; pakai `id`/`whoami`/`sleep`, bukan `rm`/`drop`

**Web3 RPC**
- [ ] Bukti modul admin/debug **aktif**, bukan cuma port terbuka
- [ ] Dampak konkret (unlocked account / node control), diuji dengan akun sendiri
- [ ] Bukan RPC baca publik (by design)

**Web3 proxy**
- [ ] State berubah oleh pemanggil tak berhak, dibuktikan dengan dua akun
- [ ] Kontrol: panggilan yang sama oleh pemilik sah → hasil berbeda
- [ ] Bukan testnet-only / bukan kontrak tanpa dana

---

## E. Hubungan dengan file lain

| Butuh | Buka |
|---|---|
| Payload & teknik per kelas | `hunt-rce`, `hunt-deserialization`, `hunt-ssti`, `hunt-file-upload` |
| Framework spesifik | `hunt-springboot`, `hunt-laravel`, `hunt-nodejs`, `hunt-aspnet`, `hunt-sharepoint`, `hunt-aem` |
| Permukaan ATO/IDOR/SSRF | `ato-idor-ssrf-surface-atlas.md` |
| Komposisi Low → Critical | `chain-to-impact`, `redteam-mindset` §3.5 |
| Bentuk bukti yang lolos gate | `evidence-state-ladder-and-reachability-gate.md` |

---

*10 titik masuk. RCE tanpa bukti eksekusi bukan RCE — itu stack trace.*
