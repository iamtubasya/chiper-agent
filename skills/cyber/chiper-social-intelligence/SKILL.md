---
name: chiper-social-intelligence
description: "Use when Real-time intelligence gathering from social platforms and community discussions — capturing what people are saying, sharing, and leaking right now."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, social, intelligence]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-social-intelligence/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-social-intelligence/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-social-intelligence/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-social-intelligence/guides
---

# Social Intelligence

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `sherlock` — install: `pip install sherlock-project`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in sherlock; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v sherlock >/dev/null 2>&1 || echo "  pip install sherlock-project"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Social Intelligence skill domain covering osint operations.

**Tools**: Brave Search API, Serper API, Reddit API, HackerNews (Algolia), Sherlock, yt-dlp, snscrape, Twint (+2 more)

**Domain**: osint

**MITRE ATT&CK**: TA0043-Reconnaissance

## Core Tools

### Search & Discovery

| Tool | Purpose | Command/Usage Example |
|------|---------|----------------------|
| **Brave Search API** | Privacy-respecting web search with API access | `curl "https://api.search.brave.com/res/v1/web/search?q=<query>" -H "X-Subscription-Token: $BRAVE_API_KEY"` |
| **Serp

## Methodology Overview

### Social Intelligence Five-Phase Process

```
Phase 1           Phase 2           Phase 3           Phase 4           Phase 5
Define Target  →  Select Platforms  →  Parallel Search  →  Normalize &    →  Cluster &
& Keywords        & Configure          & Collect           Deduplicate       Report
    │                 │                    │                   │                │
    ▼              

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-social-intelligence/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
