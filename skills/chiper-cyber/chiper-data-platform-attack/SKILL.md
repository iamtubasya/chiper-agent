---
name: chiper-data-platform-attack
description: "Use when Attacks against cloud data platforms and analytics pipelines — Snowflake, Databricks, BigQuery, Redshift, dbt, Apache Airflow, and lakehouse architectures. Co"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, data, platform, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-data-platform-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-data-platform-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-data-platform-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-data-platform-attack/guides
---

# Data Platform Attack

## Prerequisites

> 💡 Missing tools? This skill will auto-check before execution.

**Required tools:**

- `sqlmap` — install: `sudo apt install -y sqlmap`

**Quick check (run before using this skill):**

```bash
# Check which tools are missing
MISSING=""
for cmd in sqlmap; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "⚠️  Missing tools:$MISSING"
  echo "Install with:"
  command -v sqlmap >/dev/null 2>&1 || echo "  sudo apt install -y sqlmap"
else
  echo "✅ All tools installed"
fi
```

## When to Use

This skill targets modern cloud data platforms — warehouses, lakehouses, orchestration layers, and transformation pipelines — where the boundary between analytics and production has collapsed. Attackers no longer tunnel through database listeners; they walk in through SSO, service tokens, and CI/CD pipelines.

**Tools**: snowsql, databricks-cli, gcloud (BigQuery), aws cli (Redshift/Athena), bq, psql (Redshift), dbt, airflow-cli, spark-sql, sqlmap, pacu, enumerate-iam, m365 dataset scrapers

**Domain**: data-platform

**MITRE ATT&CK**: TA0006 Credential Access · T1078 Valid Accounts · T1213 Dat

## Core Tools

### Snowflake
- **snowsql** — official CLI; use with `SNOWFLAKE_ACCOUNT`, `--authenticator=externalbrowser` for SSO
- **snowflake-connector-python** — script recon and bulk queries
- **snowflake-labs** GitHub repos — reference payloads (account enumeration, role mapping)

## Methodology Overview

### Phase 1 — Reconnaissance (Account & Tenant Discovery)
- Snowflake account URL enumeration via org patterns (`acme-orgname.snowflakecomputing.com`)
- SAML IdP fingerprinting to confirm account existence
- GitHub dorks: `"snowflake_account"`, `"snowflakecomputing.com"`, `dbt_profiles.yml` blobs
- Databricks workspace URL patterns (`adb-<digits>.<azuredatabricks.net | aws>.net`)
- BigQuery datase

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-data-platform-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
