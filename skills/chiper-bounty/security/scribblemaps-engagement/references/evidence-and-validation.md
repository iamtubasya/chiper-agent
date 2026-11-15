# Evidence and validation record (2026-10-31)

Workdir: `$HOME/bounty/scribblemaps\`
Coverage doc: `COVERAGE.md` (rounds 1–8, tested / negative-with-artifact / blocked / unproven).

## Pre-submit validation (operator requires >= 3x before anything is sent)

`evidence/pre_submit_validation_f1.json` — three anonymous runs of
`GET https://www.scribblemaps.com/api/maps/paidsample/raw` with three different User-Agent
strings and a fresh session each time:

```
run1 200 16908 sha256=REDACTED_********
run2 200 16908 sha256=REDACTED_********
run3 200 16908 sha256=REDACTED_********
controls: api-host /raw = 401, www image API = 401, Secure map /raw = 401
verdict: PASS
```

`evidence/pre_submit_validation_f2.json` — three runs of the `aisubmit` differential
(own id / plus-alias id / non-existent id), identical results each time.

`evidence/ssrf_validation.json` + `oob2.txt` — three metadata-import runs, one DNS + one HTTP
interaction per run, source IPs 20.42.77.69 (DNS) and 13.72.78.248 (HTTP).

## Portal submission state

- F1 submitted: `POST /api/vulnerability/aisubmit?userId=dbVZ4Wz9LP` (session's own id,
  verified against `GET /api/account` first) → `200 {"success":true,
  "pendingConfirmation":true,"referenceId":"FF3179"}`. Saved to
  `submit/submission_result.json`.
- `GET /api/vulnerability/list` remains `[]` while the report is pending e-mail approval —
  an empty list is not evidence of failure.
- The approval e-mail had not arrived 12 minutes after the 200 (checked with the Gmail API:
  `in:anywhere`, `from:scribblemaps`, `FF3179`, `"approve this submission"`, and a raw
  last-3-hours sweep). Operator must click it; 48 h expiry.
- Program limit: one report per user per day, so F2 and F3 wait for the next window or go by
  e-mail. Payloads are staged at `submit/finding2_payload.json` and
  `submit/finding3_payload.json` (title / description / date / attachment) so they can be
  pasted straight into the portal form.

## Gmail drafts (1 finding = 1 draft + 1 PDF, verified attachments)

| draft id | finding | attachment | bytes |
|---|---|---|---|
| `r-5650808210828374501` | F1 paid-map content disclosure | ScribbleMaps_PoC_PaidMap_Content_Disclosure.pdf | 10,050 |
| `r1850442480756029124` | F2 portal userId impersonation | ScribbleMaps_PoC_Vulnerability_Portal_Impersonation.pdf | 8,467 |
| `r518573298858966182` | F3 SSRF metadata import | ScribbleMaps_PoC_SSRF_SAML_Metadata_Import.pdf | 6,829 |

All to `support@scribblemaps.com`, from `RESEARCHER_EMAIL`, unsent. Each body carries a
"SUBMISSION DETAILS" block (title, date of discovery, attachment name + size, PayPal e-mail)
plus the two agent-caused side-effect disclosures (unverified Stripe Connect account from
probing `/api/market/create-account`; per-IP 429 throttle on `/api/vulnerability/submit`
caused by dry-run probes).

## Nuclei (completed, not claimed)

105 templates (tags `exposed-panels,backup,swagger,graphql,aspnet,iis,dotnet,angularjs,jquery`)
x 6 hosts, finished at 100% — 10,783 requests, 60 connection errors, 11 minutes. One match,
informational only: `aspnet-version-detect "4.0.30319"` on `team.scribblemaps.com`. Broader
www-only sanity run (2,030 templates, tags `exposure,misconfig`) produced 10 matches, all
informational and explicitly out of scope (missing security headers, `sm_lang*` cookie flags).
Blanket CVE sweep deliberately not run — recorded as a gap, not as a negative.

## Cleanup performed

`/api/saml/toggle` and `/api/oidc/toggle` → false; all 13 test domains deleted via
`DELETE /api/saml/domains/{id}`; uploaded test overlays removed via
`GET /api/account/overlays/{id}/remove`; three orphaned `nuclei.exe` processes killed.
