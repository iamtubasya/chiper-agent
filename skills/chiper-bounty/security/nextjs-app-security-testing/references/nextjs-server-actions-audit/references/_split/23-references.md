## References
- `references/quarterwise-2026-session.md` — concrete numbers/tables from a full VDP
  engagement (lockout counts, 500-path matrix, duplicate evidence, coverage summary).
- `references/authed-api-hardening-matrix.md` — expected values and probes for a bearer-key
  API, reference-id idempotency, rate-limit headers, document store, rendering, and MFA.
- `references/gated-route-handlers-and-form-silence.md` — flag-gated route handlers (how to
  unlock and BOLA-test them), reading an id out of a collapsed row, the three submit paths that
  emit no request, the Playwright/JS snippets that fail loudly, and a parameter boundary sweep.

- Related skill: `tax-rule-verification` — load it when the same engagement also asks for
  tax/financial calculation correctness. Writing ledger entries through the product's API and
  then reading its own dashboard summary panel gives you a per-scenario oracle for the rules.
- `references/quarterwise-pro-phase2.md` — the same target after a vendor fix, testing one
  invariant across five write paths (form add/edit/delete, CSV-import mapping dropdown, REST
  API), plus the API contract results, the controls that held, and two self-inflicted
  incidents (mis-scoped revoke click, CDN block from a rate-limit burst).
- `references/quarterwise-full-matrix-2026-10.md` — the fresh re-run on the same target as a
  FIRM/multi-client plan: per-class result matrix (all negatives), the three informational
  findings, the replay/identity pitfalls in context, and the cleanup/residue list.
- `references/cross-tenant-data-access-matrix.md` — the 17-vector cross-tenant pass ("can I read
  another user's ledger?"): object pages, API, the discovered ledger-export route, aggregate
  exports, header/param tenant overrides, unauth, write-path ownership, the byte-identical-404
  oracle test, artifact-content verification, and the honest gaps when login is throttled.
- `references/server-action-wire-ids-and-inventory.md` — the two id spaces (bundle reference id vs
  the per-render `next-action` wire id) with the captured wire shape, and the 109-named-action
  inventory by subsystem with a test-priority order.
- `references/ledger-export-endpoint-abuse.md` — the 49-probe abuse sweep of an authenticated
  ledger-export route (cache leak, CRLF-in-filename, traversal/encoding, alternate id spaces,
  rewrite headers) plus the shared-property three-surface result and the zero-risk write oracles
  used against it.
- `references/server-action-target-id-tamper-matrix.md` — the in-flight target-id rewrite harness
  (route interception, wire-id capture, response parsing), the 7-action cross-tenant write matrix
  with positive controls, the review-queue population recipe, the five harness bugs that faked
  results, and the ground-truth/cleanup notes.