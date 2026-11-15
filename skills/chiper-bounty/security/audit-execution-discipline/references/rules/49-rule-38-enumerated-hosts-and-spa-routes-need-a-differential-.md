## ⛔ RULE 38: Enumerated hosts and SPA routes need a DIFFERENTIAL — most "found" surface is noise

Three differentials that turned would-be false findings into verified negatives on 2026-10-01:

1. **Wildcard DNS kills half of subfinder's output.** Prove it with random names before reporting any host:
   ```bash
   for h in zzz-nope-12345.target.com totally-random-9f3a.target.com; do
     python -c "import socket;print(socket.gethostbyname('$h'))" 2>/dev/null || echo NXDOMAIN; done
   ```
   NXDOMAIN on both => no wildcard => hosts that DO resolve are real. On this engagement that test proved 10
   subfinder hosts (`eks.ci`, `eks.security`, `app`, `test`, `preview`, `bbs`, `doc`, `mail`, `openpgpkey`,
   `assets-worker.devddx`) were NXDOMAIN FPs that would otherwise have been reported as "internal hosts discovered".
   A host that resolves but serves no working HTTPS (000) and has no CNAME is a dangling proxied record —
   informational, NOT a takeover candidate. Real takeover check: `nuclei -l subs.txt -t <mirror>/http/takeovers`.
2. **`.well-known/*` on an SPA returns 200 for everything.** Seven paths all returned 200 with ~31.5 KB — the exact
   same size. Confirm by diffing content against a deliberately bogus path:
   ```bash
   curl -s https://target/.well-known/security.txt -o a.html
   curl -s https://target/zzz-not-a-real-path-98765 -o b.html
   grep -oE '<title>[^<]*</title>' a.html b.html    # same title => catch-all, NOT real files
   ```
   Without this check, seven 200s become seven report entries.
3. **`OPTIONS` separates a real SPA app-API route from the catch-all.** A SvelteKit/Next server route handler is
   method-specific, so `GET` on it returns the SPA shell (indistinguishable from a bogus path) while `OPTIONS`
   tells the truth:
   ```bash
   curl -s -X OPTIONS -o /dev/null -w '%{http_code} allow=%header{allow}\n' https://target/api/admin/x
   # 405 allow=GET, HEAD   -> route EXISTS
   # 200 allow=            -> unhandled OPTIONS / catch-all, NOT evidence of a route
   ```
   Only the 405-with-`allow` result counts as proof a route exists. Mine discovered route JS bundles had already
   named (`/api/admin/funds/{id}/gas-costs/invoice`) — bundle mining finds the *name*, OPTIONS proves the *route*.

**Scoring rule for what comes out of this:** a route that answers an unauthenticated `GET` with `500` instead of
`401/403` is a LEAD, not a finding. No data, no side effect, no proof of an authorization gap => record it as
"unrated - lead", state exactly what is and is not proven, and never send a state-changing method to confirm it
(that would violate the vendor's "no state changes" rule and the `payment-entitlement-bypass` line).

> Full walkthrough with the raw transcripts: `references/evm-and-recon-triage-2026-10-01.md`

