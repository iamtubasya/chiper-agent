---
name: agent-web-api-integration
description: Integrating Chiper Agent with Web UIs (Open WebUI, LibreChat, Assistant-UI, Next.js) and consuming its OpenAI-compatible API Server and Web Dashboard.
category: software-development
---

# Agent Web UI & API Integration

Guide for connecting external Web UIs, frontends (Next.js, React, Open WebUI, LibreChat, Assistant-UI), and third-party applications to Chiper Agent via its built-in API Server and Web Dashboard.

---

## 1. Trigger Conditions

Load this skill when:
- Connecting an external web client (Open WebUI, LibreChat, Assistant-UI, ChatBox) to Chiper Agent.
- Building a custom web interface (Next.js, Vite, React, Vue) to interact with Chiper Agent.
- Operating or extending Chiper Agent's built-in API Server (`gateway/platforms/api_server.py`).
- Operating or embedding Chiper Agent's Web Dashboard (`chiper dashboard` / `web_server.py`).
- Consuming streaming chat completions, session lifecycle, or event streams from Chiper.

---

## 2. Chiper Agent Native Architecture

Chiper provides two core web gateways out of the box:

### A. The Web Dashboard (`chiper dashboard`)
- **Port:** `9119` (default: `http://127.0.0.1:9119`)
- **Engine:** FastAPI backend (`chiper_cli/web_server.py`) serving a compiled Vite/React frontend (`web/`).
- **Features:** Visual configuration editor, environment variable manager, multi-profile switcher, session browser, cron job scheduler, and terminal log viewer.
- **Commands:**
  ```bash
  chiper dashboard            # Start in foreground
  chiper dashboard --status   # Check running processes
  chiper dashboard --stop     # Stop running dashboard
  ```

### B. The OpenAI-Compatible API Server (`gateway/platforms/api_server.py`)
- **Port:** `8642` (default: `http://127.0.0.1:8642`)
- **Protocol:** Standard OpenAI Chat Completions + Responses API + Chiper Native Session Lineage.
- **Authentication:** `Authorization: Bearer <API_SERVER_KEY>` or `X-API-Key: <API_SERVER_KEY>`.
- **Supported Endpoints:**
  | Method | Endpoint | Description |
  | :--- | :--- | :--- |
  | `GET` | `/health` | Server health check |
  | `GET` | `/v1/models` | Lists `chiper-agent` as available model |
  | `POST` | `/v1/chat/completions` | Standard OpenAI chat completions (stateless or session-scoped) |
  | `POST` | `/v1/responses` | Stateful Responses API |
  | `GET` | `/api/sessions` | List visible Chiper sessions |
  | `POST` | `/api/sessions` | Create a new Chiper session |
  | `GET` | `/api/sessions/{id}/messages` | Get session transcript |
  | `POST` | `/api/sessions/{id}/chat/stream`| Direct SSE streaming session chat |
  | `POST` | `/v1/runs` | Async agent background runs with event stream (`/events`) |

---

## 3. Integration Patterns

### Pattern 1: Connecting Open WebUI to Chiper Agent
Chiper includes an automated setup script:
```bash
# Bootstrap Open WebUI connected to Chiper Agent
bash scripts/setup_open_webui.sh
```
Or configure manually in Open WebUI Settings:
- **Base URL:** `http://127.0.0.1:8642/v1`
- **API Key:** Value of `API_SERVER_KEY` in `~/.chiper/.env`
- **Model:** `chiper-agent`

### Pattern 2: Connecting Custom React / Next.js UI via Vercel AI SDK
```typescript
import { useChat } from "ai/react";

export function ChiperChat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "/api/chat", // Next.js Route Handler proxying to Chiper
  });

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto p-4">
      <div className="flex-1 overflow-y-auto space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`p-3 rounded-lg ${
              m.role === "user" ? "bg-cyan-600 text-white ml-auto" : "bg-zinc-800 text-zinc-100 mr-auto"
            }`}
          >
            {m.content}
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask Chiper Agent..."
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-white"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="bg-cyan-500 hover:bg-cyan-600 px-4 py-2 rounded text-black font-semibold"
        >
          Send
        </button>
      </form>
    </div>
  );
}
```

### Pattern 3: Next.js API Route Handler (`app/api/chat/route.ts`)
```typescript
import { OpenAIStream, StreamingTextResponse } from "ai";

export async function POST(req: Request) {
  const { messages } = await req.json();

  const response = await fetch("http://127.0.0.1:8642/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${process.env.CHIPER_API_KEY}`,
      // Pass session ID to maintain persistent Chiper memory
      "X-Chiper-Session-Id": "my-web-session",
    },
    body: JSON.stringify({
      model: "chiper-agent",
      messages,
      stream: true,
    }),
  });

  const stream = OpenAIStream(response);
  return new StreamingTextResponse(stream);
}
```

---

## 4. Verification & Testing

To verify API server availability and test a query from terminal:
```bash
# 1. Health check
curl -s http://127.0.0.1:8642/health | jq .

# 2. List available models
curl -s http://127.0.0.1:8642/v1/models -H "Authorization: Bearer test" | jq .

# 3. Simple completion test
curl -s http://127.0.0.1:8642/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{
    "model": "chiper-agent",
    "messages": [{"role": "user", "content": "Ping"}]
  }' | jq .
```
