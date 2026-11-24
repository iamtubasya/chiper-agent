# Cloudflare Managed Challenge + Turnstile — Bypass Reality Check (2026)

Field notes from an engagement against a Cloudflare-fronted gambling domain (`lumbung88az.xyz`,
fake-TLD `.xyz`, NS on Cloudflare, origin fully hidden). **Result: full block.** These notes exist
so the next session doesn't burn an hour re-deriving the same dead ends.

## 1. Triage in 60 seconds — is it even Cloudflare?

```bash
curl -sSIL --max-time 20 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
  (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" https://TARGET/ | head -40
```

Key tells in the response:

| Header / field | Meaning |
|---|---|
| `cf-mitigated: challenge` | Managed Challenge, NOT a WAF block — a JS/Turnstile gate |
| `server: cloudflare` + `cf-ray: …-BKK` | Cloudflare edge; the suffix is the PoP answering you |
| `critical-ch: Sec-CH-UA-*` | Client-Hints negotiation — retrying with fuller headers is expected |
| `content-length: ~5500` + `<title>Just a moment...</title>` | Classic interstitial stub |
| `Tunggu sebentar...` / `Melakukan verifikasi keamanan` | **Indonesian managed-challenge variant.** Same gate, localized. |
| `content-length: ~44000` | **Different page** — the real orchestration shell, actually loads `turnstile/v0/api.js` |

`/robots.txt` frequently leaks through **unauthenticated (HTTP 200)** while `/` is 403. Harmless but
confirms hostname is live and tells you the operator enabled Cloudflare's "Managed robots.txt" /
AI-crawler content-signals feature — i.e. the CF zone is fully configured, not a half-baked freebie.

## 2. Origin IP discovery — what actually works and what didn't

Worked / partial:

```bash
# NS + A record (will be CF anycast — expected)
dig +short TARGET NS ; dig +short TARGET A

# crt.sh certificate transparency → subdomain enumeration
curl -s "https://crt.sh/?q=%25.TARGET&output=json" | python3 -c "
import json,sys
d=json.load(sys.stdin); s=set()
for e in d:
    for n in e['name_value'].split('\n'): s.add(n.strip().lower())
print('\n'.join(sorted(s)))"

subfinder -d TARGET -silent -all
```

All of the above returned **only** `*.TARGET` + apex. Wildcard cert, no leaked subdomains.

Dead ends observed:

- `curl "https://api.hackertarget.com/hostsearch/?q=TARGET"` → returned the CF anycast IP only.
- `rapiddns.io/subdomain/...` → empty.
- `urlscan.io/api/v1/search/?q=domain:TARGET` → `total: 0` (site too new / never scanned).
- `web.archive.org/cdx` → `429 Too Many Requests` almost immediately. Throttle hard or skip.
- CNAME chase on all common names (`www mail ftp direct origin cpanel webmail admin api dev staging
  test vpn ns1 ns2 mx blog promo panel backend db mysql static cdn img`) → only `www`, and that
  CNAME'd to a **Cloudflare SaaS fallback hostname** (`fallback.forinfour.com`) that itself resolves
  to CF anycast. That pattern = Cloudflare for SaaS / custom hostname product, not an origin leak.

Confirm whether an IP is really Cloudflare before wasting a scan:

```bash
curl -s https://ipinfo.io/$IP/json | grep -E '"org"|"country"|"city"'
# "org": "AS209242 Cloudflare London, LLC" + "anycast": true  → useless, it's the edge
```

### The one reliable non-CF signal: your own egress IP

```bash
curl -s https://ipinfo.io/json | grep -E '"ip"|"org"|"country"'
```

If you're on a cloud/datacenter ASN, Cloudflare's bot score is already poisoned before you send a
single byte. In this engagement egress was `43.152.233.82 / AS132203 Tencent / TH` — datacenter,
non-ID country, wrong client hints. **No amount of stealth patching fixes a bad IP reputation.**
Check this BEFORE building a Playwright pipeline. If it's datacenter, the answer is residential
proxy or hand the dump step to the user's own browser — do not grind on fingerprint patches.

## 3. Browser stealth — what we tried, what failed, and why

Environment: Playwright 1.x + Chromium, `xvfb-run` for headed mode on a headless VPS.

```bash
python3 -m venv venv && ./venv/bin/pip install playwright
export PLAYWRIGHT_BROWSERS_PATH=$HOME/.agent-browser/browsers   # reuse existing browser cache
./venv/bin/python -m playwright install chromium
xvfb-run -a --server-args="-screen 0 1440x900x24" ./venv/bin/python script.py
```

Attempts, in order of escalation — **all returned the challenge page indefinitely (40 iterations,
80 s):**

1. Headless + `--disable-blink-features=AutomationControlled` → stuck at `Tunggu sebentar...`.
2. Headed under xvfb → same.
3. `navigator.webdriver` delete + `window.chrome` stub + fake `plugins`/`languages` + WebGL
   `UNMASKED_VENDOR/RENDERER` spoof → same.
4. `is_mobile=False`, `has_touch=False`, `device_scale_factor=1`, `locale=id-ID`,
   `timezone_id=Asia/Jakarta`, `extra_http_headers` matching a real Chrome's `Accept-Language` → same.
5. Synthetic human mouse movement loop (`page.mouse.move` with jitter, 700 ms cadence) → same.

Diagnosis: the challenge page loads fine, JS executes, Turnstile API (`turnstile/v0/b/<id>/api.js`)
is fetched — but **no valid token ever gets issued**, because the risk assessment fails on IP
reputation, not on fingerprint. Verifiable by inspecting the saved HTML:

```bash
grep -oE "challenges\.cloudflare\.com[^\"']*|/cdn-cgi/challenge-platform[^\"']*" page.html | sort -u
```

## 4. The handoff pattern — when the VPS can't pass, let the user's browser do it

Don't dead-end. Two ways to salvage the engagement:

**(a) DevTools console dump in the user's own residential browser.** They open the site, pass the
challenge once, then paste a snippet that serialises the page. Deliver as JSON via clipboard +
Blob download so nothing is lost in chat truncation:

```javascript
(async () => {
  const out = {
    url: location.href, title: document.title, cookies: document.cookie,
    ls: Object.keys(localStorage).reduce((a,k)=>(a[k]=localStorage[k],a),{}),
    ss: Object.keys(sessionStorage).reduce((a,k)=>(a[k]=sessionStorage[k],a),{}),
    scripts: [...document.scripts].map(s=>s.src).filter(Boolean),
    links: [...document.querySelectorAll('a')].map(a=>a.href).slice(0,200),
    apiHints: performance.getEntriesByType('resource').map(r=>r.name)
      .filter(u=>/api|ajax|json|graphql/i.test(u)).slice(0,100),
    forms: [...document.forms].map(f=>({action:f.action,method:f.method,
      fields:[...f.elements].map(e=>e.name||e.id).filter(Boolean)})),
    htmlLen: document.documentElement.outerHTML.length
  };
  console.log(JSON.stringify(out,null,2));
  copy(JSON.stringify(out));
  const b=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);
  a.download='evidence.json';a.click();
})();
```

**(b) The prize from (a) is `cf_clearance`.** That cookie is bound to the **user-agent + IP** it was
minted for. Replaying it from the VPS fails unless you also spoof the UA and tunnel through the same
egress IP. Plan for this up front: ask the user for their UA string alongside the cookie dump, and
only then attempt `curl -b "cf_clearance=...; __cf_bm=..." -A "<exact UA>"`.

## 5. Things NOT to claim as findings

- The marketing counters on gambling/affiliate homepages ("Total Member: 12.483", "live deposit")
  are fabricated. Never report them as data.
- `cf_clearance` from your own datacenter session is worthless and short-lived (minutes–hours).
- A `403` with `cf-mitigated: challenge` is **not** evidence the target has no vulnerabilities; it's
  absence of access, not absence of bugs. Say "not reachable from this vantage point" and move on.

## 6. Fast decision tree

```
curl → 403 + cf-mitigated:challenge?
├─ no  → normal app testing, proceed
└─ yes → check own egress ASN (ipinfo.io/json)
     ├─ datacenter/cloud → STOP stealth grinding. Options:
     │     (i) residential proxy or solver API
     │     (ii) user-browser dump + cf_clearance handoff (with matching UA)
     │     (iii) pivot to passive intel only (crtsh/subfinder/robots/urlscan)
     └─ residential → stealth browser usually passes in <10 s
           then: enumerate /api/*, dump storage, look for stats endpoints
```
