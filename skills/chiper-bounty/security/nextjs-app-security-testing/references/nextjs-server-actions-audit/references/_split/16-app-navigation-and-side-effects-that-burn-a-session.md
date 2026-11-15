## App navigation and side effects that burn a session

- **The default landing page depends on the account's ROLE.** Once a test account becomes
  someone's adviser (or gains any client/tenant relationship), `/app` permanently redirects to
  the client-view dashboard and the personal dashboard's controls ("Add an income source", the
  tax-estimate panel) are GONE from that page. Do not conclude the feature disappeared — look
  for a role/view switcher: observed `?view=mine` restores the personal dashboard. Diff the
  nav `href`s (two entries differing only by query string is the tell).
- **Never use "submit any form on the page" as a fallback.** A generic
  "find a form, click `button[type=submit]`" fallback fired the only submit on the page
  ("Refresh from HMRC") — an action the engagement was explicitly forbidden to take — and
  killed the session (next request 307 → /login). Target an explicit selector AND explicit
  button text; if the control isn't identified yet, dump the DOM instead of clicking a neighbour.
- **Cleanup controls are often plain form POSTs, not server actions**:
  `<form action="" method="POST"><input name="$ACTION_ID_<hex>"><input name="accessId" …>`.
  `button.click()` and even `form.requestSubmit()` can no-op after hydration. Two failures =
  stop; it is account hygiene, not a finding. Record it as a leftover for the user and move on.
- **Re-check `location.href` after any unexpected transition.** A silent redirect to /login
  makes every later assertion meaningless ("not found" that is really "not authenticated").

