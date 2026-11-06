# CDP-driven Chrome automation for Next.js apps behind Cloudflare

Purpose: drive a real, logged-in browser from Python when `browser_exec`/headless is
blocked or flaky, and to capture HttpOnly session cookies + Server-Action POST bodies
that curl/urllib can't reproduce (they 500 without proper action binding).

## Launch / ports

- Chrome debug profile per identity (isolated cookie jars) — critical for
  cross-tenant (IDOR/BOLA/priv-esc) testing:
  - Account A: port 9222, profile `qw-chrome-debug`
  - Account B: port 9223, profile `qw-chrome-debug2`
- Launch flags (profile cookies PERSIST across restarts — sessions survive):
  ```
  "C:/Program Files/Google/Chrome/Application/chrome.exe" \
    --remote-debugging-port=9222 --remote-allow-origins=* \
    --user-data-dir="$LOCALAPPDATA/Temp/qw-chrome-debug" \
    --no-first-run --no-default-browser-check about:blank
  ```
- `--remote-allow-origins=*` is REQUIRED or every websocket connect gets 403
  "Rejected an incoming WebSocket connection from the ... origin".
- If port is stuck: find holder `netstat -ano | grep ":9222" | grep LISTEN`,
  `taskkill //F //PID <pid>`. MSYS breaks double-slash args in places — prefer
  PowerShell `Stop-Process -Id <pid> -Force`.

## Connecting (websocket-client)

```python
import json, urllib.request, websocket
d = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=10))
pages = [t for t in d if t["type"] == "page"]
ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], header=["Origin: http://localhost"])

def cmd(method, params=None, mid=1):
    ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == mid:
            return m.get("result", {})
        if m.get("method") == "Network.requestWillBeSent":
            hook(m["params"]["request"])   # capture requests in-flight

def js(expr, mid=10):
    r = cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True}, mid=mid)
    if "exceptionDetails" in r: return {"err": r["exceptionDetails"].get("text", "")}
    return r.get("result", {}).get("value")
```

## Key operations

- **Get cookies (incl. HttpOnly)**: `Network.getAllCookies` → filter `domain` contains target.
  `document.cookie` never sees HttpOnly — use CDP only.
- **Navigate + wait**: `Page.navigate {url}` then sleep 4-6s; check `location.href`.
- **Fill forms**: set `value` + dispatch `input`/`change` + `form.requestSubmit()`
  (React/Next forms need proper events).
- **Multi-tab**: `Target.createTarget {url: "about:blank"}` for a second identity tab.
- **File upload (import/CSV/XSS-filename tests)**: `DOM.getDocument` → `DOM.querySelector`
  selector `input[type=file]` → `DOM.setFileInputFiles {nodeId, files:[abs_path]}`.
- **Full POST body capture**: `Network.getRequestPostData {requestId}` — `postData` in
  `requestWillBeSent` is truncated/absent for multipart; always use this.
- **TOTP login**: after enrolling authenticator, read the base32 secret from the page,
  generate RFC 6238 codes in Python (SHA1, 30s, 6 digits) and fill them in.

## Session-rotation / logout pattern

`Network.clearBrowserCookies` wipes a profile's session — reuse for testing whether a
lockout is per-account (persists) vs per-session (resets).

## Pitfalls

- Python `urllib` POSTs to Server-Action pages return 500 — they lack action binding.
  Browser-driven submissions are the source of truth. Capture the browser's own POST
  and replay THAT if you need a raw request.
- expression length: keep evaluate expressions short (< ~200 chars); browser harness
  truncates long async fetch probes.
- After `--remote-allow-origins=*` restarts, the old Chrome on the port may still answer
  with 403 — kill the stale holder and relaunch.