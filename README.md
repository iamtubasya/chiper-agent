<p align="center">
  <img src="assets/bannedsini.png" alt="Chiper Agent" width="100%">
</p>

# Chiper Agent ⚕️

<p align="center">
  <a href="https://github.com/iamtubasya/chiper-agent"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://iamtubasya.github.io/chiper-agent/docs"><img src="https://img.shields.io/badge/docs-online-brightgreen?style=for-the-badge" alt="Docs"></a>
  <a href="https://github.com/iamtubasya/chiper-agent"><img src="https://img.shields.io/badge/Built%20by-Chiper-blueviolet?style=for-the-badge" alt="Built by Chiper"></a>
</p>

**Chiper Agent** — AI agent yang jalan di terminal, Telegram, Discord, dan 20+ platform lain; **belajar dari pengalaman** (skill + memori lintas session), spawn subagent paralel, jalan terjadwal lewat cron, dan punya akses penuh ke terminal & browser. Bisa pakai LLM provider mana saja (OpenRouter, Anthropic, OpenAI, DeepSeek, endpoint lokal/kustom).

> Original project: [Chiper](https://github.com/iamtubasya) · Docs: [iamtubasya.github.io/chiper-agent/docs](https://iamtubasya.github.io/chiper-agent/docs)

| | |
|---|---|
| **Command** | `chiper` |
| **Data dir** | `~/.chiper` (`config.yaml`, `.env`, `skills/`, `memories/`, `state.db`) |
| **Code dir** | editable install (mis. `~/chiper`) |
| **Skill bawaan** | 577 SKILL.md dalam 22 kategori |
| **Slash command** | 79 command (menu Telegram di-cap 30 per scope) |
| **Toolset** | 57 toolset (terminal, file, browser, web, vision, TTS, delegation, cron, …) |
| **Test suite** | 32.000+ test (`pytest tests/`) |
| **License** | MIT |

---

## Alur Besar — dari nol sampai jalan

```
[1 Install] ──▶ [2 chiper setup] ──▶ [3 chiper model] ──▶ [4 pilih jalur]
                                                                    │
                     ┌──────────────────────────────────────────────┤
                     ▼                                              ▼
             [5a Chat CLI]                              [5b Gateway Telegram/dll]
                     │                                              │
                     └──────────────▶ [6 Pakai + Skills + Memory] ◀─┘
                                            │
                                            ▼
                                   [7 chiper update] (kapan saja)
```

| Flow | Perintah inti | Hasil |
|---|---|---|
| 1. Install | `curl … \| bash` | `chiper` siap dipanggil |
| 2. Setup | `chiper setup` | provider, terminal, gateway, tools terkonfigurasi |
| 3. Pilih model | `chiper model` | LLM aktif |
| 4. Jalur pakai | `chiper` **atau** `chiper gateway install` | CLI **atau** bot chat |
| 5. Sehari-hari | slash command (`/model`, `/skills`, `/new`) | kontrol dari dalam chat |
| 6. Update | `chiper update` / `/update` | versi terbaru + migrasi config |

---

## 1 · Install

**Linux, macOS, WSL2, Termux**

```bash
curl -fsSL https://raw.githubusercontent.com/iamtubasya/chiper-agent/main/scripts/install.sh | bash
```

**Manual**

```bash
git clone https://github.com/iamtubasya/chiper-agent.git
cd chiper-agent
pip install -e .
```

Cek kesehatan install:

```bash
chiper doctor
```

---

## 2 · Setup awal

```bash
chiper setup          # wizard interaktif
chiper setup model    # section tunggal: model/provider
chiper setup gateway  # section tunggal: platform chat
```

Isi `.env` (file = **rahasia saja**, pengaturan perilaku di `config.yaml`):

```env
# LLM Provider (pilih salah satu)
OPENROUTER_API_KEY=sk-or-...
ANTHROPIC_API_KEY=sk-ant-...

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABCdef...
TELEGRAM_HOME_CHANNEL=<chat_id>
```

---

## 3 · Pilih model

```bash
chiper model                 # picker interaktif provider + model
chiper config set model.default <nama-model>
```

Dari dalam chat (Telegram/Discord):

```
/model                    # buka picker (8 model/halaman, Next ▶)
/model <nama>             # ganti model session ini
/model <nama> --global    # ganti + simpan ke config.yaml (permanen)
/model --refresh          # ambil ulang daftar model dari base_url (bust cache)
```

> **Endpoint kustom / router lokal:** daftar model diambil **live** dari `{base_url}/models`.
> Cache-nya per-install di `~/.chiper/provider_models_cache.json` — `--refresh` hanya melepas cache itu.

---

## 4 · Jalur pakai

### 4a · CLI

```bash
chiper                        # chat interaktif
chiper chat -q "tugas singkat" # satu query
chiper --continue             # lanjut session terakhir
chiper -s <skill> "prompt"    # pre-load skill tertentu
```

### 4b · Gateway (Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix, DingTalk, Feishu, WeCom, Weixin, Yuanbao, Webhook, API Server, …)

```bash
chiper gateway setup    # pilih + konfigurasi platform
chiper gateway install  # pasang sebagai service background
chiper gateway start    # start/stop/restart/status
```

Dari dalam chat: `/platforms` (cek koneksi), `/restart` (restart gateway), `/sethome` (jadikan chat ini home channel).

> **Catatan container (tanpa systemd):** `/restart` di container exit `75` dan butuh supervisor untuk respawn. Pakai loop respawn (`gw-supervisor.sh`) kalau gateway sering diam setelah restart.

---

## 5 · Sehari-hari — skills, memory, otomasi

```
/skills            cari & install skill dari hub
/skill <name>      load skill ke session sekarang
/reload-skills     rescan ~/.chiper/skills/ (skill baru masuk tanpa restart)
/model /usage      ganti model / cek pemakaian token
/new /continue     session baru / lanjut session lama
/cron              jadwalkan tugas berkala + kirim hasil ke chat
/delegate          (tool) spawn subagent kerja paralel
```

**Prinsip self-improving:** pengalaman yang berguna disimpan sebagai skill (`~/.chiper/skills/`) dan memori (`~/.chiper/memories/MEMORY.md`, `USER.md`) → dipakai ulang di session berikutnya, lintas server yang share repo yang sama.

---

## 6 · Update

```bash
chiper update --check   # cek saja
chiper update -y        # update + migrasi config (tidak menimpa kredensial)
```

Dari chat: `/update` (jalan detached, hasil dikirim balik ke chat).

---

## Konfigurasi

| File | Isi | Aturan |
|---|---|---|
| `~/.chiper/config.yaml` | semua perilaku (model, approvals, compression, delegation, …) | edit kapan saja, **efek setelah restart gateway** |
| `~/.chiper/.env` | **rahasia saja** (API key, bot token) | jangan taruh perilaku di sini |
| `~/.chiper/auth.json` | OAuth token + credential pool | ditulis `chiper auth` |

```bash
chiper config edit            # buka config.yaml di $EDITOR
chiper config set <key> <val> # set cepat
chiper config path            # lokasi config
chiper auth                   # kelola kredensial / credential pool
```

**Approval command** — default instalasi baru sudah **tanpa konfirmasi**:

| Key | Default | Fungsi |
|---|---|---|
| `approvals.mode` | `off` | `manual`/`smart` = minta approve sebelum command berbahaya; `off` = langsung jalan |
| `approvals.cron_mode` | `approve` | `deny` = cron diblok dari command berbahaya |
| `approvals.destructive_slash_confirm` | `true` | konfirmasi saat `/clear` `/new` `/reset` `/undo` |
| `command_allowlist` | `[]` | pola yang di-`/approve always` |

Hardline floor (`rm -rf /`, `mkfs`, `shutdown`, fork bomb, …) **selalu diblok** — tidak bisa dimatikan mode apa pun.

---

## Struktur repo

```
chiper-agent/
├── agent/          # core AI: prompt builder, compression, memory, routing, soul/skill masking
├── chiper_cli/     # CLI + slash command registry (commands.py) + config (config.py)
├── gateway/        # messaging gateway + platforms/ (telegram, slack, signal, …)
├── tools/          # 1 file per tool (terminal, file, browser, web, …) + registry
├── plugins/        # plugin system
├── cron/           # scheduler (jobs + scheduler)
├── skills/         # 577 skill bawaan (22 kategori)
├── scripts/        # install.sh, test runner, tooling
├── tests/          # 32.000+ test
└── website/        # docs (Docusaurus)
```

Dua prinsip desain utama:

1. **Prompt cache per-conversation itu sakral** — jangan ubah system prompt / toolset di tengah percakapan (biar cost murah).
2. **Core sempit, kapabilitas di pinggir** — fitur baru lewat CLI + skill / plugin / MCP, bukan nambah tool inti (tiap tool terkirim di setiap API call).

---

## Troubleshooting cepat

| Gejala | Cek |
|---|---|
| Install aneh / dependensi hilang | `chiper doctor [--fix]` |
| Bot tidak balas / diam | `grep -i error ~/.chiper/logs/gateway.log \| tail -20` |
| Config tidak berubah | config **tidak live** — `systemctl --user restart chiper-agent.service` (atau `/restart` dari chat) |
| Skill baru tidak muncul | `/reload-skills`, pastikan file ada di `~/.chiper/skills/` |
| Model/provider bermasalah | `chiper doctor` → `chiper auth` → cek key di `.env` |
| Ganti provider endpoint | `chiper config set model.base_url <url>` + restart |

---

## Credits

- Original project & konsep: **Chiper** — [github.com/iamtubasya](https://github.com/iamtubasya)
- Fork, customisasi & pengembangan: **Tubasya** — [github.com/iamtubasya/chiper-agent](https://github.com/iamtubasya/chiper-agent)

## License

[MIT License](LICENSE) — Copyright (c) 2026 Chiper / Tubasya
