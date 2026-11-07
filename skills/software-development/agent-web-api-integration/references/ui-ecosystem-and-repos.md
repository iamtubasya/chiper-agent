# Curated AI Agent Web UI & API Repositories

Comprehensive index of top-tier open-source repositories for building Web UIs and REST/WebSocket APIs for AI Agents.

---

## 1. Web UI Stacks for AI Agents

| Repository | GitHub Stars | Key Architectural Strengths |
| :--- | :---: | :--- |
| **[`assistant-ui/assistant-ui`](https://github.com/assistant-ui/assistant-ui)** | ~13,000 ⭐ | • Highly composable React / TypeScript library for AI Chat.<br>• Native support for tool call execution badges, Markdown code blocks, and Claude Artifacts-style side-panels.<br>• Zero vendor lock-in; plugs cleanly into Vercel AI SDK or direct fetch. |
| **[`CopilotKit/CopilotKit`](https://github.com/CopilotKit/CopilotKit)** | ~38,500 ⭐ | • The frontend stack for Generative UI and autonomous agent copilot widgets.<br>• Creators of the AG-UI protocol for agent-to-UI streaming.<br>• Supports React, Angular, Mobile, and real-time state synchronization between Agent and DOM. |
| **[`open-webui/open-webui`](https://github.com/open-webui/open-webui)** | ~158,000 ⭐ | • Industry-standard self-hosted ChatGPT / Claude clone.<br>• Complete feature set: multi-model switching, web search, code runner, persistent DB, role-based access.<br>• Pairs with Chiper via `scripts/setup_open_webui.sh` pointing to port 8642. |
| **[`LibreChat-AI/LibreChat`](https://github.com/LibreChat-AI/LibreChat)** | ~46,800 ⭐ | • Enterprise multi-user AI platform with native support for Agents, MCP servers, Skills, and Artifacts.<br>• Supports OpenAI format, Anthropic format, and custom model endpoints. |
| **[`siteboon/claudecodeui`](https://github.com/siteboon/claudecodeui)** | ~14,500 ⭐ | • Lightweight mobile & web GUI specifically designed to inspect and drive CLI coding agents remotely. |

---

## 2. Agent Skills Catalogs (SKILL.md) for UI & API Design

| Repository | GitHub Stars | Focus Area |
| :--- | :---: | :--- |
| **[`anthropics/skills`](https://github.com/anthropics/skills)** | ~188,000 ⭐ | Canonical Anthropic specification for portable `SKILL.md` Agent Skills. |
| **[`sickn33/agentic-awesome-skills`](https://github.com/sickn33/agentic-awesome-skills)** | ~49,200 ⭐ | 2,900+ curated skills with AAS local catalog discovery and automatic skill routing. |
| **[`TheGoat395/Codex-Skills`](https://github.com/TheGoat395/Codex-Skills)** | ~150 ⭐ | Frontend-specific agent skills: modern responsive layouts, accessibility (a11y), visual QA, motion. |
| **[`bergside/awesome-design-skills`](https://github.com/bergside/awesome-design-skills)** | ~3,500 ⭐ | 67 `DESIGN.md` & `SKILL.md` token specifications for design systems and clean UI generation. |
| **[`Remy349/skills`](https://github.com/Remy349/skills)** | ~10 ⭐ | Hexagonal Architecture + DDD for REST APIs across Python (FastAPI), TypeScript, and Go. |

---

## 3. Protocol Bridges & Context Optimization

| Repository | GitHub Stars | Purpose |
| :--- | :---: | :--- |
| **[`open-webui/mcpo`](https://github.com/open-webui/mcpo)** | ~4,400 ⭐ | MCP-to-OpenAPI proxy server: automatically exposes any MCP tool collection as a Swagger REST API. |
| **[`headroomlabs-ai/headroom`](https://github.com/headroomlabs-ai/headroom)** | ~79,000 ⭐ | Context-window compressor: reduces JSON, tool outputs, and terminal logs by 60–95% before LLM consumption. |
| **[`IBM/mcp-context-forge`](https://github.com/IBM/mcp-context-forge)** | ~4,800 ⭐ | Enterprise AI Gateway and registry proxying MCP, REST, and Agent-to-Agent (A2A) endpoints. |
