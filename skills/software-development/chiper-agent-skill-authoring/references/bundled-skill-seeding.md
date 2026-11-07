# Bundled Skill Seeding and Installation Tier Patterns

When bundling large domain-specific skill collections (such as `chiper-cyber` or other multi-domain ecosystems):

## 1. Directory Structure Conventions
- Place the bundled source under `<repo_root>/skills/<collection-name>/`.
- Standardize the target runtime directory to `~/.chiper/skills/<collection-name>/`.
- Keep folder naming lowercase and hyphenated (`chiper-cyber`, not `Chiper` or `Cyber`).

## 2. Interactive Selection Tiers in Installer
For ecosystems with 50+ specialized domains, do not force an all-or-nothing blind copy. Implement tiered selection in `setup-chiper.sh` / installer helper scripts:
1. **Tier 1 (Full Suite):** Installs all domains (e.g. 144 domains including niche hardware, telecom, reverse engineering).
2. **Tier 2 (Curated Subset / Purpose-Built):** Installs high-frequency practical domains (e.g., 28 Bug Bounty domains: SQLi, XSS, SSRF, IDOR, Auth Bypass, Recon, API security).
3. **Tier 3 (Skip):** Skips the specialized ecosystem, keeping the install lightweight, while retaining default general-purpose skills.

## 3. Path Uniformity Checklist
- Scan all `SKILL.md` files for hardcoded legacy paths (`~/.hermes/`, `~/.chiperflux/`, or legacy camelCase names).
- Ensure references to supporting documents (`payloads.md`, `test-cases.md`, `references/`) use the exact matching folder name.

## 4. Self-Contained Skill Packages vs Reference Stub Pitfall
- **Avoid Reference Stubs:** Never create 30-50 line "pointer/stub" skills that reference external repository paths (e.g. `~/.openclaw/...`). If the external path is absent, all companion files (`payloads.md`, `test-cases.md`, `guides/`) become missing.
- **Pack Complete Files In-Place:** Store `SKILL.md` (full methodology), `payloads.md`, `test-cases.md`, `guides/`, and `scripts/` directly in the skill folder `~/.chiper/skills/<collection>/<skill-name>/`.
- **Progressive Disclosure:** Engine `skills_tool.py` automatically surfaces companion `.md` files and `guides/*.md` under `linked_files.references`, allowing on-demand loading via `skill_view("<name>", file_path="payloads.md")`.

## 5. Bridging the Markdown Skill to Host Binary Tools
- A markdown skill is purely instructional. If the required binary tools (e.g. `nmap`, `sqlmap`, `nuclei`, `subfinder`, `ffuf`) are not installed on the host OS, execution will fail with `command not found` and force the agent to fall back to generic stubs.
- **Pair Skills with Binary Installers:** Bundle an idempotent setup script (e.g. `scripts/install-bugbounty-tools.sh`) in the repo that installs essential CLI tools via system package managers (`apt`) and pre-compiled release binaries.
- **Rate-Limit-Free Binary Downloads:** When fetching GitHub release assets without an API token, avoid `api.github.com/repos/...` (which hits 403 rate limits). Instead, query `curl -fsSIL "https://github.com/<owner>/<repo>/releases/latest"` and parse the `location:` redirect header to resolve the latest tag reliably.

## 6. Root Persona Injection (`SOUL.md`)
- The Chiper agent core (`agent/prompt_builder.py`) loads `SOUL.md` into the primary system prompt identity slot only when located at `$CHIPER_HOME/SOUL.md` (`~/.chiper/SOUL.md`).
- When a skill collection defines a persona (e.g. `Chiper-Cyber Bug Bounty Hunter`), the installation script must copy `SOUL.md` to `$CHIPER_HOME/SOUL.md` so it activates across every session turn.
