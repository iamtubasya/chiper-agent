# SPA bundle + tRPC recon (Step 3d)

For a Vite / rolldown / webpack front end (and any tRPC backend), the client bundle **is** the API
map and the config dump. This extends Step 3b (bundle_apimap.py) with the two things that actually
paid off on a hardened target: (1) walking the whole chunk graph for the build-time env block, and
(2) turning the tRPC endpoint into a procedure inventory.

## 1. Identify the build + the chunk graph

```bash
curl -s https://app.<target>/ | grep -oE 'https://[^"]+/[^"]*main-[^"]+\.js'
```

Vite entry chunks are tiny (`main-*.js` ≈ a few KB) and `import` dozens of hashed chunks. Crawl them
recursively; do not stop at the entry. `scripts/` has no crawler bundled here because the one used
was ~40 lines — the pattern:

- fetch `main-*.js`
- regex `["'](\./[^"']+\.js)["']` **and** `import\(\s*[`"'](\./[^`"']+)`
- BFS, cap at a few hundred chunks, **write each chunk to disk as it arrives** (a cap that writes
  only at the end loses everything when the network resets)

A full build has thousands of chunks; 300 is plenty to recover the config and router names.

## 2. Dump the build-time env (the highest-value artefact)

Search every chunk for the injected env block:

```bash
grep -rhoE 'VITE_[A-Z_0-9]+:\s*[`"'"'"'][^`"'"'"']*[`"'"'"']' chunks/ | sort -u
```

What shows up, and how to read it:

| Value kind | Verdict |
|---|---|
| publishable/site/client keys (Clerk `pk_live_`, Stripe `pk_`, ChargeBee `live_`/publishable, Datadog `pub…` **client token**, PostHog `phc_`, reCAPTCHA/Turnstile site key, OAuth *client IDs*) | public by design — **not a finding** |
| API base URLs, feature flags, auth endpoints (`VITE_API_URL`, `VITE_*_REDIRECT_URI`) | recon intel — feeds the endpoint map |
| **allowlists** keyed by tenant/UUID (`*_ALLOWLIST_ORG_IDS`, `*_TEST_ORGS`, `*_ALLOWED_ORGS`) | internal server-side control data leaked to the client → reportable info-disclosure |
| **internal identifiers** (`*_INTERNAL_USER_IDS` = staff GitHub IDs, internal workspace UUIDs) | reportable info-disclosure |
| `VITE_ENV` / `VITE_APP_VERSION` / build SHA | confirms prod vs dev instance |

Framing for the allowlist/ID leak: the defect is that *server-authoritative gating data* (which
tenants get the privileged feature) and *internal staff identities* were baked into a public
artefact. Severity is Low — none of it is a credential — but it is intended server-side data, not
client config, so it is a valid report. **Do not** report publishable keys as secrets; that gets
N/A'd instantly.

`import.meta.env.*` in the source compiles away, so grep the built chunk, not the source.

## 3. Map the API from the routers

The env block names the API base (`VITE_API_URL` is often `https://app.<target>/trpc`). Chunk
filenames leak feature/route names (`SsoOAuthCallback`, `CLITokenAuth`, `GitLabSelfHostedLogin`,
`AzureDevOpsTenantLogin`, `ViewAs*`) — an architecture map for free.

tRPC route names also leak in **source-mapped dev paths** inside chunks, e.g.
`apps/<svc>/src/trpc/routes/session/change-stack.ts` — grep for `trpc/routes/` to recover the
server-side router layout.

## 4. Enumerate tRPC procedures unauthenticated (the 401/404/405 oracle)

tRPC's error codes make an existence oracle: `-32001 UNAUTHORIZED` (401) = procedure **exists,
auth-gated**; `-32004 NOT_FOUND` (404) = **does not exist**; `-32005 METHOD_NOT_SUPPORTED` (405) =
it is a **mutation** (exists). So a GET sweep of candidate paths returns a full procedure inventory
without credentials.

```bash
curl -s "https://app.<target>/trpc/<router>.<proc>?input=%7B%22json%22%3Anull%7D"
```

Harvest candidate `<router>.<proc>` names from the chunks first: react-query hooks of the form
`<ident>.<router>.<proc>.useQuery|useMutation|invalidate` are the reliable source (see
`scripts/trpc_enum.py`). Then classify. **A `200` is the prize** — a public procedure; the sweep on
a hardened target returned zero, which is itself a documented negative worth writing down so the
next session does not re-run it.

Guardrails:
- **GET only.** Never POST to a mutation to "see what happens" — `executeScans`, `redeem`,
  `activateOrganization`, `assign`, `update*`, `delete*` are state-changing. A GET to a mutation
  returns 405 and tells you it exists without invoking it.
- `400 badinput` = procedure exists and wants a typed input — note it, do not guess payloads blind.

## Pitfalls

- Do not `grep -oE '.{120}NEEDLE.{120}'` on a multi-MB single-line chunk: catastrophic backtracking,
  it hangs. Use windowed `str.find` (see Step 3b).
- Don't burn the run crawling 2000 chunks; 200–300 covers config + router names.
- The bundle run against one target: a same-named chunk (e.g. `ssh-config-*.js`) is reused across
  releases, so an "old vs new config diff" is only meaningful for the env chunk.
