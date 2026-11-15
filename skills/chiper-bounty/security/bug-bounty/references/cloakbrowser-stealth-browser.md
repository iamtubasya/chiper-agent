# Reference: CloakBrowser — Stealth Chromium Alternative Browser (v1)

> Install check: `python <skill>/scripts/verify_cloakbrowser.py` (exit 0 = PASS: clean UA + webdriver off).

> Drop-in Playwright replacement with 73 source-level C++ stealth patches. Not a JS
> injection like playwright-stealth / undetected-chromedriver — fingerprints are patched
> at the Chromium binary level, so antibot systems see a real browser because it IS a
> real browser. GitHub: CloakHQ/cloakbrowser · PyPI: `cloakbrowser`.

---

## Install Status (this machine — verified 2026-09-10)

```
Wrapper:    0.5.10 (pip install cloakbrowser)
Python:     3.14.6, Windows AMD64
Binary:     v146.0.7680.177.5 (free tier) at $HOME/.cloakbrowser/chromium-146.0.7680.177.5/chrome.exe
GeoIP:      geoip2 installed (ready for geoip=True)
Verified:   launch OK — UA "Chrome/146.0.0.0" (no HeadlessChrome leak), navigator.webdriver=False
```

CLI management:
```bash
python -m cloakbrowser info      # diagnostics: binary, license tier, launch test
python -m cloakbrowser install   # pre-download binary
python -m cloakbrowser update    # check/download newer binary
python -m cloakbrowser clear-cache
```

## When To Use (vs Camofox/browser tool)

| Scenario | Use |
|---|---|
| Normal browsing, program pages, public extraction | `browser_navigate` (fast, built-in) |
| Browser tool CDP refused / port 9377 down | **CloakBrowser via Python** |
| Target behind Cloudflare Turnstile, FingerprintJS, reCAPTCHA v3, Kasada, ShieldSquare | **CloakBrowser** (Camofox fails these) |
| Login flow / session needed for API testing | CloakBrowser → export cookies → curl/requests |
| POC screenshots that must look human | CloakBrowser `humanize=True` + screenshot |
| Headless/docker-detection strict targets | CloakBrowser `headless=False` |

## Quick Launch

```python
from cloakbrowser import launch

# Basic stealth — zero config, random fingerprint seed at startup
browser = launch()

# Full anti-bot config for protected targets
browser = launch(
    proxy="http://user:pass@residential-proxy:port",  # residential IP, not datacenter
    geoip=True,          # auto timezone+locale from proxy IP (also spoofs WebRTC ICE)
    headless=False,      # some sites detect headless even with C++ patches
    humanize=True,       # Bézier mouse curves, per-char typing, realistic scroll
)
page = browser.new_page()
page.goto("https://target.com")
# ... standard Playwright API — new_context(), locator(), evaluate(), screenshot()
browser.close()
```

Other entry points:
```python
from cloakbrowser import launch_async, launch_context, launch_persistent_context

# browser+context in one call — reuse cookies/storage_state between runs
ctx = launch_context(storage_state="state.json")   # restore saved session
ctx.storage_state(path="state.json")               # save for next run

# persistent profile — cookies/localStorage survive restarts, bypasses incognito detection
ctx = launch_persistent_context("./my-profile", headless=False)
```

## Anti-Bot Pass Matrix (upstream, tested Aug 2026 vs Chromium 151)

| Detection | Stock Playwright | CloakBrowser |
|---|---|---|
| Cloudflare Turnstile (non-interactive + managed) | FAIL | **PASS** (auto / single click) |
| reCAPTCHA v3 score | 0.1 | **0.9** (Pro build; v146 free lower) |
| FingerprintJS bot detection | DETECTED | **PASS** |
| BrowserScan | DETECTED | **NORMAL (4/4)** |
| `navigator.webdriver` | true | **false** (source-level) |
| UA string | HeadlessChrome | **Chrome/146** (no headless leak) |
| TLS/ja3n/ja4 fingerprint | mismatch | **identical to Chrome** |
| CDP detection | Detected | **Not detected** |

## Bug Bounty Workflows

### 1. Auth behind Turnstile → API testing
```python
from cloakbrowser import launch
browser = launch(headless=False, humanize=True)
page = browser.new_page()
page.goto("https://target.com/login")
page.fill("#email", "user@example.com"); page.fill("#password", "...")
page.click("button[type=submit]")
page.wait_for_url("**/dashboard")
cookies = page.context.cookies()   # export session
import json; json.dump(cookies, open("session.json","w"))
browser.close()
# → replay authenticated endpoints via curl/requests (EVIDENCE: pair with actual output)
```

### 2. Screenshot POC on WAF'd target
```python
browser = launch(proxy="http://proxy:8080", geoip=True, headless=False, humanize=True)
page = browser.new_page(viewport={"width":1920,"height":1080})
page.goto("https://target.com/vulnerable-path")
page.screenshot(path="poc-full.png", full_page=True)
```

### 3. Custom fingerprint flags
```python
browser = launch(stealth_args=False, args=["--fingerprint=12345",
    "--fingerprint-webrtc-ip=1.2.3.4"])   # explicit WebRTC IP, no network call
```

### 4. Free key for latest v151 binary (1 concurrent session)
```bash
python -m cloakbrowser login      # GitHub sign-in → key saved to ~/.cloakbrowser/license.key
# or: export CLOAKBROWSER_LICENSE_KEY=cb_xxxxxxxx ; or launch(license_key="cb_...")
```

## SKIP Filters / Pitfalls

- **Puppeteer wrapper leaks CDP automation signals** → reCAPTCHA Enterprise intermittent 403. Use the **Playwright** wrapper for reCAPTCHA Enterprise targets (upstream documented limitation).
- **Doesn't solve CAPTCHAs — prevents them from appearing.** No CAPTCHA-solving, no proxy rotation built in. Bring your own residential proxies; pair with Boterdrop solver (`/turnstile`) only when a challenge still renders.
- **`geoip=True` makes an HTTP call through the proxy** (ipify/checkip) to resolve exit IP — do NOT use against targets where the proxy egress hitting ipify matters for opsec isolation; use explicit `timezone=`/`locale=`/`--fingerprint-webrtc-ip=` instead.
- **Binary is ~200MB, cached in `~/.cloakbrowser/`** — free v146 ages fast (detection evolves weekly); `python -m cloakbrowser update` before hard targets, or login for v151.
- **Some sites detect headless even patched** → `headless=False` (on this Windows box headed works fine).
- **1 concurrent session on free tier** — serialize launches or use Pro.
- Same-session fingerprints regenerate per launch unless `launch_persistent_context()` — for repeat-visit flows (warm accounts) use persistent profiles.

## Relation to Other Tooling

- `tool-failure-pitfalls.md` browser fallback → CloakBrowser is the scripted escape hatch when browser tool / Camofox (:9377) is down.
- Camofox = light stealth for scraping; **CloakBrowser = heavy stealth for anti-bot auth gates**. Escalate Camofox → CloakBrowser.
- Boterdrop solver still handles hard Turnstile/reCAPTCHA tokens; CloakBrowser reduces how often they appear.

---
Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
