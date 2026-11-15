# Reflected XSS via a framework error page that echoes the request path

Found live 2026-10 on a legacy Java tier. Highest-yield cheap test on any host that runs an old
framework: request a path that has no route, with a payload in the path itself.

## The probe

```bash
curl -s "https://<host>/<any-prefix>/%3Cscript%3Ealert(document.domain)%3C/script%3E"
```

Look for the decoded payload appearing **unescaped** in the response body. Two contexts matter:

```html
<title>Error: Unhandled request: /<script>alert(document.domain)</script></title>   <!-- RCDATA: inert -->
...
<div id="header"><h1>Error: Unhandled request: /<script>alert(document.domain)</script></h1></div>
                                        ^^^ this one is in the BODY and EXECUTES
```

Occurrences inside `<title>` are inert (RCDATA consumes `<script>` as text until `</title>`). Count the
occurrences and locate each one before claiming execution — a hit count of 2 with only one live context
is the normal shape here.

## Prove execution, do not infer it

Reflection in a text response is not XSS. Drive a real browser and capture BOTH kinds of proof, because
an alert dialog can be suppressed by automation settings:

```python
dialogs = []
pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
pg.goto(payload_url); ...                       # proof 1: dialog fired, message == <host>
# proof 2: DOM mutation, works with no dialog at all
pg.goto(".../<script>document.title='XSSED-'+document.domain</script>")
pg.title()                                      # == "XSSED-<host>"
```

Keeping a payload that mutates the DOM (`document.title`) as the primary proof makes the finding
robust to environments that auto-dismiss dialogs.

## Check the mitigations before rating severity

| Control | What it means here |
|---|---|
| `Content-Security-Policy` with **no `script-src`** (only `upgrade-insecure-requests`, `frame-ancestors`) | inline script is NOT blocked — the XSS executes. Do not assume CSP saves them. |
| `script-src` present but containing `'unsafe-inline'` | same conclusion |
| `X-XSS-Protection: 1; mode=block` | legacy header, modern browsers ignore it — not a mitigation |
| `X-Content-Type-Options: nosniff` | irrelevant, the response is `text/html` by design |

## Scope the breadth honestly

Not every unhandled path produces the error page — on the live target only one prefix
(`/fcmbridge/api/*`) did, while `/zzz`, `/globus-2026/zzz`, `/migsys/zzz` returned a plain 404.
Sweep ALL in-scope hosts with the payload and record exactly which (host, prefix) pairs reflect:

```
44 requests -> hits: pipe.orf.at /fcmbridge/api/, bolek.orf.at /fcmbridge/api/   (same app, two hosts)
```

Same root cause on two hosts is still ONE finding — update the breadth, keep it one report. Narrow
breadth (one endpoint) is what keeps the rating at Medium instead of High; say that explicitly rather
than inflating it.

## What the same page usually leaks (note it, do not lead with it)

Framework error pages of this vintage also print a **server stack trace**:

```
stick/lib/stick.js:187 (unhandled) / middleware/route.js:226 / middleware/mount.js:128 /
middleware/params.js:183 / ringo/jsgi/connector.js:48 (handleRequest)
```

That identifies the stack (RingoJS + Stick on Jetty) and is useful for understanding the app, but a
stack trace alone is usually an out-of-scope "best practice" item on a VDP. Report the XSS; mention the
trace as a secondary observation in the same section.

## Pitfalls

- **Do not build elaborate payloads before you have a simple one working.** A complex
  `document.body.innerHTML=...` payload with `%23`, `%3B` and quotes was mangled by the server and did
  not execute, while `alert()` and `document.title=` worked first try. Characters like `#` (fragment)
  and `;` break the reflected context. Start with the simplest possible proof.
- **Verify the reflection is decoded, not just echoed.** Here `%3Cscript%3E` arrived as `<script>`,
  which is why it rendered as markup. If the payload comes back still percent-encoded there is no bug.
- **Count, then locate.** Grep gives a number; open the raw response and read the surrounding 200 bytes
  before you conclude the tag is live.
