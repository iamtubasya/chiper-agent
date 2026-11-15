# CloakBrowser Stealth Browser — Anti-Detection Bypass

## What It Does
CloakBrowser = stealth browser that bypasses bot detection (Cloudflare, DataDome, PerimeterX, Kasada).

## Why It Matters for Bug Bounty
Many targets use anti-bot protection. Standard curl/requests get blocked. CloakBrowser = bypass detection = test protected endpoints.

## Installation
```bash
git clone https://github.com/nicoreed/cloakbrowser
cd cloakbrowser
pip install -r requirements.txt
python setup.py install
```

## Usage
```python
from cloakbrowser import Browser

browser = Browser(headless=True)
browser.goto("https://target.com")

# Bypass Cloudflare challenge
browser.wait_for_cloudflare()

# Get page content (fully rendered)
content = browser.page_source

# Execute JavaScript
result = browser.execute_script("return document.cookie")

# Screenshot
browser.screenshot("evidence.png")
```

## Anti-Detection Features
```
- TLS fingerprint spoofing (Chrome/Firefox/Safari)
- JavaScript environment fingerprint masking
- WebGL canvas fingerprint randomization
- Screen resolution/viewport spoofing
- Timezone/locale spoofing
- WebDriver flag removal
- Navigator property override
```

## When To Use
```
USE CloakBrowser when:
✅ Target has Cloudflare/DataDome/PerimeterX
✅ Need to test authenticated endpoints behind WAF
✅ SPA requires JavaScript rendering
✅ Need realistic browser fingerprint for testing
✅ Standard requests/curl getting blocked

DON'T use CloakBrowser when:
❌ Simple curl works fine
❌ Target has no anti-bot protection
❌ Testing non-HTTP services
```

## Limitations
```
- Slower than curl (browser overhead)
- Resource intensive (RAM/CPU)
- May not bypass all anti-bot (evolving detection)
- Headless detection improving
- Some WAFs detect automation tools
```
