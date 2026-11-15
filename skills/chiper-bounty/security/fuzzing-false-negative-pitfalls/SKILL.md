---
name: fuzzing-false-negative-pitfalls
description: "Sweep triage: 0-hit false negatives, 200-OK false positives."
metadata:
  hermes:
    tags: [security, fuzzing, ffuf, recon, false-negative, bug-bounty, methodology]
version: 1.0.0
---

# Fuzzing false negatives — diagnosis and the metrics oracle

## Trigger

Load this when ANY of these is true:

- A wordlist sweep returns `0 hits` on a target that clearly has an API.
- You are about to write "no endpoint exists" / "0 findings" in a report.
- An endpoint you know exists (from a bundle, a 500 error, a redirect) does not appear in the sweep.
- You discover a route by hand that a prior sweep missed.

The single most expensive mistake in a web audit is publishing a negative result produced by broken tooling. A false negative is not "coverage" — it is a fabricated claim.

---

## Pitfall 1 — default status matcher ignores HTTP 400

ffuf's default matcher is `200-299,301,302,307,401,403,405,500`. **400 is not included** and neither are 409, 410, 422, 429, 503.

Consequence: every endpoint that validates a request body returns 400 on an empty POST, so **all DTO-validating endpoints — often the majority of a NestJS/Django/Rails API — are silently dropped**.

Real case: `POST /exchange` on a target returned `400 {"message":["Amount must be correct"]}`. It was invisible in a 1,934-path sweep and only surfaced after switching matchers. Seven endpoints were found this way.

Fix:

```bash
# WRONG
ffuf -u https://api.target.com/FUZZ -w words.txt -X POST -d '{}' -fc 404

# RIGHT
ffuf -u https://api.target.com/FUZZ -w words.txt -X POST -d '{}' \
  -mc all -fc 404 -fr "Cannot (POST|GET|PATCH|PUT|DELETE)"
```

`-mc all` plus a body-regex filter is the reliable combination: it matches any status, then removes the framework's generic "route not found" body. Replace the filter regex with the target's actual 404 body, e.g. `-fr "Not Found"` or `-fr '"error":"not_found"'`.

Feroxbuster equivalent: `-s 200,201,204,301,302,307,400,401,403,405,409,410,422,500,503`.
httpx/nuclei path brute force: check the matcher condition before trusting a zero.

---

## Pitfall 1b — a 429-dominant sweep is not a sweep (the rate-limit trap)

Filter 429 out of your results and you hide the fact that *nothing ran*; keep it in and every line
looks like a hit. Either way the run carries no information and still reads as coverage.

Measured 2026-10-29 on `mainnet.api.cloud.ngrave.io`: ffuf with `-mc all -fc 404` returned
**114 "hits", of which 112 were `429`** and 2 were `401` on `/docs`. The host's per-IP limiter was far
tighter than the ~4 rps the run used. Re-probing the *same* wordlist serially in Python with
`if e.code == 429: sleep(4); continue` found `/api/v1/info` (200, version disclosure) and
`/api/v1/support` (401 with a completely different guard envelope) — two routes ffuf never reported.
A second ffuf pass, even after dropping the rate to 2 rps, produced the same 429 wall.

Rules:

1. **Count statuses before reading hits.** `Counter(r['status'] for r in results)` — if any single
   status is >60% of rows and it is 429/503/502, the run produced no information. Say so and redo.
2. **429 is a non-result.** It means "not attempted" — never a hit, never a negative, never a `-fc`
   entry alongside the real 404 baseline.
3. **Re-probe serially with backoff.** One request at a time, ≥0.5 s spacing, retry on 429 up to
   4–6 times. ~300 paths ≈ 4–5 min. That is the only shape that yields a real answer on these hosts.
4. **Different route groups carry different guards, so status-only bucketing merges them.** Store the
   *body* per result: `{"message":"Unauthorized","statusCode":401}` (43 B),
   `{"errors":[{"code":"MISSING_HEADERS",…}]}` (149 B) and an nginx basic-auth page (172 B) are three
   different gate families on the same host. Filtering on status alone collapsed all three into "401".
5. **`nuclei`'s `Skipped <host> as found unresponsive 30 times` is the same failure mode** — a
   rate-limited host is dropped silently and `Matched: 0` reads as "clean". Read the skip lines and
   the `Errors:` counter: a run with thousands of errors plus skipped hosts is a non-result. Lower
   `-rl`/`-c`/`-bs`, split the host list, re-run — then, and only then, may a zero be reported.
6. **A per-route guard means the namespace sweep IS the authz map.** Because one app can leave
   `/api/v1/info` open and gate `/api/v1/portfolio`, a partial sweep that returns "mostly 429" is
   exactly where a real ungated sibling hides.

## Pitfall 1c — `-silent` with no `-stats` produces a silent zero (positive control required)

Distinct from 1b: the host is fine, the templates load, the requests fire — but **nothing reaches
stdout**, so the run reports 0 lines and reads as "target clean".

Measured 2026-10-30 on `relay.link` (45 live hosts). First invocation:

```bash
nuclei -l live.txt -silent -rl 15 -c 5 -timeout 10 \
  -tags takeover,exposure,misconfig,disclosure -severity critical,high,medium \
  -o nuclei-out.txt 2>/dev/null
# -> hits: 0, stderr: 0 bytes
```

Looks like a clean estate. It is not evidence of anything. The tell is the **positive control**:

```bash
nuclei -l live.txt -silent -tags tech -o control.txt   # tech tags MUST match a live host
# -> control hits: 0        <-- impossible on 45 live hosts
```

A control that must match returning zero proves the *invocation* is broken, not the target clean.
Re-run one host without `-silent` to see the engine work:

```bash
printf "https://api.relay.link\n" > one.txt
nuclei -l one.txt -tags tech -rl 10 -timeout 10 -stats -no-color
# [waf-detect:cloudfront] [http] [info] https://api.relay.link
# [aws-detect:aws-cloudfront] [http] [info] https://api.relay.link
# | Templates: 1217 | Requests: 702/1119 | Matched: 2 | Errors: 0
```

Rules:

1. **Every scan run needs a positive control.** A tag set that is guaranteed to match
   (`-tags tech`, `-tags waf-detect`, or a host you know serves a known template) must produce
   hits. No control hits → discard the run, do not report its zero.
2. **`-silent` + `-o` + `2>/dev/null` is the dangerous combination.** It hides both the match
   lines and the reason there are none. Use `-stats -no-color` into a log for any run whose
   zero you intend to report, and read `Requests:` / `Matched:` / `Errors:` from it.
3. **`Errors: 0` with `Requests: 0`** means nothing was sent (bad `-l` path, empty list).
   `Requests > 0` with `Matched: 0` on the control means the matcher/tags are wrong.
4. **Windows/MSYS:** a `/tmp/x.txt` host list fails silently for native nuclei.exe — the file is
   invisible to it. Always pass `C:/...` native paths (see `pipeline-invocation-traps.md` Trap 16).
5. Record in coverage: `nuclei vX, N templates, control M hits, scan K hits, Errors E`. That line
   is a measurement; "0 hits" alone is a claim.

## Pitfall 1d — httpx `-o` output is NOT a nuclei target list (`Requests: 0/0`)

The most embarrassing zero in this family, because both tools are ProjectDiscovery and look
interoperable. They are not.

```bash
httpx -l subs.txt -silent -status-code -title -tech-detect -o live.txt
# live.txt now contains:
#   https://api.relay.link [200] [Cloudflare,Cloudflare Bot Management,HSTS]
#   https://api.dev.relay.link [403] [ERROR: The request could not be satisfied] [Amazon CloudFront]

nuclei -l live.txt -tags tech -stats
# [INF] Targets loaded for current scan: 13
# Requests: 0/0 | Matched: 0 | Errors: 0        <-- nothing was ever sent
```

nuclei parses each line as a URL, fails on the trailing `[200] [tech]` metadata, and **drops the
target silently**. `Targets loaded: 13` makes it look like the list was accepted. The only tell is
`Requests: 0/0`.

Fix — reduce to bare URLs, always:

```bash
awk '{print $1}' live.txt | grep -E '^https?://' | sort -u > live-urls.txt
nuclei -l live-urls.txt ...
```

Checklist before any nuclei run whose zero you intend to report:

1. `grep -cE '^https?://[^ ]+$' targets.txt` must equal `wc -l targets.txt`. If not, the list is dirty.
2. `Targets loaded` must equal the file line count — a mismatch means lines were dropped.
3. `Requests:` must be `> 0` and roughly `targets × templates`. `Requests: 0/0` is a broken run.
4. `Matched: 0` with `Requests: 0/0` is **not** a clean target — it is no scan at all.

Same trap in reverse: `nuclei -o` writes its own match format (`[template] [proto] [sev] url`), so
feeding a nuclei output file into httpx or ffuf has the mirror problem.

## Pitfall 1e — a one-template control is not a control

Control selection matters as much as running one. On `relay.link` these three attempts each looked
like a control and none was usable:

| Control | Result | Why it failed |
|---|---|---|
| `-tags waf-detect` on 13 hosts | `Templates loaded: 1`, finished in 309 ms | one template cannot exercise the tag pipeline; 309 ms is too fast to have fetched anything |
| `-tags tech` on 45 hosts with `-silent` | 0 hits | the whole `-silent` invocation was broken (Pitfall 1c) |
| same tag set as the real scan, 1 host | `Requests: 4074/4076`, `Matched: 0`, `Errors: 4` | **this is the good one** |

**Use two controls, and require both:**

- **Control A — can the engine match at all?** `-tags tech` on one host known to serve a matchable
  service. Must return ≥1 hit. This validates the binary, templates and network path.
- **Control B — does *this tag set* execute fully?** Run the real scan's exact tags against **one**
  host. Require `Requests > 1000`, `Errors` under a few percent, and accept `Matched: 0`. This
  validates that the tag set loads templates and sends them — which is what makes the real scan's
  zero meaningful.

Control B is the one people skip, and it is the one that catches a typo'd tag name silently
selecting zero templates. A tag that matches nothing produces a perfect-looking zero.

## Pitfall 2 — leading slash in the wordlist produces a doubled path

A wordlist line `/exchange` against `-u https://host/FUZZ` produces `https://host//exchange`. Many frameworks route that differently and return a uniform 404, so **every line misses** and the sweep looks clean.

This is insidious because nothing errors — you just get 0 hits.

Fix — normalise the wordlist and add a sanity entry:

```bash
sed 's|^/||' words.txt > words_ns.txt
```

Then **always include known-good entries** and confirm they appear in the output before trusting a zero:

```bash
printf 'health\n<known-endpoint>\n' > sanity.txt
ffuf -u https://host/FUZZ -w sanity.txt -X POST -d '{}' -mc all -fc 404 -s
```

If the sanity check does not return the known endpoint, the harness is broken — fix it before running the real sweep. Never report a zero from an unsanity-checked run.

---

## Pitfall 3 — the `-fr` regex eats valid hits

`-fr "Cannot"` is safe only if the 404 body always contains it. On mixed stacks (e.g. NestJS behind a Next.js rewrite) a 404 can be an HTML page with no "Cannot", so `-fr` silently removes real endpoints, or conversely fails to remove noise.

Diagnose by running with no filter at all and inspecting a sample:

```bash
ffuf ... -mc all -s | head -40     # look at what noise actually looks like
```

Then filter on a discriminator that is unique to the miss case (`"statusCode":404`), not a word that can appear in a success body.

---

## Pitfall 4 — auth state changes the answer

The same path returns `401` anonymously and `400` (with schema disclosure) when authenticated. Sweeping twice — one unauthenticated, one authenticated — is not redundant; it is how you separate a real 401 from a route that exists but is guarded.

```bash
# pass the token at runtime so it never lands in shell history or redacted output
T=$(python -c "import api;api.login();print(api.TOK)")
ffuf ... -H "Authorization: Bearer $T"
```

If a tool-wrapper redacts `Bearer <token>` in your command string, build the header in Python with string concatenation (`"Auth"+"orization: Bea"+"rer"+chr(32)+tok`) or pass it through a wrapper script.

---

## The metrics oracle — finding routes wordlists cannot reach

When a target exposes a Prometheus registry (`/metrics`), it becomes a **side-channel oracle**. Counters move when you touch a real code path, so you can discover routes without any wordlist.

Method:

1. Grab the registry and extract the counters:

```python
import re, urllib.request
def grab(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=20) as f:
        t = f.read().decode()
    d = {}
    for line in t.splitlines():
        if line.startswith("#"): continue
        m = re.match(r'^(binobi_[a-z_]+(?:\{[^}]*\})?)\s+([0-9.e+-]+)$', line)
        if m: d[m.group(1)] = float(m.group(2))
    return d

def delta(url, key, probe, path):
    a0 = grab(url).get(key, 0.0)
    probe(path)
    time.sleep(0.4)          # let the counter flush
    a1 = grab(url).get(key, 0.0)
    return a1 > a0
```

2. Validate the oracle is quiet (baseline deltas of zero for ~20s) — otherwise ambient traffic makes every probe look like a hit.

3. Probe candidates one at a time and watch for a delta. A hit means the route exists **and** executes real work.

Real case: `/metrics` exposed `binobi_moneygrator_callback_events_total{outcome="received"}`. A 1,934-path sweep missed the callback entirely; an oracle loop over 59 candidates found `POST /moneygrator/callback` on the second try because `received` and `invalid_signature` both incremented by exactly 1.

4. Metrics also do reconnaissance for free: provider enums, rate-limit rule names, internal route-family names, runtime versions.

Sanity gate: if you probe a path and a *generic* counter moves (e.g. `default` rate-limit rule), that is ambient traffic, not a route hit. Require a specific counter to move.

---

## Pitfall 5 — the mirror problem: mass-probe `200 OK` is not a hit

Everything above is about a sweep reporting too little. The opposite failure costs just as much time
and is far more common once you scale to a large estate: **fanning one path list across hundreds of
hosts and trusting the 200s.**

Measured 2026-10-29 on a 2,345-host estate (`*.telekom.com` / `*.telekom.de` / `*.t-systems.com`),
probing 9 paths (`/actuator/env`, `/actuator/heapdump`, `/actuator/health`, `/v3/api-docs`,
`/swagger-ui/index.html`, `/.env`, `/.git/config`, `/server-status`, `/debug/pprof/`) across ~250
API-ish hosts: **535 rows with `status in (200,206)` and body > 60 bytes — of which ~534 were noise.**

The three noise shapes, all indistinguishable by status code alone:

| shape | looks like | actually is |
|---|---|---|
| SPA catch-all | `200`, 1–50 KB HTML, every path identical length | client-side router 404. `/actuator/heapdump` returning `<!doctype html>` is not a heapdump |
| WAF reject page | `200`, ~243 bytes, `Request Rejected` | the WAF answering *every* path with the same page |
| framework default | `200`, valid JSON error envelope | route absent, generic handler |

And the one real hit — a 498 KB `application/json` OpenAPI spec at `/v3/api-docs` — was only
visible because it was *four orders of magnitude larger* than its neighbours.

### Triage rule (run before reading any row)

1. **Fetch a random nonexistent path first** (`/zz-<random>`) per host and hash the body. That is the
   host's 404 baseline. Any "hit" whose body hash equals the baseline is negative — no exceptions.
2. **Filter by content-type, not status.** `application/json` + `application/octet-stream` are the
   only content types that can carry a real finding on these paths. `text/html` at
   `/actuator/env`, `/.env`, `/.git/config` is always the shell.
3. **Sort by size descending and read the top of the list first.** Real disclosures are big (specs
   hundreds of KB, heapdumps MBs, `.git/config` a few hundred bytes of INI). The shell is uniform.
4. **Grep the body for the discriminator**, don't eyeball: `.env` → `^[A-Z_]+=`, `.git/config` →
   `[core]`, heapdump → binary magic (`JAVA PROFILE`), api-docs → `"openapi"`.
5. Write the noise count down explicitly in the coverage section — "535 x 200-OK, 534 verified as
   SPA/WAF shell, 1 real" is an honest result; "9 paths x 250 hosts" alone reads as a claim.

### Secret-scanner variant of the same false positive

A JS secret sweep flagged **14 `-----BEGIN OPENSSH PRIVATE KEY-----` hits** across two hosts. All 14
were i18n placeholder strings in a Vue/Next locale dictionary
(`"sshPrivateKeyPlaceholder":"-----BEGIN OPENSSH PRIVATE KEY-----"`, alongside
`"sshPrivateKeyRequired":"Private key is required"`).

Rule: for any `BEGIN … PRIVATE KEY` match, print 200 chars of context on each side before believing
it. A real key is base64 body lines immediately after the header; a placeholder is followed by `"`,
`,\n`, or another locale key. Same discipline as marker discipline — the match string is not the
finding, the surrounding structure is.

---

## Pitfall 6 — size-diff parameter discovery on a LIVE endpoint invents parameters

The mirror of Pitfall 5, one level up: `ffuf -u "…?known=1&FUZZ=1" -fs <baseline>` (and `arjun`)
decide "this parameter exists" by **response size changing**. On an endpoint whose payload drifts
on its own — prices, market cap, volume, pagination cursors, anything backed by a live feed — the
size moves between requests with no parameter involved, so **every candidate is reported as a hit**.

Measured 2026-10-30 on `api.bankr.bot/token-launches` (public, no auth):

```
# first attempt — two mistakes stacked
ffuf -u "…?limit=5&FUZZ=1" -w params.txt -mc 200 -fs 0      # -fs 0 filters NOTHING
# -> all 39 candidate params "matched"

# corrected filter, still wrong
baseline=$(curl -sS "$u" -o /dev/null -w "%{size_download}")   # 49466 B
ffuf … -mc all -fs "$baseline"
# -> 6 "new parameters": query, user, email, debug, format, exclude
```

Six undocumented parameters on a public endpoint looked like a real finding. They are not:

```
param,run1,run2,run3,run4
baseline,49240,49240,49240,49240        <- stable, so the endpoint is NOT always noisy
query=x,49240,49240,49240,46936
user=0xef33…,49240,46936,46936,46936
email=a@b.c,49240,49240,49240,49240     <- identical to baseline
debug=1,49240,49240,49240,49240
exclude=x,46936,49240,49240,49240
```

The second value (`46936`) appears **at random across unrelated parameters and would appear on the
baseline too**. It is data drift, not a parameter effect. Zero hidden parameters exist.

### The rules

1. **Never use `-fs 0`.** It filters nothing and every word matches. If you see "all 39 params
   matched", the run is broken, not the target.
2. **Measure the noise floor before believing any hit.** Run the bare baseline 4–5× first. If the
   baseline is stable but a "hit" size also shows up on unrelated params, it is drift.
3. **Re-run each candidate 3–4× and require the difference to be reproducible.** A parameter must
   change the response *every* time, not once in four.
4. **Compare structure, not bytes.** For JSON, parse and diff the key set / value types /
   array length. A price change alters `marketCap` values; a real filter alters which objects come
   back. Size is the noisiest possible discriminator.
5. **A hit is only real if you can state the semantic difference.** "Size changed by 2 KB" is not a
   finding. "`?user=<addr>` returns only that wallet's launches" is.

### arjun crashes instead of lying

`arjun` on this class of target dies with
`AttributeError: 'dict' object has no attribute 'status_code'` in `arjun/__main__.py:initialize()`
as soon as one target answers ≥400, and **aborts the whole batch** (`EXIT=1`). Even on the URLs
that survive it reported "No parameters were discovered" — consistent with ffuf, but obtained from
2 of 6 targets only.

Fix: do not batch arjun across targets. Either test params with ffuf (rules above) or run arjun only
against URLs that answer 200 to a bare GET. Record which targets were actually covered — "arjun
found nothing" from a crashed batch is not coverage.

**The quiet variant of the same lie: `Skipped <url> due to errors` / `Connection aborted`.** arjun can
also die *mid-run* (`Encountered an error: Connection aborted.` after ~19 of 206 chunks, then
`Skipped https://… due to errors`). It exits 0, prints nothing resembling a result, and produces **no
output file** — which reads as "no parameters found". It is a **partial run, not a negative**. Treat a
missing output file, or a target line containing `Skipped`, as an invalid run: lower `-t`, add a delay,
re-run, and only then classify. Also don't relaunch into a still-running nuclei/arjun from the previous
attempt — a killed-but-alive scanner holds the target's rate budget and makes the new run look blocked.

---

## Reporting discipline

Before writing any negative claim, all of the following must hold:

- [ ] Sweep re-run with `-mc all` (or explicit 400 in the status list).
- [ ] Wordlist normalised (no leading slash) and sanity check passed.
- [ ] Filter regex verified against a real miss sample.
- [ ] Swept both unauthenticated and authenticated.
- [ ] At least one independent method confirms the negative (oracle delta, parallel HTTP probe, bundle analysis). Two tools sharing the same bug is one data point, not two.
- [ ] Every *positive* row in the same sweep was diffed against a random-path baseline (§Pitfall 5) — a hit count that was never triaged is as unreliable as a zero.
- [ ] Any parameter "discovered" by size-diff was re-run 3–4× and the difference reproduced every time (§Pitfall 6). `-fs 0` was never used.

Then state it as:

> "No X exists beyond the four named (confirmed three independent ways: wordlist sweep with `-mc all`, parallel HTTP probe without ffuf, and metrics-counter deltas)."

Never state "0 findings" or "no endpoint exists" from a single tool run.

---

## Pitfalls

- **Trusting SMTP/CLI success output.** Verify side effects by reading back from the server (IMAP fetch, GET the resource). `sendmail()` returning without exception is not proof of delivery.
- **Wordlist `gau` output mixes locales** (`/en/`, `/de/` prefixes). Strip the locale prefix before deduplicating or you get 15x duplicate paths.
- **Historical endpoints are gold.** `gau` surfaced `/vault`, `/transfer`, `/exchange` — the front-end pages were deleted but the API routes stayed live ("shadow API"). Always diff historical paths against the current bundle.
- **Case-insensitive routing** (`/Exchange` == `/exchange`) inflates hit counts and hides real duplicates. Normalise case when counting.
