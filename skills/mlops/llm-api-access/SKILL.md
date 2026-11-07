---
name: llm-api-access
description: "Obtain free/trial LLM API keys and wire them into security-testing tooling (garak, promptfoo, LLM red-team harnesses). Covers the free-tier provider landscape, browser-automated signup with email verification, and the hard ethical boundaries (no farming, no leaked keys, no CAPTCHA auto-solve, no auth bypass)."
version: 1.0.0
---

# LLM API Access

Provisi akses API LLM (gratis/trial) untuk menjalankan tooling security testing — khususnya `garak` & `promptfoo` untuk engagement red-team AI (mis. odin.ai).

## Kapan pakai
- User minta "API key LLM", "free API key", "trial key model bagus", "farming apikey".
- Engagement red-team AI butuh akses model buat garak/promptfoo.
- Blocker "belum ada API key LLM" muncul.

## Batas Etika (HARD — jangan pernah lewat)
Ini pelajaran utama dari sesi nyata. User sering mendorong ke area abu-abu. Pegang garis tanpa bertele-tele:

| Permintaan | Keputusan |
|-----------|-----------|
| "Farming" key bocor / key yang di-share orang | ❌ TOLAK — credential theft |
| "Skip auth" / bypass Telegram/OAuth/auth apa pun | ❌ TOLAK — circumvent kontrol keamanan |
| Auto-solve CAPTCHA (GeeTest slider dll) | ❌ TOLAK — bypass anti-bot. Tawarkan user selesaikan manual, atau minta konfirmasi eksplisit. |
| Bikin banyak akun buat abuse promo/credit/referral | ❌ TOLAK |
| **1 akun buat user sendiri (email sendiri, alur resmi)** | ✅ BOLEH — daftarkan via browser |
| Free tier / trial resmi provider | ✅ BOLEH — riset & set up |
| Audit defensif layanan (user pemilik / ada VDP) | ✅ BOLEH — dalam scope |

**Set ekspektasi jujur soal frontier:** model frontier (Sonnet/Opus/GPT-5.x/Gemini-4) **TIDAK punya free API key di mana pun**. Kalau user minta "Sonnet 5.5 / GPT 5.5 gratis", katakan jelas itu gak ada — jangan muter-muter nyari yang gak ada. Yang gratis "paling dekat frontier" biasanya model MoE besar (Nemotron Ultra 550B, Crouton Alpha, GPT-6 Luna).

## Free-tier landscape (ringkas)
Lihat `references/free-llm-providers.md` untuk daftar lengkap + kuota + syarat kartu.

Ringkasan top (update Nov 2026):
- **OpenRouter `:free`** → `nvidia/nemotron-3-ultra-550b` (550B), `stealth/crouton-alpha` (1M ctx), `google/gemma-4-31b-it` — email doang, tanpa kartu.
- **Google AI Studio** → Gemini 3.x Flash gratis (Gemini 4 & 3.x Pro berbayar).
- **Experiential Labs** → GPT-6 Luna, 1M token/hari.
- **Groq** → GPT-OSS 120B, Qwen — 1000 req/hari, latency rendah.
- **Grokified** → Grok 4.7, $5 credit.
- **Frontier berbayar:** OpenRouter pay-as-you-go, $5-10 cukup buat ribuan call garak (Sonnet 5.5 ≈ $2/M in / $10/M out).

Sumber kanonik: repo `nejib1/Free-LLM` (live di free-llm.com) — direktori komunitas 450+ model / 86 provider dengan transparansi syarat kartu.

## Signup automation (teknik teruji)
Kombinasi yang bekerja di server Linux (headless):

1. **Install browser** (sekali): `agent-browser install` — unduh Chrome for Testing. Kalau error shared-library, `agent-browser install --with-deps`.
2. **Baca kode verifikasi email** via himalaya IMAP: `himalaya envelope list --account gmail`.
3. **Drive UI** pakai `browser_navigate` + `browser_snapshot` + `browser_click` + `browser_type`.
4. **Isi/inspect form programatik** pakai `browser_console` (JS): klik submit `button[type=submit]`, baca dialog `innerText`, cek state checkbox.
5. **Email magic-link/code** lebih reliable daripada OAuth — OAuth Google/GitHub butuh password+2FA yang TIDAK dipegang agent.

Pitfall penting:
- Ref `browser_type` berubah tiap reload → re-snapshot sebelum re-type.
- Setelah klik submit, form masuk state loading (button `disabled=true`) → tunggu 3-5 detik lalu re-check via `browser_console`.
- Ant Design checkbox: input tersembunyi; cek class `.efm_ant-checkbox-wrapper-checked` + klik wrapper, bukan input langsung.
- GeeTest CAPTCHA muncul di step akhir signup → **STOP**, serahkan ke user (bukan auto-solve).
- Akun yang sudah terdaftar (minta password) → pakai reset password via email code, bukan OAuth.

## Wiring ke garak/promptfoo
Simpan key di `.env` (satu file, semua provider). Kedua tool support Google Gemini & OpenRouter natively (OpenAI-compatible endpoint). Buat script validasi `ping_keys.sh` buat cek semua key sekaligus (mana idup, mana mati).

## Referensi
- `references/free-llm-providers.md` — direktori provider free LLM (kuota, syarat kartu, model).
