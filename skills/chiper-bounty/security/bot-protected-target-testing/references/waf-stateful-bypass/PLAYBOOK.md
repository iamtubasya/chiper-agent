---
name: waf-stateful-bypass
description: Use when a WAF blocks every path on a bug-bounty target.
---

# Stateful / Rate-Based WAF Bypass — Low-and-Slow Origin Crawl

## Trigger
Every path on a target returns the same block: `302 → /msg/sg_err.php?err=..&SG_ID=..&Rule=..` (or 403 block page). Standard encoding/path bypasses all fail. Most hunters conclude "fortified, no findings". In many cases the WAF is **rate-based / stateful**: it blocks bursts but lets clean, slow, single requests through to the real application.

## FIRST: classify WHICH layer is blocking you (do this before any bypass attempt)

A single "target is blocked" conclusion hides four independent defences that need four
different responses. Build an **egress matrix** — same path, several egress paths — and read
the *shape* of the failure. Full worked example: `references/kmart-akamai-multilayer-case.md`.

| Symptom | Layer | What it means | What actually fixes it |
|---|---|---|---|
| `403` + vendor error host (`errors.edgesuite.net`, `cf-error`, vendor ref id) | **Edge policy / geo** | Your IP range is refused outright | Different egress: residential IP in the target's country |
| `429` + a challenge marker in the body (`{"cpr_chlge":"true"}`, `cf-mitigated`, JS-challenge HTML) | **Bot challenge** (Akamai CPR, Cloudflare) | IP passes the geo policy but is classed datacenter/VPN | A non-datacenter egress. **Fingerprint spoofing does NOT help** |
| Same path + same egress + same second: `curl` 200 but `python-urllib` 403 | **Client fingerprinting** | The edge fingerprints the HTTP client, not just the IP | Drive requests with `curl` (subprocess), not urllib/requests |
| Burst of ~20 → everything 403, then one clean request minutes later → 200 | **Rate / stateful** | Classic low-and-slow case (the rest of this skill) | Pace ≥5–6 s, rotate egress, cooldown after bursts |
| Clean request 403 with the *scanner's own UA*, same request 200 with a browser UA | **Tool-signature blocking** | The edge blacklists known scanner UA strings — your payloads were never filtered | Set a browser UA (or `--random-agent`) and re-run before reading anything into a negative |
| Same path, same IP, same second: default `curl/x.y` → 200, full `Chrome/…/126.0.0.0` → 200, but a *stale/incomplete* browser UA (`Chrome/126 Safari/537.36`, or bare `Mozilla/5.0`) → Cloudflare JS challenge (`Just a moment...`) | **UA *consistency*, not just UA identity** (Cloudflare) | Cloudflare scores UA *plausibility*: an incomplete Chrome version string reads as a bot, and a curl UA is fine because it's honestly self-identifying | Send a fully-formed UA (`Chrome/126.0.0.0 Safari/537.36`) — or just leave curl's default. Settle this layer with one harmless request per UA *before* you blame the payloads; the same "403" can be a UA artefact |

**Diagnostic that settles the challenge layer in one test:** hit the challenge-protected host
from a *fingerprint-spoofed* browser (e.g. camoufox) AND from a clean real browser. If both
receive the identical challenge response, the challenge is **keyed on IP reputation**, not on
browser fingerprint — stop investing in stealth-browser work and go find a better IP.
(Verified on Kmart AU: camoufox and clean Chrome both got the same
`429 {"cpr_chlge":"true"}`.)

**Client-fingerprint layer is real and is the least obvious one.** Through the same relay, to
the same path, in the same second: `curl` → 200, Python `urllib` → 403. Adding browser-like
`Accept` / `Accept-Encoding` / `Accept-Language` / `Sec-Fetch-*` headers did **not** fix it.
If your harness shells out to curl and the enumerator is written in Python-urllib, the
enumerator will report a fortress while manual curls succeed. **Rewrite the enumerator to
shell out to `curl`** (`subprocess.run([...])` with `-w '%{http_code} %{size_download} %{content_type}'`).

### Map the edge WAF's payload *signatures* before tuning payloads (5 min, saves hours)

On a Cloudflare-fronted target the useful question isn't "is there a WAF" but "which payload **shapes**
does it block vs pass". One harmless request per candidate bisects the rule set:

```bash
for p in 'plaintext' 'a"b' 'a<b' "a'b" 'a{b' 'a`b' 'a\b' 'a%00b' '<img src=x>' \
         '<img src=x onerror=alert(1)>' 'onerror=alert(1)' '<script>alert(1)</script>' \
         'javascript:' '1 or 1=1' 'AND 1=1' 'http://169.254.169.254/' '../../etc/passwd'; do
  printf '%-36s ' "$p"
  curl -s -o /dev/null -w '%{http_code}\n' -A "$BROWSER_UA" -G --data-urlencode "q=$p" "$TARGET"
  sleep 1
done
```

Verified behaviour (Cloudflare Bot Management, 2026): **benign metacharacters all pass 200** — `"`, `<`,
`'`, backtick, `\`, `%00`, `%0a`, `{{7*7}}`, `${7*7}`, bare `select` / `union` / `onerror` as a *word* —
while **complete payload strings 403**: `onerror=alert(…)`, `<script>…</script>`, `javascript:`,
`1 or 1=1`, `AND 1=1`, `169.254.169.254`, `../`. Sensitive paths (`/.git/*`, `/.env`, `/phpinfo.php`,
`/.htaccess`, `/.svn/entries`) 403 too.

Two consequences that change the plan:
- A 403 on a payload tells you **nothing about the app** — only that the edge matched. Don't report it
  as "blocked" and don't conclude the parameter is safe.
- The WAF-passes-primitives window (single quotes, angle brackets, encoding layers) is exactly where you
  re-aim: alternate encodings, parameter pollution, body-vs-query placement, context-breaking via
  characters the edge accepts, then **verify escaping server-side** (see the `og:url` FP in this file's
  pitfalls — a reflected-but-escaped value is not a finding).

### Map the edge WAF's PATH allowlist — the gate usually serves a whole surface unchallenged

The payload-signature map above answers "which **values** does it block". The companion question —
asked far less often, and the one that actually opens a target — is **"which PATHS does it serve
without challenging at all?"** A challenge page is not a blanket wall. It is frequently an
*allowlist with a challenge fallback*: a set of paths (and path shapes) is proxied straight to the
app, and everything else gets the interstitial.

**What it looked like on City-Data.com (2026-10, direct-to-company VDP):** every "obvious" path
(`/`, `/forum/`, `/api/`, `/login`) returned a Turnstile-branded `403/429` interstitial. A first
pass concluded "Cloudflare-walled, untestable" — wrong on both counts. The IPs resolved to **OVH,
not Cloudflare ranges**, and the interstitial was the origin's **own WAF** (`Server: nginx`,
`X-Server: cdn1`) reusing the Turnstile widget. Because the decision was **path-based**, simply
requesting paths *without* an attack signature walked straight past it:

```
### add a payload signature  -> interstitial       ### benign path shape -> real app, no gate
/cityname.php?id=1<script>alert(1)</script> 403    /cityname.php?id=1             200 (3603b, real)
/business-profiles/map.php?from=1<script>   403    /business-profiles/map.php     200 (8609b, real)
/api/ , /forum/ , /                     403/429    /profiles/account              200 (auth form!)
```

**The technique (10 minutes, run it before you ever say "walled"):**

1. **Enumerate candidate paths, benign.** Request a batch of *plausible, attack-free* paths and
   read status + size. Split into: `200 real content` / `301-302` / `403-429 interstitial` /
   `404`. Anything in the first bucket is a live surface you can test **right now**.
   ```bash
   for p in / /index.html /news/ /profiles/account /cityname.php /a/util.php \
            /robots.txt /.well-known/security.txt /sitemap.xml /css/style.css; do
     printf '%-32s ' "$p"
     curl -sk -A "$BROWSER_UA" -o /dev/null -w '%{http_code} %{size_download}\n' "https://$T$p"
   done
   ```
2. **Read `robots.txt` for the allowlist's shadow** — a `Disallow:` list names the *dynamic*
   endpoints the operator cares about, and those paths are frequently in the pass-through set
   (`/cityname.php`, `/business-profiles/map.php`, `/restaurants/*.class.php`, `getBoxes.php`).
   Robots-disallowed + WAF-allowed is a high-signal pair; that combination is where the auth and
   search surfaces live.
3. **Confirm the split is path-based, not client-based.** Take ONE allowlisted path and ONE gated
   path, hit both from curl, `requests`, and a real browser. If the allowlisted path is `200` under
   *all three* and the gated path is challenged under *all three*, the axis is the path — not your
   client. (This is the mirror of the IP-reputation diagnostic further up: same conclusion tool,
   opposite axis.)
4. **A signature anywhere on the request re-gates a benign path.** Appending `<script>`, `../`,
   `%00`, `'`, `SLEEP(` to an otherwise-allowlisted path flips it back to the interstitial. So the
   allowlist *does* double as a payload filter on those paths — which means a `403` on your probe
   is the edge matching, **not** the app rejecting. Do not log it as "no injection here".

**Why this matters for the report:** what you reach this way is real reconnaissance-grade surface
(auth form with its exact `name=`/`action=` fields, search endpoints, a map/news handler). It is
not automatically a finding — on City-Data the reachable auth form returned byte-identical
`invalid` for `admin`/`test`/nonexistent (no enumeration) and every injection/reference probe was
re-gated — but it converts "untestable wall" into "tested surface with a named coverage gap", which
is the honest, submittable shape.

### Before blaming the WAF: is the *tool's own User-Agent* the block?

The cheapest diagnostic in this whole skill, and the one most often skipped. Send **one clean,
harmless request** twice — once with the scanner's default UA, once with a browser UA:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -A 'sqlmap/1.9#stable (https://sqlmap.org)' \
     -H "$AUTH" 'https://target/api/v1/categories?sourceType=uk-property'     # -> 403
curl -s -o /dev/null -w '%{http_code}\n' \
     -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36' \
     -H "$AUTH" 'https://target/api/v1/categories?sourceType=uk-property'     # -> 200
```

If the *clean* request is 403 only under the tool's UA, the 403 flood in your scan log
(`[WARNING] HTTP error codes detected during run: 403 (Forbidden) - 3742 times`) means **the edge
was rejecting the tool, not filtering payloads** — every "no injection found" conclusion in that
run is void, because the application never saw the requests. Fix and re-run (`sqlmap
--random-agent`, or `--user-agent='<browser UA>'`), then confirm the 403 count in the new log is
**zero** before reading the result. Same applies to nuclei (`-H 'User-Agent: ...'`), ffuf (`-H`)
and any tool that ships a self-identifying UA.

Corollary — **an app-level rejection is stronger evidence than a WAF-limited negative.** Once the
UA is fixed, the useful evidence is the application's own validation, not the scanner's verdict:
`limit=25'` → `422 'limit must be a whole number from 1 to 200'`, `cursor=' OR 1=1--` →
`422 'cursor must be a transaction id...'`, `from=notadate` → `422 'must be real dates in
YYYY-MM-DD'`, and a SQL-looking value in a JSON body → `400 invalid_json`. Probe each parameter by
hand like that and quote the messages. "Every parameter is shape/enum-validated with a named
reason" is a defensible positive; "sqlmap said not injectable" alone is not, especially when the
log also shows thousands of 403s.

### Separate payload-blocking from client-blocking with a three-request control (run it per URL)

One path, same minute, three requests:

| # | request | tells you |
|---|---|---|
| 1 | benign params + your normal UA | baseline — is the path reachable at all? |
| 2 | attack payload + **same** UA | `403` while (1) is `200` ⇒ a **managed rule matched the payload**. The app never saw the request; the honest finding is "WAF blocked", never "no vulnerability". |
| 3 | benign params + a deliberately odd/short UA | challenge/`403` while (1) is `200` ⇒ **client-fingerprint blocking**, not payload blocking. |

Do not compress this into "the target is blocked". Measured on a Cloudflare-fronted target
(2026-09): the default `curl/8.4.0` UA passed everywhere, while a *short* Chrome UA returned `403`
on one path and `200` on another minutes apart — so the control has to be re-run **immediately
before you record each negative**, and a UA that merely "looks realistic" is not automatically the
one that passes. Managed rules on that target cleanly 403'd `1 or 1=1`, `AND 1=1`,
`http://169.254.169.254/`, `onerror=alert(…)`, `<script>`, `<svg onload>`, `javascript:`, `../`,
and sensitive paths (`/.git/*`, `/.env`, `phpinfo.php`, `.htaccess`, `/.svn/entries`, `.DS_Store`) —
while every benign special character (`"` `<` `>` `'` backtick `\` `%00` `${7*7}` `{{7*7}}`) passed
`200`. That split is useful evidence: it means the payload classes are being filtered *at the edge*,
so a clean result from a scanner aimed at those paths proves nothing about the app behind it.
If no origin IP is discoverable (everything on Cloudflare ranges, all `web1..web4`-style names
NXDOMAIN, mail-only hosts on SendGrid), record "WAF not bypassable this round" as a coverage
statement and move the effort to surfaces the WAF does not sit in front of (separate API hosts,
websocket endpoints, authenticated JSON APIs).

**Do not let a level-5 scanner run for hours on a surface you have already closed.** A
`--level=5 --risk=2 --tamper=<4 scripts>` run walked DBMS-by-DBMS for 2.5 h having produced no
candidate, and its remaining value was one verdict line. Kill it, record the partial log as
evidence (`tail -20 <log> > <log>_STOPPED.txt`), and spend 5 minutes on a focused `--level=2` run
plus hand probes instead. The recipe is packaged: `scripts/sqlmap_verdict.sh <url> <header-file>`
runs the UA diagnostic, then a level-2 single-tamper verdict run, and greps the verdict lines.

```bash
sqlmap -u "$URL" --headers="$HDR" --level=2 --risk=2 --technique=BEUST --batch \
       --disable-coloring --timeout=25 --delay=1 --random-agent \
       --tamper=space2comment --text-only -v 2 > verdict.log 2>&1
grep -aE 'does not seem to be injectable|appears to be injectable|all tested parameters|CRITICAL' verdict.log
```

Verdict lines that mean what they say and are worth quoting in the report:
`[WARNING] GET parameter 'X' does not seem to be injectable` ·
`[CRITICAL] all tested parameters do not appear to be injectable`. Confirm the 403 count in that
new log is **zero** first — otherwise you are quoting a verdict about requests the app never saw.

**Do not take sqlmap's own WAF suspicion at face value.** With the UA fixed, sqlmap logged
`[WARNING] the web server responded with an HTTP error code (422) which could interfere with the
results` followed by `[INFO] checking if the target is protected by some kind of WAF/IPS` — while
every one of those 422s was the *application's* enum/format validator (`sourceType must be one of…`).
A scanner that sees uniform non-200s on every payload will hypothesise a WAF; that hypothesis is
the scanner's problem, not evidence about the target. Read a handful of the actual response bodies
before repeating the claim.

**Long scanner jobs can drop out of the session's process registry.** After ~2 h the job no longer
appeared in the process list although the OS process was still alive and writing. Do not wait on a
completion notification that may never arrive — poll the log's mtime/size
(`stat -c '%y %s' <log>` twice, 60 s apart) to tell "still working" from "dead", then read the tail
yourself.

### When the whole API host is unreachable but the storefront is not
Retailer/SPA targets are commonly split: the app shell (`www.`) is reachable, the API host
(`api.`) is behind the strictest policy. Symptom = pages render but **no auth UI mounts**
(0 credential inputs, 0 captcha widgets) because login/register are GraphQL-driven.
Do not report "no findings" on that surface. Instead:
- Record the **access matrix as the finding** — it is a coverage statement, not a result.
- Harvest the API surface statically from client bundles (operation names, argument
  signatures, returned PII fields) so a later session with a usable IP starts at the
  high-value endpoints instead of re-conning. See `references/api-surface-from-bundles.md`.

## Mindset (operator expectation)
- **A STATUS CODE IS NOT EVIDENCE. Neither is a wall.** Operator correction delivered three times in
  one session, escalating — verbatim: *"jgn kasih 500-403-400-200, tp kasih sy bukti kalau itu ad
  impact kerasnya, spt data leak, idor, bola, ato, rce"* ("don't give me 500/403/400/200 — give me
  proof of HARD impact: data leak, IDOR, BOLA, ATO, RCE. Prove something was actually OBTAINED and
  that it has negative impact") and *"harus ada hasil kelemahan baik keamanan mau pun bisnis logic,
  itu baru bug"* ("there must be a resulting weakness — security OR business logic. Only that is a
  bug"). Before writing anything, answer: **what did I obtain? Name the artifact** — records, PII
  fields, a token, another principal's object, code execution, an action with a negative business
  consequence. If you cannot name it, it is a coverage note, never a finding. A WAF `403`, a `200`
  on a path, a version banner, or "the endpoint exists" are all ZERO on their own.
- **Differing codes buy you a MAP, not a result.** `404` = route does not exist · `401` = route
  EXISTS and enforces auth · `200` with a data shape = route exists and answered. That is
  reconnaissance value (it tells you which endpoint families are real, and therefore where
  provisioning an account is worth the budget) — journal it as a map, never report it as a finding.
- **Screen for the SPA catch-all before believing any `200`.** An app shell returning the *same
  byte-length* body for `/`, `/api`, `/login`, `/swagger-ui.html` and `/v3/api-docs` is a client-side
  route fallback — N paths that "exist" with no data in any of them. The real routes live in the JS
  bundle, not in the status table.
- **Edge refusal vs app refusal — name which one you got.** Edge/WAF: uniform `403`/`429` across
  *unrelated* paths, tiny identical body (~100–120 B), `Server: cloudflare`/`Envoy`, `CF-Ray`
  present, challenge path `/cdn-cgi/challenge-platform/...` answering `200` with a ~240 KB JS page →
  **IP/edge-keyed**; stealth work is wasted effort. App: `401` as **JSON**
  (`{"message":"Unauthorized"}`) or an app-shaped `403` from the app's own stack → the app is
  reachable and its authz works; the auth is the boundary to attack *with a session*.
- **Sweep the whole in-scope set before calling an estate "hardened".** Verified 2026-10: an apex was
  100% WAF-gated (WordPress REST `403`, Gitea `/api/v1` `403`, all paths `403`) while a **sibling
  in-scope domain** hosted an **un-WAF'd, auth-gated app** whose API answered `401` with real route
  names (`/api/users`, `/api/projects`, `/api/audit-logs`). That sibling was the only testable surface
  in the estate. Enumerate every in-scope domain, not just the apex.
- **Capture policy exclusions verbatim at 0A, not from memory at report time.** Real program text
  deferred whole classes: *"information disclosure and reflected XSS for `*.rand.*` and `*.labs.*`"*,
  *"rate limiting or brute force issues on non-authenticated endpoints"*, an explicit out-of-scope host
  list, and a third-party clause (Okta/Cloudflare/Zoom/LE). Testing an excluded class is not extra
  coverage — it is wasted budget, and on strike-rule programs it is the road to suspension.
- **Keep hand-run recon OUT of the harness's output directory.** Verified 2026-10: a 5,027-line
  `subfinder -all` result written into the orchestrator's `recon-evidence/recon-subfinder.txt` was
  **silently overwritten** by the pipeline's own tool-usage recorder, which rewrote the same path with
  a `# TOOL EVIDENCE:` header + `rc=0 subdomains=0`. Keep your own recon in your own engagement dir;
  copy into harness-owned paths only as final artefacts.
- Do NOT conclude "target fortified / all findings informational" after a first pass of aggressive probes. A rate-based WAF *looks* like a fortress until you go low-and-slow.
- **"Walled" is a HYPOTHESIS, not a conclusion.** The operator has pushed back hard on stopping at a
  challenge page ("you already gave up on Turnstile, you should have tried to break through"). Before
  you write "blocked", exhaust the *layers* — each one is a distinct 10-minute check:
  (1) **path allowlist** — do attack-free paths get served unchallenged? (see the path-allowlist
  section above) · (2) **egress/IP** — is a different IP class reachable? does the origin resolve off
  the CDN? · (3) **client fingerprint** — curl vs requests vs real browser, per path · (4) **UA
  identity vs consistency** · (5) **payload signature** — which *shapes* flip to 403.
  A challenge page tells you *which layer* fired; it never tells you the target is closed.
- **State the axis, not just the wall.** "Cloudflare-protected" is a non-answer. The submittable
  statement names the mechanism: *"the origin's own WAF serves an allowlist of paths unchallenged
  while re-gating any request carrying a payload signature — hence <paths> are tested and <classes>
  remain a coverage gap."* That is a coverage finding; "blocked" is not.
- **Do not invoke ToS as a substitute for technique.** Refusing a *Cloudflare* bypass is correct —
  but only after confirming Cloudflare is actually in the path. On City-Data the "Turnstile" wall was
  the origin's own nginx WAF and the IPs were OVH; the challenge was never CF's to bypass, and the
  reachable paths were fair game. Verify whose control is blocking you before you abstain.
- "Pastikan bisa" rule: for any CVE lead, VERIFY the exploitation conditions yourself before writing it up. No "if X is configured" claims — prove it or drop it.
- Tools first, curl as fallback; when tools are rate-limited, raw-socket python probes with gaps are the bypass itself.

## Workflow

### Step 1 — Origin discovery
The WAF may sit at CDN level only. Find the origin IP:
```bash
dig +short <host>                 # if not a Cloudflare/CF range -> origin exposed
nslookup <host> 8.8.8.8
curl -s "https://crt.sh/?q=%25.<domain>&output=json" | grep -oE '"[^"]*"' | sort -u
curl -s "https://internetdb.shodan.io/<ip>"          # CPEs, vulns, eol-product tags, ports, hostnames
```
Shodan InternetDB `vulns` and `eol-product` tags are CVE leads — but see Step 6.

### Step 2 — Direct origin test (both curl and raw socket)
```bash
curl -sk --resolve "$host:443:<origin_ip>" "https://$host/" -o /dev/null -w "%{http_code}\n"
```
If curl gets 302/403 but a **clean raw-socket** request gets 200 with a full page, you've confirmed the WAF is stateful/rate-based (this happened on ALSCO sandbox-royal: curl → 302 WAF page; python raw socket → HTTP 200, 49KB Royal CMS homepage).

### Step 3 — Detect rate-based behavior
- Aggressive burst (e.g. 15 paths fast) → everything 302/403/000 (timeout = temp IP block).
- After a **30–60s cooldown**, ONE clean GET / → 200 full page.
- Then 3 quick requests → 302 again. That oscillation = rate-based WAF, not an allowlist.

### Step 4 — Low-and-slow enumeration (the bypass)
Gap = 5–6 s per request minimum. Use `scripts/slow_probe.py` (raw socket, configurable delay) instead of curl loops — curl also works but slower to write. Walk every candidate:
```bash
python slow_probe.py <host> <origin_ip> --path "/index.php?article=8" --delay 6
```
- Enumerate sequential IDs (article=1..13), topics, pages — real 200s = the app is reachable.
- Once one path returns 200, extract its links/forms → the app's real endpoint map.
- THEN enumerate hidden dirs with gaps (`/home/program/*.php`, `/admin/`, `?page=`, etc.).

### Step 5 — WAF rule mapping (free fingerprint)
Redirect URLs leak the rule engine. Record them — they fingerprint the product and tell you which payload categories are covered:
| Observed | Meaning |
|---|---|
| `err=22 Rule=G.S.13` | generic sensitive-path block |
| `err=23 Rule=G.S.930130` | suspicious request / sensitive file (.env,.git) |
| `err=23 Rule=G.S.941100` | XSS payload detected |
| `err=23 Rule=G.S.921120` | CRLF detected |
| `err=23 Rule=G.S.920440` / `920600` | request-body / protocol anomaly |
- `SG_ID=<counter>.<decimal>` format + `X-Secure_Gateway_ID` header identify the product.

### Step 6 — CVE verification discipline
- Shodan `vulns` is a LEAD, not a finding. Verify the trigger condition yourself:
  - e.g. CVE-2025-23419 (nginx TLS session resumption bypass of client cert auth): check `openssl s_client -connect <ip>:443 -servername <host>` — if `No client certificate CA names sent`, client cert auth is NOT configured → NOT exploitable → do NOT report as a bounty finding.
- Only report when you reproduced the actual condition end-to-end.

### Step 7 — Once the app is reachable: CSRF freshness gotcha
CMS pages embed CSRF tokens that are **time-bound** (suffix is an epoch) and **session-bound**:
- GET the form page → capture cookie (PHPSESSID) + token in the SAME session.
- POST immediately with that cookie+token; tokens expire in seconds-minutes.
- A stale token → `CSRF token validation failed` (looks like a bug, isn't).
- Keep a cookie jar per session; refetch page if POST fails.

## Pitfalls
- **Don't run fast loops** (shell `for` with no delay) against a rate-based WAF — you teach it to block your IP for minutes. Gap ≥5 s, or cooldown 30–60 s after a burst.
- **000/timeout from raw socket = temp block**, not a dead target. Wait and retry once.
- `"pdo"` in a page body can be a substring of `dropdown` — false positive. Search for real error markers (`SQL syntax`, `Warning`, `Uncaught`) with context.
- XSS payloads reflected **HTML-escaped** (`&quot;`, `&lt;`) in input `value=` attributes = safe. Verify escape, don't claim reflection.
- User-enum via login timing needs n≥5 interleaved trials (methodology rule); identical status+size across users = no signal.
- Overlong/oversized inline bash with `$()`/`${}` gets hardline-blocked by the agent parser — write the loop to a temp script file first or use execute_code.

## Support files
- `scripts/sqlmap_verdict.sh` — one re-runnable pass: tool-UA vs browser-UA diagnostic, the
  hand-probe reminder, then a level-2 single-tamper verdict run with the verdict / 403-count /
  WAF-suspicion greps. Run this before quoting any scanner negative on a WAF-fronted target.
- `scripts/slow_probe.py` — low-and-slow raw-socket probe (gap-based) for rate-limited WAF targets.
- `references/kmart-akamai-multilayer-case.md` — worked example: Akamai on a Bugcrowd VDP,
  the four-layer egress matrix (geo 403 / bot challenge 429 / client fingerprint curl-vs-urllib /
  sticky rate block), and what "API host unreachable but storefront reachable" looks like.
- `references/api-surface-from-bundles.md` — harvest GraphQL operations, argument signatures and
  returned PII fields from client bundles when the API itself is blocked; how to rank the
  resulting BOLA candidates.
- `references/status-code-not-evidence-case.md` — worked example (2026-10, RIR estate) of the
  "status code is not evidence" rule: the all-403 edge apex, the Cloudflare challenge path that
  proves IP-keying, the SPA catch-all faking five routes at one byte length, the un-WAF'd sibling
  domain with real `401` route names, and **two retractions** — a `forgot-password` response that
  looked like an enumeration oracle and died to a 15-address control (1 unique body vs 1 uniform
  "Email does not exist"), plus a self-registration path that turned out invite-only. Read it before
  writing up any enumeration or "unauthenticated read" claim.
- `references/data-exposure-lookalikes-and-bucket-ownership.md` (skill `audit-execution-discipline`)
  — the four status-code lookalikes to kill (SPA catch-all, keyword-regex over HTML faking
  "hard data", same-named third-party bucket, generic error string read as an oracle) + the 3-step
  bucket-ownership test + the "prove object reachability with HEAD/Range magic bytes, don't download
  it" recipe. Use when a target's estate includes object storage or an auth-gated app.


## 2026 sweep (dork pass 2026-10-18 — 2 repo)

- **CVE-2026-61511 — PHPFuck encoding transforms payload into PHP operators/numbers to bypass WAF** (`tc4dy/CVE-2026-61511-PoC-Exploit` ★6)
  - Affected versions: **5.0.0 – 5.7.5** and **6.0.0 – 6.2.1**.
  - 2. **PHPFuck encoding** – the payload is transformed into a sequence of PHP operators and numbers that bypasses WAF filters and allows arbitrary PHP code execution.
- **Cloudflare bypass methods 2026 — which scraping approaches still work** (`gfv149/cloudflare-bypass-methods` ★1)
  - How to Bypass Cloudflare When Web Scraping — Why Requests Get Blocked, Which Methods Still Work in 2026, and How ScraperAPI Handles WAF Protection at Scale (With Full Plan Pri
  - "Cloudflare continues to evolve, improving its bot detection systems and creating increasingly complex challenges, but you'll always be one step ahead." — ScraperAPI, on its W
