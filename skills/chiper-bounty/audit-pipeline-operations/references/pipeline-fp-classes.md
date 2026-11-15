# Pipeline false-positive classes — measured 2026-10-17, with one-shot disproofs

Rule: a pipeline positive (`CONFIRMED`, `HIT`, `survivors`, `ready after review`) is a **candidate**.
Each class below reached the report/queue in a real run and died against an independent method.
Disprove with the recipe in column 2; column 3 is the measured outcome.

| Class (where it shows up) | Disproof | Measured outcome |
|---|---|---|
| **Open-redirect "CONFIRMED"** — `impact-verify` prints `location_host=<attacker>`, `offsite=true` | Raw socket two steps: `GET /?q=<url>` → read the **raw `Location`**; then follow hop 2; then baseline `?q=marker` | `302 location: /stakeholder-event/?q=<url-encoded>` — Location is **relative**, host unchanged; hop 2 = 200, no Location; baseline identical. Parser had read the query *value* as host → DROP |
| **DOM-XSS `HIT hash … dom-sink:mutated-node:SCRIPT`** — `0C-C2b` checker | Playwright: navigate to the payload URL, read `window.__DOMXSS`, `document.querySelector('img[src=x]')`, register a `dialog` handler | flag `UNSET`, payload absent from DOM, 0 dialogs — the checker's own instrumentation nodes were the "mutation" → DROP |
| **SSTI "CONFIRMED"** — `impact-verify` class `ssti`, `a_has_49` / `b_has_56`, `control_rewritten` | Normalise the dynamic parts (CSP `nonce`, OAuth `state`/`code_challenge`, session cookies, UUIDs), then diff sha256 of baseline vs each of 6 payload families × 5 params; confirm the injected marker is never substituted and never echoed | baseline body already contained `56` inside a base64url `code_challenge`; after normalisation every response sha-identical, marker never substituted → DROP. Substring "did `7*7` evaluate?" detectors are unreliable on hosts echoing base64/URL-encoded material |
| **`variants/ssrf` `[200] /http://127.0.0.1/ … [200] /http://169.254.169.254/…`** | sha256(body) vs sha256(baseline `/`) + the run's own `impact-verify` (`fired=false`, no callback) | byte-identical to the SPA/catch-all homepage (e.g. 2000 B both) → DROP |
| **`variants/info-disclosure` `[403] .env / .env.local …`** | junk-path control + read the block page | all 403 block pages of one size; deny ≠ exposure → DROP (the WAF is the control) |
| **`finding_gate` survivor whose "steps" are the tool banner** (`Author: @…`, `Based on Tplmap`, `Scanning url:`) | read `REPORT-survivors.md` and require an HTTP status + body in the steps | banner-only ⇒ triage correctly scores impact 0 → DROP |
| **Business-logic rows all `… ERR … URL can't contain control characters`** | count `ERR` lines vs `probes executed` | probe URL was malformed ⇒ request never sent ⇒ the phase tested nothing; record `NOT effectively tested`, redo manually or close with a catch-all check |
| **`ready after review: 4` while triage passes 0** | read the reconcile lines (`READY ≠ PASSED`, `impact_score=None/0`) | expected: keep the NEGATIVE report; do not resurrect the READY count |
| **Leaked API key / secret from `gitleaks` or a JS bundle** | call the key yourself from a neutral context (no victim referer): Street View metadata / geocode / any billable endpoint | `This API key is not authorized to use this service or API` + `API keys with referer restrictions cannot be used with this API` → referer-locked, unusable off-site → DROP. An unverified key is a lead, not a finding |
| **Client-set cookie that looks like a trust signal** (`document.cookie="signature=…"`, `fragmentAfterLogin`, `locationAfterLogin`) | differential: send the real value, an empty value, a garbage value, and the value plus the sibling cookies; compare sha256 of each response | all byte-identical → the server never reads the cookie → DROP. Only a *differential* proves the server trusts it |
| **Anonymous embed token / signed URL minted without auth** (e.g. Power BI `?handler=EmbedInfo`) | read the vendor's own product docs / the site's public-transparency statement before calling it a bypass | portal is a **public transparency portal** by design (catalogue of 70 reports + GTS page describing the publication) → BY DESIGN → DROP. Check whether the resource is meant to be public before treating access as a bypass |
| **Framework default error page (500) on an OAuth callback** (`error=access_denied` etc.) | read the body: stack trace? reflection of your input? | `Internal Server Error` plain text, 21 B, no stack, marker never reflected → robustness/hygiene, not disclosure → DROP (record as observation) |

## Verification primitives used (reusable)

- **Raw socket** whenever a client may normalise input (urllib encodes `<`, `"`, spaces) or when the exact
  `Location` line matters: `GET <path> HTTP/1.1` over `ssl.wrap_socket`, read status + headers verbatim.
- **Baseline sha** for any "file/endpoint exposed" claim: `sha256(junk-path body)` vs `sha256(claim body)`;
  identical = catch-all/soft-404.
- **Browser canary** for DOM claims: an assignment flag + element presence + `page.on('dialog')` — three
  independent signals, none of them "a node changed".
- **Dynamic-content normalisation** before any body diff: strip CSP `nonce`, OAuth `state`/`nonce`/
  `code_challenge`, session cookies, CSRF tokens, UUIDs, timestamps. A ±2-byte difference is rotation.
- **Host differential** for tenant/takeover claims: real `Host` vs random label of the apex against the same
  backend IP → byte-identical = host-agnostic (unbound), different = configured.
- **Key-verification call** for any leaked credential: invoke it from a neutral origin and read the error.
- **Probe-sent check** for tool phases: an execution counter with `errors == probes_executed` means nothing
  was actually sent; treat as coverage gap, not as a negative result.

## Consequence for reporting

Record every killed candidate as a **verified negative with its artefact** (log lines, sha, raw response) so
the next session does not re-chase it. A `0 findings` outcome is publishable only beside the coverage table:
ran-with-evidence / N-A-with-reason / never-tested.
