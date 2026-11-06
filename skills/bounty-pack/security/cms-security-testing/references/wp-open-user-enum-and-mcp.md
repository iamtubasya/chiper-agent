# Case: open WP user enumeration + embedded MCP on a multi-install estate

Source: mydays.de / Jochen Schweizer mydays Group (JSMG) engagement, 2026-10-12/13.
Programme: self-hosted CVD, email submissions, EUR 50–500, scope `*.mydays.de`, `*.jochen-schweizer.de`,
`*.jsmd-group.com`.

The estate runs **eight** WordPress installs across four host groups. Five leaked the user list. This file
records the finding, the controls that make it credible, and the full negative matrix so the next session
does not re-walk any of it.

---

## 1. The finding — open `/wp-json/wp/v2/users` on five installs (MD-C5)

Same route, same parameters, fetched on every host of the organisation:

| host | status | accounts | body |
|---|---|---|---|
| b2b.mydays.de | **200** | 4 | 10 795 B |
| b2b.jochen-schweizer.de | **200** | 4 | 11 746 B |
| career.jsmd-group.com | **200** | 5 | 2 934 B |
| presse.mydays.de | **200** | 2 | 15 793 B |
| presse.jochen-schweizer.de | **200** | 3 | — |
| partner.jsmd-group.com | 401 | — | `rest_user_cannot_view` |
| sokabau.kundenportal.mydays.de | 401 | — | same |
| magazin.mydays.de | 401 | — | same |
| magazin.jochen-schweizer.de | 401 | — | same |

Accounts returned (login slug → display name):

```
b2b.mydays.de            ebrancoveanu → Eduard Brancoveanu
                         emilie-carra → Emilie Carra
                         katja-hornungjsmd-group-com → Katja Hornung      <== login == corporate address
                         timoklein → Timo Klein
b2b.jochen-schweizer.de  same four (ids differ: 3/11/2/9)
career.jsmd-group.com    johann → Johann Schuster
                         piconda → piconda
                         stephan-hochmuthpiconda-com → Stefan Hochmuth    <== supplier domain in slug
                         verena → Verena Gattner
                         hauki → Verena Hauke
presse.mydays.de         leonie-wojta → Leonie.Wojta
                         schuster → Schuster
presse.jochen-schweizer.de  daniela-reinhardt, leonie-wojta, schuster
```

Two impact raisers that belong in the write-up:

- `katja-hornungjsmd-group-com` — the login name **is** a corporate e-mail address with punctuation
  stripped, so the account-naming convention is disclosed too.
- `stephan-hochmuthpiconda-com` on the **career** (public recruitment) site — carries a **third-party
  supplier domain**, i.e. the listing exposes a contractor relationship as well as a valid account name.

### Reproduce with all three reachable forms

```bash
curl -s "https://b2b.mydays.de/wp-json/wp/v2/users?per_page=100"
curl -s "https://b2b.mydays.de/?rest_route=/wp/v2/users"
curl -s "https://b2b.mydays.de/index.php?rest_route=/wp/v2/users"
```
All three returned the same body with stable byte sizes across 3 runs per host. Fetching the variants is
what stops the triager answering "a path rule must have missed it".

### Boundary you must state

```bash
curl -s "https://b2b.mydays.de/wp-json/wp/v2/users/2?context=edit"
# -> 401 {"code":"rest_forbidden_context","message":"Sie sind leider nicht berechtigt,
#          diesen Benutzer zu bearbeiten."}
```
401 on `context=edit` = **no e-mail address, no password material**, only identity + login naming. The
single-record `view` read adds one Elementor preferences field (`elementor_introduction`) and the author
link. Put this in the report's "what I did NOT demonstrate" section — it is the sentence that keeps the
finding from being read as a data breach.

**Reported severity:** Low. **Value of the report is the 200/401 split across sibling installs** — that is
what turns "WordPress behaves like this" into "five of your sites are misconfigured relative to your other
four".

---

## 2. The embedded MCP surface — correct conclusion: LOCKED, no finding

`b2b.jochen-schweizer.de` (WordPress) registered an MCP server inside REST. Namespaces seen in
`/wp-json/`:

```
mcp, elementor-mcp-composer/v1.0.17, elementor-ai, elementor(+pro/one), custom-fonts,
bsf-custom-fonts, redirection, code-snippets, wpe/cache-plugin, wpe_sign_on_plugin,
safe-svg, yoast, mlo, wp-site-health, wp-block-editor, wp-abilities
```

Route tables (GET returning 200 is normal — it is only the index; never report it):

```
/wp-json/mcp                          -> /mcp  and  /mcp/mcp-adapter-default-server (POST,GET,DELETE)
/wp-json/elementor-mcp-composer/v1.0.17 -> …/mcp-settings, …/mcp-credentials
/wp-json/elementor-ai/v1              -> /permissions
```

Probe matrix — every handler refused:

| probe | result |
|---|---|
| `POST /wp-json/mcp/mcp-adapter-default-server` `initialize` (JSON-RPC 2024-11-05) | **401** `rest_forbidden` |
| `POST …?rest_route=/mcp/mcp-adapter-default-server` (same body) | **401** — the alternate path does not bypass |
| `GET /wp-json/elementor-mcp-composer/v1.0.17/mcp-settings` | **403** `invalid_nonce` "The request nonce is invalid." |
| `GET …/…/mcp-credentials` | **404** route absent |
| `GET /wp-json/elementor-ai/v1/permissions` | **401** `rest_forbidden` |
| `GET /wp-json/code-snippets/v1/snippets` (3 hosts) | 401 |
| `GET /wp-json/redirection/v1/redirect` | 401 |
| `GET /wp-json/wpforms/v1/forms` | 401 "This route is private." |
| `GET /wp-json/wordfence/v1/config` | 401 "Authorization header format is invalid." |
| `GET /wp/v2/users` on this host | **200** (the MD-C5 finding) |
| `GET /wp-json/wp/v2/settings`, `/menus`, `/templates` | 401 |

The JSON-RPC probe (single request — an unauthenticated `initialize` should be sent **once**, not fuzzed):

```bash
curl -s -X POST "https://b2b.jochen-schweizer.de/wp-json/mcp/mcp-adapter-default-server" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H 'Origin: https://b2b.jochen-schweizer.de' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05",
       "capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' -w "\n%{http_code}\n"
```

**Conclusion: report nothing.** What would have been reportable, and was not observed: `tools/list` or a
`tools/call` answering before `initialize`, a `tools/call` executing with no session, or
`mcp-credentials` returning a body.

---

## 3. WooCommerce on `sokabau.kundenportal.mydays.de`

| probe | result |
|---|---|
| `wc-admin/options` (no args, and `?options[]=` with proper `-G --data-urlencode`) | **500** `woocommerce_rest_cannot_view` "You must supply an array of options." for every variant |
| `wc/v3/system_status` no key / bogus consumer key | **401 identically** |
| `wc/v3/products`, `wc/v3/orders`, `wc/v2/products` | 401 `woocommerce_rest_cannot_view` |
| `wc/store/v1/products`, `/cart`, `/checkout` | 404 (Store API not mounted) |
| `wp/v2/users` | 401 |
| `contact-form-7/v1/contact-forms` | 403 `wpcf7_forbidden` |

The 500 is a **missing-argument artifact**: the handler validates its required `options[]` parameter
before it reaches the permission callback. Same message with a correctly-encoded valid array ⇒ no store
configuration is reachable ⇒ **not a finding**. Record it as a negative with the exact request shapes you
tried, so nobody later reads the 500 as an authz bypass.

---

## 4. Load discipline on this estate (Cloudflare)

Cloudflare began answering **429 "Just a moment…"** after roughly 40 `wp-json` requests across the b2b
host group. What worked, and what to repeat:

- Back off for the round, then resume with an **explicit per-script request budget** (the scripts here used
  6–40 requests), a 2.5–4 s gap, and an instant stop on any 429 or Cloudflare challenge.
- Do **not** rotate egress to get around it. The b2b hosts sit on one cluster
  (`141.193.213.20/.21`), so a different front-end hostname is still one target, and the operator's policy
  forbids noticeable load. The VPN was already on; adding a second exit node would have degraded the
  report's honesty for no coverage gain.
- The 429s cleared after ~30–60 minutes (a single liveness probe returned 200 in 0.44 s), so the recovery
  move is *wait*, not *escalate*.
- When the operator says *"rehat aja jgn spam"* (just rest, don't spam), that outranks finishing the
  enumeration: stop the scanners, kill leftover recon processes, verify one harmless liveness probe, and
  report. Resume when they ask.

---

## 5. Other estate facts worth keeping

- `/wp-json/` answered 200 on all four host groups; the **index is public by design** —
  `b2b.mydays.de` 377 routes, `b2b.jochen-schweizer.de` 375, `partner.jsmd-group.com` 211,
  `sokabau.kundenportal.mydays.de` 502 (WooCommerce). Route count is a plugin map, not a finding.
- `/xmlrpc.php` → **403** on all four (nginx front) — blocked, so no pingback/multicall.
- `?author=1` → **403** on the b2b hosts (a separate edge rule), so that door is closed here even though
  the REST door is open.
- `wp/v2/media` and `wp/v2/categories` → 200 with published content on the b2b pair. Normal WordPress
  behaviour for published posts; **not counted as a defect**, listed only for completeness.
- `kundenservice.mydays.de` returned 404 for `/wp-json/` — it is Freshdesk-powered, not WordPress.
- AT/CH brands (`www.mydays.at`, `www.mych` variants, `www.jochen-schweizer.at`) → 404/000 for
  `/wp-json/`; several CT-log hostnames (`emotion.*`, `affiliate.*`, `news.*`, `gewinnspiel.*`) do not
  resolve or do not answer. Do not assume the CT list is live inventory.
