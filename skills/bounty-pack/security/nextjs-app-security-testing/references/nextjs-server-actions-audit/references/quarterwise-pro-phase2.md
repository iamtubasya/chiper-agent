# Worked example — one invariant, five write paths (quarterwise.co.uk, phase 2)

Target: a UK MTD/tax SaaS (Next.js App Router + Server Actions, Cloudflare, Stripe).
Phase 1 shipped a "category must be tied to a parent entry" finding which the vendor fixed
and rated Low + credit. Phase 2 (this file) verified the fix and continued on the paid API
surface. Every number below is from the app's own export / API, not from page text.

## The invariant, tested on every write path

Rule under test: *"Tax withheld from rent" must not be recordable as a standalone line — it
belongs to a rent entry and must be less than that rent.*

```
                path                          result
form add      choose category directly      REFUSED  "Choose a valid category."   (server)
form add      withheld 5000 > rent 500      REFUSED  "Tax taken off should be less than the rent amount."
form add      tampered multipart body       REFUSED  server-side (client had passed 100 < 500)
form edit     ordinary entry -> hidden cat  REFUSED  "Choose a valid category."
form edit     withheld 10 -> 500 (rent 200) ACCEPTED "Tax withheld at source" 10,668.02 -> 11,158.02
form edit     rent 200 -> 5 (withheld 500)  ACCEPTED
form delete   discharge the rent entry      ORPHAN   withheld row survives, total unchanged 779.24
import file   per-row category dropdown     ACCEPTED standalone row, on the FREE plan
REST API      category: "taxDeducted"       ACCEPTED 201 created  (Pro)
```

Negative controls that make the two ACCEPTs meaningful — the validator *is* running:

```
POST category=premisesRunningCosts -> 422 invalid_category
POST category=seTaxDeducted        -> 422 invalid_category
POST category=totallyBogus         -> 422 invalid_category
```

So the REST API's whitelist for `uk-property` contains a key the UI refuses: the UI is
stricter than the API, which is the strongest evidence the difference is unintended.

## Import path detail (the one that mattered most)

The bulk-import wizard has a category-mapping step per row:

```
select[name="cat-key-0"], cat-key-1, cat-key-2 ...
   option value=taxDeducted  text="Income: Tax withheld from rent"
```

Options are not filtered by the fact that the target is a UK property, and the import has no
equivalent of the "tax already deducted" field that ties the figure to a rent entry. Flow:
upload CSV (`Date,Description,Amount`) -> set the per-row selects -> "Apply mapping &
continue" -> pick the target listing -> "Continue to preview" -> "Import these
transactions". Result: `3 transactions added`, including
`03/05/2026 | Tax withheld | Tax withheld from rent (not income, not in totals) | 100`
with no rent on that date. **Import was a free-tier feature, so this reproduced on a
free account** — worth checking on every tier, not just the paid one.

Watch the flow-shape traps: the listing `<select name="listing-0">` defaults to *create a new
property* (which silently hit the free-tier limit and produced "This file covers 1
properties — the Free plan includes 1"), so pin it to the existing source id when you are
testing free-plan behaviour. And the button chain is multi-step — "Import these
transactions" only exists on the third screen, so a single pass over a label list ends one
click short.

## REST API detail

`openapi.json` was public, so the contract was known in advance: 5 operations, cursor
pagination (`limit` 1..200 default 50), bulk arrays max 500, idempotency on `externalRef`,
documented 120 req/min per key, 5,000 transactions/24 h cap. Behaviour worth recording:

```
/me capabilities: readBookkeeping true, writeBookkeeping true, hmrcSubmission FALSE
auth: no key -> 401 missing_key; garbage key -> 401 invalid_key; key+1 char -> 401 invalid_key
key with surrounding spaces -> 200  (bearer-token trim; INFO, NOT a finding)
foreign source uuid -> 404 source_not_found (GET and POST); traversal -> 400; null byte -> 400
amountPence 0 / -1234 / 1e18 / 1.5 / "100" -> 422 ; bad dates -> 422 ; type bogus -> 422
[] -> 422 empty_body ; 501-item array -> 422 too_many ; description >500 chars -> 422
externalRef twice -> 201 then 200 (created 0, deduplicated 1)
8-way concurrent POST, same externalRef -> exactly one 201  (dedup holds under race)
```

Controls that held and are worth telling the vendor about (they build credibility for the
negatives): keys stored hashed ("we store only a hash"), revocation effective immediately
(revoked keys -> 401 at once), per-source authorization, documents 404 for another account
and 307 unauthenticated, `.html`/`.svg` rejected by the document store, AI endpoint accepts
only a form upload (no URL parameter, so no SSRF).

## Two self-inflicted incidents, and the lessons

1. **Revoked both API keys with one mis-scoped click.** Revocation has no confirm dialog and
   the list re-renders; the follow-up "confirm" click landed on the next row's Revoke. Every
   key in the account then returned `401 invalid_key`. Lesson: scope destructive clicks to a
   single row container and assert the row text; verify with an explicit before/after list.
2. **A 200-request burst tripped Cloudflare `Error 1010 Access denied`** for all API traffic
   from that IP (including legitimate use), and it cleared on its own a few minutes later.
   The burst itself returned 200 ×200 with zero `429`, so the documented per-key limit is not
   enforced — but the honest write-up is that a blunt edge block substitutes for the
   documented control, not that "there is no protection". Re-test with a browser-like
   User-Agent and pacing before writing it up, and never file a finding whose only artifact
   is your own footprint.
