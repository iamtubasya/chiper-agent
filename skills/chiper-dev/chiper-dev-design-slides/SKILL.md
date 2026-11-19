---
name: chiper-dev-design-slides
description: "Deck presentasi HTML + Chart.js: layout responsif, design token, copywriting formula, strategi slide."
argument-hint: "[topic] [slide-count]"
metadata:
  author: claudekit
  version: "1.0.0"
---

# Slides

Strategic HTML presentation design with data visualization.

## When to Use

- Marketing presentations and pitch decks
- Data-driven slides with Chart.js
- Strategic slide design with layout patterns
- Copywriting-optimized presentation content

## Subcommands

| Subcommand | Description | Reference |
|------------|-------------|-----------|
| `create` | Create strategic presentation slides | `references/create.md` |

## Script Paths

This skill lives at `${CHIPER_HOME:-$HOME/.chiper}/skills/chiper-dev/chiper-dev-design-slides/` — resolve every `scripts/` path against that absolute directory (`${CHIPER_HOME:-$HOME/.chiper}/skills/chiper-dev/chiper-dev-design-slides/scripts/<file>`), never against the project working directory. Sibling sub-skills of the same bundle sit at `${CHIPER_HOME:-$HOME/.chiper}/skills/chiper-dev/<sibling>/`. Scripts read and write project files such as `docs/brand-guidelines.md`, `assets/design-tokens.json` or `src/` relative to the project root, so keep the working directory at the project root.

## References (Knowledge Base)

| Topic | File |
|-------|------|
| Layout Patterns | `references/layout-patterns.md` |
| HTML Template | `references/html-template.md` |
| Copywriting Formulas | `references/copywriting-formulas.md` |
| Slide Strategies | `references/slide-strategies.md` |

## Routing

1. Parse subcommand from `$ARGUMENTS` (first word)
2. Load corresponding `references/{subcommand}.md`
3. Execute with remaining arguments
