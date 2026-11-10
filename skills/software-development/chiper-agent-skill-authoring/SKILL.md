---
name: chiper-agent-skill-authoring
description: "Author in-repo SKILL.md: frontmatter, validator, structure."
version: 1.0.0
author: Chiper Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  chiper:
    tags: [skills, authoring, chiper-agent, conventions, skill-md]
    related_skills: [plan, requesting-code-review]
---

# Authoring Chiper-Agent Skills (in-repo)

## Overview

There are two places a SKILL.md can live:

1. **User-local:** `~/.chiper/skills/<maybe-category>/<name>/SKILL.md` (or legacy `~/.chiperflux/skills/`) — personal, not shared. Created via `skill_manage(action='create')`.
2. **In-repo (this skill is about this case):** `<repo_root>/skills/<category>/<name>/SKILL.md` (e.g. `~/chiper/skills/...`) — committed, shipped with the package. Use `write_file` + `git add`. `skill_manage(action='create')` does NOT target this tree.

## When to Use

- User asks you to add a skill "in this branch / repo / commit"
- You're committing a reusable workflow that should ship with chiper
- You're editing an existing skill under `<repo_root>/skills/` (use `patch` for small edits, `write_file` for rewrites; `skill_manage` still works for patch on in-repo skills, but not for `create`)

## Required Frontmatter

Source of truth: `tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements:

- Starts with `---` as the first bytes (no leading blank line).
- Closes with `\n---\n` before the body.
- Parses as a YAML mapping.
- `name` field present.
- `description` field present, ≤ **1024 chars** (`MAX_DESCRIPTION_LENGTH`).
- Non-empty body after the closing `---`.

Peer-matched shape used by every skill under `skills/software-development/`:

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars (MAX_NAME_LENGTH)
description: Use when <trigger>. <one-line behavior>.
version: 1.0.0
author: Chiper Agent
license: MIT
metadata:
  chiper:
    tags: [short, descriptive, tags]
    related_skills: [other-skill, another-skill]
---
```

`version` / `author` / `license` / `metadata` are NOT enforced by the validator, but every peer has them — omit and your skill sticks out.

## Size Limits

- Description: ≤ 1024 chars (enforced).
- Full SKILL.md: ≤ 100,000 chars (enforced as `MAX_SKILL_CONTENT_CHARS`, ~36k tokens).
- Peer skills in `software-development/` sit at **8-14k chars**. Aim for that range. If you're pushing past 20k, split into `references/*.md` and reference them from SKILL.md.

## Peer-Matched Structure

Every in-repo skill follows roughly:

```
# <Title>

## Overview
One or two paragraphs: what and why.

## When to Use
- Bulleted triggers
- "Don't use for:" counter-triggers

## <Topic sections specific to the skill>
- Quick-reference tables are common
- Code blocks with exact commands
- Chiper-specific recipes (tests via scripts/run_tests.sh, ui-tui paths, etc.)

## Common Pitfalls
Numbered list of mistakes and their fixes.

## Verification Checklist
- [ ] Checkbox list of post-action verifications

## One-Shot Recipes (optional)
Named scenarios → concrete command sequences.
```

Not every section is mandatory, but `Overview` + `When to Use` + actionable body + pitfalls are the minimum for the skill to feel like a peer.

## Directory Placement

```
skills/<category>/<skill-name>/SKILL.md
```

Categories currently in repo (confirm with `ls skills/`): `autonomous-ai-agents`, `creative`, `data-science`, `devops`, `dogfood`, `email`, `gaming`, `github`, `leisure`, `mcp`, `media`, `mlops/*`, `note-taking`, `productivity`, `red-teaming`, `research`, `smart-home`, `social-media`, `software-development`.

Pick the closest existing category. Don't invent new top-level categories casually.

## Workflow

1. **Survey peers** in the target category:
   ```
   ls skills/<category>/
   ```
   Read 2-3 peer SKILL.md files to match tone and structure.
2. **Check validator constraints** in `tools/skill_manager_tool.py` if unsure.
3. **Draft** with `write_file` to `skills/<category>/<name>/SKILL.md`.
4. **Validate locally**:
   ```python
   import yaml, re, pathlib
   content = pathlib.Path("skills/<category>/<name>/SKILL.md").read_text()
   assert content.startswith("---")
   m = re.search(r'\n---\s*\n', content[3:])
   fm = yaml.safe_load(content[3:m.start()+3])
   assert "name" in fm and "description" in fm
   assert len(fm["description"]) <= 1024
   assert len(content) <= 100_000
   ```
5. **Git add + commit** on the active branch.
6. **Note:** the CURRENT session's skill loader is cached — `skill_view` / `skills_list` will not see the new skill until a new session. This is expected, not a bug.

## Cross-Referencing Other Skills

`metadata.chiper.related_skills` unions both trees (`skills/` in-repo and `~/.chiperflux/skills/`) at load time. You CAN reference a user-local skill from an in-repo skill, but it won't resolve for other users who clone the repo fresh. Prefer referencing only in-repo skills from in-repo skills. If a frequently-referenced skill lives only in `~/.chiperflux/skills/`, consider promoting it to the repo.

## Editing Existing In-Repo Skills

- **Small fix (typo, added pitfall, tightened trigger):** `skill_manage(action='patch', name=..., old_string=..., new_string=...)` works fine on in-repo skills.
- **Major rewrite:** `write_file` the whole SKILL.md. `skill_manage(action='edit')` also works but requires supplying the full new content.
- **Adding supporting files:** `write_file` to `skills/<category>/<name>/references/<file>.md`, `templates/<file>`, or `scripts/<file>`. `skill_manage(action='write_file')` also works and enforces the references/templates/scripts/assets subdir allowlist.
- **Always commit** the edit — in-repo skills are source, not runtime state.

## Common Pitfalls

1. **Using `skill_manage(action='create')` for an in-repo skill.** It writes to user-local skills (`~/.chiper/skills/`), not the repo tree. Use `write_file` for in-repo creation.

2. **Hardcoding paths across imported skill trees.** When importing bundled skills or multi-domain ecosystems (e.g. `skills/chiper-cyber/`), ensure all internal relative references, guides, payloads, and READMEs strictly resolve against standardized runtime paths (`~/.chiper/skills/<domain-folder>/`) rather than legacy paths (`~/.hermes/`, `~/.chiperflux/`, or inconsistent capitalization like `~/.Chiper/`). Verify folder name matches path expectations exactly.

3. **Inconsistent interactive skill seeding during installation.** If a skill ecosystem is large (e.g. 100+ specialized pentest/bug bounty domains), provide interactive selection tiers in `setup-chiper.sh` / installer helpers (e.g. Full suite vs Curated subset like Bug Bounty vs Skip) so the user is not forced into massive storage overhead on minimal VPS setups.

4. **The Reference Stub Trap (Missing Companion Files).** Never import external skills as 30-line pointer stubs that reference paths outside the repository or assume external workspaces exist. Companion files (`payloads.md`, `test-cases.md`, `guides/`) will be missing, causing `skill_view` file errors. Always bundle full methodology and companion files in-place inside `~/.chiper/skills/<collection>/<skill>/`.

5. **The Markdown vs Binary Tool Gap.** Skills define how to use tools, but cannot execute them if the host OS lacks the binary CLI. When shipping skills that require CLI tools (`nmap`, `sqlmap`, `nuclei`, `subfinder`), pair them with an automated installer script (`scripts/install-bugbounty-tools.sh`) that installs packages via `apt` and pre-compiled release binaries. Resolve GitHub release tags via HTTP `Location:` header redirects rather than the rate-limited `api.github.com` endpoint.

6. **Burying `SOUL.md` inside skills subdirectories.** The agent prompt builder (`agent/prompt_builder.py`) only auto-injects `SOUL.md` into the identity slot if it lives at `$CHIPER_HOME/SOUL.md`. For multi-persona environments, store identities under `$CHIPER_HOME/souls/<soul_id>.md` and mirror the active selection to `$CHIPER_HOME/SOUL.md` on switch. See `references/multi-soul-and-interactive-gateway-ux.md`.

7. **Forcing CLI/server commands in chat for interactive inputs.** When a gateway button invites user input (e.g. `Add your SOUL.md`), never demand that users type complex command syntax (`/soul add ...`) or edit files on the server. Implement a conversational state (`_pending_*_prompt`) in the platform adapter so the user can directly type the instructions or drop a `.md` file in chat.

8. **The Persona-Without-Body Trap (Converting External Agent Workspaces into Souls).** Copying an external agent's `SOUL.md` into `~/.chiper/souls/` without migrating its companion `skills/`, `tools/`, and runtime dependencies creates a persona that claims capabilities it cannot execute. A complete Chiper soul conversion requires the 4-pillar integration: (1) persona template in `~/.chiper/souls/`, (2) skills suite under `~/.chiper/skills/<ecosystem>/`, (3) executable scripts and Python venv dependencies, and (4) registering soul metadata in `agent/soul_manager.py`. See `references/converting-external-agent-workspaces-to-souls.md`.

9. **Cryptic Flat File Naming in Imported Skill Ecosystems.** When converting external or community skill packs that use numbered files (`m1.md`, `m31.md`, `x1.md`), do not leave them as a flat soup of cryptic markdown files. Reorganize them into clean, self-contained subdirectories named after their specific domain with a standard `chiper-` prefix (`chiper-airdrop-intelligence/SKILL.md`, `chiper-web3-onchain-ops/SKILL.md`) matching standard YAML frontmatter (`name: chiper-<slug>`, `description: ...`), while creating relative symlinks in `skills/` (`m31.md -> ../chiper-airdrop-intelligence/SKILL.md`) to preserve backward compatibility for legacy scripts.

10. **Clean Persona Display Names vs Raw Markdown Headers.** The first line of `SOUL.md` should cleanly state the persona name (`# Chiper-Web3`), avoiding long verbose descriptions or prefixes like `# SOUL.md — ...`, so that automated parsers and gateway inline keyboards render clean, readable buttons (`⚡ Chiper-Web3`) without overflowing or displaying fallback icons (`🧠`).

11. **Python 3.11 f-String Backslash Syntax Errors.** Backslashes inside f-string `{...}` expressions (e.g. inline raw regex defaults `r'flag\{.*\}'`) fail with `SyntaxError` on Python 3.11 (PEP 701 backslash support is Python 3.12+). Always extract regex literals to local variables before string interpolation.

12. **Monolithic Memory in Multi-Soul Systems (The 95%+ Budget Trap).** Do not force all agent personas to share a single global `MEMORY.md`. High-information workloads (bounties, contracts) quickly exhaust character limits and contaminate reasoning context. Isolate long-term notes under `~/.chiper/memories/souls/<soul_id>.md`, swap them on persona switch via `sync_soul_memory_on_switch()`, and auto-mirror live memory tool writes while keeping `USER.md` global. See `references/isolated-soul-memory-architecture.md`.

13. **Vague Verification and AI Rationalization.** Models tend to rationalize skipping verification or test steps when under token/turn pressure. Every production skill should define explicit "When NOT to Use" boundaries, an Anti-Rationalization table (mapping common AI excuses to firm rebuttals), and a hard Verification Gate requiring real tool execution proof before declaring completion.

14. **The MCP Dependency Hallucination Trap.** When porting external skills designed for proprietary or editor-specific MCP servers (e.g. Chrome DevTools MCP, Figma MCP), do not copy the tool instructions verbatim without verifying the host runtime. Porting an MCP skill requires bridging it to installed local CLI tools (e.g. `agent-browser` + Chromium 157) with concrete executable syntax (`agent-browser open`, `snapshot -i`, `errors`, `screenshot`). An unadapted MCP skill causes the agent to hallucinate tool capabilities it cannot execute. See `references/integrating-production-engineering-skills.md`.

15. **The Clean-Install Multi-Soul and Memory Void.** When architecting Multi-Soul personas (`~/.chiper/souls/`) and isolated soul memories (`~/.chiper/memories/souls/`), never rely solely on lazy initialization triggered by user slash commands (`/soul`). A fresh installation via `setup-chiper.sh` or `scripts/install.sh` must explicitly execute `ensure_default_souls()` and `ensure_default_soul_memories()` during setup so the default persona (`chiper-cyber.md`) and memory stores are populated out-of-the-box. Furthermore, runtime loaders (`load_soul_md()` and `load_from_disk()`) must incorporate self-healing fallbacks that auto-regenerate default souls and memories if the files are ever manually deleted. See `references/clean-install-multi-soul-verification.md`.

16. **The Contaminated Default Memory on Fresh Install (Clean-Slate Soul Memory Isolation).** When configuring multi-soul systems with isolated per-persona memories (`DEFAULT_SOUL_MEMORIES`), never pre-populate default memory templates with developer-specific credentials, email addresses, personal IPs, or target intel. In clean repository builds, `DEFAULT_SOUL_MEMORIES` must default to empty strings `""` for all souls (`chiper-cyber`, `chiper-hunt`, `chiper-dev`, `chiper-web3`). This ensures fresh installations on new servers start with a pristine blank slate, enabling each persona to dynamically build, record, and maintain its own context without inheriting stale or sensitive historical state.

17. **Disclosed Security Reports vs GitHub Push Protection (GH013).** When bundling bug bounty reference materials, CVE writeups, or disclosed report archives into a skill repository, sample payloads and redacted HTTP dumps frequently contain tokens that match GitHub secret scanning signatures (npm `_authToken=...`, Salesforce `sid=00D...`, Facebook Graph API `EAA...`). Merely pushing a patch commit on top will fail because Git history retains the blocked commit. The required recovery protocol: (1) `git reset HEAD~1` to keep modifications unstaged, (2) run an automated regex sanitization script over all markdown, json, and text files, and (3) re-stage and commit cleanly.

18. **Soul Separation over Domain Collision (Generalist vs Specialist Personas).** When integrating specialized vulnerability packages (e.g. 67 `hunt-*` commercial bug bounty checklists) alongside an enterprise offensive suite (`chiper-web-*`), avoid overloading a single persona with duplicate skill categories. Architect distinct souls with clear operational boundaries: `🛡️ Chiper-Cyber` for enterprise infrastructure, Active Directory, telecom, and defensive standards; and `🎯 Chiper-Hunt` for commercial payout-driven bounty hunting. This eliminates LLM confusion on which skill to call, optimizes token consumption, and isolates target records in dedicated soul memory. See `references/clean-slate-soul-memory-and-push-protection.md`.

9. **Leading whitespace before `---`.** The validator checks `content.startswith("---")`; any leading blank line or BOM fails validation.

3. **Description too generic.** Peer descriptions start with "Use when ..." and describe the *trigger class*, not the one task. "Use when debugging X" > "Debug X".

4. **Forgetting the author/license/metadata block.** Not validator-enforced, but every peer has it; omitting makes the skill look half-finished.

5. **Writing a skill that duplicates a peer.** Before creating, `ls skills/<category>/` and open 2-3 peers. Prefer extending an existing skill to creating a narrow sibling.

6. **Expecting the current session to see the new skill.** It won't. The skill loader is initialized at session start. Verify in a fresh session or via `skill_view` using the exact path.

7. **Linking to skills that don't exist in-repo.** `related_skills: [some-user-local-skill]` works for you but breaks for other clones. Prefer only in-repo links.

## Verification Checklist

- [ ] File is at `skills/<category>/<name>/SKILL.md` (not in `~/.chiperflux/skills/`)
- [ ] Frontmatter starts at byte 0 with `---`, closes with `\n---\n`
- [ ] `name`, `description`, `version`, `author`, `license`, `metadata.chiper.{tags, related_skills}` all present
- [ ] Name ≤ 64 chars, lowercase + hyphens
- [ ] Description ≤ 1024 chars and starts with "Use when ..."
- [ ] Total file ≤ 100,000 chars (aim for 8-15k)
- [ ] Structure: `# Title` → `## Overview` → `## When to Use` → body → `## Common Pitfalls` → `## Verification Checklist`
- [ ] `related_skills` references resolve in-repo (or are explicitly OK to be user-local)
- [ ] `git add skills/<category>/<name>/ && git commit` completed on the intended branch
