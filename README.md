<p align="center">
  <img src="assets/bannedsini.png" alt="ChiperFlux Agent" width="100%">
</p>

# ChiperFlux Agent ⚕️

<p align="center">
  <a href="https://github.com/iamtubasya/chiper-agent">GitHub</a> | <a href="https://github.com/iamtubasya/chiper-agent/releases">Releases</a>
</p>
<p align="center">
  <a href="https://github.com/iamtubasya/chiper-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/iamtubasya/chiper-agent"><img src="https://img.shields.io/badge/Built%20by-ChiperFlux-blueviolet?style=for-the-badge" alt="Built by ChiperFlux"></a>
</p>

**ChiperFlux Agent** — AI agent yang bisa belajar dari pengalaman, bikin skill otomatis, dan makin pintar seiring waktu. Fork dari [Chiper Agent](https://github.com/NousResearch/chiper-agent) oleh Nous Research.

---

## Fitur Utama

- 🧠 **Self-Improving** — Bikin skill dari pengalaman, improve otomatis
- 💬 **Multi-Platform** — Telegram, Discord, Slack, WhatsApp, Signal, CLI
- ⏰ **Cron Scheduler** — Automasi terjadwal ke platform manapun
- 🔀 **Parallel Agents** — Spawn subagent untuk kerja paralel
- 🖥️ **Runs Anywhere** — Local, Docker, SSH, Modal, Daytona
- 🔧 **25+ Tools** — File, browser, web search, image gen, TTS, dan lainnya
- 📚 **Session Memory** — Ingat percakapan lintas session

---

## Quick Install

### Linux, macOS, WSL2, Termux

```bash
curl -fsSL https://raw.githubusercontent.com/iamtubasya/chiper-agent/main/scripts/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/iamtubasya/chiper-agent.git
cd chiper-agent
pip install -e .
```

---

## Getting Started

```bash
chiper              # Interactive CLI — mulai percakapan
chiper model        # Pilih LLM provider dan model
chiper tools        # Konfigurasi tools yang aktif
chiper config set   # Set config values
chiper gateway      # Start messaging gateway (Telegram, dll)
chiper setup        # Full setup wizard
chiper update       # Update ke versi terbaru
chiper doctor       # Diagnose masalah
```

---

## Konfigurasi

Edit `~/.chiperflux/.env` untuk API keys:

```env
# LLM Provider (pilih salah satu)
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABCdef...

# Optional
XAI_API_KEY=...
ELEVENLABS_API_KEY=...
```

---

## Struktur

```
chiper-agent/
├── agent/          # AI core
├── gateway/        # Messaging platforms
├── tools/          # 25+ built-in tools
├── plugins/        # Plugin system
├── cron/           # Scheduler
├── chiper_cli/     # CLI commands
├── providers/      # LLM providers
├── skills/         # Built-in skills
├── scripts/        # Install scripts
├── tests/          # Test suite
└── docs/           # Documentation
```

---

## Perbedaan dengan Hermes Agent

| Aspek | hermes Agent | ChiperFlux Agent |
|-------|-------------|------------------|
| Command | `hermes` | `chiper` |
| Data Dir | `~/.hermes` | `~/.chiperflux` |
| Code Dir | `/usr/local/lib/hermes-agent` | `/usr/local/lib/chiper-agent` |
| Developer | Nous Research | ChiperFlux / Tubasya |

---

## Credits

- Original: [Hermes Agent](https://github.com/NousResearch/hermes-agent) oleh [Nous Research](https://nousresearch.com)
- Fork & Customization: [ChiperFlux](https://github.com/iamtubasya)

---

## License

[MIT License](LICENSE) — Copyright (c) 2026 ChiperFlux / Tubasya

Original : @NousResearch 👍
