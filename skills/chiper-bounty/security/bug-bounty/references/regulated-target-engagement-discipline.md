# Regulated-target (bank / fintech) engagement discipline + technique bank

Hard-won on moneta.cz (Czech bank, Liferay + Spring/F5 ASM + Wultra-hardened Android app, 2026-10).
Everything here is about *how to run the audit*, not about the target.

## 1. Volume discipline — the single biggest process failure of that session
- **Never start a 7k-template nuclei sweep on a bank "to be thorough".** Two sweeps were run: one reached
  26,648/34,410 requests (77%) before being killed, another "curated" run actually loaded **1396** templates
  and issued 4,221 HTTP connections over 25 minutes. Combined result: **0 findings from ~31k requests.**
- A real curated set for a fingerprinted stack is **~10 templates** (here: 6 Liferay misconfig/exposed-panel +
  5 Liferay CVEs = 24 requests, 7 seconds, 0 findings). Match templates to the *versions you fingerprinted*,
  never to a whole CVE-year directory. Loading `http/cves/2021` + `http/cves/2024` and calling it "curated"
  is self-deception.
- The programme's "<100 requests" clause is specifically about rate-limit testing, so bulk scanning does not
  break it literally — but "make a good faith effort to avoid degradation of our services" is a separate
  clause and 31k requests is not proportionate. **Disclose the volume in the ledger rather than hiding it.**
- Cap explicitly: `-rl` low, `-c` low, hard `timeout`, and a request budget you write down before starting.

## 2. Read the telemetry before you claim what a killed run did
I wrote "killed at 1%" in the ledger; the nuclei stderr said `0:43:55 ... 26648/34410 (77%)`. **The log is the
record, not your memory of when you hit Ctrl-C.** Grep the `.err` file for the last
`[M:SS] | Templates: ... Requests: X/Y` line and quote it. If your earlier note was wrong, correct it in an
addendum and say so — an inaccurate ledger is worse than an embarrassing one.

## 3. WAF / edge block-page fingerprinting (F5 ASM + Cloudflare, reusable)
Measure the byte size of uniform responses and label them once:
- `46650` bytes = F5 ASM block page (what ffuf/nuclei default headers get)
- `48397` bytes = application 403 page (directory exists, listing denied)
- `490053` bytes = application 404 page (SPA catch-all)
Consequences:
- **ffuf with default headers returns a uniform ASM page for every path** → 0 "hits" is a *suspect run*, not a
  negative. Always pass a real browser `User-Agent` (and `Origin`/`Referer` for POST APIs).
- Filter on the *body signature* (`-fr "No static resource"`), never on status code alone, and never trust a
  `-fs`/`-ac` auto-calibration that silently eats real hits.
- A 403 vs 404 difference inside one directory can be a WAF rule matching the *path name*
  (`/backup/db.sql`, `/backup/.git/config`) rather than proof the file exists. Do not build a finding on it.

## 4. Extract API contracts with a real browser, not by guessing
Guessing 7 JSON body shapes for `exchangerate/history/list` produced the same generic error every time. One
Playwright network capture of the public page that uses the widget produced the exact contract:
`{"exchangeRatesDate":"2026-10-26T01:00:00"}`. **Capture first, then test.** Also: read the portlet's inline
`<script type="application/json">` config block in the HTML — it carries `endpointUrl`, `historyEndpoint`,
reCAPTCHA site key, and feature flags for free.

## 5. Don't kill crawlers before they print
A katana run was aborted for wandering off-scope; its tail had already emitted the only new endpoint family
found after the initial report (`/unsecured/portal/exchangerate/{list,history/list}`). Gate crawlers to
in-scope hosts and cap depth (`-d 2`, domain filter) instead of aborting, and always read the output file
after a kill.

## 6. Chain-before-discard, then re-verify 3x
Judging each lead in isolation under-scores it; a chain can turn a Low into an ATO. For every lead:
1. Write the chain as discrete hops.
2. Walk each hop to its **terminating sink in code** and record exactly where it dies.
3. Re-verify the load-bearing hops 3x with *independent* evidence (decompile + whole-dex literal count +
   enum membership + layout visibility), not the same source three times.
4. Open at least one angle you have not examined before (the QRLOGIN cross-device login CSRF check came from
   exactly this and is now documented as a non-bug with reasons).

## 7. False-positive classes that cost time here
- **Dex string-pool hits** (method-name tables) look like call sites. Verify per-method.
- **`visibility="gone"` + click listener** = dead debug code, not an exposed debug menu.
- **Strictly-typed request fields** (`java.time.LocalDateTime` via Jackson) kill injection at deserialization
  before any sink — test the type boundary, don't assume.
- **Server-side reCAPTCHA Enterprise** on write endpoints: verify with zero-token and forged-token before
  claiming the endpoint is open.
- **Pinning configs with rotation overlap**: read the whole file before concluding "all pins expired".
