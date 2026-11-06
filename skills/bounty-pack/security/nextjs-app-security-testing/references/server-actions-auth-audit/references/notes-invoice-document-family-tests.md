# Notes / Documents / Invoices — family tests, args, and what came back

Session detail behind SKILL.md tech 13. All tests: firm (multi-client) tenant vs an independent free
test tenant, both authenticated, every rejection paired with an owned-id positive control.

## Action → argument map recovered by driving the UI

| action (feature) | wire id (this build) | arguments seen from the client | binding |
|---|---|---|---|
| addNoteAction | `60c622c0804ebf60268fcf1c1e…` | `propertyId`, `body` | client ids |
| deleteNoteAction | `409d22a5487edef5fff0cf983e46c91a23446485c8` | `propertyId`, `noteId` | client-supplied id |
| Edit note (same feature) | — | **no id field** (modal: `body`, `percent`) | server-bound |
| deleteDocumentAction | `402ee1fb4d662864adc8067e126604e60a76d3e958` | `propertyId`, `documentId` | client-supplied id |
| createInvoiceAction | `60fc8d4efaf8e217efc17400ea…` | `businessRowId`, `customerName`, `issueDate`, `customerAddress`, `lineDesc0/Qty0/Price0` | client values |
| mark-paid form | — | `invoiceId`, `paidAt` | client-supplied id |
| deleteInvoiceAction | `60833897c1ec16d30a452eb89b` | `invoiceId` | client-supplied id |
| invoice settings form | — | `propertyId`, `businessRowId`, **`mfaCode`** | MFA-gated (good control) |

## Results

- **Notes, real foreign id (strongest test):** firm's delete-note POST rewritten so
  `_1_noteId` went `ce1e7f21…` (firm) → `6b47054d…` (other tenant's real note). The action ran, the
  other tenant's note **survived**, and our own note survived too (no-op). Unpatched control: own note
  deleted, list went to 0. → scoped.
- **Documents:** `/api/documents/{id}` own session = 200 (real PDF, 214 B); other tenant's session =
  404 (HTML error page, 2045 B). `deleteDocumentAction` with a RANDOM `documentId` → 200 re-render, doc
  still 200 afterwards; control deleted it → 404. Reverse direction UNTESTED: the free tenant has no
  "Add a document" affordance, so no foreign document id could be created.
- **Invoices:** created a draft on the self-employment source (INV-0002, £123.45, Unpaid).
  `deleteInvoiceAction` with a RANDOM `invoiceId` → no effect; control deleted it → list empty. Invoice
  *settings* changes demand an authenticator code.
- **Notes (weak form, for contrast):** with the other tenant's note id and the id swapped on the
  *property* field only, both tenants' notes survived — same conclusion, weaker evidence.

## UI mechanics worth reusing

- Note/reminder/invoice modals are React-controlled; set fields with the **per-prototype** native setter
  (TEXTAREA vs INPUT — see SKILL.md pitfall). Filling only `title` on a reminder leaves it uncreated
  (no object, nothing to test) — verify the object exists in the list before running the cross test.
- Delete controls are `button[aria-label='Delete note'|'Delete document']`; the note confirm is a
  second stage whose affirmative button reads **"Yes, delete"** (not "Yes"). Document delete uses
  "Yes". If the affirmative click isn't found, dump all visible `button` texts — guessing the label
  silently leaves the object alive.
- Invoice rows are collapsed accordions; expand the row (click the button whose text contains the
  invoice number) before hunting for Mark paid / Delete / Download PDF.
- The Documents tab count lives in the tab label (`Documents\n1`) — a quick oracle for "did the upload
  land" without opening the tab.

## Cleanup: confirm the object is gone with an independent read

Delete via the owner session, then re-read the object URL/page: `/api/documents/{id}` → 404, invoice
list → "No invoices yet", notes tab → 0 delete controls. For ledger rows the export PDF is the oracle
and it must go back to the pre-test byte size — a 1-byte delta is just the "Generated <date>" stamp,
but a changed row count is a real residue. Import *batch records* have no delete UI: they stay behind by
design — disclose them rather than claiming a perfectly clean account.
