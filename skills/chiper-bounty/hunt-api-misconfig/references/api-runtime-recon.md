# Runtime API recon (front-end route/endpoint harvesting)

> Clean-room re-expression of the `api-recon` methodology from ARTEX (AGPL-3.0). Our own text,
> adapted to our tooling. Read this when a target is a SPA/MPA whose API surface is hidden behind a
> JS bundle, and `hunt-api-misconfig`'s normal endpoint list is not enough.

## The two-layer model (and each layer's blind spot)

| layer | what you get | what it CANNOT give |
|---|---|---|
| **static** (JS bundles) | every endpoint path, route drafts, candidate param fields at call sites | HTTP method, params (need 1b), runtime-concatenated URLs |
| **runtime** (live session) | method + body + response + dynamic URLs + WS/SSE; multi-sample diff completes params | needs the page to actually render; one sample cannot separate required vs optional |

Neither layer alone is "complete". Static gives breadth cheaply; runtime gives truth expensively.

## Hard rule #1 — never drag a bundle into context

`index-*.js` is routinely >500 KB. **Do not `Read` or `grep` it into the conversation.** Download to an
output dir, process with a script, print only summaries.

```bash
OUT=recon; mkdir -p "$OUT/js"
curl -s "$BASE/app.js" -o "$OUT/js/app.js"
wc -l "$OUT/js/"*.js                      # verify BEFORE interpreting
grep -rhoaE '"/api/[a-zA-Z0-9_/{}.-]+"' "$OUT/js/"*.js | sort -u > "$OUT/api_static.txt"
grep -rhoaE 'path:\s*"[^"]+"' "$OUT/js/"*.js | sort -u > "$OUT/routes.txt"
```

Every grep you run in the conversation gets `| head -20` or `-m 5`. Never paste bundle fragments.

## Phase 1b — parameter reverse-engineering (the part most people skip)

Path is easy; **fields** are the work. Answer per important endpoint: field names, transport location,
inferred type, required?, sample value, confidence.

**1b.0 — transport shape.** Classify: REST-JSON (body+query) / GraphQL (`variables`) / form-urlencoded /
multipart (upload) / path param (`/user/:id`) / encrypted-or-signed (wrapped in `sign`/`data`).

**1b.1 — anchor-window grep.** Use a known path as the anchor and widen around it — that is where the
packing object lives:

```bash
grep -n '"/api/user/list"' "$OUT/js/"*.js | head -20
grep -rhoaE '.{0,120}("/api[^"]+").{0,200}' "$OUT/js/"*.js | head -20
grep -rhoaE '(params|data|body|payload)\s*:\s*\{' "$OUT/js/"*.js | head -20
```

Wrapper tells: axios instance (`data`/`params`), a shared `request` wrapper (interceptor-injected
global fields), an OpenAPI-generated client, React-Query/SWR hook 2nd arg, Vue composable args.
Type residue is a gift: `yup`/`zod`/`rules`, `Form.Item name=`, an embedded Swagger spec.

**1b.2 — binding layer.** Trace UI → payload: form submit → `onFinish/handleSubmit` → transform → API;
table search → `getFieldsValue()` → `params`; route `:id` / `?tab=`; interceptors injecting
`tenantId`/pagination/`sign`; enum `<select>` options sourced from an API. In DevTools, walk the call
stack upward from `fetch`/`XHR.send`.

**1b.3 — the three packing questions** (do not confuse with the auth gates below):
1. *assembly* — where is the payload built, what transform happened;
2. *validation* — required, pattern, enum;
3. *transport* — path / query / body / multipart / header.

**1b.4** static gives candidates; **required/optional/conditional** is settled only by the runtime
parameter matrix (below) plus error-message reverse-inference.

## Auth gates — three doors, and you must pass all three

| gate | symptom when closed | lever |
|---|---|---|
| **shell/render** | route bounce to `/login`, blank shell | runtime hook L1 |
| **interceptor** | responses arrive but the UI shows "unauthorised" despite HTTP 200 | negative-correction stub L2 |
| **permission** | module page blanks, or every route only returns bootstrap/locale | permission-tree reconstruction |

Fill env vars, cookies, localStorage keys, and a neutralised success value before running runtime.

## Runtime — hook/stub strategy (authorised testing only)

Three stub layers, in order:

- **L1 exact** — stub the auth/permission/bootstrap endpoints so the first screen renders.
- **L2 negative correction** — rewrite any "not authorised" JSON business code to the success code.
- **L3 fallback** — for unmatched `/api` calls, return an empty success body so the UI opens.

Inject at **document-start** (CDP `Page.addScriptToEvaluateOnNewDocument`, or a userscript) so the hook
is in place before the app boots. Verify with a sentinel on `window` and by confirming business paths
no longer bounce to `/login`.

> Note: stubbing changes what the UI *shows*, not what the server *receives*. Outbound bodies/headers
> stay real — **the request is the truth**. Capture it.

## Coverage enumeration (do this, it finds what crawling misses)

Click through, waiting 1–3 s for network per action:
1. every primary nav / sidebar item; 2. tabs (`role=tab`); 3. table row view/edit/detail;
4. toolbars: export, filter, create — **never an irreversible delete**; 5. merge API+routes per module;
6. for SPAs, controlled `pushState` to `routes.txt` paths not yet covered (MPA: do not).

**Parameter trigger matrix** — record each module once per operation type, then diff samples:

| operation | parameters that usually appear |
|---|---|
| list first paint | pagination + default filters |
| search click | keyword, filter |
| advanced filter | more optional fields |
| create/edit | the full entity |
| bulk / export / sort | `ids[]`, `exportType`, `sortField` |

Diffing across operations is what separates required from optional.

## Permission-tree reconstruction (when module pages are blank)

Trigger: every route returns the same tiny bootstrap set, or `routes.txt` is far smaller than the bundle.

```bash
grep -rhoaE '"/api[^"]*(permission|perm|role|menu|acl)[^"]*"' "$OUT/js/"*.js | sort -u | head -30
grep -rhoaE 'userRouteAuth|getResultTree|routeMap|routeLink|menuList|authList' "$OUT/js/"*.js | head -20
```

Typical chain: flat role/permission codes → a permissions tree endpoint → a resolver that maps
`userRouteAuth[CODE].url`. Rebuild the tree, then re-run the runtime phase so module-level APIs appear.

## Output contract (feeds our other tools)

- `api_static.txt`, `routes.txt`, `js/` — static layer
- `runtime_api.json`, `param_samples.json`, `api_detail.json` — runtime layer
- `params_merged.json` — final merged parameter model
- **Then register into the dual graph** (skill `autonomous-exploration`):
  each discovered endpoint → `dualgraph.py asset add --type endpoint`, and the permission findings →
  `node add --kind fact`.

Completion is not "found some endpoints" — it is: static + runtime both done, params merged,
permission tree reconstructed if it was gated, and assets written to the graph.
