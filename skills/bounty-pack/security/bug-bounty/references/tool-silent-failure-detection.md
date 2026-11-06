# Detecting tools that failed silently

A scanner that never contacted the target and a scanner that found nothing produce **the same
artefact**: a clean-looking empty result. Before any "tested, negative" row goes into a coverage
ledger or a report, prove the tool actually ran.

Three real cases from one engagement, all caught before they became false claims:

## Case 1 — the scanner skipped the target entirely

```
[INF] Skipped localhost:1322 from target list as found unresponsive permanently:
      cause="no address found for host"
[INF] Scan completed in 3.5219832s. No results found.
[0:00:03] | Templates: 2319 | Hosts: 1 | Matched: 0 | Errors: 43 | Requests: 36/5649 (0%)
```

Exit code 0, "No results found" — and it had issued **36 of 5649** requests. `nuclei -u http://localhost:PORT`
failed to resolve the host; the fix was `-u http://127.0.0.1:PORT`.

**Detection:** read the request counter and the "Skipped ... from target list" lines, not the verdict line.
`Requests: 36/5649` and a <10 s total runtime are the tells. A scan that "completed" far too fast did not run.

## Case 2 — the wrapper invoked a binary that does not exist

The launcher called `$SCRIPTS/sqlmap.py`; the tool was installed as `sqlmap.exe`. All three target URLs
failed instantly, and the `| grep -iE "injectable|parameter|..."` filter swallowed the traceback, so the
output file looked like a clean, empty run.

**Detection:** run the tool's own self-check first (`--version` / `-version`) and make it part of the same
captured output. After the run, assert the evidence file is non-trivially sized and contains at least one
expected marker string. Never filter a tool's stdout on a pattern list without also checking stderr and the
exit code — a filter that matches nothing is indistinguishable from a tool that produced nothing.

## Case 3 — a valid scan curtailed by the target's own rate limiter

```
[INF] Skipped 127.0.0.1:1322 from target list as found unresponsive 30 times
[INF] Scan completed in 1m. 0 matches found.
[INF] HTTP connections: 1438 total
```

The app advertises `Octopus-RateLimit-Policy: l=200;rpm=60`, so a scanner at full rate trips the product's
own limiter and gets marked unresponsive mid-scan.

**Detection:** check the target's rate-limit headers (`curl -D-`) after a throttled scan. Report this as a
**weak negative** — "0 matches over N requests, coverage curtailed by the target's rate limiting" — never as
"clean". Also lower the scanner's rate (`-rl 10`, `ffuf -p 0.15`) and re-run.

## The general rule

For every "tested, negative" claim, be able to answer:

1. Did the tool contact the target at all? (request/traffic counters, connection logs)
2. How much of its plan did it actually execute? (X/Y requests, templates loaded vs clustered)
3. Did it exit non-zero, write to stderr, or get killed by a timeout?
4. Does the evidence file contain a positive marker proving a real run (a known header, a banner)?

If any answer is missing, the claim is **unverified**, not negative. Write "INVALID RUN / could not
verify" in the ledger instead — that is a stronger report than a confident wrong negative, because a
triager who reproduces a bad negative loses trust in every other line.

## Corollary for tool wrappers

When a long shell pipeline wraps a tool, capture raw stdout+stderr to a file **first**, then filter a
copy. Filtering during execution is what hides the failure. `timeout` killing a command yields empty
output with the shell reporting success for the overall pipeline — check `${PIPESTATUS[0]}` or run the
tool without a pipe and grep the saved file afterwards.
