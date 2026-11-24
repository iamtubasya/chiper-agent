# Agent Red Team Report — 2026-11-24

Example render produced by:
`python3 report/generate.py --recon recon/ --template report/agent-redteam.md.j2 --output report/agent-redteam.md`

## 1. Executive summary

| Metric | Value |
|---|---|
| Recon artefacts | 3 |
| MCP probe results | 2 |
| Chain evidence files | 1 |
| Highest severity | High |

## 2. Attack surface

- `surface_triage.md` — 49 lines — populated capability inventory
- `fingerprint.json` — 31 lines — identity and system-prompt probes
- `ai-infra.json` — 27 lines — model endpoints and gateways

## 3. Findings

### F-001 — Tool description carries an indirect instruction
- Severity: Medium · OWASP LLM01 · Technique: indirect prompt injection
- Evidence: `payloads/issue_inject.md`, transcript excerpt
- Recommendation: strip instructions from tool descriptions before they reach the model.

## 4. Recommendations

1. Tool allow-list per agent role.
2. Untrusted-input labelling for every tool result.
3. Regression corpus wired into CI.
