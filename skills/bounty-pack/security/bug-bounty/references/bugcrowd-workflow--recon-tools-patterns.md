# Recon Report Format & Tool Patterns

## Recon Report Template
```markdown
# [TARGET] RECON REPORT
**Date**: YYYY-MM-DD
**Target**: domain.tld
**Status**: Tier 1 Complete

## Executive Summary
- X subdomains discovered
- Y live hosts identified
- Key targets: [list]
- Tech stack: [list]

## Key Findings
### 1. Infrastructure
- WAF/CDN details
- Backend technology
- Frontend framework

### 2. Critical Targets
| Target | Status | Notes |
|--------|--------|-------|
| ... | ... | ... |

### 3. Attack Surface
- Categorized list of targets

### 4. Interesting Findings
- Notable integrations, endpoints, patterns

## Next Steps (Tier 2)
- Planned testing areas

## Tools Used
- Tool + version + result count

## Files Generated
- List of output files
```

## Tool Installation Patterns (Windows/MSYS)

### ProjectDiscovery Tools
```bash
# subfinder
curl -sL https://github.com/projectdiscovery/subfinder/releases/download/v2.6.7/subfinder_2.6.7_windows_amd64.zip -o subfinder.zip
unzip -o subfinder.zip -d subfinder_tmp
cp subfinder_tmp/subfinder.exe ~/.chiper/skills/bounty-pack/hermes-agent/venv/Scripts/

# nuclei
curl -sL https://github.com/projectdiscovery/nuclei/releases/download/v3.3.7/nuclei_3.3.7_windows_amd64.zip -o nuclei.zip
unzip -o nuclei.zip -d nuclei_tmp
cp nuclei_tmp/nuclei.exe ~/.chiper/skills/bounty-pack/hermes-agent/venv/Scripts/

# httpx (projectdiscovery) - naming conflict with Python httpx
curl -sL https://github.com/projectdiscovery/httpx/releases/download/v1.6.10/httpx_1.6.10_windows_amd64.zip -o httpx.zip
unzip -o httpx.zip -d httpx_tmp
cp httpx_tmp/httpx.exe ~/.chiper/skills/bounty-pack/hermes-agent/venv/Scripts/httpx-pd.exe
# NOTE: Use 'httpx-pd' to avoid conflict with Python httpx package
```

### SPA Internal API Discovery (HIGH VALUE)
SPAs bundle their API URLs in JavaScript. Extracting these reveals backend endpoints not visible from the frontend.

```bash
# Step 1: Find JS bundle files
curl -s "https://target.com" | grep -oE 'src="[^"]*\.js"' | sed 's/src="//;s/"//'

# Step 2: Extract ALL URLs from JS bundle (including internal APIs)
curl -s "https://target.com/assets/main.js" | grep -oE 'https?://[a-zA-Z0-9._/-]+' | sort -u > js_urls.txt

# Step 3: Filter for internal/service endpoints (exclude CDNs, analytics)
cat js_urls.txt | grep -E '\.(services|internal|api|backend)\.' | sort -u > internal_apis.txt

# Step 4: Check each endpoint for auth requirements
while read url; do
  status=$(curl -sI -o /dev/null -w "%{http_code}" --connect-timeout 3 "$url")
  echo "$status $url"
done < internal_apis.txt
```

**What to look for:**
- `.services.` subdomains → internal backend APIs (often less protected)
- `/api/` paths → REST endpoints
- `graphql` paths → GraphQL endpoints
- OAuth/OIDC metadata → `.well-known/oauth-authorization-server`

**Klaviyo Example:**
JS bundle at `reviews.klaviyo.com` exposed:
- `atlas-app.services.klaviyo.com/api/onsite/reviews/review-requests/`
- `reviews-app.services.klaviyo.com/api/video_upload/`
- `fast.a.klaviyo.com/reviews/api/client_reviews/`

These internal `.services.` endpoints had weaker auth than the public-facing app.

### OAuth/OIDC Metadata Discovery
```bash
# Standard OAuth metadata endpoints
curl -s "https://target.com/.well-known/oauth-authorization-server" | jq .
curl -s "https://target.com/.well-known/openid-configuration" | jq .

# MCP server discovery
curl -s "https://target.com/.well-known/mcp" | jq .
```

**What to look for:**
- `registration_endpoint` → Open client registration (potential vuln)
- `authorization_endpoint` → Auth flow (phishing vector)
- `token_endpoint` → Token exchange (brute force target)
- `code_challenge_methods_supported` → PKCE support
- `redirect_uris` → Open redirect potential

**Klaviyo Example:**
`mcp.klaviyo.com/.well-known/oauth-authorization-server` exposed:
- `registration_endpoint: /register` → Open client registration confirmed
- Accepted arbitrary `redirect_uri` → Authorization code theft possible

### Quick Recon Commands
```bash
# Subdomain enumeration
subfinder -d target.com -o subdomains.txt -silent

# Live host detection
httpx-pd.exe -l subdomains.txt -o live.txt -silent -status-code -title -tech-detect

# JS file extraction
curl -s "https://target.com" | grep -oE 'src="[^"]*\.js"'

# URL extraction from JS
curl -s "https://target.com/assets/main.js" | grep -oE 'https?://[^"'"'"' ]+' | sort -u

# Wayback machine
curl -s "https://web.archive.org/cdx/search/cdx?url=target.com/*&output=json&limit=100"
```

### Directory Structure
```
target-recon/
├── subdomains.txt      # All subdomains
├── live.txt           # Live hosts with status codes
├── targets.txt        # Clean URLs for testing
├── js_urls.txt        # JavaScript file URLs
└── js_analysis/       # Extracted URLs from JS files
    └── *_urls.txt
```

## Pitfalls
1. **httpx naming conflict**: Python httpx vs projectdiscovery httpx → use httpx-pd.exe
2. **Windows paths**: Use `/c/Users/...` format in MSYS/Git Bash
3. **Rate limiting**: Add delays between requests (3-5 seconds)
4. **Cloudflare protection**: Many targets use Cloudflare → expect 403s
5. **JS minification**: Grep patterns may miss minified URLs
