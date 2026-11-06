# Discovering + probing an exposed LLM/RAG feature (fastapi + vector DB + JWT bearer)

Reusable recipe that surfaced an entire internal RAG chatbot (Bloom "Satori") from zero recon signal,
and mapped its auth in minutes. Apply to any target that might embed an AI/LLM feature.

## 1. Discover the AI surface from public docs/scanning
- `nuclei` `swagger-api` / `redoc-api-docs` templates caught `satori.bloomcredit.io/docs` +
  `/redoc` (fastapi auto-docs). `httpx` on `/openapi.json` (and `/api/openapi.json` for a second
  mounted app) returns the bare spec — chains of sub-apps each expose their own openapi.
- The openapi **description fields are the leak**: `/ready` said "Verifies docstore + Qdrant client…
  engine.load_storage_context_for_turn" → instantly identifies LlamaIndex + Qdrant (vector RAG) +
  an ingest pipeline. `/api/feedback` described "append as JSONL… AgentCore lane… mode REGULATORY |
  PROCEDURE | ANALYSIS | LOOKUP | REFUSAL | SELF_INFO".

## 2. Find the chat endpoint + auth model from the frontend bundle
- The SPA lives at `/chat` (React). Its minified bundle reveals the whole wiring:
  - fetch targets: `/api/chat`, `/api/chat-mcp/`, `/api/feedback`, `/api/health`
  - `localStorage` keys (minified) resolved to `satori:google_auth`, `satori:session_id`,
    `satori:profile`, `satori:eval_mode`, `satori:mcp_toggle` — `google_auth` = the bearer token source
  - Google Identity Services: `clientId = 2…apps.googleusercontent.com`, `hosted_domain = "bloomcredit.io"`
    (CLIENT-side only), `useOneTap`.
- Conclusion: bearer token = a Google ID token; `hosted_domain` is enforced only in the browser button,
  NOT necessarily server-side.

## 3. Probe the bearer endpoint to map the token validator (no creds needed)
POST `/api/chat` with crafted JWT headers and read the **differential error**:
- no token → `{"detail":"bearer token required"}`
- `garbage.token` → `{"detail":"malformed token"}`
- `alg:none` (no kid) → `{"detail":"token missing kid header"}`
- `alg:HS256` wrong secret / unknown kid → `{"detail":"token signing key not found"}`

This ordering (kid → key lookup → signature) proves proper JWKS signature verification (no alg:none
bypass). The REMAINING open question is whether the server also checks the `hd`/`aud` claims — that
split is exactly where a Broken Access Control / authz bug lives, and it is only provable with a real
ID token from a non-privileged account.

## Why this matters
An internal LLM/RAG assistant wrapped in a credit/finance domain is a high-value target: prompt
injection = PII/tradeline exfiltration, and a missing `hd` check = any Google account walks in. The
whole thing was reachable behind Cloudflare only through Playwright `ctx.request` (see
`bot-protected-target-testing` → `references/playwright-request-context-bypass.md`).