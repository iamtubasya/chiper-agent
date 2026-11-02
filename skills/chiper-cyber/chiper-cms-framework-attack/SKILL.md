---
name: chiper-cms-framework-attack
description: "Use when Targeted security assessment of Content Management Systems (WordPress, Joomla, Drupal) using specialized scanners and exploit techniques."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, cms, framework, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-cms-framework-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cms-framework-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cms-framework-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-cms-framework-attack/guides
---

# Cms Framework Attack

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `cmseek` — install: `sudo apt install -y cmseek`
- `droopescan` — install: `pip install droopescan`
- `joomscan` — install: `sudo apt install -y joomscan`
- `nikto` — install: `sudo apt install -y nikto`
- `nuclei` — install: `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest`
- `whatweb` — install: `sudo apt install -y whatweb`
- `wpscan` — install: `sudo apt install -y wpscan`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in cmseek droopescan joomscan nikto nuclei whatweb wpscan; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v cmseek >/dev/null 2>&1 || echo "  sudo apt install -y cmseek"
  command -v droopescan >/dev/null 2>&1 || echo "  pip install droopescan"
  command -v joomscan >/dev/null 2>&1 || echo "  sudo apt install -y joomscan"
  command -v nikto >/dev/null 2>&1 || echo "  sudo apt install -y nikto"
  command -v nuclei >/dev/null 2>&1 || echo "  go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
  command -v whatweb >/dev/null 2>&1 || echo "  sudo apt install -y whatweb"
  command -v wpscan >/dev/null 2>&1 || echo "  sudo apt install -y wpscan"
else
  echo "✅ All tools installed"
fi
```

## When to Use

Cms Framework Attack skill domain covering web attack operations.

**Tools**: wpscan, joomscan, droopescan, cmseek, nikto, whatweb, nuclei

**Domain**: web-attack

## Core Tools

| Tool | Purpose | Command Example |
|------|---------|-----------------|
| **wpscan** | WordPress vulnerability scanner: user enum, plugin/theme detection, brute force | `wpscan --url http://target --enumerate u,vp,vt,dbe` |
| **joomscan** | Joomla vulnerability scanner: component detection, config

## Methodology Overview

### Attack Chain

```
CMS Fingerprint → Version/Component Enum → Vulnerability Mapping → Exploitation → Escalation
(cmseek/whatweb)  (wpscan/joomscan/       (CVE database,           (plugin vuln,     (admin access,
                  droopescan)              plugin advisories)       config disclosure, webshell upload,
                                                                     brute force)

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-cms-framework-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
