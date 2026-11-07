# DOM-XSS browser stage (0C-C2b) — closing the SPA blind spot

Added 2026-10-10 after `plugins.jetbrains.com` exposed a structural false negative.

## The blind spot

Server-side scanners (dalfox, kxss, nuclei, curl) can only inject into things the
**server** sees: query strings, path segments, headers. On a modern SPA:

- routing is client-side (`/#/route`) — the fragment never reaches the server
- the interesting sink (`innerHTML`, `eval`, `document.write`, framework
  `dangerouslySetInnerHTML`) is reached only **after** the JS app boots

Measured on `plugins.jetbrains.com` (React): **0 of 123 recon URLs carried a query
parameter**. dalfox ran **53 minutes** against the root URL and could not have found
anything — there was nothing injectable. A "clean" result from that run is a **false
negative by construction**, not a statement that the target is safe.

## The stage

```bash
python ~/.chiper/skills/bounty-pack/dom-xss-test.py <target-dir> <base-url> \
       [--urls-file urls.txt] [--limit 25] [--timeout 12] [--headful]
```

Runs as **PHASE 0C-C2b** in the orchestrator, between C2 (payload variants) and
C3 (business logic). It is listed in the `0C.tools` MANIFEST as `dom-xss`, so 0D
will see it accounted for.

### What makes a hit a hit

A payload that merely **renders as text** is NOT a finding. The stage installs a
sink hook **before navigation** and marks interpretation only when one of:

| signal | meaning |
|---|---|
| `dom-sink:*` | a MutationObserver saw an `IMG`/`SCRIPT`/`SVG` node injected, or `window.onerror` fired |
| canary fetch | the browser actually **requested** `http://127.0.0.1:<port>/domxss-canary` — a local HTTP server logged the hit |
| `payload-present-in-dom` | context only, **never** a hit on its own |

Injection sources tested per URL: **query**, **hash fragment**, **path segment**.

### Outputs (inside the target dir)

| file | contents |
|---|---|
| `dom-xss-usage.json` | one ledger row: engine, url count, probes, interpreted, canary hits, status |
| `dom-xss-evidence/dom-xss-raw.json` | full per-probe record (url, source, payload, reason, title) |
| `dom-xss-findings.json` | only probes where the payload was INTERPRETED |

When no browser can be launched the ledger records `status: NO_BROWSER` — recorded
honestly rather than skipped silently (same contract as every other 0C asset).

## Verification performed (do not skip this when changing the stage)

| target | expected | observed |
|---|---|---|
| `example.com` (benign) | no hits | `interpreted=0 canary=0` |
| local app with `innerHTML = params.get('q')` | hits | 10 interpreted + 1 canary |

**Both directions matter.** A detector that only ever fires is a false-positive
machine; one that never fires is decoration. Prove the negative case too.

## Pitfalls (hit for real)

- **`page.evaluate` throwing is NOT evidence of XSS.** The first version wrapped the
  sink read inside the same try-block as `goto`, so a `TypeError` from the evaluate
  bridge was caught and recorded as `interpreted=True` — 10 false positives on the
  smoke test. Read the flag in its **own** try/except and leave the verdict false on
  error.
- **Camofox path mismatch.** `camofox-browser` looks for
  `…/camoufox/camoufox/Cache/version.json` while `camoufox fetch` writes the real
  binary under `Cache/browsers/official/<ver>/`. Copying `version.json` up one level
  moved past the first error (`Version information not found`) but the server then
  failed with `Cannot read properties of undefined (reading 'split')`. **Use
  Playwright instead** — `ms-playwright` already ships Chromium/Firefox/WebKit here
  and needs no repair.
- **Browser availability is environment-dependent.** Playwright launch is attempted
  `chromium → firefox → webkit`; the engine actually used is written to the ledger so
  the result is auditable.

## Why this is not redundant with `xss-reflected` variants

| stage | sees | blind to |
|---|---|---|
| C2 `xss-reflected` (dalfox/kxss) | server-side reflection into the HTML response | client-side sinks, hash routes |
| **C2b `dom-xss`** | DOM sinks after JS boot, hash fragments, canary fetch | nothing server-side |

They cover **different halves** of the XSS class. Both are mandated.
