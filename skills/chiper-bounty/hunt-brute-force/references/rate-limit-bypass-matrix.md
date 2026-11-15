# Rate-Limit / Brute-Force Bypass Matrix — 4-state classify + bypass + entropy

Katalog eksekusi cepat untuk `hunt-brute-force`. SKILL.md sudah punya 4-state table + 6 phase + ReDoS;
di sini condensation jadi matriks classify→bypass→proof. Additive-only.

**Prinsip (dari SKILL.md):** jangan collapse 4 state rate-limit. "No rate limit" baru boleh diklaim
setelah bukti **shadow-throttle** tidak ada + **seed test** lolos. 101 success ≠ 10^6 brute-able.

---

## A. 4-state classification (WAJIB dipilah, jangan gabung)

| State | Signal | Arti |
|---|---|---|
| **1. No rate limit** | status+latency+body SAMA semua attempt | kandidat brute |
| **2. Soft throttle** | 429/403 muncul, tapi counter reset cepat | bisa brute dengan jitter/slow |
| **3. Lockout** | 423/429 persistent + Retry-After + counter tak reset | brute mati (kecuali bypass IP) |
| **4. Shadow throttle** | status tetap 401, tapi **latency naik** / body berubah | DIAM throttling — no limit PALSU |

**5th state (Edge/WAF throttle):** 403/429 pada halaman yang seharusnya 200 render = edge block,
bukan app logic. Cek: path yang sama di SIBLING host (block vs outage), dan app masih up.

---

## B. Seed test (positive control WAJIB)

```
Seed: posisi 500 di wordlist = OTP ASLI akun tes sendiri.
Loop sampai 500 → kalau kode benar TIDAK lagi authenticate = endpoint SILENT throttling/dropping.
Artinya "no rate limit" klaim = salah.
```

**Aturan:** clean probe (101 success) = perlu, bukan cukup. Seed test yang membedakan no-limit vs shadow.

---

## C. Bypass matrix (defense → bypass)

| Defense | Bypass | Proof bar |
|---|---|---|
| Per-IP limit | spoof source header: `X-Forwarded-For`, `X-Real-IP`, `X-Client-IP`, `True-Client-IP`, `CF-Connecting-IP` | 429 hilang saat rotate header |
| Per-IP limit (multi-value) | `XFF: 1.2.3.4, 5.6.7.8` (comma-joined) | parser ambil pertama/terakhir |
| Per-session limit | oprek `session`/`cookie` rotasi | counter reset |
| Per-account limit | rotate `email`/`username` casing (`Vic@x` / `vic@x` / `VIC@x`) | counter bypass |
| CAPTCHA after N attempt | reset flow via endpoint alternatif tanpa captcha | captcha skip |
| Method-specific limit | method override `X-HTTP-Method-Override: GET` | GET tidak terhitung |
| Time-window lockout | jitter + slow drip (`-p 0.5`) | counter decay |

---

## D. OTP / 2FA brute (jangan klaim 10^6 tanpa math)

```
2a. PoC probe (101 code, no 429/lockout) → candidate
2b. Full keyspace IMPACT (jangan execute, hitung saja):
    keyspace 10^6 ; throughput req/s ; ~half = 5e5/req_s
    code rotate tiap T detik → bound = req_s * T per window
    Brute viable HANYA kalau (throughput*code_lifetime) ≈ keyspace
    ATAU code tidak rotate / reset unlimited (Instagram-2019 class)
```

**Report the math, jangan exhaust 10^6 ke pihak ketiga.** Severity = keyspace REACHABLE, bukan 101 success.

---

## E. Username/email enumeration (string + status + timing)

```
string + status: valid vs invalid beda pesan/status/len → enumeration
timing oracle: valid user hash password (lambat ~180ms) vs invalid short-circuit (~40ms)
               sample MANY, bandingkan MEDIAN (1 request = noise)
reset + registration: endpoint beda response untuk email registered vs tidak
```

**Proof bar:** median delta reproducible (bukan 1 request). Side-channel endpoint (Phase 3a) yang
tak di-rate-limit = oracle yang sering ketinggalan.

---

## F. Token entropy (ukur, jangan eyeball)

```
1. Shannon entropy / compressibility → low entropy = predictable
2. hex/base64 → decode → cari structure (timestamp, counter, PID)
3. sequential/time-correlated → sort + diff numeric consecutive
4. Burp Sequencer (10k token) → FIPS/NIST → effective bits < 64 = finding
```

---

## G. ReDoS detection

```
payload: "a"*N + "!"  ke email/URL/search regex
DOUBLING latency per +5 char (super-linear) = ReDoS
control: benign string byte-length sama → fast → regex-driven blow-up
```

---

## Priority order (sweep cepat per target)

1. Login rate-limit → class 4-state (Tier A).
2. Seed test (positive control) → bedakan no-limit vs shadow.
3. Bypass source-header (C) → kalau 429 muncul.
4. Enumeration (E) → string + timing.
5. OTP 2a probe → matematika keyspace (D), jangan lapor 101.
6. Token entropy (F) → kalau token reset/session ada.
7. ReDoS (G) → kalau search/validation endpoint.

## Refusal-pattern

- "No rate limit" tanpa seed test / shadow-throttle check → **klaim palsu**, downgrade.
- 101 success ≠ 10^6 brute-able → jangan lapor High.
- 403/429 pada halaman 200-render = edge block, bukan app logic (5th state).
- Rate-limit di `/forgot-password` tanpa brute yang mendarat = rutin ditolak.