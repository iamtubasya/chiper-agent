# Free 24/7 (Always-On) Hosting — Verified Late-2026 Landscape

Purpose: answer "where do I host a persistent Chiper/bot daemon for free, always-on?"
A persistent agent daemon needs: persistent disk, outbound net (Telegram polling + LLM API),
long-lived background process (NOT serverless that scales-to-zero), and ideally root to
install tool binaries (nmap/sqlmap/agent-browser).

## Bottom line

**Oracle Cloud Always Free is the ONLY genuinely free, contractually always-on option.**
Everything else free-tier either sleeps on inactivity, is trial-only, or was discontinued.
Verified against Oracle's official docs (curl'd live, not stale blogs).

## Oracle Cloud — Always Free (verified specs)

From docs.oracle.com "Always Free Resources" (fetched live):

> "All Oracle Cloud Infrastructure accounts (whether free or paid) have a set of resources
> that are free of charge in the home region of the tenancy, **for the life of the account**."

- **ARM Ampere A1:** 1,500 OCPU-hours + 9,000 GB-hours/month = equivalent to **2 OCPU + 12 GB RAM** running 24/7.
  ⚠️ CORRECTION to common lore: the widely cited "4 OCPU / 24 GB" is STALE — current docs say 2 OCPU / 12 GB.
- **AMD micro:** 2× `VM.Standard.E2.1.Micro` (1 GB RAM each).
- **Block storage:** ~200 GB total (boot volumes ~47 GB × 2); ~10 TB/mo egress.
- Root = YES, persistent disk = YES, no time limit (not a 30-day trial).

### Oracle gotchas (the real risks)
- **ARM capacity exhausted** in popular regions → "out of capacity" on provision. Retry, split, or use AMD micro.
- **Idle reclamation:** very idle Always Free compute (low CPU/net/mem over ~7 days) can be reclaimed.
  A Telegram bot that polls + calls LLMs shows enough activity; add a light cron ping if worried.
- **Card verification** required at signup; upgrade to PAYG keeps Always Free resources at $0 and unlocks capacity.
- Repeated failed signups / region changes can nuke the account.

## Who is NOT actually free 24/7 (2026 status)

| Provider | Status |
|---|---|
| **Render** free | ❌ Sleeps ~15 min idle; no free persistent disk; no free background worker |
| **Railway** | ❌ Free tier killed 2023 → one-time trial credit (~$5) |
| **Fly.io** | ❌ Legacy free allowance removed for new orgs (~2024) |
| **Replit** | ❌ "Always On" is paid; free Repls sleep |
| **Glitch** | ❌ Project hosting shut down (~2025) |
| **Heroku** | ❌ Free tier ended Nov 2022 |
| **Google Cloud Run** | ⚠️ "always-on CPU" (`--min-instances=1 --no-cpu-throttling`) is **billed**, NOT free. The free tier is a consumption allowance, not an "always-on instance" allowance. |
| **GitHub Actions** | ❌ Not for hosting (6h job cap, ToS ban) |
| **Koyeb** | ⚠️ Historically one rare PaaS allowing a non-sleeping free "nano" (256 MB) — verify current terms |

## HuggingFace deployment

- **HF Spaces (Docker SDK)** *can* run an image, but: single exposed port only, free tier sleeps ~48h,
  non-root runtime (no system-package installs). **Not fit for a 24/7 bot daemon.**
- Best HF use: **as the LLM provider** — host an open model, point the agent at its
  OpenAI-compatible endpoint (`provider: custom:hf`, `base_url: https://<user>.hf.space/v1`).
  Agent + tools + bot stay on the VPS; only the "brain" lives on HF.

## Verification discipline

Free-tier offerings change fast and old numbers drift (Oracle ARM 4/24→2/12, Glitch died, Railway/Fly.io killed free).
ALWAYS curl the provider's official pricing/docs page before answering — never trust training memory or year-old blogs.
