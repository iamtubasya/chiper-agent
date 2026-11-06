# Impact verification stage (0C-C2d) — SSRF / LFI / SSTI / XXE / open-redirect / blind-SQLi

Added 2026-10-10, same day as `rce-verify` (0C-C2c). Once RCE got a verifier it was
obvious the same gap existed for six more classes.

## The gap

`execute-variants.http_probe` returns `(status, size, excerpt, error)` and marks a probe
"interesting" when

```python
if status not in (404, 403, 401) and size > 0:
```

That is **detection**, and it structurally cannot separate:

| looks identical to http_probe | actually is |
|---|---|
| a page that echoes the word `passwd` | LFI that READ `/etc/passwd` |
| a 200 for `{{7*7}}` | SSTI that **evaluated** to `49` |
| any response | SSRF that called our canary |
| a merely slow page | blind SQLi that **slept** 5 s |

Blind variants of every class were invisible by construction.

## One verifier, six proof channels

```bash
python ~/AppData/Local/hermes/scripts/impact-verify.py <target-dir> <base-url> \
       [--classes ssrf,lfi,ssti,xxe,open-redirect,blind-sqli] \
       [--limit 12] [--sleep 5] [--ratio 2.5] [--rounds 3] [--timeout 20] [--insecure]
```

Runs as **PHASE 0C-C2d** (between C2c RCE-verify and C3 business logic). Listed in the
`0C.tools` MANIFEST as `impact-verify`.

| class | proof channel | why it is proof |
|---|---|---|
| **SSRF** | OOB canary callback | the target's own HTTP client resolved our host and connected |
| **LFI** | file-content signature (`root:.*?:0:0:`, `[fonts]`/`for 16-bit app support`, `/bin/bash`, `<?php`, `DOCUMENT_ROOT`) | the file's CONTENT came back, not the path string |
| **SSTI** | arithmetic evaluation — `{{7*7}}`→49 **and** `{{7*8}}`→56, plus `${}` and `<%= %>` engines | two different correct answers cannot be a coincidence in the page |
| **XXE** | OOB entity callback (+ in-band file signature fallback) | the parser resolved an external entity |
| **open-redirect** | `Location:` host differs from target host | the server itself chose an off-site destination |
| **blind-SQLi** | time differential vs benign baseline, floor `max(baseline*ratio, sleep*0.6, 0.6)` | the database executed our delay |

Every class runs **inert controls** that must stay silent (`; echo IMPACTCTRL`, a
non-existent path, a literal `7*7`, `' OR 1=1-- -`). A control that fires invalidates
the channel instead of being ignored.

## Two bugs found by testing, both real

### 1. Open redirect read as "nothing found"
`v_open_redirect` used the redirect-**following** fetcher. A 302 to `evil.example.com`
was chased by our own client, the request failed (host does not exist), and the result
came back `{"status": null, "location": ""}` — a genuine open redirect recorded as a
miss. Measured on all four payloads before the fix.

**Fix:** added `http_get_noredirect` (a `HTTPRedirectHandler` subclass returning `None`)
and used it for `Location` reading.

### 2. Open redirect masqueraded as SSRF
With the redirect-following fetcher, a 302 pointing at the canary produced a callback —
**caused by our own client**, not the target. That would report SSRF where the real bug
is an open redirect.

**Fix:** SSRF probes now use `http_get_noredirect`. A 3xx response is recorded under
`redirect_only` with an explicit note, so a redirect is classified as a redirect while a
callback that arrives from a request WE did not make stays a genuine SSRF signal.

### 3. Open-redirect "CONFIRMED" from a RELATIVE Location (query value parsed as host)
**Measured 2026-10-17** (energiekoers.gasunie.nl, 4 targets × 6 payloads = 4 "CONFIRMED"):
the verdict JSON carried
`{"status":302,"location":"/stakeholder-event/?q=https%3A%2F%2Fevil.example.com%2F","location_host":"evil.example.com","offsite":true}` —
`location_host` was read **out of the query VALUE**, so `offsite=true` was printed for a
redirect that never leaves the host.

Raw TLS-socket re-check (the only trustworthy reader here):

```
GET /?q=https://evil.example.com/      -> 302  location: /stakeholder-event/?q=https%3A%2F%2Fevil.example.com%2F   (RELATIVE, host unchanged)
GET /stakeholder-event/?q=<evil>       -> 200  (no Location)   ← no second hop, nothing leaves the host
GET /?q=testmarkerXYZ                  -> 302  location: /stakeholder-event/?q=testmarkerXYZ  ← baseline identical
```

**Verdict rules for this class:**
- `offsite` = `bool(urlparse(Location).netloc)` **and** netloc ≠ target host. Empty netloc
  (relative Location) = same-host, **always**, no matter what payload rides in the query.
- A same-host 302 that merely *carries* the payload forward is only a bug if a **later hop**
  in the chain produces an absolute off-site `Location` — walk the chain (≤6 hops) before
  closing either way.
- Payload-in-query is also why baseline behaviour must be compared: the app redirected
  `/` → `/stakeholder-event/` on every request, including the no-payload control.
- The pipeline printed `CONFIRMED` while triage suppressed it (`impact_score=None`) — that
  split is expected: **triage is not the verifier**, so re-verify the class yourself with the
  raw socket before writing a line about it in either direction.

## Verification performed (all directions)

| target | expected | observed |
|---|---|---|
| `/ssrf?url=` (fetches the URL) | SSRF CONFIRMED | **CONFIRMED** — canary callbacks, `ua=Python-urllib/3.14` |
| `/lfi?path=` (returns file content) | LFI CONFIRMED | **CONFIRMED** — `passwd-entry` signature |
| `/ssti?q=` (evaluates `{{n*m}}`) | SSTI CONFIRMED | **CONFIRMED** — 49 + 56 |
| `/redirect?q=` (302 off-site) | open-redirect CONFIRMED | **CONFIRMED** — and **no** SSRF claimed |
| `/sqli?q=` (executes `SLEEP(n)`) | blind-SQLi CONFIRMED | **CONFIRMED** — 6 time payloads fired |
| `/safe?q=` (echoes input) | nothing CONFIRMED | **0 of 6** — clean |
| inert controls | silent | **silent** |

Result of the final run: `confirmed=5 of 36 checks`, exactly the five vulnerable
endpoints, zero on the negative control.

## Pitfalls

- **A single-threaded test server deadlocks on self-referential SSRF.** The first
  vuln target returned `fetch failed: TimeoutError` for every probe because `/ssrf`
  fetched a URL pointing back at the same single-threaded server. Use
  `ThreadingHTTPServer` for any test target that fetches.
- **XXE needs a POST body.** The verifier POSTs XML; a URL list of GET endpoints will
  legitimately show XXE as not-confirmed. That is a true negative, not a bug.
- **`--sleep 3` for testing, `5`+ for real runs.** The floor scales with the requested
  sleep, so a short sleep against a slow target needs the baseline ratio to do the work.
- **Never leave a silent failure.** On exception the stage writes
  `impact-verification.json` with `status: ERROR` and the exception text.
