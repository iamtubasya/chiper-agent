---
name: chiper-logging-monitoring
description: "Use when Security logging and monitoring deficiencies (OWASP A09:2021) refer to applications failing to properly record security events or lacking effective monitoring,"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, logging, monitoring]
references:
  - path: ~/.Chiper/skills/chiper-cyber/chiper-logging-monitoring/SKILL.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-logging-monitoring/payloads.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-logging-monitoring/test-cases.md
  - path: ~/.Chiper/skills/chiper-cyber/chiper-logging-monitoring/guides
---

# Logging Monitoring

## When to Use

Logging Monitoring skill domain covering defense operations.

**Tools**: ELK Stack, Splunk, Wazuh, OSSEC, auditd, Zeek

**Domain**: defense

**OWASP**: A09:2021-Logging Failures

## Core Tools

| Tool | Purpose | Command/Usage Example |
|------|---------|----------------------|
| **ELK Stack** (Elasticsearch + Logstash + Kibana) | Centralized log collection, full-text search, visual analysis | Logstash pipeline parses logs -> Elasticsearch indexes -> Kibana Dashboard displays |
| **Splunk*

## Methodology Overview

### Attack Chain

```
[1] Log Discovery           [2] Log Injection           [3] Log Evasion
  - Log storage location      - CRLF / newline injection  - Clear/modify log files
    probing                    - Forge log levels/         - Log rotation exploitation
  - Log format reversing       timestamps                - Noise injection to
  - Collection path            - Control character        

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.Chiper/skills/chiper-cyber/chiper-logging-monitoring/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.Chiper/skills/chiper-cyber && git pull`
