# Multi-tenant SaaS white-box review (RLS-backed apps)

Worked from the carbon.ms / Carbon ERP engagement (2026-10). Target: an open-source
(AGPL) multi-tenant manufacturing ERP with a live Cloud deployment, Supabase/Postgres
RLS as the tenant boundary, API keys + OAuth connectors as machine auth.

## 1. The lane decision (third route, neither pure codebase nor pure web2)

PART 0's original table assumes either "assets = repos" or "assets = live domains".
This engagement was neither:

- Live hosts exist (`carbon.ms`, `app`, `rest`, `api`, `docs`, `mes`, `console`, `go`,
  `itar`, `csa` subdomains — enumerated from certspotter CT, not scanning).
- `/.well-known/security.txt` is published and says, verbatim:
  *"Do not run automated scanners on our infrastructure or dashboard. If you wish
  to do this, contact us and we will set up a sandbox for you."*
- The product source is public (`github.com/crbnos/carbon`, AGPL-3.0).

Correct routing: **scanners become N/A (not "passed") — see PART 0's HARD RULE — and
the track becomes source review of the public repo.** Log the clause once in the risk
log per `recon-scope-triage`'s "policy EXISTS but PROHIBITS the method" section; do not
re-raise it every turn. Passive recon (CT, robots/llms, OpenAPI, `.well-known`) is not
automated scanning and stays in play.

## 2. Surface map to build BEFORE reading a line of code

Cheap passive pulls that tell you what the code will contain:

| Artifact | What it gives you |
|---|---|
| `/.well-known/security.txt` | contact, safe-harbour, **prohibited methods**, OOS classes |
| `/robots.txt` → `/llms.txt` | the product's *own* description of plan tiers, which features are paid, API key semantics, rate limits, versioning policy |
| `/openapi.json` | the operation list → becomes your authorization test matrix |
| `/.well-known/oauth-authorization-server` + `oauth-protected-resource` | DCR endpoint, PKCE requirement, scope names, grant types |
| `/.well-known/mcp.json` (or equivalent manifest) | machine surface + declared auth scheme |
| certspotter CT (`include_subdomains=true`) | full subdomain set; reveals an app-per-vertical split (erp/mes/console/itar/csa) that implies separate tenant-isolation surfaces |

`llms.txt` in particular is a self-authored spec of the **business logic** — plan gating,
trial mechanics, per-key rate limits — which is exactly the surface the business-logic
hunting skill wants.

## 3. The bug class: a cache key that omits a dimension its value depends on

**This is the highest-value shape on this class of target. Grep for it first.**

Pattern: `getClaims(userId, companyId)` returns a value with a *company-specific* field,
but the cache key is built from `userId` only.

Observed shape (candidate — investigation was in progress, NOT yet a confirmed finding):

```ts
// key has NO company component
export function getPermissionCacheKey(userId: string) {
  return `permissions:${userId}`;
}

// but the cached payload is derived per-company
async function loadUserClaims(userId: string, companyId: string) {
  const cached = await redis.get(getPermissionCacheKey(userId)); // ignores companyId
  if (cached) return JSON.parse(cached);
  const raw = await getClaims(serviceRole, userId, companyId);   // role IS company-scoped
  await redis.set(getPermissionCacheKey(userId), JSON.stringify(claims), "EX", 3600);
}
```

Backed by a `SECURITY DEFINER` RPC whose `role` comes from
`SELECT role FROM "userToCompany" WHERE userId = uid AND companyId = company` —
so `role` genuinely differs per company for one user (employee in their own company,
portal `customer`/`supplier` in another).

### Why it matters here: `role` gates RLS bypass

```ts
client: requiredPermissions.bypassRls && myClaims.role === "employee"
  ? serviceRoleForRequest()      // full RLS bypass
  : carbonForRequest(accessToken, request)
```

And the same `role` drives the portal-account 403 gate. So a stale `"employee"` from
company A served while the session is scoped to company B would (a) skip the portal
rejection and (b) hand back a service-role client. Dozens of routes request
`bypassRls: true` — enumerate them with:

```bash
rg -n "bypassRls" --glob '*.ts' --glob '*.tsx' | grep -v '.test.'
```

### Verification checklist before filing (all four required)

1. **Does `role` actually differ across companies for one user?** Read the RPC's SQL and
   confirm `role` is selected per-`companyId`, not per-user.
2. **Is the cache invalidated on company switch?** Look for `redis.del(getPermissionCacheKey(...))`
   in the session-company switch handler. If present, read HOW it's issued — a
   fire-and-forget (not awaited) `redis.del` plus a documented "fails soft, TTL heals it"
   comment means the invalidation is *best-effort*, and there is a real window.
3. **What is the TTL?** 3600 s = the maximum staleness window; state it in severity.
4. **Is there a second gate that closes it?** Per-request memoisation
   (`oncePerRead(\`claims:${userId}:${companyId}\`)`) scopes *within* a request but not
   across requests — confirm the cross-request Redis read is the one that wins.

**Never file from the code shape alone.** Session rule: a candidate that cannot be
reproduced is `UNSTABLE`, not a finding. If steps 2–4 don't hold, log it under
VERIFIED NEGATIVES with the reason.

### Related shapes to sweep on the same target

- **`SECURITY DEFINER` RPCs called via service-role from app code** — the
  `current_setting('role')` guard inside them is inert when the caller is service role.
  Diff which RPCs have the guard and which don't.
- **A company-scoping proxy that wraps only some verbs.** Observed: a proxy that injects
  `.eq("companyId", …)` on `update`/`delete` only, with reads/inserts/RPCs explicitly
  documented as passing through untouched — so every read must be trusted to RLS
  independently. Check the RPCs.
- **Dynamic client registration open by design** (`POST /register` → `201`,
  `Access-Control-Allow-Origin: *`). Usually intended for MCP/OAuth connectors; verify a
  rate limit exists and that `redirect_uris` are validated (https / loopback-only http /
  private-use scheme, no fragment) rather than reporting "open DCR" as a finding.
- **Auth-path parity.** Machine auth (API key header) and user auth (session) take
  different branches into the same permission gate. Where an operation's permission
  check lives in one branch's middleware and not the other, the other path is ungated.

## 4. Coverage honesty for this track

Report the scanner layer as `N/A (policy prohibits automated scanning — quoted)` and the
source layer with a per-surface ledger. Do not write "clean" for anything untested.
