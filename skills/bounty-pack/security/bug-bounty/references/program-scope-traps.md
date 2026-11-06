# Program scope traps — read the brief's OOS list BEFORE recon

> Generalised checklist. The worked case study (full host map, reward tiers, hardened-host table,
> GraphQL/surface detail) lives in `references/tripadvisor-2026-10-engagement.md`; the CDP/form-fill
> mechanics in `references/authed-webapp-cdp-testing.md`. When this file and the live brief disagree,
> **the brief wins** — re-fetch it.

Most wasted effort in a bug-bounty engagement is testing an asset the program already excluded, or a
bug class the program parked. The brief's Out-of-Scope section is not boilerplate; it routinely
excludes **entire brands**, **whole bug classes**, and **path prefixes** that you will otherwise
rediscover from scratch. Read it first, and read the *rendered* page — a text/markdown extraction
silently drops the hrefs you need (see "Extraction" below).

## 1. Sibling BRANDS are usually out of scope, and they share the parent's footprint

A media/booking group lists its acquisitions as separate programmes. Their domains look like
"the same company", so they land in your recon list and feel in-scope. They are not.

Worked case — Tripadvisor Media Group (Bugcrowd `tripadvisor-bb-og`, 2026-10). Explicitly OOS
because they "operate independently":

| Brand | Domain |
|---|---|
| CruiseCritic | cruisecritic.com |
| TheFork / LaFourchette | thefork.com |
| Jetsetter | jetsetter.com |
| SeatGuru | seatguru.com |
| Viator | viator.com |
| HelloReco | helloreco.com |

Plus "domains owned by companies for which TAMG only has a minority investment" (named example:
traxo.com) — i.e. check *ownership percentage*, not just the brand name.

Rule: when a target is a holding company, build an explicit allow-list from the brief's target
tables and drop everything else — do not infer scope from shared WHOIS/branding.

## 2. A parked bug CLASS can kill a whole workstream

The Tripadvisor brief carries: **"IDOR in property owner features is temporarily out of scope"**.
Any property-owner / supplier-extranet access-control finding is therefore unsubmittable right now,
regardless of how clean the PoC is. Note it, skip the workstream, and re-check the brief in later
sessions — "temporarily" means it flips back.

Other class-level exclusions that recur and are easy to forget mid-hunt: missing HTTP security
headers, content/rating fraud, mass account creation or spam, DoS, social engineering and plain open
redirects (accepted only with additional impact), attacks against AI features, and anything needing
physical access or a rooted/compromised device.

## 3. An OOS path can hide an OOS *feature* reached by another route

`/Trips` was explicitly OOS on Tripadvisor. The same data was reachable through the GraphQL
persisted-query endpoint (`POST /data/graphql/ids`, query id returning trips for a `userId`) — a
different path, same feature. **Scope follows the feature, not the URL.** If you find a parked
feature through a side door, it is still parked; report the *route* to the operator and move on.

## 4. "Use test properties only" is a constraint on your whole method, not a footnote

Tripadvisor: *"Interacting with legitimate live properties or customers is strictly forbidden. Even
minor actions such as marking a review as helpful are forbidden."* Combined with *"use test
properties whenever possible"* (Test Hotel 1/2, Test Vacation Rental 1/2, Test Restaurant 1/2,
Test Tour(s), Test Attraction(s); Atafu = location id 446951), this means:

- Authed flows that need a **target entity** (photo upload "where'd you take these?", reviews,
  testimonials, helpful votes) are **untestable** until you have the test-property ids.
- Every flow that needs an entity ends in a place-picker — discovering the endpoint is not the same
  as being able to exercise it lawfully.
- Identify as the programme requires on every request and every created object (UA containing
  `bugcrowd`, accounts/names containing `Bugcrowd`). Assume an unlabelled artefact is a rules breach.

Practical consequence: if the test-property ids are missing, **stop that workstream and ask for
them** rather than testing against a live property. This was the correct call in the Tripadvisor
session — it blocked photo-upload and review work, and the honest blocker was reported instead.

## 5. Extraction: keep the links, or you will lose exactly the thing you need

The brief was extracted text→markdown early in the engagement; the "test properties" list came
through as bare names with **no hrefs**, and the ids were unrecoverable from the saved file later.
Two rules:

- Fetch the programme page with a tool that preserves structure (`web_extract`, or save the raw HTML)
  and keep the raw copy, not just the cleaned prose.
- Treat the brief as a live document: re-fetch it at the start of each session. Scope lines change
  (parked classes un-park, brands get added), and an old copy is how you burn a session.

## 6. Also capture from the brief: channels, rates, and the exact fix-status language

- **Submission channel** (dashboard form vs. a mailbox) — determines whether the deliverable is a
  staged draft or a filled form; never invent a recipient (`bug-report-delivery` covers this).
- **Severity authority** — some programmes use VRT+CVSS, self-hosted VDPs use CWE+CVSS only.
- Their stated rate-limited / version-disclosure / enumeration carve-outs — findings in those classes
  are typically $0 and should be excluded at triage, not after writing.

## 7. Recon still applies — just bounded

Scope filtering is not an excuse to skip reconnaissance. `subfinder` on the parent still produces
the in-scope estate (Tripadvisor: 825 subdomains, ~71 live), and vac-rental/country domains in the
brief's own target table are fair game even when a sibling brand is not. Filter the *results* by
the brief's tables; do not skip the enumeration.

## 8. Pool metadata is a HINT, the policy page is truth — verify before committing

The local target pool's `reward`/`hosting`/`live` fields are scraped and go stale. Two live
examples from one session (2026-10-17), both cost a full 0A before the policy page was read:

- Pool said `reward=monetary` for `lolipop.jp` / `shop-pro.jp` / `suzuri.jp` (Pepabo, JP). The
  actual policy says **報奨金制度は設けておりません — no reward programme at all**.
- Pool said `reward=monetary` for `dopetech.au`. The policy says *"DopeTech does not currently
  advertise a cash reward programme."*

Rule: before starting an engagement from a pool pick, **fetch the policy/security.txt and confirm
(a) a reward actually exists, (b) the scope table, (c) the exclusions list** — 5 minutes that
decide whether the next hours are worth spending. Same check when the user names a target
directly. If the program is reward-less and the user still wants the audit, that is their call —
but say so explicitly before burning the session, and record the no-reward fact in STATUS.md.
