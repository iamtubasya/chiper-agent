# BB Audit Multi-Session Architecture

## Real Config (from config.yaml)
```
context_length: 1,000,000    ← 1M tokens per session
max_tokens: ***         ← output limit per response  
max_concurrent_children: 3   ← max 3 PARALLEL workers
child_timeout_seconds: 600   ← 10 min per worker
```

## Problem
- 34 hackskill refs = ~1.7M chars → cannot fit in 1 context
- 82K+ PoCs = ~41M chars → impossible in 1 session  
- Tool output during testing = ~200-400K chars
- 1 session cannot hold everything

## Solution: 2 Waves × 3 Parallel Workers

### Wave 1 (~10 min)
| Worker | Vectors | Hackskill Refs | Payloads |
|--------|---------|----------------|----------|
| 1 | IDOR, Auth bypass, PrivEsc | hackskill-idor, hackskill-authbypass | jwt-attack-payloads.txt |
| 2 | RCE, SSRF, SQLi | hackskill-ssrf, hackskill-sqli | ssrf-payloads.txt, sqli-payloads.txt |
| 3 | XSS, GraphQL, CORS, CSRF | hackskill-xss, hackskill-graphql, hackskill-cors | xss-payloads.txt, graphql-payloads.txt |

### Wave 2 (~10 min)
| Worker | Vectors | Hackskill Refs | Payloads |
|--------|---------|----------------|----------|
| 4 | Race, BizLogic, MassAssign, InfoDisc | hackskill-race, hackskill-business-logic | sensitive-files-wordlist.txt |
| 5 | 403, Cache, OpenRedirect, Smuggling, SSTI, XXE, Upload | hackskill-403, hackskill-open-redirect, hackskill-ssti, hackskill-xxe, hackskill-request-smuggling | — |
| 6 | Nuclei scan (background) | — | nuclei templates |

### Background (across both waves)
- Nuclei scan: `nuclei -u TARGET -severity critical,high -rl 50` (terminal background=true)
- PoC repos: matched by `poc-pipeline.py` → extract → adapt → execute

## Per Worker Budget
```
System prompt:     ~20K chars
Skill loaded:      ~20K chars (only exploit-cookbook relevant sections)
Hackskill refs:    ~30-50K chars (3-5 files only)
Payload files:     ~5K chars (1-2 files only)
Tool output:       ~50K chars (curl responses, etc.)
Reasoning space:   ~625K chars
Total:             ~750K chars (fits in 1M)
```

## Output Convention
Each worker writes results to file:
```
$BB_DATA/_progress/<target>/workers/
  worker-1-idor-auth.md
  worker-2-ssrf-sqli-rce.md
  worker-3-xss-graphql-cors.md
  worker-4-race-bizlogic.md
  worker-5-403-cache-redirect.md
  worker-6-nuclei-results.txt
```

Main agent reads these files → aggregates into findings.json → finding_gate.py → report.

## Key Rules
- Each worker gets FRESH 1M context (isolated session)
- Workers only load refs for THEIR assigned vectors
- Workers write results to FILE (20K output limit)
- Max 3 concurrent (config enforced)
- 10 min timeout per worker (config enforced)
- Nuclei runs in terminal background (not delegate_task — longer than 10 min)
