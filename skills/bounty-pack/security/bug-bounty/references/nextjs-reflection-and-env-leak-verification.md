# Next.js reflection + `__NEXT_DATA__` env leak — verify before you score

Two Next.js patterns that show up on hardened targets. One is a real (low) finding, the other is
the single most common false positive a hunter files on a Next.js site.

## 1. `__NEXT_DATA__` env leak (Pages Router) — real, CWE-200 / Low

Next.js **Pages Router** app, server-rendered inline JSON:

```html
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{},
 "env":{"NNAPI_URL":"http://tunnel.nordnet.se","NNX_URL":"https://api.prod.nntech.io"},
 "page":"/[planId]/admin","query":{"planId":"1"},"buildId":"..."}
</script>
```

The `env` object is emitted when the app wires `getInitialProps` to inject config. It leaks
**internal backend hostnames and the scheme** — a plaintext `http://` internal API is the
reportable part. Grep every Next.js host for `__NEXT_DATA__`; read the `env` block.

Also pull the route table + all chunks while you're there:
- `/_next/static/<buildId>/_buildManifest.js` → the full `"/route":[chunks]` map AND the
  `__rewrites` (`{"source":"/metrics","destination":"/api/prometheus"}` — internal route aliases).
- Fetch every referenced chunk, then `grep -hoE '"/api/[^"]*"'` for the API surface
  (`/api/2/hantera/users/*`, `/authentication/v2/methods/...`). Params in chunk URLs (`?ver=`)
  give exact plugin/library versions.

App Router (13+/14+) has **no `__NEXT_DATA__`** — it ships an RSC flight payload
(`self.__next_f.push(...)`) instead. Don't conclude "no config leak" because the tag is absent.

## 2. Reflection != XSS — run the encode-differential yourself

`dalfox` prints `[I] Reflected <param> => PTYPE: URL Injected: /inATTR-double(1)/inJS-double(1)/inHTML-none(2)`
for *reflections* and only prints `[V]` when it can execute. A reflection is not a finding.
Do not file until you verify the encode behaviour by hand.

**Test matrix** — send, then read the raw response body (not a rendered view):

| payload | safe (no bug) | breakout (bug) |
|---|---|---|
| literal `"` in query | comes back `%22` | raw `"` |
| `</script>` | `%253C%252Fscript` or `\u003c/script` | raw `</script>` |
| `<>` | `&lt;&gt;` | raw `<>` |

**nordnet.se result (verified negative):** the query is reflected into the `og:url` meta tag AND
into the RSC flight payload, but is **URL-encoded on re-emit** (`"`->`%22`,
`</script>`->`%253C%252Fscript`). Non-exploitable.

**Gotcha that looks like a hit but isn't:** the flight payload renders a literal `<c>` raw
(`...\"search\":\"?lang=NNXa\\"b<c>d\"...`). `<` inside a JSON string inside `<script>` is
harmless — the only sequence that breaks out of the tag is a literal `</script>`, and that gets
encoded. Re-test after any rate-limit window clears so the negative is trustworthy.

## 3. Next.js route enumeration without the app

`_buildManifest.js` is a minified `self.__BUILD_MANIFEST=function(a,s,n,...){return{...}}` — the
per-route chunk lists reference shared chunks by **minified variable** (`[a,s,n,t,...]`), plus
literal `"static/chunks/pages/<route>-<hash>.js"` for page chunks. Extract both regexes; the
trailing `__BUILD_MANIFEST_CB` call argument list is where the shared chunk filenames live.
