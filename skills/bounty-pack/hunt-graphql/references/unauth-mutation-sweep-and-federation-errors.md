# The unauthenticated mutation sweep, and what federation errors leak

Cheap, systematic, and it finds a class the field-level work misses: **resolvers whose auth gate lives in
the wrong place**. Verified on `api.blink.sv` (Apollo Router + Federation, 68 mutations), 2026-10-13.

## 1. Sweep every mutation with NO token — the whole point is the zero-arg ones

Introspect once, then drive the probe from the schema so nothing is skipped:

```python
# fields = __type(name:"Mutation"){fields{name args{name type{kind name}}}}
args = ["%s: null" % a["name"] for a in f["args"]]
q = "mutation{ %s(%s){ __typename } }" % (f["name"], ", ".join(args))
```

Record the *error class*, not just "failed":

| response | meaning |
|---|---|
| `Not authorized` (NOT_AUTHORIZED) | gateway/resolver scope check ran — gate is where it should be |
| `Expected value of type "XInput!", found null` | **input validation runs before the auth check** — the mutation is `Auth`-gated but you cannot tell from this probe; re-probe with a *well-formed but junk* argument |
| `Subrequest HTTP error … service: "<name>"` | **the request left the gateway and hit an internal subgraph with no user context** (see below) |
| real `data` | anonymous by design (`captchaCreateChallenge`) or a finding |

**The zero-argument mutations are the ones that tell the truth.** With no input to validate, the gateway's
auth decision is the only thing left in the path, so an auth-gated resolver answers `Not authorized`
immediately. In the Blink sweep, 8 of 9 zero-arg mutations behaved (accountDelete, migrationStart,
supportChatReset, userEmailDelete, userLogout, userPhoneDelete, userTotpDelete,
userTotpRegistrationInitiate) and **one did not**:

```graphql
mutation{ kycFlowStart{ __typename } }        # no Authorization header, no arguments
```
```json
{"data":null,"errors":[
  {"message":"HTTP fetch failed from 'blink-kyc': 500: Internal Server Error",
   "extensions":{"code":"SUBREQUEST_HTTP_ERROR","service":"blink-kyc",
                 "reason":"500: Internal Server Error","http":{"status":500}}},
  {"message":"Context creation failed: Token is anon","extensions":{"code":"INTERNAL_SERVER_ERROR"}}]}
```

## 2. What a federation subrequest error is actually worth (and what it is not)

Read it honestly — this is **information disclosure + a gating inconsistency**, not access:

- Leaks the **internal subgraph service name** (`blink-kyc`), the federation error taxonomy, and the
  internal auth-context state (`"Token is anon"` = the router forwarded an anonymous token upstream).
- Proves the resolver had **no gateway-level auth gate** while its siblings did → inconsistent enforcement
  worth a hardening ticket.
- Does **not** leak data or change state: the subgraph answers `500` for an anonymous context. Score it
  LOW/INFO and say so — inflating this into "unauthenticated access to KYC" is the kind of over-claim that
  gets a whole report downgraded.

Confirm it reproduces (3 runs) and store the raw JSON as evidence; note the sibling contrast explicitly
(`accountDelete` → `Not authorized` **vs** `kycFlowStart` → subrequest error) — that contrast is what makes
it a code-level inconsistency rather than an environment quirk.

## 3. Gateway-gated ≠ resolver-gated: the four checks to run while you are there

1. **Same-op, different verb/route**: re-issue the zero-arg mutation as a `query{…}` — a `parsing error:
   cannot query field 'X' on type 'Query'` confirms you are hitting the real schema, not a proxy cache.
2. **Auth-header shapes**: a *bogus* `Authorization: Bearer x` answering `401` at the **edge (nginx page)**
   means credentials are evaluated when present; no header at all falling through to the GraphQL layer means
   anonymous traffic is expected. Record which header names the edge accepts
   (`Access-Control-Allow-Headers` on the 401 lists them: `Authorization, X-API-KEY, oauth2-token`).
3. **Public query surface**: enumerate `Query` fields too and check each unauthenticated — on the same
   target only 22 queries, all by-design (leaderboard, wallet-id lookup by username, prices). Say "by
   design" out loud instead of padding the report.
4. **Rate-limit the unauth-legal ones** rather than assuming: `POST /auth/email/code` for your own mailbox
   then N wrong codes on `/auth/email/login` → on Blink, 5 × `401 invalid code` then **sticky `429`** for the
   rest of the run = the limiter holds (negative with evidence, not a finding).

## 4. Reporting shape for a sweep negative

The sweep's main product is often the **coverage line**, not a finding:

```
tested: all 68 mutations unauthenticated (schema-driven, one probe each)
held:  67 — either 'Not authorized' at the gateway or input-validation-first
weak:   1 — kycFlowStart (no gateway gate; internal subgraph error leaked service name) -> LOW/INFO, hardening
```
Keep the raw per-mutation JSON (`{name, error_class, message}`) as the artefact; without it the negative is
unverifiable and the claim "I tested all mutations" is just a sentence.
