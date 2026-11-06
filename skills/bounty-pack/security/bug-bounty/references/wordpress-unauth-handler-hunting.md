# WordPress / WooCommerce — unauthenticated-handler hunting

Recipe distilled from an authorized VDP audit of a WooCommerce store (WordPress 7.x, WooCommerce 11.x,
Hostinger hcdn + anti-bot, ~40 plugins). Ordered so the highest-yield steps run first.

## 0. Fingerprint the plugin stack (5 minutes, no auth)

- `readme.html` carries the core version; the homepage `<meta name="generator">` tags leak WooCommerce /
  Elementor / Site Kit versions.
- Enumerate plugins by probing `GET /wp-content/plugins/<slug>/readme.txt` (200 = installed) and by
  reading `?ver=` on enqueued assets. `Stable tag:` in the readme is the version.
- Download each plugin's exact build from wordpress.org for white-box review:
  `https://downloads.wordpress.org/plugin/<slug>.<version>.zip`. The **deployed readme is usually
  byte-identical to upstream** (`diff` it) — that is what lets a source finding stand as a live finding.

## 1. Enumerate the whole REST surface, then classify by namespace

```bash
curl -s https://TARGET/wp-json/ -o wpjson_root.json      # ~1k routes on a plugin-heavy store
```

Dump route -> methods and group by namespace. Work the *plugin* namespaces, not just `wp/v2`:

```python
import json
d = json.load(open("wpjson_root.json", encoding="utf-8"))
for k, v in d["routes"].items():
    print(",".join(sorted(v.get("methods", []))), k)
```

Namespaces seen on one store (each is an attack surface): `litespeed/v1|v3`, `ctxfeed/v8`,
`wc/pos/v1/catalog`, `chatway/v1/user`, `hostinger-reach/v1`, `hostinger-tools-plugin/v1`,
`elementor/v1` + `elementor-ai` + `elementor-mcp-composer`, `safe-svg/v1`, `mcp`, `wp-abilities/v1`,
`mc4wp/v1`, `jetpack/v4`, `yoast/v1`. Two cheap, high-signal passes:

- routes with an **empty namespace** (`""`) — ad-hoc `register_route()` calls, often the least
  reviewed (e.g. a bare `/poky` returning a constant);
- `grep -i "dashboard\|import\|export\|install\|ftp\|options\|debug"` over the route list — the
  low-permission-callback offenders cluster here.

## 2. The auth-classification trap: 400 fires BEFORE the permission check

A bare `POST` with `{}` to a protected route returns **`400 rest_missing_callback_param`**, not 401 —
WordPress validates required args (`has_valid_params()`) *before* it evaluates `permission_callback`.
So `400` does not mean unprotected; it tells you nothing about auth. To classify, send
**valid-format params**:

| response | meaning |
|---|---|
| `401 rest_forbidden` / `403` | protected — permission callback ran and refused |
| `400 rest_missing_callback_param` | unknown — supply format-valid params and retry |
| any other body / `500` | the handler executed -> investigate hard |

Run the sweep as a python-requests harness (not curl loops) so you can classify ~70 endpoints in one
pass and persist `label, method, status, class, body` to JSON.

A `500` on an otherwise-protected sibling is a real signal: on this audit `/ctxfeed/v8/dashboard/*`
returned 500 unauthenticated while `/ctxfeed/v8/feeds` returned 401 — the permission callback
reference differed from the base class (`permissionCheck` vs `permission_check`). Low severity, but it
is a genuine authorization defect and it fell out of the sweep for free.

## 3. White-box: grep every downloaded plugin for anonymous entry points

```bash
grep -rn "wp_ajax_nopriv\|admin_post_nopriv" --include=*.php .
grep -rn "permission_callback.*__return_true" --include=*.php .
# then read each hit: what does the handler DO, and what is the only gate?
```

Ranking the hits that came out of one store, best -> worst:

| handler | gate | verdict |
|---|---|---|
| `nopriv_poky_create_product` / `_load_products` | **secret token only**, no cap/nonce | real defect |
| `nopriv_abandoned-carts` (Hostinger Reach) | `check_ajax_referer` | weak |
| `nopriv_sync_chatway_data` | nonce + cookies; useful branch needs login | negligible |
| `nopriv_cartbounty_save` | nonce for customer data; SQL prepared | low |
| `litespeed wp_rest_echo` | `__return_true` **but** signature-validated | not a bug — read the body |

**Read the body before believing the permission flag.** `permission_callback => '__return_true'` is
normal for callback endpoints (QUIC.cloud, webhooks) that authenticate *inside* the handler; only
call it a finding once you have confirmed nothing else gates it.

## 4. Token-gated / shared-secret handlers — how to conclude honestly

When the handler's only gate is `if ( $_POST['tok'] === get_option('tok') )`:

- `===` is strict -> **no type-juggling bypass**. Test the variants anyway and record them as
  negatives (absent key, empty string, array, duplicate param, case-differing key, alt keys, JSON
  body, GET query, other content-types). All returned the handler's benign output — a clean negative.
- **There is usually no safe oracle.** If the only distinguishing handler is the *write* one, driving
  it to distinguish "gate passed" from "gate failed" creates a real object — so it must not be used
  as a probe. The read handler returning `[]` is ambiguous (gate failed **or** gate passed but nothing
  matched the filter).
- **Disambiguate cheaply**: the read handler filtered on "has a featured image". Fetch a known
  product and confirm it *does* have an image. If yes, `[]` means the gate genuinely failed, so the
  secret is set and non-empty. That converts a hand-wave into a stated fact.
- Timing on `===`: PHP `zend_string_equals` short-circuits on length then `memcmp`, so it is not
  constant-time in principle — but the delta is sub-microsecond against ~150-400 ms of WP bootstrap,
  so remote recovery is not practical. Do not spend the budget; report it as attempted-negative.
- **Do not attack the SaaS the token comes from** (e.g. the vendor's own app endpoint that issues the
  token). It is out of the target program's scope. Flag the design risk in the report instead.

## 5. The rest of the WP checklist that actually paid off

- **`/wp-json/wp/v2/users` open + `?search=@`** -> admin slug/e-mail enumeration (`/author/<slug>/`).
  Same class as **CVE-2023-5561**; nuclei flags it (`[CVE-2023-5561]`). Train/test enums typically
  land in the program's Low / "low-sensitivity info leak" tier.
- **XML-RPC enabled** -> `POST /xmlrpc.php` `system.listMethods` reveals `system.multicall` +
  `wp.getUsersBlogs` (many credential guesses per request) and `pingback.ping` (server-side fetch of
  an attacker URL — confirm with an OOB collaborator, which fires a resolver DNS callback).
- **`/wp-json/wp/v2/media` open** -> full upload inventory enumerable (default WP behaviour; Low/Info).
- Compare a plugin's token/option handling against the **deployed `readme.txt` vs upstream** to date
  the flaw: if `wp_ajax_nopriv_*` exists in every archived version, say "long-standing (>= X)" rather
  than implying a recent regression.
- Product reviews: check moderation by POSTing a benign marker comment and re-fetching — held for
  moderation closes the stored-XSS lead honestly.

## 6. CDN / WAF behaviour when you scan hard (and how to keep working)

- Uniform `403` with a **fixed small body** (exact size, e.g. 787 bytes) across *all* paths, while
  `robots.txt` still returns 200, means a **rate-limit block**, not a dead target or a per-file WAF
  rule. Stop, do not misread it as target-down.
- The block is **per egress IP and transient** (~5-15 min observed). It also distorts unrelated tools:
  `dalfox` and `sqlmap` threw `tls: internal error` / `couldn't establish SSL connection` while curl
  still worked — that is the block, not a TLS misconfig or a broken tool. Retest after the cool-down
  before drawing any conclusion about a client's TLS stack.
- Rotating egress (a VPN/WARP address vs the direct ISP address) restores service immediately, which
  also **proves the block was IP-scoped**. Keep the request rate low afterwards (nuclei `-rl 10-15
  -c 5`) or you re-trip it; and note that a long-running "is it back yet?" prober polling every 90 s
  can itself keep the block alive — go fully quiet instead.
- Port-scanning the CDN front is low value; scan the origin IP if exposed, and expect the WAF to 403
  direct-to-origin requests with a mismatched Host.

## 7. Reporting shape for a self-hosted VDP

Severity authority is **CWE + CVSS** (there is no Bugcrowd VRT to map into). One finding = one PDF =
one e-mail draft, body opens with an introduction, PoC PDF attached — see `bug-report-delivery`
("Self-hosted VDPs" + the send-gate rule).
