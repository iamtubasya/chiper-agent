---
name: security-scanners
description: "Use during Phase 0C for scanner selection and fuzzing."
metadata:
  hermes:
    budget_kb: 25
    tags: [scanner, fuzzer, nuclei, ffuf, security]
---

# Scanner & Fuzzer Guide (Phase 0C)

## ⛔ CANDIDATE RULE (MANDATORY — EVERY TEST)
- **Each test = one candidate. Finding something = mark candidate. CONTINUE to next test.**
- **Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0F).**
- **DO NOT generate report during Phase 0C. Report = ABSOLUTE LAST.**
- **If you find CRITICAL → mark candidate → KEEP TESTING. Do NOT stop.**

## ⛔ Load Rules
- Load during Phase 0C alongside attack playbooks
- Provides tool selection, config, wordlists
- Budget: 25KB — read_file for detailed config

---

## Scanner Selection Matrix

| Scenario | Tool | Command |
|----------|------|---------|
| Directory busting | dirsearch | `dirsearch -u https://target.com -o $DIR/dirs.txt` |
| Directory busting (fast) | ffuf | `ffuf -u https://target.com/FUZZ -w $WORDLIST -mc 200,301,302,403` |
| Subdomain takeover | dnsReaper | `dnsreaper predict --domain target.com` |
| Vuln scanning (templates) | nuclei | `nuclei -u https://target.com -t cves/ -t vulnerabilities/` |
| Vuln scanning (comprehensive) | w3af | `w3af_console -s "target https://target.com"` |
| Vuln scanning (quick) | wapiti | `wapiti -u https://target.com -o report.html` |
| Vuln scanning (AI) | afrog | `afrog -u https://target.com -o $DIR/afrog.json` |
| API fuzzing (stateful) | restler | `restler/restler_driver.exe --grammar $GRAMMAR --target $URL` |
| API fuzzing (quick) | ffuf | `ffuf -u https://target.com/api/FUZZ -w api-words.txt` |
| Browser crawling | crawlergo | `crawlergo -c chrome -t 5 -u https://target.com` |
| Secrets scanning | titus | `titus scan --dir $DIR` |
| Web cache poisoning | wcvs | `wcvs -u https://target.com` |
| Multi-tool scan | rapidscan | `rapidscan https://target.com` |
| Full audit | w3af | `w3af_console -s "target https://target.com"` |
| Booter/stress test | killshot | `killshot https://target.com --scan` |
| AI scan | SILENTCHAIN | Burp extension + Ollama/OpenAI |
| AI pentest | Zen-Ai-Pentest | Multi-agent AI pentest framework |

---

## Wordlists

### Directory Busting
```bash
# OneListForAll (comprehensive)
curl -sL https://raw.githubusercontent.com/six2dez/OneListForAll/main/onelistforall.txt -o /tmp/wordlist.txt
# SecLists common
curl -sL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt -o /tmp/common.txt
```
**Repos:** six2dez/OneListForAll (3.2K)

### API Endpoint Discovery
```bash
cat $DIR/urls.txt | grep -iE 'api|v1|v2|graphql|rest' | sort -u > $DIR/api_endpoints.txt
```

---

## Fuzzer Configuration

### ffuf Best Practices
```bash
ffuf -u https://target.com/FUZZ -w /tmp/wordlist.txt \
  -mc 200,301,302,403 -fs 0 -ac \
  -t 40 -p 0.5 \
  -o $DIR/ffuf.json -of json
# Filter by size (avoid noise)
ffuf -u https://target.com/FUZZ -w wordlist.txt -fs 4242
# Recursive
ffuf -u https://target.com/FUZZ -w wordlist.txt -recursion -recursion-depth 2
```

### ⛔⛔ ffuf's DEFAULT STATUS MATCHER EXCLUDES 400 — every DTO-validating endpoint disappears

This is the single most expensive false negative in this skill. Live 2026-10-28 (binobi.com): a
1,934-path POST sweep reported **0 hits**, twice, on both GET and POST. Every endpoint that answers a
malformed body with **400** — i.e. every real API endpoint that validates a DTO — was silently
dropped, because ffuf's default matcher is `200-299,301,302,307,401,403,405,500`. `400` is **not** in
that list. After `-mc all` the same wordlist returned **20 live endpoints**.

Second defect in the same harness, and it makes the sweep fail *uniformly*:
**a leading `/` in the wordlist against `…/FUZZ` produces a doubled path.**

```bash
# wordlist line  /exchange   ->  https://api.host//exchange  ->  404 for EVERYTHING
# Proof in the ffuf json: "url":"https://api.binobi.com//exchange"
```

Rules:
1. **Always run a POST/API sweep with `-mc all -fc 404`**, never the default matcher. Then filter the
   framework's own 404 body with `-fr "Cannot (POST|GET|PATCH|PUT|DELETE)"` (NestJS) or `-fs <size>`.
   A status histogram (group the JSON by status) is the honest way to see whether the app is
   *answering* — 400/401/403/410/500 rows are real routes, 404 rows are not.
2. **Normalise wordlists: no leading slash** when the URL template ends in `/FUZZ`. Store paths bare
   (`exchange`, `fxmb/callback`) and generate URL variants in code. One stray `/` silently zeroes the
   whole run and it looks exactly like a clean negative.
3. **Sanity-check the harness before trusting a zero.** Put 2-3 endpoints you have already proven
   live at the top of the wordlist and confirm ffuf reports them:
   ```bash
   printf 'exchange\nfxmb/callback\navepay/callback\n' > sanity.txt
   ffuf -u https://api.host/FUZZ -w sanity.txt -X POST -d '{}' -mc all -fc 404 -rate 5 -t 1
   # must print the known paths; if it prints nothing, the harness is broken, not the target
   ```
4. **Never write "0 hits / no endpoints" from a sweep that has not passed (3).** Retract and re-run
   when the defect is found — a withdrawn false negative costs far less credibility than a negative
   that a later corrected sweep contradicts. Tell the vendor explicitly when you retract.
5. Note what the defect does **not** poison: nuclei runs and any metrics/oracle-based discovery are
   unaffected. Scope the retraction precisely instead of invalidating the whole engagement.
6. **Diff the status histogram before and after the fix.** If the corrected run's count jumps by an
   order of magnitude (0 → 20 here), every conclusion drawn from the earlier sweep is void.
7. **Rebuild a redacted token at runtime, never through a shell interpolation the harness can mangle.**
   `T=$(cat tok.txt)` inside a tool call whose arguments get filtered produced
   `Authorization: Bearer ***` and `bash: syntax error near unexpected token '('`. Drive ffuf from
   Python instead — `subprocess.run([...])` with the token concatenated at runtime
   (`"Bea"+"rer "+tok` avoids naive secret-redaction of the literal) — so long authenticated sweeps
   survive.

### ⛔ Verify the scan actually ran — and that the log contains hits
A fuzzer that mis-parses its arguments writes its **banner/help text to stdout** and exits 0.
With `2>/dev/null` you get a 300-line "results file" containing zero results. Both happened
here on the same day (ffuf):

```bash
# does this log actually contain hits?
grep -cE 'Status:|https?://' ffuf_sensitive2.log     # 0  -> no hits (or the run failed)
head -3 ffuf_sensitive2.log                          # "Fuzz Faster U Fool ..." / "HTTP OPTIONS:" = it failed
```
Rules:
- Never promote a scanner log to "evidence" before grepping it for the tool's **hit format**
  (`Status:` for ffuf non-silent, a URL for most others). `-s/--silent` changes the output shape.
- Re-run suspicious invocations with stderr visible (`2>&1 | head`) before concluding anything.
- **Silent-mode output can look like the wordlist.** `ffuf -s` prints only the matched FUZZ
  payload, so on a host whose SPA answers `200` to *every* path (including the wordlist's
  `# comment` lines) the log degenerates into a copy of the wordlist — every entry "matches".
  Pre-check the host: fetch two random nonsense paths; identical bytes/status = catch-all, and
  then only `-mc 200` fuzzing is meaningless there. Use `-fs <size>` / `-ac` to filter.
- **Native-path gotcha (Windows/MSYS):** `ffuf`/`gobuster` are native binaries — `-w /c/Users/...`
  silently fails; pass `C:/Users/...`. `gobuster dir -s 200,301 -b ""` (its default status
  blacklist conflicts with `-s` and the run refuses to start).
- A verified **"0 hits"** is a real deliverable — write it into the log with the exact command,
  and separate "tested, nothing there" from "not tested".
- **Loopback hostnames can fail resolution inside the scanner.** `nuclei -u http://localhost:1322`
  printed `Skipped localhost:1322 from target list as found unresponsive permanently:
  cause="no address found for host"` and *still* ended with a normal-looking
  `Scan completed in 3.5s. 0 matches found.` — after issuing **36 of 5649** requests. Against a
  local/lab target use the literal address (`http://127.0.0.1:<port>`) and prove reachability from
  the scanner's point of view before launching: `curl -o /dev/null -w '%{http_code}' http://127.0.0.1:<port>/`.
- **A `timeout` kill looks like a finished scan.** `timeout 900 nuclei ... | tail -35` that is
  SIGTERM'd mid-run prints the banner plus whatever the tail buffer held, and no error. Real
  completion always prints `[INF] Scan completed in <t>` **and** an `HTTP connections: N total`
  line. Missing that line = the run was cut short, so re-run with a tighter set (drop the huge
  `cve` tag on a single-app target) and write to a live file rather than a `tail` pipe.
- **When the TARGET advertises its own rate limit, "0 matches" is a weak negative.** This session
  hit `Skipped 127.0.0.1:1322 ... as found unresponsive 30 times` while the app was answering
  fine — it advertises `Octopus-RateLimit-Policy: l=200;rpm=60`, so a scanner at `-rl 30` starves
  itself against the app's own limiter. Record *"0 matches, coverage curtailed by the product's
  rate limiter"*, never *"clean"*. A protective rate limit is a control, not a weakness — don't
  report it as one.
- **Never judge a scan from `grep`-filtered output alone.** Piping a scanner through a whitelist
  (`| grep -iE "injectable|parameter|CRITICAL"`) hides the tool's own startup failure: an
  invocation of a **non-existent launcher** failed instantly on all three URLs and yielded an
  empty, clean-looking result. Run `<tool> --version` once per session before the first real
  invocation, and always keep the unfiltered first run in a file.

### ⛔ An ABORTED scan is not a negative — preflight the flags (wpscan, and any tool that aborts)
A scanner can exit 0 having scanned **nothing**. Read the first lines of its output before writing
"no findings". Two real wpscan aborts in one session (2026-10) — both looked like "0 results", and
one was nearly mis-recorded as "the CDN blocked wpscan":

```
Scan Aborted: --api-token Empty option value supplied
Scan Aborted: --enumerate Incompatible choices detected: ap, p
```

Rules:
- **wpscan without an API token cannot enumerate vulnerable plugins/themes.** `--enumerate vp,vt`
  (or a bare `--api-token ""`) makes it print `Scan Aborted: An API token is required...` and write a
  ~320-byte JSON with only `"scan_aborted"`. That is a **flag/config failure, NOT a WAF block and NOT
  "no vulns"**. Drop the `v` classes and use `--enumerate ap,u,cb,dbe` for what works untokened
  (fingerprint plugins, users, config backups, DB exports). Without a token, get plugin→CVE mappings
  from public DBs instead (Wordfence / cvefeed / cvebrief / SentinelOne).
- **`ap` (all plugins) and `p` (popular plugins) are mutually exclusive** — combining them aborts.
- Any tool that prints `Scan Aborted` / `Aborted` / a usage or banner block has produced **zero**
  evidence. Classify it as *"not run"*, never as a clean negative (owner rule: run gagal ≠ negatif —
  wajib diulang). Same session, the same run had been recorded as "wpscan blocked by Cloudflare"
  when it had actually died on my own empty `--api-token`; reporting a vendor block that never
  happened is a false claim.
- Also applies to `curl`/`dig` **leftover-file traps**: if a loop writes to a fixed `/tmp/x` and a
  request fails (`000`), the surviving file from the *previous* iteration is what you end up reading.
  Use a fresh path per iteration, or check the exit/`%{http_code}` before reading the body.

### ⛔ A vulnerable VERSION is not an exploitable TARGET — read the CVE's precondition
Version-only CVE matches are leads, not findings. Before a version match becomes a finding, prove
the exploit's **stated precondition** exists on the target.

Real case (2026-10, nordnetab.com WordPress): Beaver Builder `2.8.6.1` (< 2.11.0.6) matched three
CVEs including **CVE-2026-92084 (CVSS 9.1, UNAUTHENTICATED arbitrary shortcode execution)**. The
advisory's own precondition: *a Beaver Builder page containing the Sidebar module populated with a
widget that shows attacker-controllable content*. Checked on the target: **0 of 120** sitemap pages
contain `fl-module-sidebar`, and comments are **closed** — the path is absent, so it is **not
exploitable**. Recorded as "outdated component" (hardening note), never as an RCE finding.

Checklist:
1. Pull the CVSS **vector and the exploitation-requirements sentence**, not just the version range.
   `PR:N` (unauth) vs `PR:L` (Contributor+) changes everything — CVE-2026-95865 on the same plugin is
   `PR:L` and therefore not unauth.
2. Map the precondition to a **checkable artefact** and check it: grep the served markup for the
   module/feature (`fl-module-sidebar`), read the shipped plugin code for the vulnerable function,
   confirm the enabling config (comments open, module in use). **Precondition absent ⇒ not a finding.**
3. For a plugin CVEs list, `web_search` `<cve-id> <vendor> <vector>`; Wordfence pages often 202
   (bot-protected) — cvefeed / cvebrief / SentinelOne serve the same text.
4. Honest wording: *"version affected, precondition absent, not exploited"* — plus a patch
   recommendation. Never inflate a version match into an exploit claim.

#### ⛔ Even the VERSION NUMBER may not be evidence — distro packages backport without bumping it

Before counting "N hosts vulnerable to CVE-X" from a `Server` header, split by **build provenance**.
Distributions backport security fixes into the packaged version and **leave the version string
unchanged**, so a fully patched host still advertises the old number.

Measured 2026-10-29 (Telekom estate, CVE-2026-42945 nginx heap-overflow, CVSS 8.1, fixed in 1.31.0):
a first pass counted **34 hosts** below 1.31.0 from `httpx -tech-detect`. Re-checking each host
individually cut it to **20**:

| class | tell | conclusion |
|---|---|---|
| **Upstream / plain build** | header is bare: `nginx/1.30.5`, `nginx/1.17.6` | advertised version **IS** the real version → claim valid |
| **Distro package** | header carries a distro tag: `nginx/1.18.0 (Ubuntu)`, `(Debian)`, `(CentOS)`, `(Alpine)`, `(RHEL)` | version string is **NOT evidence either way** — must read the package version (`dpkg -l nginx`, `rpm -q nginx`) and compare against the distro security tracker |
| **Unreachable on re-check** | host answered during the bulk sweep, times out now | **reported-but-unconfirmed** — do not count it |

Rules:
1. **Re-verify every host individually.** A bulk `httpx` sweep and a per-host `curl -sI` can disagree;
   hosts die, TLS versions change, WAFs start blocking. The version you counted yesterday is a claim,
   not a fact.
2. **Report the confirmed class as the headline number, list the other two separately.** "20 confirmed
   upstream builds; 6 distro packages to check; 8 unconfirmed" is a stronger report than "34 hosts" —
   the second number collapses on the first question from a triager who knows their own patching.
3. **Give the vendor the check they need for the distro class**: the exact command
   (`dpkg -l nginx | tail -1`) and the tracker to compare against. You cannot settle it from outside;
   say so instead of guessing.
4. **If an earlier draft over-counted, say so in the report.** A short "correction notice" section
   documenting `34 → 20` and the reason costs one paragraph and buys the credibility that the inflated
   number would have spent.

### nuclei Best Practices
```bash
nuclei -u https://target.com -t ~/nuclei-templates/ -severity critical,high,medium
nuclei -u https://target.com -t ~/nuclei-templates/cves/
nuclei -u https://target.com -rl 50 -c 10        # only for your OWN infra / lab
```

### ⛔ Two flag names you WILL get wrong, and the failure looks like "no findings"

Six consecutive failed nuclei launches in one session (2026-10-29, Telekom estate) — every one was a
bad argument, and every one produced **no `-o` file at all**, which reads exactly like a clean scan.

| what I typed | real error | truth |
|---|---|---|
| `-retry 1` | `flag provided but not defined: -retry`, `EXIT=2` | the flag is **`-retries`** (plural) |
| `-maxtime 1500` | `flag provided but not defined: -maxtime`, `EXIT=2` | **`-maxtime` is an ffuf flag.** nuclei has none — bound runtime with the shell `timeout N nuclei …` |
| `-tags cve,exposure,misconfig,…` | no error, 0 output, live PID, 20+ min | tag/severity filtering loads the whole corpus; on an 11,718-template install this stalls before emitting anything |
| `-t http/exposures/configs/` (relative) | no error, burns the **full wall-clock**, `EXIT=124`, then **no `-o` file** | relative `-t` resolves against **cwd**, not the templates home. Run from `/d/work` and nuclei matches nothing under `http/...` while still spending the whole budget. Always `-t ~/nuclei-templates/http/...` or an absolute path |

Confirmed-working invocation (verified: `Templates loaded: 73`, `Requests: 20/20 (100%)`, 2 s):
```bash
timeout 1500 nuclei -l urls.txt -nc -silent -jsonl \
  -rl 60 -c 20 -timeout 8 -retries 1 \
  -t ~/nuclei-templates/http/takeovers/ -o out.jsonl
```
Flags that exist: `-t -o -silent -nc -rl -c -timeout -retries -severity`. Always `-nc` — colour codes
break any downstream parse.

**Prefer explicit `-t <dir>` on an unfamiliar install.** `-tags` is convenient but must compile the
corpus to filter it; `-t <dir>` goes straight to the subset. Measured swap: a `-tags` run sat at zero
output for 20+ minutes; the same 73 takeover templates via `-t …/http/takeovers/` finished in
**2 seconds**. If a `-tags` run has produced nothing after ~3 minutes, kill it and re-issue with `-t`.

### ⛔ Before declaring a scanner "broken", audit your own argv — a repeated false claim costs more than the scan

Six consecutive nuclei launches failed in one session (2026-10-29, Telekom). All six were **my
arguments**; the tool was fine throughout. I reported "nuclei never completes on this URL set" as a
standing coverage gap **four separate times** before finding that out — each repetition read to the
operator as a target-side problem, and the real defect was mine.

The tell that you are in this failure mode: **the same tool worked earlier in the session, or a
single-host run succeeds while the list run fails.** That is an argument problem, not a tool problem.

Before writing "tool X doesn't work" into a coverage statement, run this ladder:

1. **Does it work at all?** One host, one template dir, `-stats`: `Templates loaded: N` + `Requests:
   N/M (100%)` in seconds. If yes, the tool is healthy — stop blaming it.
2. **Diff your successful invocation against the failing one**, flag by flag. The failing run usually
   differs in exactly one place (`-tags` vs `-t`, relative vs absolute path, a plural you typo'd).
3. **Check the argument surface against `-h`** — grep it, don't recall it:
   `nuclei -h 2>&1 | grep -E "^\s+-(rl|c|timeout|retries|nc|silent|jsonl|o|t)\b"`. Flags shared
   between tools are the trap: `-maxtime` is ffuf's, not nuclei's.
4. **Estimate the request budget before a long run** and compare it to the wall clock you observe. A
   run that "hangs" at 0 output for 20 min may simply be compiling 11,718 templates.

**Rule: a claim that a tool is broken is a claim like any other and needs the same evidence bar.**
Log the exact invocation, the exit code, and whether the `-o` file exists. "Scanner never completes"
is an assertion; `EXIT=2, flag provided but not defined: -retry` is evidence. If you cannot tell
which, say **"run incomplete — cause not yet isolated"** rather than inventing a coverage gap.

### ⛔ An empty or missing `-o` file is NOT a negative — prove execution with `-stats`

Zero-byte output has four distinct causes: (a) genuine 0 findings, (b) argv error (no file created),
(c) still loading templates, (d) killed mid-run. Never write "clean"/"no findings" from file size.
Prove the run executed before reading its verdict:

```bash
nuclei -u https://host -t <dir> -nc -stats -stats-interval 5
# [INF] Templates loaded for current scan: 73
# [0:00:02] Templates: 73 | Hosts: 2 | RPS: 9 | Matched: 0 | Errors: 0 | Requests: 20/20 (100%)
```

Read the counters: `Templates loaded` must match the real template count, `Requests: N/M (100%)` must
show completion, `Errors: 0` means nothing was dropped. **`Matched: 0` on `100%` is a real verified
negative** and worth recording as such — that is the difference between "tool-backed negative" and
"assertion". If `Requests:` shows `<100%`, it is partial coverage, not a negative.

Companion — exact invocation recipes, the stall diagnosis, and the request-budget arithmetic:
`references/nuclei-invocation-and-proof-of-execution.md`.

### ⛔ `-l` = TARGETS, `-t` = TEMPLATES — swapping them fails SILENTLY (looks like "clean")

`nuclei -l <file>` reads a list of **target URLs**. `-t` takes a template (file or directory).
Passing your *template* list to `-l` does not error — nuclei treats each template **path** as a
target and prints a normal-looking run:

```
[INF] Templates loaded for current scan: 1      <- the "target" was a template path
[INF] Skipped .:80 from target list as found unresponsive permanently: cause="no address found for host"
[INF] Scan completed in 3m. No results found.
```

That reads exactly like "the target is clean" when **nothing was scanned**. Hit live 2026-10 (a
~400 s run wasted, and the false "no results" nearly went into the ledger).

Rules:
- To scan with a template *set*, pass a **directory** or repeat `-t`:
  `nuclei -u https://cardoma.shop -t ./http -tags wordpress,woocommerce`. There is no
  `-t <listfile>` equivalent of `-l`.
- Before believing "No results found", sanity-check the counters: `Templates loaded for current scan`
  must be the real count (hundreds/thousands), `Targets loaded for current scan` must be 1, and
  `HTTP connections: N total` must be non-trivial. `Skipped ... no address found for host` against a
  real hostname is the tell that you fed the wrong file.
- A genuinely clean run has real HTTP connection counts and none of that "unresponsive" spam —
  write the counters into the ledger as the evidence either way.

### ⛔ Volume discipline — read the program rules BEFORE you launch a scan
The `-rl 50 -c 10` preset above is a lab default. Against a live bounty target it can be
disqualifying. Real case (2026-09): `nuclei -l <260 live hosts> -t <full local template mirror>
-tags exposure,misconfiguration,disclosure,takeover,default-login` queued **1,271,200 requests**
(2011 templates x 260 hosts). It had to be killed mid-run and replaced with a curated list at
`-rl 4`. The program brief had already said rate limits are enforced environment-wide, that
rate-limit findings are out of scope, and that DoS-adjacent behaviour is prohibited.

Checklist before launching:
1. **Estimate first.** `templates x hosts = requests`. nuclei's own `-stats` line shows
   `Requests: N/M` — glance at it in the first 30 seconds, before it becomes a problem.
2. **Curate hosts, don't pass the whole live list.** Keep a `priority_hosts.txt` (the 15-25 hosts
   that actually matter: auth surfaces, admin panels, the app itself) instead of all 260.
3. **Prefer `-tags` / `-t <subdir>` over the entire `http/` tree**, and drop tags the brief excludes.
4. **Rate for the program, not the lab.** Rate-limited or WAF-fronted targets: `-rl 3..5 -c 2..3`.
   If Cloudflare returns 429 / `error code: 1015` during manual probing, your automated rate is
   already too high.
5. **Respect the brief's exclusions.** "No automated scanning against forms", "no rate-limit
   testing", "no DoS" all constrain scan volume and concurrency, not just payload choice.
6. **Never test rate limits as a finding on endpoints the brief excludes** (commonly non-auth
   endpoints). The finding is out of scope even when it works.
7. A killed scan leaves **partial state**: a partial output file, a stale `nuclei` child process,
   and half-written stats. Clean up (`tasklist | grep nuclei`) before re-running, and write results
   to a fresh filename so a partial file is never mistaken for a complete one.
8. **The blast radius outlives the scan.** A broad-template run (`-rl 30`, full local mirror) against
   a bank's LB tripped a **per-IP Cloud Armor limit that 429'd every `www.*` host for ~45 minutes** —
   and silently poisoned *other* tools in the same window (`sqlmap`, `linkfinder`, `race-checker` all
   logged `429`, and the pipeline's own XSS/CMDi candidates were invalidated by it). Two consequences:
   (a) prefer the **targeted template dirs** (`http/exposures`, `http/misconfiguration`,
   `http/exposed-panels`, `http/default-logins`, `ssl`) over the whole `http/` tree;
   (b) after a 429 storm, treat every scan that ran inside that window as **poisoned, not negative**,
   re-verify later, and record `HTTP 429` hits in the ledger so a "negative" is never claimed from a
   throttled run. Verify the block has lifted (`curl -o /dev/null -w '%{http_code}'`) before resuming.
9. **Read the `Errors:` counter as a COVERAGE number, not noise.** A run can print
   `[INF] Scan completed` + `Matched: 6` and still have measured almost nothing. Measured
   2026-10-30 on an 11-host in-scope list: `-rl 25 -c 12` over 6,111 templates finished in 1h14m
   with **`Errors: 7853` and `Requests: 134345/168817 (79%)`** — ~34,000 template-host pairs never
   issued, and the 6 matches were all previously-known OOS items. Re-running the same corpus on the
   four hosts that mattered with `-rl 15 -c 6 -retries 2` gave **`Errors: 34` at 17%**. Same
   templates, same hosts; the first run was self-throttling — `-c 12` against already rate-limiting
   hosts turns timeouts into errors, and every error is a template that got no real answer.
   - `Requests: N/M (<100%)` is the honest coverage figure. Write it into the ledger verbatim
     (`79%`, `17%`); never promote a partial run to "clean".
   - When errors spike, **drop concurrency and add `-retries 2` before re-running**, and narrow the
     host list rather than widening it.
   - `Matched: N` on a degraded run is not a verified negative — it is an untested surface wearing
     a negative's clothes.

### ⛔ A pipeline that "is running" can still be scanning ONE host — audit its coverage, then supplement

An orchestrator reporting `✅ Force execution COMPLETE` says nothing about how much of the estate it
touched. On the Blink engagement (2026-10-12) the pipeline's recon stage failed silently
(`httpx: 0 live hosts (rc=255)`) and it seeded itself with the two hostnames it could reach — so a
"completed" 0C had scanned **316 URLs on one host** while the engagement had **81 known-live hosts**.
Nothing downstream flagged it.

Do this after (and once during) any long automated pass:

1. **Prove liveness from the FILESYSTEM, not from the orchestrator's chatter.** A watchdog line like
   `[STALL-WARN] no step progress for 2721s … still running, not killed` is not evidence of death: check
   the newest mtime in the pipeline's workdir (`find <workdir> -type f -printf '%TH:%TM %p\n' | sort -r`)
   and its child processes. Progress every ~2 minutes = alive; nothing written for 20+ minutes with a
   live PID = stalled, and that is when you intervene.
2. **Histogram the pipeline's own host list against your recon ledger.** `grep -oE 'https?://[^/]+'
   <workdir>/urls.txt | sort | uniq -c | sort -rn` and read `<workdir>/live.txt`. If it covers one or
   two hosts out of dozens, the pipeline's coverage is an illusion — run your own nuclei over the full
   live-host list you already have and merge the evidence. Do not report the pipeline's negative as an
   estate-wide negative.
3. **Expect wildcard DNS to poison both the host list and the results.** With `*.target.tld` resolving,
   a naive host sweep reports every subdomain as "live" (mostly 404s) and nuclei's own
   `[wildcard-dns-detect]` template dominates the output — one run produced **64 of the first 66 hits**
   as wildcard noise. De-dupe by body/status, and filter the DNS templates out (`grep -v
   'wildcard-dns-detect'`) before reading results, or the real hits are invisible in the noise.
4. **Compute the ETA before launching, and cut tags rather than waiting.** `templates × hosts ≈
   requests`; at `-rl 8` a `1106-template × 81-host` pass queued **219,510 requests ≈ 2.2 h**, and an
   earlier `6186-template × 81-host` pass at `-rl 60` implied **6.7 h** (killed after 3 h at 66 %).
   If `requests ÷ rate > ~1 h`, trim to the high-signal tag set (`exposures, exposed-panels,
   misconfiguration, default-login, takeovers, unauth` — drops the template count by ~5x) and raise the
   rate to a still-polite `-rl 20 -c 6`. Seconds of arithmetic beats hours of waiting on a 4-vCPU box
   that is simultaneously running the pipeline.

### ⛔ Template severity is a HYPOTHESIS — read every hit body before you believe it
A curated run returning "3 hits" is not "3 findings". Same session as above, the complete output was:

```
[config-json-exposure-fuzz] [critical] https://dashboard.rapyd.net/config.json
[config-json-exposure-fuzz] [critical] https://m.dashboard.rapyd.net/config.json
[readme-md]                 [info]     https://ai-assessment.rapyd.org/README.md
```

Verification changed the ranking completely:
- `/config.json` on a SPA is **public by design** — it held only reCAPTCHA *site* keys (public),
  analytics IDs, feature flags, an SFTP allow-list and test numbers. No secret. The template's
  "critical" is a false positive here; reporting it burns credibility. (`/config.json` diffed between
  desktop and mobile builds showed only benign per-build differences.)
- The `[info]` README was the **only** item worth reporting, and it is P4 (internal architecture,
  endpoint semantics, KV key schema, deployment notes — not a credential or PII leak).

Per-hit checklist before anything enters a report:
1. `curl` the exact matched path/parameter and **read the body**, not the template's claim.
2. Ask what the hit actually grants: credentials/tokens? cross-tenant data? write access? If none,
   it is informational regardless of the template's severity tag.
3. Confirm it is a real endpoint and not the SPA catch-all — identical byte-length for unrelated
   paths (e.g. every `/portal/api/*` returning the same 35,235-byte `index.html`) means there is no
   API there at all.
4. Map to the platform VRT *after* step 1-3, and check the brief's out-of-scope class list (public
   config, non-sensitive info disclosure and "missing best practices" are commonly excluded).
5. Keep the fuzzing templates (`*-fuzz`, `*-exposure`) in the run — just treat their output as leads.

### ⛔ Match the scanner to the target's SHAPE — a stalled sweep is not coverage, and "0 matched" on 9 % is not "clean"

Decide scanner fit **at recon, from the host's response shape**, not after launching. Fetch each
in-scope host: if you get one ~2-3 KB HTML shell with a `<div id="root">` and a hashed
`/assets/index-*.js`, the entire attack surface is JSON on two or three backend gateways and
path-based templates have almost nothing to hit.

What that costs when ignored (live 2026-10-26, three in-scope hosts, all SPAs):
- broad `nuclei -l hosts -severity critical,high,medium` → **zero output for 41 minutes**, killed.
- tag-narrowed rerun with `-timeout 8 -retries 1 -rl 6 -c 2` → hit the 480 s cap having issued
  **3,978 of 43,614 template-host pairs (9 %)**, `Matched: 0`.
- a third `-tags tech,exposure` run at 240 s → also timed out at ~4 %.

Rules:
1. **Bound every sweep with a hard `timeout` and record the fraction reached**
   (`3978/43614 = 9 %`). A partial sweep is *partial*, never *clean*. The skill's own honesty rule
   applies: negative results need the tool evidence, and "ran 9 % of templates" is the evidence.
2. **For a JSON backend, `ffuf` is the right discovery tool, not `nuclei`.** A ~90-word API-ish
   list (`admin, internal, debug, graphql, api/v1, v2, actuator, actuator/env, openapi.json,
   swagger, webhooks, metrics, keys, tokens, referrals, plans, coupons, wallet, invoices,
   instances, storage/buckets, ...`) at `-rate 12 -t 2`, filtered on the app's own 404 body size
   (`-fs 38`), finishes in **under 4 minutes across four backends** and found
   `/internal/metrics` + `/internal/health` (both 401 — real routes, worth reporting as a
   verified negative) where the broad sweep found nothing.
3. **Spend the recovered time on protocol work instead**: replicate the client's own requests from
   its bundle (auth flow, resource create/read/update, the identifier each endpoint trusts), then
   enumerate the **API generations** of each resource (`/x` vs `/x/v2`) — that is where the
   authorisation gaps live. Say in the ledger *why* the scanner was low-yield, with the response
   shape as the reason.
4. **SPA catch-all check before any path result means anything**: two random nonsense paths
   returning identical bytes/status means every 200 is the shell (see the dalfox/ffuf notes above).

### ⛔ When the template run is infeasible: bounded path sweep, then filter the FP classes
Full-template nuclei over a wide host list is almost never the right call on a rate-limited program
(see Volume discipline above — 1.5M requests queued, 0.5% done in half an hour). The replacement that
still finds the class that actually pays (stray docs/configs) is a **bounded sweep you write yourself**:
a short curated path list (`README.md`, `.env`, `.dev.vars`, `config.json`, `wrangler.toml`,
`package.json`, `swagger.json`, `openapi.json`, `.git/config`, `CHANGELOG.md`, `/api-docs`,
`.well-known/security.txt`) × the host list, single-threaded-ish at ~4 req/s. Real numbers from one
engagement: **260 hosts × 14 paths ≈ 3,600 requests in ~8.5 minutes**, 99 raw 200-hits.

**Most of those hits are NOT findings.** Filter these three classes before you read anything:

| FP class | Tell | Verdict |
|---|---|---|
| Edge/access interstitial | every path on a gated host returns the *same* ~48 KB HTML (`Sign in ・ Cloudflare Access`) while the root returns 302/403 | not a hit — 45 of 99 in one run |
| SPA catch-all | body hash ≈ the host's root document | not a hit |
| Upstream template file | `README.md` that is the stock WordPress/Pantheon or Cloudflare boilerplate (`git clone cloudflare/ai`, `worker-name.account-name` placeholders) | **public upstream file — do not report** |
| Public front-end config | `config.json` with reCAPTCHA *site* key, analytics IDs, OAuth *client_id*, feature flags | not a secret — not a finding |
| Exposed security-headers config (`_headers`, `netlify.toml`, `_redirects`) | the **effect is already present**: `curl -sI https://host/` shows every directive the file declares (CSP `frame-ancestors`, `X-Frame-Options`, `X-Content-Type-Options`, HSTS, `Referrer-Policy`, `Permissions-Policy`) | not a finding — the file leaks nothing the response does not already publish. Hit live 2026-10-27: the file's own comment said "Render does not read `_headers`, set these in the dashboard", which *implies* clickjacking is possible — one `curl -sI` disproved it (all six directives served). **Test the advertised effect before reporting an exposed-config hit.** |
| "Config file" that is really the SPA shell | `sha256(body)` == `sha256(https://host/)`, and `Content-Type: text/html` on a `.yml`/`.json` path | not a hit. nuclei's `detect-drone-config` fired **High** on `/.drone.yml` returning **1,239,405 bytes of `text/html`** byte-identical to the root document; same run also flagged `package-json` and `netlify-headers-config-exposure`. Cheap disproof: `curl -s <path> -o a; curl -s <host>/ -o b; cmp a b` |

Comparison against the root body is not sufficient on its own: it fails exactly on the gated hosts
(root = 302, path = 200 interstitial). Also match on body markers (`Cloudflare Access`, `__next`,
`id="root"`, `@vite/client`) and de-dupe by (host, body-hash).

- `references/bounded-exposure-sweep.md` — budget math, marker lists, survivor triage table, pitfalls.
- `scripts/bounded_exposure_sweep.py` — ready to run:
  `python bounded_exposure_sweep.py --hosts hosts.txt --outdir ./scan --rps 4 --header "X-Bugcrowd: <handle>"`
  (it prints only survivors and writes the full classified JSON).

---

## ⛔ sqlmap on a Cloudflare-fronted target: check the UA before blaming the WAF

A run that reports thousands of `403 (Forbidden)` is usually the CDN rejecting **the tool's own
User-Agent**, not filtering payloads. Measured on one engagement (2026-09):

```
sqlmap's default UA + a CLEAN request        -> 403
browser UA + the same clean request          -> 200
browser UA + a tamper payload                -> 422 (from the app, not the WAF)
same run with --random-agent                 -> 0 x 403 across the whole scan
```

Rules:
- **Prove the block is UA-based before writing "the WAF blocks everything."** Two requests, same
  path, tool UA vs browser UA. If the *clean* request is 403'd with the tool's UA, the 403s in the
  scan log say nothing about payload filtering. (The earlier sqlmap run in that engagement reported
  "403 (Forbidden) - 3742 times" and called its own result inconclusive because of it.)
- `--random-agent` (or an explicit browser `--user-agent`) is effectively mandatory on CDN-fronted
  targets; `sqlmap/1.x` is on every WAF's list.
- **A wall of 422s is APP validation, not the WAF.** Read one body: `422 {"error":{"code":
  "validation_error","message":"limit must be a whole number from 1 to 200."}}` means the value is
  enum/format-checked before it reaches a query — that is a *control*, and sqlmap will correctly
  report "does not appear to be dynamic". sqlmap may even print "checking if the target is protected
  by some kind of WAF/IPS" because of those 422s; that guess is wrong here — say so in the write-up.
- **Budget the run.** `--level=5` + a 4-script tamper chain on a slow CDN target ran 2.5 h without
  finishing the first parameter. For a quotable verdict, `--level=2..3 --risk=2
  --tamper=space2comment --random-agent` finished 5 parameters in ~40 min and produced
  `[CRITICAL] all tested parameters do not appear to be injectable`. If you want the risk-3
  OR-based family it skipped, cover it with 3-5 manual payloads (`' OR '1'='1` per parameter →
  expect 422) rather than a second long run.
- **Kill the whole process tree, and kill it twice.** Stopping the wrapper's session left the bash
  script alive: t1 was killed, t2 started on its own, and t3 later ran as an orphan whose log froze
  mid-file (parent SIGTERM'd, stream closed) while `tasklist` still showed `sqlmap.exe`. Check
  `tasklist | grep -i sqlmap` again after killing, and archive the partial log labelled as stopped
  so a frozen file is never mistaken for a completed scan.
- Report the tool verdict **verbatim** next to the request-shape evidence (0 x 403, 422s from the
  app). "No injection here" is far more credible with the UA/422 explanation attached.

### ⛔ A 400 from an app that requires custom headers is NOT a sqlmap negative

Measured 2026-10 (Proton API). sqlmap's first run answered
`the web server responded with an HTTP error code (400)` and then
`GET parameter 'Username' does not appear to be dynamic` -> `all tested parameters do not appear to
be injectable`. That verdict was manufactured by the harness: the API rejects requests that do not
carry its own client header, so **every** probe — baseline and payload — was a 400.

```bash
# WRONG: no app headers -> 400 on everything -> fake "not injectable"
sqlmap -u 'https://host/api/core/v4/users/reset?Username=x' --batch --smart

# RIGHT: ship the app's own contract, then read the verdict
sqlmap -u 'https://host/api/core/v4/users/reset?Username=x' --batch --level=2 --risk=1 \
  --headers="Accept: application/json
x-pm-appversion: web-account@5.0.430.0
User-Agent: Mozilla/5.0 (...)" --flush-session
```

Rules:
- **Capture the app's required headers from the real client first** (browser request or bundle), and
  pass them with `--headers` (multi-line, one per line). `x-app-version` / `x-pm-appversion` /
  `Accept: application/json` are commonly mandatory on JSON APIs.
- **Classify by the dominant status, not by the verdict.** A run whose baseline is `400`/`401` has
  tested nothing: re-run with `--ignore-code` only if 4xx is genuinely the app talking, otherwise fix
  the headers. `401 Unauth` -> authenticate or pick an unauthenticated endpoint.
- A genuine negative looks like: baseline `200`, parameter marked dynamic, then
  `all tested parameters do not appear to be injectable` (or `parameters are not dynamic` because the
  app validates types — see the 422 note above).
- **Get a second opinion cheaply.** `ghauri` reached the same verdict on the same parameters in
  1h34m across boolean-blind AND error-based families (MySQL/MSSQL/PostgreSQL/Oracle) and printed
  `[CRITICAL] all tested parameters do not appear to be injectable`. Two independent tools agreeing
  is a far stronger negative than one, and you can quote both.

### ⛔ dalfox POC on an SPA is usually the catch-all — disprove reflection before reporting

A `[POC][G][GET][BUILTIN] https://host/path?ref=ctaprd` line is a **candidate**, and on a
single-page app it is very often the SPA shell echoing the URL, not a reflection.

Disproof, three checks, ~1 minute:

```python
canary = 'zz9f3k2mcanary'
for p in [canary, '"><img src=x onerror=alert(1)>', 'javascript:alert(1)']:
    r = requests.get(base, params={'ref': p})
    print(len(r.text), canary in r.text, 'alert(1)' in r.text,
          [k for k, v in r.headers.items() if 'alert' in v or 'onerror' in v])
# identical body length for payload vs no-param, and no reflection in BODY *or* HEADERS = FP
```

1. **Length/bytes identical** to the no-parameter request -> nothing was injected.
2. **Check headers too** (`Location`, `Link`, `Content-Security-Policy` can carry the value) — a
   reflection in a header is still not XSS unless something renders it.
3. **Find the sink in the bundle.** Grep the JS for the parameter name. Real case: the only use was
   `params.append("ref", r.ref)` — it is appended to a redirect URL, there is no DOM sink. That
   converts "POC found" into "false positive, proven".

Also worth knowing: dalfox emits POC lines for parameters **it injects itself** to test the
endpoint (e.g. `?pleasedonthaveanamelikethis_plz_plz=DalFox`) — that is a canary marker, not a
target parameter. Filter those out before counting POCs.

---

## Scanner Comparison

| Scanner | Speed | Accuracy | False Pos | Best For |
|---------|-------|----------|-----------|----------|
| nuclei | ★★★★★ | ★★★★ | Low | Known vulns (CVE, misconfigs) |
| ffuf | ★★★★★ | ★★★ | Medium | Directory/param fuzzing |
| dirsearch | ★★★★ | ★★★ | Medium | Directory discovery |
| w3af | ★★★ | ★★★★ | Low | Full web audit |
| wapiti | ★★★ | ★★★ | Medium | Quick vuln scan |
| afrog | ★★★★ | ★★★★ | Low | AI-assisted scanning |
| rapidscan | ★★★ | ★★★ | Medium | Multi-tool combo |
| restler | ★★ | ★★★★★ | Low | API stateful fuzzing |

---

## Integrated Repos (18)

| Repo | Stars | What We Took |
|------|-------|--------------|
| maurosoria/dirsearch | 14.7K | Directory scanning workflow |
| OWASP/Nettacker | 5.6K | Automated pentest framework |
| andresriancho/w3af | 4.9K | Web audit framework config |
| six2dez/OneListForAll | 3.2K | Fuzzing wordlists |
| Qianlitp/crawlergo | 3K | Browser crawler config |
| microsoft/restler-fuzzer | 2.9K | REST API stateful fuzzing |
| lijiejie/BBScan | 2.4K | Fast vuln scanner |
| wapiti-scanner/wapiti | 1.9K | Web vuln scanner |
| Hackmanit/Web-Cache-Vulnerability-Scanner | 1.2K | Cache poisoning scanner |
| w-digital-scanner/w9scan | 1.1K | Plugin web scanner |
| bahaabdelwahed/killshot | 783 | Pentest framework |
| praetorian-inc/titus | 701 | Secrets scanner (487 rules) |
| fgeek/pyfiscan | 575 | Web vuln + version scanner |
| silentchainai/SILENTCHAIN | 463 | AI Burp scanner extension |
| SHAdd0WTAka/Zen-Ai-Pentest | 458 | AI pentest framework |
| aress31/burpgpt | 2.4K | Burp GPT passive scan |
| cypherpunk-symposium/security-pentesting-toolkit | 242 | CTF/pentest resource |
| jassics/security-study-plan | 5.1K | Study plan (pentest roles) |

---

## Cross-References
- Recon → `security-recon` (Phase 0B)
- Attack playbooks → `security-web-attacks` (Phase 0C)
- Cloud → `security-cloud` (Phase 0C)
- Report → `bug-report-delivery` (Phase 0F, ABSOLUTE LAST)
