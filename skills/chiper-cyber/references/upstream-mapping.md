# Upstream Mapping: `chiper-cyber` ↔ `brucesongs/chiper-cyber`

## Root Cause of Missing Companion Files

`chiper-cyber` was initially generated using the "Approach 2: Semi-Manual Migration (Reference Stubs)" script from `GUIDE-HERMES-en.md` in `https://github.com/brucesongs/chiper-cyber`. That script emits 50–100 line pointer `SKILL.md` files referencing `payloads.md`, `test-cases.md`, and `guides/` without copying the underlying files.

## Directory & Skill Mapping

| `chiper-cyber` Path | `brucesongs/chiper-cyber` Upstream Path | Notes |
|---|---|---|
| `chiper-<domain>/SKILL.md` | `skills/<domain>/SKILL.md` | Upstream has full methodology + Defense Triple (~300–500 lines/skill); `chiper-cyber` adds `## Prerequisites` apt/pip tool auto-check block |
| `chiper-<domain>/payloads.md` | `skills/<domain>/payloads.md` | Ready-to-use categorized attack payloads (139 files) |
| `chiper-<domain>/test-cases.md` | `skills/<domain>/test-cases.md` | Structured `TC-*` test cases with prerequisites & expected results (139 files) |
| `chiper-<domain>/guides/` | `skills/<domain>/guides/` | Deep-dive guides, lab notes, and helper `.py`/`.sh` scripts (762 files across 139 skills) |
| `validation/` | `validation/` | `SCORE.sh`, `heartbeat.sh`, `orchestrator.sh`, `tool-selector.sh`, `report-generator.sh`, `skill-lint.py`, `validate-payloads.py`, `validate-testcases.py` |
| `TOOLS.md`, `HEARTBEAT.md`, `AGENTS.md`, `KALI_TOOLS_BASELINE_*.md` | Root of `chiper-cyber` | Referenced by `chiper-kali-tools`, `chiper-kali-heartbeat`, and `chiper-kali-pentest-orchestrator` |
| `docs/tools/full-inventory.md` | `docs/tools/full-inventory.md` | 518 Kali tool inventory referenced by `chiper-kali-tools` |

## Skills Unique to Each Repository

- **Chiper-Cyber Custom Skills (Preserve During Sync)**:
  - `chiper-bootstrap/` (`scripts/install.sh`, `scripts/verify.sh`, `references/tool-inventory.md`)
  - `chiper-voice-agent-attack/` (LiveKit/WebRTC voice agent exploitation)
  - `chiper-security/llm-agent-bounty-platform/` (`references/bluejay-agent-targets.md`, `references/supabase-cookie-injection.md`)
  - `chiper-security-bounty-hunter/references/` (`spa-api-and-mcp-recon.md`, `spa-api-recon.md`, `web3-frontend-recon.md`)
- **Additional Skills in `chiper-cyber` (Import with `chiper-` Prefix)**:
  - `ai-agent-supply-chain-attack` → `chiper-ai-agent-supply-chain-attack`
  - `eu-ai-act-compliance-redteam` → `chiper-eu-ai-act-compliance-redteam`
  - `pqc-implementation-attack` → `chiper-pqc-implementation-attack`
