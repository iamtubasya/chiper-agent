# AI agent surface triage worksheet

> Populate during `chiper-ai-agent-security` recon:
> `# executes code? has destructive tools? — populate recon/surface_triage.md`

## Target header

| Field | Value |
|---|---|
| Agent / product | |
| Endpoint | |
| Auth model | `none / api key / oauth / session` |
| Data stores | |
| Last updated | |

## Capability inventory

| Capability | Present? | Evidence | Risk if abused |
|---|---|---|---|
| Executes code (REPL / sandbox) | | | |
| Reads/writes files | | | |
| Network egress (unrestricted) | | | |
| Destructive tools (delete/send/pay) | | | |
| Holds credentials in context | | | |
| Connects to MCP servers | | | |
| Long-term memory write | | | |
| Multi-agent delegation | | | |

## Trust boundaries

```
user input ──► system prompt ──► tool layer ──► (files | network | code)
                    ▲                  │
                    └── retrieved docs ┘   ← untrusted, injection-capable
```

## Injection entry points to test

1. Uploaded documents / retrieved web content (indirect).
2. Tool outputs — error messages, API responses, repository issues.
3. Memory writes that persist across sessions.
4. Multi-agent messages from a lower-trust peer.

## Prioritised next tests

| # | Test | Skill | Status |
|---|---|---|---|
| 1 | | chiper-ai-agent-security | |
| 2 | | chiper-llm-red-team | |
