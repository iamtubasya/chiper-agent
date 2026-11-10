# ChiperRouter — Architecture & 9router Clone Guide

Discovered and established during 9router to ChiperRouter refactoring (2026-11).

## Codebase Architecture
9router is packaged as an npm CLI wrapper around a compiled Next.js standalone server:
- `cli.js`: CLI entrypoint handling daemon lifecycle, interface menu (Web/Terminal UI), port kills, and background process spawning.
- `hooks/sqliteRuntime.js`: Checks and compiles/installs native `better-sqlite3` and `sql.js` into user data directory `runtime/node_modules/`.
- `app/`: Next.js standalone build.
  - `server.js` & `custom-server.js`: HTTP entrypoint running Next.js `startServer`.
  - `.next-cli-build/server/`: Server-side chunks, route cache (`.segment.rsc`, `.rsc`, `.html`).
  - `.next-cli-build/static/`: Client-side bundles (`chunks/`) and stylesheets (`css/`).

## Data Directory Override (`~/.chiperrouter`)
Next.js chunks check `process.env.DATA_DIR` before falling back to `~/.9router`:
1. In `cli.js`, `app/server.js`, and `app/custom-server.js`, prepend at the very top:
   ```javascript
   const os = require("os");
   const path = require("path");
   if (!process.env.DATA_DIR) {
     process.env.DATA_DIR = process.platform === "win32"
       ? path.join(process.env.APPDATA || "", "chiperrouter")
       : path.join(os.homedir(), ".chiperrouter");
   }
   ```
2. In `hooks/sqliteRuntime.js`, update fallback `getDataDir()` from `.9router` to `.chiperrouter`.

## Safe Text Refactoring Across Next.js Standalone Build
Do not attempt text replacement on binary assets (.node, .wasm, .woff2, .png, .ico).
Run Python script scanning for text files only:
```python
replacements = [
    (".9router", ".chiperrouter"),
    ("9ROUTER", "CHIPERROUTER"),
    ("9Router", "ChiperRouter"),
    ("9router", "chiperrouter"),
    ("https://9remote.cc", "https://github.com/iamtubasya/chiper-agent"),
    ("https://9english.net/", "https://chiper.site"),
    ("9Remote", "Chiper"),
    ("9English", "ChiperDocs"),
]
```
Ensure `package.json` updates `name: "chiperrouter"` and `bin: {"chiperrouter": "./cli.js"}` with author `Tubasya`.

## Preserving User State & Database Migration
Copy the data directory completely to avoid losing active provider connections:
```bash
mkdir -p ~/.chiperrouter
cp -a ~/.9router/* ~/.chiperrouter/
cp -a ~/.9router/.* ~/.chiperrouter/ 2>/dev/null || true
```
This preserves `db/data.sqlite`, machine ID, JWT secret, and compiled native SQLite binaries in `runtime/`.

## Cloudflare Tunnel API & DNS Routing Automation
To expose a new service port (e.g. port 20130 as `router.chiper.site`) via an existing Cloudflare Tunnel without needing `cloudflared` CLI login:

1. **Query Account, Zone, and Tunnel IDs via Cloudflare API v4**:
   ```bash
   # List zones
   curl -s -X GET "https://api.cloudflare.com/client/v4/zones" \
     -H "X-Auth-Email: <email>" -H "X-Auth-Key: <global_api_key>"
   # List tunnels
   curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/<account_id>/cfd_tunnel" \
     -H "X-Auth-Email: <email>" -H "X-Auth-Key: <global_api_key>"
   ```

2. **Update Remote Tunnel Ingress Configuration**:
   Fetch existing ingress rules, add the new route, and `PUT`:
   ```python
   import urllib.request, json

   url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations"
   payload = {
       "config": {
           "ingress": [
               {"hostname": "ssh.chiper.site", "service": "ssh://localhost:22"},
               {"hostname": "api.chiper.site", "service": "http://localhost:20128"},
               {"hostname": "router.chiper.site", "service": "http://localhost:20130"},
               {"service": "http_status:404"}
           ],
           "warp-routing": {"enabled": False}
       }
   }
   req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="PUT")
   urllib.request.urlopen(req)
   ```

3. **Create Proxied DNS CNAME Record**:
   ```python
   dns_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
   payload = {
       "type": "CNAME",
       "name": "router",
       "content": f"{tunnel_id}.cfargotunnel.com",
       "ttl": 1,
       "proxied": True
   }
   req = urllib.request.Request(dns_url, data=json.dumps(payload).encode(), headers=headers, method="POST")
   urllib.request.urlopen(req)
   ```

## Web UI Cyberpunk/Obsidian Redesign & Route Cache Patching
When redesigning Next.js standalone UI without source recompilation:

1. **Replace Brand Colors & Append Glassmorphism in `.next-cli-build/static/css/*.css`**:
   - Replace orange/coral palette (`#e56a4a` -> `#00f2fe`, `#cc5236` -> `#00c6ff`, `#fdfaf6` -> `#06080d`).
   - Append glassmorphic card surfaces (`rgba(14, 20, 32, 0.82)` with backdrop-filter blur), glowing neon borders, and gradient buttons.
   - Hide unwanted components cleanly via CSS (e.g. `button[aria-label="Donate"] { display: none !important; }`).

2. **CSS Selector Pitfalls in Compiled Tailwind / Next.js**:
   - **Attribute contains selector on compiled utility classes:** Never use broad substring selectors like `[class*="bg-surface"]` when Tailwind uses pseudo-class prefixes like `disabled:bg-surface-3`. The substring matches the disabled class on action buttons, causing buttons to unintentionally inherit the dark card background. Use targeted classes instead.
   - **Invalid pseudo-selectors:** Standard browser CSS engines reject rules containing non-standard jQuery-like pseudo-selectors such as `:contains(...)`. If an invalid selector is parsed, the browser drops the entire rule block. Use standard CSS selectors (`button[type="submit"]`, `form button`, `.btn-primary`).

3. **Prevent Light-Theme Flash via Route-Cache Patching**:
   Next.js prerenders initial HTML/RSC chunks into `.next-cli-build/server/route-cache/**/*.html` and `*.rsc`. If left unpatched, initial requests or hard refreshes will render light mode before client JS executes.
   Patch all cached route files:
   ```python
   import glob

   files = glob.glob('app/.next-cli-build/server/route-cache/**/*.{html,rsc}', recursive=True)
   for p in files:
       with open(p, 'r', encoding='utf-8', errors='ignore') as f:
           content = f.read()
       modified = False
       if '<html lang="en"' in content and 'class="dark"' not in content[:content.find('<body')]:
           content = content.replace('<html lang="en"', '<html lang="en" class="dark"')
           modified = True
       if ":'system'" in content:
           content = content.replace(":'system'", ":'dark'")
           modified = True
       if modified:
           with open(p, 'w', encoding='utf-8') as f:
               f.write(content)
   ```
4. Restart `systemctl --user restart chiperrouter` and verify visual design via `browser_vision`.

## Systemd User Service Integration & Dual-Port Setup (Coexistence)
To run both 9router (port 20128) and ChiperRouter (port 20130) simultaneously without conflict:
1. In `cli.js`, update default port: `const DEFAULT_PORT = 20130;`
2. Create/update `~/.config/systemd/user/chiperrouter.service`:
```ini
[Unit]
Description=ChiperRouter - LLM proxy dashboard (port 20130)
After=network-online.target

[Service]
Environment=PATH=%h/.local/bin:%h/.npm-global/bin:/usr/local/bin:/usr/bin:/bin
Environment=DATA_DIR=%h/.chiperrouter
Environment=PORT=20130
Environment=JWT_SECRET_FILE=%h/.chiperrouter/.jwt_secret
ExecStartPre=/bin/sh -c 'test -f %h/.chiperrouter/.jwt_secret || (umask 077 && openssl rand -hex 32 > %h/.chiperrouter/.jwt_secret)'
ExecStart=/usr/bin/script -qec "%h/.local/bin/chiperrouter -p 20130 --no-browser" /dev/null
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

**Crucial Systemd Pitfalls:**
- **No multiline env or unescaped quotes:** Never put bash logic into `Environment=`; use a dedicated `ExecStartPre=` line. Merging shell commands or newlines inside `Environment=` causes systemd `Invalid environment assignment, ignoring:` and `Unit has a bad unit file setting`.
- **TTY requirement:** The CLI expects a TTY for interface selection; running inside systemd requires `/usr/bin/script -qec "... --no-browser" /dev/null` to fake a pseudo-terminal.

Enable and verify:
```bash
systemctl --user daemon-reload
systemctl --user restart chiperrouter
curl -sI http://127.0.0.1:20130
curl -sI http://127.0.0.1:20128
```

## Git Repository & Clean Commits
In `~/chiperrouter`, create `.gitignore` before committing:
```
node_modules/
app/node_modules/
.next/
.next-cli-build/
*.log
.DS_Store
.env.local
.env*.local
```
Configure author identity and commit:
```bash
git config user.name "Tubasya"
git config user.email "tubasya@chiper.local"
git add .
git commit -m "feat: initial commit for ChiperRouter by Tubasya (port 20130)"
```
