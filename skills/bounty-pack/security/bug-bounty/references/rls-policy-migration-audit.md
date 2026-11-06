# RLS policy audit — white-box multi-tenant authz from SQL migrations

Use when the target is a multi-tenant SaaS whose authorization lives in Postgres RLS
(Supabase, Cockroach), the source is public (AGPL/GitHub), and the vendor's security.txt
discourages automated scanning. White-box on the migration history is the highest-signal
lane and needs no live probing.

Worked case: Carbon (`github.com/crbnos/carbon`) — 1,704 live policies reconstructed,
scope-blind API-key gap found on 182 tables / 35 writable.

---

## 1. Reconstruct live policy state (last-op-wins)

Migrations are timestamped filenames; sort them and apply ops in order. Final state for a
`(policy, table)` key = the last op seen.

```python
POLICY_OP = re.compile(
    r'\b(DROP|CREATE)\s+POLICY\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?"([^"]+)"\s+ON\s+(?:"[a-z_]+"\.)?"([^"]+)"',
    re.I)
```

### Trap A — the quoted schema (cost a false "137 live policies")
Real syntax is `ON "public"."table"` — the schema is **quoted**. Pattern `(?:public\.)?`
does not match `"public".` (quote before the name, quote after). Group 2 then captures
`public` instead of the table, so every DROP is keyed to a phantom table and never
overrides its CREATE. Result: hugely inflated live count.
**Fix:** `(?:"[a-z_]+"\.)?`

### Trap B — DROP matched without its ON clause (cost a false "policy was dropped")
A looser `DROP\s+POLICY[^;]*"name"` matched an unrelated DROP and reported a policy as
removed while its table still carried it.
**Fix:** always require the `ON <table>` clause inside the same match.

### Verification habit (non-negotiable)
Before trusting any count: pick one table you can reason about by hand, print its full
event history, and confirm manually. Then print the policy BODIES.
**A count with no bodies is not evidence** — three wrong numbers were shipped in one
session before this step was done.

---

## 2. Classify scope-awareness by reading the HELPER, not the policy name

A policy body just calls a helper; the helper decides whether scopes matter. Read each
helper body once and bin it:

| Bin | Signature in the body | Effect for an API key |
|---|---|---|
| **scope-aware** | reads `current_setting('request.headers')` → `carbon-key` → `apiKey.scopes` and branches on it | returns `'{}'` when scopes empty/missing → denies |
| **scope-blind, key-aware** | `IF api_key_company IS NOT NULL THEN RETURN ARRAY[api_key_company]` | grants by company **regardless of scopes** |
| **key-unaware** | uses `auth.uid()` / `has_role()` / `has_company_permission()` | NULL for PostgREST anon+key → denies (fails closed) |

Known scope-blind helpers (Carbon): `has_valid_api_key_for_company()`,
`get_companies_with_employee_role()`, `get_companies_with_any_role()`.

**Trap C — never bin by function name.** `get_companies_with_employee_role` *sounds*
strict; it is the scope-blind one. Binning it as scope-aware under-counted the finding by
an order of magnitude.

---

## 3. The insight that carries the finding: PERMISSIVE policies OR together

A table with 4 scope-aware policies **plus** 1 scope-blind `FOR ALL` policy is fully
open — the blind one grants access and the others are neutralized. One missed blanket
policy defeats the whole table.

So the question is never "is this table scope-aware?" but:
> **Does ANY live policy on this table grant API-key access without a scope check?**

Also:
- `FOR ALL USING (p)` with no `WITH CHECK` ⇒ INSERT is checked with `p` too (writes included).
- No `TO <role>` clause ⇒ applies to `PUBLIC`, including `anon`.
- RLS `ENABLED` + zero policies ⇒ deny (safe). RLS never altered ⇒ check GRANTs instead.
- Confirm no later migration dropped the blanket policy — print the event history per table.

---

## 4. Docs promise vs. code comment = the finding, quoted

Search docs for the guarantee, then grep the authz module for a comment stating the
opposite. Worked example (Carbon):

- `docs/content/docs/building/api-keys.mdx:40` — *"A key with no scopes can authenticate
  but cannot read or write data."*
- `packages/database/src/authz/rules.ts:31-32` — *"any API key of it **regardless of the
  key's scopes**"*

Quote both with `file:line`. The contradiction is the report; severity needs no fresh
argument.

---

## 5. App-layer gate skip ≠ a finding until you check RLS compensation

When the app skips a scope check (e.g. `if (permission.module === null) return;`), that
alone is **not** a finding — the DB layer may compensate. Walk the affected tables:

- RLS scope-aware ⇒ app skip is defense-in-depth only; report as hardening at most.
- RLS scope-blind or key-unaware-but-permissive ⇒ both layers skip ⇒ real finding.

Report the **residual set**: tables where neither layer checks scope.

Symmetric check — an app-layer check with vacuously-true input is a no-op. Confirm what
the caller actually passes:
```js
Object.entries(requiredPermissions).every(...)   // {}  →  true, always
```
(`authenticateApiKey()` calls `requirePermissions(req, {})`.)

Also verify a tool's target table at all: a `WRITE`-classified tool on a pure function
that never touches the DB (`resolveBuyUnitCost`) is not a write path.

---

## 6. Deliverable shape

- counts: policies parsed, scope-aware vs blind, tables affected, writable subset
- exact policy bodies for every headline table
- the docs-vs-code contradiction, both sides quoted with file:line
- **mitigations that DO hold** — if tenant isolation is intact, say so plainly: this is a
  same-tenant scope bypass, not a cross-tenant leak. Calibrating down builds credibility.
- coverage split: source-verified vs not (proxy layer absent from repo, GRANT state often
  absent from repo — name them unknown, don't assume)

Never claim end-to-end without a live repro; label source-level explicitly.
