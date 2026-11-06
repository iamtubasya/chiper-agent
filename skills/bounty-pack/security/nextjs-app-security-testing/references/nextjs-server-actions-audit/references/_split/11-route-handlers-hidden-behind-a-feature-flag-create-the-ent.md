## Route handlers hidden behind a feature flag — create the entity that unlocks them

Bundle greps surface handlers whose UI never renders for your account. On Quarterwise the group
was `InvoicesTab`: its props included `invoicing`, and the tab only appeared once a source was a
**self-employment business** — the Pro account (property-only) never saw it, so an earlier pass
had filed the handler as "coverage gap".

Playbook when a handler's object model is gated:

1. Read the tab/component's props in the chunk (`{propertyId, businessRowId, isSe, invoicing, …}`)
   — that names the flag and therefore the entity to create.
2. Create the enabling entity through the app's own flow (here: dashboard → **Add an income
   source → Self-employment**, name only). The tab then renders; the reverse (a self-employment
   source on an account that had none) is also how you get `businessRowId` values to play with.
3. Objects inside the tab are **collapsed rows**: `button[aria-expanded="false"]` whose innerText
   carries the visible reference (`INV-0001`). Click it, *then* grep the DOM for the handler URL
   (`/api/invoices/<uuid>/pdf`). Grepping before the expand returns nothing and reads like "no id".
4. Run the standard BOLA matrix on the id: owner session / second account / no session / random
   uuid. Keep the owner's 200 body as evidence (it carries customer name + address — exactly why
   the handler matters) and clean the object up afterwards.
5. A sensitive sibling form that *does* require a `mfaCode` is a **positive control** worth
   reporting (bank details are code-gated even with 2FA already on).

