# authentik-outpost estates: unauthenticated testing recipe

Worked example: nationalcompute.com bounty (2026-10-26). Estate: apex API host + console + auth
(authentik 2026.5.8) + docs + onboarding + JupyterHub workspaces + Grafana, all behind Google CLB,
every app host behind an authentik proxy outpost. Outcome: unauth surface fully mapped, zero
findings, authenticated attack plan staged. The recipe below is the reusable part.

## 1. Map the outpost's public-path allowlist FIRST

Every non-allowlisted path 302s to `https://<host>/outpost.goauthentik.io/start?rd=...`. Probe a
curated list (API paths from OpenAPI contracts + SPA routes + common files) and record which answer
something other than 302. On the worked example the allowlist was:

- `/api/{vm,k8s,market,billing,org}/openapi.json` (unauthenticated contracts - these ARE the map)
- `/api/checkpoints/public` + `/api/checkpoints/public/<id>` + `.../content[?download=1]`
- `/public/*` SPA routes (`/public/marshall`, `/public/checkpoints`), `/login`, `/request-access`
- `/llms.txt`, `/AGENTS.md`, `/FIRST-JOB.md`, `/documents/*`, `/static/*`, `/.well-known/security.txt`
- Public POST form endpoints NOT in any contract (found by mining public content - see §5)

## 2. Path-normalization bypass matrix (run all, expect 401)

If the outpost matches the raw path but the backend normalizes, a public prefix could reach a
gated route. Test on every outposted host:

```
/api/checkpoints/public/../whoami          -> must be 401 at the API layer
/api/checkpoints/public/..%2fwhoami
/api/checkpoints/public/%2e%2e/whoami
/api/checkpoints/public/../../api/whoami
/public/marshall/../api/whoami
/public/marshall/..%2fapi%2fwhoami
//api/whoami        /api//whoami        /api/./whoami
/api/whoami/        /api/whoami%20      /api/whoami?
/API/whoami         /api/checkpoints/public/..;/whoami
/api/checkpoints/public/..%00/whoami      (null byte -> 400)
/llms.txt/../api/whoami    /documents/../api/whoami
```

Result on the worked example: every variant reached the API's own auth check (401) or was rejected
(400/301). No bypass. A 401 through a trick path is the CORRECT outcome - report nothing.

Related trap: parameterised routes that answer 422 before 401 (FastAPI validates query params
before the auth dependency). Re-test with complete parameters; if it flips to 401, that is
validation ordering, not an auth bypass.

## 3. Drive the sign-in flow via the executor API (no browser needed)

The browser flow is a Lit SPA in shadow DOM (see §4). The same flow is plain HTTP:

```python
import requests, re, urllib.parse
s = requests.Session()
s.headers["User-Agent"] = "<browser UA>"
r  = s.get("https://apex/sign-in", allow_redirects=False)          # 302 -> outpost start
r2 = s.get(r.headers["Location"], allow_redirects=False)           # 302 -> /application/o/authorize/...
r3 = s.get(r2.headers["Location"], allow_redirects=False)          # 302 -> /if/flow/default-authentication-flow/?...
q  = urllib.parse.urlparse(r3.headers["Location"]).query
ex = s.get("https://auth.host/api/v3/flows/executor/default-authentication-flow/",
           params={"query": q}).json()
to = ex["to"]                     # xak-flow-redirect -> the real flow slug (e.g. nc-magic-link)
m  = re.search(r"/if/flow/([^/?]+)/\?(.*)$", to)
slug, query = m.group(1), m.group(2)
challenge = s.get(f"https://auth.host/api/v3/flows/executor/{slug}/",
                  params={"query": query}).json()
# challenge: component=ak-stage-identification, user_fields=["email"], sources=[Google...]
post = s.post(f"https://auth.host/api/v3/flows/executor/{slug}/",
              params={"query": query},
              data={"uidField": "test@example.com"})               # FORM-ENCODED, not JSON
```

Hard-won details:

- **The POST body must be `application/x-www-form-urlencoded`.** JSON (any shape: bare fields,
  `{component, ...fields}`, nested `flowChallengeResponseRequest`) fails with
  `{"non_field_errors": ["No identification data provided."]}`.
- **The identification field is `uidField`**, not `email`/`username` - `user_fields: ["email"]`
  in the challenge describes the widget, the wire name is `uidField`. Confirm by dumping the
  shadow DOM (§4) or the stage chunk (`/static/dist/src/flow/stages/identification/chunks/*.js`).
- The `authentik_csrf` cookie may never be set; the POST succeeds without the header anyway.
- Success = the challenge advances (`ak-stage-email-sent` / "Check your Inbox"). A systematic
  `ak-stage-flow-error` with only a `request_id` means the request shape is wrong, not a platform
  500 - fix the request before reporting anything.
- Flow slugs to probe: `default-authentication-flow` (usually redirects to the product's real
  flow), plus product-specific ones seen in redirects; `default-invalidation-flow` is stock.

## 4. Browser fallback for shadow-DOM (Lit) forms - use pyautogui

When you must complete the flow in a real browser (magic-link click-through, consent screens):

- WebDriver CSS selectors do NOT pierce shadow roots. `sb.type('input[name=...]')` either misses
  or types one character before the Lit re-render detaches the element.
- `execute_script` with a native value setter + synthetic events sets the DOM value but the
  framework's submit handler reads empty state; the Continue click then does nothing.
- CDP `Input.insertText` / `dispatchKeyEvent` works for typing but BREAKS subsequent
  `Runtime.evaluate` calls (they silently return null) - do all verification before typing, or
  use a different channel after.
- **What works: headed SeleniumBase + pyautogui.** Find the input's viewport coordinates with a
  shadow-piercing JS `getBoundingClientRect`, `pyautogui.click(x, y)`, `pyautogui.typewrite(...)`,
  `pyautogui.press("enter")`. Real OS input events satisfy the framework every time.

```js
// shadow-piercing finder (self-contained IIFE - window helpers are wiped by SPA navigation)
(() => {
  const walk = (root, sel) => {
    let f = root.querySelector(sel);
    if (f) return f;
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) { const r = walk(el.shadowRoot, sel); if (r) return r; }
    }
    return null;
  };
  const i = walk(document, 'input[name="uidField"]');
  if (!i) return 'NO';
  i.focus();
  const r = i.getBoundingClientRect();
  return 'YES:' + (r.x + r.width/2) + ':' + (r.y + r.height/2);
})()
```

To capture the exact wire format for later replication, run the browser through mitmdump
(`mitmdump -p 8899 -s addon.py --ssl-insecure`, browser launched with
`proxy="http://127.0.0.1:8899"` + `--ignore-certificate-errors`; if a port is permission-denied,
pick another - do not fight it).

## 5. OAuth + MCP registration checks (quick, high-signal)

- **redirect_uri validation**: hit `/application/o/authorize/?client_id=<id>&redirect_uri=<X>&response_type=code&scope=openid&state=x`
  with the exact legit URI (302 = accepted baseline), then evil host, extra query param, case
  variant, encoded `?`, and the bare path. All-400 except the exact match = strict = no finding.
- **MCP dynamic client registration** (`POST /mcp/oauth/register`): probe redirect_uris
  (evil.com, console host, `*.` subdomain, `urn:ietf:wg:oauth:2.0:oob`, loopback with odd ports).
  Loopback-only acceptance with a shared public client_id is the secure pattern.
- **MCP endpoint pre-auth**: `POST /mcp` with an `initialize` or `tools/list` JSON-RPC body must
  401 with a `WWW-Authenticate: Bearer resource_metadata=...` header; `GET /mcp` must 405.

## 6. The waitlist / disposable-inbox playbook (signup blocked)

For platforms that self-serve only `.edu/.mil/.gov` (auto-org + credits) and wave everyone else:

1. Create a mail.tm inbox: `GET https://api.mail.tm/domains` -> `POST /accounts {address,password}`
   -> `POST /token` -> bearer for `GET /messages` (+ `/messages/{id}` for bodies).
2. Submit that address through the real sign-in flow (browser, §4). The reply mail states the
   policy verbatim ("no account for this address yet... opens in waves") - archive it as evidence.
3. Cron monitor (every 20m) that fetches the inbox and prints WAITLIST_OPENED + body + links only
   when a NEW mail arrives that is not the original waitlist note; otherwise stays silent.
4. Meanwhile extract the authenticated attack plan from the SPA JS (§7) and stage it by tier.
5. Tell the operator the blocker with concrete options (their own org token / an eligible address
   / wait). Do not fabricate progress.

## 7. SPA-JS endpoint extraction (when jsluice is unavailable)

If jsluice cannot be built or run, the complete inventory is one regex pass over the SPA HTML and
its JS bundles (the console SPA here was a 1.27 MB server-rendered page with the whole app inline;
the gardengate bundles under `/static/gardengate/` were plain public files):

```python
import re
c = open("spa.html", encoding="utf-8").read()
paths = set()
for m in re.finditer(r'["\'`](/(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]*)["\'`]', c):
    paths.add(m.group(1))                       # string literals starting with /
for m in re.finditer(r'`(/[^`]{2,90})`', c):    # template literals
    paths.add("T:" + m.group(1))
```

This yielded every route and every org-scoped API path (`/api/orgs/{ORG_UUID}/billing/...`,
`/api/orgs/{uuid}/k8s/storage/bucket/reveal`, `/api/clusters/{cluster}/...`), plus the RPC method
inventory of the workspace daemon (`grep -oE 'call\("[a-z.]+"' app.js`). Then probe each path on
each host and record the gate (302/401/404/200). Download the public JS bundles and grep them the
same way - transport comments in them (e.g. "credentials travel only in the hello frame") document
the auth architecture for free.

## 8. What was clean on the worked example (do not re-burn)

OAuth redirect_uri (exact-match), outpost rd= (no open redirect), MCP DCR (loopback-only),
authentik API beyond documented endpoints (403/404), Grafana signed-out (within the documented
allowance - check /bootdata for secrets/org names, not for feature toggles), JupyterHub signed-out
(no signup, /hub/api 403), checkpoint feed (UUIDv5 IDs not predictable; q= not injectable by both
sqlmap and ghauri; dalfox 0 issues), public form endpoints (strict validation, CRLF blocked, type
confusion blocked, no SSRF via URL fields), CORS (credential-less `*` on public data only),
TRACE 405, XFO DENY + frame-ancestors 'none' on all public pages, DNS (no dangling records),
gau historical URLs (all gated), scope params ignored server-side.
