# Secret leak via error strings, logs and status APIs

Class: an operator/protocol secret ends up in text that leaves the trust boundary —
an error message returned to a client, a status endpoint, a log line shipped to an aggregator.
This is the concrete shape of the Immunefi **"Private information being stolen"** (High) impact,
and it is a genuinely reachable bug class on *off-chain* software (indexers, nodes, agents, APIs)
where the contract-only hunt usually stops.

Verified while auditing graph-node (The Graph Immunefi program, 2026-10).

## The canonical source: credentials embedded in URLs
Provider URLs carry the secret in the path/query and are the #1 carrier:
- RPC endpoints: `https://eth-mainnet.g.alchemy.com/v2/<KEY>`, Infura, QuickNode, dRPC
- DSNs / connection strings: `postgres://user:pass@host/db`
- webhooks, log-store endpoints (Elasticsearch/Loki basic-auth), S3 buckets

HTTP clients put the **whole URL** into their error text. `reqwest` (which alloy, most Rust
stacks, and graph-node's transport sit on) yields:
`HTTP status client error (401 Unauthorized) for url (https://…/v2/<KEY>)`
and `error sending request for url (https://…/v2/<KEY>)`. Python `requests`/`urllib` behave the
same way, so a 20-line local harness proves "the transport error text carries the secret" without
standing up the whole target.

## The method (in order)
1. **Enumerate the secret sources** in config/env, then grep for those values' shapes being
   formatted into output: `format!(`, `err.to_string()`, `{:?}`, `{:#}` (anyhow alternate = FULL
   cause chain), `Internal server error: {}`, `"error": …`.
2. **Find whether a redaction helper exists** (this is the tell that the team already considers
   the value sensitive). graph-node's is `redact_log_urls(true)` with regex
   `https?://[a-zA-Z0-9\-\._:/?#&=]+` → `[REDACTED]`, in `graph/src/util/futures.rs`.
3. **Check WHAT the redactor is applied to.** The graph-node case is the textbook bug: redaction
   is applied to the *log string built inside the retry loop*, while the returned error **value**
   is passed through untouched (`Err(result.map_err(TimeoutError::Inner))`) and later formatted
   unredacted into the persisted error message.
4. **Check consistency across call sites.** The smoking gun is asymmetry within one failure:
   ```
   WARN ... failed ... error sending request for url ([REDACTED])          <- redacted path
   ERRO ... failed ... error sending request for url (http://…/v2/<KEY>)   <- same URL, unredacted
   ```
   Also check boot-time logs (graph-node prints the full `web3.url` at "Creating transport").
5. **Trace promotion to a client-visible surface.** Persisted error → status/graphql API →
   is that endpoint authenticated? Watch for APIs whose auth gates *only some fields*
   (graph-node's `PoiProtection` gates `proofOfIndexing` and leaves `fatalError.message` open).
6. **Check the default deployment**: does the shipped `docker-compose.yml` publish the port, and
   is there a default-off auth env var (with a startup WARN admitting it)?

## Control-gap testing: the product ships a redactor — does it actually redact?

The sibling of the section above. There the bug is a *missing* redaction; here the product
advertises masking/redaction of values marked sensitive, and the control itself is the target.
High yield on self-hosted/on-prem products, and programs often name it in their focus list
(the Octopus Deploy brief asked outright for "variables marked 'sensitive' not correctly masked
in task logs").

Set up one runnable unit (a deploy/runbook/task that executes a script), then one variable per
row, and read the RAW log back through the API:

| # | Probe | Gap it exposes |
|---|-------|----------------|
| 1 | print the value plainly | baseline — does the control work at all |
| 2 | print it again after a long stretch of filler output | streaming / chunk-boundary handling |
| 3 | values of length 1, 2, 3, 4, 8, 16 | **minimum-length cutoff**: implementers skip short values ("masking a 1-char string would blank the whole log"), so a 3-char secret is never masked. Find the exact boundary and quote it |
| 4 | `\| head -n 1`, `\| tail -n 1`, `\| cut -c1-20`, `\| fold -w 10` | **exact-match-only**: a trie/Aho-Corasick masker rewrites only *complete* occurrences, so every partial reproduction is emitted verbatim |
| 5 | a multi-line secret (2, 3 and 40 lines) printed whole vs. one line of it | multi-line handling — the whole value often masks fine while any prefix/suffix leaks |
| 6 | the value embedded mid-line (`echo "x${S}y"`, or a shell error that echoes the line) | substring matching |
| 7 | the value in a **platform-rendered** surface rather than script output (step instructions, manual-intervention text, notes, an approval prompt) | the control is wired into the log path but not the templating path |

Then read the shipped code for the two constants that decide everything: the length cutoff and
the match semantics. The same masking classes are frequently shipped in several components
(server *and* agent), so one root cause explains both — verify by counting the class-name string
in each DLL rather than assuming.

Root cause to name in the report: a trie of sensitive values matched with **complete-pattern**
semantics, plus a hardcoded `length < 4` skip, plus a deferred-partial buffer that is flushed
**unmodified** when no complete match ever arrives.

Severity honesty: partial disclosure and short secrets are genuinely low (P4/P5) — do not inflate
it into "secret exfiltration". The finding's weight is that a *documented security control*
silently fails. Two things raise its credibility:
- name the boundary exactly (length 1–3 unmasked, 4 masked) instead of "short values leak";
- prove the **audience** rather than asserting it — read the leaked log as a deliberately
  under-privileged account and paste that request. Then the impact is demonstrated, not claimed.

Check every surface that carries the log (`/raw`, `/details`, `?verbose`): they normally all leak,
because they share one renderer — worth one line in the report so the fix is scoped correctly.

## Evidence that actually convinces a triager
- The same failure captured twice: redacted line + unredacted line.
- The exact code line that formats/persists the unredacted value.
- The served response (curl output) containing the secret.
- The default config that exposes the surface (compose port mapping, default bind address).

## Pitfalls
- **Verify the promotion path before claiming a served leak.** A background retry loop may log
  the secret forever without ever writing it to a record a client can read. On graph-node, a dead
  RPC never becomes a served `fatalError.message` — the streamer just retries.
- **Distinguish log-only from remotely-readable.** "Secret in a local log file" is much weaker
  than "secret in an HTTP response". Say which one you proved.
- An **unauthenticated admin/control API** is a separate (and easier) finding: prove it by issuing
  a real state-changing call from outside the container. Impact wording differs from an
  info-disclosure, and programs that list "best practice critiques" as out-of-scope may reject an
  insecure-default binding — check the reward table, not the prose.
- Don't over-claim severity: a leak of the *provider* key (a paid-but-replaceable credential) is a
  clean High on a program that accepts "private information", but it is not "user funds stolen".

## Related
- `references/graph-node-indexer-audit.md` — the full live PoC harness this came out of.
- `references/info-disclosure-complete.md` — broader info-disclosure surface checklist.
- `references/self-hosted-product-audit.md` — the workflow when the "secret in logs" target is a
  product you install yourself (licence, container lab, RBAC negative, plain-text reporting).
