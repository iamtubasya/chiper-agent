# Plotly Dash apps: the callback engine is the API, and it is usually unauthenticated

Hit live 2026-10-13 (Arrakis engagement, `analytics.arrakis.finance`). Dash serves a lot of internal
analytics/finance dashboards, and its whole data flow runs through **two endpoints that most people
never think of as attack surface**. Both are discoverable without any login.

## Fingerprint in one request

The bundle advertises it: `_dash-component-suites/dash/dash-renderer/…`, `dash_core_components`,
`dash_table`, `dash_bootstrap_components`, and an HTML comment holding the app build id. Any 200 with
those paths is a Dash app.

## Endpoint 1 — `GET /_dash-dependencies` (public callback graph)

Returns the entire callback registry as JSON. Observed: **296 callbacks, 160 KB**, no auth.

```bash
curl -s https://target/_dash-dependencies -o dashdeps.json
python3 - <<'PY'
import json
d=json.load(open('dashdeps.json'))
print(len(d), "callbacks")
for i,c in enumerate(d):
    if c.get('clientside_function'): continue          # client-side = nothing to attack
    print(i, "|", c['output'][:90])
PY
```

This is the map: every server callback's `output` string, its `inputs`/`state`, and — most usefully —
**the component ids of every gate and every data store**. In the worked case it handed over
`login-password`, `revenue-password-input`, `auth-store`, `revenue-data-store`, `revenue-vault-table`
and the per-vault `selected-vault-store` without a single guess.

`GET /_dash-layout` is also public and gives the component tree (the `dcc.Store` entries and their
`storage_type: session` vs `local` are how you tell which "auth" is client-side only).

## Endpoint 2 — `POST /_dash-update-component` executes callbacks

The request is the callback's `output` string plus `inputs`/`state`/`changedPropIds`. Build it
**verbatim from `/_dash-dependencies`** — a partial or hand-typed `output` string silently returns
`{"multi":true,"response":{}}` (that empty response looks like a dead end and is really a bad key).

```python
req = {"output": cb['output'],                  # exact string, do not truncate
       "outputs": [{"id": o.rsplit('.',1)[0].lstrip('.'), "property": o.rsplit('.',1)[1]}
                   for o in cb['output'].split('...') if o],
       "inputs":  [{"id": i['id'], "property": i['property'], "value": <must match the type>}
                   for i in cb['inputs']],
       "state":   [{"id": s['id'], "property": s['property'], "value": None} for s in cb['state']],
       "changedPropIds": [f"{cb['inputs'][0]['id']}.{cb['inputs'][0]['property']}"]}
```

Send it with `Referer: <origin>/` and `Origin: <origin>`. **Watch the value types** — a password field
needs a *string*; passing an int there produced a 500, not a 401, and sent the triage down the wrong path
for a while.

## What the gate actually is (and is not)

Two different barriers showed up and they must not be confused:

- **`Referer`/`Origin` absence → `401 {"error":"unauthorized"}`.** Adding the two headers flipped the
  *same* request to 200. That is a CSRF-ish origin check, not authentication — but it is also not a
  vulnerability on its own, because the caller controls both headers.
- **Per-callback authorisation that survives the headers → 401.** Of the sampled callbacks, the login
  callback and a couple of store writers ran unauthenticated; `page-content`, `revenue-*`, `vaults`,
  `grafana` and the per-vault detail callbacks all answered 401 with the same headers. So there IS an
  allowlist; map it (`{200, 401}` per callback) before claiming anything.

**Report only what is allowlisted and useful.** In the worked case that was the login callback, and the
finding was this:

> an anonymous POST reaches the password check, the response distinguishes a correct password from a
> wrong one (`"Invalid password"`), and nothing throttles it — **20 attempts in a row returned
> `{200: 20}`**, no 429, no lockout, ~1.2 s each.

That is CWE-307 / CWE-204. Verify it the same way: 3 identical runs (compare `md5` of the bodies —
byte-identical proves determinism), then one burst purely to measure the throttle. Do **not** run a
dictionary; say in the report that the attempts were fixed probe strings used to measure the limit.
Note in "what I did NOT do" that the data callbacks still 401, so authorisation on the data is intact —
the missing control is the limit on the login itself.

## Remediation that lands

Rate limit + lockout on the login callback (per IP and per session), a delay that grows with failures,
CAPTCHA after a few, and put `/_dash-dependencies` behind auth too — it maps exactly what the password
protects. Client-side-only gates (`dcc.Store` with no server check) are worth flagging separately: if a
Store is the only thing gating data, the data callbacks are the place to prove it.

## Cheapest triage order

1. `GET /_dash-dependencies` → is it public? (almost always yes)
2. `POST /_dash-update-component` with the login callback + `Referer`/`Origin` → 200 or 401?
3. If 200: is the wrong-password response distinguishable, and is there any throttle?
4. Map `{200,401}` across the callback list; anything 200 that returns data is the real finding.
