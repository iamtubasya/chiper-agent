# Optimization Patterns — worked fixes by symptom

> Each section is the "worked fix" behind a bullet in the SKILL.md anti-pattern
> list. Open the one you need when you reach that code — not before.
> Anchors are stable so `SKILL.md` links resolve.

---

## N+1 queries (backend) {#n1-queries-backend}

**Signature.** A loop that issues one query per row: `for u in users: u.posts`.
Shows up as query count scaling linearly with result size.

**Fix.** One query with an eager join / `include` / `prefetch_related`.
```python
# before — N+1
users = User.all()
for u in users:
    print(u.posts.count())          # one query per user

# after — 2 queries total
users = User.objects.prefetch_related("posts")
```
**Verify.** Log the query count before/after; it should stop growing with N.

---

## Unbounded data fetching {#unbounded-data-fetching}

**Signature.** `SELECT *` / `.all()` / `findMany()` with no `LIMIT`, on a table
that only grows. Works in staging, dies in production.

**Fix.** Page or cap at the query, not the client. Prefer keyset pagination over
`OFFSET` for deep pages (OFFSET re-scans).
```python
page = Post.objects.filter(id__gt=after_id).order_by("id")[:100]
```

---

## Queries that ignore their index {#queries-that-ignore-their-index}

**Signature.** A filter/order column with no matching index; `EXPLAIN` shows a
sequential scan on a large table.

**Fix.** Add the index that matches the actual predicate + sort order. Composite
index column order matters: equality columns first, range/sort last.
```sql
CREATE INDEX idx_orders_user_status_created
  ON orders (user_id, status, created_at DESC);
```
**Verify.** Re-run `EXPLAIN ANALYZE` — the plan should switch to an index scan.

---

## Connection-pool exhaustion {#connection-pool-exhaustion}

**Signature.** Latency climbs under concurrency; errors like "too many clients"
/ "timeout acquiring connection". Often a leaked connection on an error path.

**Fix.** Size the pool to the DB's real limit, always release in `finally` /
context manager, and set a bounded acquire timeout so failures are fast.
```python
with engine.connect() as conn:      # never rely on GC to release
    ...
```
Match `pool_size + max_overflow` across all app instances to the server's
`max_connections` — oversubscribing just moves the queue.

---

## Missing caching (backend) {#missing-caching-backend}

**Signature.** The same expensive, slow-changing read recomputed every request.
Trace shows a hot endpoint spending most of its time in one query/computation.

**Fix.** Cache at the level that matches the invalidation truth; set a TTL as a
backstop. Cache the *result*, not the query builder.
```python
val = cache.get(key)
if val is None:
    val = expensive()
    cache.set(key, val, ttl=300)
```
Never cache per-user data under a shared key — that is a data-leak bug, not just
a staleness one.

---

## Missing image optimization (frontend) {#missing-image-optimization-frontend}

**Signature.** Largest Contentful Paint dominated by one oversized image;
full-resolution asset shipped into a thumbnail slot.

**Fix.** Serve responsive sizes and a modern format; set explicit dimensions to
avoid layout shift.
```html
<img src="hero.webp" srcset="hero-480.webp 480w, hero-960.webp 960w"
     sizes="(max-width: 600px) 480px, 960px" width="960" height="540"
     loading="lazy" decoding="async" alt="">
```

---

## Unnecessary re-renders (React) {#unnecessary-re-renders-react}

**Signature.** React DevTools Profiler shows a subtree re-rendering when its
props did not change. Usually an inline object/array/function prop, or context
that changes on every render.

**Fix.** Stabilize identities and split context. Measure before memoizing —
blind `useMemo`/`memo` adds cost and hides the real dependency.
```jsx
const handler = useCallback(() => submit(id), [id]);
const options = useMemo(() => ({ sort, filter }), [sort, filter]);
```
A list that re-renders wholesale is often a `key={index}` problem — use a stable id.

---

## Large bundle size {#large-bundle-size}

**Signature.** A single chunk in the megabytes; a heavy library imported at the
top level for one function.

**Fix.** Route-level code splitting, dynamic import for heavy widgets, and drop
moment/lodash-style whole-library imports for tree-shakeable ones.
```js
const Chart = lazy(() => import("./Chart"));
```
**Verify.** Compare the analyzer output before/after; a chunk should shrink for a
reason you can name.
