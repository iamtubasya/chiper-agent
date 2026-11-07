# Converting External Agent Workspaces (OpenClaw, Superagent, Hermes) into Chiper Multi-Soul Personas

## Overview
When users import third-party autonomous agent packages (e.g., OpenClaw, Superagent, Hermes-Crypto, or custom agent distributions) as a zip/tarball, they often ask to "make this a soul in Chiper".

Simply copying the package's `SOUL.md` to `~/.chiper/souls/<soul_id>.md` is the **Persona-Without-Body Anti-Pattern**: the agent speaks with the requested persona but cannot execute its specialized operations because the accompanying skills and executable tools were left behind.

## The 4-Pillar Soul Architecture in Chiper

A complete operational soul in Chiper comprises:

```
~/.chiper/
├── souls/
│   ├── chiper-cyber.md
│   ├── chiper-dev.md
│   └── <soul_id>.md             <── Pillar 1: Persona & Operating Boundaries
│
├── skills/
│   └── <ecosystem_name>/        <── Pillar 2: Specialized Skills Suite
│       ├── SKILL.md             (Root harness or category manifest)
│       ├── AGENTS.md / INDEX.md (Router & task mapping)
│       └── skills/ / references/ (Sub-skills, e.g., m0-m48, hermes)
│
├── tools/ / venv / system bin   <── Pillar 3: Executable Scripts & Python Deps
│   ├── scripts / tools in path  (e.g., swap_engine.py, ctf_solver.py)
│   └── pip install dependencies (e.g., web3, solana, eth-account)
│
└── agent/soul_manager.py        <── Pillar 4: Gateway Registration
    └── well_known metadata      (id, name, icon, desc for inline buttons)
```

## Step-by-Step Conversion Workflow

### 1. Extract and Mount the Skills Suite
Extract the external package into a designated category under Chiper's skill tree:
```bash
unzip package.zip -d ~/.chiper/skills/<ecosystem_name>/
```
Ensure directory structure matches Chiper's scanner conventions:
- Standalone sub-skills with YAML frontmatter `SKILL.md` (e.g., `skills/hermes/SKILL.md`) are automatically indexed by `skills_tool`.
- Flat numbered module lists (e.g., `m0.md` ... `m48.md`, `x1.md` ... `x7.md`): **Never leave them as a flat soup of cryptic numbers.** Reorganize each into a dedicated subfolder with a standard **`chiper-`** prefix and semantic slug: `~/.chiper/skills/<ecosystem>/chiper-<semantic-slug>/SKILL.md` (e.g., `chiper-airdrop-intelligence/SKILL.md`, `chiper-ctf-whitehat-toolkit/SKILL.md`, `chiper-web3-onchain-ops/SKILL.md`, `chiper-hermes-crypto-engine/SKILL.md`). Include YAML frontmatter (`name: chiper-<slug>`, `description: ...`) so Chiper indexes each as a first-class skill matching its folder name.
- **Preserve backward compatibility:** In the legacy `skills/` folder, create relative symlinks (`m31.md -> ../chiper-airdrop-intelligence/SKILL.md`, `hermes -> ../chiper-hermes-crypto-engine`) so existing scripts and references never break.

### 2. Craft & Rebrand the Persona (`~/.chiper/souls/<soul_id>.md`)
External packages frequently contain third-party branding (e.g., `SUPERAGENT`, `IRONCLAW`, `OpenClaw`). Look for `IDENTITY.md` — authors often specify:
`> Rename: replace SUPERAGENT in this file + SOUL.md only.`

Rebrand to Chiper conventions (`Chiper-Web3` / `ChiperAgent Web3`), updating the self-introduction prompt while strictly preserving the operator tone, flexibility doctrine, and risk gates.

**Clean Persona Header Rule:**
Always format the very first line of `SOUL.md` cleanly as `# <Clean Name>` (e.g. `# Chiper-Web3`), avoiding long verbose descriptions or prefixes like `# SOUL.md — ...`. Automated parsers and gateway inline keyboards extract the first line as the button label; a long header causes text overflow on mobile and triggers fallback brain icons (`🧠`).

Crucially, insert a **Skill & Tool Loading Protocol** section into the soul text:
```markdown
## Skill & Tool Execution Protocol
- When executing domain tasks, consult skills at: `~/.chiper/skills/<ecosystem_name>/skills/`
- Run local tool scripts located at: `~/.chiper/skills/<ecosystem_name>/tools/`
- Prioritize minimal PoC and simulate transactions before broadcast.
```
This guarantees the agent knows where its tools and reference manuals live upon switching souls.

### 3. Provision Runtime Dependencies & Avoid Legacy Conflicts
External agent engines frequently rely on domain-specific libraries. Read `DEPLOY.md` or `requirements.txt` from the imported package and install them in the active environment:
```bash
pip install web3 eth-account mnemonic solders solana httpx cryptography tonsdk aptos-sdk pysui
```

**Common Dependency Pitfalls:**
- **Legacy vs Native Packages:** Do NOT install ancient packages like `ens` (which pulls `ens 0.6.1` and forces `web3<4`, breaking Python 3.11+). Modern `web3.py` (v6/v7) includes ENS resolution natively via `Web3.ens`.
- **Core Runtime Pin Protection:** If a new package requests a newer transitive dependency (e.g. `websockets>=16` for `solana`), verify against Chiper's core requirements (`websockets==15.0.1`). Re-pin Chiper's core requirement and test imports directly — client libraries almost always execute fine without forcing an incompatible upgrade.

### 4. Integrity Manifest Regeneration (`SKILLS.lock`)
Packages with on-chain or security capabilities often enforce strict tamper detection (e.g., `tools/skill_integrity.py`).
After editing or rebranding `SOUL.md` and `IDENTITY.md`, or restructuring subdirectories, the old checksums in `SKILLS.lock` will mismatch and block on-chain ops.
Always regenerate and verify the lock:
```bash
cd ~/.chiper/skills/<ecosystem_name>/
python tools/skill_integrity.py generate
python tools/skill_integrity.py verify
```

### 5. Automated Unit Testing & Python 3.11 Compatibility Checks
Before declaring an imported suite ready, execute its offline test suites:
```bash
cd ~/.chiper/skills/<ecosystem_name>/tools/tests && bash run_tests.sh
cd ~/.chiper/skills/<ecosystem_name>/chiper-hermes-crypto-engine/tests && bash run_tests.sh
```
**Python 3.11 f-string Syntax Constraint:**
Backslashes inside the `{...}` expression blocks of f-strings (`f"{chal.get('flag_format', r'flag\{.*\}')}"`) raise a fatal `SyntaxError` in Python 3.11 and earlier (PEP 701 backslash support was only introduced in Python 3.12). When constructing dynamic regexes or escaping characters in string interpolation, always assign default regex strings to a variable outside the f-string first:
```python
# BROKEN in Python <= 3.11:
lines.append(f"Regex: {data.get('pattern', r'default\{.*\}')}")

# CLEAN across all Python versions:
pattern = data.get('pattern') or r"default\{.*\}"
lines.append(f"Regex: {pattern}")
```

### 6. Register in Soul Switcher (`agent/soul_manager.py` & Slash Commands)
Add the new soul ID to the `well_known` dictionary and `get_active_soul()` in `agent/soul_manager.py`:
```python
"chiper-web3": {
    "name": "Chiper-Web3",
    "icon": "⚡",
    "desc": "Web3, Crypto Ops, DeFi & CTF Whitehat",
    "priority": 3,
},
```
Also add natural aliases in `gateway/slash_commands.py` (`_handle_soul_command`):
```python
elif target_id in ("web3", "crypto", "superagent"):
    target_id = "chiper-web3"
```
This enables native Telegram/Discord inline buttons (`/new` and `/soul`) and natural text switches (`/soul web3`) with zero friction.
