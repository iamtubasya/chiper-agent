# Document-viewer / link-preview `?url=` fetch SSRF (blind) — hunting notes

Class: a product's **viewer / preview / unfurl endpoint fetches a URL the caller names**.
Highest-frequency real-world shape: `?url=` on a viewer front that hands the URL to an internal
renderer. Yandex DocViewer is the worked case (2026-10), but the method generalises.

## 1. Find the real fetch endpoint, not the alias it redirects from

The public alias was a thin redirector:

```
docviewer.yandex.ru/?url=<X>          -> 302 -> https://docs.yandex.ru/docs/view?url=<X>&serpParams=...
```

Both shapes were tested; only the **front** (`docviewer.yandex.*/?url=`) actually triggered the fetch
(the `/docs/view` target did not). A redirect chain that 302s does not tell you which hop fetches —
request each hop yourself and fire one OOB probe per hop.

## 2. The outbound request carries the SERVICE's identity — collect it verbatim

This is the difference between "somebody fetched my URL" and "the DocViewer front fetched my URL":

```
GET /x HTTP/1.1
Host: <label>.oast.pro
User-Agent: Yandex DocViewer
X-Request-Attempt: 1
Yandex-Cloud-Request-Id: dv-73db6acdbc98cacbdac438a9cc226313-docviewer-front-stable-docviewer-95
```

- the `User-Agent` names the fetching component;
- `X-Request-Attempt: 1` = the service **retries** the fetch;
- the request-id names the internal service (`docviewer-front-stable`) — quote it in the report.

## 3. The fetch is SYNCHRONOUS — which both proves it and breaks timing probes

Measured (3 samples each, mean): OOB-host fetch `2.89/2.64/4.50` s vs DNS-fail `1.41` s, private
`1.4` s, unroutable `1.47` s, public-IP `1.61` s. Reading: a real fetch costs seconds; everything that
fails fast is ~1.4 s. Two consequences:

- a slow response to your OOB host is *itself* weak evidence the fetch happened (before the callback lands);
- **the same signal cannot separate private-range reach**, because filter-rejected, refused and unroutable all
  land in the same ~1.4 s band. Do not claim internal reach from timing.

## 4. Read-back trap: a viewer's `<title>` mirrors the URL — that is NOT read-back

The viewer page title was the **last path segment of the URL I sent**: `?url=http://h/x` -> `title="x"`,
`.../index.html` -> `title="index.html"`, `.../Main_Page` -> `title="Main_Page"`. It looks like the fetched
document leaked into the response and it is string formatting.

Settle read-back with content, not shape: serve a **unique marker in the fetched body** and grep the response for
it, and compare two different bodies at the same URL. Absent ⇒ **blind**, and say so.
Yandex DocViewer: blind — the response was a fixed HTML shell, marker never appeared.

## 5. Bypass battery — what actually reproduced here

| probe | result |
|---|---|
| `http://<oast>/x` | **hit** (fetch confirmed) |
| decimal IP literal `http://2994787537/x` (= our host) | **hit** — dotted-quad filters do not catch it |
| public URL that answers 302 → OOB hop | **hit** — redirects are followed |
| `127.0.0.1`, `10.0.0.1`, `169.254.169.254`, `192.0.2.1` | no hit; ~1.4 s (filter/refusal) |
| `file:///etc/passwd` | `400` — scheme rejected |

So: numeric-IP acceptance + redirect handling are **confirmed**, private-range reach is **not**. Report the two
bypasses, and keep internal reach explicitly in the not-demonstrated bucket.

## 6. Endpoint discovery beside the viewer

The viewer's own JS exposed a JSON router `POST /api/<method>?*=<url>&dsid=<id>` (headers `Content-Type`,
`X-Requested-With`, `X-Retpath-Y`). Every method guess (`preview`, `page`, `convert`, `print`) answered
`400 {"error":true,"code":400}` — record it as *"method names not established"*, never as a clean negative.

## 7. Attribution discipline (matches the OOB gate)

One unique collaborator label per request, one request at a time, poll between requests. A batch of 51 blocks with
several labels lands unattributable; the per-label separation above is what produced `t1/t2/t3` + `ru1` + `com1` + `r1`
cleanly enough to state "3 of 3, on two hostnames, plus redirect hop".

## 8. Honest boundary wording that survived review

> The response returned to the caller is a fixed HTML shell and does not contain the fetched document, so the issue is
> blind. Loopback and private-range targets did not produce a hit, and the same-host timing probe did not separate them
> (1.42 s vs 1.47 s), so reach into loopback or RFC1918 space is not demonstrated here. No internal service was
> accessed and no state was changed.
