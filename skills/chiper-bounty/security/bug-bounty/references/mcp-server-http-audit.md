# Auditing MCP (Model Context Protocol) servers over HTTP/SSE

MCP servers are a new public attack surface: AI-agent tool backends, often shipped with weak or
no auth, frequently on forgotten subdomains (`mcp.*`, `mcp-docs.*`). This file is the driving
playbook. Worked case: `mcp.bytefederal.com` (Byte Federal engagement, 2026-10-20).

## Discovery

- Subdomain enum + httpx: `mcp.<target>`, `mcp-docs.<target>` (docs site often names the server
  and links its GitHub repo).
- Probe paths on any 404-at-root host: `/mcp`, `/sse`, `/message`, `/tools`, `/rpc`, `/health`.
  A **200 on `/sse` with `event: endpoint` / `data: /sse?sessionId=<uuid>`** = live SSE-transport
  MCP server. A JSON `{"error":"Not Found"}` on siblings = Express-style router (path-guessing works).
- WordPress sites: check `/wp-json/` root namespace list for `mcp` and
  `elementor-mcp-composer/*` — WP-internal MCP adapters (usually auth-gated; verify anyway).

## Driving the protocol (no client library needed)

```
1. GET  https://host/sse            (stream)  -> first "data:" line = message endpoint URI
                                                 e.g. /sse?sessionId=28d478ae-...
2. POST <URI>  {"jsonrpc":"2.0","id":1,"method":"initialize",
                "params":{"protocolVersion":"2025-03-26","capabilities":{},
                          "clientInfo":{"name":"probe","version":"1.0"}}}
3. POST <URI>  {"jsonrpc":"2.0","method":"notifications/initialized"}
4. POST <URI>  {"jsonrpc":"2.0","id":2,"method":"tools/list"}
5. POST <URI>  {"jsonrpc":"2.0","id":N,"method":"tools/call",
                "params":{"name":"<tool>","arguments":{...}}}
```

Pitfalls:
- The SSE `data:` line can be slow/flaky — retry the GET up to 4× with 2s sleeps before giving up.
- `serverInfo` in the initialize result names the server + version (fingerprint).
- `prompts/list`, `resources/list` → `-32601 Method not found` on tools-only servers (normal).
- The message URI is often `/sse?sessionId=...` — POST JSON-RPC there, NOT to `/message`.

## Test shapes per tool class

| Tool arg shape | Test |
|---|---|
| Sequential numeric ID (`atmId: number`) | Enumerate valid IDs; compare fields returned for valid vs invalid — look for INTERNAL-only fields (host names, cash levels, keys, internal notes). Invalid-ID empty + public-fields-only = verified negative, write it down. |
| Free-text location/search | Injection ladder: `' OR '1'='1`, `"; DROP TABLE x;--`, `../../etc/passwd`, `http://169.254.169.254/latest/meta-data` (SSRF via geocoder), `{{7*7}}` / `${7*7}` (SSTI). No reflection + no error differential = negative. |
| URL-fetching tools | Point at interactsh/burp collaborator → SSRF/OOB. |
| Anything "run/execute" | Treat as RCE candidate; check auth FIRST. |

## Session/auth checks

- **Cross-session posting**: open two SSE sessions (A, B); POST a `tools/call` to B's URI without
  initializing B. Works on stateless servers → note it, but if tools are public read-only data
  there is NO impact (verified-negative, don't report as a finding).
- **Random sessionId**: POST to `/sse?sessionId=00000000-...` — if the server answers, session
  IDs aren't validated at all. Same impact logic as above.
- If ANY tool mutates state or returns non-public data and the endpoint is unauthenticated →
  that IS the finding (broken access control on an AI tool backend).

## Reporting honesty

An unauthenticated MCP server serving public data is **by design** (public discovery tools exist).
Report only: (a) internal/non-public data exposed, (b) state mutation without auth, (c) injection
that produces reflection/errors/SSRF callbacks. Otherwise record the negative with the tool list.
