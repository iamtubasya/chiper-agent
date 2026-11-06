# Recon Techniques — bug-bounty reference

> **SPA/staging target tanpa akun?** Baca `references/js-bundle-recon.md` — bundle mining → endpoint map → response classification. Proven on Luno staging (luno-og): 33 API paths + WS gateway + CSRF flow extraction dari main.js/vendor.js, tanpa akun, tanpa temuan palsu (semua 401/405 diklasifikasi sebagai "the wall works", bukan finding).

## Quick classification table (unauth probe)

| Response | Meaning | Action |
|---|---|---|
| 401 `ErrUnauthorized` + "type mismatch" | Multi-auth-type surface (cookie vs API key) | Auth-confusion candidate — retry setelah punya akun |
| 405 on GET | POST-only (trade/order/move) | CSRF enforced; map sekarang, test pasca-registrasi |
| 400 param-specific ("invalid duration: must be a number") | Parser hidup | Fuzz candidate |
| 404 on documented prod path | Staging layout beda dari prod docs | Trust bundle, bukan docs |
| 200 static content | Low value | Skip |
| CF 403/challenge di semua host | Origin tersembunyi baik | Jangan grind; pivot ke auth surface |

## Staging vs prod

- Staging biasanya mirror prod behavior persis (Luno: Cloudflare di semua host, clean 401s, zero origin leak). Artinya: **permukaan unauth deadlock** → kuncinya akun uji.
- Changelog brief (Bugcrowd) jarang berisi material baru — cek sekali saja, fokus ke brief utama.

## Artifact convention

Simpan ke `D:\data hermes\bug-bounty\_progress\<target>\`:
- `js/main.js`, `js/vendor.js` — harvested bundles
- `RECON-STATUS.md` — asset map, API behavior, next candidates (resumable cold)
- `cookies.txt`, `crtsh_*.json` — evidence
