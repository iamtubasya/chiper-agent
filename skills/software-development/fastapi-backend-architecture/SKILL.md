---
name: fastapi-backend-architecture
description: Production-grade REST API backend development with FastAPI, Pydantic v2 schemas, async lifespan, CORS, JWT/API key authentication, and streaming SSE.
category: software-development
---

# FastAPI Backend Architecture

Design and build robust, high-throughput REST APIs and WebSocket/SSE streaming services using FastAPI and Python 3.10+.

---

## 1. Trigger Conditions

Load this skill when:
- Creating or refactoring REST APIs using FastAPI or Starlette.
- Defining request/response contracts using Pydantic v2 `BaseModel` & `Field`.
- Implementing async lifespan management (`@asynccontextmanager`), DB connection pools, or background workers.
- Adding API authentication (Bearer JWT, API Key headers, OAuth2).
- Implementing streaming responses (Server-Sent Events / SSE, NDJSON, chunked transfer).
- Configuring CORS, rate limiting, and structured error handling.

---

## 2. Core Architecture Standards

### Application Structure & Lifespan
- **Use Async Lifespan:** Never use deprecated `@app.on_event("startup")` or `"shutdown"`. Use `@asynccontextmanager` with `FastAPI(lifespan=lifespan)`.
- **Clean Dependency Injection:** Use FastAPI `Depends()` for database sessions, authentication, and service locators. Never instantiate shared state globally inside route functions.
- **Async Safety:**
  - If a function performs I/O (database, network, file read), define it as `async def` and `await` non-blocking libraries (e.g., `httpx.AsyncClient`, `asyncpg`, `aiofiles`).
  - If calling a blocking synchronous library (e.g., CPU-bound computation or legacy sync SDK), either define the route as regular `def` (FastAPI automatically offloads it to a threadpool) or use `anyio.to_thread.run_sync()`. Never block the async event loop with `time.sleep()` or sync `requests.get()`.

### Pydantic v2 Schema Design
- **Separate Request & Response Models:**
  - Input: `UserCreateRequest` (strict validation, `min_length`, regex).
  - Output: `UserResponse` (`model_config = ConfigDict(from_attributes=True)`).
- **Explicit Field Constraints:** Always annotate fields with `Field(..., description="...", ge=..., le=...)`.
- **Zero Mutable Defaults:** Never use `tags: list = []`. Always use `tags: list[str] = Field(default_factory=list)`.

---

## 3. Production FastAPI Template

```python
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

logger = logging.getLogger("api")

# --- Schemas ---
class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model identifier")
    messages: list[dict[str, str]] = Field(..., min_length=1)
    stream: bool = Field(default=False)

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    content: str

# --- Security ---
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-API-Key header",
        )
    # Validate key hash / constant-time compare
    return api_key

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing API services & DB connections...")
    yield
    logger.info("Cleaning up connections...")

# --- Application ---
app = FastAPI(
    title="Chiper Core Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "chiper-agent-api"}

@app.post("/v1/chat/completions", tags=["Agent"])
async def create_chat_completion(
    payload: ChatCompletionRequest,
    _api_key: str = Depends(verify_api_key),
):
    if payload.stream:
        async def event_generator() -> AsyncGenerator[str, None]:
            tokens = ["Hello", " from", " Chiper", " Agent!"]
            for token in tokens:
                yield f"data: {{\"content\": \"{token}\"}}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    return ChatCompletionResponse(
        id="resp_123",
        content="Executed successfully.",
    )
```

---

## 4. Verification & Testing

Before declaring backend API work done:
1. **Automated Endpoint Testing:** Write test cases using `pytest` and `httpx.AsyncClient(app=app, base_url="http://test")`.
2. **OpenAPI Schema Check:** Verify `/docs` (Swagger UI) and `/openapi.json` load without validation errors.
3. **HTTP Status Code Verification:** Verify proper HTTP status codes (200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found, 422 Unprocessable Entity).
