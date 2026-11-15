# CMS Vulnerability Patterns — Reference

## Craft CMS

### `window.Craft` Configuration Disclosure
**Severity:** Low/Informational (Medium if chained with XSS)

**What leaks:**
- `csrfTokenName` + `csrfTokenValue` — session-bound, rotates per request
- `systemUid` — stable installation identifier
- `baseSiteUrl` / `baseUrl` — may reveal secondary domains
- `baseCpUrl` / `actionUrl` — admin panel URLs
- `resourceBaseUrl` — CP resource paths
- `timezone`, `language`, `cookie` configuration
- `path` — what action/route was attempted
- `useEmailAsUsername` — false = username-based auth
- `minPasswordLength` / `maxPasswordLength`

**PoC (from ZOwonen audit 2026-09-21):**
```bash
# Extract CSRF token
curl -s https://cms.projecten.zowonen.com/ | grep -o '"csrfTokenName":"[^"]*","csrfTokenValue":"[^"]*"'
# Extract system UID
curl -s https://cms.projecten.zowonen.com/admin/login | grep -o '"systemUid":"[^"]*"'
# Extract secondary domain
curl -s https://cms.projecten.zowonen.com/ | grep -o '"baseSiteUrl":"[^"]*"'
# Extract admin URL
curl -s https://cms.projecten.zowonen.com/ | grep -o '"baseCpUrl":"[^"]*"'
```

**Real findings (ZOwonen):**
- systemUid: `6c745547-b877-4664-994a-d8b290a485e5`
- baseSiteUrl: `https://debaenje.nl/` (secondary domain)
- baseCpUrl: `https://cms.projecten.zowonen.com/admin`
- actionUrl: `https://cms.projecten.zowonen.com/index.php?p=actions/`

**Chaining:**
1. XSS + leaked CSRF token = CSRF bypass on admin actions
2. Leaked `baseSiteUrl` = secondary domain discovery (wider attack surface)
3. Leaked `systemUid` = instance fingerprinting across deployments
4. Leaked `actionUrl` = internal API endpoint discovery

**Why it's by-design:** Craft CMS embeds `window.Craft` in every HTML response for the control panel JavaScript. The object is needed for AJAX requests and CSRF protection. However, it should not be present on non-admin public pages.

### Craft CMS Admin Panel
- Default path: `/admin` → redirects to `/admin/login`
- Actions endpoint: `/index.php?p=actions/`
- Check for unauthenticated action access
- Test default credentials (admin/admin, admin/password)
- Check for rate limiting on login

### Craft CMS + Yii Framework
- Craft CMS uses Yii framework internally
- Yii debug toolbar may be exposed at `/?toolbar`
- Check for Yii-specific vulnerabilities
- Yii CSRF protection may have different implementation

### Craft CMS + GraphQL
- Craft CMS 3+ has built-in GraphQL API
- Default endpoint: `/api`
- Check for introspection enabled
- Query for sensitive content types

---

## WordPress

### User Enumeration
```bash
# Author enumeration
curl -s https://TARGET/?author=1 | grep -o '/author/[^/"]*'
# REST API enumeration
curl -s https://TARGET/wp-json/wp/v2/users | python3 -m json.tool
# Login error messages reveal valid usernames
```

### Version Detection
```bash
curl -s https://TARGET/ | grep -o 'content="WordPress [^"]*"'
curl -s https://TARGET/feed/ | grep -o 'WordPress/[^"]*'
```

### Plugin/Theme Enumeration
```bash
curl -s https://TARGET/ | grep -o 'wp-content/plugins/[^/"]*'
curl -s https://TARGET/ | grep -o 'wp-content/themes/[^/"]*'
```

### Common Vulnerabilities
- `/xmlrpc.php` — brute-force, SSRF, DDoS amplification
- `/wp-login.php` — brute-force target
- `/wp-admin/` — admin panel
- `/wp-content/debug.log` — debug log disclosure
- `/wp-content/uploads/` — file listing
- Plugin-specific CVEs (check version from source)

### Exploit Tools
- `wpscanteam/wpscan` — WordPress scanner
- `rastating/wordpress-exploit-framework` — WP exploit framework

---

## Drupal

### Version Detection
```bash
curl -s https://TARGET/CHANGELOG.txt | head -5
curl -s https://TARGET/core/CHANGELOG.txt | head -5
curl -s https://TARGET/ | grep -o 'Drupal.settings'
```

### User Enumeration
```bash
curl -s https://TARGET/user/1 | grep -i 'title\|name\|error'
```

### Common Vulnerabilities
- Drupalgeddon (CVE-2018-7600) — form API injection
- `/admin/content` — content management
- `/CHANGELOG.txt` — version disclosure
- `/core/CHANGELOG.txt` — version disclosure

---

## Joomla

### Version Detection
```bash
curl -s https://TARGET/ | grep -o 'Joomla! [^"]*'
curl -s https://TARGET/ | grep -o '/media/jui/'
```

### Admin Panel
```bash
curl -sI https://TARGET/administrator/
curl -sI https://TARGET/configuration.php~
curl -sI https://TARGET/cli-config.php
```

### Common Vulnerabilities
- `/administrator/` — admin panel
- `/configuration.php~` — backup config file
- Known CVEs for specific versions

---

## Tomcat

### Version Detection
```bash
# Often in 404 error pages
curl -s https://TARGET/ | grep -o 'Apache Tomcat/[0-9.]*'
# Manager app reveals version
curl -sI https://TARGET/manager/html
```

### Manager App
```bash
# Default credentials
curl -u admin:admin https://TARGET/manager/html
curl -u tomcat:tomcat https://TARGET/manager/html
curl -u admin:password https://TARGET/manager/html
curl -u tomcat:s3cret https://TARGET/manager/html
```

### Common Vulnerabilities
- `/manager/html` — WAR file deployment (default creds)
- Version-specific CVEs
- AJP ghostcat (CVE-2020-1938) if AJP port (8009) exposed
- `/host-manager/html` — virtual host management

---

## Cross-Cutting Patterns

### Admin Panel Discovery
```bash
# Common admin paths
for path in admin administrator wp-admin wp-login.php manager html login; do
  curl -sI "https://TARGET/$path" | head -1
done
```

### Configuration File Discovery
```bash
# Common config files
for path in .env config.php wp-config.php configuration.php settings.py \
            .htaccess web.config appsettings.json; do
  curl -sI "https://TARGET/$path" | head -1
done
```

### Version Disclosure
```bash
# Check headers
curl -sI https://TARGET/ | grep -iE 'server|x-powered|x-generator'
# Check source
curl -s https://TARGET/ | grep -iE 'version|powered.by|generator'
```
