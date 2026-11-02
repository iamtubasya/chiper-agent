---
name: chiper-article-writing
description: "Use when Transform technical findings into clear, structured written content: penetration test reports, vulnerability disclosures, security blog posts, and technical docume"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, article, writing]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-article-writing/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-article-writing/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-article-writing/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-article-writing/guides
---

# Article Writing

## When to Use

Article Writing skill domain covering knowledge operations.

**Domain**: knowledge

## Methodology Overview

### Phase 1: Gather Intelligence

```bash
# Aggregate all findings from knowledge-ops
grep -rn "type: finding" memory/*target*.md | wc -l

# Extract high-confidence findings (>= 75)
grep -rn "confidence: [789][0-9]\|confidence: 100" memory/*target*.md -l | \
  xargs grep -h "## Summary"

# Group by severity
grep -rn "tags:.*critical\|tags:.*high" memory/*target*.md
```

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-article-writing/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
