# CHANGELOG — SUPERAGENT OPENCLAW EDITION

Version history. Baseline **v3.1** (2026-05-25) → **v4.0** (2026-06-03) → **v4.1** (2026-06-04) → **v4.1.1** (2026-06-05) → **v4.1.2** (2026-06-05) → **v4.2** (2026-06-09).

---

## v4.2 (update 2026-06-12) — CTF PROMPT-INJECTION / LLM RED-TEAM (m48)

Update aditif **dalam v4.2** — versi TIDAK naik. Nambah kategori CTF **AI/LLM** ke keluarga CTF (orchestrator m32). Nambah **1 sub-skill (m48)** + **`tools/ctf/gandalf_solver.py`** (host-locked solver buat Lakera Gandalf, mode static + adaptive) + **test offline buat extractor**. Total skill **54 → 55** (m1–m48 · x1–x7).

### 🤖 Yang baru
- **m48 — CTF Prompt-Injection / LLM Red-Teaming**: methodology ngalahin guard berlapis (input vs output guard), defense ladder Gandalf L1–L8, taksonomi 8 teknik (authority reframe, indirect, encoding, format coercion, language switch, roleplay, instruction extraction, sidestepping), workflow + defensive takeaway (tiap bypass = peta kontrol). Dispatched m32 buat soal "AI/LLM/jailbreak".
- **`tools/ctf/gandalf_solver.py`**: solver otomatis **host-locked ke gandalf.lakera.ai** (`_check_host` nolak host lain). Mode `static` (ladder strategi) + `adaptive` (attacker-LLM lewat `coordinator/llm.py`). `candidates()` ekstrak kandidat secret (ALL-CAPS, acrostic, separated-letters, base64/rot13 decode) — pure/offline, ke-test.
- **Full-auto wiring (coordinator)**: kategori AI/LLM sekarang ikut ke-solve di swarm `run.py`, gak cuma manual. `solver.build_system()` nyuntik addendum red-team m48 ke system prompt buat soal AI/LLM doang; `coordinator.extract_targets()` narik target dari `connection_info` **+ URL di deskripsi**, semua di-scope-check sebelum dikasih network (`bridge`). Soal AI/LLM tanpa target keparse = di-skip aman.
- **Adapter OpenAI + Gemini lengkap (`coordinator/llm.py`)**: bukan stub lagi — Chat Completions (OpenAI) & generateContent (Gemini) full tool-calling, REST murni zero-SDK. History kanonik = format blok Anthropic; tiap adapter konversi via fungsi pure yang ke-test offline (`to_openai`/`from_openai`/`to_gemini`/`from_gemini`), stop_reason dinormalisasi ke `tool_use`. Gemini: functionResponse di-key pakai NAMA (id→nama di-resolve dari history), id call disintesis stabil. `config.validate()` sekarang nagih API key per provider yang dipakai di `MODELS`. Swarm bisa race lintas-provider buat semua kategori, termasuk AI/LLM.

### 🔍 Review & perbaikan
- **Model ID placeholder** `anthropic:claude-opus-4-8` (gak ada) → diselaraskan ke `claude-opus-4-1` (konsisten sama config coordinator).
- Catatan: API contract Gandalf (path/field/defender id) gak resmi dipublish → didokumentasiin "VERIFY di DevTools" di skill + docstring. Adapter `.step()/.text` udah cocok sama `AssistantTurn`.

### 📚 Docs
- m32 dispatch + delegation table (+row m48), AGENTS.md, m0.md, INDEX.md, IDENTITY.md, README.md (55 skills), panduan.md (item 12 diperluas + cheat-sheet row). `SKILLS.lock` regen & verified.

---

## v4.2 (update 2026-06-12) — CTF SWARM INTEGRATION (m43–m47 + tools/ctf)

Update aditif **dalam v4.2** — versi TIDAK naik. Integrasi paket CTF agent (karya operator/Setya) ke dalam SUPERAGENT, kompatibel dengan m32 (CTF/whitehat) yang sudah ada. Nambah **5 sub-skill kategori** (m43–m47) + **package `tools/ctf/`** (orchestrator helpers + full-auto coordinator runtime + sandbox) + **24 test offline baru**. Total skill **49 → 54** (m1–m47 · x1–x7). **216 test offline hijau** (44 hermes + 172 tools), zero ResourceWarning.

### 🚩 Arsitektur
- **m32** naik peran jadi **orchestrator/router CTF**: triage → cek scope → dispatch ke sub-skill kategori → validasi flag → writeup.
- **m43 web · m44 pwn · m45 rev · m46 crypto · m47 forensics** — playbook per kategori (toolbox sandbox, decision tree, delegation table, safety rails), format SUPERAGENT.
- **`tools/ctf/`** — runtime full-auto: `coordinator/` poll CTFd → race N model per soal di Docker sandbox → consensus/HITL gate sebelum submit. Plus `scope_guard.py`, `flag_validator.py`, `rsa_attacks.py`, `templates/`, `sandbox/Dockerfile.sandbox`, `run.py`, `README.md`.

### 🔍 Review & perbaikan (atas paket asli — lihat `REVIEW.md`)
- **Consensus unreachable**: swarm cuma balikin flag pertama + cancel sisanya → `AUTO_SUBMIT_CONSENSUS>=2` gak pernah kepenuhi (semua diam-diam masuk antrian HITL). Fix: `race()` consensus-aware (kumpulin semua kandidat, Counter agreement).
- **flag_validator longgar**: `re.search` fallback nerima string ber-junk. Fix: `validate()` full-match only (extract pakai `extract_all`).
- **scope_guard**: DNS resolve sia-sia buat IP literal → reorder.
- **rsa_attacks butuh gmpy2** (gak ada di host, cuma di sandbox) → gmpy2 dibikin optional + fallback pure-Python (`_iroot` binary search, `_invert` via `pow(a,-1,m)`).
- **Path rewire**: `coordinator` importlib path + `SCOPE_PATH` default disesuaikan ke `tools/ctf/`.
- **Model placeholder & Dockerfile gaps**: model ID di-set ke nilai jelas + tool sandbox ditambah (radare2, john, exiftool, ropper, hashpumpy, jwt_tool) + dokumentasi tool berat per-event.

### 📚 Docs
- `AGENTS.md` (m43–m47 keyword rows) + `skills/m0.md` registry + `INDEX.md` (skills + tools/ctf) + `IDENTITY.md` + `README.md` (54 skills + whatsnew) + `panduan.md` di-update.
- `SKILLS.lock` diregenerasi & verified.

---

## v4.2 (update 2026-06-12) — GROWTH & PROTECTION EXTENSION (m33–m42)

Update aditif **dalam v4.2** — versi TIDAK naik. Nambah **10 skill opsional** (m33–m42) + **10 tool baru** + **63 test baru**. Semua offline, deterministik, zero-dep; on-chain read didelegasi ke m10/hermes, fund movement tetap via Spend Governor, time logic via `now` injected (TIME.md). Identitas inti & safety machinery utuh. **192 test offline hijau** (44 hermes + 148 tools), zero ResourceWarning.

### 🛠️ Skill baru (load on-trigger)
- **m33 — Pre-TGE Alpha Radar**: skor proyek 0-100 + tier (cold/watch/warm/hot) dari sinyal pre-token (points program, testnet, VC, momentum); token udah ada → cap 30.
- **m34 — Farming Portfolio & ROI Optimizer**: EV/ROI per posisi (gas vs estimasi×confidence), aksi keep/trim/drop, deteksi wallet idle.
- **m35 — Auto Guide Studio**: 1 airdrop → panduan ID lengkap + varian TG/X + referral embed + daftar screenshot jobs (delegasi browser).
- **m36 — Tokenomics & Unlock Pressure Engine**: kalender unlock + pressure ratio (nilai unlock vs volume harian) → sinyal exit makro.
- **m37 — Anti-Scam Sentinel**: typosquat (levenshtein) + sinyal halaman (seed phrase/drainer/SSL baru) → risiko 0-100 + draft warning. Read-only defensif.
- **m38 — Contract-Change & Claim-Address Watcher**: diff snapshot kontrak (proxy/claim addr/admin/code hash/fungsi sensitif) → alert + `safe_to_claim` gate.
- **m39 — Community Intelligence**: pesan komunitas → topik trending, pertanyaan berulang, sentimen, FUD alert, ide konten.
- **m40 — Omni-Repurpose Engine**: 1 sumber → X thread (≤280) / TG / IG carousel / TikTok / YouTube, lokal ID.
- **m41 — Video Script-to-Screen Pipeline**: brief → script ber-timing (hook 15%/body/CTA 15%) + storyboard + voiceover + SRT.
- **m42 — Hook A/B Lab**: generate varian hook + skor stop-scroll deterministik 0-100 + ranking.

### 🔧 Tool baru
`alpha_radar.py` · `farm_roi.py` · `guide_studio.py` · `unlock_engine.py` · `scam_sentinel.py` · `contract_watch.py` · `community_intel.py` · `repurpose.py` · `video_pipeline.py` · `hook_lab.py` — masing-masing dengan test suite sendiri di `tools/tests/`.

### 📚 Docs
- `AGENTS.md` router + `skills/m0.md` registry + `INDEX.md` + `IDENTITY.md` (daftar modul opsional) + `README.md` (49 skills) + `panduan.md` di-update.
- `SKILLS.lock` diregenerasi & verified.

---

## v4.2 — WHITEHAT & AIRDROP INTELLIGENCE (2026-06-09)

Rilis aditif besar. Nambah **2 skill** (m31, m32) + **10 tool baru** + extend `eval.py`, plus **6 perbaikan** dari audit internal. Identitas inti crypto + dev (IRONCLAW) utuh — skill baru load on-trigger. Safety machinery (governor, SKILLS.lock, integrity boot) tetap, malah diperkuat. **129 test offline hijau** (44 hermes + 85 tools), zero ResourceWarning.

### 🛠️ Skill baru
- **m31 — Airdrop Intelligence**: 4 tahap ber-angka — eligibility scorer, sybil self-audit, claim-window calendar, exit planner. Semua offline/deterministik; data on-chain didelegasi ke m10/hermes; time selalu di-inject (TIME.md).
- **m32 — CTF / Whitehat Toolkit**: triage kategori, multi-decode, classic crypto (caesar/xor/vigenere), hash-id. **Legal & in-scope only** (R9 gate buat target asing). Stdlib-only & pasif.

### 🔧 Tool baru
- `tools/eligibility.py` — `WalletStats` → `score_wallet()` 0-100 + gaps + flags, rubric override-able per-project.
- `tools/sybil_audit.py` — `audit()` korelasi antar-wallet sendiri (funding/timing/gas/tx/overlap) + saran de-correlation.
- `tools/claim_watcher.py` — `ClaimWatcher` H-48/H-2/H-0 fire-once + `upcoming()` kalender; `now` wajib di-inject.
- `tools/exit_planner.py` — `build_plan()` exit ladder (conservative/balanced/degen), nyesuaiin likuiditas/vesting, eksekusi via governor.
- `tools/rugcheck.py` — `check(SignalSet)` → SAFE/CAUTION/DANGER + critical/warnings/unknowns (m11 + H4).
- `tools/ctf.py` — find_flags/triage/try_decode/caesar/xor/identify_hash.
- `tools/cost_ledger.py` — ledger token+on-chain+API terpusat, summary per-provider/chain (observability — fix #6).
- `tools/router_log.py` — log keputusan router + deteksi tie → tuner bobot keyword (fix #4 + observability).
- `tools/secret_tripwire.py` — redaksi secret di output layer (priv key/mnemonic/API key/JWT/PEM), `guard(strict=)` (leak tripwire).
- `tools/dryrun.py` — dry-run global (contextvars): engine `plan()` bukan broadcast; `with dry_run()`.
- `tools/eval.py` — **+`RegressionSuite`**: golden-set regression lintas rilis (record_baseline → run → diff).

### 🐛 Fixes (audit internal)
1. **README stale** — judul/badge → v4.2, hapus "Successor to v2", path `superagent-v3/` → `superagent/`.
2. **Test resource leaks / ResourceWarning** — `governor.py`, `airdrop_runner.RunState`, `CostLedger`, `RouterLog` dapat `close()` + context manager; test `test_api_harvester`, `test_governor`, `test_airdrop_runner` nutup koneksi & file. Full suite kini bersih di `-W error::ResourceWarning`.
3. **Skill count inkonsisten** — diseragamkan ke **39 skills** (m1–m32 · x1–x7) di README/INDEX.
4. **Router keyword collision** — `router_log.py` nge-log tie & ngasih `tune_report()` (data buat retune bobot, bukan nebak).
5. **Governor per-VPS only** — `SpendGovernor` terima `conn=` injectable + docstring multi-VPS (cap global lintas mesin via backend share-able).
6. **No central cost observability** — `cost_ledger.py` jadi sumber tunggal biaya token+on-chain+API.

### ✅ Testing
- Tool baru semua punya test offline (stdlib unittest, zero-dep): cost_ledger, router_log, secret_tripwire, dryrun, eligibility, sybil_audit, claim_watcher, exit_planner, rugcheck, ctf, eval-regression.
- `SKILLS.lock` di-regenerate (integrity boot otomatis mencakup file `.md`/`.py` baru).
- Registry/router/docs terupdate: `m0.md`, `AGENTS.md` (keyword weights m31/m32), `panduan.md` (TOC + section v4.2), `INDEX.md`, `IDENTITY.md`, README.

---

## v4.1.2 — CLIENT REVENUE ENGINE / m30 (2026-06-05)

Rilis aditif kecil. Nambah **1 skill orkestrator** + **2 tool** + test. Identitas inti crypto + dev tetap; skill baru load on-trigger, gak ganggu karakter utama. Safety machinery (governor, SKILLS.lock, integrity boot) utuh.

### 🛠️ Skill baru — m30: Client Revenue Engine (bulk gig, API-first)
- **Doctrine "browser = last resort"**: garapan bulk dikerjain lewat kode & API; headless browser cuma kalau data render-only & gak ada endpoint yang bisa direplikasi.
- **Orkestrator, bukan duplikat** — m30 nyetir & delegasi:
  - Pattern A (harvest/scrape API) → parse_curl + paginate + extract + BulkRunner, delegasi m6/m5, browser_engine (H8) last resort.
  - Pattern B (mass akun/airdrop/on-chain) → BulkRunner + Checkpoint, delegasi m10 + hermes, **wajib lewat Spend Governor**.
  - Pattern C (integrasi API & otomasi job) → RequestSpec + retry + provider cascade, delegasi m6/m16/m4.
- Terdaftar di `INDEX.md`, `m0.md` registry, dan router `AGENTS.md` (keyword weights). High-weight m30 spesifik (garapan, harvest, scrape API, anti-browser, parse curl) supaya gak nyolong "bulk" generik dari m12.

### 🔧 Tool baru
- `tools/revenue_engine.py` — `BulkRunner` (concurrency + retry/backoff + **checkpoint-resume** + dedupe), `TokenBucket` (rate limit, clock injectable), `Checkpoint` (idempotent, thread-safe).
- `tools/api_harvester.py` — `parse_curl()` (DevTools → RequestSpec), `paginate_offset`/`paginate_cursor`, `extract()` (JSON path + wildcard), `to_jsonl`/`to_csv`, `send()` (httpx, lazy import).

### ✅ Testing
- Test offline `tools/tests/` (stdlib unittest, zero-dep): rate-limit, backoff+jitter bounds, checkpoint resume, dedupe, BulkRunner (sukses/skip/retry/fail), pagination, JSON-path extract, cURL parse, JSONL/CSV roundtrip.
- `SKILLS.lock` di-regenerate (integrity boot mencakup file baru).

---

## v4.1.1 — CODE QUALITY & TESTS (2026-06-05)

Maintenance/hardening patch. **No behaviour or capability changes** to the agent — identitas inti crypto + dev (IRONCLAW) utuh. Fokus: keandalan script Hermes crypto + test suite offline.

### 🐛 Bug fixes (Hermes crypto scripts)
- **Mutable-default dataclass bugs** diperbaiki — bisa bikin state bocor antar-instance:
  - `swap_engine.py` → `SwapResult.warnings` sekarang `field(default_factory=list)`
  - `nft_engine.py` → `NFTResult.tx_hashes` sekarang `field(default_factory=list)`
  - `airdrop_runner.py` → `TaskSpec.params` sekarang `field(default_factory=dict)`
- **`bridge_engine.py` relative-import fragile** — `from .swap_engine import ...` gagal kalau script dipakai flat/standalone (persis cara yang README anjurkan). Sekarang ada fallback ke import top-level, jadi jalan di dua mode (package & template).

### ✅ Testing (baru)
- Test suite **offline, zero-dependency** di `skills/hermes/tests/` (stdlib `unittest`; jalan juga di `pytest`). 44 test, semua hijau.
- `_bootstrap.py` nge-stub paket berat (web3/eth_account/httpx/solana/…) lewat import hook → bisa nguji logika murni tanpa install apa-apa & tanpa jaringan.
- Coverage: governor (allow/block/halt, caps, rate-limit trip, kill-switch), SIWE/signature helpers, mempool filter, RPC failover, jitter & run-state dedupe, explorer URL, default-list safety.
- Tooling dev: `pyproject.toml` (config pytest + ruff), `requirements-dev.txt`, `tests/run_tests.sh`, `tests/README.md`.

---

## v4.1 — CAPABILITY EXPANSION (2026-06-04)

Rilis aditif. Identitas inti **tetap crypto + dev** (IRONCLAW); semua yang baru = **modul opsional** yang load on-trigger dan gak ganggu karakter utama. Safety machinery v4.0 (Spend Governor, FROZEN_PATHS, SKILLS.lock, reflection gate) **utuh & diperluas**. 7 skill + 6 tool baru.

### 🧠 Self-improvement & eval (extend x-cluster)
- **x5 — Agentic Eval & Self-Critique**: eval terstruktur (Case/assert), **variance testing** (jalanin task N× → ukur konsistensi; <0.95 = jangan otomasi), self-critique adversarial sebelum output berisiko. → `skills/x5.md`, `tools/eval.py`
- **x6 — Systematic Debugging**: 4-fase RCA → Pattern → Hypothesis → Fix + **auto-debug loop** (rank hipotesis by likelihood×murah-diuji, uji, bantah, ulang). Untuk bug yang gak ada di pustaka x3. → `skills/x6.md`
- **Instinct extraction** (x4): lesson berulang-&-kebukti dipadatkan jadi reflex; dikawal eval (variance jelek → gak boleh jadi reflex). → `skills/x4.md`

### 🎨 Creative & media (m18)
- ComfyUI (API/headless, graph patch), **Manim** animasi math, **Excalidraw** diagram programmatic, ASCII/retro video (chafa+ffmpeg), web design systems (Stripe/Linear/Vercel token), Felo-style content→deck, **aesthetic judgment** checklist. → `skills/m18.md`, `tools/scene_prep.py`

### 🤖 Desktop & physical (m19)
- **macOS native control — background-first, NO cursor steal** (AppleScript/Accessibility, gak ngerebut pointer/fokus operator). NVIDIA **Isaac Sim/Omniverse** (headless), **scene preparation** (USD assembly + domain randomization), mobility (Isaac Lab/ROS2; real-robot = R9 gate). → `skills/m19.md`, `tools/desktop_control.py`

### ✍️ Humanizer & brand voice (m20)
- AI-tell detector (heuristik keyless) + rewrite deterministik + brand voice adaptation. Jujur soal batas (bukan alat ngecoh detektor akademik). → `skills/m20.md`, `tools/humanizer.py`

### 🛡 Enterprise & defensive (m21)
- **Azure/KQL** troubleshooting (Log Analytics/Sentinel, read-only investigasi), **Mini-HIDS** auto-firewall dari log (allowlist + TTL + dry-run + alert; R9 gate aktivasi). Defensif murni. → `skills/m21.md`, `tools/hids.py`

### 🧭 Soft & human-level (x7)
- **Problem shaping** (tujuan kabur → subtask presisi), **brainstorming + sign-off** workflow, **decision support dengan ketidakpastian** (known/assumed/unknown + confidence + one-way vs two-way door), context design. Sengaja memperlambat HANYA saat kabur/taruhan tinggi. → `skills/x7.md`

### 🧩 Orchestration
- **Skill marketplace (skills.sh)** — `tools/skill_market.py`: unduh ke **quarantine**, WAJIB audit (m11), operator pindah + re-lock. Tidak pernah auto-install+auto-activate (friksi = fitur).
- Multi-agent orchestration & role specialization sudah ada di v4.0 (`swarm.py`/m17) — tetap.

### 🔒 Safety
- `FROZEN_PATHS` diperluas: `hids.py`, `desktop_control.py`, `skill_market.py` (surface OS/firewall/desktop/marketplace) gak bisa diedit loop self-improve.
- Aksi baru yang nyentuh OS/desktop/robot fisik/firewall → **R9 gate** (terpisah dari governor dana).
- `SKILLS.lock` diregenerasi (version 4.1, file_count baru). Semua tool baru import-clean (Python 3.9+, `from __future__ import annotations`).

### Expansion wave 2 — meta, scientific, product & enterprise

Penambahan lanjutan (tetap v4.1, tetap modul opsional crypto-first). 5 skill + 3 tool + 1 doc meta.

- **m22 — Scientific & Deep Research**: dispatcher riset AI-Q (report bersitasi), scientific tool workflows (ToolUniverse-style), hypothesis generation & experimental design. Privasi: query ke server eksternal → sanitize. → `skills/m22.md`, `tools/research_q.py`
- **m23 — Executive Function & Neurodivergent**: task breakdown anti-overwhelm (ADHD-style), context-switch + breadcrumb resume (via memory_engine), prioritization saat overwhelmed. Grounded di executive-function, bukan motivational fluff. → `skills/m23.md`
- **m24 — MCP-Builder & Prompt Engineering**: scaffold MCP server (Python FastMCP / TS sdk) dgn best practices, prompt auditor (deteksi+fix masalah prompt, eval-driven). → `skills/m24.md`, `tools/mcp_builder.py`
- **m25 — Compliance, CI/CD & Code Migration**: regulatory review (advisory, bukan legal advice), brand-guidelines enforcement, CI/CD pipeline, code-migrator antar bahasa/framework (test-first). → `skills/m25.md`
- **m26 — Product & Spec Workflows**: Grill-Me (idea kabur→tajam), To-PRD, To-Issues, TDD superpower, internal-comms. → `skills/m26.md`, `tools/prd.py`
- **Extend**: x5 + `eval.py` → **LLM-as-judge** production-grade (rubrik + panel + judge variance-check); m19 → **Cosmos Physical AI** + **meta-actions** (STOP > deselerasi > perintah, refleks keselamatan fisik); m18 → canvas design & visual art (Pillow/SVG); x7 → handoff Grill-Me ke m26; x4 → instinct extraction (wave 1).
- **`STANDARD.md`** (baru): membakukan emerging meta trends yang **sudah** jadi sifat sistem — progressive disclosure, open SKILL.md format, cross-platform (Claude/Cursor/Codex/Gemini), marketplace. Bukan fitur baru, dokumentasi prinsip.
- **`panduan.md`**: section baru "Skill non-crypto (v4.1)" + cheat-sheet rows untuk semua skill v4.1.

### Expansion wave 3 — content, social media & marketing

Domain marketing/konten sosial (proposal kategori 18–24) + pendalaman sains & embodied AI (16–17). 3 skill + 1 tool + extends. Tetap v4.1, tetap opsional crypto-first.

- **m27 — Content Strategy & Social Media**: content pillars/audience/positioning, content calendar generator, platform-specific adapter (X/LinkedIn/IG/TikTok), viral hook & scroll-stopper, caption+hashtag optimizer, thread/carousel/reels writer. → `skills/m27.md`, `tools/content.py`
- **m28 — Copywriting & Writing Mastery**: frameworks (AIDA/PAS/BAB/4P/CHEF/70-20-10), SEO writer, storytelling/narrative, multilingual & localization (termasuk RTL). → `skills/m28.md`
- **m29 — Content Research, Analytics & Pipeline**: trend/competitor research, audience insight & social listening, performance analyzer, A/B variant, best-time-to-post, engagement handler, **full content pipeline** (research→draft→visual→schedule→analyze) + cross-platform publisher + human-in-the-loop + repurposing. → `skills/m29.md`, `tools/content.py`
- **Extend m22** — scientific domain library dispatch (genomics/docking/MD/geospatial/time-series via library tervalidasi, bukan reimplementasi), Hugging Science (HF Hub discovery), multi-step pipeline literature→paper drafting, K-Dense BYOK (local co-scientist).
- **Extend m19** — **VLA** (Vision-Language-Action: perceive→reason→act), multimodal reasoning (text+vision+audio+action), scene understanding/object manipulation — semua di bawah meta-action safety.
- **Extend m18** — content repurposing, infographic/carousel design, image-prompt engineer (Midjourney/Flux/Canva).
- **`content.py`** — scaffolder deterministik (kalender, adapt, thread/carousel/reels, repurpose); analitik/best-time bertanda 'estimate' kalau tanpa data real (jujur, gak ngarang angka).
- **`panduan.md`** — section "Konten & social media (v4.1)" + cheat-sheet rows m27–m29.
- **Kejujuran desain**: "141+ scientific tools" = dispatch ke library matang + verifikasi, BUKAN klaim built-in palsu. Analitik konten butuh data real platform; tanpa itu heuristik bertanda estimasi.

### Ringkasan angka
- 37 skill (m0–m29 + x1–x7), 28 tool, 15 reference Hermes (tak berubah dari v4.0), +`STANDARD.md`.
- Semua skill baru = modul opsional, on-trigger; always-on token budget tetap ~3.5k (progressive disclosure).

---

## v4.0 — OPENCLAW EDITION (2026-06-03)

Major release. Dari baseline v3.1, v4.0 nambahin lapisan keamanan/governance penuh, kemampuan belajar sendiri, suite asisten harian, tooling smart-contract lengkap (baca/tulis/deploy), manajemen LLM dinamis, "power pack" orkestrasi, dan skill software-engineering umum. Semua aksi yang nyentuh dana lewat **Spend Governor**; file kritis dijaga **FROZEN_PATHS**.

### 🛡 Keamanan & governance
- **Spend Governor** — circuit breaker di tiap tx: cap per-tx / harian / sesi (USD), batas slippage, auto-HALT pas gas spike / rate-limit, simulation gate, kill-switch manual. `auto_confirm` matiin prompt, **bukan** governor. → `skills/hermes/references/governor.md`, `scripts/governor.py`
- **MEV protection** — swap & snipe lewat private relay (Flashbots Protect / MEV Blocker), bukan mempool publik; fallback-with-warning yang jujur. → `scripts/mev.py`
- **Skill integrity verify** — manifest SHA-256 (+ opsional Ed25519) dicek saat boot; file skill yang berubah/baru/hilang nahan operasi on-chain sampai diaudit. → `tools/skill_integrity.py`, `SKILLS.lock`
- **FROZEN_PATHS** — file kritis (SOUL, AGENTS, governor, integrity, reflection, vault, watchdog, model_registry, planner, swarm, automation, skill_forge) **gak bisa diedit** oleh loop self-improve. Di-enforce di kode (`guard_write`).

### 🧠 Self-improvement
- **Compounding memory** — recall lokal keyless (SQLite); memori berguna di-reinforce & makin sering muncul. → `tools/memory_engine.py`
- **Reflection loop (x4)** — belajar dari masalah berulang, auto-fix isu ops yang reversible (allowlist only), tulis *proposal* upgrade buat di-review operator; ada audit log. → `skills/x4.md`, `tools/reflection.py`

### 📅 Asisten harian (m14, m15)
- **Daily briefing** + **alert engine** kondisional (price/gas/wallet/claim, DexScreener keyless, cooldown-dedup). → `tools/briefing.py`, `tools/alerts.py`
- **Watchdog** self-healing, **vault** snippet/alamat + macro, input **voice** (Whisper lokal) + **screenshot** (vision), **triage** inbox. → `tools/watchdog.py`, `tools/vault.py`, `tools/multimodal.py`, `tools/triage.py`

### 🔗 Tooling smart-contract
- **Universal contract reader** — multi-chain, ABI auto-fetch (Sourcify/Blockscout, keyless), call read function apa pun, deteksi ERC-20/721/1155, resolve proxy EIP-1967. Read-only. → `references/contract_read.md`, `scripts/contract_reader.py`
- **Universal contract writer** — kirim tx ke fungsi apa pun, gated penuh (sim → screen → governor → konfirmasi → record). → `references/contract_write.md`, `scripts/contract_writer.py`
- **Crypto developer** — compile/test (Foundry), deploy (governor-gated), verify (Sourcify keyless), CREATE2 deterministic multi-chain. → `references/deploy.md`, `scripts/deploy_engine.py`

### 🧩 Manajemen LLM (m7 extended)
- **Dynamic model registry** — `add model` satu perintah (name/api_key/base_url/model/kind/priority); OpenAI-compatible + Anthropic; key dienkripsi (scrypt+Fernet), redacted, masuk cascade R7 dengan fallback otomatis. → `tools/model_registry.py`

### ⚙️ Power Pack (m17)
- **NL workflow planner** (tujuan → plan multi-step gated), **multi-agent swarm** (lane specialist paralel + pemisahan key), **skill forge** (draft skill baru → proposal), **automation engine** (WHEN/THEN), **backtester**, **live dashboard**, **voice conversation mode** (STT→LLM→TTS), **explainability**. → `skills/m17.md` + `tools/{planner,swarm,skill_forge,automation,backtest,dashboard,voice,explain}.py`

### 💻 Software engineering (m16)
- **Skill coding umum** — backend API (FastAPI/Express/Go/Django), database (skema/migration/ORM), testing default (pytest/vitest/go test), scaffolding (struktur + Dockerfile + CI), multi-bahasa (Python/TS/Go/Rust), refactoring & code review, CLI/library, git workflow. Komplemen m9 (frontend) + m2 (deploy) + x3 (debug) = full-stack. → `skills/m16.md`

### 🛠 Tooling & docs
- **`.env.example`** — semua env var (50+) dikelompokin, ditandain wajib/opsional/gratis/berbayar.
- **`DEPLOY.md`** — panduan deploy VPS yang akurat (menggantikan quick-start lama).

### Ringkasan angka
- 22 skill (m0–m17 + x1–x4), ~30+ script Python, 15 reference Hermes.
- Lapisan baru: governance, self-improve, daily assistant, contract read/write/deploy, model registry, power pack, software engineering.

---

## v3.1 — baseline (2026-05-25)

Rilis dasar yang jadi titik tolak v4.0.

### Headline changes
- 🆕 **3 new skills**: m10 Web3, m11 Security, m12 Batch
- 🆕 **NFT minter skill**: m13 (universal mint with auto-gas, OpenSea/Manifold/Zora)
- 🆕 **Hermes Crypto Agent absorbed**: full deep-crypto layer at `skills/hermes/` (10 refs + 8 Python templates)
- ⏰ **TIME.md** — 5-layer time-awareness architecture (system inject → tool → cache → infer → disclose). No more time-blind hallucination on deadlines/cron/vesting/claim windows.
- ⚡ **Smarter router**: priority-weighted keywords, multi-skill orchestration, H1-H7 hermes dispatch
- 🛠 **m4 Telegram** now production-grade (anti-duplicate, webhook mode, multi-bot)
- 🤖 **m7 AI** rewritten: streaming, function calling, provider fallback chain, cost tracking
- 🖥 **m2 VPS** expanded: systemd, tmux, nginx security headers, backup automation
- 🔐 **Tighter SOUL**: 2 hard stops only, permissive on grey-area + operational rails for crypto ops
- 🇮🇩 **m3 voice**: airdrop template now matches operator's exact format

### New files
| File | Why |
|---|---|
| `skills/m10.md` | Web3 ops: RPC fallback, BIP39 wallet gen, NonceManager, simulate→send→wait, eligibility O(1) checker, mass farming with p-limit, multicall, Solana basics. |
| `skills/m11.md` | Security audits: skill-file injection checklist, Solidity red flags, suspicious package signals, secret leak detection, OpenClaw-specific safety. |
| `skills/m12.md` | Batch patterns: p-limit, asyncio.gather, token bucket, progress tracking, resume-from-failure checkpoint. |
| `skills/m13.md` | **Universal NFT minter**: parse OpenSea/Manifold/Zora URL atau raw address, auto-detect mint fn + price, auto-gas, simulate→send→wait. Combo m12 buat mass mint. |
| `skills/hermes/*` | **Hermes Crypto Agent** — deep-crypto skill (SKILL.md + references + Python templates). H1-H7 dispatch (swap/bridge/defi/sniping/mempool/NFT/SIWE). EVM + Solana + Sui + Aptos + TON. |
| `TIME.md` | **5-layer time-awareness**. Solves LLM time-blindness. Strict mode buat crypto cron/deadline/vesting/claim. Contributor: 👁⃤Fiⱥnͥ.ⱥsͣsͫⱥn 𓂀 ([@fianassan25](https://t.me/fianassan25)). |
| `CONTRIBUTORS.md` | Credits — CVC Owner + Member contributions. |
| `panduan.md` | Operator usage guide (12 sections + cheat sheet) dengan contoh Hermes nyata. |
| `CHANGELOG.md` | This file. |
| `INDEX.md` | One-line index of all files. |

### Upgraded files (ringkas)
- **`AGENTS.md`** — rules R1-R10, provider cascade (R7), multi-skill orchestration (R8), token economy (R9), escape hatch (R10), weighted keyword table EN+ID, crypto trigger cluster.
- **`IDENTITY.md`** — 3 response speed tiers, Web3 operator voice, anti motivational filler.
- **`SOUL.md`** — 2 hard stops (CSAM, mass-casualty weapons), single risk gate, doktrin permisif buat crypto ops.
- **`HEARTBEAT.md`** — continuity triggers, token discipline (warn 60% / compact 80%), resume protocol.
- **`TOOLS.md`** — agent-side vs operator-side, OpenClaw streaming config bug (`streaming: false` boolean).
- **`USER.md`** — template fill-in + trigger phrases + domain focus.
- **`MEMORY.md`** — compact format (1 baris/entry), 30-day window, monthly compaction.
- **`skills/m0–m9, x1–x3`** — registry diperluas, reflection loop, escape hatch, crypto monetization (m1), VPS bootstrap (m2), airdrop template + CT voice (m3), Telegram rewrite anti-duplicate (m4), O(1) lookup (m5), circuit breaker (m6), AI rewrite + fallback (m7), PDF hyperlinks (m8), Web3 UI (m9), audits (x1), pre-mortem (x2), error library (x3).

### Known good combos (multi-skill load)
- "bikin bot Telegram + bayar TON" → m4 + m6 + m10
- "mass mint 300 wallet" → m13 + m12 + m10
- "swap 1000 USDC ke ETH di base" → H1 (hermes/swap.md) + m10
- "farming airdrop layerzero 50 wallet" → H2 + H1 + m12
- "buat landing page web3" → m9 + m10
