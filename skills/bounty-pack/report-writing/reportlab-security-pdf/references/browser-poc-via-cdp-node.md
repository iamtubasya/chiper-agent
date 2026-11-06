# Browser-based PoC evidence via headless Chrome + CDP (Node.js)

Use when you must validate a client-side / in-browser security PoC (postMessage origin
bypass, DOM XSS, CORS, clickjacking, in-browser crypto, service worker, etc.) and the MCP
browser tools are unavailable (SeleniumBase MCP erroring, Camofox not running,
`browser_navigate` backend down). Do NOT record "browser tools are broken" as a standing
constraint — this is the working fallback, and the MCP layer may be fixed later.

## Launch headless Chrome with remote debugging
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" \
  --headless=new --remote-debugging-port=9222 \
  --user-data-dir=/c/tmp/chrome_poc --no-first-run --disable-gpu \
  "http://localhost:8899/poc.html"
```
Edge equivalent: `/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`.

Verify + enumerate targets (shows page AND every iframe with its origin — confirms
cross-origin frames actually loaded):
```bash
curl -s http://localhost:9222/json | python -c "import sys,json;[print(t['type'],t['url'],t['webSocketDebuggerUrl'][:60]) for t in json.load(sys.stdin)]"
```

## Minimal CDP driver (Node >= 22, built-in global WebSocket — zero deps)
```js
const http=require('http');
const targets=await new Promise((res,rej)=>http.get('http://localhost:9222/json',r=>{let b='';r.on('data',c=>b+=c);r.on('end',()=>res(JSON.parse(b)));}).on('error',rej));
const page=targets.find(t=>t.type==='page'&&t.url.includes('poc.html'));
const ws=new WebSocket(page.webSocketDebuggerUrl);
let id=0;const pending=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
const send=(method,params={})=>new Promise(r=>{const i=++id;pending.set(i,r);ws.send(JSON.stringify({id:i,method,params}));});
const evalJS=async expr=>(await send('Runtime.evaluate',{expression:expr,returnByValue:true})).result.result.value;
await new Promise(r=>ws.onopen=r);
await send('Runtime.enable');
// poll for the exploit effect, then capture evidence:
let out=await evalJS("JSON.stringify({hit:document.body.innerHTML.includes('PWNED')})");
const shot=await send('Page.captureScreenshot',{format:'png'});
require('fs').writeFileSync('evidence.png',Buffer.from(shot.result.data,'base64'));
```
Key methods: `Page.enable`, `Page.navigate`, `Page.reload{ignoreCache:true}` (keeps the
same page-target WS — good for re-running a PoC N times on one connection),
`Page.captureScreenshot`, `Runtime.evaluate`. For "validate 3x", loop
reload → re-arm the PoC → re-probe.

## Two-origin harness for cross-origin PoCs (postMessage / XSS)
One static server, two origins:
```bash
cd /c/tmp/poc && python -m http.server 8899 --bind 0.0.0.0
```
- Parent: `http://localhost:8899/poc.html` — loads the real target widget/lib under test.
- Attacker: `http://127.0.0.1:8899/attacker.html` — framed by the parent
  (`localhost` != `127.0.0.1` as origins).

Attacker does `parent.postMessage({...}, '*')`; observe the effect in the parent via
`Runtime.evaluate`. This proves a genuinely foreign origin's message is processed — far
stronger than dispatching a synthetic `MessageEvent` from the same origin.

## Windows path trap (execute_code vs bash)
Python `os.makedirs('/tmp/x')` writes to `C:/tmp/x`; git-bash `/tmp` is a DIFFERENT dir.
Serve from bash with `/c/tmp/...` and keep both tools on the same absolute path, or the
server 404s / `cd` fails silently.

## make_evidence.py prefix-filter pitfall
`scripts/make_evidence.py` keeps only lines matching its hardcoded PoC-output prefixes;
custom evidence text is mostly dropped and the PNG renders nearly empty (a 40-line file
came out 5 lines / 294px tall). Fixes, in order of preference:
1. Inline the evidence as a ``` code block in the report (legible, no image dependency).
2. Render with a small custom PIL monospace renderer (Consolas ~17px, pitch ~27,
   wrap ~118, width ~1600, colour-code RESULT/CONFIRMED/attacker lines).
3. Massage the text to match make_evidence.py's expected prefixes.

## Target-program status check — do this FIRST
Before any active testing, confirm the program is ACTIVE vs SUSPENDED. A target can
publish a full scope/rules PDF yet carry a banner like "temporarily suspending our bug
bounty program … reports submitted prior to <date> only", with every scope section tagged
"(applicable to prior reports)". Suspended = no active safe harbor = do NOT actively test;
clarify by email first. (Seen 2026-10: CDN77 suspended → held; SendSafely active → tested.)
Also check the submission channel: some programs mandate an encrypted in-product form and
explicitly forbid email submission — a Gmail draft addressed to such a target would
forfeit the reward + safe harbor, so stage the deliverable for the mandated channel.
