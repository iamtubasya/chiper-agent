# Legacy / zombie surface archaeology (worked example: forexfactory.com, round 3c)

Modern front-ends keep routing legacy PHP (forum engines, ad servers, upload handlers). Those paths
are frequently absent from the HTML/JS you can see and are usually the least-hardened code left.
History is where the endpoint names **and the real parameter names** live.

## 1. Harvest history

```bash
gau --subs --threads 5 forexfactory.com cryptocraft.com energyexch.com metalsmine.com \
    | sort -u > recon/disc/gau_urls.txt        # 520,055 URLs in the FF case
# fallback (was dead for this target — 0 URLs):  echo DOMAIN | waybackurls
```

## 2. Mine endpoint + parameter names

```bash
# legacy script files, by frequency
cat gau_urls.txt wayback_urls.txt | grep -oE "/[A-Za-z0-9_]+\.php" | sort | uniq -c | sort -rn | head -30

# real query parameters, digits normalised so variants collapse
grep -oE "/attachment\.php\?[^\"' ]{0,120}" gau_urls.txt \
  | sed 's/[0-9]\{2,\}/N/g' | sort | uniq -c | sort -rn | head -8
```

Controls nothing else would give you: `attachmentid`, `stc`, `thumb`, `d`, `do=whitelist_img&p=`,
`eventid`, `what=zone:N&exclude=,&referer=`, `filename=&contenttype=`, `bannerid/clientid/zoneid/cb`.
That parameter list is the actual test plan — do not guess parameter names on legacy files.

## 3. Liveness classification (one request per unique path)

| class | meaning | example result |
|---|---|---|
| 404 | dead | `ads/adjs.php`, `ads/adimage.php`, `ads/adlog.php`, `ads/adview.php`, `ajax.php`, `ajax_actual.php`, `about.php` |
| 301 → modern route | alive, re-pointed | `attachment.php?attachmentid=N` → `/attachment/file/N` |
| 200, 0 bytes | stub kept for includes | `global.php` |
| 401 + `www-authenticate` | gated at the edge | `/admincp/`, `/admincp/index.php` → nginx `Basic realm="Restricted Content"` (body is the Cloudflare JS challenge) |
| 200 same shape for any word | **soft-404** | see §5 |

## 4. Probing a legacy download endpoint (`/attachment/file/<id>`)

What a complete probe looks like — all negative here, but this is the shape of the test:

* **Byte truth, not status**: `curl -s -D hdr.txt -o body.bin <url>` → `Content-Length`,
  `Content-Disposition`, magic bytes (`%PDF-1.4`, 547 726 bytes, served unauthenticated for public ids).
* **Per-object ACL**: ids 1–5, 100, 999999999 → 403 as guest / **400** with a session, while public
  ids → 200. Never conclude "IDOR" from one 200; check the 403 class first.
* **ID normalisation / injection**: `1240107'` → 1240107, `1240107 and 1=1` → ignored, `1e5` →
  `100000`, `1%00` → 1 ⇒ numeric cast (consistent with no SQLi). Traversal `..`, `%2e%2e%2f`, `%00`,
  pretty-path `/id/x.pdf`, quoted/CRLF filenames → 302 to the canonical URL with `?fr=1`, or 404/400.
* **Conversion pipeline**: `?thumb=1` returning the identical byte size ⇒ no on-the-fly image
  conversion, so no ImageMagick-style SSRF/RCE angle to chase (if the size *did* differ, hunt that).
* `Content-Disposition: attachment; filename="…"` percent-encoded ⇒ no header injection.

## 5. Soft-404 detection (mandatory before trusting any dir-bust)

`www.cryptocraft.com` / `www.metalsmine.com` answer **HTTP 200 for unknown paths** with a *username
profile page* (`/upload` → `<title>upload's Profile`). Control path: `/zzz-nonexistent-xyz` →
`Notice | Page Not Found`. So:

* every ffuf/dirsearch hit on those hosts is noise until you read the `<title>`;
* `/.env`, `/.git`, `/.git/HEAD` → the 5503-byte Cloudflare block page (403), not a leak;
* same trap on the main site for `/<anything>` usernames (e.g. `/core/` = "Core's Profile").

## 6. Admin-panel bypass matrix (when a panel answers 401 Basic)

Path normalisation:
```
/admincp/..;/   /admincp/./   //admincp/   /admincp%2f   /%61dmincp/   /admincp/../admincp/
/./admincp/index.php   /admincp//index.php   /admincp;/   /;/admincp/   /admincp/index.php/..;/
/admincp/index.php%00.html   /ADMINCP/   /admincp/?x=1   /admincp/%2e%2e/admincp/
```
Methods: `POST PUT PATCH OPTIONS TRACE` (TRACE usually 405).
Header spoofs: `X-Forwarded-For / X-Real-IP / X-Original-URL / X-Rewrite-URL /
X-Custom-IP-Authorization / X-Originating-IP / Client-IP / CF-Connecting-IP / X-Forwarded-Host /
X-Forwarded-Prefix` all set to `127.0.0.1` or the panel path.

FF result: every variant stayed 401 (three were 403 by the WAF) — no bypass. Do not brute force the
credential (excluded class).

## 7. When semgrep is unavailable: DOM-sink inventory by hand

`semgrep` on this box fails to import (missing `colorama` → `protobuf` → `ruamel.yaml`). Substitute:

```python
# sinks
r'(innerHTML\s*=|\.html\(|document\.write|insertAdjacentHTML|\.append\(|\.prepend\()'
# sources that matter for DOM XSS
r'(location\.hash|location\.search|URLSearchParams|document\.referrer|postMessage)'
```

Then read every hit's context and judge the *source*:

* `window.addEventListener("message"` → check whether it is a **first-party** handler reaching a
  sink. Third-party IAB CMP surrogates (`id5-production.js`: `postMessage(o,"*")` + callId matching)
  are standard ad-tech and not a finding.
* sinks fed by **server-rendered HTML** (`$(el).html(v.data.post)`, `m.innerHTML=<flex XML>`,
  `f.html(a.html)`) are the same escaping surface you already tested server-side — not DOM XSS.
* a "legacy hash parser" that only `parseInt()`s is safe; `location.hash → innerHTML` is the pattern
  to look for.
* static `cgs-*` chart templates are inert.

## 8. Cheap high-signal differentials to run on every hardened target

* **CSRF-freeness (significant requests only)**: repeat the state-changing POST with (a) no CSRF
  header and (b) `Origin: https://evil.example`, `Referer: https://evil.example/`. Expect 400 — or
  `200 + <error>Your request could not be completed…</error>` for `/member.php`. Only "insignificant"
  requests are excluded, so a real hole here is payable.
* **Open redirect** (NOT on FF's exclusion list — always worth it): try `//evil.example`,
  `/%2f%2fevil.example`, `/\/evil.example`, `/path//evil.example`, `/path/../..//evil.example`,
  `?next=`, `?url=`, `?redirect=` against any canonicaliser/trailing-slash 302.
* **Clickjacking**: grep `x-frame-options|content-security-policy` on /, /login, /create-account,
  /resetpassword and a profile. FF sends `SAMEORIGIN` + `frame-ancestors 'self'` → dead.
* **Secrets**: run trufflehog on the **JS/HTML assets only** — pointed at a 40 MB URL dump it reports
  junk (Roaring/Box detectors matching forum slugs like `kitty-faces-securities-fraud`). Add a regex
  sweep (`AIza…`, `AKIA…`, `sk_live_…`, `ghp_…`, `xox…`, `BEGIN … PRIVATE KEY`) and look for
  internal hosts (`10.`/`192.168.`/`.internal`).
* **Buckets/ports**: `s3scanner` on plausible names (all absent here); `naabu` is meaningless behind
  Cloudflare — every port "answers" at the edge, which is not a service.

## 9. Excluded-classes discipline (Forex Factory program, "Last Updated: October 2026")

Do not spend depth on, and never submit: DoS, **TLS config**, SPF/DMARC, host-header injection,
CORS config, cookie flags, weak password policy, session management, unique email,
**email enumeration / IDOR / brute force**, CSRF-less insignificant requests, phishing,
client/CDN cached information. Payable: real server-side attacks (SQLi/RCE/SSRF/deserialisation/
template) and XSS that survives sanitisation — Critical $5–10K, High $2.5–5K, Medium $250–1K (XSS),
Low $100–250.
