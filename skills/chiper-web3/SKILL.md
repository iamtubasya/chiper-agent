---
name: chiper-web3
description: "Chiper-Web3 suite — Autonomous Web3, Crypto Ops, DeFi, Airdrop Automation, MEV/Arbitrage, and Whitehat CTF Solver. Includes Hermes execution engine and 56 operational skills in dedicated chiper-* directories."
---

# Chiper-Web3: Web3, Crypto Ops, DeFi & CTF Whitehat Specialist

Suite terpadu untuk operasi Web3, multi-chain on-chain execution, otomatisasi airdrop multi-wallet, audit smart contract, dan penyelesaian CTF security challenge.

## Standar Struktur Direktori (`Chiper-Web3/chiper-<nameskill>/`)

Semua modul skill diorganisir menggunakan standar prefix **`chiper-*`** yang seragam dengan `chiper-cyber`:

### 1. Web3, Crypto & DeFi
- `chiper-web3-onchain-ops/` — Operasi transaksi on-chain, fallback RPC redundan, multi-wallet checks.
- `chiper-hermes-crypto-engine/` — Engine eksekusi H1-H10 (swap DEX, bridge cross-chain, DeFi, sniping, contract read/write).
- `chiper-nft-universal-minter/` — Universal NFT minter lintas marketplace (OpenSea, Manifold, Zora).
- `chiper-frontend-web3-ui/` — Interface Web3, React, Tailwind CSS, tombol wallet connect.

### 2. Airdrop Farming & Intelligence
- `chiper-airdrop-intelligence/` — Evaluasi kelayakan airdrop 0-100, anti-sybil audit, kalender claim, exit plan ladder.
- `chiper-pre-tge-alpha-radar/` — Deteksi dini kandidat airdrop pra-token, scoring sinyal potensi.
- `chiper-farming-portfolio-roi/` — Optimasi portofolio airdrop, evaluasi EV/ROI biaya gas vs reward.
- `chiper-auto-guide-studio/` — Generator tutorial dan panduan airdrop step-by-step.
- `chiper-tokenomics-unlock-pressure/` — Kalender vesting, analisis tekanan jual unlock token.
- `chiper-anti-scam-sentinel/` — Deteksi domain phishing airdrop & peringatan scam komunitas.
- `chiper-contract-change-watcher/` — Snapshot differ smart contract, proxy upgrade & claim address.
- `chiper-community-intelligence/` — Analisis sentimen komunitas, ekstraksi topik trending.

### 3. CTF & Whitehat Security
- `chiper-ctf-whitehat-toolkit/` — Triage koordinasi tantangan CTF & flag validator anti-halusinasi.
- `chiper-ctf-web-exploitation/` — Eksploitasi web (SQLi, SSTI, SSRF, IDOR, XXE, JWT).
- `chiper-ctf-binary-exploitation-pwn/` — Binary pwn (ret2win, ret2libc, format string, heap, ROP).
- `chiper-ctf-reverse-engineering/` — Reverse engineering (angr symbolic execution, Ghidra, radare2).
- `chiper-ctf-cryptography/` — Kriptografi CTF (serangan RSA offline, block ciphers, PRNG).
- `chiper-ctf-forensics-stego/` — Analisis forensik PCAP, memory dump, dan steganografi.
- `chiper-ctf-prompt-injection-redteam/` — LLM red-teaming & bypass guardrail model Gandalf.
- `chiper-security-audit-review/` — Audit keamanan skill, integrity check, scanner rahasia.

### 4. Otomasi, Bot & Growth
- `chiper-client-revenue-engine/` — Bulk gig harvesting, pagination extractor, otomatisasi job.
- `chiper-telegram-bots-automation/` — Orkestrasi bot Telegram, anti-duplicate, webhook.
- `chiper-monetization-value-gen/` — Packaging penawaran bernilai tinggi, funnel revenue.
- `chiper-api-integrations-webhooks/` — Integrasi REST API, webhook, Midtrans, WhatsApp Cloud.
- `chiper-batch-parallel-execution/` — Eksekusi paralel concurrent, worker queue.
- `chiper-content-copywriting-viral/` — Copywriting konversi tinggi, formula hook viral.
- `chiper-copywriting-mastery/` — Framework copywriting (AIDA, PAS, CHEF), SEO writing.
- `chiper-content-strategy-social/` — Kalender editorial media sosial, carousel, reels.
- `chiper-content-research-analytics/` — Riset tren kompetitor, social listening.
- `chiper-omni-repurpose-engine/` — Repurpose 1 ide ke X thread, IG carousel, TikTok, YouTube.
- `chiper-video-script-pipeline/` — Naskah video terstruktur, storyboard scene, SRT subtitle.
- `chiper-hook-ab-lab/` — Generator hook & prediksi skor stop-scroll.

### 5. Dev & Infra
- `chiper-vps-infrastructure-devops/` — Linux VPS, SSH, Nginx, Docker, systemd, PM2, tmux.
- `chiper-software-engineering-coding/` — Backend FastAPI/Node.js, database, pytest scaffolding.
- `chiper-ai-model-orchestration/` — Multi-provider AI cascade, fallback routing.
- `chiper-mcp-builder-prompt-engineering/` — FastMCP server scaffolding, audit prompt model.
- `chiper-compliance-cicd-migration/` — SOC2/GDPR compliance, CI/CD pipeline, migrasi kode.
- `chiper-product-spec-workflows/` — PRD, GitHub issues, Grill-Me session, TDD specs.
- `chiper-structured-data-analytics/` — Excel, CSV, lookup O(1), analisis dataset.
- `chiper-document-generator-render/` — Dokumen PDF, DOCX, XLSX, PPTX, ReportLab.
- `chiper-creative-media-generation/` — ComfyUI, Manim math animation, Excalidraw JSON.
- `chiper-desktop-robotics-control/` — Kontrol background macOS, Isaac Sim/Omniverse, USD.
- `chiper-humanizer-brand-voice/` — Deteksi & pembersihan AI-tell, rewriter natural.
- `chiper-enterprise-defensive-hids/` — Azure KQL analytics, Mini-HIDS auto-firewall.
- `chiper-scientific-deep-research/` — Riset mendalam, hipotesis eksperimen, bukti bersitasi.
- `chiper-executive-function-focus/` — Dekomposisi tugas mikro, mitigasi overwhelm fokus.
- `chiper-daily-briefing-alerts/` — Ringkasan harian terjadwal, alert harga token.
- `chiper-system-watchdog-vault/` — Watchdog proses, address vault terenkripsi, audio Whisper.
- `chiper-power-pack-automation-swarm/` — Swarm orchestrator, backtester, dashboard live.
- `chiper-skill-registry/` — Dynamic skill registry, self-reflection cycle.

### 6. Meta
- `chiper-meta-self-audit/`, `chiper-meta-deep-strategy/`, `chiper-meta-fault-diagnosis/`, `chiper-meta-self-improvement/`, `chiper-meta-agentic-eval/`, `chiper-meta-systematic-debug/`, `chiper-meta-problem-shaping/`

## Cara Memuat Skill
- Baca langsung file: `read_file("~/.chiper/skills/chiper-web3/chiper-<nama>/SKILL.md")`
- Atau via skill tool: `skill_view("chiper-<nama>")`
