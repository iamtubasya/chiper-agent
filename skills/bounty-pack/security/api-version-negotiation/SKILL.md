---
name: api-version-negotiation
description: "Unlock APIs that 404 with 400 invalid-version."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [api-recon, bug-bounty, versioning, accept-header, media-type, oracle, authz]
---

# API Version Negotiation — the hidden route surface behind Accept headers

## When to Use

- An API (Rails/Stripe/Salemove-style) returns `404 Route Not Found` on nearly every guessed path,
  but one or two return `400 "Invalid api version used"` — versioning is in the `Accept` media-type
  header, not the URL.
- You need a cheap route-existence oracle (400 vs 404) to enumerate a hidden API surface, or to test
  version-downgrade authz bypass.

Some APIs version their routes **not** in the URL path (`/v1/`, `/api/v2/`) but in the
**`Accept` media-type header** (`application/vnd.<vendor>.<version>+json`). When you miss that, every
route looks dead. This skill turns the two symptoms into a discovery + access-control oracle.

## The core symptom pattern

Two observations, seen together, are the fingerprint:

1. A blanket `404 Route Not Found` / `{"error":"Not found"}` on almost every path you guess.
2. One or two paths return **400 `"Invalid api version used"`** (or `"Invalid api version"`,
   `"unsupported media type"` / `415`) — the route **exists** but you sent the wrong version key.

The 400 is the prize: it proves the route is wired and tells you the version lives somewhere other
than the URL.

## Technique — find the version key

Try these in order; the vendor media-type form is the most common:

```bash
# 1) vendor media type (most common for Rails/Salemove/Stripe-style APIs)
curl -s https://<target>/sites/<id> -H "Accept: application/vnd.<vendor>.v1+json"

# 2) bare version
curl -s ... -H "Accept: application/vnd.<vendor>+json"

# 3) fall back to plain JSON (often 400 invalid version → confirms media-type is the gate)
curl -s ... -H "Accept: application/json"
```

The magic string shape is almost always `application/vnd.<name>.<ver>+json`. When you have a real
domain (`api.salemove.com` → `vnd.salemove.v1`), derive the `<name>` from the host/company; when you
don't, grep the JS bundle for the literal `application/vnd.` string.

```python
# recover the exact media type from the client bundle when you have it
import re
bundle = open("app.min.js", encoding="utf-8", errors="ignore").read()
for m in set(re.findall(r'application/vnd\.[a-z0-9.-]+\+json', bundle)):
    print(m)   # e.g. application/vnd.salemove.v1+json
```

The route that returned 400 without the header flips to **200/401/403** with the correct one — that
is the whole undocumented API surface becoming reachable.

## The oracle — 400 "invalid version" vs 404 = route EXISTS

This is a **route-existence oracle** you can exploit before you even know the version string:

| Response | Meaning |
|---|---|
| `404 Route Not Found` | path never registered — dead guess, move on |
| `400 Invalid api version used` | route **exists**; version key is just wrong/missing |
| `200` | route + version correct and (for this identity) authorized |
| `401` / `403` | route + version correct but **authz-scaled** (denied or wrong token) |

Use it to enumerate candidate paths cheaply: anything that returns 400 (not 404) is a real route,
just hidden behind the Accept version. Then once you have the version string, re-probe and the
401/403-vs-200 split is a live access-control map.

## Authz implications (why this pays)

- **Version downgrade.** Re-send the same route with an OLDER media-type version (`v0`, `v1`, or a
  media type the router doesn't validate). Older routes frequently carry weaker or missing authz.
  Observed shape: `Accept: application/vnd.<vendor>.v1+json` → 200, but `.v2+json`/`.v0+json` → 400,
  exactly because v1 is the only/weakest registered version.
- **The 401/403 differential names the operator surface.** After the right Accept header, `/sites/{id}`
  may return 200 (own) but 403 (other tenant) — that 403 is the scoping wall, and you test whether the
  version-downgrade path skips it.

## False-positive guard

A `200` on your OWN object is correct scoping, not a bug. A `201` from a mint endpoint that still
writes **your own** identity in the response (decode the token/MessagePack and confirm the account_id
is yours) is the server *ignoring* your supplied foreign ID — not IDOR. Always read back the effect,
never trust the status code. (See the Cross-Tenant-Write rule in `bb-methodology`.)

## Pitfalls

- Version can also live in a **query param** (`?version=1`) or a custom header (`X-Api-Version`,
  `X-Version`) — but the media-type Accept form is the one that re-hides plain `/sites/{id}` routes,
  so try it before the query/header forms.
- `Accept: */*` and `Accept: application/json` are usually rejected (400) by media-type-versioned
  routers — that rejection is itself the confirm signal, not a dead end.

## Related

- `hunt-api-misconfig` — the version-downgrade probe family (URL-prefixed `/v1/` vs `/v2/`).
- `security-recon` Step 3b — JS-bundle API-surface extraction (how you recover the exact media type
  and endpoint strings).
- `hunt-idor` / `bb-methodology` Cross-Tenant-Write rule — reading back the effect before claiming BOLA.