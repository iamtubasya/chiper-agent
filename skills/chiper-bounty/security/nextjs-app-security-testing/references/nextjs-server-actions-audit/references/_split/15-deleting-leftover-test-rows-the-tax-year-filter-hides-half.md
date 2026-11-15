## Deleting leftover test rows: the tax-year filter hides half of them

When clearing an account you tested, the entries list renders ONE tax year by default
(`?ty=2026-27`), so rows dated inside the previous year stay invisible and your "0 entries"
API count contradicts the UI. Iterate the year param (`?ty=2025-26`, `?ty=2024-25`, …),
deleting `button[aria-label="Delete entry"]` until zero, and finish with an API count per
source. Also expect MORE than one probe property: a previous import run may have created
"<filename>" as its own source — enumerate `/api/v1/sources` and clear each, not just the one
you remember.

