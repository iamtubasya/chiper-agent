## Cross-tenant data-access pass — "can I read someone else's ledger?"

Run this as its own named pass whenever the user asks whether OTHER USERS' data is reachable (as
opposed to hunting one BOLA). Two independent tenants, both directions, one matrix; the deliverable
is a table of what held, not a hunt for a single bug. Full 17-vector matrix, commands and the honest
untestable gaps: `references/cross-tenant-data-access-matrix.md`.

Condensed rules that separate a finding from a false positive:

- **A 200 on an aggregate/named export is not automatically a leak.** `/app/clients/export.csv` as a
  non-firm account returned **200 with a header-only CSV** (no rows) — scoped, correct. Read the body
  before scoring a 200 either way.
- **Verify the artifact, not just the status.** Download the export (PDF/XLSX) and assert it carries
  only the requesting tenant's identifiers: parse the PDF text with `pymupdf`, unzip the XLSX and
  scan the XML for foreign names/uuids. That turns "the endpoint is scoped" into evidence.
- **Test for an existence oracle.** A foreign id and a random uuid must return byte-identical bodies
  (`{"error":"not found"}`, 21 bytes, both classes). If they differ you have an enumeration oracle
  even when nothing leaks — worth reporting in its own right.
- **Tenant-override attempts belong in the matrix, not in your head.** Headers `X-Account-Id /
  X-User-Id / X-Client-Id / X-Organisation-Id / X-Firm-Id / X-Tenant-Id / accountId / X-Account` and
  query params `accountId / clientId / userId / sourceId / includeShared / all / debug / raw` — all
  ignored here; a param that IS honoured is the interesting one.
- **Validate numeric params at their boundaries.** `limit` accepted 1–200 and rejected `-5` / `1e9`
  with `422 limit must be a whole number from 1 to 200` — that 422 is the control proving the
  limiter runs, and it is what makes "unknown params ignored" credible.
- **Re-verify ownership on the WRITE path too**, by overriding the hidden id in a real form
  (`form.requestSubmit()` after setting `propertyId`) while signed in as the other tenant. Explicit
  refusal strings are the evidence; a digest-only 500 is a harness failure, not a denial.
- **Do not claim edge throttling as a finding.** Intermittent 500s on authed pages (`/app/file`,
  `/app/year-end`) during a high-volume pass, using the digest-only Next.js error page (no stack, no
  data), are almost always your own footprint. Record them as unverified and say they need a retest
  from a clean IP.

