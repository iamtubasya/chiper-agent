# CORS verification: the raw client and the browser disagree in BOTH directions

Measured on finanzen.net (2026-10-18, deepdive 2), on hosts that the Go scanner layer
could not reach at all (see `references/http2-alpn-edge-discriminator.md`). The whole
CORS question had to be answered with a python HTTP/2 harness plus real Chrome.

**Why this lives here rather than in `hunt-cors`:** `hunt-cors` is user-owned, and this
is not a CORS-methodology note — it is the *verification discipline* that applies when
you are already working through an edge-blocked host with a custom harness. The two
phases of `hunt-cors` you still must satisfy (multi-item-ACAO rejection, same-origin
control) are assumed known; what follows is the third case neither of them covers.

## The trap: a readable cross-origin body is not automatically a finding

`hunt-cors` Phase 2b covers the shape where the browser **blocks** a read that the raw
client made look exploitable (a two-item `ACAO: <origin>, *`). This session produced the
**mirror image**, and it is the more dangerous one because it passes every browser check
and still is not a finding.

### Case A — reflect-any-origin + credentials, browser-readable, zero impact

```
GET https://ai.dev.finanzen.net/      Origin: https://evil.example
-> 200   access-control-allow-origin: https://evil.example     <- single valid value
         access-control-allow-credentials: true
```
- Reflected `Origin: null` → `ACAO: null` too.
- Reproduced 6/6 across header variants (with/without `Sec-Fetch-*`, with a `Cookie`
  header, `Accept: text/html`, and on a 404 path).
- **Real Chrome (Playwright, `channel="chrome"`):** a cross-origin credentialed
  `fetch` from `http://127.0.0.1:<port>` returned **200 and the body was readable.**
  A same-origin control from the target origin also returned 200. So the browser did
  *not* block it — the Phase 5a "crown jewel" signature is fully satisfied.

And it is still **Informational**, because of what is actually behind it:

| question | answer |
|---|---|
| what did the readable body contain? | the static SPA shell — an identical 8,488-byte `index.html` for **every** path, including `/main.js`, `/assets/config.json`, `/robots.txt` |
| is any API mounted on that host? | no — every `/api/*` path returned `404 {"detail":"Not Found"}` |
| can the host ever set a session cookie? | no cookie was set, so `credentials: include` transmitted nothing |

**Rule: a CORS bug is a data-exposure bug.** "I could read the response" is step one of
the proof, not the proof. Before classifying, answer three questions — *what is in the
body, is there an authenticated route on this host, and can this host set a session* —
and only then decide severity. A dev host that reflects any origin while serving a
static shell is a hardening item.

### Case B — a fixed, non-reflecting ACAO is a third shape

```
GET https://login.finanzen.net/       Origin: https://evil.example
-> 200   access-control-allow-origin: mein.finanzen-zero.net
         access-control-allow-credentials: true
         access-control-allow-methods: OPTIONS, HEAD, GET, POST, PUT, DELETE, PATCH
```
Same response for a benign Origin and for no Origin at all. This is **neither
reflection nor wildcard** — it is a single allowlist entry, and it must not be logged as
either of the other two. It only becomes interesting if you can get content served
*from* that fixed origin, which is a different host (and here, out of scope).

## How to run the sweep so these shapes separate cleanly

Send **two** requests per host — one with an attacker Origin, one with a benign Origin —
and compare. A single-origin probe cannot distinguish reflection from a fixed allowlist
entry from a wildcard:

```python
for u in urls:
    evil   = probe(c, u, "https://evil.example")
    benign = probe(c, u, "https://www.finanzen.net")
    if evil["acao"] == "https://evil.example":      flag = "REFLECTS-EVIL"
    elif evil["acao"] == "*":                        flag = "WILDCARD"
    elif evil["acao"] and evil["acao"] == benign["acao"]: flag = "FIXED-ALLOWLIST"
```
`REFLECTS-EVIL` + `ACAC: true` is the only shape that can be High, and it is High only
after the Case-A questions above are answered. Runnable version:
`scripts/cors_origin_sweep.py`.

## Verification order that avoids a false positive

1. Raw client, both origins → classify the header shape (reflection / wildcard /
   fixed / multi-item / none).
2. If reflection + `ACAC: true`: real Chrome, credentialed cross-origin fetch **with a
   same-origin control in the same page** (`hunt-cors` Phase 5d — an opaque `null`
   origin from `page.set_content` or `about:blank` throws the identical
   `TypeError: Failed to fetch` and fabricates a "BLOCKED").
3. Only if the read succeeded: enumerate what the host actually serves. A catch-all SPA
   is the usual reason a "successful" read is worthless — probe a deliberately random
   path and compare byte length and `<title>` against the "hit".
4. Ask whether the host can set a session at all. No cookie ⇒ `credentials: include`
   is decorative.

## Two harness notes from the same run

- **A `sandbox` iframe cannot be used as a null-origin emitter from a served page.**
  Accessing `iframe.contentWindow.fetch` from the parent threw
  `SecurityError: Failed to read a named property 'fetch' from 'Window'` — the frame is
  cross-origin to the parent even when sandboxed. Use `srcdoc` + `postMessage`
  (`hunt-cors` Phase 5b), or drive the fetch from a page whose *document* origin is the
  target's.
- **Cross-origin `fetch` to a host that 403s non-browser clients fails in the browser
  too.** `ai.finanzen.net`, `login.finanzen.net` and `zeroapp.finanzen.net` all returned
  `TypeError: Failed to fetch` from the attacker page while the same URLs answered the
  harness fine — the edge rule that blocks the Go layer also blocks a browser fetch that
  lacks the right fetch-metadata headers. That is a transport artefact, not a CORS
  verdict; re-test those hosts from a page loaded on their own origin before recording
  anything.
