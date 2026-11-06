# Browser-Based Bugcrowd Access via computer_use

## When to Use
User provides Bugcrowd engagement URL + says they're already logged in via browser. Use `computer_use` to navigate the authenticated session and extract scope, targets, and rules.

## Workflow (Phase 0A Alternative)

### Step 1: Verify Browser Session
```
computer_use(action="list_windows")
→ Look for Chrome/Firefox with Bugcrowd tab
```

### Step 2: Navigate to Engagement
```
computer_use(action="focus_app", app="chrome", raise_window=True)
computer_use(action="key", keys="ctrl+l", delivery_mode="foreground")
computer_use(action="type", text="https://bugcrowd.com/engagements/...", delivery_mode="foreground")
computer_use(action="key", keys="return", delivery_mode="foreground")
computer_use(action="wait", seconds=3)
computer_use(action="capture", app="chrome", mode="vision")
```

### Step 3: Extract Scope
From the engagement page, extract:
- **Targets** (domains/IPs in scope)
- **Bounty tiers** (P1-P4 payouts)
- **Scope rating** (1-4)
- **Testing period** (start/end dates)
- **Safe harbor** (yes/no)
- **Known issues** (if listed)

### Step 4: Explore Target Dashboard
If target has a web dashboard (e.g., Magic Labs dashboard):
```
computer_use(action="key", keys="ctrl+l", delivery_mode="foreground")
computer_use(action="type", text="https://TARGET.com/dashboard", delivery_mode="foreground")
computer_use(action="key", keys="return", delivery_mode="foreground")
computer_use(action="capture", app="chrome", mode="som")
```

Explore: sidebar menu, settings, users, API keys, authentication config.

### Step 5: Extract API Endpoints via Network Tab
```
computer_use(action="key", keys="ctrl+shift+i", delivery_mode="foreground")
computer_use(action="capture", app="chrome", mode="som")
→ Click "Network" tab element
computer_use(action="key", keys="f5", delivery_mode="foreground")
computer_use(action="wait", seconds=3)
computer_use(action="capture", app="chrome", mode="vision")
```

Look for: XHR/Fetch requests, API base URLs, auth tokens in headers.

### Step 6: Check Application Tab for Tokens
```
→ Click "Application" tab in DevTools
→ Check Local Storage, Session Storage, Cookies
→ Note auth tokens, API keys, session IDs
```

## Pitfalls

| Issue | Fix |
|-------|-----|
| DevTools F12 doesn't open | Try `ctrl+shift+i` instead |
| Console command not executing | Click console input area first, then type |
| `hermes computer-use install` says "macOS-only" | Ignore — cua-driver may already be installed. Dependencies: `pip install mcp==2.0.0 httpx2==2.7.0 starlette==1.3.1` |
| computer_use action returns "session ended" | Re-capture with `computer_use(action="capture", mode="som")` to re-establish |
| Background input doesn't reach Chrome | Use `delivery_mode="foreground"` for Chrome DevTools and address bar |

## SPA Catch-All Detection
When checking if URLs return real content vs SPA shell:
```bash
ROOT_SIZE=$(curl -s "https://TARGET/" | wc -c)
PATH_SIZE=$(curl -s "https://TARGET/${PATH}" | wc -c)
[ "$ROOT_SIZE" = "$PATH_SIZE" ] && echo "SPA CATCH-ALL" || echo "REAL CONTENT"
```
Vercel/Next.js returns 200 + same HTML for ALL paths. Verify with Content-Type.

## Error Disclosure Pattern
When testing API endpoints, detailed error messages reveal backend stack:
- Python FastAPI/Pydantic: `{"detail":[{"type":"...", "loc":[...], "msg":"...", "input":...}]}`
- Reveals: language, framework, validation library
- Not a bounty finding alone, but aids further attacks

## Subdomain Takeover Detection
```
dig subdomain.target.com CNAME +short
curl -sI "https://subdomain.target.com" | head -5
```
Cloudflare error 1016 = "Origin server not configured" → potential takeover if DNS points to Cloudflare IPs with no active deployment.

## Related
→ Also read: `references/cors-multisubdomain-testing.md`
→ Also read: `references/tool-execution-pitfalls.md`
