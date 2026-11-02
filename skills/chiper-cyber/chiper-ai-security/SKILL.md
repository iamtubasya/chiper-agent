---
name: chiper-ai-security
description: "Use when Semantic-layer attack testing against AI systems and LLM-integrated applications."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-security/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-security/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-security/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-security/guides
---

# Ai Security

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `burpsuite` — install: `echo "Download: https://portswigger.net/burp/communitydownload"`
- `ffuf` — install: `go install github.com/ffuf/ffuf/v2@latest`
- `garak` — install: `pip install garak`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in burpsuite ffuf garak; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v burpsuite >/dev/null 2>&1 || echo "  echo "Download: https://portswigger.net/burp/communitydownload""
  command -v ffuf >/dev/null 2>&1 || echo "  go install github.com/ffuf/ffuf/v2@latest"
  command -v garak >/dev/null 2>&1 || echo "  pip install garak"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Ai Security skill domain covering ai operations.

**Tools**: garak, promptfoo, llm-guard, picklescan, ffuf, burpsuite, Custom Python, Burp Suite

**Domain**: ai

## Methodology Overview

### Attack Surface Mapping

Before testing, enumerate all AI integration points in the target:

| Surface | Examples | Injection Vector |
|---------|---------|-----------------|
| API Endpoints | `/v1/chat/completions`, `/api/ask` | `messages[].content`, `system` parameter |
| Chat Interfaces | Web chatbots, Slack bots, embedded widgets | User message field |
| Document Processors | PDF summarizer

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-ai-security/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
