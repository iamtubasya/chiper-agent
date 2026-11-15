# WordPress Admin Panel Attack Surface

## Pattern: Non-Cloudflare WordPress Admin

When WordPress site has admin panel accessible WITHOUT Cloudflare/WAF:

### 1. Information Disclosure
```bash
# Version leak
curl -s "https://TARGET/" | grep -oE 'content="WordPress [0-9.]+"'

# Plugin enumeration via REST API
curl -s "https://TARGET/wp-json/" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for n in d.get('namespaces',[]):
    print(f'  {n}')
"

# jQuery version
curl -s "https://TARGET/wp-login.php" | grep -oE 'jQuery [0-9.]+' | head -1
```

### 2. Login Form Analysis
```bash
# Get CSRF token
CSRF=$(curl -s "https://TARGET/wp-login.php" | grep -o 'name="nonce" value="[^"]*"' | head -1)

# Test login error messages (username enumeration)
curl -s -X POST "https://TARGET/wp-login.php" \
  -d "log=admin&pwd=wrong&wp-submit=Log+In" \
  | grep -oE '(incorrect|not registered|invalid|error)[^<]*'
```

### 3. Hidden Form Fields
Check for exploitable hidden fields in login/admin forms:
- `server` field → SSRF potential
- `redirect_to` → Open redirect potential
- `testcookie` → Cookie manipulation

### 4. File Manager Plugin
```bash
# Check for file manager plugins
curl -s "https://TARGET/wp-json/" | grep -o 'file-manager[^"]*'

# Common file manager endpoints
for path in /wp-content/plugins/wp-file-manager/ /wp-content/plugins/advanced-file-manager/; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://TARGET${path}")
  echo "[${code}] ${path}"
done
```

### 5. XML-RPC
```bash
# Check if enabled
curl -s "https://TARGET/xmlrpc.php" | head -5

# Test methods
curl -s -X POST "https://TARGET/xmlrpc.php" \
  -H "Content-Type: text/xml" \
  -d '<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName></methodCall>'
```

### 6. Debug/Info Endpoints
```bash
for f in /wp-content/debug.log /readme.html /license.txt /wp-config.php.bak /wp-content/db.php; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://TARGET${f}")
  [ "$code" != "404" ] && echo "[${code}] ${f}"
done
```

## Severity Guide

| Finding | Severity | Notes |
|---------|----------|-------|
| Admin panel exposed (no auth bypass) | Low/Info | By-design if admin knows |
| Username enumeration via login | Low | P4 |
| Version disclosure | Info | P5 |
| File manager plugin accessible | Medium | If allows upload |
| XML-RPC enabled | Low/Medium | If brute force possible |
| Debug log exposed | Medium | May contain sensitive data |
| wp-config.php.bak accessible | Critical | May contain DB creds |
| SSRF via hidden field | High/Critical | If server processes URL |
| CSP unsafe-eval | Medium | XSS→RCE chain needed |

## Proven Findings (Atmail, August 2026)
- admin.atmailcloud.com: nginx, no Cloudflare, CSP unsafe-eval, hidden server field, jQuery 3.5.0
- www.atmail.com: WordPress with Cloudflare + Wordfence + Shield (hardened)
- webmail.junara.com: SPA webmail, previous XSS worm (CVE-2017-11617)

---

# REST surface as the plugin map (highest-yield WP recon step)

On a marketing/docs WordPress site (in-scope Tier1 for many fintech programs) `/wp-json/` is usually
public and is the single best recon call — it returns the **full route table**, not just namespaces:

```bash
curl -s -H 'X-Bugcrowd: Bugcrowd-<alias>' https://TARGET/wp-json/ -o wp_json.json   # 472 routes / 24 namespaces observed
```

Mine it: ignore core namespaces (`wp/v2`, `wp-site-health`, `oembed`, `batch`, `wp-block-*`) and treat
every remaining namespace as a plugin fingerprint **plus** a probe list — e.g.
`ithemes-security/rpc`, `ithemes-security/v1`, `wpml/v1`, `ultimate-vc/v1`, `coauthors/v1`,
`redirection/v1`, `userway/v1`, `yoast/v1`, `wp-all-import/v1`, `duplicate-post/v1`,
`objectcache/v1`, `epic/v2`, `regenerate-thumbnails/v1`, `otgs/installer/v1`, `nps-survey/v1`.

Why this beats a plugin-name grep: the route table exposes argument names and the per-route
permission surface, so you can pick the few routes worth probing instead of fuzzing blind.

## The finding class: one plugin route that forgot `permission_callback`

Probe the plugin routes unauthenticated (GET only) and hunt for the **differential** — one route
returning 200 with data while its siblings return 401. The differential is the evidence a triager
accepts; "the plugin's REST API is exposed" is not.

```bash
for r in /wp-json/ithemes-security/v1/bans /wp-json/ithemes-security/v1/logs \
         /wp-json/ithemes-security/v1/settings /wp-json/redirection/v1/redirect \
         /wp-json/objectcache/v1/status /wp-json/wp/v2/users /wp-json/wp/v2/plugins ; do
  printf '%-58s ' "$r"; curl -s -o r.json -w '%{http_code} %{size_download}\n' \
    -H 'X-Bugcrowd: Bugcrowd-<alias>' "https://TARGET$r"; head -c 120 r.json; echo
done
```

Observed on a production fintech marketing site:

| Route | Result |
|---|---|
| `/wp-json/ithemes-security/v1/bans` | **200 with no auth** → ban records: `label` = the banned **IP** (v4+v6), `created_at`, `created_by {id:'brute_force', type:'lockout_module'}` |
| same namespace `logs`, `settings`, `modules`, `actors`, `site-scanner/scans`, `dashboard-available-cards`, `rpc/lockout-stats/top-blocked-ips` | 401 |
| `/wp-json/wp/v2/users` · `/wp/v2/plugins` · `/wp/v2/settings` | 401 (good) |
| `/xmlrpc.php` | 403 (good) |
| `/wp-json/ithemes-security/v1/geolocate/127.0.0.1` · `/169.254.169.254` | 401 — re-probe here for SSRF whenever it answers 200 |

- **Check sibling hosts for the same install.** A second in-scope host of the same brand served a
  byte-identical `/wp-json/` and the same exposed `/bans` → the finding covers two hosts; stating that
  also tells the triager whether it is one multisite or two installs.
- Severity, honestly: **P4/informational**. Leaked third-party IPs + security-posture data is
  GDPR-flavoured personal data, so Low is defensible, but expect "informational". Pair the leak with the
  401-sibling differential and let the triager rate it — never inflate an IP list to Medium.
- `?rest_route=/wp/v2/users` is an equivalent spelling of any REST path — test both when a rule looks
  like it matches on the URL only.

## Version fingerprinting + CVE discipline

Two sources and one hard rule:

1. per-plugin `readme.txt`: `curl -s https://TARGET/wp-content/plugins/<dir>/readme.txt | grep -E 'Stable tag|Version'`
2. `nuclei -tags wordpress,wp-plugin,wp-theme -rl 5`: its `wordpress-<slug>:detected_version` templates
   print `["<installed>"] [last_version="<known>"]` and name plugins you would not have guessed.

**A version string is not a vulnerability.** If `detected > last_version` (site runs newer than the
newest version the templates know) there is nothing to claim at all. Even when a version looks old, do
not write "vulnerable to CVE-XXXX-YYYY" unless you looked the CVE up and checked the affected range.
In one pass every detected plugin was *ahead* of `last_version` → zero CVE claims, which was the
correct output.

## User enumeration (two cheap paths)

```bash
# 1) author id → nicename (301 chain: follow Location, do not read the body)
curl -s -D - -o /dev/null "https://TARGET/?author=1" | grep -i '^location:'   # → /blog/author/<nicename>/
# 2) Yoast author sitemap (works even when /?author= is blocked)
curl -s "https://TARGET/author-sitemap.xml" | grep -oE '<loc>[^<]+' | head
```

nuclei reports the second as `wp-yoast-user-enumeration`. Username disclosure is P4/P5 and often OOS —
carry it as a secondary observation, never as the headline finding.

## Honest negatives worth repeating (so the next session skips them)

- `ffuf` with a curated sensitive-file wordlist across 10 hosts → **0 hits**; `.env`, `.git/config`,
  `wp-config.php` all 403 on hardened hosts. A 200 whose body is an **SPA shell** (775 bytes of
  `<!DOCTYPE html>`) means "route not found", not an exposed file — always read the body.
- `interactsh` OOB (blind XXE in a SAML ACS, JNDI `${jndi:ldap://…}` in User-Agent / X-Forwarded-For /
  X-Api-Version, SSRF via `?url=` / `?callback=` / `?redirect_url=` on app hosts) → zero callbacks.
- Request smuggling (CL.TE, TE.CL, TE-obfuscated, double-TE, duplicate-CL) and cache-poisoning headers
  (`X-Forwarded-Host/Scheme`, `X-Host`, `X-Original-URL`) → no desync, no reflection. One host answered
  200 to the ambiguous CL.TE/TE.CL pair where siblings answered 400 — a one-line hardening note, but
  with no follow-on response it is **not** smuggling.
- `dalfox` on a reflected `?s=` search parameter → no XSS. `kxss` reporting a parameter as
  "unfiltered" (`[$ | ( ) \` : ; { }]`) only means those characters are not stripped; WordPress still
  escapes the term in-context. Reflection != XSS; let dalfox decide.

## REST auth-classification: the 400-before-permission trap (read this before calling anything "ALLOW?")

WordPress core validates **required args before it ever calls `permission_callback`**
(`WP_REST_Server::respond_to_request()` → `has_valid_params()` / `sanitize_params()` run first), so an
empty-body probe is ambiguous:

| Response | Meaning |
|---|---|
| `401 rest_forbidden` / `woocommerce_rest_cannot_*` | protected (permission callback denied) |
| `400 rest_missing_callback_param` | **inconclusive** — validation ran *before* the permission check. NOT proof the route is unprotected. |
| `200` / `500` / anything else | the callback (or its permission fn) actually executed |

To decide, **re-send with valid-format required params**, e.g. `?url=http://127.0.0.1/` for a
`file_size` route, `{"uri":"..."}` for an MCP-proxy route, `{"host":..,"username":..,"password":..,"path":..}`
for an ftp-test route. Returns 401 → protected; processes → real lead. On the cardoma run ~10 endpoints
that first looked like `ALLOW?` (400) all collapsed to 401 once real params were sent.

## The 500-not-401 differential (weaker class — report honestly)

A plugin route returning **500 (WP "critical error" fatal)** to an anonymous caller while sibling routes
return 401 means the authorization decision is **not enforced as intended** on that route. Severity: **Low**
— unauthenticated fatal = error-based info leak / minor DoS, no data returned. Do not inflate it.

Root-causing without a stack trace: download the exact deployed build and read the registration.
CTX Feed 8.0.26 registered dashboard routes with `'permission_callback' => array($this,'permissionCheck')`
while the abstract base defines `permission_check()`; PHP method names are case-insensitive, so casing
alone should NOT change behaviour — treat a casing mismatch as a **lead, not a proven cause** (the deployed
build may differ from the wordpress.org tarball). Report the observable differential, not the guess.

## White-box confirmation: download the exact plugin build

Faster and more certain than black-box probing. `downloads.wordpress.org/plugin/<slug>.<ver>.zip` serves
any published version (bare `<slug>.zip` = latest). Confirm the deployed slug+version first via
`/wp-content/plugins/<slug>/readme.txt` (200 = present). Then:

```bash
grep -rn "register_rest_route"  . --include=*.php     # every route + its permission_callback
grep -rn "wp_ajax_nopriv"       . --include=*.php     # <- anonymous handlers: the money grep
grep -rn "wp_ajax_"             . --include=*.php     # logged-in handlers (usually fine)
```

## The finding class: `wp_ajax_nopriv_*` handlers (unauthenticated plugin endpoints)

Any plugin with `add_action('wp_ajax_nopriv_<x>', ...)` exposes `<x>` to anonymous callers. The high-yield
shape is a handler performing a privileged action gated **only** by a static secret compared with `===`
(non-constant-time) and **no** `current_user_can()` / nonce:

```php
add_action('wp_ajax_nopriv_poky_create_product', 'poky_create_product');
function poky_create_product() {
    if ($_POST['pokyToken'] === get_option('poky_token')) {  // only gate; no capability, no nonce
        $p = json_decode(stripslashes($_POST['product']), true);
        $PokyImport->insert_product($p);                     // -> media_sideload_image() = SSRF + media write
    }
}
```

PoC that does not mutate state or trip the WAF:
- **positive control:** `POST /wp-admin/admin-ajax.php` with `action=zzz` → `400 "0"`.
- **handler ran anonymously:** `action=<real>` (any/absent token) → `200 []` (or empty) — the body is the
  handler's own output, not a generic response.
- Read-only actions only. Do **NOT** drive a create/write action unless the gate is actually bypassed. If the
  secret is unknown the honest finding is "unauthenticated entry point, no capability check" → **Medium at
  most**; never claim RCE/ATO off it.
- Corroborate with third-party static analysis (`wp-safety.org/plugins/<slug>`, `amibeingpwned.com`) — they
  flag the same "unprotected AJAX handlers" and add weight to the report.

## Case study — cardoma.shop (WooCommerce VDP, Oct 2026)

WP 7.1.2 / Woo 11.1.2 / Woodmart 8.3.8 / Hostinger hcdn + anti-bot. 1,105 routes / 38 namespaces.
- **F1 (Medium)** POKY Product Importer v2.2.0 — `nopriv_poky_create_product` + `nopriv_poky_load_products`,
  token-only gate; `insert_product → upload_media → media_sideload_image()` = SSRF. Token not recovered → no
  write performed.
- **F2 (Low)** CTX Feed 8.0.26 dashboard routes 500-not-401 (see above).
- **F3 (Low-Med)** xmlrpc enabled — `system.multicall` brute amplification + `pingback.ping` SSRF (OOB-confirmed).
- **F4 (Low)** `/wp/v2/users` → admin slug → inferred email. **F6 (Info)** `/wp/v2/media` fully enumerable.
- Clean negatives: `wc/v3`, `wc-admin`, `elementor*`, `yoast`, `wc_stripe`, `jetpack`, `google-site-kit`,
  `safe-svg/v1/svg/<id>`, `litespeed`, `wp-abilities`, `mcp`, hostinger `regenerate-bypass-code` → all 401/403;
  sqlmap `?s=` not injectable; dalfox 0 findings; product reviews moderated (no stored XSS); `.env`/`.git`/
  backups → 403 (WAF).
- The two reportable items came from the **nopriv grep** + **white-box download**, not black-box fuzzing.
  Download the plugins first.

## Token-gate deepdive — handler gated ONLY by a static secret compared with `===`

When the sole gate is `$_POST['x'] === get_option('secret')`, the bypass space is finite — run the whole
checklist once, then stop. A **strict `===` defeats every coercion / type-juggling trick**:

- key absent · empty string · array (`x[]=`) · duplicate param (PHP keeps the last) · case-swapped key
  (`POKYTOKEN`) · alternate key names (`token`,`key`) · `0e0` magic-hash · literal `"false"`/`"null"`/`"0"`
  · the value leaked by any marker route (`/wp-json/poky` returned `813` — not the token)
- JSON body (`application/json` → PHP leaves `$_POST` empty → "no route", not a bypass) · GET query (gate
  reads `$_POST` only) · `Content-Type: text/plain` (body unparsed)
- Result on the cardoma run: all 14 variants → identical failure output ⇒ no bypass possible against `===`.

Then answer *"is the secret even set?"* — the read handler returning empty is ambiguous:

- **Empty-secret hypothesis:** empty output means either the gate failed **or** the gate passed and the
  data set is empty. Resolve with an independent read of the same data (WooCommerce Store API product →
  does a featured image exist?). Data exists + handler still empty ⇒ secret is set and non-empty.
- **No safe write-path oracle:** a create handler that runs `$product->save()` / an INSERT the instant the
  gate passes cannot be used as a probe. PHP 8 `foreach(null)` is a **Warning** (loop skipped), *not* a
  fatal, so a malformed payload will still reach the write — you cannot distinguish gate-passed vs
  gate-failed without mutating state. Do **not** probe it.
- **Timing side-channel on `===` is not practical remotely:** `zend_string_equals` short-circuits on
  length then `memcmp`s, but the delta is sub-µs and drowned by WP bootstrap + admin-ajax (~150–400 ms).
  Record as attempted-negative; don't spend a session on it.
- **Date the flaw** by diffing consecutive releases (`downloads.wordpress.org/plugin/<slug>.<ver>.zip`).
  The `nopriv` gate was byte-identical in POKY 2.0.0/2.1.0/2.2.0 ⇒ long-standing, not a one-release
  regression — state that in the report.

## Tool pitfalls hit on WP engagements

- **nuclei `-l` = list of TARGET URLs; `-t` = templates.** Passing a template list to `-l` makes nuclei
  treat each template path as a host (`Skipped .:80 … no address found for host`) and scan nothing. For a
  template set use `-t <dir>` (e.g. `nuclei -u URL -t ./http -tags wordpress,woocommerce -rl 10`).
- **`grep -rn` over extracted plugin trees times out** on the big ones (hostinger-reach ~12 MB,
  woocommerce-pos ~8 MB). Use ripgrep (`search_files`) — same hits, no hang.
- **`ffuf` with a wordlist that has `#` comment / blank lines**: every comment line becomes FUZZ →
  request to `TARGET/` → `200` homepage → floods results with false positives. Pre-clean:
  `grep -vE '^\s*(#|$)' wl.txt > clean.txt`.
- **CVE-2023-5561** (`/wp-json/wp/v2/users?search=@`) verified live on WP 7.1.2 → returns the admin user.
  The WAF may block the `%40`/`@` pattern specifically while plain `/wp/v2/users` still reads — try both.

## CDN / anti-bot rate-limit while scanning (hcdn "mx-page", Hostinger)

Bursts (nuclei 1k+ requests, ffuf, sqlmap) trip an **IP-attributed** block: `/wp-json/*` and `/wp-admin/*`
start returning `403` (a JS-challenge / "Access Denied" page, `Server: hcdn`, body has `id="mx-page"`),
while `/` and `/robots.txt` still `200`. So *"some paths 403, root 200"* = rate-limit, not app behaviour.

- The same block surfaces as a **TLS alert** to non-browser clients (`tlsv1 alert internal error`, Go
  `remote error: tls: internal error`) — a client failing TLS while curl works is the CDN, not your tool.
- **Do not keep polling** — a cooldown prober itself keeps the block hot. Go fully quiet ~5–15 min; it
  clears on its own (observed clear at ~10 min).
- Need to continue now? Rotate egress: `warp-cli disconnect` (fresh ISP IP) / `warp-cli connect`; a new IP
  is not blocked. Restore the original egress when the engagement ends.
- Report it as a **working defensive control** (positive note), never as a finding.
