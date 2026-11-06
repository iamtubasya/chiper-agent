# Source Map Analysis — Client-Side Source Code Extraction

## What It Is

JavaScript source maps (`.js.map`) leak original TypeScript/JS source code of production frontend apps. When deployed, they expose:
- Full authentication flow implementations (SRP, OAuth, TFA)
- Internal environment configs (staging/dev/trunk URLs)
- API endpoint structures and payload shapes
- Crypto material (public keys, salt sizes, parameters)
- Feature flags, reCAPTCHA site keys, analytics IDs
- Internal hostnames invisible from outside

## Finding Source Maps

1. **Fetch main HTML + JS bundles** and scan for `//# sourceMappingURL=` comments at end of `.js` files:
```bash
curl -s https://target/ | grep -oP 'src="[^"]+\.js"'
# then for each bundle:
curl -s https://target/assets/index-XXXX.js | tail -c 200 | grep sourceMappingURL
```

2. **Direct probe** of common map suffixes: append `.map` to JS URL (`index-XXXX.js.map`).

3. **Check HTML meta / link tags** — some frameworks declare maps there.

4. **Scan all JS assets on the page** (login, account, dashboard apps often have separate builds).

## Downloading and Parsing

```bash
# Download the map (can be very large — TeamViewer example was 8.3 MB)
curl -s -o app-index.js.map "https://target/Frontend/assets/index-XXXX.js.map"

# Parse: sources + sourcesContent arrays
python3 -c "
import json
with open('app-index.js.map') as f:
    data = json.load(f)
print('Total sources:', len(data['sources']))
for i, src in enumerate(data['sources']):
    if 'node_modules' not in src:
        print(f'[{i}] {src}')
"
```

Key JSON fields: `sources` (file paths), `sourcesContent` (original source code), `mappings`.

## Extracting Everything to Disk

```python
import json, os
with open('app-index.js.map') as f:
    data = json.load(f)
outdir = 'extracted_src'
os.makedirs(outdir, exist_ok=True)
for i, src in enumerate(data['sources']):
    if 'node_modules' not in src:  # skip third-party
        content = data['sourcesContent'][i]
        if content:
            fname = src.replace('../../src/', '').replace('/', '_')
            with open(f'{outdir}/{fname}', 'w') as out:
                out.write(content)
```

## What to Grep For in Extracted Sources

| Signal | Pattern |
|--------|---------|
| API endpoints | `/login/`, `/sso/`, `/config/`, `api.post(`, `api.get(` |
| Staging/dev URLs | `staging`, `dev.`, `rc.`, `trunk`, `playground` |
| Crypto material | `masterPublicKey`, `n:`, `e:`, `saltSize`, `keySize` |
| reCAPTCHA keys | `recaptchaSiteKey`, `invisibleRecaptchaSiteKey`, `6L[A-Za-z0-9_-]{38}` |
| Feature flags | `featureFlags`, `isTestMaster` |
| Auth flow | `authenticateaccountchallenge`, `setaccountlogintoken`, `checktfa` |
| Internal domains | `tvwebservices`, `internal.`, `.corp.`, `.local` |
| Analytics/tracking | `gtmId`, `adobeDtmUrl`, `launch-*.min.js` |

## Real-World Example (TeamViewer, 2026-09)

- Source map at `https://account.teamviewer.com/Frontend/assets/index-Bxyk2pl1.js.map`
- 180 TV-specific files exposed: SRP auth flow, AES-CBC encryption params, 16 environment configs
- Discovered: `web.us.teamviewer.com` (Azure, live), staging IPs (`trunk.web.tvwebservices.org` → 98.71.184.120), 10 reCAPTCHA keys, RSA master public keys per env, full SRP login API endpoint list

## Severity Assessment

- Source maps alone = **Info/Low** on most programs (client-side code is "public" in principle)
- Escalate severity only if map exposes: staging URLs that are actually live, secrets/API keys, undocumented admin endpoints, or materially aids an exploitable chain
- Always pair with follow-up probing of discovered hosts (test HTTPS, check for 401/403 vs 404 on API paths) before claiming impact

## Pitfalls

- Maps can be huge (5-10MB+) — don't paste into context, extract to disk and grep
- `sources` may contain hundreds of `node_modules` entries — filter these out first
- Some builds minify file names in `sources` — check `sourcesContent` directly if paths look opaque
- If HTTPS connection fails to staging hosts discovered (000/cert error), still note the IP — may be reachable via other protocols
