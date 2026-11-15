# Scanner artefacts and vendor-documented errors are not findings

Two triage cases measured on live programs (2026-10). Both reached a draft stage before the "is this even
ours / is this even a defect?" question was asked. Ask it earlier.

## 1. Network/TLS scan hits on a CDN or wildcard-DNS host

A scan `ssltest`-style report flagged weak cipher suites, a 2048-bit key and a corporate-looking CN on hosts
the program had not listed. Reverse DNS put them in a cloud provider's shared edge pool — no relationship to
the target's own infrastructure.

Checks to run before writing anything network-level:

- `dig +short <host>` / `host <host>` → does the IP belong to the target, or to a shared CDN/edge block?
- Wildcard test: resolve a random name (`zzz-not-real-92731.<domain>`). If it answers, every "finding" under
  that domain (expired cert, weak cipher, parked page) is DNS/CDN noise, not the target.
- Does the host even appear in the program's scope list? "It resolves" is not "it is in scope".

The same discipline applies to a scanner's `info`-level results on a host you never confirmed ownership of.

## 2. A `500` the vendor already documents

A "crash" claim was built on an API endpoint returning `500` for a missing/incorrect parameter. The vendor's
own documentation states the field takes exactly twelve digits and that any other value produces an unhandled
exception server-side.

Rules:

- Read the vendor's documented constraints for the parameter before calling an error response a finding.
- An input-validation `500` that the docs describe as expected behaviour is **at most a hardening note**
  ("return 400 instead of 500"), not a vulnerability — and if it is documented, it is usually excluded.
- The version of this that *is* a finding: the error leaks something it shouldn't (stack trace with internal
  paths, SQL, secrets), or the same input path reaches an unauthenticated operation. Test that specific
  consequence; don't report the status code alone.

## Where this belongs in the funnel

Both cases are the same failure mode the 7-question triage exists to catch: a raw signal (scan output, error
status) promoted to a finding without the ownership/expected-behaviour question. Apply it at candidate time —
before a draft, a PDF or an email exists, because a withdrawn report costs more credibility than a quiet
"not a finding".
