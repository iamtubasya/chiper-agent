---
name: chiper-kali-heartbeat
description: "Use when Running chiper-cyber maintenance: SCORE.sh, heartbeat, backup, drift detection."
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [chiper-cyber, heartbeat, maintenance, scoring, validation, automation]
references:
  - path: /home/chiper/.Chiper/chiper-cyber/HEARTBEAT.md
  - path: /home/chiper/.Chiper/chiper-cyber/validation
---

# chiper-cyber Heartbeat & Automation

## Prerequisites

> 💡 Tools are auto-checked when this skill is invoked.
> Missing tools get install commands; installed tools are skipped.

**Required tools:**

- `file` — `sudo apt install -y file`

```bash
# Auto-check: only install what's missing
MISSING=""
for cmd in file; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
[ -z "$MISSING" ] && echo "✅ All tools ready" && exit 0
echo "⚠️  Missing:$MISSING"
command -v file >/dev/null 2>&1 || sudo apt install -y file
```

## When to Use

When performing chiper-cyber maintenance, scoring skills, running health checks, or using automation scripts.

## Validation Scripts

All scripts in `/home/chiper/.Chiper/chiper-cyber/validation/`:

| Script | Purpose |
|--------|---------|
| `SCORE.sh` | Quality scoring (7 metrics × 4 components × 5 tiers) |
| `heartbeat.sh` | Workspace health check (`--fix`, `--json`) |
| `auto-backup.sh` | Backup rotation (`--restore`, `--keep N`) |
| `drift-detect.sh` | Config drift detection |
| `scenario-runner.sh` | Cross-skill scenario execution |
| `orchestrator.sh` | End-to-end pentest workflow |
| `tool-selector.sh` | Target-to-tool mapping |
| `report-generator.sh` | Automated report generation |
| `update-skill-standard.py` | Align SKILLs to standard |

## Heartbeat Tasks

# HEARTBEAT.md - Heartbeat Tasks

> Execute the following tasks during each heartbeat poll. Don't just reply HEARTBEAT_OK every time — use heartbeats efficiently.

---

## Health Check

- [ ] Check system resource usage (CPU, memory, disk)
- [ ] Verify core configuration file integrity (SOUL.md, AGENTS.md, IDENTITY.md)
- [ ] Confirm bak/ directory backup is up to date (no older than 3 hours)
- [ ] Verify core file consistency: VERSION matches README version, skill count in CLAUDE.md matches actual directory count (130)
- [ ] Check for `__pycache__` artifacts in skills/ directories

---

## Skill Domain Completeness

- [ ] Verify all 130 skill domains have FULL enrichment (SKILL.md + payloads.md + test-cases.md + guides/)
- [ ] Check for newly added skills that need supplementary files
- [ ] Spot-check 2-3 random skill directories for file consistency

---

## Learning Progress

- [ ] Check today's learning progress (against the learning strategy in TOOLS.md)
- [ ] Advance to the next tool to learn
- [ ] If there's new learning content, update the corresponding skills/ files

---

## Security Check

- [ ] Check memory/alerts.txt for new security alerts
- [ ] Verify core files haven't been tampered with (compare with last backup)
- [ ] Check if sensitive information has been accidentally leaked to non-main sessions

---

## Knowledge Maintenance

- [ ] Clean up memory log files older than 30 days (extract summaries to chronicle/ then archive)
- [ ] If there are important lessons learned, distill them into MEMORY.md
- [ ] Check if MEMORY.md is stale (should be updated within 14 days)
- [ ] Verify skill files in skills/ are up to date with latest tool versions

---

## Execution Rules

1. **Priority Order**: Security Check > Health Check > Skill Domain Completeness > Learning Progress > Knowledge Maintenance
2. **Lightweight Execution**: Only do 1-2 items per heartbeat, rotate tasks to avoid overloading
3. **Record Results**: Briefly log to memory/heartbeat-check-YYYYMMDDHHMM.md
4. **Alert on Anomalies**: When anomalies are detected, immediately log to memory/alerts.txt and notify the captain

---

_Last updated: 2026-06-02_

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
