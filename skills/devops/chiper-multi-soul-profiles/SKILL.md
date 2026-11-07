---
name: chiper-multi-soul-profiles
description: Architect and operate multi-soul and multi-profile Chiper Agent deployments — profile isolation via CHIPER_HOME, per-soul isolated memory, fresh-install provisioning, and safe concurrent profiles. Use when splitting/adding souls (personas), isolating memory per persona, or running multiple profiles/instances at once.
---

# Chiper Multi-Soul & Multi-Profile Architecture

Knowledge for building and operating the user's Chiper Agent fork (multi-soul + multi-profile).
Source of truth: read the actual code before answering architecture questions — do NOT hand-wave.

## Core model (two layers, don't conflate)

- **Profile** = one isolated install/instance, switched by the `CHIPER_HOME` env var.
  One profile holds its own `SOUL.md`, `memories/`, `skills/`, `plugins/`, `cron/`, `config.yaml`, sessions.
- **Soul** = a persona *inside* one profile. Default profile has 4: `Chiper-Cyber` (🛡️ red team/enterprise), `Chiper-Hunt` (🎯 bug bounty hunter), `Chiper-Dev` (💻 engineer), `Chiper-Web3` (⚡ web3/crypto).

## Profile boundary — `CHIPER_HOME`

- `chiper_constants.py` → `get_chiper_home()` is the single source of truth.
  Reads `CHIPER_HOME` env var, else falls back to platform default (`~/.chiper`).
- Profile layout: `~/.chiper/profiles/<name>/`. `active_profile` file marks a sticky non-default profile.
- Docker/custom deployments: `CHIPER_HOME` can point outside `~/.chiper` (e.g. `/opt/data`); `get_default_chiper_root()` resolves the profile root.
- Env leakage warning: if `CHIPER_HOME` is unset but `active_profile` is non-default, the process falls back to `~/.chiper` (wrong profile) and logs a loud one-shot `[CHIPER_HOME fallback]` warning.

## Soul & memory isolation

- Master soul templates live in `~/.chiper/souls/<soul_id>.md`; the active one is copied to `~/.chiper/SOUL.md`.
- **Per-soul long-term memory** = `~/.chiper/memories/souls/<soul_id>.md` (isolated, persists across soul switches).
- **`USER.md` is GLOBAL/shared** — one file for all souls (who the user is), never isolated.
- Switching handshake (`agent/soul_manager.py` → `sync_soul_memory_on_switch(from, to)`):
  1. save current active `MEMORY.md` back to the *from* soul file,
  2. copy the *to* soul file into active `MEMORY.md`.
- The `memory` tool mirrors every mutation to BOTH `MEMORY.md` and the active soul file in real time (`tools/memory_tool.py` `save_to_disk`), so nothing is lost on switch.
- **Fresh-install rule (user requirement):** every soul memory file must start EMPTY (tabula rasa); each soul builds its own memory dynamically. Installer calls `ensure_default_souls()` + `ensure_default_soul_memories()` + `switch_soul('chiper-cyber')`.
- Self-healing: `agent/prompt_builder.py` and `tools/memory_tool.py` regenerate `SOUL.md` / memory files if manually deleted (never crash/blank).

## Concurrent profiles — 7 isolation layers (not just 3)

Two profiles run in parallel WITHOUT conflict ONLY IF each process isolates all seven layers. Three are headline; four are easy to miss:

1. **`CHIPER_HOME`** — data root (memory, sessions, config, skills, cron). Set inline per command, never `export` (leaks to sibling shells).
2. **`HOME`** — OS home for external tools. Default `terminal.home_mode=auto` keeps the REAL home, so two profiles share `~/.gitconfig`, `~/.ssh/known_hosts`, `~/.npmrc`, `~/.aws/credentials` → tool-credential collisions. Force `terminal.home_mode=profile` (uses `{CHIPER_HOME}/home`) to isolate. See `get_subprocess_home()` / `apply_subprocess_home_env()` in `chiper_constants.py`.
3. **`CHIPER_REAL_HOME`** — pointer back to the real OS home so subprocess tools don't get stranded in profile home.
4. **`TMPDIR`** — per-profile temp dir; shared `/tmp` lets same-named temp files collide.
5. **Service ports** — dashboard (9119) + API (8642) must differ per profile, else `Address already in use`.
6. **Process identity** — systemd unit name + pidfile/socket paths must differ, else lock collision.
7. **Bot token** — Telegram bans two getUpdates consumers on one token → `Conflict: terminated by other getUpdates`.

Shared-file hazard: `~/.chiper/active_profile` (sticky non-default-profile pointer) lives at the ROOT, NOT inside a profile dir — two processes writing it race.

Recommended launcher pattern (7-env):
```bash
CHIPER_HOME=~/.chiper/profiles/kerja HOME=~/.chiper/profiles/kerja/home \
  CHIPER_REAL_HOME=$HOME TMPDIR=~/.chiper/profiles/kerja/tmp \
  chiper gateway start --port 9120 --api-port 8643 --unit chiper-kerja
CHIPER_HOME=~/.chiper HOME=~/.chiper/home CHIPER_REAL_HOME=$HOME \
  TMPDIR=~/.chiper/tmp chiper gateway start --port 9119 --api-port 8642 --unit chiper-default
```

## "Completely conflict-free" = OS-level boundary, not env vars

The 7-env approach is ~99%. The only *provable* 100% isolation is a kernel boundary: one Linux user per profile, or one Docker/Podman container per profile (Chiper detects containers via `is_container()`). Containers auto-isolate 6 of 7 layers via namespaces (filesystem, HOME, TMPDIR, network, PID); only the bot token remains external. Internal ports can be identical across containers (separate network namespaces) — only host port mapping differs. Docker layer-sharing means the 2nd..Nth container adds only ~50 MB disk (shared image layers), not a full copy — RAM (~400–700 MB idle per container) is the real cost, not disk. Tool binaries (nmap/sqlmap/agent-browser) should be baked into the image, not bind-mounted, to avoid missing `.so` deps.

## Key files

- `chiper_constants.py` — `get_chiper_home()`, profile root, subprocess HOME policy.
- `agent/soul_manager.py` — soul registry, `switch_soul`, `sync_soul_memory_on_switch`, `ensure_default_souls`, `ensure_default_soul_memories`.
- `tools/memory_tool.py` — memory persistence + real-time soul-file mirroring.
- `agent/prompt_builder.py` — self-healing soul regeneration.

## Pitfalls

- Don't answer architecture questions from memory of the model — read the source; the mechanism has sharp edge cases (env leakage, port/token collisions) that only the code shows.
- Never conflate "profile" and "soul" when explaining; users get confused by the two-layer isolation.
- For concurrent profiles, always set `CHIPER_HOME` inline per command (not `export`) so it can't leak to sibling processes.
- Don't claim two profiles are "completely" isolated while only `CHIPER_HOME` + port + token are separated — `HOME`/`TMPDIR`/unit/pidfile/`active_profile` remain shared (see the 7-layer section).
- When asked about deploying elsewhere (HF Spaces, free PaaS), separate "agent + tool + bot daemon" from "LLM brain" — the daemon needs always-on + persistent disk + root for tool installs, which most free serverless tiers cannot provide. See `references/free-24x7-hosting-options.md`.

## Reference files

- `references/free-24x7-hosting-options.md` — verified 2026 landscape of free 24/7 (always-on) hosting for a persistent Chiper/bot daemon, plus why HF Spaces and serverless free tiers don't fit.
