# Engagement Scope Discipline — read the rules BEFORE touching a target

Learned the hard way on the 2026-10 Tripadvisor (Bugcrowd) engagement: time was spent probing
assets that turned out to be out of scope, and a rule gray-area was entered on a live property.
Both were avoidable by reading the brief's OOS list and program rules first.

## Rule 1 — Parse the OOS list AND the brand carve-outs up front

A program's scope page is not just "here are the domains". It usually contains:

- **Explicit OOS paths** — e.g. `/Trips`, `/Mobile*`, `/engineering`, `/WidgetEmbed-*`,
  `*adexpress`, `*wifi`, `taplus/*-plus`.
- **Explicit OOS hosts** — e.g. `ir.<corp>`, `*.<locale-tld>`, `careers.*`, `spotlight*`.
- **OOS CLASSES** — frequently: missing-security-headers, mass signup/spam, content fraud,
  DoS, social engineering / open redirect, AI-system attacks, physical access, and — often
  *temporarily* — a whole feature area (e.g. "IDOR in property-owner features is temporarily
  out of scope"). A **temporary** carve-out matters: a real bug in that area earns nothing now.
- **Separately-operated brands under the same parent.** This is the trap. Parent companies
  list brands that "operate independently" as OOS even though they share a domain family.
  On Tripadvisor that was: CruiseCritic, TheFork/LaFourchette, Jetsetter, SeatGuru, Viator,
  HelloReco — plus minority-investment domains (e.g. traxo.com). A researcher who assumes
  "same parent ⇒ in scope" wastes an entire recon+test cycle.

**Do:** grep the brief for the words *out of scope / OOS / not eligible / independent / temporary*
and write the carve-outs into the engagement log before any probing.

## Rule 2 — Never touch live/production customer entities

Standard program rule, and the one most easily tripped: *"Interacting with legitimate live
properties or customers is strictly forbidden — even minor actions such as marking a review as
helpful."*

- If the program supplies **test entities**, use ONLY those (the brief names them: test hotel /
  rental / restaurant / tour / attraction, a test city + geo id, test bank details).
- **Missing test-entity identifiers is a hard blocker, not an invitation to improvise.** If you
  can't find them, the correct move is to ask the user to paste them from the brief — not to
  POST to a real customer's object. Testing "does the endpoint accept an unauthenticated write"
  by actually writing to a live object risks the whole submission being omitted.
- Label every created entity/account/content with the program's required token (usually the
  platform name, e.g. `bugcrowd`) and put it in the `User-Agent` too.

## Rule 3 — A gated feature you cannot test safely is a NEGATIVE, not a workaround

If a feature requires a "place target" (photo upload, review, booking) and no test target is
available, record it as *blocked / not tested* and move on. Do not substitute a live object.

## Rule 4 — Log the state you changed on the target

Disclose every mutation in the engagement log: accounts created, fields set and reverted,
requests sent to live objects (even one, even reverted). It protects the submission and makes
the "we only used test entities" claim auditable.

## Related

- `evidence-hygiene` — capture + redaction discipline for what you *do* test.
- `triage-validation` — validate before writing the report.
- `report-writing` / `bugcrowd-reporting` — program-shaped deliverable.
