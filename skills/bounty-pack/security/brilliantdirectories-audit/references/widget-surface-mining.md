# Mining a component/widget render surface for authz bugs

Generalises beyond BD: any platform that ships "components the site owner can place on a page"
(widgets, blocks, shortcodes, Liquid partials, Gutenberg blocks, Elementor widgets, Twig includes)
usually exposes a **render endpoint** that executes the component's server-side code. Page-level
auth lives in the page controller; the render endpoint is a *different* entry point and frequently
forgets the session check. That asymmetry is the bug class.

## Why this beats endpoint fuzzing
You are not guessing paths. You are reading the vendor's own server-side source, because the product
hands it to you via its own API:

```
GET /api/v2/data_widgets/get?limit=100&page=N     # 520 rows on a default BD install
# 415 of them contain "<?php" -> that is 2.9 MB of the product's source code
```

No decompilation, no CVE, no guessing. Then grep for auth smells.

## Procedure

1. **Enumerate** every component. Paginate until `current_page == total_pages`.
2. **Dump** `widget_data` (server code), `widget_javascript`, `widget_settings` per component.
3. **Classify by auth smell**, in this order of payoff:

| smell | meaning | payoff |
|---|---|---|
| `$_COOKIE['userid']` used directly in a query or `getUser()` | identity from client | **IDOR** |
| `if (!isset($_COOKIE['userid'])) $_COOKIE['userid'] = $_GET['user'];` | explicit fallback to a request param | **IDOR, unambiguous** |
| `$_GET['<id>']` / `$_POST['<id>']` reaching a query without an owner compare | object ref with no authz | **IDOR** |
| no `$_SESSION` / `isUserLogged` / CSRF token anywhere in the file | gate simply absent | **unauth access** |
| `showquery`, `debug=1`, `print_r`, SQL echoed | debug left in prod | free SQLi confirmation + info disclosure |
| `curl_init` + attacker-influenced URL | SSRF | separate finding |
| query built by concatenation (`LIKE '%$v%'`, `= '".$x."'`) | injection primitive | report as code-level unless proven |

4. **Contrast the gate.** Prove the page is protected *and* the component is not, with the same
   client. This single pair is the strongest evidence you can put in a report:

```
GET /account                     -> 302 /login?login_direct_url=/account     (gate exists)
GET /wapi/widget?...&user=4242   -> 200 + member-scoped output              (gate skipped)
```

5. **Turn the debug echo into the smoking gun.** `showquery=1` (BD) returns the SQL the server ran,
   including the id you supplied — no payloads, no WAF, no timing statistics. It proves both the
   interpolation and the per-identity behaviour in one request.

6. **Differential, then repeat.** Same id twice → identical hash (deterministic). Two different ids →
   different bodies (the query is really per-identity). Then 3 runs × 3 independent installations.

## Evidence discipline (what makes it undeniable)

Build the table from disk, not from notes:

| id | request | http | bytes | sha256[:16] | runs |
|---|---|---|---|---|---|
| 1 | `/account` (no cookies) | 302 | 0 | – | 3/3 |
| 2 | widget, user=1 | 200 | 1351 | ddbd4fad… | 3/3 |
| 3 | widget, user=2 | 200 | 431 | 6939f2ba… | 3/3 |
| 4 | widget, user=4242 + showquery | 200 | 725 | 8d4d4460… | 3/3 |

- Save every response body to `evidence/`, hash at report-build time so the numbers cannot drift.
- Two ids with **different** sizes kill the "maybe it's a cached static page" counter-argument.
- Three independent hosts kill "maybe it's one misconfigured site".

## Verified negatives — do not re-spend time here

These are correctly gated on BD (tested, not assumed):

- `Bootstrap Theme - Function - Comment Handling` — checks `HTTP_ORIGIN` + `validateCSRFToken` +
  `user::isUserLogged` before any write.
- `Bootstrap Theme - Account - Feature Edit` — compares `$post['user_id'] != $user_data['user_id']`
  and redirects.
- `System - Froala Upload Read Images` — requires `$_SESSION['sess']['admin_id']` or a short-lived
  `fmtoken`; unauth returns `[]`.
- `Bootstrap Theme - Member Login Page` — reCAPTCHA enforced, and `formname` must equal `member_login`
  (a missing/different formname skips reCAPTCHA, so they pinned it).
- Admin console: `admin_token` is bound to its own `website_id`; the `newmanage` cookie is site-bound;
  `generateSuperKey` → 400 "Only super admins can generate super API keys".
- REST API v2: keys are per-site (`401 API Key is invalid` cross-install); `X-BD-Site-URL` does not
  switch tenants.

## Do not use payloads to prove injection here

WAF is LiteSpeed + ModSecurity. `AND 1=1`, `SLEEP()`, `extractvalue()` → 403, then the vhost
firewalls the egress IP ("Unauthorized Access … blocked IP", or bare `403 1242`), and the vendor's
monitoring **auto-suspends the trial site**. You lose the environment and gain nothing: `showquery`
plus the concatenated source already proves the primitive. Report it as a code-level observation if
you could not extract data — never claim blind extraction you did not perform.
