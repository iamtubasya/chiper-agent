# WordPress REST API Attack Surface — NASA VDP Patterns

## WordPress Custom Post Types via REST API

WordPress VIP sites (like NASA) often expose custom post types via `/wp-json/wp/v2/{rest_base}`.

### Discovery
```bash
# List all registered post types
curl -s "https://TARGET/wp-json/wp/v2/types" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for k,v in d.items():
    print(f'{k}: rest_base={v.get(\"rest_base\",\"?\")}')"

# Count items per post type
for cpt in $(curl -s "https://TARGET/wp-json/wp/v2/types" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for v in d.values():
    print(v.get('rest_base',''))"); do
  count=$(curl -sI "https://TARGET/wp-json/wp/v2/$cpt?per_page=1" | grep -i "x-wp-total:" | grep -oP '\d+')
  [ -n "$count" ] && echo "$cpt: $count items"
done
```

### NASA Findings (oig.nasa.gov)
- 28 custom post types including: people, topic, mission, reference, event, podcast, guest-author, migration
- `/wp-json/wp/v2/people` → 6 staff members (names, titles, slugs) without auth
- `/wp-json/wp/v2/topic` → 27 topics, 1.5MB+ content (audits 599KB, whistleblower-form 47KB)
- `/wp-json/wp/v2/posts` → 1137 posts accessible
- All content = STATUS: publish (same as public website)

### Severity Assessment
- **Content only = P4-P5** — same data as public website, just structured via API
- **Staff directory = P4** — names + titles, but these are public officials
- **NOT P1-P3** unless unpublished/draft content is accessible
- Check: `?status=draft` `?status=pending` `?status=private` — if all return 0, published-only

### Custom Plugin Namespaces
```bash
# List all namespaces from wp-json root
curl -s "https://TARGET/wp-json/" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for n in d.get('namespaces',[]):
    print(f'  {n}')"
```

NASA discovered namespaces: `nasa-external-content`, `nasa-apps`, `nasa-hds`, `redirection`, `create-block-theme`, `coauthors`, `smd`, `pum`, `nasaplus`, `nasa-3-column-block`

### Redirection Plugin Testing
```bash
# Check redirect logs (may contain IPs, user agents)
curl -s "https://TARGET/wp-json/redirection/v1/log?per_page=10"
curl -s "https://TARGET/wp-json/redirection/v1/404?per_page=10"
curl -s "https://TARGET/wp-json/redirection/v1/group"
curl -s "https://TARGET/wp-json/redirection/v1/setting"
```
All write endpoints (POST) require auth (401). Read endpoints may return data.

### GravityForms Endpoints
```bash
curl -s "https://TARGET/wp-json/gf/v2/forms"
curl -s "https://TARGET/wp-json/gf/v2/entries"
```
Usually 401 (requires auth). But check — some configs expose entries.

### Key WordPress Endpoints to Test
```
wp-json/                    — Root (namespaces, routes)
wp-json/wp/v2/types         — All post types
wp-json/wp/v2/{type}        — Items per type
wp-json/wp/v2/{type}/{id}   — Single item (IDOR test)
wp-json/wp/v2/users         — User enum (often VDP-excluded)
wp-login.php?action=register — Registration test
wp-login.php?action=lostpassword — Password reset
xmlrpc.php                  — XML-RPC (often blocked on VIP)
wp-content/debug.log        — Debug log (403 = exists but blocked)
wp-config.php.bak           — Config backup (403 = exists but blocked)
```

## WordPress VIP POST Route Enumeration

**LESSON (NASA VDP 2026-09-19):** After discovering namespaces from `/wp-json/` root, the next critical step is enumerating ALL POST routes per namespace. nccs.nasa.gov had 83 POST routes, oig.nasa.gov had 251. Some expose write operations that may bypass auth.

### Systematic Enumeration
```bash
# Step 1: Get root routes (shows all registered routes with methods)
curl -s "https://TARGET/wp-json/" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for route, methods in d.get('routes', {}).items():
    for m in methods:
        if m.get('methods'):
            print(f\"{list(m['methods'].keys())[0]:7s} {route}\")" > routes_full.txt

# Step 2: Filter for non-standard POST routes (custom plugin endpoints)
grep -i "post" routes_full.txt | grep -v "wp/v2/" | head -30

# Step 3: Test each POST route (write access check)
for route in $(grep -i "post" routes_full.txt | awk '{print $2}'); do
  status=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" -d '{}' \
    "https://TARGET${route}" --max-time 5)
  echo "[${status}] POST ${route}"
done
# Expected: 401 (auth required), 400 (bad request = endpoint exists), 404 (not found)
# 200 = VULNERABLE — write access without auth
```

### NASA Route Findings
- **nccs.nasa.gov:** 83 POST routes — `/redirection/v1/redirect` (create redirects), `/create-block-theme/v1/*` (theme management), `/batch/v1` (batch operations)
- **oig.nasa.gov:** 251 POST routes — `/coauthors/v1/authors/{id}`, bulk operations, custom import/export
- **All write endpoints returned 401** — auth required on every POST route tested

### NASA Custom Namespace Inventory
```bash
# Extract all namespaces from root
curl -s "https://TARGET/wp-json/" | python3 -c "
import sys, json; d = json.load(sys.stdin)
for n in d.get('namespaces', []): print(n)"
# NASA namespaces: nasa-external-content, nasa-apps, nasa-hds, nasa-3-column-block, nasaplus, smd, pum

# Test each namespace's content-list / content-group endpoints
for ns in nasa-apps nasa-hds nasa-external-content; do
  resp=$(curl -s "https://TARGET/wp-json/${ns}/v1/content-list" --max-time 5)
  echo "${ns}: ${resp:0:100}"
done
```

### ffuf 403 Pattern (Exists But Blocked)
FFUF across WP targets consistently returns 403 for sensitive files — this means they EXIST on the server:
```
[403] .env           — environment config (blocked)
[403] .env.local     — local environment (blocked)
[403] debug.log      — PHP error log (blocked)
[403] wp-config.php.bak — config backup (blocked)
[500] wp-config-sample.php — sample config EXECUTING (database error)
```
The 500 on `wp-config-sample.php` is interesting — it means the file is being parsed by PHP, not served as static. If it contained real DB creds, they'd leak. But sample configs typically use placeholder values.
