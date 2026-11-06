---
name: web2-recon
description: Web2 recon pipeline — subdomain enumeration (subfinder, Chaos API, assetfinder), live host discovery (dnsx, httpx), URL crawling (katana, waybackurls, gau), directory fuzzing (ffuf), JS analysis (LinkFinder, SecretFinder), continuous monitoring (new subdomain alerts, JS change detection, GitHub commit watch). Use when starting recon on any web2 target or when asked about asset discovery, subdomain enum, or attack surface mapping.
sources: community, public_research
---

# WEB2 RECON PIPELINE

Full asset discovery from nothing to a prioritized URL list ready for hunting.

> **Tech-org / internal-infra targets** (CI/CD, BI, per-developer envs behind one internal domain):
> read `references/tech-org-subdomain-expansion-and-iap.md` — `subfinder -all` vs CT-only gap,
> sibling-zone discovery via 302 redirects, IAP / Cloud-Armor / ACL fingerprinting, and the
> **"empty resolver output is NOT a negative"** pitfall (cross-check every NXDOMAIN).

---

## SETUP (one-time)

```bash
# 1. Set your Chaos API key (get free key at chaos.projectdiscovery.io)
export CHAOS_API_KEY="your-key-here"
# Add to ~/.zshrc or ~/.bashrc for persistence:
echo 'export CHAOS_API_KEY="your-key-here"' >> ~/.zshrc

# 2. Update nuclei templates (run weekly)
nuclei -update-templates

# 3. Configure subfinder with API keys for more sources
mkdir -p ~/.config/subfinder
cat > ~/.config/subfinder/config.yaml << 'EOF'
# Get free keys at: virustotal.com, securitytrails.com, censys.io, shodan.io
virustotal: [YOUR_VT_KEY]
securitytrails: [YOUR_ST_KEY]
censys_apiid: YOUR_CENSYS_ID
censys_secret: YOUR_CENSYS_SECRET
shodan: [YOUR_SHODAN_KEY]
EOF

# 4. Verify all tools installed
which subfinder httpx dnsx nuclei katana waybackurls gau dalfox ffuf anew gf interactsh-client
```

---

## THE 5-MINUTE RULE

> If a target shows nothing interesting after 5 minutes of recon, move on. Don't burn hours on dead surface.

**5-minute kill signals:**
- All subdomains return 403 or static marketing pages
- No API endpoints visible in URLs
- No JavaScript bundles with interesting endpoint paths
- nuclei returns 0 medium/high findings
- No forms, no authentication, no user data

---

## STANDARD RECON PIPELINE

### Pre-Hunt: Always Run First

```bash
TARGET="target.com"

# Step 0: Passive — crt.sh certificate transparency (no API key needed)
curl -s "https://crt.sh/?q=%.${TARGET}&output=json" \
  | jq -r '.[].name_value' \
  | sed 's/\*\.//g' \
  | sort -u > /tmp/subs.txt
echo "[+] crt.sh: $(wc -l < /tmp/subs.txt) subdomains"
```

> **Recon-to-finding shortcut (crt.sh step):** don't stop at *enumerating* names — **resolve them all
> and flag any public A record that answers with an RFC1918 address**, and grep served JS for
> internal/staging hostnames. On hardened targets this internal-infra disclosure is the highest-yield
> (low) finding. Full recipe + framing rules: `references/internal-infra-disclosure.md`. crt.sh query
> form matters — bare `?q=TARGET` works, `?q=%25.TARGET` sometimes 404s.
> **§4 of that reference is the higher-yield half:** run `subfinder -all` on the TECH-SUBSIDIARY domain
> in the background first thing (certspotter gave 85 names; `-all` gave 14,404), then walk the
> non-prod zones (`*.dev.*`, `*.test.*`, `cd.*`/`cd-test.*`, `*.dcc.*`) for CI/CD, BI and per-developer
> environments. It also has the control-recognition table (Google IAP vs Cloud-Armor 403 vs network ACL
> vs GCS AccessDenied — report the control, not a fake compromise), the sibling-domain-via-redirect
> trick, and the "never call NXDOMAIN from one resolver" rule.
# Step 1: Chaos API (ProjectDiscovery — most comprehensive source)
curl -s "https://dns.projectdiscovery.io/dns/$TARGET/subdomains" \
  -H "Authorization: $CHAOS_API_KEY" \
  | jq -r '.[]' >> /tmp/subs.txt

echo "[+] Chaos returned $(wc -l < /tmp/subs.txt) subdomains"

# Step 2: subfinder (passive multi-source)
subfinder -d $TARGET -silent | anew /tmp/subs.txt
assetfinder --subs-only $TARGET | anew /tmp/subs.txt

echo "[+] Total subdomains after all sources: $(wc -l < /tmp/subs.txt)"

# Step 3: DNS resolution + live host check
cat /tmp/subs.txt | dnsx -silent | httpx -silent -status-code -title -tech-detect | tee /tmp/live.txt

echo "[+] Live hosts: $(wc -l < /tmp/live.txt)"

# Step 4: URL crawl
cat /tmp/live.txt | awk '{print $1}' | katana -d 3 -jc -kf all -silent | anew /tmp/urls.txt

# Step 5: Historical URLs
echo $TARGET | waybackurls | anew /tmp/urls.txt
gau $TARGET --subs | anew /tmp/urls.txt

echo "[+] Total URLs: $(wc -l < /tmp/urls.txt)"

# Step 6: Nuclei scan
nuclei -l /tmp/live.txt -t ~/nuclei-templates/ -severity critical,high,medium -o /tmp/nuclei.txt
```

### ⛔ Step 7 (mandatory): re-diff the subdomain file before you close recon

`subfinder -all` on a large estate runs for **10–30+ minutes** in the background. If you built
`all-clean.txt` / `live-hosts.txt` from the *first* snapshot and then kept hunting, every name
subfinder added afterwards was **never resolved, never probed, never scanned** — and nothing warns
you, because your scan tools exited 0 on a list that was simply incomplete.

Measured on Deutsche Telekom (2026-10-29): the early snapshot was 93,423 names → `all-clean.txt`
83,639. The background `-all` run finished later at **118,176**. The delta was **3,202 names never
scanned**, which resolved to **594 hosts, 238 live** — a full recon round's worth of surface that
had been silently skipped while the engagement was being written up.

```bash
# after EVERY background subfinder/dnsx job reports "completed", before closing recon:
sort -u subs.txt | grep -v -E "$OOS_REGEX" > all-clean.txt
comm -13 <(sort -u scanned-hosts.txt) <(sort -u all-clean.txt) > new-subs.txt
wc -l new-subs.txt          # if > 0 you are NOT done — go scan them
dnsx -l new-subs.txt -silent -a -threads 200 -retry 1 -timeout 3 -o new-resolved.txt
cut -d' ' -f1 new-resolved.txt | sort -u > new-live-hosts.txt
httpx -l new-live-hosts.txt -silent -status-code -title -tech-detect -json -o new-live.jsonl
```

Rules:
1. **Keep a `scanned-hosts.txt` that the scan steps append to**, not just the raw subdomain file.
   Diffing against the raw file is what lets the gap hide.
2. **A background job completing is a recon event, not a notification.** Treat every
   `proc_… completed` notice on a recon command as a trigger to run Step 7.
3. **Never say "recon complete" while `new-subs.txt` is non-empty.** Say "recon complete at N names,
   delta M pending" instead.
4. The delta is cheap to close (one dnsx+httpx pass) and disproportionately valuable: freshly
   discovered names are the *least*-tested surface on the estate, so hit rate per host is highest
   there. On the Telekom delta this produced four verified negatives and one live Cognito pool that
   the earlier snapshot never saw.

### ⛔ `dnsx` output parsing — three ways it reports success while giving you nothing

`dnsx` is the tool most likely to hand you a silent zero. All three of these were hit in one
session (2026-10-29) and each produced a confident-but-wrong conclusion.

**1. `-resp` emits ANSI colour codes → your regex matches zero lines.**

```
api.padi.ng.telekom.net [^[[35mCNAME^[[0m] [^[[32md-2r6...amazonaws.com^[[0m]
```

A parse using `\[CNAME\]` returns **0 rows** while `wc -l` reports 730. I reported "730 CNAMEs
mapped" off the line count and the entire takeover analysis was built on nothing.

```bash
dnsx -l hosts.txt -silent -nc -cname -resp -retry 1 -o out.txt   # -nc = no colour, ALWAYS
```

If output is already coloured, strip before matching:
`re.sub(r'\x1b\[[0-9;]*m', '', line)`. **Never use `wc -l` as the parse-success signal** — print
`len(parsed_records)` and assert it is `> 0` before drawing any conclusion from it.

**2. `-cname` WITHOUT `-resp` gives hostnames only — no targets.** The output lists *which* hosts
have CNAMEs, not *what they point to*. Diffing that file against a `-resp` run revealed **242 hosts
whose CNAME targets had never been resolved** — the entire takeover sweep had been running on a
target-blind list. For any takeover/CNAME work you need `-cname -resp` together.

**3. `-retry 0` is rejected** — `[FTL] retries must be at least 1`, exit 1, **and no `-o` file is
written**. A missing output file plus exit 1 is an argument error, never "nothing found". Minimum is
`-retry 1`.

**Rule:** for every dnsx invocation whose output you will parse — `-nc`, `-retry 1`, assert the
parsed record count, and confirm the `-o` file exists before reading it. A bulk-DNS stage that
"returned nothing" is almost always one of these three, not an empty estate.

### Output to Organized Directory

```bash
TARGET="target.com"
RECON_DIR="recon/$TARGET"
mkdir -p $RECON_DIR

# All outputs go here:
/tmp/subs.txt         → $RECON_DIR/subdomains.txt
/tmp/live.txt         → $RECON_DIR/live-hosts.txt
/tmp/urls.txt         → $RECON_DIR/urls.txt
/tmp/nuclei.txt       → $RECON_DIR/nuclei.txt
```

---

## ATTACK SURFACE TRIAGE

### Find Interesting Targets in URL List

```bash
# Parameters worth testing
cat /tmp/urls.txt | grep -E "[?&](id|user|file|path|url|redirect|next|src|token|key|api_key)=" | tee /tmp/interesting-params.txt

# API endpoints
cat /tmp/urls.txt | grep -E "/api/|/v1/|/v2/|/v3/|/graphql|/rest/|/gql" | tee /tmp/api-endpoints.txt

# File upload endpoints
cat /tmp/urls.txt | grep -E "upload|file|attachment|document|image|avatar|photo|media" | tee /tmp/uploads.txt

# Admin/internal paths
cat /tmp/urls.txt | grep -E "/admin|/internal|/debug|/test|/staging|/dev|/management|/console" | tee /tmp/admin-paths.txt

# Authentication endpoints
cat /tmp/urls.txt | grep -E "/oauth|/login|/auth|/sso|/saml|/oidc|/callback|/token" | tee /tmp/auth-paths.txt
```

### gf Patterns (Quick Classification)

```bash
# Install gf patterns: https://github.com/tomnomnom/gf
cat /tmp/urls.txt | gf xss | tee /tmp/xss-candidates.txt
cat /tmp/urls.txt | gf ssrf | tee /tmp/ssrf-candidates.txt
cat /tmp/urls.txt | gf idor | tee /tmp/idor-candidates.txt
cat /tmp/urls.txt | gf sqli | tee /tmp/sqli-candidates.txt
cat /tmp/urls.txt | gf redirect | tee /tmp/redirect-candidates.txt
cat /tmp/urls.txt | gf lfi | tee /tmp/lfi-candidates.txt
cat /tmp/urls.txt | gf rce | tee /tmp/rce-candidates.txt
```

---

## JS ANALYSIS

### SecretFinder (API keys, tokens in JS bundles)

> **Triage the hits before believing any of them** — and before dismissing any of them. A grep hit is
> a string; a finding is a credential that authenticates against the provider *and* lacks its
> restriction. The expensive error is the **false negative**: a live Google Maps key was dismissed as
> a placeholder because the tool printed it as `AIzaSy...pVXo` — the `...` was output truncation, not
> data. Never judge a secret from a truncated string; print `len()` and the full value first.
> Classification table (real key vs minified identifier vs UI placeholder), the sibling-key negative
> control that makes provider verification trustworthy, the Referer-restriction probe, the
> `BEGIN OPENSSH PRIVATE KEY` placeholder trap, and honest Low/quota-billing scoring:
> `references/js-secret-triage-and-provider-verification.md`. Read it before writing up OR dropping
> any secret hit.

```bash
# Activate venv
source ~/tools/SecretFinder/.venv/bin/activate

# Scan a single JS file
python3 ~/tools/SecretFinder/SecretFinder.py -i "https://target.com/static/js/main.js" -o cli

# Scan all JS URLs found in recon
cat /tmp/urls.txt | grep "\.js$" | head -50 | while read url; do
  echo "=== $url ==="
  python3 ~/tools/SecretFinder/SecretFinder.py -i "$url" -o cli 2>/dev/null
done

deactivate
```

### LinkFinder (Endpoints hidden in JS)

```bash
source ~/tools/LinkFinder/.venv/bin/activate

# Single JS file
python3 ~/tools/LinkFinder/linkfinder.py -i "https://target.com/app.js" -o cli

# All pages (crawls JS from HTML)
python3 ~/tools/LinkFinder/linkfinder.py -i "https://target.com" -d -o cli

deactivate
```

---

## DNS-hijack preflight — RUN THIS FIRST on any home/ISP network

Verified 2026-10-12 (MyRepublic ID / AS63859). The ISP answers `*.duckduckgo.com`
with `158.140.186.3` (PTR `block.myrepublic.co.id`) — an IP that **blackholes on
:443**. Symptoms: `curl` returns `http=000` after a 12 s timeout, CloakBrowser
returns `ERR_CONNECTION_TIMED_OUT`, and recon Layer 1 silently reports **0 results**
(empty output = silent failure, not "no findings"). Bing / Google are unaffected,
so the bug looks intermittent. The system resolver is DHCP-configured, so you
**cannot** fix it by editing DNS settings.

```bash
PY314="C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe"
"$PY314" ~/AppData/Local/hermes/scripts/dnsfix.py     # prints HIJACKED / ok per host
```

`scripts/dnsfix.py` resolves the DoH truth (cloudflare-dns.com / dns.google) and
emits bypass flags. `dork-recon.py` imports it automatically and passes
`--host-resolver-rules=MAP host IP,...` to the stealth browser, so Layer 1 works
on a hijacked network with no manual steps.

### Two-layer diagnosis — `dnsfix.py --full` (hijack ≠ interception)

DNS hijack (wrong answer) and TCP interception (right answer, hijacked route) are
**different failures needing different fixes**. Verified 2026-10-12 on a Telkomsel
tethering link (Android hotspot, gateway `192.168.43.1`): the ISP answered with a
different IP *and* transparently proxied the TLS session to DDG's real IP — asking
for `SNI=example.com` against `20.43.161.105` returned `CN=*.duckduckgo.com`.
The certificate followed the **SNI**, not the IP — that is the tell.

```bash
PY314="C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe"
"$PY314" ~/AppData/Local/hermes/scripts/dnsfix.py            # layer 1 only
"$PY314" ~/AppData/Local/hermes/scripts/dnsfix.py --full     # layers 1+2 + verdict
```

Exit codes: `0` clean · `1` DNS hijack only · `2` hijack **+** TCP interception.

| Result | Meaning | What actually works |
|---|---|---|
| hijack only | DoH truth ≠ system answer | DoH + `--host-resolver-rules` / `curl --resolve` **fully repairs** it |
| hijack + interception | TLS session hijacked too | **DoH alone is NOT enough** — use the browser path (Camoufox Firefox-DoH, or CloakBrowser with `--host-resolver-rules`), which pins the IP and validates the session |

**Pitfall — do not diagnose with plain `curl` on a hostile link.** On a
two-layer link (Telkomsel hotspot), bare `curl` fails even *with* `--doh-url` or
`--resolve`, because TCP to the real IP is intercepted. A failed bare `curl` is
therefore **not** evidence that the pipeline is broken — check
`dnsfix.py --full` first and test the browser path before concluding anything.
`INCONCLUSIVE` (TLS never completed) must never be reported as "ok".

**Second, independent blocker:** `html.duckduckgo.com/html/?q=` now returns a bot
challenge (**HTTP 202** + `anomaly`/`challenge` in the body) *even from a clean IP*.
The working path is the JS app — `https://duckduckgo.com/?q=...` with a 4 s wait
(`ddg-js` engine in `dork-recon.py`). Keep `html` as a cheap first probe, fall
through to `ddg-js`, then Bing.

### Non-admin global fix — `sitecustomize.py` DoH patch (repairs EVERY python tool)

The hosts file needs elevation (`Permission denied` from the agent shell), and the
adapter is DHCP-controlled — so the *persistent, no-admin* fix for python-based tools
is a resolver monkeypatch at
`<Python314>/Lib/site-packages/sitecustomize.py` (create only if absent):

- It wraps `socket.getaddrinfo` **for a small `HIJACKED_HOSTS` set only** (the DDG
  family): DoH lookup (cloudflare-dns.com) + TTL cache → pin real IP; any DoH failure
  falls back to the original resolver (fail-open, zero change for every other host).
- `sitecustomize` auto-loads at interpreter start → covers **ddgs (hermes
  web_search / web_extract), requests, urllib** — everything python, not just one tool.
- **Activation: restart the gateway** (long-running processes don't reload it).
  **Disable: rename** `sitecustomize.py` → `sitecustomize.off` — no file edit needed.
- Verified end-to-end: system resolve → real DoH IPs, `ddgs.text()` returns results
  on a hijacked link; `example.com` and other hosts untouched.
- Keep the host set surgical. Never make the patch generic — a broad getaddrinfo
  wrapper becomes an invisible single point of failure for all python networking.

## Parallel dorking without paying — `dork-pool.py`

CloakBrowser's free tier is **1 concurrent session** (paid: $19/mo = 5, $49/mo = 20,
$199/mo = 200, $499/mo = 2000; 3-day trial, 5 sessions, no card). For bulk dorking
you don't need to pay — fan out across **Camoufox workers** (free, unbounded), each
with its own DNS bypass:

- **Camoufox** → Firefox-native DoH (`network.trr.mode=3`, `network.trr.uri=
  https://cloudflare-dns.com/dns-query`). This is *cleaner* than Chromium IP-pinning
  and returns **20 results** on `ddg-html` (vs ~10 on CloakBrowser).
- **CloakBrowser** (`--premium`) → Chromium `--host-resolver-rules` MAP, kept as the
  single premium worker for the hardest targets.

```bash
PY314="C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe"
cd ~/AppData/Local/hermes/scripts
"$PY314" dork-pool.py --target target.com                     # auto workers from free RAM
"$PY314" dork-pool.py --target target.com --workers 3 --premium
"$PY314" dork-pool.py --target target.com --queries dorks.txt --out ./dp
```

**RAM guard is built in** (this host = 6 GB, ~0.6 GB per Camoufox node): `--workers 0`
auto-sizes from free RAM; requesting too many is clamped with a warning
(`--force-workers` overrides). Verified: 3 workers → 51 URLs; auto → 62 URLs, all
parallel, no key.

## Per-category dork generation — `dorkgen.py`

The flat dork list is replaced by **11 categories**, so an agent can hand the
operator a clean per-category worklist instead of one soup of 300 queries:

```bash
PY314="C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe"
cd ~/AppData/Local/hermes/scripts
"$PY314" dorkgen.py --list-cats                                  # 11 cats, 61 dorks
"$PY314" dorkgen.py --target target.com --format md              # human list
"$PY314" dorkgen.py --target target.com --format json --out d.json
"$PY314" dorkgen.py --target target.com --format per-cat --out ./dorks/
"$PY314" dorkgen.py --target target.com --cats exposed_files,admin_panels,api_keys
```

Categories: `exposed_files` · `admin_panels` · `api_keys` · `api_surface` ·
`dir_listing` · `auth_flows` · `uploads` · `errors_debug` · `params_juicy` ·
`web3_infra` · `source_leak`.

## web3 targets — hunt the WEB2 infra, not just the contract

The contracts get audited; the money leaks from the infra around them. Container
**free** tooling (no Shodan/FOFA/ZoomEye key needed, so it works on this box):

```bash
"$PY314" ~/AppData/Local/hermes/scripts/web3-infra-recon.py \
    --target project.xyz --out ./web3-recon
"$PY314" web3-infra-recon.py --target project.xyz --rpc https://rpc.project.xyz
```

Stages: (1) subdomain enum (subfinder + crt.sh) → httpx live; (2) concurrent probe
of a web3-flavoured infra wordlist — dashboard / rpc / jsonrpc / subgraph / indexer /
faucet / bridge / explorer / api/v1-v3 / metrics / .env / .git/config; (3) **RPC
namespace probe** — `eth_accounts`, `admin_peers`, `admin_nodeInfo`, `txpool_status`,
`rpc_modules`, `personal_listAccounts` (an open `admin_*` or `eth_accounts` is
Critical/High); (4) GraphQL/subgraph introspection; (5) JS-bundle secret scan
(`RPC_URL`, INFURA/ALCHEMY/QUICKNODE keys, WalletConnect id, `PRIVATE_KEY`,
`MNEMONIC`); (6) web3-infra dorks via `dorkgen.py`. Outputs `report.json` with a
pre-severity `findings` array.

Real run against `dexe.network`: 22 subdomains → 16 live (found
`sale.dexe.network` = "DeXe Explorer" on CloudFront/S3, plus `test34.dexe.network`
exposing a full DAO-management UI). RPC/graphql correctly came back empty.

## DIRECTORY FUZZING — ffuf

### ffuf — Standard Fuzzing

```bash
# Directory discovery on a live host
ffuf -u "https://target.com/FUZZ" \
     -w ~/wordlists/common.txt \
     -mc 200,201,204,301,302,307,401,403 \
     -ac \
     -t 40 \
     -o /tmp/ffuf-dirs.json

# API endpoint discovery
ffuf -u "https://target.com/api/FUZZ" \
     -w ~/wordlists/api-endpoints.txt \
     -mc 200,201,204,301,302 \
     -ac \
     -t 20

# IDOR fuzzing with authenticated request
# Create req.txt with Authorization: Bearer TOKEN
ffuf -request /tmp/req.txt \
     -request-proto https \
     -w <(seq 1 10000) \
     -fc 404 \
     -ac \
     -t 10
```

### ffuf invocation traps (verified 2026-10-16, bluewin.ch deep-dive)

- **Two `-w` flags + one `FUZZ` placeholder = garbage results.**
  `-u …/FUZZ -w wl1 -w wl2` came back with every match URL stuck on a single word
  (`/actuator` / `/actuator/health` repeated once per wordlist line — 9,504 "matches"
  that were really two URLs, produced on both a Spring and a Java target). The run
  *looks* healthy (4 req/s, 0 errors) and only the URL column gives it away. Merge
  wordlists into one deduped file first, pass a single `-w`.
- **Calibrate before the big run.** Same `-u`/flags against a ~100-word slice, *without*
  `-s`, and read the banner (`:: Progress: [N/M] :: 4 req/sec :: Errors: 0`) — proves
  rate, timeouts and URL templating in ~30 s before committing a 4,945-word × 4-host job.
- **Don't run long jobs fully silent.** With `-s` you cannot tell "slow" from "stuck";
  keep the progress banner (or drop `-s` and tail the background log). Add
  `-maxtime <sec>` — it force-ends the run *and still writes the `-o` JSON*
  (`Maximum running time for entire process reached, exiting`); without it a stuck run
  leaves no file at all, and a file written by maxtime is **partial coverage** — check
  the run log for that line before claiming the wordlist was fully tested.
- **Catch-all triage:** cluster matches by `(status, length)` before fetching anything —
  105 matches all `(200, 487B)` = SPA shell catch-all, zero findings; only unique
  clusters deserve a fetch. Same rule as the impact-verifier body-prefix check
  (`bb-audit-launcher` → `references/pipeline-invocation-traps.md` trap #15).

---

## TARGET SCORING — GO / NO-GO

Score before spending time. Skip if score < 4.

| Criterion | Points |
|---|---|
| Max bounty >= $5K | +2 |
| Large user base (>100K) or handles money | +2 |
| Program launched < 60 days ago | +2 |
| Complex features: API, OAuth, file upload, GraphQL | +1 |
| Recent code/feature changes (GitHub, changelog) | +1 |
| Private program (less competition) | +1 |
| Tech stack you know | +1 |
| Source code available | +1 |
| Prior disclosed reports to study | +1 |

**< 4:** Skip
**4-5:** Only if nothing better available
**6-8:** Good — spend 1-3 days
**>= 9:** Excellent — spend up to 1 week

### Pre-Dive Hard Kill Signals

1. Max bounty < $500 → not worth your time
2. All recent reports are N/A or duplicate → hunters saturated it
3. Scope is only a static marketing page → no attack surface
4. Company < 5 employees with no revenue → won't pay
5. Explicitly excludes your planned bug class in rules

---

## TECH STACK DETECTION (2 min)

```bash
# Response headers reveal backend
curl -sI https://target.com | grep -iE "server|x-powered-by|x-aspnet|x-runtime|x-generator"

# Common signals:
# Server: nginx + X-Powered-By: PHP/7.4 → PHP backend
# Server: gunicorn OR X-Powered-By: Express → Python/Node.js
# X-Powered-By: ASP.NET → .NET
# Server: Apache Tomcat → Java
# X-Runtime: Ruby → Ruby on Rails

# Framework from JS bundle paths:
# /_next/static/ → Next.js
# /static/js/main.chunk.js → CRA (React)
# /packs/ → Ruby on Rails + Webpacker
# /__nuxt/ → Nuxt.js (Vue)
```

### Stack → Primary Bug Class Map

| Stack | Hunt First | Hunt Second |
|---|---|---|
| Ruby on Rails | Mass assignment | IDOR (`:id` routes) |
| Django | IDOR (ModelViewSet, no object perms) | SSTI (mark_safe) |
| Flask | SSTI (render_template_string) | SSRF (requests lib) |
| Laravel | Mass assignment ($fillable) | IDOR (Eloquent, no ownership) |
| Express (Node.js) | Prototype pollution | Path traversal |
| Spring Boot | Actuator endpoints (/actuator/env) | SSTI (Thymeleaf) |
| ASP.NET | ViewState deserialization | Open redirect (ReturnUrl) |
| Next.js | SSRF via Server Actions | Open redirect via redirect() |
| GraphQL | Introspection → auth bypass on mutations | IDOR via node(id:) |
| WordPress | Plugin SQLi | REST API auth bypass |

---

## CONTINUOUS MONITORING SETUP

Set up once per target. Alerts you before other hunters.

### New Subdomain Alerts (daily cron)

```bash
#!/bin/bash
TARGET="target.com"
KNOWN="/tmp/$TARGET-subs-known.txt"

subfinder -d $TARGET -silent > /tmp/$TARGET-subs-fresh.txt
curl -s "https://dns.projectdiscovery.io/dns/$TARGET/subdomains" \
  -H "Authorization: $CHAOS_API_KEY" \
  | jq -r '.[]' >> /tmp/$TARGET-subs-fresh.txt

# Diff against known
NEW=$(comm -23 <(sort /tmp/$TARGET-subs-fresh.txt) <(sort $KNOWN 2>/dev/null))

if [ -n "$NEW" ]; then
  echo "NEW SUBDOMAINS: $NEW"
  echo "$NEW" >> $KNOWN
fi

# Schedule: crontab -e → 0 8 * * * /bin/bash ~/monitors/subs-watch.sh
```

### GitHub Commit Watch

```bash
#!/bin/bash
REPO="TargetOrg/target-app"
LAST_SHA="/tmp/$REPO-last-sha.txt"

CURRENT=$(curl -s "https://api.github.com/repos/$REPO/commits?per_page=1" | jq -r '.[0].sha')
KNOWN=$(cat $LAST_SHA 2>/dev/null)

if [ "$CURRENT" != "$KNOWN" ]; then
  echo "New commit on $REPO: $CURRENT"
  echo $CURRENT > $LAST_SHA
  # Get changed files
  curl -s "https://api.github.com/repos/$REPO/commits/$CURRENT" \
    | jq -r '.files[].filename' | grep -E "auth|middleware|route|permission|role|admin"
fi

# Schedule: */30 * * * * /bin/bash ~/monitors/github-watch.sh
```

---

## PORT SCANNING (often skipped — don't skip)

```bash
# naabu — fast port scanner from ProjectDiscovery
# Finds non-standard ports: 8080, 8443, 3000, 8888, 9000, etc.
cat /tmp/live.txt | awk '{print $1}' | naabu -port 80,443,8080,8443,3000,4000,5000,8000,8888,9000,9090,9200,6379 -silent | tee /tmp/open-ports.txt

# Why this matters: admin panels, debug services, internal APIs often run on alt ports
# Example wins: :8080/actuator/env (Spring Boot), :9200/_cat/indices (Elasticsearch), :6379 (Redis)
```

## SECRET SCANNING IN JS BUNDLES

```bash
# trufflehog — high-signal secret detection with entropy analysis
# Scans JS files and git repos
pip install trufflehog3 2>/dev/null || true
trufflehog filesystem --only-verified recon/$TARGET/ 2>/dev/null

# SecretFinder — manual JS bundle scan (already in tools/)
source ~/tools/SecretFinder/.venv/bin/activate
cat /tmp/urls.txt | grep "\.js$" | head -100 | while read url; do
  python3 ~/tools/SecretFinder/SecretFinder.py -i "$url" -o cli 2>/dev/null
done
deactivate

# Quick grep for common patterns in downloaded JS
wget -q -r -l 1 -A "*.js" -P /tmp/js-files/ "https://$TARGET" 2>/dev/null
grep -rn "api_key\|apiKey\|client_secret\|access_token\|private_key\|AWS_SECRET\|AKIA" /tmp/js-files/ 2>/dev/null
```

### ⛔ A found key is a HYPOTHESIS until you call the provider with it

**The miss this section exists to prevent (Telekom, 2026-10-29):** a sweep produced 113 secret hits.
At triage the Google keys displayed as `AIzaSy...rZxU` — and they were dismissed as placeholders
in three consecutive summaries. They were not placeholders. The `...` was **the agent's own display
truncation**, not the key's content. One of them (`AIzaSyDo7W8bpq…`, 39 chars, from
`b2b-europe.telekom.com/fileadmin/template/Public/js/myscript.js`) authenticated against live
Google Cloud project **291523791773** with Geocoding enabled and **no referrer restriction**. That
was a real reportable finding, discovered only because a later pass stopped trusting the display.

**Rules**

1. **Never judge a secret from a truncated rendering.** Print `len(value)`, the first 6 and last 4
   chars, and `re.match(provider_pattern)` — never a bare `value[:12]+"..."`. If your own tooling
   abbreviates, you cannot tell a placeholder from a live credential. Re-read the raw JSONL.
2. **Match the provider's real format before calling it a placeholder.** Google API keys are
   `AIza` + 35 chars = **39 total**; AWS access key IDs are `AKIA`/`ASIA` + 16 = 20; Stripe live
   secret keys are `sk_live_` + 24+. If the length matches the pattern, it is a candidate, full stop.
3. **Call the provider.** A pattern match proves nothing; a `200` with real data proves the key is
   live. Pick the cheapest read-only endpoint that returns data (Maps Geocode, GitHub `/user`,
   Stripe `/v1/balance`, SendGrid `/v3/scopes`). Never call a *billable* or *mutating* endpoint to
   satisfy curiosity.
4. **Test the restriction, not just liveness.** For browser keys the finding is the *missing*
   control. Replay the same request with (a) no `Referer`, (b) `Referer: https://evil.example/`,
   (c) `Referer: https://attacker.test/`. All three succeeding = referrer-unrestricted =
   the actual defect. A restricted key answers `REQUEST_DENIED — Requests from referrer … are blocked`.
5. **Use the estate's other keys as the negative control.** Two other Google keys from the same
   sweep returned `REQUEST_DENIED — This API is not activated on your API project`. That control is
   what converts "the endpoint responded nicely" into "this specific key is genuinely authorised":
   it proves the request is well-formed and that project-level enablement — not a permissive default
   — is what made the hit succeed. Without it a `200` is unfalsifiable.
6. **Classify what you actually got.** A live unrestricted key = configuration defect, **Low**
   (quota/billing exposure, bounded by the provider's daily cap). It is *not* a data breach and
   grants no system access. Say which is proven and which is reasoned; do **not** exhaust quota to
   "demonstrate impact" — that degrades a live service and violates most RoE.
7. **Private keys need a different bar.** `-----BEGIN OPENSSH PRIVATE KEY-----` in a bundle is
   usually a **placeholder string in an input field's help text** (Yopass/Coder-style UIs ship the
   literal header as a form hint). Check the surrounding context before raising it; a bare header
   token with no base64 body is a placeholder by definition.

Full provider-by-provider verification recipes, the exact request shapes, and the "is it live /
is it restricted / what does it prove" matrix:
`references/js-secret-triage-and-provider-verification.md`.

## GITHUB DORKING FOR TARGET

```bash
# Search GitHub for hardcoded secrets before hunting the app
TARGET_ORG="TargetOrgName"  # Check their GitHub org

# Useful dorks (search on github.com):
# org:TARGET_ORG password
# org:TARGET_ORG api_key
# org:TARGET_ORG "Authorization: Bearer"
# org:TARGET_ORG .env
# org:TARGET_ORG "BEGIN RSA PRIVATE KEY"

# CLI with gh (GitHub CLI):
gh search code "api_key" --owner "$TARGET_ORG" --json path,repository 2>/dev/null | jq '.'
gh search code "password" --owner "$TARGET_ORG" --json path,repository 2>/dev/null | head -20

# GitDorker (if installed):
python3 ~/tools/GitDorker/GitDorker.py -t GITHUB_TOKEN -d ~/tools/GitDorker/Dorks/alldorksv3 -q "$TARGET" -org
```

## 30-MINUTE RECON PROTOCOL

### Minutes 0-5: Read Program Page

```
Note:
- ALL in-scope assets (every domain listed)
- Out-of-scope list (read carefully — common trap)
- Safe harbor statement
- Impact types accepted (some exclude "low")
- Average bounty amount (signals program generosity)
```

### Minutes 5-15: Asset Discovery

Run the standard pipeline above. Focus on live.txt output.

### Minutes 15-25: Surface Map

Run gf patterns and the interesting-params grep above.

### Minutes 25-30: Manual Exploration

Open Burp Suite. Browse the app with proxy on:
1. Register an account
2. Perform main user actions (create/read/update/delete resources)
3. Note all API calls in Burp history
4. Look for endpoints not in your URL list

### After 30 min: Prioritize

```
Priority 1: API endpoints with ID parameters → IDOR candidates
Priority 2: File upload features → XSS/RCE candidates
Priority 3: OAuth/SSO flows → auth bypass candidates
Priority 4: Search/filter with user input → SQLi/SSRF/SSTI candidates
Priority 5: Admin/debug endpoints → auth bypass candidates
```

---

## Toolchain fallback (when `dnsx` / `httpx` crash)

The projectdiscovery Go binaries (`dnsx`, `httpx`, `naabu`) occasionally `SIGSEGV` on macOS arm64 due to a cgo / system-resolver interaction. The crash signature is identical regardless of install method — both `brew install` and `go install github.com/projectdiscovery/<tool>@latest` produce binaries that segfault at the same address. Smoke-test once before relying on them in a real engagement:

```bash
dnsx -version   # if SIGSEGV: use the dig fallback below
httpx -version  # if SIGSEGV: use the curl fallback below
```

### `dnsx` → `dig` fallback

> **MSYS/Windows pitfall (verified 2026-10-14, WARP active):** `dig` is unreliable on this box —
> use `nslookup <host> 1.1.1.1` with an explicit resolver. Two silent traps: (1) with WARP's
> local resolver (`127.0.2.2`) EVERY host "resolves" (sinkhole), so bulk resolve loops report
> 100% live; always pass an explicit upstream resolver and filter both `127.*` and the resolver
> IP itself out of results (nslisting prints the resolver's own `Address:` line). (2) nslookup
> output is CRLF on MSYS — a hostname with a trailing `\r` makes every subsequent curl return
> `000` with no error; pipe through `tr -d '\r'` before consuming.

```bash
# Replaces: dnsx -l subs.txt -a -resp -silent
while read s; do
  ips=$(dig +short +tries=1 +time=3 "$s" \
    | grep -E '^[0-9.]+$' \
    | paste -sd, -)
  [ -n "$ips" ] && echo "$s|$ips"
done < subs.txt
```

### `httpx` → `curl` fallback

```bash
# Replaces: httpx -l subs.txt -silent -status-code -title -tech-detect
while read s; do
  resp=$(curl -s -L -m 5 -o /tmp/body \
    -w "%{http_code}|%{url_effective}|%{header_server}" \
    "https://$s")
  code=$(echo "$resp" | cut -d'|' -f1)
  if [ "$code" != "000" ]; then
    title=$(grep -oE '<title[^>]*>[^<]*</title>' /tmp/body | head -1 | sed 's/<[^>]*>//g')
    echo "$s|$resp|$title"
  fi
done < subs.txt
```

**Trade-off:** Serial vs. concurrent. The fallback handles ~24 subdomains in 14 seconds; the same workload on `httpx` with default 50 threads finishes in 2-3 seconds. For VDP-scale recon (< 100 subdomains) the fallback is fine. For mass recon (1000+) fix the toolchain first.

Verified against HackerOne's own VDP in `docs/verification/recon-hackerone-vdp.md`.

---

## API Spec / Swagger / OpenAPI Discovery (2024-2026 surface)

API spec endpoints are the single highest-leverage recon target on any modern .NET / Node / Python / Java backend. The spec discloses every endpoint, HTTP methods, parameter names + types + formats, models, validation rules — a complete attack-map in JSON. Default routes are commonly left enabled in production. **Add this wordlist to the directory-fuzzing phase** (after the standard `common.txt` pass).

### Default discovery path wordlist (paste into `swagger-paths.txt`)

```
# NSwag / Swashbuckle (ASP.NET Core)
/swagger
/swagger/
/swagger/index.html
/swagger/ui/index.html
/swagger/v1/swagger.json
/swagger/v2/swagger.json
/swagger/v3/swagger.json
/swagger/docs/v1
/swagger/docs/v2
/swagger-ui
/swagger-ui/
/swagger-ui.html
/swagger-resources
/swagger-resources/configuration/ui
/nswag
/nswag/index.html
/api/swagger
/api/swagger.json
/api/swagger/v1/swagger.json
/api/openapi
/api/openapi.json
/api/v1/swagger.json
/api/v2/swagger.json
/api-docs
/api-docs/swagger.json

# OpenAPI generic
/openapi
/openapi.json
/openapi.yaml
/openapi.yml
/openapi/v1.json
/openapi/v2.json
/openapi/v3.json
/.well-known/openapi.json

# Java / Spring (Springfox / springdoc)
/v2/api-docs
/v3/api-docs
/v3/api-docs.yaml
/v3/api-docs/swagger-config
/swagger-ui/index.html

# Python (FastAPI / Flask-RESTPlus / Connexion / DRF)
/docs
/docs/
/redoc
/redoc/
/openapi.json
/swagger.json
/swagger/?format=openapi
/swagger.yaml

# Express / Node / Hapi
/api-docs
/api-docs.json
/swagger.json
/swagger-stats
/graphql-docs

# GraphQL adjacent (often co-located)
/graphql
/graphiql
/playground
/altair
/voyager
/graphql/console
/graphql-explorer

# ReDoc / RapiDoc / Stoplight / alt UIs
/redoc
/redoc.html
/redoc-ui.html
/rapidoc
/rapidoc.html
/stoplight
/elements

# Misc / dev-leftover
/actuator
/actuator/openapi
/actuator/mappings
/q/openapi
/q/swagger-ui
/docs/swagger.json
/api/v1/docs
/api/v2/docs
/internal/swagger
/admin/swagger
/management/swagger
```

### Integration with the standard pipeline

```bash
# After live-hosts.txt is built (Phase 1 / 2), run:
ffuf -w swagger-paths.txt -u "https://FUZZ.target.com" -mc 200,302 -fs 0 -t 50 -o swagger-hits.json
# Or with httpx for content-aware filtering:
httpx -l live-hosts.txt -path swagger-paths.txt -mc 200 -mr "swagger|openapi" -json | tee swagger-hits.jsonl
# For every hit:
jq '.paths | keys' swagger.json > endpoints.txt
jq '.components.schemas' swagger.json > schemas.json   # mass-assignment field candidates
```

### Why this matters for recon-to-hunting handoff

- **Spec → mass IDOR/BOLA** — `jq '.paths | keys' swagger.json` becomes the input list for `Autorize`/`ffuf` per-user testing.
- **Spec → mass-assignment payload construction** — `components.schemas.UserUpdateDto` enumerates `isAdmin`, `emailVerified`, `tenantId`, `role`.
- **Spec → hidden endpoint discovery** — `/internal/*`, `/debug/*`, `/v0/*`, `/legacy/*` routes documented but never auth-gated.
- **Spec → injection-class seeding** — every parameter's type + format + enum + max-length means payloads pass validation before reaching the sink. Especially valuable against ASP.NET Core where the model binder rejects malformed input before any controller logic.

### Tools

- `kiterunner` — natively ingests OpenAPI spec, generates requests against the API.
- `sj` (Swagger Jacker) — purpose-built for Swagger spec exploitation.
- `apidetector` (brinhosa) — Swagger-UI mass scanner.
- `XSSwagger` (vavkamil) — detects vulnerable Swagger UI versions (CVE-2018-25031 family).
- `nuclei -t http/exposures/apis/` — built-in templates for default spec paths.

### Anti-pattern reminder

A 404/403 on `/swagger` does NOT mean no spec is exposed. Many .NET projects route the spec under `/api/swagger/v1/swagger.json` rather than `/swagger`. Always test the full path list, not just the root.

Full attack-chain analysis is in `hunt-api-misconfig` → `NSwag / Swagger / OpenAPI Spec Exposure`.

---

## Scan budget on a LIVE production target (read before firing nuclei)

Broad sweeps get you banned, not findings. `templates × hosts` is your request count — a 14k-template
sweep against 73 hosts is ~1M requests / ~9 h and trips Cloud Armor. Use **targeted template dirs**
(`http/exposures`, `http/misconfiguration`, `http/exposed-panels`, `http/takeovers`,
`http/default-logins`) at `-rl 20..40 -c 10..20`; add `http/cves -tags <tech>` only for the stack you
fingerprinted. On a 429 (`via: 1.1 google`) **stop, probe a baseline GET, wait it out** — do not rotate
egress, and mark every result from the window as POISONED, never "negative" (tools exit 0 with empty
output against a 429). Full recipe, the shared-LB-across-TLDs trap, and the MSYS leading-slash curl
mangling that fakes a `000` response: `references/live-target-scan-budget-and-429-backoff.md`.

---

## Related Skills & Chains

- **`offensive-osint`** — When recon needs concrete probes / wordlists / regexes beyond the basic pipeline. Workflow primitive: this skill produces the URL set; `offensive-osint` provides the secret regexes, GraphQL/Swagger paths, and identity-fabric probes you apply to that URL set.
- **`osint-methodology`** — When you need a severity rubric for what you discovered. Workflow primitive: after recon outputs `subdomains.txt` / `live-hosts.txt` / `urls.txt`, score each asset against `osint-methodology`'s findings rubric to decide what gets a finding versus what stays in the asset graph.
- **`hunt-subdomain`** — When recon surfaces stale CNAMEs / dangling DNS. Workflow primitive: any subdomain in `subdomains.txt` whose CNAME points to S3 / GitHub Pages / Heroku / Shopify / Azure should auto-route to `hunt-subdomain` for takeover validation.
- **`security-arsenal`** — When the URL set is classified by `gf` and ready for active testing. Workflow primitive: `gf xss/ssrf/sqli/idor` output names become payload-class queries against `security-arsenal`'s payload library.
- **`bb-methodology`** — When recon completes and Phase 1 transitions to Phase 2 (Mapping). Workflow primitive: hand the live host + URL set back to `bb-methodology` Phase 2 for endpoint mapping and Phase 3 vulnerability discovery routing.

---

## Operator Notes (Claude-BugHunter)

> Engagement-derived + 2026-specific additions to the vendored foundation.
> Wisdom from real authorized engagements + Phase 2 verification across
> this repo's 31+ skill-area live tests. The upstream pipeline covers the WHAT;
> this layer covers the WHEN-IT-WORKS-vs-WHEN-IT-DOESN'T.

### Cross-TLD pivot discipline

> **See `references/sibling-domain-and-dev-surface-discovery.md`** for the full play: enumerate the
> **tech-org** domain (`subfinder -d <techorg> -all` → 14k names vs 85 from the brand TLDs), find the
> **sibling corporate TLD** via a cross-domain `Location:` redirect, use certspotter when crt.sh is
> unreachable, **cross-check any bulk-DNS "NXDOMAIN"** (a resolver returning nothing is not proof),
> fingerprint the controls on the discovered surface (IAP / Cloud Armor / ACL / GCS), and capture the
> per-project dev naming scheme — which is itself often the finding.

Phase 2C's HackerOne VDP recon walked from `hackerone.com` (24 subdomains) into a sister TLD `hacker.one` (12 more subdomains found in JS bundle references). Operators who only enumerate `*.target.com` miss attack surface that the target legitimately operates on a different domain.

Always grep JS bundles for plausible sibling TLDs:

```bash
# pull all JS, grep for sibling-TLD candidates
for url in $(cat live-hosts.txt); do
  curl -s "$url" | grep -oE 'src="[^"]+\.js"' | sed 's/src="//;s/"//'
done | sort -u > js-urls.txt

# then on each JS file
for j in $(cat js-urls.txt); do
  curl -s "$j" | grep -oE '[a-z0-9.-]+\.(io|app|one|dev|test|cloud|ai|co)' | sort -u
done | sort -u > sibling-tld-candidates.txt
```

Common sibling-TLD patterns: `target.com → target.io / target.app / target.one / target.dev / target.test / target-corp.com / target-cdn.net`. Always validate via WHOIS or by checking if the cert chain trusts the same internal CA before treating the sister TLD as in-scope.

### Subdomain wordlist priorities by 2026

Top discovery prefixes by hit rate against enterprise VDPs in our 2024-2026 corpus:

```
mta-sts.*          api.*              docs.*
dev-*              staging-*          *-qa
*-stage            *-uat              events.*
portal.*           customer.*         partner.*
vendor.*           internal-*         admin-*
employee-*         hr.*               jobs.*
sso.*              auth.*             id.*
```

Internal-looking subdomains often expose more surface than the marketing site — `partner.target.com` and `vendor-portal.target.com` frequently have weaker auth than the main app because they're scoped for "trusted" external users. Always send a probe to the long-tail wordlist after the standard subfinder run completes.

### Live-host probe: how to fingerprint stack quickly

`curl -sI <host>` headers are 80% of the fingerprint:

- `Server:` — apache / nginx / cloudflare / kestrel (= .NET Core) / openresty / envoy
- `X-Powered-By:` — PHP version, ASP.NET version, Express.js
- `X-Drupal-Cache`, `X-Generator: Drupal 9` — Drupal
- `X-Generator: WordPress` — WordPress
- `Via:` — CDN chain (1.1 varnish, 1.1 cloudfront)
- `Set-Cookie:` names — `JSESSIONID` (Java), `PHPSESSID` (PHP), `ASP.NET_SessionId` (.NET), `connect.sid` (Express), `laravel_session` (Laravel)

JS bundle filename patterns:

- `/_next/static/` = Next.js
- `/_nuxt/` = Nuxt
- `/assets/static/` with hash filenames = Vite
- `/static/js/main.*.chunk.js` = Create React App
- `runtime.*.js + polyfills.*.js + main.*.js` = Angular CLI

The first 10s of recon should yield a stack guess; the rest is targeting. If your fingerprint contradicts itself (Server says nginx, Set-Cookie says ASP.NET) you've found a reverse proxy front-end — note the origin app for later smuggling/cache attacks.

### GitHub Pages 404 vs takeover signal

Critical distinction operators get wrong:

- **"Page not found · GitHub Pages"** with HTTP 404 means the repo EXISTS — NOT a takeover.
- **"There isn't a GitHub Pages site here"** means the repo was deleted — TAKEOVER candidate.

Same distinction for CloudFront:

- **"Error - 404"** with `Server: CloudFront` = distribution exists, origin returned 404 — NOT a takeover.
- **"The request could not be satisfied"** with `X-Cache: Error from cloudfront` = origin missing entirely — potential takeover.

Phase 2C verified both patterns live. Always check the EXACT response body string before filing a takeover finding — the takeover-scanner tools (subzy, subjack) match on multiple fingerprints and frequently false-positive on the "still owned, just empty" case.

### Toolchain fallback

Already covered in this file's Phase 2C addition. Quick reminder: dnsx/httpx may segfault on macOS arm64; the dig+curl fallback works for < 100-host runs in ~14 seconds. Don't burn an hour debugging Go binary panics when the fallback gets you to the same URL set.
