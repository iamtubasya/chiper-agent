---
name: chiper-ai-agent-framework-attack
description: "Use when AI agent framework attack surface — orchestration-layer compromise of LangChain (Python/JS), LangGraph, CrewAI, Microsoft AutoGen, OpenAI Assistants API"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, agent, framework, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-agent-framework-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-agent-framework-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-agent-framework-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-ai-agent-framework-attack/guides
---

# Ai Agent Framework Attack

## When to Use

AI Agent Framework Attack skill domain covering orchestration-layer compromise of LLM agent systems. While adjacent skills (ai-security, llm-red-team) focus on model-layer attacks (jailbreaks, adversarial suffixes, GCG), this skill targets the **orchestration layer**: the framework code that decides which tools to call, how to parse outputs, when to loop, and what to send back to the model. The framework is where 2025's most consequential AI vulnerabilities have lived — from Simon Willison's tool-poisoning demonstrations to the November 2024 MCP rug-pull disclosures to the wave of LangChain CV

## Core Tools

The agent framework attack toolkit is unusually polyglot — offensive work spans Python, JavaScript/TypeScript, and sometimes Rust/Go. The below are the workhorses:

| Tool | Category | Purpose |
|------|----------|---------|
| `langchain` | Framework target | Python/JS agent framework; inspect via `

## Methodology Overview

The attack surface of an agent system decomposes into seven concentric layers, each with its own recon, payload design, and exploitation techniques. The methodology proceeds outside-in: start with externally observable behavior, then progressively internalize.

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-ai-agent-framework-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
