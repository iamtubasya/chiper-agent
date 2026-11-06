# SSRF through model-side fetching (tool schemas, `$ref`, image URLs)

Measured 2026-10-25 on Proton Lumo (`POST /api/ai/v1/chat/completions`) — unauthenticated blind SSRF,
reported as Medium. Applies to **any** product that exposes an OpenAI-compatible chat endpoint
(`messages` + `model` + `tools` + `stream`): Lumo, Copilot-style assistants, in-app "AI" features,
self-hosted gateways.

## 1. Where to look

1. Find the AI endpoint. Bundle grep beats guessing:
   ```bash
   grep -ohE '[`"]([a-z0-9/_${}.-]*(ai|llm|chat|completions|assistant)[a-z0-9/_${}.-]*)[`"]' *.js | sort -u
   ```
   Proton Lumo exposed exactly: `ai/v1/chat/completions`, `ai/v1/models`, `ai/v1/limits`,
   `ai/v1/feedback`, `lumo/v1/{spaces,settings,masterkeys,events,assets}`.
2. Fire one benign completion to learn the shape, then read `usage`:
   ```json
   {"model":"lumo-lite","messages":[{"role":"user","content":"Say OK"}],"stream":false,"max_tokens":5}
   → {"usage":{"remaining_limits":{"lite":99,"max":20,"images":20},"applied_limit_category":"lite"}}
   ```
   A per-category quota counter that decrements server-side is normal; a *client-settable* category is a
   finding (it was not, here).
3. Test every field the gateway might fetch on the server: `tools[].function.parameters.$ref`,
   `$schema`, `image_url.url`, `images[].url`, attachment/import URLs, and any "fetch this webpage" tool.

## 2. The primitive

```http
POST /api/ai/v1/chat/completions HTTP/1.1
Host: lumo.proton.me
Accept: application/json
Content-Type: application/json
x-pm-appversion: web-lumo@1.3.0

{"model":"lumo-lite","max_tokens":4,"stream":false,
 "messages":[{"role":"user","content":"hi"}],
 "tools":[{"type":"function","function":{"name":"t","description":"d",
   "parameters":{"$ref":"https://<collab>/poc.json"}}}]}
```
Server issues `GET /poc.json HTTP/2.0` with **only** `Host` and `Accept: */*` — no cookies, no
Authorization, nothing forwarded. Then it validates the fetched document as a JSON Schema.

## 3. ⚠️ The gate that decides SSRF-or-not: `description` is mandatory

**Without `description` the body fails validation and NO fetch happens:**
```
500 Unhandled rejection: InvalidBody("data did not match any variant of untagged enum IncomingToolSpec")
```
With `description` present: `200` + callback. Two consequences:

- **Do not conclude "no SSRF" from a malformed probe.** A missing/short field returns a fast 500 that
  looks identical to "the fetcher refused". Build the tool object exactly as the vendor's own client
  builds it (read the bundle), then vary only `$ref`.
- Keep the malformed variant as your **negative control** in the report: it proves the fetch is caused by
  schema resolution of a well-formed tool definition, not by the 500 path.

Useful fast tells measured here: refused loopback ≈ 1.5–2 s, "no fetch at all" ≈ 1.3–1.7 s, real
outbound fetch ≈ 3–6 s, filtered range = client/connect timeout ≈ 30 s. Time the request, don't only
look at the status.

## 4. Characterise the oracle before claiming impact

The oracle is **schema validity**, not "valid JSON". All documents below were served with HTTP 200, so
the split is content-driven:

| remote body (HTTP 200) | API | reading |
|---|---|---|
| plain JSON object (`{"slideshow":…}`) | 200 | accepted as an (empty) schema |
| real schema `{"type":"object","properties":{…}}` | 200 | accepted |
| `{"not":"a schema"}` (`not` must be a schema) | 500 | rejected — *proves schema validation* |
| HTML / XML / PNG | 500 | not JSON |
| empty body (`/status/204`, `/status/200`) | 500 | nothing to parse |

**Check for reflection before calling it a read primitive:** put a unique marker inside the fetched
document and grep the response for it. On Proton the marker never appeared ⇒ **boolean oracle only**.
Say "blind SSRF with a boolean content oracle", not "internal file read".

## 5. Proving it is server-side, not your client

- Run `interactsh-client -json -o oast.log -v` and log the **source address** of every callback.
- Compare with your own egress (`curl https://api.ipify.org`). Proton: 12 distinct Proton addresses vs
  researcher 104.28.226.245.
- A **redirect chain** settles it beyond argument: point `$ref` at a 302 (e.g.
  `httpbin.org/redirect-to?url=…`) and show the final hop in the collaborator log with the first hop in
  `Referer`. Proton followed redirects; note that this also defeats a first-hop allowlist.
- Expect **duplicate callbacks per payload** (Proton emitted 2, from different addresses) — that is two
  fetch paths in their stack, not a retry. Count payloads and callbacks separately.

## 6. Escalation ladder (do all of it — it decides severity)

| target | Proton result | what it means |
|---|---|---|
| `127.0.0.1:{22,80,443,3000,5432,6379,8080,9000,9200,10250,2375}` | all closed, 1.5–4 s | fetcher runs in an isolated netns with no local listeners |
| `172.17.0.1` (docker bridge) | closed | no reachable container API |
| `10.255.255.1`, `10.0.0.1`, `192.168.0.1` | 30–32 s | RFC1918 **dialled then filtered** ⇒ working host/port classifier |
| AWS ECS `169.254.170.2`, EKS `169.254.170.23`, IMDS `169.254.169.254`, Alibaba `100.100.100.200`, Oracle `192.0.0.192` | filtered / fast-fail | **no credentials** — say so |
| `metadata.google.internal`, `kubernetes.default.svc` | no DNS | cluster DNS not resolvable |
| `file://`, `gopher://` | refused | scheme allowlist |
| other endpoints (`/ai/v1/feedback`) | string-only body, no fetch | primitive confined to one route |

The closed-port-fast vs filtered-slow split is itself the impact argument: an unauthenticated party can
classify internal hosts/ports (open vs closed vs filtered) without any content. That is **Medium**.
Only escalate to High/Critical if you actually retrieve internal content or credentials — and if you
don't, write that limit into the Impact section explicitly. Reviewers pay for the honest ceiling.

## 7. Lumo-specific notes (verify before reuse — code rotates)

- Model tiers: `lumo-lite` (100/day), `lumo-max` (20/day), `lumo-preview` (capacity-gated, 503),
  `apertus-15`. **Unknown model names silently fall back to `lumo-lite`** (no error) — not a finding.
- Anonymous chat works and gets its own quota bucket (`lite: 20`) — test unauthenticated first.
- Client-supplied `{"role":"system"}` **is honoured** and overrides the hidden system prompt (verified:
  a pirate-persona system message changed the reply). Self-scoped only; no cross-user impact ⇒
  content-policy territory, program excludes content injection without significant risk. Drop it.
- Prompt extraction and tool-schema introspection both refused by the model.
- `X-Pm-Appversion` is mandatory on some paths (`{"Code":5002,"Error":"Missing x-pm-appversion header"}`).

## 8. Report skeleton that survived review

1. Plain-language summary (what fetches what, unauthenticated).
2. Raw repro with **no** Authorization header, plus the honest note that `description` is required.
3. Source addresses table (collaborator) vs researcher egress.
4. Oracle table (§4) including the invalid-schema row that proves schema parsing.
5. Timing/port matrix (§6) and what it does/doesn't prove.
6. Impact with an explicit ceiling sentence: "no internal content was retrieved because …".
7. Fix: local `#/` pointers only, or allowlist + block RFC1918/loopback/link-local + re-resolve DNS per
   redirect + short connect timeout (removes the timing oracle) + auth required for schema resolution.
