---
name: cms-security-testing
author: RESEARCHER_NAME
description: "Audit CMS targets: WordPress/Drupal patterns, SAP Hybris OCC, JSF/PrimeFaces."
metadata:
  hermes:
    tags: [security, bug-bounty, cms, craft-cms, wordpress, drupal, tomcat]
version: 1.0.0
---

# CMS Security Testing

## When to Use
- Target identified as Craft CMS, WordPress, Drupal, Joomla, or Tomcat during recon
- Phase 0C testing of CMS-powered web applications
- Need CMS-specific vulnerability patterns beyond generic web attacks

> **Phase 0C-Web2 skill** for CMS/framework-specific vulnerability patterns.
> Load when target uses a known CMS or framework. Complements `security-web-attacks`.

## ⛔ Load Rules
- Load during Phase 0C (testing) when CMS is identified
- Can run alongside `security-web-attacks` for general web attack playbooks
- CMS patterns are ADDITIONAL to standard web attack vectors

---

## CMS Identification

```bash
# Quick fingerprint
whatweb https://TARGET
# Check source for CMS markers
curl -s https://TARGET/ | grep -iE 'generator|powered.by|craft|wordpress|drupal|joomla|tomcat'
# Check common paths
for path in robots.txt sitemap.xml security.txt .env wp-config.php configuration.php; do
  curl -sI "https://TARGET/$path" | head -1
done
```

**CMS Markers:**
| CMS | Markers |
|-----|---------|
| Craft CMS | `window.Craft`, `/admin`, `CraftSessionId` cookie, `CRAFT_CSRF_TOKEN` |
| WordPress | `wp-content`, `wp-includes`, `wp-json`, `/wp-admin/` |
| Drupal | `Drupal.settings`, `sites/default/files`, `X-Generator: Drupal` |
| Joomla | `Joomla!`, `/administrator/`, `com_content` |
| Tomcat | `Apache Tomcat`, `/manager/html`, `JSESSIONID` |

---

## Craft CMS Patterns

### `window.Craft` Configuration Disclosure
**Severity:** Low/Informational (can chain to Medium with XSS)

Every HTML response includes `window.Craft` JS object leaking:
- `csrfTokenName` + `csrfTokenValue` (session-bound)
- `systemUid` (stable installation ID)
- `baseSiteUrl` / `baseUrl` (may reveal secondary domains)
- `baseCpUrl` / `actionUrl` (admin panel URLs)
- `resourceBaseUrl`, `timezone`, `language`, `cookie` config
- `useEmailAsUsername`, `minPasswordLength`, `maxPasswordLength`

**PoC:**
```bash
curl -s https://TARGET/ | grep -o '"csrfTokenName":"[^"]*","csrfTokenValue":"[^"]*"'
curl -s https://TARGET/admin/login | grep -o '"systemUid":"[^"]*"'
curl -s https://TARGET/ | grep -o '"baseSiteUrl":"[^"]*"'
```

**Chaining:**
- XSS + leaked CSRF = CSRF bypass
- Leaked `baseSiteUrl` = secondary domain discovery
- Leaked `systemUid` = instance fingerprinting

**Fix:** Suppress `window.Craft` on non-admin pages.

### Craft CMS Admin Panel
- Default: `/admin` → `/admin/login`
- Actions: `/index.php?p=actions/`
- Check unauthenticated action access
- Test default credentials

### Craft CMS + Yii Framework
- Craft uses Yii internally
- Check for Yii debug toolbar exposure
- Yii-specific vulnerabilities apply

---

## WordPress Patterns

### Recon
```bash
# User enumeration
curl -s https://TARGET/?author=1 | grep -o '/author/[^/"]*'
curl -s https://TARGET/wp-json/wp/v2/users | python3 -m json.tool
# Version disclosure
curl -s https://TARGET/ | grep -o 'content="WordPress [^"]*"'
# Plugin/theme enumeration
curl -s https://TARGET/ | grep -o 'wp-content/plugins/[^/"]*'
curl -s https://TARGET/ | grep -o 'wp-content/themes/[^/"]*'
```

### REST surface = free plugin map + the authz-inconsistency hunt
`/wp-json/` is usually reachable **unauthenticated** and enumerates every registered
namespace → the plugin inventory, without touching readme files:

```bash
curl -s https://TARGET/wp-json/ | python3 -c "import sys,json;d=json.load(sys.stdin);\
print(len(d['namespaces']),'namespaces');[print(' ',n) for n in d['namespaces']]"
# 24 namespaces / 472 routes is normal for a marketing site with a page builder
```

Then GET each **non-core** namespace and its sub-routes unauthenticated. Plugin routes are
frequently protected *inconsistently* — that gap IS the finding class:

```
[401] /wp-json/ithemes-security/v1/logs
[401] /wp-json/ithemes-security/v1/settings
[401] /wp-json/ithemes-security/v1/modules
[200] /wp-json/ithemes-security/v1/bans   <== leaks the banned/locked-out IP list
```
(2026-09, Rapyd `www.rapyd.net` + `join.rapyd.net`, same WP install — P4 info disclosure:
third-party IPs + timestamps + `created_by:brute_force`. The 401 siblings are what makes the
claim credible: it is a misconfiguration, not "the plugin is public".)

Rules for this class:
- **Only GET.** These routes have write siblings (`…/settings`, `…/import/run`,
  `…/redirect` creation, `…/duplicate-post`). Read the route list from `/wp-json/` and stop
  at reads — a config write on a live marketing site is not a bug-hunt action.
- Report the *specific* leaked fields and say what the sibling routes did, so the triager can
  see the inconsistency. Expect P4/P5; many programs treat IP disclosure as informational.
- A plugin's namespace appearing in the index does **not** mean its routes are unauthenticated
  — test each, and check `context=edit` separately.

`scripts/wp_rest_probe.py <base-url>` automates the whole pass: index → namespaces →
non-core route GETs → author enum → readme versions → control checks (read-only, stdlib only).

### An OPEN `/wp-json/wp/v2/users` is itself the reportable finding — and the sibling 401s are your evidence
The section below covers the *locked* case. The **open** case is a different and more valuable finding:
the route returns login slugs + display names to an unauthenticated caller, which is the first half of a
credential attack. Observed 2026-10-13 (mydays/JSMG): **5 of 8** WordPress installs answered 200 —
`b2b.mydays.de` (4 accounts), `b2b.jochen-schweizer.de` (4), `career.jsmd-group.com` (5),
`presse.mydays.de` (2), `presse.jochen-schweizer.de` (3) — while `partner.jsmd-group.com`,
`sokabau.kundenportal.mydays.de`, `magazin.mydays.de` and `magazin.jochen-schweizer.de` answered
`401 {"code":"rest_user_cannot_view","message":"Sorry, you are not allowed to list users."}`.

What makes it a configuration slip and not "the CMS is designed this way" is **your own sibling sites**.
Always fetch the same route on every host of the same organisation and put the 200/401 split in the
report — that contrast is the finding's credibility:

```bash
for h in b2b.example.de career.example.com presse.example.de partner.example.com; do
  printf "%-40s " "$h"
  curl -s -o /tmp/u.json -w "%{http_code} " "https://$h/wp-json/wp/v2/users?per_page=100"
  grep -c '"slug"' /tmp/u.json
done
```
Request the same route through **all three reachable forms** — `/wp-json/wp/v2/users`,
`/?rest_route=/wp/v2/users` and `/index.php?rest_route=/wp/v2/users` — and report that all three return
the body, so it cannot be dismissed as a path rule that was missed. (On this estate the `?rest_route=`
form did *not* unlock the MCP or snippet routes — those stayed 401/403, which is itself the control that
proves the MCP permission layer is real.)

Boundary check to run and state, so the report stops where the evidence stops:

```bash
curl -s "https://b2b.example.de/wp-json/wp/v2/users/2?context=edit"   # -> 401 rest_forbidden_context
```
401 there means **no email address or password material** is exposed — only identity and login naming.
Say that explicitly; it pre-empts the triager's "so what" and keeps the claim honest.

What to look for in the leaked slugs, because it is what raises the impact above "informational":
a slug that is a corporate address with punctuation removed (`katja-hornungjsmd-group-com`), and — seen
on the **career** site — a slug carrying a **third-party supplier domain**
(`stephan-hochmuthpiconda-com`), which discloses a contractor relationship on a public recruitment
site.

### The embedded MCP surface is now part of a modern WordPress audit — and it is usually locked
Page-builder stacks now register an **MCP (Model Context Protocol) server inside WordPress REST**. Seen
2026-10-13 on `b2b.jochen-schweizer.de`: the `/wp-json/` namespace list contained `mcp`,
`elementor-mcp-composer/v1.0.17` and `elementor-ai`. Ask each of them for its route table, then probe
the routes they name:

```
[200] /wp-json/mcp                                -> {"namespace":"mcp","routes":{
                                                        "/mcp/mcp-adapter-default-server": POST,GET,DELETE …}}
[200] /wp-json/elementor-mcp-composer/v1.0.17     -> … "/mcp-settings", "/mcp-credentials"
[200] /wp-json/elementor-ai/v1                    -> … "/permissions"
```

**The route-table GET returning 200 is normal** (it is the index) — do not report it. Probe the handlers:

```bash
curl -s -X POST "https://HOST/wp-json/mcp/mcp-adapter-default-server" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05",
       "capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' -w "\n%{http_code}\n"
```

Observed result on this estate: `initialize` → **401 `rest_forbidden`**,
`elementor-mcp-composer/…/mcp-settings` → **403 `invalid_nonce` ("The request nonce is invalid.")**,
`mcp-credentials` → 404 (route absent), `elementor-ai/v1/permissions` → 401. And the `?rest_route=` form
did **not** change any of those. That is a correctly configured MCP surface across all three routes —
report nothing, and record it as a negative with the status codes.

What to report, and only if you see it: `tools/list` or a `tools/call` answering **before**
`initialize` (MCP servers must reject anything pre-initialize), a `tools/call` executing with no
session, or `mcp-credentials` returning anything. The pairing that makes such a claim credible is the
401/403 siblings above: they prove the app *can* refuse, so a 200 is a defect rather than a design.

Two load rules for this surface: an unauthenticated `initialize` is **1 request** — send it once, do not
enumerate tool names or fuzz it; and if the edge starts answering 429 (Cloudflare "Just a moment…"), stop
for the round and say so, rather than rotating egress, because VPN is already on and a second exit node
degrades the report's honesty rather than helping it.

### Author enumeration survives when the REST users route is locked
`/wp-json/wp/v2/users` → 401 **and** `/xmlrpc.php` → 403 are the controls working. Enumeration
usually still works through two other doors — check them:
```bash
curl -sL "https://TARGET/?author=1" | grep -o "/author/[a-z0-9._-]*/"   # 301 -> /author/<nicename>/
curl -s  "https://TARGET/author-sitemap.xml" | grep -o "<loc>[^<]*"     # Yoast author list
```
Iterate `?author=1..6`: hits on 1/4/5 and 404 on the rest is the normal pattern (IDs are
sparse once users are deleted). Username leakage alone is usually informational.

### WooCommerce admin routes: a 500 before the permission check is a missing-argument artifact, NOT a bypass
`/wp-json/wc-admin/options` repays a careful second look, because the reflex is to file the 500 as an
authz bypass ("it got past the permission check!"). Chase it properly before writing anything up:

```bash
curl -s -G --data-urlencode "options[]=blogname"              "https://HOST/wp-json/wc-admin/options"
curl -s -G --data-urlencode "options[]=woocommerce_currency"  "https://HOST/wp-json/wc-admin/options"
curl -s -G --data-urlencode "options[]=woocommerce_stripe_settings" "https://HOST/wp-json/wc-admin/options"
```
Note `-G` + `--data-urlencode`: a hand-built `?options[]=` query string does **not** survive as an array.

Observed 2026-10-13: valid, correctly-encoded arrays for blogname / currency / store address / Stripe /
PayPal settings **all** returned
`500 {"code":"woocommerce_rest_cannot_view","message":"You must supply an array of options."}` — the same
message as no arguments at all. That is the handler validating its own required parameter before it
reaches the permission callback. **No store configuration is disclosed, so there is no finding.** Record
it as a negative with the request shapes you tried; do not report the status code.

The matching control worth running while you are there, because `system_status` is the classic
gateway-key leaker:

```bash
curl -s -o /dev/null -w "%{http_code}\n" "https://HOST/wp-json/wc/v3/system_status"                       # 401
curl -s -o /dev/null -w "%{http_code}\n" -u "ck_bogus…:cs_bogus…" "https://HOST/wp-json/wc/v3/system_status" # 401
```
Identical 401 with no key and with a bogus key = the error surface leaks nothing and the permission
check is real. `wc/v3/products`, `wc/v3/orders` → 401 `woocommerce_rest_cannot_view` is the same story.

### Version numbers are fingerprints, not vulnerabilities
`/wp-content/plugins/<slug>/readme.txt` → `Stable tag:` gives versions, and
`<meta name="generator" content="WordPress X.Y">` gives core. **Do not claim a CVE from a
version string.** On this engagement nuclei's WP templates reported
`[wordpress-redirection:detected_version] 5.8.0 [last_version="5.5.2"]` — the deployed
version was *newer* than the scanner's known-latest, i.e. nothing to claim, and a scanner's
"last_version" is stale by design. Verify an advisory's affected range before writing it up,
or report the version disclosure itself (usually informational / often OOS).

### `admin-ajax.php` action discovery — the literal `0` is your oracle
When the visible surface is thin but a custom plugin is active, `/wp-admin/admin-ajax.php` is often
the whole application. It answers with a literal **`0`** for an unregistered `action`, which gives a
free, unambiguous registered/unregistered oracle — no guessing from response length:

```bash
# unregistered
curl -s -X POST https://TARGET/wp-admin/admin-ajax.php -d 'action=nope_not_here'   # -> 0
# registered, needs params
curl -s -X POST https://TARGET/wp-admin/admin-ajax.php -d 'action=real_action'     # -> JSON / HTML
```

Sweep `action=<prefix>_<noun>` and `<prefix><verb>_<noun>` candidates, then read the plugin's own
inline JS for the authoritative list — every `data.append('action', …)` / `'action' : '…'` in the
page is a confirmed handler with its exact parameter contract:

```bash
curl -s https://TARGET/some-page/ | grep -oE "action'?\"?[:=] ?'[a-z0-9_]+'" | sort -u
```

Contract details that matter:
- **CSRF token single-use.** Tokens minted by a `*create_csrf_token*` action are frequently valid
  for exactly one use; replaying one returns `{"result":false}` / "invalid access" and looks like a
  permission failure. Fetch a fresh token **per call** before concluding anything.
- **GET vs POST split.** Some handlers respond only to `GET`, others only to `POST`, and several
  accept both with different behaviour — test the pair.
- **Encoding kills curl one-liners.** A space in a value makes curl emit a malformed request
  (`HTTP 000`, empty output). Use `urllib.parse.urlencode` (or `curl -G --data-urlencode`) rather
  than string-concatenating a query string; a silent `000` reads exactly like a blocked endpoint.
- A handler returning "no permission" while authenticated is an authorisation control working —
  record it, don't treat it as a bypass.

Same discovery style as the REST index pass in `scripts/wp_rest_probe.py`, applied to `admin-ajax`
instead of `/wp-json/`.

### Common Vulnerabilities
- `/xmlrpc.php` — brute-force, SSRF, DDoS amplification (check it is even reachable: 403 = blocked)
- `/wp-login.php` — brute-force target (never brute-force on a live program)
- `/wp-admin/` — admin panel
- `/wp-content/debug.log` — debug log disclosure
- `/wp-content/uploads/` — file listing
- Plugin-specific CVEs (check version from source)

### Exploit Tools
- `wpscanteam/wpscan` — WordPress scanner
- `rastating/wordpress-exploit-framework` — WP exploit framework

---

## Drupal Patterns

### Recon
```bash
# Version detection
curl -s https://TARGET/CHANGELOG.txt | head -5
curl -s https://TARGET/core/CHANGELOG.txt | head -5
# User enumeration
curl -s https://TARGET/user/1 | grep -i 'title\|name\|error'
```

### Common Vulnerabilities
- Drupalgeddon (CVE-2018-7600) — form API injection
- `/admin/content` — content management
- `/CHANGELOG.txt` — version disclosure

---

## Joomla Patterns

### Recon
```bash
# Version detection
curl -s https://TARGET/ | grep -o 'Joomla! [^"]*'
# Admin panel
curl -sI https://TARGET/administrator/
# Config backup
curl -sI https://TARGET/configuration.php~
```

### Common Vulnerabilities
- `/administrator/` — admin panel
- `/configuration.php~` — backup config file

---

## Tomcat Patterns

### Recon
```bash
# Version detection (often in 404 pages)
curl -s https://TARGET/ | grep -o 'Apache Tomcat/[0-9.]*'
# Manager app
curl -sI https://TARGET/manager/html
# Default credentials
curl -u admin:admin https://TARGET/manager/html
curl -u tomcat:tomcat https://TARGET/manager/html
```

### Common Vulnerabilities
- `/manager/html` — WAR deployment (default creds)
- Version-specific CVEs
- AJP ghostcat (CVE-2020-1938) if AJP port exposed

---

## Cross-References
- General web attacks → `security-web-attacks` (Phase 0C)
- Recon methodology → `security-recon` (Phase 0B)
- Report → `bug-report-delivery` (Phase 0F)

## References
- `references/wp-open-user-enum-and-mcp.md` — the 2026-10-13 JSMG case in full: the five open
  `wp/v2/users` hosts with their account lists, the four sibling installs that answer 401 (the
  configuration-slip proof), the `context=edit` boundary, the embedded-MCP probe matrix
  (`mcp-adapter-default-server` 401 / `mcp-settings` 403 nonce / `mcp-credentials` 404 /
  `elementor-ai/permissions` 401), the WooCommerce 500 artifact, the 429/Cloudflare load discipline,
  and every negative with its status code so the next session does not re-walk it.
- `references/cms-vuln-patterns.md` — detailed CMS vulnerability patterns with PoC
- `scripts/wp_rest_probe.py` — read-only WordPress REST-surface probe: `/wp-json/` plugin map →
  non-core route GETs (authz-inconsistency hunt) → author enum (`?author=N`, Yoast sitemap) →
  readme version fingerprints → control checks. Run: `python wp_rest_probe.py https://TARGET`

## Absorbed playbooks (complete sub-packages under `references/`)
Platform-specific drill-downs for CMS/commerce targets, each a full package:

- `references/hunt-hybris/PLAYBOOK.md` — SAP Commerce (Hybris): OCC v2 REST surface, anonymous vs
  customer tokens, CMS component and preview endpoints, and the config/credential leaks that pay.
- `references/hunt-jsf-primefaces/PLAYBOOK.md` — JavaServer Faces + PrimeFaces appliances:
  ViewState handling/deserialization, `javax.faces.ViewState` replay, PrimeFaces EL/RCE gadget
  paths, and the file-upload/servlet surface (`references/`, `scripts/` included).
