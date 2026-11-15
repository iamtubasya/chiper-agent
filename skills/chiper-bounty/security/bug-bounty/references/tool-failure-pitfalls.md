# Reference: Tool Failure Pitfalls — Documented Failures & Recovery Patterns

Real-world tool failures with exact errors and verified recovery pivots. Check here
BEFORE concluding the environment is broken. Pattern discipline: capture the FIX, not
the failure — never harden "X is broken" into a rule; backends and configs change.

---

## web_extract Returns Search-Backend Error (cannot extract URL)

**Exact error:** `DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content. Set web.extract_backend to firecrawl, tavily, exa, or parallel.`

**Cause:** `web.extract_backend` unset or `ddgs` — search-only, no extraction capability.

**Recovery (first that fits):**
1. **GitHub repos/READMEs** — skip extract, go straight to terminal:
   `curl -sL https://raw.githubusercontent.com/<org>/<repo>/main/README.md`
   (try `main` then `master`; instant, works when web_extract cannot)
2. Plain-text endpoints (`.md` `.txt` `.json` `.csv`, raw.githubusercontent.com) — same curl pattern.
3. Durable fix: set `web.extract_backend: firecrawl|tavily|exa|parallel` in config.yaml.
4. Dynamic/JS pages — `browser_navigate` + JS extraction.

**Pattern:** web_extract ≠ web_search. On a search-only backend, extraction-class tasks
fall immediately to curl (static) or browser (dynamic) — don't retry web_extract.

## Browser Tool Non-Functional (CDP Connection Refused)

**Problem:** All `browser_navigate` calls return HTTP 500 from localhost:9377 with CDP connection refused.

**Recovery:**
- Use `execute_code` for API testing that needs token lifecycle (bypasses subagent timeouts)
- Use `web_search`/`web_extract` for public program enumeration (faster than browser)
- Use `terminal` for CLI tool install/verification (`tool-installation-windows.md`)
- **Stealth/scripted need:** CloakBrowser from Python — `from cloakbrowser import launch` (see `cloakbrowser-stealth-browser.md`); verified working when the built-in browser stack is down.

**Pattern:** browser fails → `execute_code` for attacks, `web_search` for recon, `terminal` for tool management, CloakBrowser for anti-bot/scripted browsing.

## DuckDuckGo Rate Limiting

**Problem:** `web_search` returns empty results after ~10 queries.

**Recovery:**
- Aggregator endpoints: `bugcrowd.com/engagements.json`, `curl https://api.yeswehack.com/v2/programs?states=published`
- Cached scope data: `arkadiyt/bounty-targets-data` (Bugcrowd)
- Batch similar searches; reduce query frequency

**Pattern:** program discovery → `curl` → `python3` parsing, not repeated `web_search`.

## search_files Pattern "*" Fails (rg regex error)

**Error:** rg "repetition operator missing expression".

**Cause:** bare `*` is an invalid regex (glob≠regex confusion).

**Fix:** content search → `pattern: "."`; file listing → `target='files'` with a real glob (`*.py`), or terminal `ls`/`find`.

## Program-Page Extraction 503/504 (Immunefi, program portals)

**Problem:** curl returns 503 on lab/program URLs; `web_extract` often 504 on SPA program pages.

**Recovery:** `browser_navigate` + JS extraction from the live page. Immunefi is a client-rendered SPA — no static endpoint; use SmartContractsHacking.com aggregator or `web_search` for program discovery (`immunefi-program-discovery.md`).

## Subagent Timeout on Sequential Workflows

**Problem:** Subagents timeout on sequential API workflows (create account → test endpoints) due to 300s hard limit.

**Recovery:**
- `execute_code` from main thread for token-lifecycle API testing
- `terminal` for external scripts with `timeout=300`
- `process` tool for background tasks with explicit `wait`/`poll` verification

## Scanner Reported "No Results" Without Ever Running (silent target skip)

**Symptom:** a scan finishes suspiciously fast and prints a clean verdict — `nuclei` exited in
~3.5 s with `Matched: 0`. Buried above it:

```
[INF] Skipped localhost:1322 from target list as found unresponsive permanently:
      cause="no address found for host"
[0:00:03] | Templates: 2319 | Hosts: 1 | RPS: 10 | Matched: 0 | Errors: 43 | Requests: 36/5649 (0%)
```

**Cause:** the target was passed as `localhost:<port>`. The scanner could not resolve/reach it,
dropped it from the target list, then "completed" having issued 36 of 5649 requests.

**Recovery:**
1. Address the service by literal IP — `-u http://127.0.0.1:<port>` — not `localhost`.
2. **Prove the scan ran before believing its verdict.** Compare the final `Requests:` counter
   against the clustered total. `36/5649` is a failed run; a real one converges on the total
   (minus `-timeout`/`-rl` drops). A "clean" scan that issued 0.6% of its requests is silence,
   not evidence.
3. Confirm reachability from the tool's own vantage point first:
   `curl -o /dev/null -w "%{http_code}" http://127.0.0.1:<port>/`.

**Pattern:** `Matched: 0` is a finding only when the request counter says the templates ran.
The same rule covers ffuf (`0 hits` after a fraction of the wordlist), sqlmap ("not injectable"
after a single probe) and anything else with a progress line — read the progress line, always.

## The Pipeline Ate the Real Error (empty output misread as "0 findings")

**Symptom:** a loop over three URLs left a result file containing only the section headers — an
empty result set that reads as "nothing found".

**Cause:** the tool was invoked at a path that did not exist, so every iteration failed instantly
and the only capture was `... | grep -iE "injectable|parameter|..." | head -12`. The genuine error
(`can't open file '...sqlmap.py': [Errno 2] No such file or directory`) matched none of the grep
patterns and was discarded. That install shipped a `sqlmap.exe`, not a `sqlmap.py`.

**Recovery:**
1. Run the tool's own self-test (`--version` / `-h`) inside the same script, before the loop, and
   require it to print something. Silent self-test ⇒ stop, do not scan.
2. Never let a grep-filtered stream be the only evidence of a run. Write the raw output to a file
   first, then filter a COPY for reading.
3. Find the real entry point instead of assuming the module name:
   `command -v <tool>`, `ls <Scripts>/`, `file <path>`.

**Pattern:** an empty result file is not a negative result — it is an unverified one. Capture the
first thing the tool prints; if there is nothing, the tool never ran.

## `dig` silently returns EMPTY (read as NXDOMAIN) — Windows/MSYS hosts

**Symptom:** `dig +short <host>` prints nothing for names that clearly exist; a whole sweep looks
like "all NXDOMAIN / no live hosts". `curl` and `python socket` resolve the SAME name fine.

**Cause:** the `dig` in the MSYS toolchain is unreliable on some Windows hosts.

**Recovery:** resolve with `nslookup <host> 8.8.8.8` or `python -c "import socket;print(socket.gethostbyname('<host>'))"`.
Re-verify every "NXDOMAIN" conclusion before it becomes a report line — an empty `dig` is NOT NXDOMAIN.

## `dnsx` alias: an unsupported flag = silent whole-run failure

**Symptom:** `dnsx -l big_list.txt -a -resp -retries 1` prints `1 resolved` out of 14k names.

**Cause:** `flag provided but not defined: -retries` (the flag does not exist in this build). The run
aborts, writes almost nothing, and looks like "1 live host".

**Fix:** drop the unsupported flag and re-run (`dnsx -l <f> -silent -a -resp -threads 80 -timeout 5`).
A 1/N resolve ratio is a tool failure, never a result.

## `curl -o relative.txt` lands in the WRONG directory (MSYS)

`curl -o out.json https://...` with a RELATIVE `-o` may write outside the cwd (a later
`open('out.json')` then raises FileNotFoundError even though curl printed a 200). Use an absolute
path for `-o`, or `cd` in the SAME invocation that runs the reader.

## Stale `/tmp` output files fake results across steps

Every `curl -o /tmp/x` that fails leaves the PREVIOUS step's `/tmp/x` in place, so `head /tmp/x`
shows a body for a request that never returned (`code=000`). Read status from `-w '%{http_code}'`
and prefer a per-target output filename; never trust a body file without a matching 2xx.

## `wpscan` aborts — three distinct causes, all look like "the target blocked me"

1. `--api-token ""` → `Scan Aborted: --api-token Empty option value supplied`. Just OMIT the flag.
2. `-e vp,vt` (vulnerable plugins/themes) → `An API token is required for vulnerable plugin/theme
   enumeration`. Without a token use `--enumerate ap,u,cb,dbe` (fingerprint + users only).
3. `-e ap,p` together → `Incompatible choices detected: ap, p`. `ap` (all) and `p` (popular) are
   mutually exclusive.
None of these is a WAF block — do not write "Cloudflare blocked wpscan" into the coverage ledger.
Plugin→CVE mapping without a token: use the version shown by `?ver=` + a web CVE DB.

## `nikto` cloned but quarantined by Windows Defender

Cloning `sullo/nikto` succeeds, then `perl program/nikto.pl` returns `Permission denied` and the
file vanishes on the next `ls` — Defender removed `nikto.pl` (AV flags nikto). Docker daemon may be
off too. Record the class as covered by `nuclei exposures/misconfiguration` + `ffuf`, and note
"nikto unavailable (AV quarantine)" honestly instead of writing a negative scan result.

## Cloudflare Bot Management blocks scanner UAs (uniform 403 / stalled scans)

**Symptom:** `ffuf` returns an identical-size 403 (e.g. 5863 b, 668 words) for EVERY path —
real endpoints and 404s alike. `nuclei` against the same host stalls for many minutes with
empty output. Meanwhile `curl` with a browser UA gets normal app responses (200/401/500).

**Cause:** Cloudflare Bot Management fingerprints the default tool UAs (`ffuf/x.y`, nuclei's
default, python-requests) and serves a uniform challenge/403 at the edge — the scanner never
reaches the app, so its verdict is about the WAF, not the target.

**Fix:** pass a browser UA to every scanner: `ffuf -H "User-Agent: Mozilla/5.0 (Windows NT
10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"`,
same for `-H` on other curl-style tools. If nuclei still stalls on a CF-challenged host, kill
it and record the host as WAF-blocked (coverage limit), not clean. Heavy probing of one host
can also earn a soft per-IP limit (CF error 1006 on previously-fine paths) — rotate focus or
pause that host rather than reading the 1006 as an app behavior.

**Pattern:** uniform identical-size responses across different inputs = the WAF answering,
not the app. Before believing ANY scanner verdict, re-probe one known-good and one known-bad
path with a browser UA and compare.

## `dalfox` CDP event parse errors (local Chrome build mismatch)

**Symptom:** dalfox spams `ERROR: could not unmarshal event: unknown ClientNavigationReason
value: initialFrameNavigation` / `parse error ... cookiePart...` and spins without scanning.

**Cause:** dalfox's bundled CDP client is older than the local Chrome's DevTools protocol.

**Recovery:** this is a TOOL ERROR (rework), not a target negative — record it as such in the
coverage ledger and cover the XSS class another way (manual reflection differential: kxss to
find candidates, then verify encode-differential by hand — `"`→`%22`, `</script>`→`%253C`
— reflection alone is not a finding).

---
Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
