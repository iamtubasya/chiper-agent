# Upstream Skill Suite Sync & Hydration Protocol

When updating or syncing `chiper-cyber` from upstream multi-file security skill repositories:

## 1. User Preferences & Hard Requirements
- **Full `SKILL.md` only (No Reference Stubs):** Never use stub generators (such as `create_stubs.py`) that replace `SKILL.md` with short pointer wrappers. Always use the complete upstream `SKILL.md` (including full Methodology, Core Tools, Practical Steps, and Defense Triple) and remove legacy wrapper stubs.
- **Strict `chiper-` Prefix & Branding:**
  - All skill directories and frontmatter `name:` fields must use `chiper-<domain>`.
  - Executable scripts inside `guides/` or `validation/` must be placed in `scripts/` (and `validation/`) with the `chiper-` prefix (e.g., `scripts/chiper-bug-bounty-sqli-scanner.py`, `validation/chiper-tool-selector.sh`, `validation/chiper-orchestrator.sh`).
  - Baseline files must use `CHIPER_TOOLS_BASELINE_*.md`.
  - Strip all upstream `kali-claw` and `openclaw` branding and rewrite cross-skill links (`skills/<domain>/...` or `<domain>/SKILL.md`) to `chiper-<domain>/...`.
- **Zero Missing References:**
  - Copy every companion file in each skill directory (`payloads.md`, `test-cases.md`, `guides/*`, and root-level companion guides such as `sqli-double-query-guide.md`, `sqli-cross-db-guide.md`, `api-security-guide.md`, `access-control-guide.md`, `auth-bypass-guide.md`).
  - Populate frontmatter `references:` only with paths that exist on disk.

## 2. Chiper Loader Integration (`agent/skill_utils.py` & `tools/skills_tool.py`)
- `SKILL_SUPPORT_DIRS` in `agent/skill_utils.py` includes `("references", "templates", "assets", "scripts", "guides", "validation", "docs", "evidence")` and `is_skill_support_path()` treats any non-`SKILL.md` file in a directory containing `SKILL.md` as a support file.
- `tools/skills_tool.py` automatically surfaces root companion `.md` files (`payloads.md`, `test-cases.md`, etc.) and `guides/*.md` in `linked_files["references"]` when `skill_view(name)` is called.

## 3. Verification Commands
Run all three validators from the `chiper-cyber` root before committing:
```bash
python3 validation/chiper-skill-lint.py
python3 validation/chiper-validate-payloads.py
python3 validation/chiper-validate-testcases.py
```
Sync changes across `~/.chiper/skills/chiper-cyber`, `~/.chiper/skills/chiper-cyber`, and `/home/agentuser/chiper/skills/chiper-cyber`.
