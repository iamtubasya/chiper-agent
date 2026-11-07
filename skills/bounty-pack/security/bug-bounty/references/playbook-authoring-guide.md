# Playbook Authoring Guide — extending the articles compendium / reference playbooks

Workflow used to build the 15 `articles-*-playbook.md` (v3.1.0). Follow it for any future playbook addition (new research batches, new topic compendiums).

## Format spec (clone from `references/articles-csp-bypass-playbook.md` — the reference implementation)
7 sections, ~80 lines, 5.3-7.4KB:
1. Title + source quote block (article count, year range, authors, extracts path, "Complements:" links)
2. `## Article Map` — table: Year | Title | Contribution
3. `## Key Techniques` — bullets, mechanism-level (explain WHY, not just steps)
4. `## Payload / Bypass Table` — literal payloads only, never paraphrase
5. `## By-Design / SKIP Filters` — false-positive filters, dead-chain conditions
6. `## Severity Guide` — HIGH→INFO ladder, every tier tied to proof quality; blocked chain = INFORMATIONAL per master KB
7. `## Reporting Checklist` — evidence items + footer: `> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.`

## Workflow (source-first, non-negotiable)
1. Read the source articles FULLY before writing a single playbook line — payloads/techniques must be accurate, not reconstructed from memory. Large files: read in offset chunks until `total_lines` reached.
2. Re-verify format by `head`/`tail` on the reference playbook immediately before writing.
3. Write playbooks in batches of 3 (delegatable); name new files `articles-<topic>-playbook.md`.
4. After each batch: `ls -la` sizes + per-file `grep -cE '^## '` section count.
5. Final verify: playbook count, gate order in SKILL.md (`grep -nE "GATE|TOOLING"`), version bump in SKILL.md frontmatter + gate section referencing the new playbook.
6. Update the master memory entry (skill version + gate list) after the version bump.

## Pitfalls
- `search_files` with pattern `*` (or any bare repetition operator) → rg error "repetition operator missing expression". Use `terminal` ls/find/grep for file enumeration, or a valid regex.
- Skill playbook location is `~/.chiper/skills/bounty-pack/bug-bounty/references\` — a `D:\data hermes\bug-bounty\skill\` mirror does NOT exist. Only bug-bounty DATA lives on D: (global rule); skill/knowledge files stay on C:.
- SKILL.md is >100KB: never full-read before patching; use grep for anchors + targeted `read_file` windows, then `patch` (replace mode) — write_file would require a full read and risks clobbering.
- `grep -cE '^## '` counts 6 not 7 when the footer isn't a `##` — footer is a `>` blockquote by design; don't "fix" it.
- Path conventions inside playbooks: extracts `D:\data hermes\bug-bounty\_portswigger-extracts\articles\`, index `articles-index.json`.
