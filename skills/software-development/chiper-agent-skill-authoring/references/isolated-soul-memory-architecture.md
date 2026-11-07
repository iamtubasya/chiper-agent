# Isolated Soul Memory Architecture

## Context & The Problem
In multi-persona AI agent systems (e.g. Chiper Agent switching between `Chiper-Cyber`, `Chiper-Dev`, and `Chiper-Web3`), `SOUL.md` successfully changes the agent's identity, mindset, and operational rules. However, if all personas share a single global `MEMORY.md`, two critical issues arise:
1. **Memory Budget Exhaustion**: High-information workloads (such as bug bounty target scope or smart contract addresses) quickly consume 95%+ of the character limit (e.g., 2,200 chars), leaving zero headroom for other personas to record new durable facts.
2. **Context Cross-Contamination**: Offensive security notes (e.g. bypass patterns, bug reports) pollute the context window during software development or Web3 crypto operations, confusing the model and degrading reasoning quality.

## Architectural Solution

### 1. Separation of Concerns: Identity, Profile & Memory
* **`USER.md` (Global / Shared)**: Who the user is, communication preferences, informal tone, server access (Termius/Tailscale), and universal habits. This is identical regardless of active persona.
* **`SOUL.md` (Active Identity Template)**: Mirrored from `~/.chiper/souls/<soul_id>.md` to `~/.chiper/SOUL.md`.
* **`MEMORY.md` (Active Working Memory)**: Mirrored and dynamically swapped from `~/.chiper/memories/souls/<soul_id>.md` to `~/.chiper/memories/MEMORY.md`.

### 2. Directory Layout
```text
~/.chiper/
├── SOUL.md                    <-- Active persona identity
├── souls/                     <-- Master persona templates
│   ├── chiper-cyber.md
│   ├── chiper-dev.md
│   └── chiper-web3.md
└── memories/
    ├── USER.md                <-- Global user profile
    ├── MEMORY.md              <-- Active persona memory
    └── souls/                 <-- Isolated per-persona memories
        ├── chiper-cyber.md    <-- Cyber: bounties, targets, pentest tooling
        ├── chiper-dev.md      <-- Dev: server ports, repo branches, Docker
        └── chiper-web3.md     <-- Web3: RPCs, spend governor, CTF solvers
```

### 3. Dual-Synchronization Engine

#### A. Swap-on-Switch (`sync_soul_memory_on_switch`)
Triggered during `soul_manager.switch_soul(to_soul_id)`:
1. Read current active `~/.chiper/memories/MEMORY.md` and persist it to `~/.chiper/memories/souls/<from_soul_id>.md`.
2. Locate `~/.chiper/memories/souls/<to_soul_id>.md` (or initialize from defaults if non-existent).
3. Overwrite `~/.chiper/memories/MEMORY.md` with the target soul's memory file.

#### B. Auto-Mirror on Live Writes (`MemoryStore.save_to_disk`)
When the agent executes `memory(action="add", target="memory", ...)`:
1. Write to active `MEMORY.md`.
2. Inspect active soul via `get_active_soul()`.
3. Immediately mirror the entries to `~/.chiper/memories/souls/<active_soul_id>.md`.
This ensures that sudden process termination or unexpected container restarts never lose newly recorded memory entries.

### 4. Backward Compatibility Invariant
Never change `MemoryStore`'s core interface or point external consumers to custom paths. By maintaining `~/.chiper/memories/MEMORY.md` as the active file:
* CLI commands (`chiper doctor`, `chiper memory reset`, `chiper prompt-size`) continue to work without modification.
* System prompt builders and prefix-cache algorithms retain 100% contract stability.
