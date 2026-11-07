# Chiper Agent Forking & Customization Guide

Playbook and workflow patterns for maintaining, branding, and standardizing the customized Chiper Agent repository.

## 1. Repository & Identity Architecture
- **Canonical Custom Repo Path**: `/home/agentuser/chiper`
- **Branding Standard**:
  - Eliminasi total seluruh referensi: `Nous Research`, `nousresearch.com`, `Hermes`, `hermes-agent`, `ChiperFlux`.
  - Author/Maintainer: **Tubasya** (`iamtubasya@chiper.local`).
  - Remote GitHub URL: `https://github.com/iamtubasya/chiper-agent`.

## 2. Standard Data Directory (`CHIPER_HOME`)
- The single source of truth for runtime state is `chiper_constants.py`:
  ```python
  def _get_platform_default_chiper_home() -> Path:
      return Path.home() / ".chiper"
  ```
- All configuration (`config.yaml`), sessions (`state.db`), OAuth tokens (`auth.json`), logs, and persistent memory live in:
  `~/.chiper/` (replacing legacy `~/.chiperflux/` and `~/.hermes/`).

## 3. Bundled Skills Seeding Concept
- When installing Chiper Agent via `install.sh` / `setup-chiper.sh`, bundled skills inside `/skills/` in the repository are automatically seeded into `~/.chiper/skills/`:
  ```bash
  CHIPER_SKILLS_DIR="${CHIPER_HOME:-$HOME/.chiper}/skills"
  mkdir -p "$CHIPER_SKILLS_DIR"
  cp -rn "$SCRIPT_DIR/skills/"* "$CHIPER_SKILLS_DIR/"
  ```
- To make custom skill ecosystems (such as `chiper-cyber` with 144 security domains) available out-of-the-box on new VPS installations without manual copy commands:
  1. Audit and sanitize all legacy paths/branding in the skill files.
  2. Place the ecosystem directly inside the repo: `/home/agentuser/chiper/skills/<category>/`.
  3. Commit to the git repository.
  4. On any new server running `install.sh`, the installer copies and activates all domains automatically on first run.

## 4. URL Sanitization Pitfall
- When running batch regex replacement to purge upstream branding, check for broken/fictional hostnames (e.g. `chiper-agent.Chiper.com` or `github.com/Chiper/...`).
- Normalize all documentation, clone scripts (`install.sh`, `install.ps1`), and security advisory links to `https://github.com/iamtubasya/chiper-agent`.
