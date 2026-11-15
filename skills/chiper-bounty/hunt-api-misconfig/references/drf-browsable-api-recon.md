# Django REST Framework: the browsable API is a schema oracle

DRF ships the browsable renderer by default. On any host where it is left enabled — extremely common on
control panels, SaaS back-offices and internal APIs — two requests hand you more structure than most
leaked OpenAPI specs, with no auth bypass needed:

```bash
# 1. field spec, per method, per endpoint
curl -s -H "Authorization: Token $T" -H "Accept: application/json" $API/systemuser/ -X OPTIONS

# 2. the actual FORM: enum values AND the real FK rows the server will let you reference
curl -s -H "Authorization: Token $T" -H "Accept: text/html"    $API/websitelocation/
```

Measured live 2026-10-25 against a hosting control panel (`api.djangoeurope.com`, DRF, 55 endpoints).

## What each view gives you

### `OPTIONS` → machine-readable field spec

```json
{"name":"Systemuser Instance","actions":{"POST":{
  "id":        {"type":"string","read_only":true},
  "name":      {"type":"string","required":false,"read_only":false,"max_length":32},
  "password":  {"type":"string","read_only":false},
  "server":    {"type":"field","read_only":true},
  "uid":       {"type":"integer","read_only":true},
  "limit_ram": {"type":"field","read_only":false},
  "status":    {"type":"field","read_only":true}}}}
```

Read it as an authorisation map, not documentation:

- **`read_only: true`** = the serializer drops that key if you send it. `uid`, `gid`, `home`,
  `has_password`, `is_superuser`, `is_staff`, `reporter`, `price`, `is_active` all landed here on this
  target — i.e. the whole obvious mass-assignment list is closed. Sending them is a no-op, and
  *verifying that* is how you avoid reporting a non-bug.
- **`read_only: false` on a value the customer should not set** is the finding. Here `limit_ram`,
  `limit_nproc`, `limit_data`, `can_su`, `is_active` (on some models) were writable.
- `"type":"choice"` with a `choices` array gives enum **values** (`ptype`: 0 local / 1 remote-IPv4 /
  2 remote-IPv6). `"type":"field"` (a nested serializer) does **not** list the values — that is what
  the HTML form is for.

### `Accept: text/html` → the HTML form (the FK / enum oracle)

The browsable renderer emits a real `<form>` with a `<select>` per relational field:

```
SELECT directive  8  root, redirect, proxy, uwsgi, webdav, ws, error_page, svn
SELECT port       3  --------, 127.0.0.1:62035, 127.0.0.1:62036
SELECT ca        67  Fake LE Root X1, Let's Encrypt Authority X1, ...
SELECT content_type 3 domain, systemgroup, system user
```

Three things fall out that `OPTIONS` refused to give:

1. **Enum slugs.** The FK column wants the *slug* (`proxy`), not the UUID. Sending a guessed integer
   produced `"WebsiteDirective does not exist"` for three attempts before the form showed the values.
2. **Real candidate rows.** The `<select>` is populated by the serializer's real queryset — if it is not
   tenant-scoped, it enumerates **other tenants' objects** (19 servers, 24 shared IPs here). Comparing
   that list against "what this account should see" is itself a finding candidate; don't skip it
   because the API JSON looked scoped.
3. **Which encodings are accepted** (`_content_type` select) and the exact field-name spelling the
   browser uses — which is what a real CSRF/HTML-form request must match.

Also grep the HTML for the token you already have: the form embeds the API token for its own submit
button, which confirms the token is the same credential the web UI uses.

### Error bodies are a working spec

DRF's validation errors name the exact constraint you just violated, and they are worth harvesting:

| message | what it tells you |
|---|---|
| `The fields website, path must make a unique set.` | composite unique constraint — reason about race/replay |
| `Incorrect type. Expected a UUID or dictionary, but got int` | the FK really wants a uuid object |
| `Invalid user name. The name must be a system user name or must start with a system user name followed by an underscore.` | a naming rule that encodes ownership — read it carefully, it may be the only tenancy check present |
| `Domain does not exist. Add the domain and make sure you have access to it.` | **the guard validates against a table the caller can write**. Check whether the "add" step itself verifies ownership, or the composite path is unprotected even though each message looks right |
| `Only https:// supported.` / `Max RAM limit is 16GB` | the validation that exists, and the ceiling it uses — compare that ceiling against the paid plan |

## Two differentials this surface makes cheap

**1. create vs update.** On this target `POST /systemuser/` accepted `limit_data: 500` with no check at
all, while `PATCH /systemuser/<id>/` validated against a **global absolute maximum** (16 GB / 1600 /
100 GB) and never against the customer's plan. Both are wrong in different ways and the pair is much
stronger evidence than either alone: the validator demonstrably knows how to refuse, and the number it
refuses is not the one the customer paid for. Always test create AND update, and read values back —
`200 OK` with the old value means the field is protected, not that you won.

**2. silent-ignore vs enforce.** `PATCH /systemgroup/ {"limit_ram":8}` returned **200** and changed
nothing (protected). `PATCH /systemuser/<id>/` changed it (not protected). Same field name, opposite
behaviour, one endpoint apart. Never infer enforcement from a status code; always re-GET.

## Auth shape

The token from `POST /login/mfa/` is bound to the `webkey` cookie it was issued with — replaying it from
a bare session gives `Invalid API token`, which reads like a bad credential. Additionally mint a
long-lived key once (`POST /token/ {"description":..., "expires_in":2592000}`) and use that for
standalone scripts; on this target it worked cookie-free and cut the whole OTP/token-rotation dance out
of the testing loop.

Note the deliberate restriction test: a token created with `permissions={"domain":{"view":true}}` does
read but gets `403` on write, and cannot mint a wider token (`POST /token/` → 403). So "the permission
model exists" is not the same as "the permission model is enforced everywhere" — check both, and check
that a narrow key cannot escalate.

## Checklist

1. `OPTIONS` every endpoint in the API root; build a table of `read_only` vs writable, flagging values a
   customer should not control.
2. `Accept: text/html` on every endpoint with a relational field; harvest enum slugs and FK rows, and
   count how many rows are not yours.
3. Send deliberate invalid values to collect the constraint messages; treat any message that mentions a
   *global* limit as a paywall-candidate.
4. For every writable numeric/boolean that maps to money, quota or privilege: create-vs-update
   differential, then re-GET to see what actually changed.
5. Only then write a payload.
