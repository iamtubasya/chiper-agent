## ⛔ RULE 28: Pipeline Output != Findings — Triage Before Reporting

**Session (quarterwise 2026-09-26):** pipeline 0A→0F completed, 1048 candidates → 13 "READY"
→ 3 "High" in validated-findings — ALL were knowledge-base noise, not target bugs
(reference-file text counted as responses, `target.com` placeholders, Next.js query params
echoed into RSC payloads, CVE repo hits returning generic 404 pages, and 400/404 blocked
probes flagged "interesting"). Before reporting pipeline output:

- Orchestrator target MUST be full URL (`https://host.tld`); bare domain ⇒ every tool
  "skipped — target is not a URL" and the gate read is meaningless.
- force-full-execution HARD BLOCK when a MANDATORY_HACKSKILLS file < 500 bytes
  (repo ships `common-passwords.txt` at 404B) — replace in BOTH skills/ and bundle-src/.
- Grep every candidate's poc/evidence for placeholder `target.com` → drop as noise.
- Diff normalized baseline vs variant bodies to disprove query-echo "findings".
- Verify CVE-repo hits with the canonical bypass probe manually (e.g. CVE-2025-29927:
  `x-middleware-subrequest` header must leave protected 401 as 401).
- `dalfox <url>` is wrong CLI (needs `dalfox url <url>`); CORScanner/ffuf reject
  `--headless`; SSRFmap needs `-r/-p`; graphqlmap crashes on py3.14 readline — these get
  logged "EXECUTED" but never scan, so don't trust their evidence files as coverage.
- **A catch-all route (or a `/<username>` URL scheme) manufactures fake "exposed panel" hits.**
  On a target whose router turns any unknown path into a 200 page (2026-09), the pipeline flagged
  `/admin/login`, `/manager`, `/swagger`, `/debug`, `/upload` as "info-disclosure … 200" — all noise:
  the site's URL scheme is `/<username>` → public member profile, so `/manager` and `/swagger` are
  just traders' profiles, and `/admin/login` returns `302`. Tells to catch it before it reaches a
  report: (a) **identical response sizes across unrelated paths** (the pipeline logged exactly
  `2000`/`4000` for every one — a truncation artefact, not content), (b) every path in the list has
  the same status, (c) the size is far smaller than a real page. Confirm with one direct request per
  path (`curl -o /dev/null -w '%{http_code} %{size_download}'`) and drop the whole set if the sizes
  match. Never carry "panel discovered" into a report off the pipeline's `interesting` flag alone.

> **Full triage recipe + screenshots of the noise:** `references/pipeline-triaging-2026-09-26.md`

