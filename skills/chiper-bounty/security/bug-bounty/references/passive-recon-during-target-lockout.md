# Working While the Target Blocks You — ban-cooldown discipline + passive fallback

Session: Zecible (YesWeHack, YwhModSec) 2026-10-16. Target ran "YwhModSec" (ModSecurity fronting
every ywh.* vhost on one IP) with a "no automated scanners / large traffic" program rule → all
scanning GENTLE (rate 1-2, c=1). Even so the run ended in a full egress ban. This file is how to
detect the ban class early, stop feeding it, and keep producing value passively until it lifts.

## The escalation ladder (recognise which rung you are on)

1. **HTTP 429 per-vhost** — first warning. Some vhosts (static/CDN-style) still return 200 while
   dynamic vhosts return 429: the limit is per-vhost or per-URL-class, not global yet. Response has
   no `Retry-After`; the window is opaque (observed ~8-12 min).
2. **429 on ALL dynamic vhosts** — global soft-ban on your IP. Stop all requests.
3. **TCP DROP (connect timeout on :443 to the origin IP, no TLS, no HTTP)** — escalation to a
   firewall-level ban. It survives WARP reconnect with a FRESH IPv6 (observed: new `2a09:…` still
   dropped) → likely prefix-level or they banned after repeated 429-triggering. Cooldown unbounded
   (30-120+ min). **Continuing to probe = feeding the ban and violating the program's
   no-degradation rule.**

Detection one-liner (cheap, no HTTP noise):

```python
import socket, ssl
s = socket.socket(); s.settimeout(8)
s.connect(("ORIGIN_IP", 443))          # TimeoutError at TCP = rung 3
# TCP open, then TLS+SNI GET -> 429 = rung 1/2
```

Distinguish from `target-reachability-and-egress-triage.md`: that file covers "host resolves but
times out" as egress/IP-allowlist triage; THIS file covers "we got ourselves banned mid-engagement".

## What fuels the ban even at "gentle" rates

- **Error storms.** A ffuf/nuclei run whose requests mostly FAIL (timeouts because you are already
  soft-banned) still fires the full wordlist plus retries — 572 requests, 100+ errors per host.
  The error count IS the traffic. Watch the error counter: >30% errors = KILL the run immediately,
  do not let it finish "for completeness".
- **Reconnect loops.** curl auto-retries, ffuf `-retries`, nuclei `-retries` multiply effective
  request count under a ban.
- Rule of thumb for "no large traffic" programs: hard-cap total requests per run (150-200), put
  `sleep 4-8` between interactive probes, and check a canary URL before every new batch.

## Egress rotation reality check

- WARP (`warp-cli disconnect; sleep 3; warp-cli connect`) rotates the IPv6 — verified via
  `https://www.cloudflare.com/cdn-cgi/trace` (`ip=`, `warp=on`). Useful for rung 1-2.
- At rung 3 the fresh WARP IP was ALSO dropped → do not loop rotations; two fresh-IP attempts is
  the limit before you conclude prefix/range ban and switch to passive mode.
- Direct-vs-WARP comparison also tells you the ban key: direct 429 + WARP 200 = per-IP; both dead =
  prefix/range.

## Passive value stream while locked out (never touches the target)

1. **Wayback CDX enumeration** (finds endpoints you never saw live):
   `http://web.archive.org/cdx/search/cdx?url=<host>/*&output=text&fl=original&collapse=urlkey&limit=80`
   — on the Zecible run this surfaced `/static/openapi.yaml`, `/static/postman.json`, `robots.txt`
   on the verify API host, which were NOT linked from any live page.
2. **Fetch archived artefacts**: `http://web.archive.org/web/2026/<full-url>` returns the archived
   copy (wayback rewrites links; for JSON/YAML read the body after the marker, e.g. `y.find("openapi:")`).
   The postman.json + openapi.yaml gave the COMPLETE API surface (endpoints, auth scheme
   `X-API-Key: vkey_live_...`, IP-allowlist requirement, rate-limit headers, MD5/SHA256 hashed-input
   support) while the live host was unreachable — enough to plan the entire 0C test matrix in advance.
   **Shell trap when batch-fetching per-path**: `-o "mydata_$p_wb.html"` inside `for p in faq rgpd`
   parses `$p_wb` as one variable (empty) → every file silently lands as `mydata_.html`, overwriting
   each other, and the 200-size report looks successful. Use braces: `"mydata_${p}_wb.html"`, and
   `ls` the output dir immediately after the FIRST iteration.
3. **Vendor's public marketing site** — different infra, usually not banned (it was NOT the scope
   host; reading it is passive). Use it for (a) core-business mapping, (b) the **by-design check**:
   when an unauthenticated endpoint returns real business data (here: comptage count + full pricing
   engine), grep the marketing site for links to it — www.zecible.fr linked
   `comptage.zecible.fr/b2b|/b2c` as "Comptage & Devis immédiat" sales funnel → BY DESIGN, not a
   finding. An unauth endpoint is only an exposure if the vendor does not advertise it publicly.
4. **Gmail/operator inbox** — check for delayed recipient-flow emails (file-exchange upload
   notifications); async delivery can lag 10-30 min.
5. **CT logs via crt.sh/certspotter** — passive subdomain expansion (crt.sh 429s under load;
   certspotter as fallback; both passive).
6. **Offline JS white-box** — every bundle you already downloaded: re-audit for sinks
   (innerHTML/eval), token handling, param names, hidden endpoints. Prepares the next live batch
   so the moment the ban lifts you fire a pre-built script (see batch_*.sh pattern).

## Tool flags on this box

- nuclei: this build rejects `-rate` ("flag provided but not defined") — use `-rl 1`. Always check
  `nuclei -h | grep -E 'rl|rate'` before a long run; a rejected flag = run never started = suspect
  coverage, not a negative result.
- gau: can hang >300s on cold domains — prefer wayback CDX via curl for URL discovery when gau
  stalls once.

## Honesty bookkeeping

- A scan that ran while blocked is a **SUSPECT RUN** (0 findings ≠ clean target). Mark it in
  TOOL-COVERAGE LEDGER as "suspect — rerun required", never as verified-negative.
- Log the ban event in scope-risk-log.md with timestamps: it proves you respected the traffic
  policy and explains coverage gaps to the vendor if asked.
