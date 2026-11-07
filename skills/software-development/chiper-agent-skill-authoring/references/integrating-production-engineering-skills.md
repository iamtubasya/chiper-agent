# Integrating Production Engineering Skills into Chiper Agent

## Overview

When adopting external engineering skills (such as Addy Osmani's `agent-skills` canon or Anthropic's skill-creator workflows), importing prose alone is insufficient. AI coding agents fail when skills reference tools that do not exist or when verification gates lack enforceable terminal commands.

This guide details the 4 architectural pillars for porting and adapting production-grade engineering skills into Chiper Agent so they execute with 100% verifiability and zero hallucination.

---

## 1. Bridging External MCP Servers to Native Host Binaries

### The Problem
External skills often assume the presence of proprietary MCP servers (e.g. `mcp__chrometools__*`). If an agent attempts to call nonexistent MCP tools, it falls back to either failing the turn or hallucinating simulated browser output.

### The Chiper Solution
Always map browser and DOM verification workflows to Chiper's installed `/usr/local/bin/agent-browser` CLI:
- Navigation: `agent-browser open <url>`
- AI DOM Inspection: `agent-browser snapshot -i` (generates accessibility tree with `@e1`, `@e2` interactive handles)
- Interaction: `agent-browser click @e1`, `agent-browser fill @e2 "value"`
- Error Audit: `agent-browser errors` and `agent-browser console`
- Visual Proof: `agent-browser screenshot <path>` delivered via `MEDIA:<path>`
- Web Vitals: `agent-browser vitals <url> --json`

Never allow an agent to declare a frontend task completed without real evidence from `agent-browser errors` and a screenshot.

---

## 2. Adversarial Fresh-Context Review via `delegate_task`

### The Problem
Skills like `doubt-driven-development` require an adversarial reviewer with a "fresh context" (biased to disprove, not validate, non-trivial decisions). In long-lived single sessions, the parent agent carries its own confirmation bias and rationalizes flaws.

### The Chiper Solution
Use Chiper's native subagent tool `delegate_task` to spawn an isolated leaf subagent:
```python
delegate_task(
    goal="Adversarial review: Find what is wrong with this artifact. Assume author is overconfident. Look for unstated assumptions, unhandled edge cases, hidden state, and contract violations. Do NOT validate or summarize. Return identified flaws only.",
    context="ARTIFACT:\n" + artifact_diff + "\n\nCONTRACT:\n" + contract_spec,
    toolsets=["file", "terminal"]
)
```
The subagent gets its own pristine conversation and returns only the issues found, completely preventing parent context pollution.

---

## 3. Anti-Rationalization Tables (Blocking AI Excuses)

LLMs under token or iteration limits routinely attempt to skip tests, write stubs, or comment out linters. Every adapted engineering skill must feature an Anti-Rationalization Table that pairs excuses with non-negotiable rebuttals:

| Rationalization (Excuses AI Makes) | Rebuttal (Strict Rule) |
| :--- | :--- |
| *"This is just a small change, I don't need tests."* | **REJECTED:** Tests are proof, not options. Run Red-Green-Refactor. |
| *"I read the code, so I know the UI is fine."* | **REJECTED:** Static code does not prove runtime layout. Run `agent-browser snapshot -i`. |
| *"The test failed due to a strict linter, so I'll add @ts-ignore."* | **REJECTED:** Suppressing linters or skipping tests is a constraint violation. Fix the root cause. |

---

## 4. Constraint-Driven Enforced Standards (`CONSTRAINTS.md`)

To prevent agents from quietly eroding quality over multi-turn sessions:
1. Generate a project-level `CONSTRAINTS.md` defining coverage thresholds, bundle budgets, and forbidden suppression patterns (`@ts-ignore`, `# noqa`, `eslint-disable`).
2. Run automated validation commands before any commit or PR creation.
3. If an agent weakens the bar, reject the turn immediately.
