# ⚡ SUPERAGENT 4.2 — IRONCLAW

### OpenClaw Edition · ⚙️ Hermes-Compatible

Production-grade autonomous agent brain — crypto + dev core, self-hosted, integrity-verified.
**Compatible dengan Hermes runtime** (full H1–H10 crypto dispatch: swap · bridge · DeFi · sniping · monitoring · NFT · contract · deploy). Crypto + dev core, additive capability layers (v4.0→v4.2).

`v4.2` · 55 skills (m1–m48 · x1–x7) · 🔒 integrity-verified · keys never leave your VPS

---

## Quick start

### Install on VPS
> ⚠️ Konvensi OpenClaw berubah — ikuti **`DEPLOY.md`** (root) untuk langkah yang akurat. Blok di bawah ini ditahan sebagai referensi historis.

```bash
# 1. Drop this folder into the agent workspace
cp -r openclaw ~/.openclaw/workspace/superagent/

# 2. Point the agent config at it
nano ~/.openclaw/workspace/openclaw-agents.json
# Add or update:
# {
#   "system_prompt_path": "~/.openclaw/workspace/superagent/AGENTS.md",
#   "skills_dir": "~/.openclaw/workspace/superagent/skills",
#   "memory_dir": "~/.openclaw/workspace/superagent/memory"
# }

# 3. (RECOMMENDED) Enable time-awareness injection in host wrapper
#    See TIME.md Layer 1 for the host-side code that prepends
#    [RUNTIME CONTEXT] block to every user message. Without this,
#    agent falls back to tool call (Layer 2) or inference (Layer 4).

# 4. Restart the agent
pm2 restart openclaw  # or screen -r / systemctl
```

### Load order
1. `AGENTS.md` — core router (always loaded)
2. `IDENTITY.md` + `SOUL.md` — character (always loaded)
3. `HEARTBEAT.md` + `TOOLS.md` + `MEMORY.md` — runtime config (always loaded)
4. `USER.md` — operator profile (always loaded, customize first)
5. `skills/m*.md` and `skills/x*.md` — loaded on-demand by router

Always-on token budget: ~3.5k. Skills bring task-specific knowledge only when triggered.

---

## What's new in v4.2

Rilis aditif — fokus **whitehat & airdrop intelligence**. Identitas inti crypto + dev tetap; semua baru load on-trigger. **192 test offline hijau** (44 hermes + 148 tools), integrity utuh.

- **🎯 Airdrop Intelligence (m31)** — eligibility scorer (skor 0-100 + apa yang kurang), **sybil self-audit** (cek pola multi-wallet sendiri biar gak ke-cluster filter), claim-window calendar (alert H-48/H-2/H-0, time di-inject), exit planner (ladder jual conservative/balanced/degen).
- **🏴 CTF / Whitehat (m32)** — triage kategori, multi-decode (base64/hex/rot13/url/binary), classic crypto (caesar/xor/vigenere), hash-id. **Legal & in-scope only** (R9 gate buat target asing).
- **🛡 Hardening (6 fixes)** — secret tripwire di output layer, dry-run global (engine `plan()` bukan broadcast), cost ledger terpusat (token+on-chain+API), router observability + tie tuner, governor multi-VPS injectable backend, regression suite golden-set (`eval.py`), plus README/skill-count/test-leak cleanup.
- **📡 Extension wave (m33–m42, 2026-06-12)** — 10 modul opsional baru, semua offline/deterministik/zero-dep: **alpha radar** pre-TGE (skor proyek sebelum token ada), **farm ROI optimizer** (EV per posisi, keep/trim/drop), **auto guide studio** (panduan ID + varian TG/X + referral), **unlock pressure engine** (kalender vesting vs likuiditas), **anti-scam sentinel** (typosquat + drainer signals, read-only), **contract watcher** (`safe_to_claim` gate), **community intelligence** (topik/FUD/sentimen), **omni-repurpose** (1 konten → X/TG/IG/TikTok/YT), **video pipeline** (script+storyboard+SRT), **hook A/B lab** (prediksi stop-scroll 0-100). +63 test baru.
- **🚩 CTF Swarm (m43–m48 + `tools/ctf/`, 2026-06-12)** — framework CTF full-auto whitehat di bawah orchestrator **m32**: 6 sub-skill kategori (**web · pwn · rev · crypto · forensics · prompt-injection/LLM**) + coordinator runtime (poll CTFd → race N model per soal di sandbox Docker → consensus/HITL submit). Pengaman: `scope_guard` (allowlist, deny menang), `flag_validator` (full-match anti-halusinasi), `rsa_attacks` (offline, gmpy2-optional). Plus **m48** (prompt-injection/LLM red-team, host-locked Gandalf solver + full-auto coordinator wiring) dan adapter **Anthropic/OpenAI/Gemini** lengkap (race lintas-provider, REST zero-SDK). +46 test offline.

Detail lengkap di `CHANGELOG.md` (v4.2 section).

---

## What's new in v4.1

Rilis aditif. **Identitas inti tetap crypto + dev** — semua yang baru = modul **opsional** yang load on-trigger, gak ganggu karakter utama. Safety machinery v4.0 utuh & diperluas.

- **🧠 Eval & debug** — x5 agentic eval + **variance testing** (konsistensi <0.95 → jangan otomasi), x6 systematic debugging 4-fase + auto-debug hypothesis loop, instinct extraction (x4).
- **🎨 Creative & media (m18)** — ComfyUI · Manim · Excalidraw · ASCII/retro video · web design systems · slides · aesthetic judgment.
- **🤖 Desktop & physical (m19)** — macOS native control **background-first, no cursor steal** · Isaac Sim/Omniverse · scene prep · mobility (ROS2).
- **✍️ Humanizer (m20)** — buang AI-tone → suara natural + brand voice.
- **🛡 Enterprise & defensive (m21)** — Azure/KQL troubleshooting · Mini-HIDS auto-firewall (allowlist+TTL+dry-run).
- **🧭 Soft skills (x7)** — problem shaping · brainstorming sign-off · decision support w/ uncertainty.
- **🧩 Marketplace** — skills.sh via quarantine (audit dulu, baru aktif).
- **🔬 Research & meta (wave 2)** — m22 deep research (AI-Q, bersitasi), m23 executive-function/neurodivergent, m24 MCP-builder + prompt-engineer, m25 compliance/CI-CD/code-migration, m26 To-PRD/To-Issues/TDD; x5 **LLM-as-judge**; m19 **Cosmos** + meta-actions; `STANDARD.md` (open SKILL.md/progressive disclosure/cross-platform).
- **📣 Content & marketing (wave 3)** — m27 content strategy & social (calendar, platform adapter, hooks, thread/carousel/reels), m28 copywriting mastery (AIDA/PAS/CHEF, SEO, storytelling, localization/RTL), m29 content research/analytics/**full pipeline** (research→draft→visual→schedule→analyze); m22 scientific libraries + Hugging Science; m19 **VLA**/multimodal.
- **🔒 Safety** — FROZEN_PATHS diperluas (hids/desktop/marketplace), aksi OS/desktop/robot fisik → R9 gate, SKILLS.lock diregenerasi.

Detail lengkap di `CHANGELOG.md` (v4.1 section).

## What's new in v4.0

Major release dari baseline v3.1 — nambahin lapisan keamanan/governance, self-improvement, asisten harian, tooling smart-contract (baca/tulis/deploy), manajemen LLM dinamis, power pack orkestrasi, dan skill software-engineering.

- **🛡 Safety & governance** — Spend Governor (cap + kill-switch), MEV protection, skill integrity (`SKILLS.lock`), FROZEN_PATHS.
- **🧠 Self-improvement** — compounding memory + reflection loop (x4), semua di balik gate struktural.
- **📅 Daily assistant (m14/m15)** — briefing, alert engine, watchdog, vault+macro, voice/screenshot input, triage.
- **🔗 Contract tooling** — universal reader + writer (gated) + crypto-dev deploy/compile/test/verify (CREATE2).
- **🧩 Dynamic LLM (m7)** — `add model` satu perintah, key terenkripsi, masuk cascade R7.
- **⚙️ Power Pack (m17)** — planner, swarm, skill-forge, automation, backtest, dashboard, voice mode, explainability.
- **💻 Software engineering (m16)** — backend/db/testing/scaffold/refactor; full-stack bareng m9+m2+x3.
- **🛠 Tooling** — `.env.example` lengkap + `DEPLOY.md`.

Detail lengkap di `CHANGELOG.md` (v4.0 section).

## What's in v3

### Core files
| File | Purpose |
|---|---|
| `AGENTS.md` | Router, rules R1-R10, weighted keyword table |
| `IDENTITY.md` | Response speed tiers, character modes |
| `SOUL.md` | Flexibility doctrine, hard stops, operational rails |
| `TIME.md` | **5-layer time awareness** (NEW — system inject → tool call → cache → infer → disclose) |
| `HEARTBEAT.md` | Session continuity, time refresh, token discipline |
| `TOOLS.md` | Agent-side vs operator-side execution, time tool specs |
| `USER.md` | Operator profile template (FILL THIS IN) |
| `MEMORY.md` | Compaction rules, format |
| `CONTRIBUTORS.md` | Credits — community contributors |
| `panduan.md` | Operator usage guide with real examples |

### Skills
| Skill | Domain |
|---|---|
| m0 | Skill registry, reflection loop |
| m1 | Monetization, business ops |
| m2 | VPS, infra, deployment |
| m3 | Content, copywriting, Indonesian voice |
| m4 | Telegram bots, production patterns |
| m5 | Data handling, snapshots, large files |
| m6 | Integrations, payments, webhooks |
| m7 | AI providers, multi-LLM, streaming, fallback |
| m8 | Documents (docx/xlsx/pptx/pdf), images |
| m9 | Frontend, landing pages, Web3 UI |
| **m10** | **Web3 ops, on-chain, mass farming** *(NEW)* |
| **m11** | **Security audit, skill safety, secret scan** *(NEW)* |
| **m12** | **Batch ops, parallel exec, queues** *(NEW)* |
| **m13** | **Universal NFT minter — OpenSea/Manifold/Zora, auto-gas** *(NEW)* |
| **hermes** | **Deep crypto layer** — multi-chain wallets, 1inch/Jupiter swap, Seaport/Blur/ME NFT buy, LI.FI bridge, Aave/Lido/GMX DeFi, mempool sniffer, Nansen/Arkham smart money, sniping with honeypot gate *(INTEGRATED)* |
| x1 | Self-audit, system refinement |
| x2 | Deep decomposition, strategy |
| x3 | Debug, fault diagnosis |

---

## Configure for your operator
Edit `USER.md`:
- Name, honorific, timezone
- Domain focus checkboxes
- Trigger phrases
- Language default

---

## Upgrade from v2
- Back up v2 memory: `cp -r ~/.openclaw/workspace/superagent-v2/memory ~/.openclaw/backups/`
- Drop v3 in beside it (don't overwrite v2 immediately)
- Test on staging agent if available
- Migrate memory: copy daily logs into `v3/memory/`
- Switch agent config to v3 path
- Keep v2 for 7 days before deleting

See `CHANGELOG.md` for full version history.

---

## Token budget
- Always-on: ~3.5k
- Light skill load (1 skill): +0.5-1.5k
- Heavy skill load (2-3 skills, e.g. m4+m7+m10 on Web3 bot bug): +3-5k
- Hermes deep ref: +2-4k per reference, loaded only on H-skill match
- Hard ceiling: 12k context spent on system. If higher, run x1 audit.

## How hermes loads (token discipline)
H-skills never preload. When operator mentions e.g. "bridge layerzero":
1. `hermes/DISPATCH.md` loads once per session (cached)
2. `hermes/references/bridge.md` loads only when bridge keyword fires
3. Other 9 references stay on disk until their keywords trigger

10 deep references add ~0 always-on cost.
