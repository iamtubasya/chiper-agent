# HackenProof Platform Workflow

**Platform:** hackenproof.com (now HackenProof by Hacken)
**Type:** Smart contract / blockchain bug bounty platform
**Dashboard:** dashboard.hackenproof.com
**Programs page:** hackenproof.com/programs (HTML-rendered, curl works)

## Platform Structure

HackenProof hosts smart contract / DeFi / blockchain bug bounty programs. Unlike Bugcrowd/Immunefi, the programs page is server-rendered HTML — `curl` + grep works for discovery.

## Program Discovery

### Method 1: Direct scrape of programs page (RECOMMENDED)
```bash
curl -s "https://hackenproof.com/programs" | grep -oP 'href="[^"]*"' | grep -i '/program/' | sort -u
```
Returns program slugs like `/program/cetus`, `/program/solana`, etc.

### Method 2: Search by keyword
```bash
curl -s "https://hackenproof.com/programs" | grep -i "PROGRAM_KEYWORD"
```

### Method 3: Direct program page (if slug is known)
```bash
curl -s "https://hackenproof.com/program/PROGRAM_SLUG"
```
Returns scope, rewards, rules.

## URL Patterns

| Page | URL |
|------|-----|
| All programs | `https://hackenproof.com/programs` |
| Specific program | `https://hackenproof.com/program/{slug}` |
| Dashboard (auth) | `https://dashboard.hackenproof.com` |

**Pitfall:** There is NO `/programs/{slug}` path — that redirects to the programs list. The correct path is `/program/{slug}` (singular).

## Scope Extraction

Program pages contain scope information in HTML. Extract with:
```bash
curl -s "https://hackenproof.com/program/PROGRAM_SLUG" | grep -i 'scope\|target\|asset\|url\|address'
```

For structured extraction, use Python with BeautifulSoup:
```python
from bs4 import BeautifulSoup
import requests
r = requests.get("https://hackenproof.com/program/PROGRAM_SLUG")
soup = BeautifulSoup(r.text, 'html.parser')
# Look for scope/target sections
```

## Key Platforms on HackenProof (known)

- **Cetus** — Move/Sui DEX (CLMM, concentrated liquidity) — scope: Move contracts
- **Solana ecosystem** — Various Solana programs
- **TON ecosystem** — TON contracts

**Note:** Cetus is ALSO on Immunefi. Cross-check both platforms for bounty details.

## Comparison with Other Platforms

| Feature | HackenProof | Bugcrowd | Immunefi | YesWeHack |
|---------|------------|----------|----------|-----------|
| Programs page | HTML (curl works) | React SPA (needs JS) | SPA (needs aggregator) | API (JSON) |
| API for discovery | None known | `/engagements.json` | None | `/v2/programs` |
| Primary focus | Smart contracts | Web/API + SC | DeFi/Web3 | General |
| Auth required for scope | No (public pages) | Yes (SPA) | Varies | No |

## Pitfalls

1. **URL confusion:** `/programs/{slug}` (WRONG) vs `/program/{slug}` (RIGHT, singular)
2. **No public API:** Unlike Bugcrowd's `engagements.json`, HackenProof has no known public API for program enumeration
3. **Camofox/browser failure:** If browser is down, `curl` + `grep` works fine for HackenProof (unlike Bugcrowd which needs JS rendering)
4. **Program verification:** Always check if a target is actually on HackenProof before deep-diving. Some targets may have been removed or moved to other platforms.
