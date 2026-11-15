## Shared-book authz: co-owner vs view-only adviser (API surface)

When the app has any sharing model, test what the API does with each grant — this is where
"self-scoped" findings become cross-account ones:

- Read `/sources` (or equivalent) as each role. A **co-owner** source shows up with
  `role:"sharer"` (plus `sharePercent`) and is **writable** through the API — so a
  fabricated ledger entry can be planted in ANOTHER account's books, and it appears in the
  owner's own export as their own bookkeeping with no attribution. Verify from the victim
  side by downloading the owner's export with the owner's cookie.
- A **view-only adviser** must NOT appear in the API at all. Verified control: the client's
  source is absent from `/sources` and POST returns 404 `source_not_found`. State this
  explicitly — it is the control that proves the API respects the grant.
- Ask whether the API docs mention shared sources at all. Usually they don't, even though
  shared sources appear and accept writes — a consent/documentation gap worth reporting
  alongside whatever write-validation gap exists.
- **A view-only share must be tested on THREE surfaces, because they disagree.** Verified on
  Quarterwise for one shared property (`92d58d01`, badge "Can view"): the app page returned **200**
  ("You are viewing <client>'s books as their adviser · Can view"), `/api/v1/sources` **omitted it
  entirely**, and `/api/properties/{id}/export` returned **404**. None of those is a leak — the
  sharee is entitled to read — but the inconsistency is a legitimate informational report
  (the vendor's own release note claimed the API docs explain how shared properties appear).
  Record all three readings before concluding anything about the grant.
- **Gate-order evidence beats "the button is missing".** With the firm session, three write actions
  aimed at the shared property all refused at the ownership gate, each with a distinct string:
  `updateSourceSettings` → "Only the owner can change these settings.",
  `updateOwnerShare` → "That property could not be found.",
  `deletePropertyAction` → "Only the property owner can delete a property."
  And the firm **could** read it (200) while a genuinely unrelated tenant's property 404'd — so the
  access is per-share, not blanket. That combination (read yes / write no / unrelated no) is the
  shape to report; see the zero-risk oracles section for how to obtain it without mutating anything.

